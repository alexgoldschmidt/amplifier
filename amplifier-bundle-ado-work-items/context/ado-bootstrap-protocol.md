# Azure DevOps Bootstrap Protocol

The ADO bundle discovers org-specific process metadata and caches it locally. This eliminates hardcoded assumptions about process templates, work item types, and field requirements.

## Bootstrap Flow

```
Agent invoked
    │
    ├─ Auth check: az account show → FAIL → "Run az login" → STOP
    │
    ├─ Detect org/project from git remote
    │
    ├─ Check cache: ~/.amplifier/ado-cache/{org}/{project}/process.yaml
    │     │
    │     ├─ EXISTS → Load cache, proceed
    │     └─ MISSING → Run discovery sequence ↓
    │
    ├─ DISCOVERY SEQUENCE
    │     1. Get project → extract process template ID
    │     2. Get all work item types for process
    │     3. For each type: get fields (required/optional)
    │     4. Get behaviors → derive hierarchy levels
    │     5. Write cache file
    │
    └─ Load cache, proceed with operation
```

## Trigger Conditions

| Trigger | Action |
|---------|--------|
| No cache file exists | Full discovery |
| User runs `bootstrap --refresh` | Force full discovery |
| API returns "type not found" error | Auto-refresh cache, retry once |

## Cache Location

**Path:** `~/.amplifier/ado-cache/{org}/{project}/process.yaml`

User-level storage (not in repo) because:
- Org-specific data shouldn't be committed
- Survives repo clones
- Different users may have different access levels

## Discovery API Sequence

### Step 1: Get Project Process Template

```bash
# Get project details
PROJECT_INFO=$(az devops project show \
  --project "$PROJECT" \
  --organization "https://dev.azure.com/$ORG" \
  -o json)

PROJECT_ID=$(echo "$PROJECT_INFO" | jq -r '.id')

# Get process template ID
PROCESS_ID=$(az rest --method get \
  --resource "499b84ac-1321-427f-aa17-267ca6975798" \
  --uri "https://dev.azure.com/$ORG/_apis/projects/$PROJECT_ID/properties?api-version=7.1-preview.1" \
  | jq -r '.value[] | select(.name == "System.ProcessTemplateType") | .value')
```

### Step 2: Get All Work Item Types

```bash
az rest --method get \
  --resource "499b84ac-1321-427f-aa17-267ca6975798" \
  --uri "https://dev.azure.com/$ORG/_apis/work/processes/$PROCESS_ID/workitemtypes?api-version=7.1-preview.2" \
  | jq '.value[] | {name: .name, refName: .referenceName, class: .class}'
```

### Step 3: Get Fields Per Type

```bash
WIT_REF="Microsoft.VSTS.WorkItemTypes.Task"  # example

az rest --method get \
  --resource "499b84ac-1321-427f-aa17-267ca6975798" \
  --uri "https://dev.azure.com/$ORG/_apis/work/processes/$PROCESS_ID/workitemtypes/$WIT_REF/fields?api-version=7.1-preview.2" \
  | jq '.value[] | {name: .name, refName: .referenceName, required: .required, type: .type}'
```

### Step 4: Get Behaviors (Hierarchy Levels)

```bash
az rest --method get \
  --resource "499b84ac-1321-427f-aa17-267ca6975798" \
  --uri "https://dev.azure.com/$ORG/_apis/work/processes/$PROCESS_ID/behaviors?api-version=7.1-preview.1" \
  | jq '.value[] | {id: .id, name: .name, rank: .rank}'
```

## Cache Schema

```yaml
# ~/.amplifier/ado-cache/{org}/{project}/process.yaml
_meta:
  org: msazure
  project: one
  discovered-at: "2026-03-07T17:58:00Z"
  process-id: "a1b2c3d4-..."
  process-name: "Scrum_AzureOneBranchGoldCore"

work-item-types:
  Epic:
    ref-name: "Microsoft.VSTS.WorkItemTypes.Epic"
    class: "derived"
    backlog-level: "portfolio-epic"
    fields:
      required:
        - { key: "System.Title", name: "Title", type: "string" }
        - { key: "System.State", name: "State", type: "string" }
      optional:
        - { key: "System.Description", name: "Description", type: "html" }
    allowed-children: [Feature, Scenario]

  Task:
    ref-name: "Microsoft.VSTS.WorkItemTypes.Task"
    class: "derived"
    backlog-level: "task"
    fields:
      required: [...]
      optional: [...]
    allowed-children: []

  "Key Result":
    ref-name: "Custom.KeyResult"
    class: "custom"
    backlog-level: null
    fields: { ... }
    allowed-children: []

hierarchy:
  levels:
    - name: "portfolio-epic"
      rank: 4
      types: [Epic]
    - name: "portfolio-feature"
      rank: 3
      types: [Feature, Scenario]
    - name: "requirement"
      rank: 2
      types: ["Product Backlog Item", Bug]
    - name: "task"
      rank: 1
      types: [Task]
```

## Agent Bootstrap Check

Every ADO agent includes this at the start of operations:

```
Step 0: Bootstrap Check
  1. Auth check (az account show)
  2. Org/project detection from git remote
  3. Load process cache → if missing, run discovery
  4. Load team config (.amplifier/ado-team-config.yaml) → optional overlay
  5. Check work item templates (.amplifier/ado-templates/) → optional
```

## Work Item Templates

After process discovery, check if the repo has work item templates:

```bash
TEMPLATES_DIR="$(git rev-parse --show-toplevel)/.amplifier/ado-templates"
if [ -d "$TEMPLATES_DIR" ]; then
    # Templates available - use when creating work items
    ls "$TEMPLATES_DIR"
fi
```

**If templates exist:** Use them when creating work items of that type.
**If templates missing:** Offer to create templates based on discovered process types.

See `ado-work-item-templates.md` for template structure and usage.

## Two Layers of Configuration

| Layer | Source | Contains | Committed? |
|-------|--------|----------|------------|
| **Process cache** | ADO API discovery | What's *possible* (types, fields, hierarchy) | No |
| **Team config** | `.amplifier/ado-team-config.yaml` | What's *preferred* (defaults, templates) | Yes |

Team config references types/fields that exist in the process cache. If team config references a type not in cache, the agent warns.

## Manual Refresh

To force re-discovery:

```bash
# Delete cache and let auto-bootstrap recreate it
rm ~/.amplifier/ado-cache/{org}/{project}/process.yaml

# Or trigger refresh explicitly on next operation
```

Future: An explicit `ado-bootstrap --refresh` command could be added.

## Fallback Behavior

| Scenario | Behavior |
|----------|----------|
| No auth | STOP, ask for `az login` |
| Auth OK, no cache, API works | Run full discovery, cache, proceed |
| Auth OK, no cache, API fails | Warn: "Cannot discover process. Check permissions." |
| Cache exists, type-not-found error | Auto-refresh cache, retry once |

## No Hardcoded Assumptions

The bootstrap protocol means:
- No assumed work item types (discover what exists)
- No assumed fields per type (discover from process API)
- No assumed hierarchy rules (derive from behavior levels)
- Works for standard AND custom process templates
