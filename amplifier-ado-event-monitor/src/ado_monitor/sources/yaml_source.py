"""YAML-based subscription source.

Wraps static subscriptions from subscriptions.yaml for use with the
SubscriptionSource protocol.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Subscription

logger = logging.getLogger(__name__)


class YamlSubscriptionSource:
    """Wraps static subscriptions from subscriptions.yaml.

    This source returns the same subscriptions on every call - it's purely
    for compatibility with the SubscriptionSource protocol so static and
    dynamic sources can be composed together.
    """

    source_id: str = "yaml"

    def __init__(self, subscriptions: list[Subscription]) -> None:
        """Initialize with a list of subscriptions.

        Args:
            subscriptions: Static subscriptions parsed from YAML config.
        """
        self._subscriptions = subscriptions

    async def get_subscriptions(self) -> list[Subscription]:
        """Return the static subscriptions.

        Always returns the same list - no dynamic behavior.
        """
        return self._subscriptions
