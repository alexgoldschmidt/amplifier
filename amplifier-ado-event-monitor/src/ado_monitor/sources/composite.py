"""Composite subscription source.

Merges subscriptions from multiple sources into a single stream.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Subscription
    from . import SubscriptionSource

logger = logging.getLogger(__name__)


class CompositeSubscriptionSource:
    """Merges subscriptions from multiple sources.

    Queries each child source and combines their subscriptions into a single
    list. If a source fails, it logs the error and continues with other sources.
    """

    source_id: str = "composite"

    def __init__(self, sources: list[SubscriptionSource]) -> None:
        """Initialize with a list of subscription sources.

        Args:
            sources: List of SubscriptionSource implementations to query.
        """
        self.sources = sources

    async def get_subscriptions(self) -> list[Subscription]:
        """Return combined subscriptions from all sources.

        Queries each source and merges results. Failed sources are logged
        but don't prevent other sources from being queried.

        Returns:
            Combined list of subscriptions from all sources.
        """
        results: list[Subscription] = []

        for source in self.sources:
            try:
                subs = await source.get_subscriptions()
                results.extend(subs)
            except Exception:
                logger.exception(f"Source {source.source_id} failed")

        return results
