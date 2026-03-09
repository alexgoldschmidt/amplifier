---
bundle:
  name: ado-scrum
  version: 1.0.0
  description: |
    Standup generation, journal tracking, and blocker detection for Azure DevOps.
    
    Auto-generates standup updates from commits, PRs, and work item changes.
    Tracks journal entries for work not in ADO. Surfaces blockers with escalation recommendations.
    
    Prerequisites:
    - Azure CLI with devops extension: az extension add --name azure-devops
    - Authenticated: az login
    - Optional: .amplifier/scrum-config.yaml for team rituals

includes:
  - bundle: foundation

agents:
  include:
    - ado-scrum:agents/ado-scrum-helper

context:
  include:
    - ado-scrum:context/scrum-config-schema.md
    - ado-scrum:context/scrum-workflow.md

tools:
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@v1.0.0
---

# ADO Scrum Bundle

Standup generation and journal tracking for Azure DevOps workflows.

## Quick Start

```bash
# Generate today's standup
"generate my standup"

# Add journal entry
"add journal entry: synced with platform team on auth approach"

# Check blockers
"what's blocking me?"
```

## Configuration

Create `.amplifier/scrum-config.yaml` for team-specific settings:

```yaml
version: 1
recurring:
  - name: "Sprint planning"
    schedule: "biweekly/monday"
    tags: [scrum]

standup:
  include_journal: true
  include_blockers: true
  escalation_threshold_hours: 24
```
