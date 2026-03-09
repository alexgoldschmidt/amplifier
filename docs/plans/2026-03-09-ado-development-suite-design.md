# ADO Development Suite Design

## Goal

Build three new Amplifier bundles (`ado-scrum`, `ado-test`, `ado-kql`) that complete end-to-end development coverage for Microsoft developers using Azure DevOps.

## Background

The existing Amplifier ADO bundles cover core DevOps operations — work items, PRs, pipelines, repos, boards, and documentation research. What's missing is the daily developer workflow layer: standup preparation, test execution, and production diagnostics. These three bundles close that gap, giving developers a complete AI-assisted development loop from sprint planning through production incident response.

## Existing Bundle Landscape

| Bundle | Purpose |
|--------|---------|
| `ado-work-items` | Work item CRUD, WIQL queries, templates |
| `ado-boards` | Sprint planning, iterations, capacity |
| `ado-pr` (includes ado-work-items) | PR lifecycle, comments, WI linking |
| `ado-research` | Lazy TOC-driven EngHub doc research |
| `ado-pipelines` | Trigger, monitor, logs |
| `ado-repos` | Branches, commits (not PRs) |
| `azure-devops` | Full suite composing all above |

## Approach

Three new bundles, each with a dedicated agent, integrated into the existing `azure-devops` composition. Each bundle is independently usable but designed to complement the others. Config files are project-committed YAML, following the existing `.amplifier/` convention.

**Implementation order:** `ado-scrum` → `ado-test` → `ado-kql` (highest daily value first, increasing complexity).

## Architecture

```
azure-devops (full suite)
├── foundation
├── ado-pr
│   └── ado-work-items
├── ado-research
├── ado-scrum          ← NEW
├── ado-test           ← NEW
├── ado-kql            ← NEW
└── dev-machine (external)
```

All three bundles use `az devops` CLI and REST APIs for ADO integration. `ado-test` additionally uses `dotnet` CLI for local test execution. `ado-kql` uses `az monitor` CLI and Geneva APIs for telemetry.

---

## Components

### 1. `ado-scrum` — Standup, Journal & Escalation Tracker

**Agent:** `ado-scrum-helper`

**Purpose:** Auto-generate standup updates from actual work, track journal entries for untracked work, and surface blockers with escalation recommendations.

#### Config Files

**`.amplifier/scrum-config.yaml`** — Team rituals and standup preferences (committed):

```yaml
version: 1
recurring:
  - name: "Platform sync"
    schedule: "weekly/tuesday"
    tags: [coordination, platform]
  - name: "Sprint planning"
    schedule: "biweekly/monday"
    tags: [scrum, planning]
  - name: "On-call rotation check"
    schedule: "weekly/friday"
    tags: [oncall]

standup:
  include_journal: true
  include_blockers: true
  escalation_threshold_hours: 24

blocker_tracking:
  auto_detect: true    # PRs waiting, WIs stuck
  accept_feedback: true # User can mark resolved/still-blocked
```

**`.amplifier/scrum-journal.yaml`** — Diary entries (committed):

```yaml
entries:
  - date: 2026-03-08
    text: "Synced with platform team on Geneva integration approach"
    tags: [coordination, platform]
  - date: 2026-03-08
    text: "Investigated PPE 500 errors - root cause in auth service"
    tags: [debugging, ppe]
```

#### Features

| Feature | Description |
|---------|-------------|
| **Standup generation** | Queries commits, PR activity, and WI state changes from last 24h → generates yesterday/today/blockers |
| **Journal tracking** | Free-form diary entries for work not tracked in ADO (meetings, research, coordination) |
| **Recurring meeting awareness** | Config-driven recurring items surface in standup on relevant days |
| **Blocker detection** | Auto-detects PRs waiting >threshold, WIs stuck in same state, failed pipelines |
| **Escalation recommendations** | Suggests actions for blocked items (ping reviewer, escalate to lead, update status) |
| **Blocker feedback loop** | User can update blocker status, mark resolved, or note still-blocked with context |

#### Example Output

```
## Yesterday (from ADO)
- Merged PR #1234: Fixed auth token refresh
- Moved WI#5678 to Code Review

## Yesterday (journal)
- Synced with platform team on Geneva integration
- Investigated PPE 500 errors

## Today
- Continuing WI#5679 (API rate limiting)
- PR #1235 needs review
- Platform sync meeting (recurring/tuesday)

## Blockers & Recommended Actions
- PR #1233 waiting 3 days → Ping @reviewer, escalate to @lead if no response by EOD
- WI#5679 blocked on external dependency → Update status, add blocked tag
```

---

### 2. `ado-test` — Test Runner & Analysis

**Agent:** `ado-test-runner`

**Purpose:** Run local unit tests, test services locally against PPE, parse pipeline test results, and link failures to work items.

#### Config File

**`.amplifier/ado-test-config.yaml`** (committed):

```yaml
version: 1
unit_tests:
  project: tests/MyService.Tests/MyService.Tests.csproj
  logger: trx
  results_dir: TestResults/

local_service:
  methods:
    dotnet:
      project: src/MyService/MyService.csproj
      args: ["--urls", "http://localhost:5000"]
    docker:
      compose_file: docker-compose.yml
      services: [api, db]
    manual:
      base_url: http://localhost:5000

  environment:
    ASPNETCORE_ENVIRONMENT: Development
    # DefaultAzureCredential handles auth automatically

  smoke_tests:
    - name: health
      method: GET
      url: /health
      expect_status: 200
    - name: api-version
      method: GET
      url: /api/version
      expect_status: 200

failure_linking:
  auto_create_bugs: false
  link_existing: true
```

#### Features

| Mode | What it does |
|------|-------------|
| **Run UTs** | `dotnet test --logger trx` → parse TRX → summarize pass/fail/skip |
| **Local service** | Start service via dotnet run / docker-compose / manual, run smoke tests |
| **Pipeline results** | Fetch TRX from pipeline artifacts → analyze failures and trends |
| **Failure linking** | Link test failures to existing work items, optionally create bugs |
| **Flaky detection** | Flag tests with inconsistent results across runs |

#### Local Dev Testing Flow

```
1. Start service (dotnet run / docker-compose / already running)
2. Wait for readiness (health check)
3. Run smoke tests from config
4. Report results
5. Optionally run full UT suite
```

**Auth:** Uses `DefaultAzureCredential` for PPE/dev environment access — no secrets in config.

---

### 3. `ado-kql` — Diagnostics with Evolving Query Library

**Agent:** `ado-kql-analyst`

**Purpose:** Execute KQL queries against App Insights / Log Analytics / Geneva, maintain a persistent query library that evolves with user suggestions, and execute Geneva Actions for diagnostics.

#### Config Files

**`.amplifier/kql-queries.yaml`** — Query library (committed, evolves over time):

```yaml
version: 1
defaults:
  app_insights_resource: /subscriptions/.../appInsights/ppe-app
  time_range: 1h

queries:
  - name: recent-exceptions
    description: Exceptions in the last hour
    kql: |
      exceptions
      | where timestamp > ago(1h)
      | summarize count() by type, outerMessage
      | order by count_ desc
    tags: [errors, triage]

  - name: slow-requests
    description: Requests slower than 5s
    kql: |
      requests
      | where timestamp > ago(1h)
      | where duration > 5000
      | summarize count() by name, resultCode
      | order by count_ desc
    tags: [performance, triage]

  - name: dependency-failures
    description: Failed downstream calls
    kql: |
      dependencies
      | where timestamp > ago(1h)
      | where success == false
      | summarize count() by target, type, resultCode
    tags: [dependencies, errors]
```

**`.amplifier/geneva-actions.yaml`** — Available Geneva Actions (committed):

```yaml
version: 1
cluster: your-geneva-cluster
available_actions:
  - name: collect-dump
    description: "Collect memory dump from service instance"
    action_id: CollectDump
  - name: restart-service
    action_id: RestartService
  - name: run-diagnostics
    action_id: RunDiagnostics
```

#### Features

| Feature | Description |
|---------|-------------|
| **KQL execution** | Run queries via `az monitor` CLI / REST APIs against App Insights and Log Analytics |
| **Persistent query library** | Project-committed YAML that accumulates useful queries over time |
| **User suggestions** | User can suggest new queries → agent validates and saves to library |
| **Proactive updates** | Agent suggests new queries based on observed patterns and context |
| **Geneva Actions** | Execute diagnostic actions (collect dumps, restart, run diagnostics) |
| **Incident correlation** | Link telemetry findings to recent PRs, deployments, and work items |

#### Query Library Evolution

The query library is designed to grow:
1. Starts with team-standard queries (committed to repo)
2. User discovers useful ad-hoc queries during incidents → saves to library
3. Agent proactively suggests queries based on observed failure patterns
4. Library becomes institutional knowledge, shared via git

---

## Data Flow

### `ado-scrum` Data Flow
```
ADO Commits/PRs/WIs → Query via az devops CLI → Aggregate by author + time
Journal entries → Read from scrum-journal.yaml
Recurring items → Read from scrum-config.yaml → Filter by today's schedule
All sources → Standup report + Blocker recommendations
```

### `ado-test` Data Flow
```
dotnet test → TRX file → Parse XML → Summarize results
Pipeline artifacts → Download TRX → Parse → Compare with previous runs
Failures → Match to work items via test name / stack trace
```

### `ado-kql` Data Flow
```
User request / proactive trigger → Select query from library or compose new
Query → az monitor app-insights query → Results
Results → Summarize + correlate with recent deployments/PRs
New useful query → Save to kql-queries.yaml
```

## Error Handling

- **Auth failures:** All bundles depend on `az login` / `DefaultAzureCredential`. Clear error messages directing user to authenticate.
- **Missing config:** Bundles work with defaults if config files don't exist. Agent guides user through initial setup.
- **API failures:** Retry with backoff for transient ADO/Azure API errors. Surface clear error for permission issues.
- **Test failures:** Test failures are results, not errors. Agent reports them cleanly without treating them as tool failures.
- **KQL errors:** Invalid KQL syntax surfaced with suggestions for correction.

## Testing Strategy

- **Unit tests:** Each bundle's agent logic tested with mocked ADO API responses
- **Integration tests:** Run against ADO PPE organization with test project
- **Config validation:** Schema validation for all YAML config files
- **Manual verification:** Standup output reviewed against actual ADO state

## Open Questions

- **Geneva auth model:** How does the agent authenticate to Geneva APIs? Service principal, managed identity, or user token?
- **Query library conflicts:** How to handle merge conflicts in kql-queries.yaml when multiple team members add queries?
- **Scrum journal git hygiene:** Should journal entries be pruned after N days to keep the file manageable?
- **Test result retention:** How many pipeline test runs to retain for flaky detection trend analysis?
