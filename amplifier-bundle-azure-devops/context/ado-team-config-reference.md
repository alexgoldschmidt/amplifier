# Azure DevOps Team Configuration Reference

Teams can customize PR and work item workflows by creating `.amplifier/ado-team-config.yaml` in their repository.

**Important:** This config specifies team *preferences*. Available work item types and fields come from the **process cache** (discovered via bootstrap). If you reference a type or field not in your org's process, the agent will warn.

## Two Configuration Layers

| Layer | Source | Contains |
|-------|--------|----------|
| **Process cache** | ADO API discovery | What's *possible* (types, fields, hierarchy) |
| **Team config** | `.amplifier/ado-team-config.yaml` | What's *preferred* (defaults, templates) |

See `ado-bootstrap-protocol.md` for how discovery works.

## Quick Start

Create `.amplifier/ado-team-config.yaml` in your repo root:

```yaml
ado:
  work-item:
    default-type: "<TYPE_FROM_YOUR_PROCESS>"  # Must exist in process cache
    required-fields:
      - description
      - assigned-to
  pr:
    default-draft: true
    require-work-item: true
```

**No config file?** The agent uses process cache to determine valid types and prompts interactively.

## Full Schema

```yaml
# .amplifier/ado-team-config.yaml
ado:
  # Work item configuration
  work-item:
    default-type: "<TYPE>"      # Must exist in your process (check cache)
    required-fields:            # Fields agent MUST prompt for if missing
      - description             # Use field keys from process cache
      - assigned-to
    type-overrides:             # Additional requirements by work item type
      "<TYPE_A>":               # Type must exist in your process
        required-fields:
          - "<field-key>"
      "<TYPE_B>":
        required-fields:
          - "<field-key>"

  # PR configuration
  pr:
    default-draft: true         # Create PRs as draft by default
    title-prefix: ""            # Prepended to all PR titles, e.g., "[TEAM-X]"
    description-template: |     # Markdown template for PR descriptions
      ## Summary
      {summary}

      ## Testing
      - [ ] Unit tests pass
      - [ ] Manual verification

      ## Work Items
      Resolves #{work_item_id}
    require-work-item: true     # true = block PR without WI, false = warn only

  # Branch naming convention (informational, not enforced)
  branch:
    pattern: "{type}/{id}-{slug}"  # e.g., feature/12345-add-auth
    types: [feature, bugfix, hotfix, chore]

  # Default area/iteration paths for new work items
  area-path: ""                 # e.g., "Project\\Team Alpha"
  iteration-path: ""            # e.g., "Project\\Sprint 42" or "@CurrentIteration"

  # Work item templates
  templates:
    dir: .amplifier/ado-templates  # directory containing templates
    require: false                  # true = warn if no template for type
```

## Defaults (When No Config Exists)

| Setting | Default |
|---------|---------|
| `work-item.default-type` | Task |
| `work-item.required-fields` | [description, assigned-to] |
| `pr.default-draft` | true |
| `pr.require-work-item` | false (warn only) |
| `pr.title-prefix` | "" (none) |
| `branch.pattern` | none (no enforcement) |
| `area-path` | "" (project default) |
| `iteration-path` | "" (project default) |
| `templates.dir` | .amplifier/ado-templates |
| `templates.require` | false |

## Field Reference

**Available fields come from your process cache, not this table.** The cache is populated by the bootstrap protocol from your org's actual process template.

To see available fields for a type:
```bash
cat ~/.amplifier/ado-cache/{org}/{project}/process.yaml | grep -A 50 "YourType:"
```

### Common Field Keys (May Vary by Org)

These are *common* field keys seen in standard processes. Your org may have different or additional fields:

| Field Key | Typical API Path | Notes |
|-----------|------------------|-------|
| `description` | System.Description | Usually all types |
| `assigned-to` | System.AssignedTo | Usually all types |
| `start-date` | Microsoft.VSTS.Scheduling.StartDate | Scheduling types |
| `due-date` | Microsoft.VSTS.Scheduling.DueDate | Scheduling types |
| `priority` | Microsoft.VSTS.Common.Priority | Prioritized types |

**Check your process cache for the definitive list of fields per type.**

### Template Variables for PR Description

| Variable | Value |
|----------|-------|
| `{summary}` | First line of most recent commit message |
| `{work_item_id}` | Linked work item ID (if any) |
| `{branch}` | Current branch name |
| `{author}` | Git config user.name |

## Example Configurations

### Minimal Team (Just Works)

No config file needed. Defaults apply.

### Scrum Team with Strict Standards

```yaml
ado:
  work-item:
    default-type: "User Story"
    required-fields:
      - description
      - assigned-to
      - start-date
      - due-date
      - acceptance-criteria
      - priority
  pr:
    require-work-item: true
    title-prefix: "[Pricing]"
    description-template: |
      ## Summary
      {summary}

      ## Acceptance Criteria
      See linked work item.

      ## Testing
      - [ ] Unit tests
      - [ ] Integration tests
      - [ ] Manual QA

      ## Work Items
      Resolves AB#{work_item_id}
  area-path: "OnePrice\\Pricing Team"
  iteration-path: "@CurrentIteration"
```

### Bug-Fix Focused Team

```yaml
ado:
  work-item:
    default-type: Bug
    required-fields:
      - description
      - assigned-to
      - repro-steps
      - priority
  pr:
    require-work-item: true
    default-draft: false
```

### Task-Heavy Engineering Team

```yaml
ado:
  work-item:
    default-type: Task
    required-fields:
      - description
      - assigned-to
      - remaining-work
      - original-estimate
    type-overrides:
      Task:
        required-fields:
          - remaining-work
          - original-estimate
  pr:
    default-draft: true
    require-work-item: false
```

## How Agents Use Config

1. **ado-pr-manager** reads config at the start of any lifecycle operation
2. If `.amplifier/ado-team-config.yaml` exists, it's parsed and applied
3. If missing, defaults are used
4. Config values drive:
   - Whether to block or warn when no work item is linked
   - Which fields to prompt for when auditing work items
   - PR title prefix and description template
   - Default work item type when creating new items

## Config Location

The config file must be at:
```
<repo-root>/.amplifier/ado-team-config.yaml
```

The agent finds it using:
```bash
CONFIG_PATH="$(git rev-parse --show-toplevel)/.amplifier/ado-team-config.yaml"
```

## Validation

When config references types or fields:

1. **Agent checks process cache** for validity
2. **If type not in cache**: Warn "Type 'X' not found in process cache. Run bootstrap refresh."
3. **If field not in cache for type**: Warn "Field 'X' not valid for type 'Y'."

The agent continues but may not enforce invalid config entries.

## Future Considerations

- **Inheritance**: Org-level → project-level → repo-level config merging (not yet implemented)
- **Branch Enforcement**: Actually validate branch naming patterns
