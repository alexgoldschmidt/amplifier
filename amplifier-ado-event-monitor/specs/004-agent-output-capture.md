# Feature Spec: Agent Output Capture and Logging

## Overview

Capture and persist the full output of agent invocations for debugging, audit trails, and feeding results back into the system. Store session IDs for recipe invocations to enable session inspection and resumption.

## Acceptance Criteria

1. **Output storage**: Agent stdout/stderr captured in SQLite `dispatch_logs` table
2. **Session tracking**: Recipe session IDs stored for later inspection
3. **Structured logging**: JSON-formatted logs with event context
4. **Log rotation**: Old logs automatically purged after configurable retention
5. **Query interface**: CLI command to view dispatch history
6. **Feedback loop**: Agent results queryable for downstream processing

## Interface

```python
# Additions to src/ado_monitor/state.py

class StateStore:
    def record_dispatch(
        self,
        event_id: int,
        agent: str,
        success: bool,
        session_id: str | None = None,
        output: str | None = None,
        error: str | None = None,
        duration_ms: int | None = None,
    ) -> int:
        """Record a dispatch attempt. Returns dispatch_log_id."""

    def get_dispatch_logs(
        self,
        subscription_id: str | None = None,
        event_id: int | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get dispatch history."""

    def get_session_output(self, session_id: str) -> dict | None:
        """Get stored output for a recipe session."""

    def cleanup_old_logs(self, retention_days: int = 30) -> int:
        """Delete old dispatch logs. Returns count deleted."""
```

```python
# Enhanced DispatchResult in src/ado_monitor/dispatcher.py

@dataclass
class DispatchResult:
    success: bool
    agent: str
    session_id: str | None = None
    output: str | None = None
    error: str | None = None
    duration_ms: int | None = None  # NEW: Track execution time
```

## Database Schema

```sql
CREATE TABLE dispatch_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    subscription_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    session_id TEXT,
    success INTEGER NOT NULL,
    output TEXT,
    error TEXT,
    duration_ms INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id)
);

CREATE INDEX idx_dispatch_event ON dispatch_logs(event_id);
CREATE INDEX idx_dispatch_subscription ON dispatch_logs(subscription_id);
CREATE INDEX idx_dispatch_session ON dispatch_logs(session_id);
CREATE INDEX idx_dispatch_created ON dispatch_logs(created_at);
```

## CLI Commands

```bash
# View dispatch history
ado-monitor logs [--subscription PR-123] [--limit 50]

# View specific dispatch output
ado-monitor logs show <dispatch_id>

# View recipe session (delegates to amplifier)
ado-monitor session <session_id>

# Cleanup old logs
ado-monitor logs cleanup [--older-than 30]
```

## Config Extension

```yaml
# subscriptions.yaml
settings:
  log_retention_days: 30      # Auto-cleanup after this many days
  capture_output: true        # Store full agent output
  max_output_size: 1048576    # Truncate output larger than 1MB
```

## Files to Modify

| File | Change |
|------|--------|
| `src/ado_monitor/state.py` | Add dispatch_logs table and methods |
| `src/ado_monitor/dispatcher.py` | Capture output, track duration, record dispatch |
| `src/ado_monitor/monitor.py` | Call state_store.record_dispatch() after each dispatch |
| `src/ado_monitor/config.py` | Parse new settings section |
| `src/ado_monitor/cli.py` | Add `logs` subcommand |
| `tests/test_state.py` | Add dispatch log tests |

## Test Cases

1. `test_dispatch_output_captured` - stdout/stderr stored correctly
2. `test_session_id_tracked` - Recipe session IDs preserved
3. `test_duration_measured` - Execution time recorded accurately
4. `test_output_truncated_if_too_large` - Large outputs handled gracefully
5. `test_logs_query_by_subscription` - Filtering works
6. `test_cleanup_respects_retention` - Only old logs deleted

## Edge Cases

- Agent produces binary output: Store as base64 or skip
- Agent timeout: Record partial output if available
- Very long running agent: Stream output or capture at end
- Session ID extraction from recipe output: Parse JSON response

## Dependencies

None - extends existing SQLite schema.

## Estimated Complexity

Low-Medium - touches multiple files but straightforward additions.
