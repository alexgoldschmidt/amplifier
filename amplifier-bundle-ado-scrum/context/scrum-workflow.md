# Scrum Workflow

## Standup Generation Flow

```
1. Bootstrap ADO context (org, project from git remote)
2. Query commits → filter by author + last 24h
3. Query PRs → filter by creator + last 24h  
4. Query WI changes → filter by @Me + last 24h
5. Read journal entries → filter by yesterday/today
6. Read recurring items → filter by today's schedule
7. Detect blockers → apply threshold from config
8. Format and present
```

## Journal Entry Flow

```
1. User provides entry text
2. Auto-detect tags from keywords (optional)
3. Read existing scrum-journal.yaml
4. Append entry with today's date
5. Write file
6. Confirm to user
```

## Blocker Detection Logic

| Condition | Recommendation |
|-----------|----------------|
| PR waiting > threshold | "Ping @reviewer" |
| PR waiting > 2x threshold | "Escalate to @lead" |
| WI stuck > 3 days | "Update status or add blocked tag" |
| Pipeline failed | "Check logs, may need fix" |

## Integration with ADO

Uses standard ADO CLI commands:
- `az repos commit list` — commit history
- `az repos pr list` — PR status
- `az boards query` — work item queries (WIQL)
- `az pipelines runs list` — pipeline status
