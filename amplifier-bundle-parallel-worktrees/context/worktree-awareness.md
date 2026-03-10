# Parallel Worktree Development

You have access to parallel worktree orchestration for multi-branch development.

## When to Use

- Working on multiple features simultaneously
- Need branch isolation without stashing/switching
- Running parallel Amplifier sessions on different features
- Features may have overlapping file changes

## Capability

Delegate to `parallel-worktrees:agents/worktree-orchestrator` for:
- Creating worktree layouts for parallel feature work
- Coordinating rebase/merge strategies for overlapping changes
- Cleanup after features are merged

## Quick Reference

```bash
# List worktrees
git worktree list

# Create worktree for existing branch
git worktree add ../repo-feature feature-branch

# Create worktree with new branch
git worktree add -b new-feature ../repo-new-feature master

# Remove worktree
git worktree remove ../repo-feature
```

## Key Insight

Worktrees solve "I can't switch branches" — they don't prevent merge conflicts. Conflicts resolve at integration time via rebase before the second PR.
