---
bundle:
  name: parallel-worktrees
  version: 1.0.0
  description: |
    Parallel git worktree orchestration for multi-branch development.
    Enables running separate Amplifier sessions on different feature branches
    from the same repository.

agents:
  include:
    - parallel-worktrees:agents/worktree-orchestrator

context:
  include:
    - parallel-worktrees:context/worktree-awareness.md
---

# Parallel Worktrees Bundle

Git worktree orchestration for simultaneous multi-branch development.

## When to Use

- Working on multiple features simultaneously
- Need branch isolation without stashing/switching
- Running parallel Amplifier sessions on different features

## Agent

| Agent | Use For |
|-------|---------|
| `worktree-orchestrator` | Creating, managing, and cleaning up worktree layouts |

## Quick Start

```bash
# Create worktree for a feature branch
git worktree add ../repo-feature feature-branch

# List worktrees
git worktree list

# Remove worktree after merge
git worktree remove ../repo-feature
```
