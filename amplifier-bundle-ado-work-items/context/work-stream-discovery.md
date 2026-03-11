# Work Stream Discovery

Discovery queries for parallel work stream management. Used by both SWE Agent and Worktree execution modes.

## Execution Mode Tags

Work items are tagged to indicate how they're being worked:

| Tag | Meaning |
|-----|---------|
| `execution:swe-agent` | Being worked by GitHub Copilot SWE Agent (remote) |
| `execution:worktree` | Being worked locally via Amplifier worktree session |
| `execution:manual` | Being worked manually (no automation) |

## Prerequisites

Discovery queries require team context. Ensure `.amplifier/ado-team-config.yaml` has:

```yaml
ado:
  team: "Your Team Name"        # REQUIRED for @CurrentIteration
  area-path: "Project\\TeamArea"  # Scopes to team's areas
```

Without team context, `@CurrentIteration` uses project defaults which may be incorrect.

## SWE Agent Candidates (Unstarted Only)

Work items eligible for SWE Agent pickup:
- In team's current sprint
- In team's area path
- No PR link attached
- No `execution:worktree` or `execution:manual` tag
- State = "New" or "Active"

```sql
SELECT [System.Id], [System.Title], [System.WorkItemType], [System.Tags]
FROM WorkItems
WHERE [System.IterationPath] = @CurrentIteration
  AND [System.AreaPath] UNDER 'Project\TeamArea'
  AND [System.State] IN ('New', 'Active')
  AND [System.WorkItemType] IN ('Task', 'Bug')
  AND NOT [System.Tags] CONTAINS 'execution:worktree'
  AND NOT [System.Tags] CONTAINS 'execution:manual'
ORDER BY [Microsoft.VSTS.Common.Priority]
```

**Post-query filter:** Check each item for PR links via API — items with PRs are NOT eligible.

```bash
# Check if work item has linked PR
az boards work-item relation list --id <ID> \
  --query "[?attributes.name=='Pull Request'].url" -o tsv
```

## Worktree Candidates (Any Assigned to Me)

Work items I can work on locally (can resume existing work):
- Assigned to me
- Any state except Closed/Resolved
- May or may not have PR (worktrees can continue existing PRs)
- Not being worked by SWE Agent

```sql
SELECT [System.Id], [System.Title], [System.WorkItemType], [System.Tags]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.AreaPath] UNDER 'Project\TeamArea'
  AND [System.State] NOT IN ('Closed', 'Resolved')
  AND NOT [System.Tags] CONTAINS 'execution:swe-agent'
ORDER BY [Microsoft.VSTS.Common.Priority]
```

## All Active Work Streams

Show all work items currently being worked (any execution mode):

```sql
SELECT [System.Id], [System.Title], [System.Tags], [System.State]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.Tags] CONTAINS 'execution:'
ORDER BY [System.ChangedDate] DESC
```

## Setting Execution Mode

When starting work on an item, tag it:

```bash
# Mark as SWE Agent work
az boards work-item update --id <ID> \
  --fields "System.Tags=execution:swe-agent"

# Mark as worktree work  
az boards work-item update --id <ID> \
  --fields "System.Tags=execution:worktree"
```

**Append to existing tags:**
```bash
# Get current tags
CURRENT_TAGS=$(az boards work-item show --id <ID> \
  --query "fields.\"System.Tags\"" -o tsv)

# Append new tag
az boards work-item update --id <ID> \
  --fields "System.Tags=${CURRENT_TAGS}; execution:worktree"
```

## PR Link Detection

Check if a work item has a linked PR:

```bash
az boards work-item relation list --id <ID> \
  --query "[?attributes.name=='Pull Request']" -o json
```

Returns empty array `[]` if no PR linked.

## State Transitions

```
┌─────────────────┐
│   Unstarted     │ ← No PR link, no execution:* tag
│  (Eligible for  │
│   SWE Agent)    │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐  ┌────────┐
│  SWE   │  │Worktree│
│ Agent  │  │        │
│ Tagged │  │ Tagged │
└────┬───┘  └────┬───┘
     │           │
     ▼           ▼
   PR Created  PR Created
     │           │
     └─────┬─────┘
           ▼
      ┌────────┐
      │  Done  │ ← PR merged, work item resolved
      └────────┘
```

## Key Constraint

**SWE Agent can only pick up unstarted items** — no PR, no `execution:worktree` tag.

**Worktrees can pick up any item assigned to you** — including items with existing PRs you want to continue.
