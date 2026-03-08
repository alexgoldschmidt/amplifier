"""Tests for the Differ component."""

from ado_monitor.differ import diff_snapshots
from ado_monitor.models import EventType, Snapshot


class TestDiffPrThreads:
    """Tests for PR thread diffing."""

    def test_no_events_on_first_poll(self) -> None:
        """First poll should produce no events (no baseline to compare)."""
        current = Snapshot(
            subscription_id="pr-123",
            data={"threads": [{"id": 1, "comments": [{"content": "test"}]}]},
        )

        events = diff_snapshots(None, current)

        assert events == []

    def test_new_thread_detected(self) -> None:
        """New thread should produce PR_COMMENT_NEW event."""
        previous = Snapshot(
            subscription_id="pr-123",
            data={"threads": []},
        )
        current = Snapshot(
            subscription_id="pr-123",
            data={
                "threads": [
                    {
                        "id": 1,
                        "comments": [
                            {"author": {"displayName": "Alice"}, "content": "Review comment"}
                        ],
                    }
                ]
            },
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 1
        assert events[0].event_type == EventType.PR_COMMENT_NEW
        assert events[0].author == "Alice"

    def test_new_reply_in_existing_thread(self) -> None:
        """New reply in existing thread should produce PR_COMMENT_NEW event."""
        previous = Snapshot(
            subscription_id="pr-123",
            data={
                "threads": [
                    {
                        "id": 1,
                        "comments": [{"author": {"displayName": "Alice"}, "content": "First"}],
                    }
                ]
            },
        )
        current = Snapshot(
            subscription_id="pr-123",
            data={
                "threads": [
                    {
                        "id": 1,
                        "comments": [
                            {"author": {"displayName": "Alice"}, "content": "First"},
                            {"author": {"displayName": "Bob"}, "content": "Reply"},
                        ],
                    }
                ]
            },
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 1
        assert events[0].event_type == EventType.PR_COMMENT_NEW
        assert events[0].author == "Bob"

    def test_thread_resolved(self) -> None:
        """Thread status change to resolved should produce PR_COMMENT_RESOLVED event."""
        previous = Snapshot(
            subscription_id="pr-123",
            data={"threads": [{"id": 1, "status": "active", "comments": []}]},
        )
        current = Snapshot(
            subscription_id="pr-123",
            data={"threads": [{"id": 1, "status": "fixed", "comments": []}]},
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 1
        assert events[0].event_type == EventType.PR_COMMENT_RESOLVED

    def test_ignored_author_filtered(self) -> None:
        """Events from ignored authors should be filtered out."""
        previous = Snapshot(subscription_id="pr-123", data={"threads": []})
        current = Snapshot(
            subscription_id="pr-123",
            data={
                "threads": [
                    {
                        "id": 1,
                        "comments": [
                            {"author": {"displayName": "Amplifier Bot"}, "content": "Auto-reply"}
                        ],
                    }
                ]
            },
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 0


class TestDiffPrIterations:
    """Tests for PR iteration (push) diffing."""

    def test_new_push_detected(self) -> None:
        """New iteration should produce PR_PUSH event."""
        previous = Snapshot(
            subscription_id="pr-123",
            data={"iterations": [{"id": 1}]},
        )
        current = Snapshot(
            subscription_id="pr-123",
            data={"iterations": [{"id": 1}, {"id": 2, "author": {"displayName": "Dev"}}]},
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 1
        assert events[0].event_type == EventType.PR_PUSH
        assert events[0].author == "Dev"


class TestDiffPrStatus:
    """Tests for PR status diffing."""

    def test_status_change_detected(self) -> None:
        """PR status change should produce PR_STATUS_CHANGED event."""
        previous = Snapshot(
            subscription_id="pr-123",
            data={"status": "active", "pr_id": 123},
        )
        current = Snapshot(
            subscription_id="pr-123",
            data={"status": "completed", "pr_id": 123},
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 1
        assert events[0].event_type == EventType.PR_STATUS_CHANGED
        assert events[0].payload["previous_status"] == "active"
        assert events[0].payload["current_status"] == "completed"


class TestDiffPrVotes:
    """Tests for PR vote diffing."""

    def test_new_vote_detected(self) -> None:
        """New reviewer vote should produce PR_VOTE_CHANGED event."""
        previous = Snapshot(
            subscription_id="pr-123",
            data={"votes": {}},
        )
        current = Snapshot(
            subscription_id="pr-123",
            data={"votes": {"alice@example.com": 10}},  # 10 = approved
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 1
        assert events[0].event_type == EventType.PR_VOTE_CHANGED
        assert events[0].payload["current_vote"] == 10

    def test_vote_change_detected(self) -> None:
        """Changed vote should produce PR_VOTE_CHANGED event."""
        previous = Snapshot(
            subscription_id="pr-123",
            data={"votes": {"alice@example.com": 0}},  # 0 = no vote
        )
        current = Snapshot(
            subscription_id="pr-123",
            data={"votes": {"alice@example.com": -10}},  # -10 = rejected
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 1
        assert events[0].event_type == EventType.PR_VOTE_CHANGED
        assert events[0].payload["previous_vote"] == 0
        assert events[0].payload["current_vote"] == -10


class TestDiffWorkItem:
    """Tests for work item diffing."""

    def test_state_change_detected(self) -> None:
        """Work item state change should produce WI_STATE_CHANGED event."""
        previous = Snapshot(
            subscription_id="wi-456",
            data={
                "work_item_id": 456,
                "latest_revision": {
                    "rev": 1,
                    "fields": {"System.State": "New", "System.ChangedBy": "Alice"},
                },
            },
        )
        current = Snapshot(
            subscription_id="wi-456",
            data={
                "work_item_id": 456,
                "latest_revision": {
                    "rev": 2,
                    "fields": {"System.State": "Active", "System.ChangedBy": "Bob"},
                },
            },
        )

        events = diff_snapshots(previous, current)

        # Expect 2 events: state change + field update (System.ChangedBy)
        assert len(events) == 2
        state_event = next(e for e in events if e.event_type == EventType.WI_STATE_CHANGED)
        assert state_event.payload["previous_state"] == "New"
        assert state_event.payload["current_state"] == "Active"

    def test_new_comment_detected(self) -> None:
        """New work item comment should produce WI_COMMENT_ADDED event."""
        previous = Snapshot(
            subscription_id="wi-456",
            data={"work_item_id": 456, "comments": []},
        )
        current = Snapshot(
            subscription_id="wi-456",
            data={
                "work_item_id": 456,
                "comments": [{"createdBy": {"displayName": "Alice"}, "text": "Comment"}],
            },
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 1
        assert events[0].event_type == EventType.WI_COMMENT_ADDED
        assert events[0].author == "Alice"
