# Feature Spec: Dead Letter Queue for Failed Dispatches

## Overview

When agent dispatches fail (agent crash, timeout, unexpected error), events should be moved to a dead letter queue (DLQ) for manual inspection and replay rather than being lost or retried indefinitely.

## Acceptance Criteria

1. **DLQ storage**: Failed events stored in SQLite `dead_letter_events` table
2. **Failure capture**: Error message, stack trace, attempt count, timestamps preserved
3. **Retry limits**: Events moved to DLQ after 3 failed dispatch attempts
4. **Manual replay**: CLI command to replay DLQ events
5. **Inspection**: CLI command to list and inspect DLQ entries
6. **Cleanup**: CLI command to purge old DLQ entries
7. **Metrics**: Log count of DLQ entries on startup and periodically

## Interface

```python
# Additions to src/ado_monitor/state.py

class StateStore:
    def move_to_dlq(
        self,
        event_id: int,
        error: str,
        traceback: str | None = None,
    ) -> None:
        """Move a failed event to the dead letter queue."""

    def get_dlq_events(
        self,
        subscription_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get dead letter queue entries."""

    def replay_dlq_event(self, dlq_id: int) -> int:
        """Move a DLQ event back to pending. Returns new event_id."""

    def purge_dlq(self, older_than_days: int = 30) -> int:
        """Delete old DLQ entries. Returns count deleted."""
```

```python
# New CLI commands in src/ado_monitor/cli.py

# ado-monitor dlq list [--subscription PR-123]
# ado-monitor dlq inspect <dlq_id>
# ado-monitor dlq replay <dlq_id>
# ado-monitor dlq purge [--older-than 30]
```

## Database Schema

```sql
CREATE TABLE dead_letter_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_event_id INTEGER NOT NULL,
    subscription_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    author TEXT,
    original_created_at TEXT NOT NULL,
    moved_to_dlq_at TEXT NOT NULL,
    attempt_count INTEGER NOT NULL,
    error_message TEXT NOT NULL,
    error_traceback TEXT
);

CREATE INDEX idx_dlq_subscription ON dead_letter_events(subscription_id);
CREATE INDEX idx_dlq_moved_at ON dead_letter_events(moved_to_dlq_at);
```

## Files to Modify

| File | Change |
|------|--------|
| `src/ado_monitor/state.py` | Add DLQ table and methods |
| `src/ado_monitor/dispatcher.py` | Track attempt count, move to DLQ after 3 failures |
| `src/ado_monitor/cli.py` | Add `dlq` subcommand with list/inspect/replay/purge |
| `tests/test_state.py` | Add DLQ tests |
| `tests/test_dispatcher.py` | **NEW** - Test DLQ integration |

## Test Cases

1. `test_event_moves_to_dlq_after_3_failures` - Verify 3-strike rule
2. `test_dlq_preserves_error_details` - Error message and traceback captured
3. `test_replay_creates_new_pending_event` - Replayed event returns to queue
4. `test_purge_respects_age_threshold` - Only old entries deleted
5. `test_dlq_list_filters_by_subscription` - Filtering works correctly

## Edge Cases

- Replay of already-deleted event: Return error, don't crash
- DLQ event with invalid payload: Log warning, still store
- Multiple replays of same event: Each creates new pending event

## Dependencies

None - extends existing SQLite schema.

## Estimated Complexity

Medium - multiple components touched, but well-defined boundaries.
