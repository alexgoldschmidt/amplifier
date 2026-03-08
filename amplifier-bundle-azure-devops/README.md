# Azure DevOps Bundle for Amplifier

Integrate Azure DevOps into your Amplifier workflows.

## Features

- **Work Items**: Create, query (WIQL), update, and link work items
- **Pipelines**: Trigger runs, monitor status, retrieve logs
- **Repos**: Manage PRs, branches, code review workflows
- **Boards**: Sprint planning, backlog management, iterations

## Prerequisites

```bash
# Install Azure CLI devops extension
az extension add --name azure-devops

# Login and configure defaults
az login
az devops configure --defaults organization=https://dev.azure.com/YOURORG project=YOURPROJECT

# Verify
az devops project show
```

## Installation

Add to your bundle:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-azure-devops@main
```

Or include just the behavior:

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-azure-devops@main#subdirectory=behaviors/azure-devops.yaml
```

## Available Agents

| Agent | Use For |
|-------|---------|
| `azure-devops:agents/ado-work-items` | Work item CRUD, WIQL queries, linking |
| `azure-devops:agents/ado-pipelines` | Pipeline triggers, monitoring, logs |
| `azure-devops:agents/ado-repos` | PRs, branches, code review |
| `azure-devops:agents/ado-boards` | Sprints, backlog, iterations |

## Usage Examples

Delegate to the appropriate agent:

```
"Create a bug for the login issue"
→ delegates to ado-work-items

"Trigger the CI pipeline on the feature branch"
→ delegates to ado-pipelines

"Create a PR from feature/auth to main"
→ delegates to ado-repos

"What's in the current sprint?"
→ delegates to ado-boards
```

## Design

This bundle uses the `az devops` CLI (no Python SDK dependency). Agents inherit `tool-bash` from the parent bundle and execute CLI commands directly.

Authentication relies on existing `az login` session. Run `az devops configure` to set defaults.

## License

MIT
