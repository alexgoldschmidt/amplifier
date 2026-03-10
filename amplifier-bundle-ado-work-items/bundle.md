---
bundle:
  name: ado-work-items
  version: 1.0.0
  description: |
    Azure DevOps work item management. Standalone bundle for sprint planning,
    triage, status tracking, and work item CRUD operations.

    Use independently for project management tasks, or compose with
    ado-pr for full PR + work item workflows.

agents:
  include:
    - ado-work-items:agents/ado-work-items
    - ado-work-items:agents/ado-boards

context:
  include:
    - ado-work-items:context/ado-auth.md
    - ado-work-items:context/ado-bootstrap-protocol.md
    - ado-work-items:context/ado-team-config-reference.md
    - ado-work-items:context/ado-work-item-templates.md
    - ado-work-items:context/ado-wiql-reference.md

tools:
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@v1.0.0
---

# ADO Work Items Bundle

Azure DevOps work item management for Amplifier sessions.

## Capabilities

- Create, update, query work items
- Sprint planning and backlog management
- Work item templates per type
- Bootstrap protocol for dynamic process discovery
- Team configuration support

## Usage

```yaml
# In your bundle
extends:
  - ado-work-items:bundle
```

## Key Agents

- `ado-work-items` — Work item CRUD operations
- `ado-boards` — Sprint/iteration management

## Context Files

- `ado-auth.md` — Authentication setup
- `ado-bootstrap-protocol.md` — Dynamic process discovery
- `ado-work-item-templates.md` — Per-type templates
- `ado-team-config-reference.md` — Team customization
