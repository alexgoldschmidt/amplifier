"""Webhook Accelerator - Optional HTTP endpoint for ADO Service Hooks.

Receives webhooks from Azure DevOps and triggers immediate polls,
reducing latency from poll interval to near-real-time without
depending on webhooks for correctness.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .monitor import Monitor

logger = logging.getLogger(__name__)


class WebhookReceiver:
    """HTTP endpoint for ADO Service Hook webhooks."""

    def __init__(
        self,
        monitor: "Monitor",
        secret: str | None = None,
    ) -> None:
        """Initialize the webhook receiver.

        Args:
            monitor: The running monitor instance
            secret: Optional HMAC secret for signature validation
        """
        self.monitor = monitor
        self.secret = secret
        self._recent_webhooks: set[str] = set()
        self._recent_lock = asyncio.Lock()

    def _verify_signature(self, payload: bytes, signature: str | None) -> bool:
        """Verify the HMAC signature from ADO.

        Args:
            payload: Raw request body
            signature: Signature from X-Hub-Signature header

        Returns:
            True if signature is valid or no secret configured
        """
        if self.secret is None:
            return True

        if signature is None:
            logger.warning("Missing signature on webhook request")
            return False

        # ADO uses sha1 HMAC
        expected = hmac.new(
            self.secret.encode(),
            payload,
            hashlib.sha1,
        ).hexdigest()

        # Signature format: sha1=<hex>
        if signature.startswith("sha1="):
            signature = signature[5:]

        return hmac.compare_digest(expected, signature)

    def _extract_subscription_id(self, data: dict[str, Any]) -> str | None:
        """Extract subscription ID from webhook payload.

        ADO Service Hooks send JSON with structure:
        {
          "eventType": "git.pullrequest.updated",
          "resource": {
            "repository": {"name": "myrepo", "project": {"name": "myproject"}},
            "pullRequestId": 123
          },
          "resourceContainers": {
            "account": {"baseUrl": "https://dev.azure.com/myorg/"}
          }
        }

        We match to subscription via: org + project + repo + pr_id
        or: org + project + work_item_id
        """
        try:
            event_type = data.get("eventType", "")
            resource = data.get("resource", {})
            containers = data.get("resourceContainers", {})

            # Extract org from account baseUrl
            account_url = containers.get("account", {}).get("baseUrl", "")
            org = self._extract_org_from_url(account_url)
            if not org:
                return None

            # PR events
            if "pullrequest" in event_type.lower():
                repo_info = resource.get("repository", {})
                project = repo_info.get("project", {}).get("name")
                repo = repo_info.get("name")
                pr_id = resource.get("pullRequestId")

                if project and repo and pr_id:
                    # Match against subscriptions
                    return self._find_pr_subscription(org, project, repo, pr_id)

            # Work item events
            if "workitem" in event_type.lower():
                project = resource.get("fields", {}).get("System.TeamProject")
                work_item_id = resource.get("id")

                if project and work_item_id:
                    return self._find_wi_subscription(org, project, work_item_id)

        except Exception:
            logger.exception("Error extracting subscription from webhook")

        return None

    def _extract_org_from_url(self, url: str) -> str | None:
        """Extract org name from ADO URL."""
        # https://dev.azure.com/myorg/ -> myorg
        if "dev.azure.com/" in url:
            parts = url.split("dev.azure.com/")
            if len(parts) > 1:
                return parts[1].strip("/").split("/")[0]
        return None

    def _find_pr_subscription(self, org: str, project: str, repo: str, pr_id: int) -> str | None:
        """Find subscription matching PR coordinates."""
        for sub_id, sub in self.monitor.subscriptions.items():
            if (
                sub.org == org
                and sub.project == project
                and sub.repo == repo
                and sub.pr_id == pr_id
            ):
                return sub_id
        return None

    def _find_wi_subscription(self, org: str, project: str, work_item_id: int) -> str | None:
        """Find subscription matching work item coordinates."""
        for sub_id, sub in self.monitor.subscriptions.items():
            if sub.org == org and sub.project == project and sub.work_item_id == work_item_id:
                return sub_id
        return None

    async def _deduplicate_webhook(self, payload_hash: str) -> bool:
        """Check if we've recently seen this webhook.

        Args:
            payload_hash: Hash of the webhook payload

        Returns:
            True if this is a duplicate (should be ignored)
        """
        async with self._recent_lock:
            if payload_hash in self._recent_webhooks:
                return True

            # Add to recent set
            self._recent_webhooks.add(payload_hash)

            # Prune old entries (keep last 1000)
            if len(self._recent_webhooks) > 1000:
                # Remove oldest (arbitrary since set is unordered, but good enough)
                to_remove = list(self._recent_webhooks)[:500]
                for h in to_remove:
                    self._recent_webhooks.discard(h)

            return False

    async def handle_webhook(
        self,
        payload: bytes,
        signature: str | None = None,
    ) -> tuple[int, str]:
        """Handle incoming ADO Service Hook webhook.

        Args:
            payload: Raw request body
            signature: Optional X-Hub-Signature header

        Returns:
            Tuple of (status_code, message)
        """
        # Verify signature if secret configured
        if not self._verify_signature(payload, signature):
            return (401, "Invalid signature")

        # Parse payload
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return (400, "Invalid JSON")

        # Deduplicate
        payload_hash = hashlib.sha256(payload).hexdigest()[:16]
        if await self._deduplicate_webhook(payload_hash):
            logger.debug("Ignoring duplicate webhook")
            return (200, "OK (duplicate)")

        # Find matching subscription
        subscription_id = self._extract_subscription_id(data)
        if not subscription_id:
            logger.debug("No matching subscription for webhook")
            return (200, "OK (no match)")

        # Trigger immediate poll
        logger.info(f"Webhook triggering immediate poll for {subscription_id}")
        await self.monitor.trigger_immediate_poll(subscription_id)

        return (200, "OK")


async def create_webhook_app(
    monitor: "Monitor",
    secret: str | None = None,
) -> Any:
    """Create a Starlette ASGI app for the webhook receiver.

    Args:
        monitor: The running monitor instance
        secret: Optional HMAC secret for signature validation

    Returns:
        Starlette application instance
    """
    try:
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
    except ImportError as e:
        raise ImportError(
            "Webhook support requires starlette. Install with: "
            "pip install ado-event-monitor[webhook]"
        ) from e

    receiver = WebhookReceiver(monitor, secret)

    async def webhook_handler(request: Request) -> PlainTextResponse:
        payload = await request.body()
        signature = request.headers.get("X-Hub-Signature")
        status, message = await receiver.handle_webhook(payload, signature)
        return PlainTextResponse(message, status_code=status)

    async def health_handler(request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    routes = [
        Route("/webhook/ado", webhook_handler, methods=["POST"]),
        Route("/health", health_handler, methods=["GET"]),
    ]

    return Starlette(routes=routes)
