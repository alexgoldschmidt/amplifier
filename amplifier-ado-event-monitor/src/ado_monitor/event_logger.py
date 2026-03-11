"""Event Logger - Structured event logging to file.

Logs all detected events to a JSONL file for observability and debugging.
Each line is a self-contained JSON record with full event details.
"""

import json
import logging
from datetime import datetime, timezone

UTC = timezone.utc
from pathlib import Path
from typing import Any

from .models import Event, Subscription

logger = logging.getLogger(__name__)


class EventLogger:
    """Logs events to a JSONL file for observability."""

    def __init__(self, log_path: Path | str = "events.jsonl") -> None:
        """Initialize the event logger.

        Args:
            log_path: Path to the JSONL log file
        """
        self.log_path = Path(log_path)
        # Ensure parent directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event: Event,
        subscription: Subscription,
        dispatch_result: dict[str, Any] | None = None,
    ) -> None:
        """Log an event with full context.

        Args:
            event: The detected event
            subscription: The subscription that triggered this event
            dispatch_result: Optional result from dispatcher
        """
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event.event_type.value,
            "subscription_id": event.subscription_id,
            "author": event.author,
            "event_created_at": event.created_at.isoformat(),
            # Subscription context
            "subscription": {
                "type": subscription.type.value,
                "org": subscription.org,
                "project": subscription.project,
                "repo": subscription.repo,
                "pr_id": subscription.pr_id,
                "work_item_id": subscription.work_item_id,
            },
            # Event payload (the actual change data)
            "payload": event.payload,
            # Dispatch result if available
            "dispatch": dispatch_result,
        }

        self._write_record(record)

    def log_discovery(
        self,
        source: str,
        subscription_count: int,
        subscriptions: list[Subscription],
    ) -> None:
        """Log a discovery event.

        Args:
            source: Source identifier (e.g., 'discovery', 'yaml')
            subscription_count: Number of subscriptions discovered
            subscriptions: The discovered subscriptions
        """
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": "discovery.complete",
            "source": source,
            "subscription_count": subscription_count,
            "subscriptions": [
                {
                    "id": s.id,
                    "type": s.type.value,
                    "org": s.org,
                    "project": s.project,
                    "repo": s.repo,
                    "pr_id": s.pr_id,
                    "work_item_id": s.work_item_id,
                }
                for s in subscriptions
            ],
        }

        self._write_record(record)

    def log_poll(
        self,
        subscription_id: str,
        events_detected: int,
        error: str | None = None,
    ) -> None:
        """Log a poll cycle.

        Args:
            subscription_id: The subscription polled
            events_detected: Number of events detected
            error: Optional error message if poll failed
        """
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": "poll.complete" if not error else "poll.error",
            "subscription_id": subscription_id,
            "events_detected": events_detected,
            "error": error,
        }

        self._write_record(record)

    def log_dispatch(
        self,
        event: Event,
        agent: str,
        success: bool,
        session_id: str | None = None,
        error: str | None = None,
        output: str | None = None,
    ) -> None:
        """Log a dispatch action.

        Args:
            event: The event being dispatched
            agent: The agent invoked
            success: Whether dispatch succeeded
            session_id: Optional Amplifier session ID
            error: Optional error message
            output: Optional output from agent
        """
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": "dispatch.complete" if success else "dispatch.failed",
            "subscription_id": event.subscription_id,
            "original_event_type": event.event_type.value,
            "agent": agent,
            "success": success,
            "session_id": session_id,
            "error": error,
            "output_preview": output[:500] if output else None,
        }

        self._write_record(record)

    def _write_record(self, record: dict[str, Any]) -> None:
        """Write a record to the log file.

        Args:
            record: The record to write
        """
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except OSError:
            logger.exception(f"Failed to write to event log: {self.log_path}")
