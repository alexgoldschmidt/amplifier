"""Integration tests for ADO Event Monitor + Docker Foreman (Spec 006).

These tests cover the ForemanSubscriptionSource, CompositeSubscriptionSource,
YamlSubscriptionSource, and reconciliation-related behaviors described in
spec 006-foreman-integration-spec.md.

NOTE: The ``ado_monitor.sources`` module does not yet exist. These tests will
fail with ImportError until the implementation is complete. They serve as
executable acceptance criteria for the implementation work.

Run with: pytest tests/test_foreman_integration.py -v
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ado_monitor.differ import IGNORE_AUTHORS, diff_snapshots
from ado_monitor.dispatcher import Dispatcher
from ado_monitor.models import Action, Event, EventType, Snapshot, Subscription, SubscriptionType

# These imports will work once the sources/ module is implemented.
from ado_monitor.sources.composite import CompositeSubscriptionSource
from ado_monitor.sources.foreman import ForemanSubscriptionSource
from ado_monitor.sources.yaml_source import YamlSubscriptionSource

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def workers_dir(tmp_path: Path) -> Path:
    """Create a temporary workers/ directory inside a docker-foreman layout."""
    d = tmp_path / "workers"
    d.mkdir()
    return d


@pytest.fixture()
def foreman_base(tmp_path: Path, workers_dir: Path) -> Path:
    """tmp_path acts as the docker-foreman base directory (contains workers/)."""
    return tmp_path


def _write_worker(workers_dir: Path, name: str, work_item_id: int, **extra: object) -> Path:
    """Helper: write a valid worker JSON file."""
    data = {
        "name": name,
        "container_id": f"ctr-{name}",
        "session_id": f"sess-{name}",
        "work_item_id": work_item_id,
        "branch": f"feature/{name}",
        "created_at": "2026-03-08T04:30:00Z",
        "task": f"Implement {name}",
        "state": "active",
        **extra,
    }
    path = workers_dir / f"{name}.json"
    path.write_text(json.dumps(data))
    return path


def _make_foreman_source(base_path: Path, **kwargs: object) -> ForemanSubscriptionSource:
    return ForemanSubscriptionSource(
        project="test-project",
        org="testorg",
        ado_project="TestProject",
        poll_interval_seconds=60,
        base_path=base_path,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# T1 — Worker spawn → subscription created
# ---------------------------------------------------------------------------


class TestWorkerSpawnCreatesSubscription:
    """Scenario 1: Creating a worker JSON → ForemanSubscriptionSource generates a subscription."""

    async def test_single_worker_produces_one_subscription(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        _write_worker(workers_dir, "feature-auth", work_item_id=101)

        source = _make_foreman_source(foreman_base)
        subs = await source.get_subscriptions()

        assert len(subs) == 1
        sub = subs[0]
        assert sub.id == "foreman:wi-101"
        assert sub.type == SubscriptionType.WORK_ITEM
        assert sub.work_item_id == 101
        assert sub.org == "testorg"
        assert sub.project == "TestProject"

    async def test_subscription_id_uses_foreman_prefix(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        _write_worker(workers_dir, "bugfix-api", work_item_id=202)

        source = _make_foreman_source(foreman_base)
        subs = await source.get_subscriptions()

        assert subs[0].id == "foreman:wi-202"

    async def test_subscription_has_docker_worker_actions(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        _write_worker(workers_dir, "feature-auth", work_item_id=101)

        source = _make_foreman_source(foreman_base)
        subs = await source.get_subscriptions()

        actions = subs[0].actions
        assert len(actions) >= 1
        agents = {a.agent for a in actions}
        assert "docker-worker" in agents

    async def test_subscription_events_include_comment_and_state(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        _write_worker(workers_dir, "feature-auth", work_item_id=101)

        source = _make_foreman_source(foreman_base)
        subs = await source.get_subscriptions()

        events = subs[0].events
        assert "comment-added" in events or "wi.comment.added" in events
        assert "state-change" in events or "wi.state.changed" in events

    async def test_multiple_workers_produce_multiple_subscriptions(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        _write_worker(workers_dir, "feature-auth", work_item_id=101)
        _write_worker(workers_dir, "bugfix-api", work_item_id=202)

        source = _make_foreman_source(foreman_base)
        subs = await source.get_subscriptions()

        assert len(subs) == 2
        ids = {s.id for s in subs}
        assert "foreman:wi-101" in ids
        assert "foreman:wi-202" in ids

    async def test_poll_interval_forwarded_to_subscription(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        _write_worker(workers_dir, "feature-auth", work_item_id=101)

        source = _make_foreman_source(foreman_base, poll_interval_seconds=30)
        subs = await source.get_subscriptions()

        assert subs[0].poll_interval_seconds == 30

    async def test_source_id_is_foreman(self, foreman_base: Path) -> None:
        source = _make_foreman_source(foreman_base)
        assert source.source_id == "foreman"


# ---------------------------------------------------------------------------
# T2 — Human comment → WI_COMMENT_ADDED event produced
# ---------------------------------------------------------------------------


class TestHumanCommentDetected:
    """Scenario 2: Comment on WI → WI_COMMENT_ADDED event via differ."""

    def test_new_comment_produces_wi_comment_added(self) -> None:
        previous = Snapshot(
            subscription_id="foreman:wi-101",
            data={"work_item_id": 101, "comments": []},
        )
        current = Snapshot(
            subscription_id="foreman:wi-101",
            data={
                "work_item_id": 101,
                "comments": [
                    {
                        "createdBy": {"displayName": "John Doe"},
                        "text": "🔧 RESPONSE: Use JWT for stateless auth",
                    }
                ],
            },
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 1
        assert events[0].event_type == EventType.WI_COMMENT_ADDED
        assert events[0].subscription_id == "foreman:wi-101"
        assert events[0].author == "John Doe"

    def test_comment_payload_contains_work_item_id(self) -> None:
        previous = Snapshot(
            subscription_id="foreman:wi-101",
            data={"work_item_id": 101, "comments": []},
        )
        current = Snapshot(
            subscription_id="foreman:wi-101",
            data={
                "work_item_id": 101,
                "comments": [{"createdBy": {"displayName": "Alice"}, "text": "Hello"}],
            },
        )

        events = diff_snapshots(previous, current)

        assert events[0].payload["work_item_id"] == 101

    def test_no_events_on_first_poll_for_wi(self) -> None:
        current = Snapshot(
            subscription_id="foreman:wi-101",
            data={
                "work_item_id": 101,
                "comments": [{"createdBy": {"displayName": "Alice"}, "text": "Initial"}],
            },
        )

        events = diff_snapshots(None, current)

        assert events == []


# ---------------------------------------------------------------------------
# T3 — Event dispatch → docker-worker agent invoked
# ---------------------------------------------------------------------------


class TestEventDispatchToDockerWorker:
    """Scenario 3: WI_COMMENT_ADDED event routes to docker-worker agent."""

    def _make_foreman_subscription(self, wi_id: int = 101) -> Subscription:
        return Subscription(
            id=f"foreman:wi-{wi_id}",
            type=SubscriptionType.WORK_ITEM,
            org="testorg",
            project="TestProject",
            poll_interval_seconds=60,
            work_item_id=wi_id,
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
        )

    async def test_wi_comment_dispatches_to_docker_worker(self) -> None:
        sub = self._make_foreman_subscription()
        dispatcher = Dispatcher(
            subscriptions={"foreman:wi-101": sub},
            amplifier_cmd="amplifier",
        )

        event = Event(
            event_type=EventType.WI_COMMENT_ADDED,
            subscription_id="foreman:wi-101",
            payload={
                "work_item_id": 101,
                "comment": {"createdBy": {"displayName": "John"}, "text": "Use JWT"},
            },
            author="John",
        )

        with patch("ado_monitor.dispatcher.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            result = await dispatcher.dispatch(event)

        assert result is not None
        assert result.success is True
        assert result.agent == "docker-worker"

    async def test_dispatch_invokes_amplifier_with_agent_flag(self) -> None:
        sub = self._make_foreman_subscription()
        dispatcher = Dispatcher(
            subscriptions={"foreman:wi-101": sub},
            amplifier_cmd="amplifier",
        )

        event = Event(
            event_type=EventType.WI_COMMENT_ADDED,
            subscription_id="foreman:wi-101",
            payload={"work_item_id": 101, "comment": {}},
        )

        captured_cmd: list[list[str]] = []

        def capture_run(cmd: list[str], **_: object) -> MagicMock:
            captured_cmd.append(cmd)
            return MagicMock(returncode=0, stdout="ok", stderr="")

        with patch("ado_monitor.dispatcher.subprocess.run", side_effect=capture_run):
            await dispatcher.dispatch(event)

        assert len(captured_cmd) == 1
        cmd = captured_cmd[0]
        assert "amplifier" in cmd
        assert "--agent" in cmd
        idx = cmd.index("--agent")
        assert cmd[idx + 1] == "docker-worker"

    async def test_wi_state_change_dispatches_to_docker_worker(self) -> None:
        sub = self._make_foreman_subscription()
        dispatcher = Dispatcher(
            subscriptions={"foreman:wi-101": sub},
            amplifier_cmd="amplifier",
        )

        event = Event(
            event_type=EventType.WI_STATE_CHANGED,
            subscription_id="foreman:wi-101",
            payload={"work_item_id": 101, "previous_state": "Active", "current_state": "Blocked"},
        )

        with patch("ado_monitor.dispatcher.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            result = await dispatcher.dispatch(event)

        assert result is not None
        assert result.agent == "docker-worker"

    async def test_dispatch_context_contains_work_item_id(self) -> None:
        sub = self._make_foreman_subscription(wi_id=101)
        dispatcher = Dispatcher(subscriptions={"foreman:wi-101": sub})

        context = dispatcher._build_context(
            event=Event(
                event_type=EventType.WI_COMMENT_ADDED,
                subscription_id="foreman:wi-101",
                payload={"comment": {"text": "hello"}},
            ),
            action=sub.actions[0],
            subscription=sub,
        )

        assert context["work_item_id"] == 101
        assert context["event_type"] == "wi.comment.added"
        assert context["behavior"] == "resume-from-response"


# ---------------------------------------------------------------------------
# T4 — Worker destroy → subscription removed
# ---------------------------------------------------------------------------


class TestWorkerDestroyRemovesSubscription:
    """Scenario 4: Worker JSON deleted → subscription disappears from source."""

    async def test_deleted_worker_json_removed_from_subscriptions(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        worker_file = _write_worker(workers_dir, "feature-auth", work_item_id=101)

        source = _make_foreman_source(foreman_base)

        subs_before = await source.get_subscriptions()
        assert len(subs_before) == 1

        worker_file.unlink()

        subs_after = await source.get_subscriptions()
        assert len(subs_after) == 0

    async def test_only_destroyed_worker_removed(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        worker_a = _write_worker(workers_dir, "feature-auth", work_item_id=101)
        _write_worker(workers_dir, "bugfix-api", work_item_id=202)

        source = _make_foreman_source(foreman_base)

        worker_a.unlink()
        subs = await source.get_subscriptions()

        assert len(subs) == 1
        assert subs[0].id == "foreman:wi-202"

    async def test_closed_state_worker_excluded(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        """Workers with state='closed' or 'destroyed' should be excluded."""
        _write_worker(workers_dir, "feature-auth", work_item_id=101, state="closed")
        _write_worker(workers_dir, "bugfix-api", work_item_id=202, state="active")

        source = _make_foreman_source(foreman_base)
        subs = await source.get_subscriptions()

        assert len(subs) == 1
        assert subs[0].id == "foreman:wi-202"

    async def test_destroyed_state_worker_excluded(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        _write_worker(workers_dir, "feature-auth", work_item_id=101, state="destroyed")

        source = _make_foreman_source(foreman_base)
        subs = await source.get_subscriptions()

        assert len(subs) == 0


# ---------------------------------------------------------------------------
# T5 — Static YAML + foreman sources coexist
# ---------------------------------------------------------------------------


class TestStaticAndForemanSourcesCoexist:
    """Scenario 5: CompositeSubscriptionSource merges YAML and foreman subscriptions."""

    def _make_static_sub(self) -> Subscription:
        return Subscription(
            id="yaml:pr-123",
            type=SubscriptionType.PULL_REQUEST,
            org="testorg",
            project="TestProject",
            repo="test-repo",
            pr_id=123,
            poll_interval_seconds=60,
            events=["new-comments"],
            actions=[Action(agent="ado-pr-manager", trigger="new-comments")],
        )

    async def test_composite_returns_both_sources(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        _write_worker(workers_dir, "feature-auth", work_item_id=101)

        yaml_source = YamlSubscriptionSource(subscriptions=[self._make_static_sub()])
        foreman_source = _make_foreman_source(foreman_base)
        composite = CompositeSubscriptionSource(sources=[yaml_source, foreman_source])

        subs = await composite.get_subscriptions()

        assert len(subs) == 2
        ids = {s.id for s in subs}
        assert "yaml:pr-123" in ids
        assert "foreman:wi-101" in ids

    async def test_yaml_source_returns_static_subscriptions(self) -> None:
        static_sub = self._make_static_sub()
        source = YamlSubscriptionSource(subscriptions=[static_sub])

        subs = await source.get_subscriptions()

        assert subs == [static_sub]

    async def test_yaml_source_id(self) -> None:
        source = YamlSubscriptionSource(subscriptions=[])
        assert source.source_id == "yaml"

    async def test_composite_source_id(self, foreman_base: Path) -> None:
        composite = CompositeSubscriptionSource(sources=[])
        assert composite.source_id == "composite"

    async def test_composite_with_no_workers_and_static_subs(self, foreman_base: Path) -> None:
        yaml_source = YamlSubscriptionSource(subscriptions=[self._make_static_sub()])
        foreman_source = _make_foreman_source(foreman_base)  # workers/ exists but is empty
        composite = CompositeSubscriptionSource(sources=[yaml_source, foreman_source])

        subs = await composite.get_subscriptions()

        assert len(subs) == 1
        assert subs[0].id == "yaml:pr-123"


# ---------------------------------------------------------------------------
# T6 — Malformed worker JSON skipped
# ---------------------------------------------------------------------------


class TestMalformedWorkerJsonSkipped:
    """Scenario 6: Bad JSON files are warned and skipped; valid workers unaffected."""

    async def test_malformed_json_skipped_with_warning(
        self, foreman_base: Path, workers_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        bad_file = workers_dir / "bad-worker.json"
        bad_file.write_text("{ this is not valid json }")

        source = _make_foreman_source(foreman_base)
        with caplog.at_level(logging.WARNING):
            subs = await source.get_subscriptions()

        assert len(subs) == 0
        assert any("bad-worker" in record.message for record in caplog.records)

    async def test_valid_workers_unaffected_by_malformed_peer(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        bad_file = workers_dir / "bad-worker.json"
        bad_file.write_text("not-json")
        _write_worker(workers_dir, "good-worker", work_item_id=101)

        source = _make_foreman_source(foreman_base)
        subs = await source.get_subscriptions()

        assert len(subs) == 1
        assert subs[0].id == "foreman:wi-101"

    async def test_json_missing_work_item_id_skipped(
        self, foreman_base: Path, workers_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        incomplete = {
            "name": "incomplete-worker",
            "container_id": "abc",
            "session_id": "xyz",
            "branch": "feature/x",
            "created_at": "2026-01-01T00:00:00Z",
            # work_item_id intentionally missing
        }
        (workers_dir / "incomplete-worker.json").write_text(json.dumps(incomplete))

        source = _make_foreman_source(foreman_base)
        with caplog.at_level(logging.WARNING):
            subs = await source.get_subscriptions()

        assert len(subs) == 0
        assert any("incomplete-worker" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# T7 — Missing workers directory
# ---------------------------------------------------------------------------


class TestMissingWorkersDirectory:
    """Scenario 7: No workers/ directory → empty subscription list, no crash."""

    async def test_missing_workers_dir_returns_empty_list(self, tmp_path: Path) -> None:
        # tmp_path has no workers/ subdirectory
        source = _make_foreman_source(tmp_path)
        subs = await source.get_subscriptions()

        assert subs == []

    async def test_missing_workers_dir_logs_info(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        source = _make_foreman_source(tmp_path)
        with caplog.at_level(logging.INFO):
            await source.get_subscriptions()

        # Should log something (at least info level), not crash
        # The exact message is implementation-defined, but should not be an error
        error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_records) == 0

    async def test_no_exception_raised_for_missing_dir(self, tmp_path: Path) -> None:
        source = _make_foreman_source(tmp_path)
        # Must not raise
        result = await source.get_subscriptions()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# T8 — Monitor restart recovery
# ---------------------------------------------------------------------------


class TestMonitorRestartRecovery:
    """Scenario 8: On startup, all existing worker JSONs are discovered."""

    async def test_all_existing_workers_discovered_on_startup(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        # Pre-populate workers as if the foreman had already spawned them
        _write_worker(workers_dir, "feature-auth", work_item_id=101)
        _write_worker(workers_dir, "bugfix-api", work_item_id=202)
        _write_worker(workers_dir, "refactor-db", work_item_id=303)

        source = _make_foreman_source(foreman_base)
        subs = await source.get_subscriptions()

        assert len(subs) == 3
        ids = {s.id for s in subs}
        assert "foreman:wi-101" in ids
        assert "foreman:wi-202" in ids
        assert "foreman:wi-303" in ids

    async def test_closed_workers_not_rediscovered_on_restart(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        _write_worker(workers_dir, "feature-auth", work_item_id=101, state="active")
        _write_worker(workers_dir, "done-task", work_item_id=200, state="closed")

        source = _make_foreman_source(foreman_base)
        subs = await source.get_subscriptions()

        assert len(subs) == 1
        assert subs[0].id == "foreman:wi-101"

    async def test_source_is_stateless_across_calls(
        self, foreman_base: Path, workers_dir: Path
    ) -> None:
        """Each call to get_subscriptions re-reads disk (no stale cache)."""
        _write_worker(workers_dir, "feature-auth", work_item_id=101)

        source = _make_foreman_source(foreman_base)
        first = await source.get_subscriptions()
        assert len(first) == 1

        _write_worker(workers_dir, "bugfix-api", work_item_id=202)
        second = await source.get_subscriptions()
        assert len(second) == 2


# ---------------------------------------------------------------------------
# T9 — Anti-loop filtering
# ---------------------------------------------------------------------------


class TestAntiloopFiltering:
    """Scenario 9: Comments from IGNORE_AUTHORS are not dispatched."""

    def test_amplifier_bot_comment_filtered(self) -> None:
        previous = Snapshot(
            subscription_id="foreman:wi-101",
            data={"work_item_id": 101, "comments": []},
        )
        current = Snapshot(
            subscription_id="foreman:wi-101",
            data={
                "work_item_id": 101,
                "comments": [
                    {
                        "createdBy": {"displayName": "Amplifier Bot"},
                        "text": "🤖 [Amplifier] Work in progress",
                    }
                ],
            },
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 0

    def test_amplifier_bracket_bot_comment_filtered(self) -> None:
        previous = Snapshot(
            subscription_id="foreman:wi-101",
            data={"work_item_id": 101, "comments": []},
        )
        current = Snapshot(
            subscription_id="foreman:wi-101",
            data={
                "work_item_id": 101,
                "comments": [
                    {
                        "createdBy": {"displayName": "amplifier[bot]"},
                        "text": "Status update from bot",
                    }
                ],
            },
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 0

    def test_human_comment_not_filtered(self) -> None:
        previous = Snapshot(
            subscription_id="foreman:wi-101",
            data={"work_item_id": 101, "comments": []},
        )
        current = Snapshot(
            subscription_id="foreman:wi-101",
            data={
                "work_item_id": 101,
                "comments": [
                    {
                        "createdBy": {"displayName": "John Doe"},
                        "text": "Use JWT for auth",
                    }
                ],
            },
        )

        events = diff_snapshots(previous, current)

        assert len(events) == 1
        assert events[0].author == "John Doe"

    def test_ignore_authors_contains_expected_defaults(self) -> None:
        assert "Amplifier Bot" in IGNORE_AUTHORS
        assert "amplifier[bot]" in IGNORE_AUTHORS

    async def test_filtered_event_not_dispatched(self) -> None:
        """Dispatcher returns None for events with no matching action trigger."""
        sub = Subscription(
            id="foreman:wi-101",
            type=SubscriptionType.WORK_ITEM,
            org="testorg",
            project="TestProject",
            poll_interval_seconds=60,
            work_item_id=101,
            events=["comment-added"],
            actions=[Action(agent="docker-worker", trigger="comment-added")],
        )
        dispatcher = Dispatcher(subscriptions={"foreman:wi-101": sub})

        # Simulate what happens after filter: no events make it through
        # (author is in IGNORE_AUTHORS, so differ produces no events)
        previous = Snapshot(
            subscription_id="foreman:wi-101",
            data={"work_item_id": 101, "comments": []},
        )
        current = Snapshot(
            subscription_id="foreman:wi-101",
            data={
                "work_item_id": 101,
                "comments": [
                    {
                        "createdBy": {"displayName": "Amplifier Bot"},
                        "text": "Auto-reply",
                    }
                ],
            },
        )

        events = diff_snapshots(previous, current)
        assert events == [], "Amplifier Bot comments must be filtered by differ"

        # Confirm no dispatch calls needed (events list is empty)
        with patch("ado_monitor.dispatcher.subprocess.run") as mock_run:
            for event in events:
                await dispatcher.dispatch(event)
            mock_run.assert_not_called()
