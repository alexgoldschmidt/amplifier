"""Monitor - Main event loop for the ADO Event Monitor.

Coordinates the Poller, Differ, State Store, and Dispatcher into a
running service that watches Azure DevOps and triggers Amplifier agents.
"""

import asyncio
import logging
import signal
from pathlib import Path

from .config import Config
from .differ import IGNORE_AUTHORS, diff_snapshots
from .dispatcher import Dispatcher
from .models import Subscription
from .poller import ADOClient, Poller
from .sources import (
    CompositeSubscriptionSource,
    DiscoverySubscriptionSource,
    YamlSubscriptionSource,
)
from .state import StateStore

logger = logging.getLogger(__name__)


class Monitor:
    """Main event monitor service."""

    def __init__(
        self,
        config: Config,
        state_store: StateStore,
    ) -> None:
        """Initialize the monitor.

        Args:
            config: Parsed configuration
            state_store: State persistence
        """
        self.config = config
        self.state_store = state_store

        # Build subscription lookup
        self.subscriptions = {s.id: s for s in config.subscriptions}

        # Initialize dispatcher with state store for logging
        self.dispatcher = Dispatcher(self.subscriptions, state_store=state_store)

        # ADO clients per org (lazily created)
        self._clients: dict[str, ADOClient] = {}
        self._pollers: dict[str, Poller] = {}

        # Immediate poll requests from webhooks
        self._immediate_poll_queue: asyncio.Queue[str] = asyncio.Queue()

        # Shutdown flag
        self._shutdown = asyncio.Event()

        # Update IGNORE_AUTHORS from config
        IGNORE_AUTHORS.update(config.ignore_authors)

    def _get_poller(self, subscription: Subscription) -> Poller:
        """Get or create a poller for the subscription's org."""
        org = subscription.org
        if org not in self._pollers:
            client = ADOClient(org)
            self._clients[org] = client
            self._pollers[org] = Poller(client)
        return self._pollers[org]

    async def trigger_immediate_poll(self, subscription_id: str) -> None:
        """Trigger an immediate poll for a subscription (called by webhook).

        Args:
            subscription_id: ID of the subscription to poll immediately
        """
        if subscription_id in self.subscriptions:
            await self._immediate_poll_queue.put(subscription_id)

    async def start(self) -> None:
        """Start the monitor service."""
        logger.info(f"Starting ADO Event Monitor with {len(self.subscriptions)} subscriptions")

        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: self._shutdown.set())

        try:
            # Start a poll loop for each subscription
            tasks = [asyncio.create_task(self._poll_loop(sub)) for sub in self.config.subscriptions]

            # Wait for shutdown signal
            await self._shutdown.wait()
            logger.info("Shutdown signal received, stopping...")

            # Cancel all poll loops
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        finally:
            await self._cleanup()

    async def _cleanup(self) -> None:
        """Clean up resources."""
        for client in self._clients.values():
            await client.close()
        logger.info("Monitor stopped")

    async def _poll_loop(self, subscription: Subscription) -> None:
        """Polling loop for a single subscription."""
        interval = subscription.poll_interval_seconds
        logger.info(f"Starting poll loop for {subscription.id} (every {interval}s)")

        poller = self._get_poller(subscription)

        while not self._shutdown.is_set():
            try:
                await self._poll_once(subscription, poller)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(f"Error polling {subscription.id}")

            # Wait for next poll interval or shutdown
            try:
                await asyncio.wait_for(
                    self._shutdown.wait(),
                    timeout=subscription.poll_interval_seconds,
                )
                break  # Shutdown requested
            except TimeoutError:
                pass  # Normal timeout, continue polling

    async def _poll_once(self, subscription: Subscription, poller: Poller) -> None:
        """Execute a single poll cycle for a subscription."""
        logger.debug(f"Polling {subscription.id}")

        # Get current state from ADO
        current_snapshot = await poller.poll(subscription)

        # Get previous state from store
        previous_snapshot = self.state_store.get_snapshot(subscription.id)

        # Diff to find events
        events = diff_snapshots(previous_snapshot, current_snapshot)

        # Save current state
        self.state_store.save_snapshot(current_snapshot)

        if not events:
            logger.debug(f"No events detected for {subscription.id}")
            return

        logger.info(f"Detected {len(events)} events for {subscription.id}")

        # Record and dispatch events
        for event in events:
            # Record event (deduplicates automatically)
            event_id = self.state_store.record_event(event)
            if event_id is None:
                logger.debug(f"Skipping duplicate event: {event.event_type.value}")
                continue

            # Dispatch to agent
            try:
                result = await self.dispatcher.dispatch(event)
                if result:
                    status = "done" if result.success else "failed"
                    self.state_store.mark_event_processed(event_id, status=status)
                    if result.success:
                        logger.info(f"Successfully dispatched to {result.agent}")
                    else:
                        logger.error(f"Dispatch failed: {result.error}")
                else:
                    # No matching action
                    self.state_store.mark_event_processed(event_id, status="skipped")
            except Exception:
                logger.exception(f"Failed to dispatch event {event_id}")
                self.state_store.mark_event_processed(event_id, status="failed")


async def run_monitor(
    config_path: Path,
    db_path: Path | None = None,
) -> None:
    """Run the monitor with the given configuration.

    Authentication is via Azure CLI (`az login`). Ensure you're logged in before running.

    Args:
        config_path: Path to subscriptions.yaml
        db_path: Path to SQLite database (default: ado_monitor.db)
    """
    config = Config.from_file(config_path)
    state_store = StateStore(db_path or "ado_monitor.db")

    # Build subscription sources
    sources = []

    # Static subscriptions from YAML
    if config.subscriptions:
        sources.append(YamlSubscriptionSource(config.subscriptions))

    # Discovery source for dynamic PR/WI discovery
    if config.pr_discovery or config.wi_discovery:
        discovery_source = DiscoverySubscriptionSource(
            pr_configs=config.pr_discovery,
            wi_configs=config.wi_discovery,
        )
        sources.append(discovery_source)

    # Run initial discovery to populate subscriptions
    if sources:
        composite = CompositeSubscriptionSource(sources)
        discovered_subs = await composite.get_subscriptions()
        logger.info(f"Discovered {len(discovered_subs)} total subscriptions")

        # Merge discovered subscriptions into config
        # (static ones are already in config.subscriptions)
        for sub in discovered_subs:
            if sub.id not in {s.id for s in config.subscriptions}:
                config.subscriptions.append(sub)

    monitor = Monitor(config, state_store)
    await monitor.start()
