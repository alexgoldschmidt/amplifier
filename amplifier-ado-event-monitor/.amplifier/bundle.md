---
bundle:
  name: ado-event-monitor
  version: 1.0.0
  description: |
    ADO Event Monitor - autonomous event detection for Azure DevOps.
    
    Polls ADO for changes and triggers Amplifier agents without human intervention.
    
    Prerequisites:
    - Azure CLI with devops extension: az extension add --name azure-devops
    - Authenticated: az login

extends: foundation

includes:
  # Dev machine bundle for autonomous development infrastructure
  - bundle: git+https://github.com/ramparte/amplifier-bundle-dev-machine@main

tools: []
# No custom tools — agents use tool-bash inherited from foundation
---

# ADO Event Monitor Bundle

Autonomous Azure DevOps event detection and agent triggering.

## Architecture

```
Poller → Differ → Dispatcher → Amplifier Agent
           ↓
      State Store (SQLite)
```

## Quick Start

```bash
# Install Azure CLI devops extension
az extension add --name azure-devops

# Login
az login

# Run the monitor
uv run python -m ado_monitor
```

## Development

```bash
# Run tests
uv run pytest

# Type check
uv run pyright

# Lint
uv run ruff check --fix
```
