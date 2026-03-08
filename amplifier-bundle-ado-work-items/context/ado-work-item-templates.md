# Azure DevOps Work Item Templates

The ADO bundle supports **per-type work item templates** for structured, consistent work item creation.

## Overview

Templates define required sections for work items. When creating a work item, the agent:
1. Loads the template for that type
2. Prompts user to fill each section
3. Formats sections into the appropriate ADO fields

## Template Location

Templates live in `.amplifier/ado-templates/` at the repo root:

```
.amplifier/ado-templates/
├── task.md
├── bug.md
├── product-backlog-item.md
├── feature.md
├── user-story.md
├── epic.md
└── _default.md  # fallback for unconfigured types
```

## Template Naming

Template filename = work item type name, lowercase, hyphenated:

| Work Item Type | Template File |
|----------------|---------------|
| Task | `task.md` |
| Bug | `bug.md` |
| Product Backlog Item | `product-backlog-item.md` |
| User Story | `user-story.md` |
| Feature | `feature.md` |
| Key Result | `key-result.md` |
| Any other type | `_default.md` (fallback) |

## Template Selection Logic

When creating a work item of type `X`:

1. Check for `.amplifier/ado-templates/{x-slug}.md`
2. If not found, use `.amplifier/ado-templates/_default.md`
3. If no default, use minimal format (title + required fields from process cache only)

## Template Structure

Templates are Markdown files with sections. Each section becomes part of the work item's Description or Acceptance Criteria field.

### Example: task.md

```markdown
# Task Template

## Problem Statement
<!-- What problem does this task solve? -->

## Work Breakdown
<!-- Steps to complete this task -->
- [ ] Step 1
- [ ] Step 2

## Dependencies
<!-- Blockers or related work -->

## Test Plan
<!-- How to verify completion -->

## Acceptance Criteria
<!-- Definition of done -->
```

### Section Mapping to ADO Fields

| Template Section | ADO Field |
|------------------|-----------|
| Problem Statement | System.Description |
| Work Breakdown | System.Description |
| Dependencies | System.Description |
| Root Cause Analysis | System.Description |
| Repro Steps | Microsoft.VSTS.TCM.ReproSteps (Bug only) |
| Test Plan | System.Description OR Acceptance Criteria |
| Acceptance Criteria | Microsoft.VSTS.Common.AcceptanceCriteria |

The agent combines most sections into `Description` as HTML. `Acceptance Criteria` gets its own field.

## Agent Workflow: Creating Work Items with Templates

1. **Bootstrap check** (process cache loaded)
2. **Determine type** (from config default or user selection)
3. **Load template** for that type
4. **For each section:**
   - Show section heading and guidance
   - Prompt user for content (or generate from context)
5. **Format as HTML** and populate ADO fields
6. **Create work item** with populated fields
7. **Link to PR** if applicable

## Template Variables

Templates can include variables that agents fill automatically:

| Variable | Value |
|----------|-------|
| `{{branch}}` | Current git branch |
| `{{author}}` | Git config user.name |
| `{{date}}` | Current date |
| `{{pr_id}}` | Linked PR ID (if known) |
| `{{commits}}` | Summary of recent commits on branch |

## Bootstrap Awareness

When bootstrapping a new repo with the ADO bundle, the agent should:

1. Check if `.amplifier/ado-templates/` exists
2. If not, offer to create templates based on org's process types
3. Suggest templates for types discovered in process cache

**Example prompt:**
```
Your org has these work item types: Task, Bug, Product Backlog Item, Feature...
Would you like me to create templates for them in .amplifier/ado-templates/?
```

## Configuration

Teams can specify template preferences in `.amplifier/ado-team-config.yaml`:

```yaml
ado:
  work-item:
    templates-dir: .amplifier/ado-templates  # default
    require-template: true                    # warn if template missing
    default-type: Task                        # type must have template
```

## Validation

When `require-template: true`:
- Agent warns if creating a WI type with no template
- Prompts: "No template for [Type]. Create with minimal fields or abort?"

## Best Practices

1. **Start simple** — `_default.md` covers most cases initially
2. **Add type-specific templates** as team needs emerge
3. **Keep sections focused** — Each section = one piece of information
4. **Use HTML sparingly** — Markdown sections get converted automatically
5. **Include acceptance criteria** — Makes auditing easier
6. **Review templates periodically** — Update as team process evolves
