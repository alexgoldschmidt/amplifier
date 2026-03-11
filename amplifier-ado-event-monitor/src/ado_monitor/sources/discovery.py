"""Discovery subscription source.

Dynamically discovers PRs and work items assigned to the current user
by querying Azure DevOps APIs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..models import Action, Subscription, SubscriptionType
from ..poller import ADOClient

logger = logging.getLogger(__name__)


@dataclass
class PRDiscoveryConfig:
    """Configuration for PR discovery."""

    org: str
    project: str
    repo: str
    filter: str = "assigned_to_me"  # or "created_by_me"
    poll_interval_seconds: int = 60


@dataclass
class WorkItemDiscoveryConfig:
    """Configuration for work item discovery."""

    org: str
    project: str
    filter: str = "assigned_to_me"
    area_path: str | None = None  # Optional area path filter
    poll_interval_seconds: int = 120


class DiscoverySubscriptionSource:
    """Discovers PRs and work items assigned to the current user.

    Queries ADO APIs to find:
    - PRs where user is a reviewer or creator
    - Work items assigned to the user

    Generates subscriptions dynamically based on discovery results.
    """

    source_id: str = "discovery"

    def __init__(
        self,
        pr_configs: list[PRDiscoveryConfig] | None = None,
        wi_configs: list[WorkItemDiscoveryConfig] | None = None,
        default_pr_actions: list[Action] | None = None,
        default_wi_actions: list[Action] | None = None,
    ) -> None:
        """Initialize the discovery source.

        Args:
            pr_configs: List of PR discovery configurations.
            wi_configs: List of work item discovery configurations.
            default_pr_actions: Default actions for discovered PRs.
            default_wi_actions: Default actions for discovered work items.
        """
        self.pr_configs = pr_configs or []
        self.wi_configs = wi_configs or []

        self.default_pr_actions = default_pr_actions or [
            Action(agent="ado-pr-manager", trigger="new-comments", behavior="address-feedback"),
            Action(agent="ado-pr-manager", trigger="vote-change", behavior="check-approval"),
        ]

        self.default_wi_actions = default_wi_actions or [
            Action(agent="ado-work-items", trigger="comment-added", behavior="process-comment"),
            Action(agent="ado-work-items", trigger="state-change", behavior="sync-status"),
        ]

        # Cache clients per org
        self._clients: dict[str, ADOClient] = {}

    def _get_client(self, org: str) -> ADOClient:
        """Get or create an ADO client for the org."""
        if org not in self._clients:
            self._clients[org] = ADOClient(org)
        return self._clients[org]

    async def get_subscriptions(self) -> list[Subscription]:
        """Discover and return subscriptions for user's PRs and work items.

        Returns:
            List of subscriptions for discovered entities.
        """
        subscriptions: list[Subscription] = []

        # Discover PRs
        for config in self.pr_configs:
            try:
                pr_subs = await self._discover_prs(config)
                subscriptions.extend(pr_subs)
            except Exception:
                logger.exception(
                    f"Failed to discover PRs for {config.org}/{config.project}/{config.repo}"
                )

        # Discover work items
        for config in self.wi_configs:
            try:
                wi_subs = await self._discover_work_items(config)
                subscriptions.extend(wi_subs)
            except Exception:
                logger.exception(f"Failed to discover work items for {config.org}/{config.project}")

        return subscriptions

    async def _discover_prs(self, config: PRDiscoveryConfig) -> list[Subscription]:
        """Discover PRs matching the config filter."""
        client = self._get_client(config.org)
        prs = await self._query_my_prs(client, config)

        subscriptions = []
        for pr in prs:
            pr_id = pr.get("pullRequestId")
            if pr_id is None:
                continue

            sub = Subscription(
                id=f"discovery:pr-{config.org}-{config.project}-{config.repo}-{pr_id}",
                type=SubscriptionType.PULL_REQUEST,
                org=config.org,
                project=config.project,
                repo=config.repo,
                pr_id=pr_id,
                poll_interval_seconds=config.poll_interval_seconds,
                events=["new-comments", "status-change", "vote-change", "push-update"],
                actions=self.default_pr_actions.copy(),
            )
            subscriptions.append(sub)

        logger.info(
            f"Discovered {len(subscriptions)} PRs in {config.org}/{config.project}/{config.repo}"
        )
        return subscriptions

    async def _query_my_prs(
        self, client: ADOClient, config: PRDiscoveryConfig
    ) -> list[dict[str, Any]]:
        """Query PRs where user is reviewer or creator."""
        import asyncio
        import subprocess

        # Get current user ID via az cli
        result = await asyncio.to_thread(
            subprocess.run,
            ["az", "account", "show", "--query", "user.name", "-o", "tsv"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error(f"Failed to get current user: {result.stderr}")
            return []

        current_user = result.stdout.strip()

        # Query PRs via REST API
        # GET /{project}/_apis/git/repositories/{repo}/pullrequests?searchCriteria.status=active
        headers = await client._ensure_auth()
        url = f"/{config.project}/_apis/git/repositories/{config.repo}/pullrequests"
        params = {
            "api-version": "7.1",
            "searchCriteria.status": "active",
        }

        if config.filter == "created_by_me":
            params["searchCriteria.creatorId"] = current_user
        # For assigned_to_me, we'll filter client-side (reviewer check)

        response = await client._client.get(url, params=params, headers=headers)
        response.raise_for_status()
        prs = response.json().get("value", [])

        if config.filter == "assigned_to_me":
            # Filter to PRs where user is a reviewer
            prs = [
                pr
                for pr in prs
                if any(
                    r.get("uniqueName", "").lower() == current_user.lower()
                    or r.get("displayName", "").lower() == current_user.lower()
                    for r in pr.get("reviewers", [])
                )
            ]

        return prs

    async def _discover_work_items(self, config: WorkItemDiscoveryConfig) -> list[Subscription]:
        """Discover work items assigned to the user."""
        client = self._get_client(config.org)
        work_items = await self._query_my_work_items(client, config)

        subscriptions = []
        for wi in work_items:
            wi_id = wi.get("id")
            if wi_id is None:
                continue

            sub = Subscription(
                id=f"discovery:wi-{config.org}-{config.project}-{wi_id}",
                type=SubscriptionType.WORK_ITEM,
                org=config.org,
                project=config.project,
                work_item_id=wi_id,
                poll_interval_seconds=config.poll_interval_seconds,
                events=["comment-added", "state-change", "field-update"],
                actions=self.default_wi_actions.copy(),
            )
            subscriptions.append(sub)

        logger.info(f"Discovered {len(subscriptions)} work items in {config.org}/{config.project}")
        return subscriptions

    async def _query_my_work_items(
        self, client: ADOClient, config: WorkItemDiscoveryConfig
    ) -> list[dict[str, Any]]:
        """Query work items assigned to the user via WIQL."""
        # Build WIQL query
        wiql = """
        SELECT [System.Id]
        FROM WorkItems
        WHERE [System.AssignedTo] = @Me
          AND [System.State] NOT IN ('Closed', 'Resolved', 'Done', 'Removed')
        """

        if config.area_path:
            wiql += f"\n  AND [System.AreaPath] UNDER '{config.area_path}'"

        wiql += "\nORDER BY [System.ChangedDate] DESC"

        # Execute WIQL query
        headers = await client._ensure_auth()
        url = f"/{config.project}/_apis/wit/wiql"
        payload = {"query": wiql}

        response = await client._client.post(
            url,
            params={"api-version": "7.1"},
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        result = response.json()

        # WIQL returns just IDs, convert to list of dicts
        work_items = [{"id": wi["id"]} for wi in result.get("workItems", [])]
        return work_items

    async def close(self) -> None:
        """Close all HTTP clients."""
        for client in self._clients.values():
            await client.close()
