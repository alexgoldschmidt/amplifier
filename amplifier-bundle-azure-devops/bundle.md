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
    
    Prerequisites:
    - Azure CLI with devops extension: az extension add --name azure-devops
    - Authenticated: az login

includes:
  # Foundation provides core tools (bash, filesystem, etc.)
  - bundle: foundation
  # Core bundles (ado-pr includes ado-work-items via composition)
  - bundle: ../amplifier-bundle-ado-pr/bundle.md
  # Additional agents not in composed bundles
  - bundle: azure-devops:behaviors/azure-devops-extras
  # EngHub documentation research
  - bundle: ../amplifier-bundle-ado-research/bundle.md
  # Scrum and standup helpers
  - bundle: ../amplifier-bundle-ado-scrum/bundle.md
  # Test execution and analysis
  - bundle: ../amplifier-bundle-ado-test/bundle.md
  # KQL diagnostics
  - bundle: ../amplifier-bundle-ado-kql/bundle.md
  # SWE Agent task management (GitHub Copilot auto-PR creation)
  - bundle: ../amplifier-bundle-ado-swe-agents/bundle.md
  # Dev machine bundle for autonomous development infrastructure
  - bundle: git+https://github.com/ramparte/amplifier-bundle-dev-machine@main

---

# Azure DevOps Bundle

Full Azure DevOps integration via `az devops` CLI.

## Bundle Composition

```
azure-devops (full suite)
├── foundation
├── ado-pr (PR lifecycle)
│   └── ado-work-items (work item management) ← foundational
├── ado-research (EngHub documentation research)
├── ado-scrum (standup & journal tracking) ← NEW
├── ado-test (test execution & analysis) ← NEW
├── ado-kql (KQL diagnostics) ← NEW
├── ado-swe-agents (GitHub Copilot SWE Agent tasks) ← NEW
├── ado-pipelines (pipeline ops)
├── ado-repos (repository ops)
└── ado-boards (sprint management)
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

## Lighter Alternatives

```yaml
# Just work items (sprint planning, triage, no code)
extends:
  - ado-work-items:bundle

# PRs + work items (most common dev workflow)
extends:
  - ado-pr:bundle

# Full suite (everything)
extends:
  - azure-devops:bundle
```
