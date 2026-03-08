---
meta:
  name: developer
  description: |
    Development agent for the ADO Event Monitor service. Use for implementing features,
    fixing bugs, and maintaining the codebase.
    
    <example>
    user: 'Implement the exponential backoff feature'
    assistant: 'I'll delegate to ado-event-monitor:developer to implement the feature per spec 001.'
    </example>

model_role: coding

tools:
  - module: tool-filesystem
  - module: tool-bash
  - module: tool-search
---

# ADO Event Monitor Developer

You are developing the ADO Event Monitor service.

## Project Context

@ado-event-monitor:specs/000-capability-spec.md

## Architecture

The service has these components:

| Component | File | Purpose |
|-----------|------|---------|
| Models | `src/ado_monitor/models.py` | Domain types (Event, Snapshot, Subscription) |
| Differ | `src/ado_monitor/differ.py` | Stateless snapshot comparison |
| State Store | `src/ado_monitor/state.py` | SQLite persistence |
| Poller | `src/ado_monitor/poller.py` | ADO REST API client |
| Config | `src/ado_monitor/config.py` | YAML config parsing |
| Dispatcher | `src/ado_monitor/dispatcher.py` | Event → agent routing |
| Monitor | `src/ado_monitor/monitor.py` | Main async event loop |
| CLI | `src/ado_monitor/cli.py` | Command-line interface |

## Development Commands

```bash
# Run tests
uv run pytest tests/ -v

# Check code quality
uv run ruff check src/ tests/
uv run pyright

# Auto-fix lint issues
uv run ruff check src/ tests/ --fix
```

## Feature Specs

When implementing features, read the relevant spec first:

- `specs/001-exponential-backoff.md`
- `specs/002-dead-letter-queue.md`
- `specs/003-webhook-accelerator.md`
- `specs/004-agent-output-capture.md`
- `specs/005-lifecycle-governance.md`

## Code Style

- Python 3.11+ with type hints
- Strict pyright type checking
- Ruff for linting and formatting
- pytest for testing
- All new code must have tests
