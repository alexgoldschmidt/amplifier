"""Domain models for ADO Event Monitor."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Event types produced by the Differ."""

    # PR events
    PR_COMMENT_NEW = "pr.comment.new"
    PR_COMMENT_RESOLVED = "pr.comment.resolved"
    PR_VOTE_CHANGED = "pr.vote.changed"
    PR_STATUS_CHANGED = "pr.status.changed"
    PR_PUSH = "pr.push"
    PR_POLICY_CHANGED = "pr.policy.changed"

    # Work item events
    WI_STATE_CHANGED = "wi.state.changed"
    WI_FIELD_UPDATED = "wi.field.updated"
    WI_COMMENT_ADDED = "wi.comment.added"


class SubscriptionType(Enum):
    """Types of ADO entities that can be subscribed to."""

    PULL_REQUEST = "pull-request"
    WORK_ITEM = "work-item"


@dataclass
class Event:
    """An event detected by the Differ."""

    event_type: EventType
    subscription_id: str
    payload: dict[str, Any]
    author: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Snapshot:
    """A point-in-time snapshot of an ADO entity's state."""

    subscription_id: str
    data: dict[str, Any]
    polled_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Action:
    """An action to take when an event is detected."""

    agent: str
    trigger: str
    behavior: str | None = None
    recipe: str | None = None


@dataclass
class Subscription:
    """A subscription to an ADO entity."""

    id: str
    type: SubscriptionType
    org: str
    project: str
    poll_interval_seconds: int
    events: list[str]
    actions: list[Action]
    # PR-specific
    repo: str | None = None
    pr_id: int | None = None
    # Work item-specific
    work_item_id: int | None = None
