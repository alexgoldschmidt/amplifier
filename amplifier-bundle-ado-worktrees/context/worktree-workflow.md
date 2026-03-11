# Worktree Development Workflow

You are operating in **local worktree mode** — isolated git checkouts for parallel work item development.

## Execution Model

| Aspect | Worktree Reality |
|--------|------------------|
| Execution | Local machine (user's terminal) |
| Git access | Full local git + worktrees |
| Filesystem | Full access to worktree directory |
| User interaction | Direct Amplifier session |
| Work item updates | Via az devops CLI |

## vs SWE Agent Mode

| Worktree Mode | SWE Agent Mode |
|---------------|----------------|
| Runs locally | Runs on GitHub cloud |
| Full git access | PR comments only |
| Can continue existing PRs | Only unstarted work |
| Manual commits/pushes | Automated PR creation |
| Any tooling available | Limited to SWE agent tools |

## When to Use Worktrees

Use worktrees when you need to:
- Work on multiple ADO work items simultaneously
- Keep context-switching overhead to zero
- Continue work on existing PRs
- Use local tooling not available to SWE agents
- Debug complex issues requiring local environment

## State Tracking

All state is tracked in ADO via work item tags. No local state files.

### Execution Tags

| Tag | Meaning |
|-----|---------|
| `execution:worktree` | Being worked locally via Amplifier worktree |
| `execution:swe-agent` | Being worked by GitHub Copilot SWE Agent |
| `execution:manual` | Being worked manually (no automation) |

### Why Tags Matter

- **Prevents conflicts** — SWE Agent won't pick up items tagged `execution:worktree`
- **Visibility** — Team can see who's working on what via ADO queries
- **Cleanup tracking** — Know which worktrees to remove after merge

## Workflow

### Starting a Worktree Session

1. Ask coordinator: "What work items can I start?"
2. Pick an item from the list
3. Coordinator creates worktree + tags ADO
4. Open new terminal in worktree directory
5. Run `amplifier run`
6. Work on the item in that session

### During Development

- Commit and push normally
- Create PR when ready (link to work item)
- Work item PR link is added automatically by ADO

### Finishing

When PR is merged:
1. Come back to main repo terminal
2. Ask coordinator to clean up worktree
3. Tag is removed, worktree deleted, branch cleaned up

## Directory Layout

Recommended sibling layout:

```
/path/to/repo              (main checkout)
/path/to/repo-wi-12345     (worktree for work item 12345)
/path/to/repo-wi-67890     (worktree for work item 67890)
```

## Key Constraint

**Don't interfere with SWE Agent work.** If a work item has `execution:swe-agent` tag,
it's being actively worked by GitHub Copilot. Either:
- Wait for SWE Agent to finish
- Reassign the work item to yourself (removes SWE Agent assignment)

## Quick Reference

```bash
# List worktrees
git worktree list

# Create worktree for work item
git worktree add ../repo-wi-<ID> -b wi-<ID>/description main

# Remove worktree after merge
git worktree remove ../repo-wi-<ID>
git branch -d wi-<ID>/description
git worktree prune
```
