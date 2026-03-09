# ADO Development Suite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build three Amplifier bundles (`ado-scrum`, `ado-test`, `ado-kql`) for complete Microsoft developer workflow coverage.

**Architecture:** Each bundle follows the thin bundle pattern — includes foundation, declares one agent, and references context/config files. Agents use `az devops` CLI and REST APIs via `az rest`. Config files use `.amplifier/` convention.

**Tech Stack:** Amplifier bundle YAML, markdown agent definitions, `az devops` CLI, `az monitor` CLI, `dotnet` CLI

---

## Phase 1: ado-scrum Bundle

### Task 1.1: Create ado-scrum bundle structure

**Files:**
- Create: `amplifier-bundle-ado-scrum/bundle.md`
- Create: `amplifier-bundle-ado-scrum/agents/ado-scrum-helper.md`
- Create: `amplifier-bundle-ado-scrum/context/scrum-config-schema.md`
- Create: `amplifier-bundle-ado-scrum/context/scrum-workflow.md`

**Step 1: Create bundle directory**

```bash
mkdir -p amplifier-bundle-ado-scrum/agents amplifier-bundle-ado-scrum/context
```

**Step 2: Create bundle.md**

```markdown
---
bundle:
  name: ado-scrum
  version: 1.0.0
  description: |
    Standup generation, journal tracking, and blocker detection for Azure DevOps.
    
    Auto-generates standup updates from commits, PRs, and work item changes.
    Tracks journal entries for work not in ADO. Surfaces blockers with escalation recommendations.
    
    Prerequisites:
    - Azure CLI with devops extension: az extension add --name azure-devops
    - Authenticated: az login
    - Optional: .amplifier/scrum-config.yaml for team rituals

includes:
  - bundle: foundation

agents:
  include:
    - ado-scrum:agents/ado-scrum-helper

context:
  include:
    - ado-scrum:context/scrum-config-schema.md
    - ado-scrum:context/scrum-workflow.md

tools:
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@v1.0.0
---

# ADO Scrum Bundle

Standup generation and journal tracking for Azure DevOps workflows.

## Quick Start

```bash
# Generate today's standup
"generate my standup"

# Add journal entry
"add journal entry: synced with platform team on auth approach"

# Check blockers
"what's blocking me?"
```

## Configuration

Create `.amplifier/scrum-config.yaml` for team-specific settings:

```yaml
version: 1
recurring:
  - name: "Sprint planning"
    schedule: "biweekly/monday"
    tags: [scrum]

standup:
  include_journal: true
  include_blockers: true
  escalation_threshold_hours: 24
```
```

**Step 3: Verify bundle structure**

```bash
ls -la amplifier-bundle-ado-scrum/
```
Expected: `agents/`, `context/`, `bundle.md`

**Step 4: Commit**

```bash
git add amplifier-bundle-ado-scrum/bundle.md
git commit -m "feat(ado-scrum): create bundle structure"
```

---

### Task 1.2: Create ado-scrum-helper agent

**Files:**
- Create: `amplifier-bundle-ado-scrum/agents/ado-scrum-helper.md`

**Step 1: Create agent definition**

```markdown
---
meta:
  name: ado-scrum-helper
  description: |
    Generates standup updates from ADO activity, tracks journal entries, and surfaces blockers.
    
    Use PROACTIVELY when:
    - User needs standup preparation
    - User wants to track work not in ADO (meetings, research, coordination)
    - User asks about blockers or stale PRs/work items
    
    Capabilities:
    - Generate standup from commits, PRs, WI state changes (last 24h)
    - Manage journal entries in .amplifier/scrum-journal.yaml
    - Detect blockers (PRs waiting, WIs stuck, failed pipelines)
    - Recommend escalation actions for blocked items
    - Track recurring meetings from config

model_role: general
---

# ADO Scrum Helper

You help developers prepare standups and track their work.

## Core Workflows

### Generate Standup

1. Query recent commits (last 24h, filtered by user):
   ```bash
   az repos commit list --repository {repo} --top 50 --query "[?author.email=='{user_email}']" -o json
   ```

2. Query PR activity:
   ```bash
   az repos pr list --repository {repo} --creator {user_email} --status all --top 20 -o json
   ```

3. Query work item changes:
   ```bash
   az boards query --wiql "SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.ChangedBy] = @Me AND [System.ChangedDate] >= @Today - 1" -o json
   ```

4. Read journal entries from `.amplifier/scrum-journal.yaml`

5. Check recurring items from `.amplifier/scrum-config.yaml`

6. Format output:
   ```
   ## Yesterday (from ADO)
   - [activity list]
   
   ## Yesterday (journal)
   - [journal entries]
   
   ## Today
   - [planned work + recurring meetings]
   
   ## Blockers & Recommended Actions
   - [blockers with recommendations]
   ```

### Add Journal Entry

1. Read existing `.amplifier/scrum-journal.yaml` (create if missing)
2. Append new entry with today's date and tags
3. Write back to file

```yaml
entries:
  - date: YYYY-MM-DD
    text: "User's entry"
    tags: [auto-detected-or-user-provided]
```

### Detect Blockers

Query for:
- PRs waiting > 24h: `az repos pr list --status active` + filter by last update
- WIs stuck in same state: `az boards query` with state change filter
- Failed pipelines: `az pipelines runs list --status failed --top 5`

Recommend actions based on threshold from config.

### Blocker Feedback

When user provides feedback on a blocker:
- Update internal tracking (in-memory for session)
- Adjust recommendations based on user input
- Example: "PR #123 - @reviewer is OOO, reassigned to @other"

## Config Schema

See @ado-scrum:context/scrum-config-schema.md for full schema.

## Important

- Always use `az rest --resource "499b84ac-1321-427f-aa17-267ca6975798"` for ADO API calls that aren't covered by `az repos`/`az boards`
- Filter all queries by user to avoid showing team-wide activity
- Journal entries are committed to git — keep them professional
```

**Step 2: Commit**

```bash
git add amplifier-bundle-ado-scrum/agents/ado-scrum-helper.md
git commit -m "feat(ado-scrum): add scrum-helper agent definition"
```

---

### Task 1.3: Create ado-scrum context files

**Files:**
- Create: `amplifier-bundle-ado-scrum/context/scrum-config-schema.md`
- Create: `amplifier-bundle-ado-scrum/context/scrum-workflow.md`

**Step 1: Create config schema context**

```markdown
# Scrum Config Schema

## File: `.amplifier/scrum-config.yaml`

```yaml
version: 1

# Recurring meetings/events to surface in standup
recurring:
  - name: "Meeting name"
    schedule: "weekly/monday" | "biweekly/tuesday" | "daily" | "monthly/first-monday"
    tags: [optional, tags]

# Standup generation settings
standup:
  include_journal: true      # Include journal entries in standup
  include_blockers: true     # Include blocker section
  escalation_threshold_hours: 24  # Hours before recommending escalation
  
# Blocker tracking settings
blocker_tracking:
  auto_detect: true          # Auto-detect from ADO state
  accept_feedback: true      # Allow user to update blocker status
```

## Schedule Format

| Format | Meaning |
|--------|---------|
| `daily` | Every day |
| `weekly/monday` | Every Monday |
| `biweekly/tuesday` | Every other Tuesday |
| `monthly/first-monday` | First Monday of month |
| `monthly/15` | 15th of each month |

## File: `.amplifier/scrum-journal.yaml`

```yaml
entries:
  - date: 2026-03-08
    text: "Free-form description of work"
    tags: [coordination, platform]
```

Entries are appended, not replaced. Consider pruning old entries periodically.
```

**Step 2: Create workflow context**

```markdown
# Scrum Workflow

## Standup Generation Flow

```
1. Bootstrap ADO context (org, project from git remote)
2. Query commits → filter by author + last 24h
3. Query PRs → filter by creator + last 24h  
4. Query WI changes → filter by @Me + last 24h
5. Read journal entries → filter by yesterday/today
6. Read recurring items → filter by today's schedule
7. Detect blockers → apply threshold from config
8. Format and present
```

## Journal Entry Flow

```
1. User provides entry text
2. Auto-detect tags from keywords (optional)
3. Read existing scrum-journal.yaml
4. Append entry with today's date
5. Write file
6. Confirm to user
```

## Blocker Detection Logic

| Condition | Recommendation |
|-----------|----------------|
| PR waiting > threshold | "Ping @reviewer" |
| PR waiting > 2x threshold | "Escalate to @lead" |
| WI stuck > 3 days | "Update status or add blocked tag" |
| Pipeline failed | "Check logs, may need fix" |

## Integration with ADO

Uses standard ADO CLI commands:
- `az repos commit list` — commit history
- `az repos pr list` — PR status
- `az boards query` — work item queries (WIQL)
- `az pipelines runs list` — pipeline status
```

**Step 3: Commit**

```bash
git add amplifier-bundle-ado-scrum/context/
git commit -m "feat(ado-scrum): add context files for config and workflow"
```

---

## Phase 2: ado-test Bundle

### Task 2.1: Create ado-test bundle structure

**Files:**
- Create: `amplifier-bundle-ado-test/bundle.md`
- Create: `amplifier-bundle-ado-test/agents/ado-test-runner.md`
- Create: `amplifier-bundle-ado-test/context/test-config-schema.md`
- Create: `amplifier-bundle-ado-test/context/trx-parsing.md`

**Step 1: Create bundle directory**

```bash
mkdir -p amplifier-bundle-ado-test/agents amplifier-bundle-ado-test/context
```

**Step 2: Create bundle.md**

```markdown
---
bundle:
  name: ado-test
  version: 1.0.0
  description: |
    Local test execution and pipeline test result analysis for .NET projects.
    
    Runs unit tests locally, starts services for integration testing,
    parses TRX results from pipelines, and links failures to work items.
    
    Prerequisites:
    - .NET SDK installed: dotnet --version
    - Azure CLI for pipeline queries: az login
    - Optional: Docker for docker-compose testing

includes:
  - bundle: foundation

agents:
  include:
    - ado-test:agents/ado-test-runner

context:
  include:
    - ado-test:context/test-config-schema.md
    - ado-test:context/trx-parsing.md

tools:
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@v1.0.0
---

# ADO Test Bundle

Local test execution and pipeline result analysis.

## Quick Start

```bash
# Run unit tests
"run the unit tests"

# Start local service and run smoke tests
"start the service locally and test it"

# Analyze recent pipeline test results
"show me test failures from the last pipeline run"
```

## Configuration

Create `.amplifier/ado-test-config.yaml`:

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
```
```

**Step 3: Commit**

```bash
git add amplifier-bundle-ado-test/bundle.md
git commit -m "feat(ado-test): create bundle structure"
```

---

### Task 2.2: Create ado-test-runner agent

**Files:**
- Create: `amplifier-bundle-ado-test/agents/ado-test-runner.md`

**Step 1: Create agent definition**

```markdown
---
meta:
  name: ado-test-runner
  description: |
    Runs local tests, manages local service testing, and analyzes pipeline test results.
    
    Use PROACTIVELY when:
    - User wants to run unit tests locally
    - User needs to test a service against dev/PPE environment
    - User wants to analyze test failures from CI/CD
    - User asks about flaky tests or test trends
    
    Capabilities:
    - Execute dotnet test with TRX output
    - Start local services (dotnet run, docker-compose, or detect already running)
    - Run smoke tests against local service
    - Parse TRX files from pipeline artifacts
    - Link test failures to existing work items
    - Detect flaky tests from historical data

model_role: coding
---

# ADO Test Runner

You help developers run tests locally and analyze test results.

## Core Workflows

### Run Unit Tests

1. Read config from `.amplifier/ado-test-config.yaml`
2. Execute tests:
   ```bash
   dotnet test {project} --logger "trx;LogFileName=results.trx" --results-directory {results_dir}
   ```
3. Parse TRX results (see @ado-test:context/trx-parsing.md)
4. Summarize: passed, failed, skipped, duration
5. For failures, show test name + error message

### Start Local Service

Support three modes (check config for preferred method):

**dotnet run:**
```bash
dotnet run --project {project} {args}
```

**docker-compose:**
```bash
docker-compose -f {compose_file} up -d {services}
```

**manual (already running):**
- Skip start, just verify service is up

After start, wait for health check:
```bash
curl -s -o /dev/null -w "%{http_code}" {base_url}/health
```

### Run Smoke Tests

From config `smoke_tests` list:
```bash
curl -s -X {method} -o /dev/null -w "%{http_code}" {base_url}{url}
```

Report pass/fail for each test.

### Analyze Pipeline Results

1. Get latest pipeline run:
   ```bash
   az pipelines runs list --pipeline-name {name} --top 1 -o json
   ```

2. Download TRX artifact:
   ```bash
   az pipelines runs artifact download --run-id {id} --artifact-name {name} --path ./artifacts
   ```

3. Parse TRX, compare with previous runs for flaky detection

### Link Failures to Work Items

For each failure:
1. Search for existing bug with test name in title
2. If found, add comment with latest failure
3. If not found and `auto_create_bugs: true`, create new bug

## Environment

Local service testing uses `DefaultAzureCredential`:
- Picks up `az login` credentials automatically
- No secrets in config files
- Works with PPE/dev Azure resources

## TRX Parsing

See @ado-test:context/trx-parsing.md for TRX XML structure and parsing logic.
```

**Step 2: Commit**

```bash
git add amplifier-bundle-ado-test/agents/ado-test-runner.md
git commit -m "feat(ado-test): add test-runner agent definition"
```

---

### Task 2.3: Create ado-test context files

**Files:**
- Create: `amplifier-bundle-ado-test/context/test-config-schema.md`
- Create: `amplifier-bundle-ado-test/context/trx-parsing.md`

**Step 1: Create config schema**

```markdown
# Test Config Schema

## File: `.amplifier/ado-test-config.yaml`

```yaml
version: 1

# Unit test configuration
unit_tests:
  project: tests/MyService.Tests/MyService.Tests.csproj  # Path to test project
  logger: trx                    # Output format (trx for .NET)
  results_dir: TestResults/      # Where to store results

# Local service testing
local_service:
  methods:
    # dotnet run method
    dotnet:
      project: src/MyService/MyService.csproj
      args: ["--urls", "http://localhost:5000"]
    
    # docker-compose method
    docker:
      compose_file: docker-compose.yml
      services: [api, db]        # Which services to start
    
    # Manual (service already running)
    manual:
      base_url: http://localhost:5000

  # Environment variables for local testing
  environment:
    ASPNETCORE_ENVIRONMENT: Development
    # Azure auth handled by DefaultAzureCredential

  # Smoke tests to run after service starts
  smoke_tests:
    - name: health
      method: GET
      url: /health
      expect_status: 200
    - name: api-version
      method: GET
      url: /api/version
      expect_status: 200

# Work item linking for failures
failure_linking:
  auto_create_bugs: false        # Create bugs for new failures
  link_existing: true            # Link to existing bugs
```

## Service Start Priority

Agent tries methods in order:
1. `dotnet` if configured
2. `docker` if configured
3. `manual` (assume already running)

User can override: "start service with docker"
```

**Step 2: Create TRX parsing context**

```markdown
# TRX Parsing

## TRX File Structure

Visual Studio Test Results XML format:

```xml
<?xml version="1.0" encoding="utf-8"?>
<TestRun>
  <Results>
    <UnitTestResult testId="..." testName="TestClassName.TestMethodName" 
                    outcome="Passed|Failed|Skipped" duration="00:00:00.123">
      <Output>
        <ErrorInfo>
          <Message>Assertion failed...</Message>
          <StackTrace>at ...</StackTrace>
        </ErrorInfo>
      </Output>
    </UnitTestResult>
  </Results>
  <ResultSummary outcome="Failed">
    <Counters total="100" passed="98" failed="2" />
  </ResultSummary>
</TestRun>
```

## Parsing Logic

```python
import xml.etree.ElementTree as ET

def parse_trx(trx_path):
    tree = ET.parse(trx_path)
    root = tree.getroot()
    
    # Handle namespace
    ns = {'t': 'http://microsoft.com/schemas/VisualStudio/TeamTest/2010'}
    
    results = []
    for result in root.findall('.//t:UnitTestResult', ns):
        results.append({
            'name': result.get('testName'),
            'outcome': result.get('outcome'),
            'duration': result.get('duration'),
            'error': result.find('.//t:Message', ns)?.text
        })
    
    summary = root.find('.//t:Counters', ns)
    return {
        'total': int(summary.get('total')),
        'passed': int(summary.get('passed')),
        'failed': int(summary.get('failed')),
        'results': results
    }
```

## Summary Format

```
## Test Results
- **Total:** 100
- **Passed:** 98 ✓
- **Failed:** 2 ✗
- **Duration:** 45.2s

## Failures
1. `MyService.Tests.AuthTests.TokenRefresh_Expired_ShouldRefresh`
   > Expected: 200, Actual: 401
   
2. `MyService.Tests.ApiTests.RateLimit_Exceeded_ShouldReturn429`
   > System.TimeoutException: Operation timed out
```

## Flaky Detection

Track outcomes across last N runs:
- If test has >20% failure rate but <80% → flag as flaky
- Store history in `.amplifier/test-history.json` (gitignored)
```

**Step 3: Commit**

```bash
git add amplifier-bundle-ado-test/context/
git commit -m "feat(ado-test): add context files for config and TRX parsing"
```

---

## Phase 3: ado-kql Bundle

### Task 3.1: Create ado-kql bundle structure

**Files:**
- Create: `amplifier-bundle-ado-kql/bundle.md`
- Create: `amplifier-bundle-ado-kql/agents/ado-kql-analyst.md`
- Create: `amplifier-bundle-ado-kql/context/kql-reference.md`
- Create: `amplifier-bundle-ado-kql/context/query-library-schema.md`

**Step 1: Create bundle directory**

```bash
mkdir -p amplifier-bundle-ado-kql/agents amplifier-bundle-ado-kql/context
```

**Step 2: Create bundle.md**

```markdown
---
bundle:
  name: ado-kql
  version: 1.0.0
  description: |
    KQL query execution and diagnostics for Azure Application Insights and Log Analytics.
    
    Maintains an evolving query library that grows with team knowledge.
    Executes Geneva Actions for automated diagnostics and remediation.
    
    Prerequisites:
    - Azure CLI: az login
    - Access to Application Insights / Log Analytics workspace
    - Optional: Geneva cluster access for Geneva Actions

includes:
  - bundle: foundation

agents:
  include:
    - ado-kql:agents/ado-kql-analyst

context:
  include:
    - ado-kql:context/kql-reference.md
    - ado-kql:context/query-library-schema.md

tools:
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@v1.0.0
---

# ADO KQL Bundle

KQL diagnostics with an evolving query library.

## Quick Start

```bash
# Run a saved query
"run the recent-exceptions query"

# Ad-hoc query
"query exceptions from the last hour"

# Save a useful query
"save this query as auth-failures"

# Geneva Action (if configured)
"collect diagnostics from the service"
```

## Configuration

Create `.amplifier/kql-queries.yaml` to build your query library:

```yaml
version: 1
defaults:
  app_insights_resource: /subscriptions/.../appInsights/my-app
  time_range: 1h

queries:
  - name: recent-exceptions
    description: Exceptions in the last hour
    kql: |
      exceptions
      | where timestamp > ago(1h)
      | summarize count() by type
```
```

**Step 3: Commit**

```bash
git add amplifier-bundle-ado-kql/bundle.md
git commit -m "feat(ado-kql): create bundle structure"
```

---

### Task 3.2: Create ado-kql-analyst agent

**Files:**
- Create: `amplifier-bundle-ado-kql/agents/ado-kql-analyst.md`

**Step 1: Create agent definition**

```markdown
---
meta:
  name: ado-kql-analyst
  description: |
    Executes KQL queries, maintains query library, and runs Geneva diagnostics.
    
    Use PROACTIVELY when:
    - User is debugging production issues
    - User needs to query Application Insights or Log Analytics
    - User wants to save/manage useful queries
    - User needs to run Geneva Actions (collect dumps, restart, diagnostics)
    
    Capabilities:
    - Execute KQL against App Insights / Log Analytics
    - Manage persistent query library (.amplifier/kql-queries.yaml)
    - Suggest new queries based on context
    - Execute Geneva Actions for diagnostics
    - Correlate telemetry with recent deployments/PRs

model_role: reasoning
---

# ADO KQL Analyst

You help developers diagnose production issues using KQL and Geneva.

## Core Workflows

### Execute Query from Library

1. Read `.amplifier/kql-queries.yaml`
2. Find query by name
3. Execute via az CLI:
   ```bash
   az monitor app-insights query \
     --app {resource_id} \
     --analytics-query "{kql}" \
     -o json
   ```
4. Format and present results

### Execute Ad-Hoc Query

1. Compose KQL from user request
2. Execute via az CLI
3. After presenting results, ask: "Save this query to library?"
4. If yes, append to kql-queries.yaml

### Save Query to Library

1. Validate KQL syntax (dry run)
2. Generate name and description from user or auto-detect
3. Add tags based on query content (errors, performance, auth, etc.)
4. Append to `.amplifier/kql-queries.yaml`
5. Commit change suggestion

### Query Suggestions

Based on context, proactively suggest relevant queries:
- User debugging auth → suggest auth-related queries
- Recent deployment mentioned → suggest deployment correlation query
- Error spike discussed → suggest exception breakdown query

### Execute Geneva Actions

If `.amplifier/geneva-actions.yaml` configured:

1. List available actions
2. User selects action
3. Execute via Geneva API (internal Microsoft)
4. Report status

## KQL Execution

Always use `az monitor` for reliable execution:

```bash
# Application Insights
az monitor app-insights query \
  --app {resource_id} \
  --analytics-query "{kql}" \
  --start-time {start} \
  --end-time {end} \
  -o json

# Log Analytics
az monitor log-analytics query \
  --workspace {workspace_id} \
  --analytics-query "{kql}" \
  -o json
```

## Query Library Management

The query library is designed to grow over time:
1. Team commits standard queries
2. Individuals add useful ad-hoc queries during incidents
3. Agent suggests queries based on patterns
4. Library becomes institutional knowledge

See @ado-kql:context/query-library-schema.md for schema.

## Correlation with Deployments

When investigating issues, correlate with recent activity:
```bash
# Recent pipeline runs
az pipelines runs list --top 5 -o json

# Recent commits
az repos commit list --top 10 -o json
```

Link telemetry timestamps to deployment times.
```

**Step 2: Commit**

```bash
git add amplifier-bundle-ado-kql/agents/ado-kql-analyst.md
git commit -m "feat(ado-kql): add kql-analyst agent definition"
```

---

### Task 3.3: Create ado-kql context files

**Files:**
- Create: `amplifier-bundle-ado-kql/context/kql-reference.md`
- Create: `amplifier-bundle-ado-kql/context/query-library-schema.md`

**Step 1: Create KQL reference**

```markdown
# KQL Quick Reference

## Common Tables

| Table | Contains |
|-------|----------|
| `exceptions` | Unhandled exceptions and errors |
| `requests` | HTTP request telemetry |
| `dependencies` | Calls to external services |
| `traces` | Log messages and traces |
| `customEvents` | Custom application events |
| `performanceCounters` | System performance metrics |

## Essential Operators

```kql
// Filter
| where timestamp > ago(1h)
| where success == false
| where name contains "auth"

// Aggregate
| summarize count() by type
| summarize avg(duration), p95=percentile(duration, 95) by name

// Sort and limit
| order by timestamp desc
| take 100

// Project specific columns
| project timestamp, name, duration, success
```

## Useful Patterns

### Exception Breakdown
```kql
exceptions
| where timestamp > ago(1h)
| summarize count() by type, outerMessage
| order by count_ desc
```

### Slow Requests
```kql
requests
| where timestamp > ago(1h)
| where duration > 5000
| summarize count(), avg(duration) by name
| order by count_ desc
```

### Failed Dependencies
```kql
dependencies
| where timestamp > ago(1h)
| where success == false
| summarize count() by target, type, resultCode
```

### Error Rate
```kql
requests
| where timestamp > ago(1h)
| summarize 
    total = count(),
    failed = countif(success == false)
| extend error_rate = round(100.0 * failed / total, 2)
```

### Correlation with Deployment
```kql
requests
| where timestamp > ago(6h)
| summarize count(), error_rate = round(100.0 * countif(success == false) / count(), 2) by bin(timestamp, 15m)
| render timechart
```

## Time Functions

| Function | Example |
|----------|---------|
| `ago(1h)` | 1 hour ago |
| `ago(1d)` | 1 day ago |
| `now()` | Current time |
| `bin(timestamp, 15m)` | 15-minute buckets |
| `startofday(timestamp)` | Start of day |
```

**Step 2: Create query library schema**

```markdown
# Query Library Schema

## File: `.amplifier/kql-queries.yaml`

```yaml
version: 1

# Default settings for all queries
defaults:
  app_insights_resource: /subscriptions/{sub}/resourceGroups/{rg}/providers/microsoft.insights/components/{name}
  time_range: 1h  # Default time range if not specified in query

# Query library
queries:
  - name: recent-exceptions        # Unique identifier
    description: Exceptions in the last hour
    kql: |
      exceptions
      | where timestamp > ago(1h)
      | summarize count() by type, outerMessage
      | order by count_ desc
    tags: [errors, triage]
    
  - name: slow-requests
    description: Requests slower than 5 seconds
    kql: |
      requests
      | where timestamp > ago(1h)
      | where duration > 5000
      | summarize count() by name, resultCode
    tags: [performance, triage]
```

## File: `.amplifier/geneva-actions.yaml`

```yaml
version: 1

# Geneva cluster configuration
cluster: your-geneva-cluster
namespace: your-namespace  # Optional

# Available actions
available_actions:
  - name: collect-dump
    description: Collect memory dump from service instance
    action_id: CollectDump
    parameters:  # Optional parameters
      - name: instance_id
        required: true
    
  - name: restart-service
    description: Restart service instance
    action_id: RestartService
    
  - name: run-diagnostics
    description: Run standard diagnostic collection
    action_id: RunDiagnostics
```

## Query Naming Conventions

| Pattern | Use For |
|---------|---------|
| `{category}-{specific}` | General pattern |
| `errors-*` | Error-related queries |
| `perf-*` | Performance queries |
| `auth-*` | Authentication queries |
| `deps-*` | Dependency queries |

## Tags

Standard tags for categorization:
- `triage` — First-look queries for incidents
- `errors` — Error/exception related
- `performance` — Latency and throughput
- `auth` — Authentication and authorization
- `dependencies` — External service calls
- `user-contributed` — Added by team members (not standard)
```

**Step 3: Commit**

```bash
git add amplifier-bundle-ado-kql/context/
git commit -m "feat(ado-kql): add context files for KQL reference and schema"
```

---

## Phase 4: Integration

### Task 4.1: Update azure-devops bundle composition

**Files:**
- Modify: `amplifier-bundle-azure-devops/bundle.md`

**Step 1: Add new bundles to includes**

Add after the existing includes:
```yaml
includes:
  # Foundation provides core tools (bash, filesystem, etc.)
  - bundle: foundation
  # Core bundles (ado-pr includes ado-work-items via composition)
  - bundle: ado-pr:bundle
  # Additional agents not in composed bundles
  - bundle: azure-devops:behaviors/azure-devops-extras
  # EngHub documentation research
  - bundle: ado-research:behaviors/ado-research
  # Scrum and standup helpers
  - bundle: ado-scrum:bundle
  # Test execution and analysis
  - bundle: ado-test:bundle
  # KQL diagnostics
  - bundle: ado-kql:bundle
  # Dev machine bundle for autonomous development infrastructure
  - bundle: git+https://github.com/ramparte/amplifier-bundle-dev-machine@main
```

**Step 2: Update bundle composition diagram**

```
azure-devops (full suite)
├── foundation
├── ado-pr
│   └── ado-work-items
├── ado-research
├── ado-scrum          ← NEW
├── ado-test           ← NEW
├── ado-kql            ← NEW
├── ado-pipelines
├── ado-repos
├── ado-boards
└── dev-machine (external)
```

**Step 3: Commit**

```bash
git add amplifier-bundle-azure-devops/bundle.md
git commit -m "feat(azure-devops): compose ado-scrum, ado-test, ado-kql bundles"
```

---

### Task 4.2: Final verification and push

**Step 1: Verify all bundle structures**

```bash
ls -la amplifier-bundle-ado-scrum/
ls -la amplifier-bundle-ado-test/
ls -la amplifier-bundle-ado-kql/
```

Each should have: `bundle.md`, `agents/`, `context/`

**Step 2: Verify bundle YAML syntax**

```bash
# Check frontmatter is valid YAML
head -30 amplifier-bundle-ado-scrum/bundle.md
head -30 amplifier-bundle-ado-test/bundle.md
head -30 amplifier-bundle-ado-kql/bundle.md
```

**Step 3: Push all changes**

```bash
git push origin master
```

**Step 4: Verify pushed commits**

```bash
git log --oneline -10
```

---

## Summary

| Phase | Bundle | Agent | Key Features |
|-------|--------|-------|--------------|
| 1 | `ado-scrum` | `ado-scrum-helper` | Standup gen, journal, blockers |
| 2 | `ado-test` | `ado-test-runner` | Local tests, TRX parsing, failure linking |
| 3 | `ado-kql` | `ado-kql-analyst` | KQL queries, query library, Geneva Actions |
| 4 | Integration | — | Compose into azure-devops bundle |
