# ADO Event Monitor - Agent Instructions

## Project Overview

This is the ADO Event Monitor service - an autonomous event detection system for Azure DevOps that triggers Amplifier agents without human intervention.

## Architecture

```
Poller → Differ → Dispatcher → Amplifier Agent
           ↓
      State Store (SQLite)
```

## Key Files

| File | Purpose |
|------|---------|
| `src/ado_monitor/differ.py` | Core event detection - stateless snapshot comparison |
| `src/ado_monitor/state.py` | SQLite persistence and event deduplication |
| `src/ado_monitor/poller.py` | ADO REST API client with AAD auth |
| `src/ado_monitor/monitor.py` | Main async event loop |
| `specs/` | Feature specifications for future work |

## Development Workflow

1. **Read the spec** before implementing any feature
2. **Run tests** after every change: `uv run pytest`
3. **Check types**: `uv run pyright`
4. **Format code**: `uv run ruff check --fix`

## Current Status

- **Phase 1 Complete**: Polling, diffing, state store, basic dispatch
- **Phase 2 Spec'd**: Exponential backoff, DLQ, output capture
- **Phase 3 Spec'd**: Webhook accelerator
- **PM Feature Spec'd**: Lifecycle governance

## Authentication

Uses Azure AD tokens via Azure CLI (`az login`). No PAT support.

## Anti-Loop Safety

Critical: The service must never react to its own actions. Enforced via author filtering in `differ.py`.
