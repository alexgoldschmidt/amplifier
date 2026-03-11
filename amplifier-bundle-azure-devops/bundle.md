---
bundle:
  name: azure-devops
  version: 1.0.0
  description: |
    Full Azure DevOps integration for Amplifier.
    
    Composes work items + PR management + pipelines + repos + boards.
    For lighter usage, use individual bundles:
    - ado-work-items: Just work item management
    - ado-pr: PR lifecycle + work item linking
    - ado-infra: Pipelines, repos, boards
    
    Prerequisites:
    - Azure CLI with devops extension: az extension add --name azure-devops
    - Authenticated: az login

includes:
  # Foundation provides core tools (bash, filesystem, etc.)
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  # Core bundles (ado-pr includes ado-work-items via composition)
  - bundle: git+https://github.com/alexgoldschmidt/amplifier@master#subdirectory=amplifier-bundle-ado-pr
  # Infrastructure: pipelines, repos, boards
  - bundle: git+https://github.com/alexgoldschmidt/amplifier@master#subdirectory=amplifier-bundle-ado-infra
  # EngHub documentation research
  - bundle: git+https://github.com/alexgoldschmidt/amplifier@master#subdirectory=amplifier-bundle-ado-research
  # Scrum and standup helpers
  - bundle: git+https://github.com/alexgoldschmidt/amplifier@master#subdirectory=amplifier-bundle-ado-scrum
  # Test execution and analysis
  - bundle: git+https://github.com/alexgoldschmidt/amplifier@master#subdirectory=amplifier-bundle-ado-test
  # KQL diagnostics
  - bundle: git+https://github.com/alexgoldschmidt/amplifier@master#subdirectory=amplifier-bundle-ado-kql
  # SWE Agent task management (GitHub Copilot auto-PR creation)
  - bundle: git+https://github.com/alexgoldschmidt/amplifier@master#subdirectory=amplifier-bundle-ado-swe-agents
  # Local worktree-based parallel development
  - bundle: git+https://github.com/alexgoldschmidt/amplifier@master#subdirectory=amplifier-bundle-ado-worktrees

context:
  include:
    - azure-devops:context/ado-routing.md

---

# Azure DevOps Bundle

Full Azure DevOps integration via `az devops` CLI. **This is a pure aggregator — no local agents.**

## Bundle Composition

```
azure-devops (full suite)
├── foundation
├── ado-pr (PR lifecycle)
│   └── ado-work-items (work item management)
├── ado-infra (infrastructure)
│   ├── ado-pipelines (pipeline ops)
│   ├── ado-repos (repository ops)
│   └── ado-boards (sprint management)
├── ado-research (EngHub documentation research)
├── ado-scrum (standup & journal tracking)
├── ado-test (test execution & analysis)
├── ado-kql (KQL diagnostics)
├── ado-swe-agents (GitHub Copilot SWE Agent tasks)
└── ado-worktrees (local parallel development)
```

## Quick Start

```bash
# Install Azure CLI devops extension
az extension add --name azure-devops

# Login (bootstrap protocol auto-detects org/project from git remote)
az login

# Verify
az devops project show
```

## Available Agents

| Agent | Use For |
|-------|---------|
| `ado-work-items` | Work items: create, query, update, link |
| `ado-pr-manager` | PR lifecycle: draft PRs, review comments, WI linking |
| `ado-pipelines` | Pipelines: trigger, monitor, logs |
| `ado-repos` | Repos: branches, commits (NOT PRs) |
| `ado-boards` | Boards: sprints, backlog, iterations |
| `ado-scrum-helper` | Standup generation, journal tracking, blocker detection |
| `ado-test-runner` | Local tests, pipeline results, failure linking |
| `ado-kql-analyst` | KQL queries, query library, Geneva diagnostics |
| `ado-swe-agent` | **REQUIRED** for creating PRs via GitHub Copilot SWE Agent |
| `worktree-coordinator` | Local parallel development via git worktrees |

## Lighter Alternatives

```yaml
# Just work items (sprint planning, triage, no code)
includes:
  - bundle: ado-work-items

# PRs + work items (most common dev workflow)
includes:
  - bundle: ado-pr

# Infrastructure only (pipelines, repos, boards)
includes:
  - bundle: ado-infra

# Full suite (everything)
includes:
  - bundle: azure-devops
```
