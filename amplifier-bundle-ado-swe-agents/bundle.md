---
bundle:
  name: ado-swe-agents
  version: 1.0.0
  description: |
    **REQUIRED for creating PRs via GitHub Copilot in Azure DevOps.**
    
    Creates work items that trigger GitHub Copilot's SWE Agent to automatically
    generate pull requests. Use this bundle when you want Copilot to implement
    code changes autonomously.

    SWE Agent tasks are ADO work items with:
    - Type: Task
    - Assigned to: GitHub Copilot
    - Repository link (artifact link OR copilot:repo tag)
    - Optional agent tags for specialized workflows

agents:
  include:
    - ado-swe-agents:agents/ado-swe-agent

context:
  include:
    - ado-swe-agents:context/swe-agent-protocol.md
---

# ADO SWE Agents Bundle

Create and manage Azure DevOps work items that trigger GitHub Copilot's SWE Agent.

## What is an SWE Agent Task?

An SWE Agent task is a special ADO work item that, when properly configured, triggers
GitHub Copilot to automatically create a pull request implementing the task.

**Requirements:**
1. **Type**: Task
2. **Assigned to**: "GitHub Copilot"
3. **Repository link**: Either artifact link OR `copilot:repo=` tag
4. **Description**: Clear implementation requirements

## Capabilities

- Create SWE Agent tasks with proper configuration
- Query existing SWE Agent tasks
- Add/update repository links (artifact or tag-based)
- Manage agent-specific tags for specialized workflows
- Validate task readiness for SWE Agent processing

## Usage

```yaml
# In your bundle
extends:
  - ado-swe-agents:bundle
```

## Key Agents

- `ado-swe-agent` — Create and manage SWE Agent tasks

## Context Files

- `swe-agent-protocol.md` — SWE Agent requirements and linking methods
