# Azure DevOps CLI Reference

Quick reference for `az devops` and `az boards` commands.

## Setup

```bash
# Install extension
az extension add --name azure-devops

# Configure defaults
az devops configure --defaults organization=https://dev.azure.com/YOURORG project=YOURPROJECT

# Verify
az devops project show
```

## Output Formats

| Flag | Use |
|------|-----|
| `-o json` | Parsing (default) |
| `-o table` | Human-readable |
| `-o tsv` | Tab-separated |
| `-o yaml` | YAML format |

## JMESPath Queries

```bash
# Single field
--query "id"

# Multiple fields
--query "{id:id, title:fields.\"System.Title\"}"

# Array filter
--query "[?status=='active']"

# First item
--query "[0]"
```

## Common Commands

### Work Items (`az boards`)

| Command | Description |
|---------|-------------|
| `az boards work-item create --type TYPE --title "..."` | Create item |
| `az boards work-item show --id ID` | Get item |
| `az boards work-item update --id ID --state STATE` | Update item |
| `az boards work-item delete --id ID --yes` | Delete item |
| `az boards query --wiql "..."` | WIQL query |
| `az boards work-item relation add --id ID --relation-type TYPE --target-id TID` | Link items |

### Pipelines (`az pipelines`)

| Command | Description |
|---------|-------------|
| `az pipelines list` | List pipelines |
| `az pipelines run --name NAME` | Trigger run |
| `az pipelines runs list --pipeline-name NAME` | List runs |
| `az pipelines runs show --id ID` | Get run details |

### Repos (`az repos`)

| Command | Description |
|---------|-------------|
| `az repos list` | List repos |
| `az repos pr create --title "..." --source-branch SRC --target-branch TGT` | Create PR |
| `az repos pr list --status active` | List PRs |
| `az repos pr show --id ID` | Get PR details |
| `az repos pr set-vote --id ID --vote approve` | Vote on PR |
| `az repos ref list --filter heads/` | List branches |

### Boards (`az boards iteration/area`)

| Command | Description |
|---------|-------------|
| `az boards iteration team list --team TEAM` | List sprints |
| `az boards iteration team list-work-items --team TEAM --id SPRINT` | Sprint items |
| `az boards area team list --team TEAM` | List areas |

## REST API Fallback

For operations CLI doesn't cover:

```bash
az rest --method GET --uri "https://dev.azure.com/{org}/{project}/_apis/..."

az rest --method POST --uri "..." --body '{"key": "value"}'

az rest --method PATCH --uri "..." --body '{"status": "cancelling"}'
```

Common API endpoints:
- Build logs: `/_apis/build/builds/{id}/logs?api-version=7.1`
- Capacity: `/{team}/_apis/work/teamsettings/iterations/{id}/capacities?api-version=7.1`
- PR threads: `/_apis/git/repositories/{repo}/pullRequests/{pr}/threads?api-version=7.1`
