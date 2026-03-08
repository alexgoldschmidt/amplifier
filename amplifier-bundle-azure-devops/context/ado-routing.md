# ADO Agent Routing Guide

When working with Azure DevOps, **delegate to the appropriate agent** rather than using raw `az` CLI commands directly. Each agent carries domain expertise, error handling, and best practices.

## Agent Selection Matrix

| Task | Delegate To | NOT This |
|------|-------------|----------|
| Create/discover/update PRs | `ado-pr-manager` | `az repos pr` |
| PR comments and threads | `ado-pr-manager` | `az rest` to PR threads API |
| Resolve merge conflicts | `ado-pr-manager` | manual git + az commands |
| Work item CRUD | `ado-work-items` | `az boards work-item` |
| WIQL queries | `ado-work-items` | `az boards query` |
| Sprint/iteration management | `ado-boards` | `az boards iteration` |
| Backlog and capacity | `ado-boards` | `az rest` to boards API |
| Pipeline runs and logs | `ado-pipelines` | `az pipelines` |
| Branch operations | `ado-repos` | `az repos ref` |
| Repository listing | `ado-repos` | `az repos list` |

## Why Delegation Matters

1. **Bootstrap protocol** — Agents run auth checks and cache validation automatically
2. **Process awareness** — Agents use the cached process template for valid work item types
3. **Team config** — Agents respect `.amplifier/ado-team-config.yaml` for defaults
4. **Error handling** — Agents know ADO API quirks (empty responses, rate limits, etc.)
5. **Consistency** — AI-generated comments include `🤖 [Amplifier]` prefix

## Quick Reference

```
"create a PR"           → ado-pr-manager
"check PR comments"     → ado-pr-manager  
"create a work item"    → ado-work-items
"what's in my sprint"   → ado-boards
"run the CI pipeline"   → ado-pipelines
"list branches"         → ado-repos
```

## Anti-Pattern: Direct CLI Usage

❌ **Don't do this:**
```bash
az repos pr list --org ... --project ... --status active
az boards work-item create --type Task --title "..."
```

✅ **Do this instead:**
```
delegate to ado-pr-manager: "list active PRs for current branch"
delegate to ado-work-items: "create a Task titled '...'"
```

The agents handle org/project detection, auth, and process validation automatically.
