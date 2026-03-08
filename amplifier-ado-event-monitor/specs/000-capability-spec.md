# ADO Event Monitor - Capability Specification

## Purpose

An autonomous service that **detects changes** in Azure DevOps (PR updates, work item changes, pipeline completions) and **triggers Amplifier agents** without human intervention.

## Problem Statement

The existing `amplifier-bundle-azure-devops` has agents that respond to human commands. This service closes the loop by watching ADO for events and invoking those agents automatically.

## Core Capabilities

### 1. Event Detection

Detect changes in Azure DevOps entities via polling:

| Entity | Events Detected |
|--------|-----------------|
| Pull Requests | New comments, replies, thread resolutions, status changes, vote changes, new pushes |
| Work Items | State changes, field updates, new comments |

### 2. Event-to-Agent Routing

Route detected events to appropriate Amplifier agents based on user-defined subscriptions:

```yaml
subscriptions:
  - id: pr-123
    type: pull-request
    events: [new-comments, push-update]
    actions:
      - agent: ado-pr-manager
        trigger: new-comments
        behavior: address-feedback
```

### 3. State Persistence

Maintain state to:
- Track last-seen snapshot per subscription (diff detection)
- Deduplicate events (prevent reprocessing)
- Record event history (debugging and audit)

### 4. Recipe Integration

Invoke agents via Amplifier recipes (preferred) for:
- Resumability after interruption
- Approval gates for high-risk actions
- Full audit trails via session logs

## Scope Boundaries

### In Scope

- Polling ADO REST APIs for PR and work item state
- Diffing snapshots to detect changes
- Dispatching to Amplifier agents/recipes
- SQLite-based state persistence
- CLI for configuration and monitoring
- AAD token authentication via Azure CLI
- Optional webhook acceleration (Phase 3)

### Out of Scope

- Pipeline monitoring (future: `ado-pipelines` integration)
- Board/sprint monitoring (future: `ado-boards` integration)
- Multi-tenant deployments (single org focus initially)
- Real-time streaming (polling-first architecture)
- Custom event transformations (events pass through as-is)

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Detection latency | ≤ poll interval (default 60s for PRs, 120s for WIs) |
| Availability | Survives restarts without reprocessing events |
| Scalability | 100+ subscriptions per instance |
| Resource usage | < 100MB memory, minimal CPU when idle |
| Dependencies | Python 3.11+, Azure CLI, SQLite |

## Success Criteria

1. **Detection**: Service detects new PR comment within 60 seconds
2. **Routing**: Events correctly matched to subscription actions
3. **Durability**: Service survives restart without re-processing old events
4. **Safety**: Service never triggers infinite loops from its own actions
5. **Compatibility**: Works with both cloud ADO and on-premises ADO Server

## Anti-Loop Safety (Critical)

The service MUST NOT react to its own actions. Enforced via:
- Author filtering (ignore events from "Amplifier Bot", service principal)
- All agent replies include `🤖 [Amplifier]` prefix
- Configurable `ignore_authors` list in subscriptions.yaml

## Authentication

- **Primary**: Azure AD tokens via Azure CLI (`az login`)
- **Fallback**: None (PAT support removed per design decision)
- **Token refresh**: Automatic via Azure CLI on each API call

## Deployment Models

| Mode | Description |
|------|-------------|
| Local/Dev | `ado-monitor --config subscriptions.yaml` on developer machine |
| Server | Container or systemd service with managed identity |
| Cloud | Azure Container Instance or similar |

## Phased Delivery

| Phase | Capabilities | Status |
|-------|--------------|--------|
| 1 | Polling, diffing, state store, basic dispatch | ✅ Complete |
| 2 | Exponential backoff, DLQ, output capture | 📋 Spec'd |
| 3 | Webhook accelerator | 📋 Spec'd |

## Dependencies on Other Components

| Component | Dependency Type | Purpose |
|-----------|-----------------|---------|
| Azure CLI | Runtime | AAD token acquisition |
| Amplifier CLI | Runtime | Agent/recipe invocation |
| `ado-pr-manager` | Integration | PR feedback handling |
| `ado-work-items` | Integration | Work item processing |
| `ado-pipelines` | Future | Build monitoring |

## Configuration Schema

See `subscriptions.yaml.example` for full schema. Key elements:
- `subscriptions[]`: List of entities to watch
- `ignore_authors`: Authors to filter (anti-loop)
- `settings`: Global configuration (retention, output capture)
