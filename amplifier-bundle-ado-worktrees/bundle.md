---
bundle:
  name: ado-worktrees
  version: 1.0.0
  description: |
    Local parallel development using git worktrees, coordinated via ADO work items.
    
    Enables running multiple Amplifier sessions on different work items simultaneously,
    with state tracked in Azure DevOps.
    
    Use this mode when:
    - Working on multiple work items at once
    - Continuing work on items with existing PRs
    - Need full local tooling access


includes:
  # Foundation provides core tools (bash, filesystem, etc.)
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/alexgoldschmidt/amplifier@master#subdirectory=amplifier-bundle-ado-work-items

agents:
  include:
    - ado-worktrees:agents/worktree-coordinator

context:
  include:
    - ado-worktrees:context/worktree-workflow.md
---

# ADO Worktrees Bundle

Local parallel development via git worktrees, coordinated with Azure DevOps work items.

## When to Use

| Use Worktrees When | Use SWE Agent When |
|--------------------|-------------------|
| Need full local tooling | Task is well-scoped, no special tools needed |
| Continuing existing PR work | Starting fresh (no PR exists) |
| Multiple items simultaneously | Single item, fire-and-forget |
| Complex debugging required | Straightforward implementation |

## vs SWE Agent Mode

| Aspect | Worktrees | SWE Agent |
|--------|-----------|-----------|
| Execution | Local machine | Remote cloud |
| Interaction | Direct development | PR comments only |
| Eligible items | Any assigned to you | Unstarted only |
| Can resume | Yes (continue existing PRs) | No (creates new PRs) |

## Key Agent

- `worktree-coordinator` — Creates worktrees, tags work items, tracks status

## Workflow

1. **Discover** — Query ADO for work items assigned to you
2. **Create worktree** — Isolated checkout for the work item
3. **Tag in ADO** — Mark item with `execution:worktree`
4. **Run Amplifier** — cd to worktree, start session
5. **Cleanup** — After PR merge, remove worktree and tag
