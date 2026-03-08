"""Tests for the State Store component."""

import tempfile
from pathlib import Path

from ado_monitor.models import Event, EventType, Snapshot
from ado_monitor.state import StateStore


class TestSnapshotPersistence:
    """Tests for snapshot storage."""

    def test_save_and_retrieve_snapshot(self) -> None:
        """Saved snapshots should be retrievable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / "test.db")

            snapshot = Snapshot(
                subscription_id="pr-123",
                data={"threads": [{"id": 1}], "status": "active"},
            )

            store.save_snapshot(snapshot)
            retrieved = store.get_snapshot("pr-123")

            assert retrieved is not None
            assert retrieved.subscription_id == "pr-123"
            assert retrieved.data == {"threads": [{"id": 1}], "status": "active"}

    def test_get_nonexistent_snapshot_returns_none(self) -> None:
        """Getting a snapshot that doesn't exist should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / "test.db")

            result = store.get_snapshot("nonexistent")

            assert result is None

    def test_save_replaces_existing_snapshot(self) -> None:
        """Saving a snapshot should replace any existing one for that subscription."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / "test.db")

            snapshot1 = Snapshot(subscription_id="pr-123", data={"version": 1})
            snapshot2 = Snapshot(subscription_id="pr-123", data={"version": 2})

            store.save_snapshot(snapshot1)
            store.save_snapshot(snapshot2)

            retrieved = store.get_snapshot("pr-123")

            assert retrieved is not None
            assert retrieved.data == {"version": 2}


class TestEventRecording:
    """Tests for event persistence and deduplication."""

    def test_record_new_event(self) -> None:
        """New events should be recorded and return an ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / "test.db")

            event = Event(
                event_type=EventType.PR_COMMENT_NEW,
                subscription_id="pr-123",
                payload={"thread_id": 1},
                author="Alice",
            )

            event_id = store.record_event(event)

            assert event_id is not None
            assert event_id > 0

    def test_duplicate_event_returns_none(self) -> None:
        """Recording a duplicate event should return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / "test.db")

            event = Event(
                event_type=EventType.PR_COMMENT_NEW,
                subscription_id="pr-123",
                payload={"thread_id": 1},
            )

            first_id = store.record_event(event)
            second_id = store.record_event(event)

            assert first_id is not None
            assert second_id is None

    def test_get_pending_events(self) -> None:
        """Should retrieve all pending events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / "test.db")

            event1 = Event(
                event_type=EventType.PR_COMMENT_NEW,
                subscription_id="pr-123",
                payload={"thread_id": 1},
            )
            event2 = Event(
                event_type=EventType.PR_PUSH,
                subscription_id="pr-123",
                payload={"iteration": 2},
            )

            store.record_event(event1)
            store.record_event(event2)

            pending = store.get_pending_events()

            assert len(pending) == 2

    def test_get_pending_events_filtered_by_subscription(self) -> None:
        """Should filter pending events by subscription."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / "test.db")

            event1 = Event(
                event_type=EventType.PR_COMMENT_NEW,
                subscription_id="pr-123",
                payload={"thread_id": 1},
            )
            event2 = Event(
                event_type=EventType.PR_COMMENT_NEW,
                subscription_id="pr-456",
                payload={"thread_id": 2},
            )

            store.record_event(event1)
            store.record_event(event2)

            pending = store.get_pending_events("pr-123")

            assert len(pending) == 1
            assert pending[0].subscription_id == "pr-123"


class TestEventProcessing:
    """Tests for event processing workflow."""

    def test_mark_event_processed(self) -> None:
        """Marking an event processed should remove it from pending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / "test.db")

            event = Event(
                event_type=EventType.PR_COMMENT_NEW,
                subscription_id="pr-123",
                payload={"thread_id": 1},
            )

            event_id = store.record_event(event)
            assert event_id is not None

            store.mark_event_processed(event_id, status="done")

            pending = store.get_pending_events()
            assert len(pending) == 0

    def test_event_history(self) -> None:
        """Should retrieve processed event history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / "test.db")

            event = Event(
                event_type=EventType.PR_COMMENT_NEW,
                subscription_id="pr-123",
                payload={"thread_id": 1},
            )

            event_id = store.record_event(event)
            assert event_id is not None
            store.mark_event_processed(event_id, status="done")

            history = store.get_event_history("pr-123")

            assert len(history) == 1
            assert history[0]["status"] == "done"
