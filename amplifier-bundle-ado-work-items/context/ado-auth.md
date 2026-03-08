# Azure DevOps Authentication

## CRITICAL: Pre-Flight Auth Check

**Before executing ANY `az` CLI command, verify authentication:**

```bash
# Check auth status (silent success, clear failure)
if ! az account show --query "name" -o tsv >/dev/null 2>&1; then
    echo "ERROR: Not logged in to Azure CLI. Run: az login"
    exit 1
fi
```

If auth fails, **STOP** — do not attempt any `az devops` commands. Inform the user:

```bash
# Standard login
az login

# Headless/WSL environments
az login --use-device-code
```

## Initial Setup

```bash
# 1. Install Azure DevOps extension
az extension add --name azure-devops

# 2. Login to Azure
az login

# 3. Configure defaults (optional — bootstrap protocol auto-detects from git remote)
az devops configure --defaults organization=https://dev.azure.com/YOURORG project=YOURPROJECT

# 4. Verify
az devops project show
```

## Verify Configuration

```bash
# Show current defaults
az devops configure --list

# Test access
az boards work-item show --id 1  # any valid work item ID
```

## Troubleshooting

### "You are not authorized"

```bash
# Re-login
az logout
az login

# Or use device code flow
az login --use-device-code
```

### "Project not found"

```bash
# List available projects
az devops project list -o table

# Set correct project
az devops configure --defaults project=CorrectProjectName
```

### Using Personal Access Token (PAT)

If Azure CLI auth doesn't work:

```bash
# Set PAT in environment
export AZURE_DEVOPS_EXT_PAT=your-pat-token

# Or login with PAT
echo $AZURE_DEVOPS_PAT | az devops login --organization https://dev.azure.com/YOURORG
```

PAT needs scopes:
- Work Items: Read & Write
- Code: Read & Write
- Build: Read & Execute
- Project and Team: Read

## Multiple Organizations

```bash
# Switch organization
az devops configure --defaults organization=https://dev.azure.com/OTHERORG

# Or specify per-command
az boards work-item show --id 123 --org https://dev.azure.com/OTHERORG
```

## Azure AD Token Authentication

For REST API calls, on-premises ADO, or restricted environments.

### Get Azure AD Token for ADO

```bash
# ADO resource ID (constant for all Azure DevOps)
ADO_RESOURCE_ID="499b84ac-1321-427f-aa17-267ca6975798"

# Get token
TOKEN=$(az account get-access-token --resource $ADO_RESOURCE_ID --query accessToken -o tsv)
```

### Using Token with REST API

```bash
# Use with az rest (recommended)
az rest --method get \
  --resource "499b84ac-1321-427f-aa17-267ca6975798" \
  --uri "https://dev.azure.com/{org}/_apis/projects?api-version=7.1"

# Or with curl
TOKEN=$(az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://dev.azure.com/{org}/{project}/_apis/pipelines?api-version=7.1"
```

### When to Use Which Auth Method

| Scenario | Auth Method |
|----------|-------------|
| Cloud ADO with CLI | `az devops` commands (simplest) |
| Cloud ADO REST API | `az rest` with `--resource` flag |
| On-premises ADO Server | Azure AD token (if federated) or PAT |
| CI/CD automation | PAT or service principal token |
| Restricted environments | Azure AD token with device code flow |

### Token Refresh

Azure AD tokens expire after ~1 hour. For long-running scripts:

```bash
get_ado_token() {
  az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv
}

TOKEN=$(get_ado_token)
# ... make API calls ...
```
