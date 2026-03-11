# Team and Iteration Discovery

Team context is required for accurate work item discovery. Both `@CurrentIteration` resolution and area path scoping are team-specific.

## Why Team Context Matters

In Azure DevOps:
- Different teams can be in different sprints (iterations)
- Different teams own different area paths
- `@CurrentIteration` resolves to the team's active sprint, not a global value

Without explicit team context, queries may return unexpected results.

## Configuration

Set team context in `.amplifier/ado-team-config.yaml`:

```yaml
ado:
  team: "Your Team Name"              # REQUIRED for @CurrentIteration
  area-path: "Project\\TeamArea"      # Team's owned area path
  iteration-path: "@CurrentIteration" # Uses team's current sprint
```

## Get Current Iteration for Team

```bash
TEAM="Your Team Name"

# Get current iteration
az boards iteration team list \
  --team "$TEAM" \
  --timeframe current \
  -o json | jq '.[0]'
```

Returns:
```json
{
  "id": "abc123",
  "name": "Sprint 42",
  "path": "Project\\Sprint 42",
  "attributes": {
    "startDate": "2026-03-01",
    "finishDate": "2026-03-14",
    "timeFrame": "current"
  }
}
```

## List All Iterations for Team

```bash
# Past, current, and future sprints
az boards iteration team list --team "$TEAM" -o table

# Just current and future
az boards iteration team list --team "$TEAM" --timeframe current -o table
```

## Team Discovery

If team name is not configured:

```bash
# List all teams in project
az devops team list -o table

# Get default team
az devops project show -o json | jq '.defaultTeam.name'

# List teams you're a member of
az devops team list-member --team "<team>" -o table
```

## Area Path Discovery

Get area paths assigned to a team:

```bash
az boards area team list --team "$TEAM" -o table
```

## Bootstrap Sequence

When team context is needed:

1. **Check config** — read `ado.team` from `.amplifier/ado-team-config.yaml`
2. **If missing** — try to detect from project's default team
3. **If ambiguous** — prompt user to specify team
4. **Cache team's iteration** — resolve `@CurrentIteration` to actual path
5. **Cache team's areas** — get assigned area paths

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Wrong sprint items returned | No team specified | Set `ado.team` in config |
| `@CurrentIteration` returns nothing | Team not set up for iterations | Check team board settings |
| Area path access denied | User not member of team | Verify team membership |

## REST API Fallback

If CLI commands fail, use REST API:

```bash
# Get team settings (includes iteration and area config)
az rest --method get \
  --resource "499b84ac-1321-427f-aa17-267ca6975798" \
  --uri "https://dev.azure.com/{org}/{project}/{team}/_apis/work/teamsettings?api-version=7.1"
```
