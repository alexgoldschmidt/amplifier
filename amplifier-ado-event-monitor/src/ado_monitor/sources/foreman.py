"""Docker Foreman subscription source.

Generates subscriptions from the Docker Foreman worker registry by reading
worker JSON files from the filesystem.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..models import Action, Subscription, SubscriptionType

logger = logging.getLogger(__name__)


class ForemanSubscriptionSource:
    """Generates subscriptions from Docker Foreman worker registry.

    Reads worker JSON files from ~/.amplifier/projects/{project}/docker-foreman/workers/
    and generates work item subscriptions for each active worker.
    """

    source_id: str = "foreman"

    def __init__(
        self,
        project: str,
        org: str,
        ado_project: str,
        poll_interval_seconds: int = 60,
        base_path: Path | None = None,
    ) -> None:
        """Initialize the foreman subscription source.

        Args:
            project: Amplifier project name (used for path lookup).
            org: ADO organization name.
            ado_project: ADO project name.
            poll_interval_seconds: How often to poll each worker's WI (default 60s).
            base_path: Override path to docker-foreman directory.
        """
        self.project = project
        self.org = org
        self.ado_project = ado_project
        self.poll_interval_seconds = poll_interval_seconds
        self.base_path = (
            base_path or Path.home() / ".amplifier" / "projects" / project / "docker-foreman"
        )

    async def get_subscriptions(self) -> list[Subscription]:
        """Read worker JSONs and generate subscriptions.

        Returns:
            List of subscriptions for active workers. Empty list if no workers
            or on error (errors are logged, not raised).
        """
        subscriptions: list[Subscription] = []
        workers_dir = self.base_path / "workers"

        if not workers_dir.exists():
            logger.info(f"Workers directory does not exist: {workers_dir}")
            return subscriptions

        try:
            for worker_file in workers_dir.glob("*.json"):
                sub = self._parse_worker_file(worker_file)
                if sub is not None:
                    subscriptions.append(sub)
        except PermissionError:
            logger.exception(f"Permission denied reading workers directory: {workers_dir}")
            return []
        except OSError:
            logger.exception(f"Error reading workers directory: {workers_dir}")
            return []

        return subscriptions

    def _parse_worker_file(self, worker_file: Path) -> Subscription | None:
        """Parse a single worker JSON file into a Subscription.

        Args:
            worker_file: Path to the worker JSON file.

        Returns:
            Subscription for the worker, or None if file is invalid/skipped.
        """
        try:
            content = worker_file.read_text()
            worker: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Skipping malformed JSON: {worker_file.name}")
            return None
        except OSError:
            logger.warning(f"Error reading worker file: {worker_file.name}")
            return None

        # Validate required fields
        work_item_id = worker.get("work_item_id")
        if work_item_id is None:
            logger.warning(f"Skipping worker missing work_item_id: {worker_file.name}")
            return None

        # Skip closed or destroyed workers
        state = worker.get("state", "active")
        if state in ("closed", "destroyed"):
            logger.debug(f"Skipping {state} worker: {worker_file.name}")
            return None

        # Build subscription
        # Note: foreman-specific metadata (container_id, session_id, branch, worker_name)
        # is available in the worker JSON file. The dispatcher can re-read it when needed
        # using the work_item_id to locate the file.
        return Subscription(
            id=f"foreman:wi-{work_item_id}",
            type=SubscriptionType.WORK_ITEM,
            org=self.org,
            project=self.ado_project,
            poll_interval_seconds=self.poll_interval_seconds,
            events=["comment-added", "state-change"],
            actions=[
                Action(
                    agent="docker-worker",
                    trigger="comment-added",
                    behavior="resume-from-response",
                ),
                Action(
                    agent="docker-worker",
                    trigger="state-change",
                    behavior="handle-state-change",
                ),
            ],
            work_item_id=work_item_id,
            # Store foreman-specific metadata in a way the dispatcher can access
            # This is a slight extension - we'll add foreman_context to Subscription
            # For now, the dispatcher will need to re-read the worker JSON
        )
