"""Subscription sources for the ADO Event Monitor.

This module provides the SubscriptionSource protocol and implementations
for dynamic subscription discovery.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..models import Subscription

logger = logging.getLogger(__name__)


@runtime_checkable
class SubscriptionSource(Protocol):
    """Protocol for subscription providers.

    Sources provide subscriptions to the monitor. They are called periodically
    by the reconciliation loop to discover new subscriptions or detect removed ones.

    Design decisions:
    - Protocol, not ABC: Structural typing for loose coupling
    - runtime_checkable: Enables isinstance() checks for validation
    - source_id property: Prefixed to subscription IDs to avoid collisions
    - No-throw contract: get_subscriptions() must catch its own exceptions
    """

    @property
    def source_id(self) -> str:
        """Unique identifier for this source.

        Used in subscription ID prefixing to avoid collisions between sources
        (e.g., 'foreman:wi-101' vs 'yaml:wi-456').
        """
        ...

    async def get_subscriptions(self) -> list[Subscription]:
        """Return the current set of subscriptions.

        Called periodically by the reconciliation loop.
        Must be safe to call concurrently.
        Must not raise — return empty list on error and log.
        """
        ...


# Re-export implementations for convenience
from .composite import CompositeSubscriptionSource
from .discovery import DiscoverySubscriptionSource, PRDiscoveryConfig, WorkItemDiscoveryConfig
from .foreman import ForemanSubscriptionSource
from .yaml_source import YamlSubscriptionSource

__all__ = [
    "SubscriptionSource",
    "YamlSubscriptionSource",
    "ForemanSubscriptionSource",
    "CompositeSubscriptionSource",
    "DiscoverySubscriptionSource",
    "PRDiscoveryConfig",
    "WorkItemDiscoveryConfig",
]
