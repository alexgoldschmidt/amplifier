# Feature Spec: Webhook Accelerator Endpoint

## Overview

An optional HTTP endpoint that receives ADO Service Hook webhooks and triggers immediate polls, reducing latency from poll interval (60s) to near-real-time (~seconds) without depending on webhooks for correctness.

## Acceptance Criteria

1. **Optional component**: Monitor works without webhook receiver; webhooks only accelerate
2. **Thin endpoint**: POST `/webhook/ado` receives webhook, triggers poll, returns 200
3. **Subscription matching**: Webhook payload matched to subscription via org/project/repo/id
4. **Immediate poll**: Matching subscription's next poll happens immediately (skip wait)
5. **Idempotent**: Multiple webhooks for same event don't cause multiple polls
6. **No auth dependency**: Webhook receiver doesn't authenticate requests (ADO signs them)
7. **Signature validation**: Optionally validate ADO's HMAC signature if secret configured

## Interface

```python
# New module: src/ado_monitor/webhook.py

class WebhookReceiver:
    def __init__(
        self,
        monitor: Monitor,
        secret: str | None = None,
    ) -> None:
        """Initialize webhook receiver.
        
        Args:
            monitor: The running monitor instance
            secret: Optional HMAC secret for signature validation
        """

    async def handle_webhook(self, request: Request) -> Response:
        """Handle incoming ADO Service Hook webhook."""

    def start(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """Start the webhook HTTP server."""
```

## Webhook Payload Matching

ADO Service Hooks send JSON with structure:
```json
{
  "publisherId": "tfs",
  "eventType": "git.pullrequest.updated",
  "resource": {
    "repository": {"name": "myrepo", "project": {"name": "myproject"}},
    "pullRequestId": 123
  },
  "resourceContainers": {
    "account": {"baseUrl": "https://dev.azure.com/myorg/"}
  }
}
```

Match to subscription via: `org + project + repo + pr_id` or `org + project + work_item_id`

## CLI Extension

```bash
# Start monitor with webhook receiver
ado-monitor --config subscriptions.yaml --webhook-port 8080

# Optional: Specify webhook secret for HMAC validation
ado-monitor --config subscriptions.yaml --webhook-port 8080 --webhook-secret $SECRET
```

## Files to Create/Modify

| File | Change |
|------|--------|
| `src/ado_monitor/webhook.py` | **NEW** - HTTP endpoint with FastAPI/Starlette |
| `src/ado_monitor/monitor.py` | Add `trigger_immediate_poll(subscription_id)` method |
| `src/ado_monitor/cli.py` | Add `--webhook-port` and `--webhook-secret` flags |
| `pyproject.toml` | Add optional `starlette` and `uvicorn` dependencies |
| `tests/test_webhook.py` | **NEW** - Webhook handling tests |

## Test Cases

1. `test_webhook_triggers_immediate_poll` - Valid webhook causes poll
2. `test_webhook_matches_pr_subscription` - PR webhook finds correct subscription
3. `test_webhook_matches_wi_subscription` - Work item webhook finds correct subscription
4. `test_unmatched_webhook_ignored` - Unknown entity doesn't crash
5. `test_invalid_signature_rejected` - Bad HMAC returns 401 (if secret configured)
6. `test_missing_signature_allowed` - No signature OK if no secret configured
7. `test_duplicate_webhooks_deduplicated` - Rapid-fire webhooks don't cause multiple polls

## ADO Service Hook Setup

Users configure Service Hooks in ADO:
1. Project Settings → Service Hooks → Create subscription
2. Select "Web Hooks" service
3. Configure trigger (PR updated, WI changed, etc.)
4. Set URL to `http://<monitor-host>:8080/webhook/ado`
5. Optionally set HMAC secret

## Edge Cases

- Webhook arrives before poll loop starts: Queue for processing after startup
- Webhook for non-existent subscription: Log and ignore
- Monitor restarting during webhook: Return 503, ADO will retry

## Dependencies

- `starlette` (or `fastapi`) - async HTTP framework
- `uvicorn` - ASGI server

These are optional dependencies (`pip install ado-event-monitor[webhook]`).

## Estimated Complexity

Medium - new component, but well-isolated from core logic.
