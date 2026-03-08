# WIQL Reference (Work Item Query Language)

Azure DevOps uses WIQL for querying work items.

## Basic Syntax

```sql
SELECT [Field1], [Field2]
FROM WorkItems
WHERE [Condition]
ORDER BY [Field]
```

## Common Fields

| Field | Description |
|-------|-------------|
| `[System.Id]` | Work item ID |
| `[System.Title]` | Title |
| `[System.State]` | State (New, Active, Closed) |
| `[System.AssignedTo]` | Assigned user |
| `[System.WorkItemType]` | Type (Bug, Task, User Story) |
| `[System.IterationPath]` | Sprint/iteration |
| `[System.AreaPath]` | Area path |
| `[System.CreatedDate]` | Created date |
| `[System.ChangedDate]` | Last modified |
| `[Microsoft.VSTS.Common.Priority]` | Priority (1-4) |
| `[Microsoft.VSTS.Scheduling.StoryPoints]` | Story points |
| `[Microsoft.VSTS.Scheduling.RemainingWork]` | Remaining hours |

## Macros

| Macro | Meaning |
|-------|---------|
| `@Me` | Current user |
| `@Today` | Today's date |
| `@CurrentIteration` | Active sprint |
| `@project` | Current project |

## Example Queries

### My Active Items

```sql
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.State] <> 'Closed'
ORDER BY [Microsoft.VSTS.Common.Priority]
```

### Current Sprint Items

```sql
SELECT [System.Id], [System.Title], [System.AssignedTo]
FROM WorkItems
WHERE [System.IterationPath] = @CurrentIteration
ORDER BY [Microsoft.VSTS.Common.BacklogPriority]
```

### Bugs by Priority

```sql
SELECT [System.Id], [System.Title], [Microsoft.VSTS.Common.Priority]
FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
  AND [System.State] <> 'Closed'
ORDER BY [Microsoft.VSTS.Common.Priority] ASC
```

### Recent Changes (Last 7 Days)

```sql
SELECT [System.Id], [System.Title], [System.ChangedDate]
FROM WorkItems
WHERE [System.ChangedDate] > @Today - 7
ORDER BY [System.ChangedDate] DESC
```

### Unassigned Items

```sql
SELECT [System.Id], [System.Title]
FROM WorkItems
WHERE [System.AssignedTo] = ''
  AND [System.State] = 'New'
```

### Items Without Estimates

```sql
SELECT [System.Id], [System.Title]
FROM WorkItems
WHERE [System.WorkItemType] = 'User Story'
  AND [Microsoft.VSTS.Scheduling.StoryPoints] = ''
  AND [System.State] <> 'Closed'
```

### High Priority in Current Sprint

```sql
SELECT [System.Id], [System.Title], [System.AssignedTo]
FROM WorkItems
WHERE [System.IterationPath] = @CurrentIteration
  AND [Microsoft.VSTS.Common.Priority] <= 2
ORDER BY [Microsoft.VSTS.Common.Priority]
```

### Items by Area

```sql
SELECT [System.Id], [System.Title]
FROM WorkItems
WHERE [System.AreaPath] UNDER 'Project\Area1'
  AND [System.State] <> 'Closed'
```

## CLI Usage

```bash
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.AssignedTo] = @Me"
```

## Tips

- Field names are case-sensitive
- Use single quotes for string values
- `UNDER` matches path and children
- `=` for exact iteration match
- Date math: `@Today - 7` for 7 days ago
