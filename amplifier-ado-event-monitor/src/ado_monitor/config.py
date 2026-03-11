"""Configuration parsing for subscriptions.yaml.

Parses the subscription configuration file that defines what ADO entities
to watch and what actions to take when events are detected.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .models import Action, Subscription, SubscriptionType
from .sources import PRDiscoveryConfig, WorkItemDiscoveryConfig


@dataclass
class Config:
    """Parsed configuration for the event monitor."""

    subscriptions: list[Subscription]
    ignore_authors: set[str]
    pr_discovery: list[PRDiscoveryConfig] = field(default_factory=list)
    wi_discovery: list[WorkItemDiscoveryConfig] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path | str) -> "Config":
        """Load configuration from a YAML file.

        Args:
            path: Path to the subscriptions.yaml file

        Returns:
            Parsed Config object
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Parse configuration from a dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Parsed Config object
        """
        subscriptions = []
        for sub_data in data.get("subscriptions", []):
            subscriptions.append(_parse_subscription(sub_data))

        ignore_authors = set(data.get("ignore_authors", ["Amplifier Bot", "amplifier[bot]"]))

        # Parse discovery section
        pr_discovery = []
        wi_discovery = []
        discovery = data.get("discovery", {})

        for pr_cfg in discovery.get("pull_requests", []):
            pr_discovery.append(
                PRDiscoveryConfig(
                    org=pr_cfg["org"],
                    project=pr_cfg["project"],
                    repo=pr_cfg["repo"],
                    filter=pr_cfg.get("filter", "assigned_to_me"),
                    poll_interval_seconds=_parse_duration(pr_cfg.get("poll_interval", "60s")),
                )
            )

        for wi_cfg in discovery.get("work_items", []):
            wi_discovery.append(
                WorkItemDiscoveryConfig(
                    org=wi_cfg["org"],
                    project=wi_cfg["project"],
                    filter=wi_cfg.get("filter", "assigned_to_me"),
                    area_path=wi_cfg.get("area_path"),
                    poll_interval_seconds=_parse_duration(wi_cfg.get("poll_interval", "120s")),
                )
            )

        return cls(
            subscriptions=subscriptions,
            ignore_authors=ignore_authors,
            pr_discovery=pr_discovery,
            wi_discovery=wi_discovery,
        )


def _parse_subscription(data: dict[str, Any]) -> Subscription:
    """Parse a single subscription from config data."""
    sub_type = SubscriptionType(data["type"])

    actions = []
    for action_data in data.get("actions", []):
        actions.append(
            Action(
                agent=action_data["agent"],
                trigger=action_data["trigger"],
                behavior=action_data.get("behavior"),
                recipe=action_data.get("recipe"),
            )
        )

    # Parse poll interval (e.g., "60s" -> 60)
    poll_interval = _parse_duration(data.get("poll_interval", "60s"))

    return Subscription(
        id=data["id"],
        type=sub_type,
        org=data["org"],
        project=data["project"],
        poll_interval_seconds=poll_interval,
        events=data.get("events", []),
        actions=actions,
        repo=data.get("repo"),
        pr_id=data.get("pr_id"),
        work_item_id=data.get("work_item_id"),
    )


def _parse_duration(duration: str) -> int:
    """Parse a duration string like '60s' or '2m' into seconds."""
    if duration.endswith("s"):
        return int(duration[:-1])
    if duration.endswith("m"):
        return int(duration[:-1]) * 60
    if duration.endswith("h"):
        return int(duration[:-1]) * 3600
    # Assume seconds if no suffix
    return int(duration)
