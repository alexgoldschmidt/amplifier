---
bundle:
  name: ado-pr
  version: 1.0.0
  description: |
    Azure DevOps pull request lifecycle management. Composes with ado-work-items
    for complete PR + work item workflows.

    Includes: PR creation, discovery, comment review, work item linking.

includes:
  - bundle: ../amplifier-bundle-ado-work-items/bundle.md
  - bundle: ado-pr:behaviors/ado-pr

tools:
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@v1.0.0
---

# ADO PR Bundle

Azure DevOps pull request lifecycle management for Amplifier sessions.

## Capabilities

- Create draft PRs for current branch
- Discover and track existing PRs
- Review and respond to PR comments
- Link work items to PRs (composes ado-work-items)
- AI-generated comment indicators

## Usage

```yaml
# In your bundle
extends:
  - ado-pr:bundle
```

This automatically includes `ado-work-items` for work item management.

## Key Agents

- `ado-pr-manager` — Full PR lifecycle (create, discover, comments, WI linking)

## Context Files

- `ado-pr-comments-api.md` — REST API for PR threads and comments
- Inherits auth, bootstrap, templates from `ado-work-items`
