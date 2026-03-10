---
bundle:
  name: ado-infra
  version: 1.0.0
  description: |
    Azure DevOps infrastructure operations: pipelines, repos, and boards.
    
    For work items and PR workflow, use ado-work-items or ado-pr bundles.
    
    Prerequisites:
    - Azure CLI with devops extension: az extension add --name azure-devops
    - Authenticated: az login

includes:
  - bundle: foundation

agents:
  include:
    - ado-infra:agents/ado-boards
    - ado-infra:agents/ado-pipelines
    - ado-infra:agents/ado-repos

context:
  include:
    - ado-infra:context/ado-bootstrap-protocol.md
    - ado-infra:context/ado-cli-reference.md

tools:
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@v1.0.0
---

# ADO Infrastructure Bundle

Azure DevOps infrastructure operations via `az devops` CLI.

## Available Agents

| Agent | Use For |
|-------|---------|
| `ado-pipelines` | Pipelines: trigger, monitor, logs, cancel |
| `ado-repos` | Repos: branches, commits, policies (NOT PRs) |
| `ado-boards` | Boards: sprints, backlog, iterations, capacity |

## Quick Start

```bash
# Install Azure CLI devops extension
az extension add --name azure-devops

# Login (bootstrap protocol auto-detects org/project from git remote)
az login

# Verify
az devops project show
```

## When to Use Other Bundles

| Need | Use |
|------|-----|
| Work item management (create, query, update) | `ado-work-items` |
| PR lifecycle (create, review, merge) | `ado-pr` |
| Full ADO suite | `azure-devops` |
