# 006 — Docker Foreman Integration Specification

## Status: Draft
## Author: Zen Architect
## Date: 2026-03-08

---

## 1. Overview

### Problem

The ADO Event Monitor detects changes in Azure DevOps and dispatches to Amplifier agents. The Docker Foreman spawns AI workers in isolated containers, each tracked by an ADO work item. Today these systems are disconnected:

- **Event Monitor** uses a static `subscriptions.yaml` — subscriptions are defined at startup and never change.
- **Docker Foreman** workers poll their own work items with 30s backoff — no external event detection.
- Workers lack PR lifecycle capabilities — they can only interact with work items, not create or respond to PRs.

### Solution

Integrate the two systems so that:

1. The Event Monitor **dynamically discovers** active workers from the Foreman's worker registry.
2. The Event Monitor **watches each worker's ADO work item** for human responses.
3. The Event Monitor **dispatches events to the docker-worker agent** inside the container.
4. Docker workers are **bootstrapped with full ADO capabilities** (`ado-pr` bundle, which includes `ado-work-items`).

### Scope

**In scope (v1):**
- `SubscriptionSource` protocol abstracting subscription origins
- `ForemanSubscriptionSource` reading worker JSON files
- `CompositeSubscriptionSource` merging static YAML + dynamic foreman sources
- Monitor reconciliation loop (add/remove poll tasks dynamically)
- Work item event detection for foreman workers (`WI_COMMENT_ADDED`, `WI_STATE_CHANGED`)
- ADO bundle upgrade in `docker-foreman.yaml` (`ado-work-items` → `ado-pr`)

**Out of scope (deferred):**
- PR discovery by branch name (requires ADO search queries)
- Direct container signaling / wake mechanism
- Worker-to-worker coordination events
- Pipeline monitoring for worker branches

---

## 2. Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     ADO Event Monitor                           │
│                                                                 │
│  ┌──────────────────────┐    ┌────────────────────────────┐     │
│  │ CompositeSubscription│    │        Monitor              │     │
│  │ Source                │◄──►│  (reconciliation loop)     │     │
│  │  ├─ YamlSource       │    │  ├─ poll tasks per sub     │     │
│  │  └─ ForemanSource    │    │  └─ 15s reconcile interval │     │
│  └──────────┬───────────┘    └─────────────┬──────────────┘     │
│             │                              │                    │
│  ┌──────────▼───────────┐    ┌─────────────▼──────────────┐     │
│  │ Worker JSON files    │    │     Dispatcher              │     │
│  │ ~/.amplifier/        │    │  (routes to docker-worker)  │     │
│  │  projects/{p}/       │    └─────────────┬──────────────┘     │
│  │  docker-foreman/     │                  │                    │
│  │  workers/*.json      │                  │                    │
│  └──────────────────────┘                  │                    │
└────────────────────────────────────────────┼────────────────────┘
                                             │
                    ┌────────────────────────▼─────────────────┐
                    │           Azure DevOps                    │
                    │  ┌─────────────┐  ┌─────────────┐        │
                    │  │ WI #101     │  │ WI #102     │        │
                    │  │ (Active)    │  │ (Blocked)   │        │
                    │  └──────┬──────┘  └──────┬──────┘        │
                    └─────────┼────────────────┼───────────────┘
                              │                │
                    ┌─────────▼──┐  ┌──────────▼─┐
                    │ Worker A   │  │ Worker B   │
                    │ Container  │  │ Container  │
                    │ (working)  │  │ (polling)  │
                    └────────────┘  └────────────┘
```

### Data Flow

```
1. Foreman spawns worker → writes workers/feature-auth.json
2. Monitor reconciliation (every 15s) → reads workers/*.json
3. ForemanSource generates Subscription for WI #101
4. Monitor starts poll task for WI #101 (60s interval)
5. Human comments on WI #101 in ADO
6. Poller detects snapshot change → Differ produces WI_COMMENT_ADDED
7. Dispatcher routes to docker-worker agent in Worker A's container
8. Worker A receives event, reads comment, resumes work
```

---

## 3. SubscriptionSource Protocol

### Interface

```python
# src/ado_monitor/sources.py

from typing import Protocol, runtime_checkable
from .models import Subscription


@runtime_checkable
class SubscriptionSource(Protocol):
    """Protocol for subscription providers."""

    @property
    def source_id(self) -> str:
        """Unique identifier for this source (used in subscription ID prefixing)."""
        ...

    async def get_subscriptions(self) -> list[Subscription]:
        """Return the current set of subscriptions.

        Called periodically by the reconciliation loop.
        Must be safe to call concurrently.
        Must not raise — return empty list on error and log.
        """
        ...
```

### Design Decisions

- **Protocol, not ABC**: Structural typing for loose coupling. Any object with matching methods qualifies.
- **`runtime_checkable`**: Enables `isinstance()` checks for validation at startup.
- **`source_id` property**: Prefixed to subscription IDs to avoid collisions between sources (e.g., `foreman:wi-101` vs `yaml:wi-456`).
- **No-throw contract**: `get_subscriptions()` must catch its own exceptions. A failing source must not crash the monitor.

---

## 4. ForemanSubscriptionSource

### Purpose

Reads the Docker Foreman's worker registry and generates work item subscriptions for each active worker.

### File Locations

```
~/.amplifier/projects/{project}/docker-foreman/
├── config.yaml              # ADO org/project, fleet settings
└── workers/
    ├── feature-auth.json    # One file per active worker
    └── bugfix-api.json
```

### Implementation

```python
# src/ado_monitor/sources/foreman.py

class ForemanSubscriptionSource:
    """Generates subscriptions from Docker Foreman worker registry."""

    source_id: str = "foreman"

    def __init__(
        self,
        project: str,
        org: str,
        ado_project: str,
        poll_interval_seconds: int = 60,
        base_path: Path | None = None,
    ) -> None:
        self.project = project
        self.org = org
        self.ado_project = ado_project
        self.poll_interval_seconds = poll_interval_seconds
        self.base_path = base_path or Path.home() / ".amplifier" / "projects" / project / "docker-foreman"

    async def get_subscriptions(self) -> list[Subscription]:
        """Read worker JSONs and generate subscriptions."""
        ...
```

### Behavior

1. **Scan** `{base_path}/workers/` for `*.json` files.
2. **Parse** each file, extracting `work_item_id`, `branch`, `container_id`, `session_id`.
3. **Skip** files that are malformed or missing required fields (log warning).
4. **Skip** workers whose state is `"closed"` or `"destroyed"` (if state field present).
5. **Generate** one `Subscription` per active worker:
   - `id`: `"foreman:wi-{work_item_id}"`
   - `type`: `SubscriptionType.WORK_ITEM`
   - `org`: from constructor (sourced from `config.yaml`)
   - `project`: from constructor
   - `work_item_id`: from worker JSON
   - `poll_interval_seconds`: from constructor (default 60s)
   - `events`: `["comment-added", "state-change"]`
   - `actions`: Single action dispatching to `docker-worker` (see §7)

### Error Handling

| Condition | Behavior |
|-----------|----------|
| `workers/` directory doesn't exist | Return empty list, log info |
| Individual JSON file is malformed | Skip file, log warning with filename |
| JSON missing `work_item_id` | Skip file, log warning |
| File system permission error | Return empty list, log error |
| `config.yaml` missing | Raise at construction time (fail-fast) |

### Caching

- Worker JSONs are small (<1KB each) and few (<20 typically).
- No caching needed — re-read from disk on every call.
- Filesystem reads are fast enough for 15s reconciliation interval.

---

## 5. Monitor Reconciliation

### Current Behavior (Problem)

```python
# monitor.py — current start()
tasks = [asyncio.create_task(self._poll_loop(sub)) for sub in self.config.subscriptions]
await self._shutdown.wait()
```

All poll tasks are created at startup from `config.subscriptions` and never change.

### New Behavior

Add a reconciliation loop that periodically compares running poll tasks against current subscriptions from all sources.

### Algorithm

```python
async def _reconciliation_loop(self) -> None:
    """Periodically reconcile running poll tasks with current subscriptions."""
    while not self._shutdown.is_set():
        try:
            current_subs = await self._source.get_subscriptions()
            current_ids = {s.id for s in current_subs}
            running_ids = set(self._poll_tasks.keys())

            # Start new subscriptions
            for sub in current_subs:
                if sub.id not in running_ids:
                    logger.info(f"Starting poll task for new subscription: {sub.id}")
                    self._subscriptions[sub.id] = sub
                    self._poll_tasks[sub.id] = asyncio.create_task(
                        self._poll_loop(sub)
                    )
                    # Update dispatcher's subscription map
                    self.dispatcher.subscriptions[sub.id] = sub

            # Stop removed subscriptions
            for sub_id in running_ids - current_ids:
                logger.info(f"Stopping poll task for removed subscription: {sub_id}")
                self._poll_tasks[sub_id].cancel()
                del self._poll_tasks[sub_id]
                del self._subscriptions[sub_id]
                self.dispatcher.subscriptions.pop(sub_id, None)

        except Exception:
            logger.exception("Error during reconciliation")

        # Wait for next reconciliation or shutdown
        try:
            await asyncio.wait_for(self._shutdown.wait(), timeout=15.0)
            break
        except TimeoutError:
            pass
```

### Timing

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Reconciliation interval | 15 seconds | Fast enough to detect new workers, cheap (just filesystem reads) |
| Initial reconciliation | Immediate on startup | Replaces current static task creation |
| Grace period on removal | None (v1) | Cancel immediately; worker JSON removal = worker destroyed |

### Race Condition Handling

- **Single writer**: Only the reconciliation loop modifies `_poll_tasks`. Poll loops are read-only consumers.
- **Atomic source reads**: `get_subscriptions()` returns a complete snapshot. No partial reads.
- **Task cancellation safety**: `_poll_loop` already handles `CancelledError` gracefully.
- **Dispatcher map sync**: Dispatcher's `subscriptions` dict is updated in the same reconciliation pass that creates/removes tasks.

### State Store Cleanup

When a subscription is removed (worker destroyed):
- The poll task is cancelled.
- Snapshots for that subscription remain in SQLite (useful for audit).
- No automatic cleanup (retention handled by existing spec 005).

---

## 6. ADO Bundle Integration

### Current State

`docker-foreman.yaml` line 13:
```yaml
- bundle: file:///mnt/c/git/one/pricing.mcp/amplifier-bundle-ado-work-items#subdirectory=behaviors/ado-work-items.yaml
```

Workers only get work item CRUD. No PR capabilities.

### Required Change

Replace `ado-work-items` with `ado-pr` bundle (which already includes `ado-work-items` via composition):

```yaml
# behaviors/docker-foreman.yaml — updated includes
includes:
  # Docker container management
  - bundle: git+https://github.com/microsoft/amplifier-bundle-execution-environments@main#subdirectory=behaviors/env-docker.yaml
  # Full ADO capabilities: PR lifecycle + work items + boards
  - bundle: file:///mnt/c/git/one/pricing.mcp/amplifier-bundle-ado-pr#subdirectory=behaviors/ado-pr.yaml
```

### What Workers Gain

| Capability | Source Bundle | Use Case |
|------------|--------------|----------|
| Work item CRUD | `ado-work-items` (via `ado-pr`) | Progress tracking, questions (existing) |
| PR creation | `ado-pr` | Create draft PR when work is done |
| PR comment management | `ado-pr` | Respond to review feedback |
| PR status/vote reading | `ado-pr` | React to approvals/rejections |

### docker-worker.md Updates

Add to the worker agent's capabilities section:

```markdown
## PR Lifecycle (via ado-pr bundle)

When your work is complete and pushed:
1. Create a draft PR targeting the appropriate base branch
2. Post the PR URL as a work item comment
3. If the Event Monitor notifies you of PR feedback, address it

You have access to:
- `ado-pr-manager` agent for PR operations
- `ado_create_pr`, `ado_add_pr_comment` tools
```

---

## 7. Dispatch Behavior

### Dispatch Target

Events from foreman-sourced subscriptions dispatch to the **docker-worker agent inside the worker's container**, not to generic ADO agents.

### Why docker-worker, Not ado-work-items

The docker-worker has:
- Task context (what it was working on)
- Branch context (where its code lives)
- Session history (what it already tried)
- Container access (can resume coding)

A generic `ado-work-items` agent would lack all of this.

### Action Configuration

ForemanSubscriptionSource generates actions with a special dispatch target:

```python
actions=[
    Action(
        agent="docker-worker",
        trigger="comment-added",
        behavior="resume-from-response",
    ),
    Action(
        agent="docker-worker",
        trigger="state-change",
        behavior="handle-state-change",
    ),
]
```

### Dispatch Context

The dispatcher builds context including foreman-specific metadata:

```python
{
    "event_type": "wi.comment.added",
    "subscription_id": "foreman:wi-101",
    "org": "myorg",
    "project": "MyProject",
    "work_item_id": 101,
    "payload": {
        "comment_text": "🔧 RESPONSE: Use JWT for stateless auth",
        "comment_author": "John Doe",
        "comment_id": 42
    },
    "behavior": "resume-from-response",
    # Foreman-specific fields
    "foreman": {
        "worker_name": "feature-auth",
        "container_id": "abc123",
        "session_id": "sess-xyz",
        "branch": "feature/auth"
    }
}
```

### Dispatch Mechanism (v1)

For v1, dispatch is via Amplifier CLI invocation (same as existing dispatcher):

```bash
amplifier run \
  --agent docker-worker \
  --instruction "A human responded to your question on WI #101: 'Use JWT for stateless auth'. Resume your work." \
  --context '{"work_item_id": 101, ...}'
```

**Known limitation**: This starts a *new* agent session, not the worker's existing session inside the container. The worker's internal polling will also detect the response independently.

**v1 mitigation**: The worker's own polling (30s backoff, up to 5min) will catch responses. The external dispatch provides faster detection but is additive, not exclusive.

### Behavior Instructions

| Behavior | Instruction Template |
|----------|---------------------|
| `resume-from-response` | "A human responded to your question on WI #{work_item_id}: '{comment_text}'. Resume your work." |
| `handle-state-change` | "Work item #{work_item_id} state changed to '{new_state}'. Acknowledge and adjust your work accordingly." |

---

## 8. Configuration Schema

### Event Monitor Configuration Extension

The existing `subscriptions.yaml` gains a new top-level `sources` key:

```yaml
# subscriptions.yaml — extended format

# Static subscriptions (existing, unchanged)
ignore_authors:
  - "Amplifier Bot"
  - "amplifier[bot]"

subscriptions:
  - id: pr-123
    type: pull-request
    org: myorg
    project: myproject
    repo: myrepo
    pr_id: 123
    poll_interval: 60s
    events: [new-comments]
    actions:
      - agent: ado-pr-manager
        trigger: new-comments
        behavior: address-feedback

# Dynamic sources (new)
sources:
  - type: foreman
    project: my-project          # ~/.amplifier/projects/{project}/docker-foreman/
    org: myorg                   # ADO organization
    ado_project: MyProject       # ADO project name
    poll_interval: 60s           # How often to poll each worker's WI
    # Optional overrides:
    # base_path: /custom/path/to/docker-foreman/
    # reconcile_interval: 15s
```

### Backward Compatibility

- `sources` key is optional. If absent, monitor behaves exactly as before (static subscriptions only).
- Existing `subscriptions` key is always loaded via `YamlSubscriptionSource`.
- Both static and dynamic subscriptions coexist via `CompositeSubscriptionSource`.

### Config Parsing Changes

```python
# config.py — additions

@dataclass
class SourceConfig:
    """Configuration for a dynamic subscription source."""
    type: str                     # "foreman" (extensible)
    project: str                  # Amplifier project name
    org: str                      # ADO organization
    ado_project: str              # ADO project
    poll_interval_seconds: int    # Per-subscription poll interval
    base_path: Path | None        # Override for worker registry path
    reconcile_interval: int       # Override reconciliation interval (default 15s)


@dataclass
class Config:
    subscriptions: list[Subscription]
    ignore_authors: set[str]
    sources: list[SourceConfig]   # NEW
```

---

## 9. Worker JSON Schema

### File Location

```
~/.amplifier/projects/{project}/docker-foreman/workers/{worker-name}.json
```

### Schema

```json
{
    "name": "feature-auth",
    "container_id": "abc123def456",
    "session_id": "sess-xyz-789",
    "work_item_id": 101,
    "branch": "feature/auth",
    "created_at": "2026-03-08T04:30:00Z",
    "task": "Implement JWT authentication per spec",
    "state": "active"
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Worker name (matches filename without `.json`) |
| `container_id` | string | Yes | Docker container ID |
| `session_id` | string | Yes | Amplifier session ID running inside container |
| `work_item_id` | integer | Yes | ADO work item ID for coordination |
| `branch` | string | Yes | Git branch the worker operates on |
| `created_at` | ISO 8601 | Yes | When the worker was spawned |
| `task` | string | No | Human-readable task description |
| `state` | string | No | Worker state: `"active"`, `"blocked"`, `"closed"`, `"destroyed"` |

### Lifecycle

| Foreman Operation | JSON Effect | Monitor Reaction |
|-------------------|-------------|------------------|
| `spawn` | File created | Next reconciliation adds poll task |
| Worker goes Blocked | `state` updated to `"blocked"` | No change (still polling) |
| Worker completes | `state` updated to `"closed"` | No change (still polling until destroy) |
| `destroy` | File deleted | Next reconciliation cancels poll task |
| `destroy_all` | All files deleted | All foreman poll tasks cancelled |

### Notes

- The `state` field in the JSON reflects the *foreman's* knowledge of the worker, not the ADO work item state. The monitor reads the ADO work item state directly via polling.
- Files are written by the `docker_foreman` tool, not by workers themselves.
- The monitor treats file presence as "subscription active" and file absence as "subscription removed".

---

## 10. Success Criteria

### Acceptance Tests

| # | Scenario | Expected Result | Measurement |
|---|----------|----------------|-------------|
| 1 | Foreman spawns a worker (JSON created) | Monitor starts polling its WI within 15s | Log: "Starting poll task for new subscription: foreman:wi-{id}" |
| 2 | Human comments on a blocked worker's WI | Monitor detects `WI_COMMENT_ADDED` event | Event recorded in SQLite `events` table |
| 3 | Monitor dispatches to docker-worker | Amplifier CLI invoked with correct context | Log: "Dispatching wi.comment.added to docker-worker" |
| 4 | Foreman destroys a worker (JSON deleted) | Monitor stops polling within 15s | Log: "Stopping poll task for removed subscription: foreman:wi-{id}" |
| 5 | Static YAML subscriptions still work | Existing behavior unchanged | Existing test suite passes |
| 6 | Malformed worker JSON | Skipped with warning, other workers unaffected | Log: warning with filename |
| 7 | ForemanSource with no workers directory | Empty subscription list, no crash | Log: info message |
| 8 | Monitor restart with existing workers | Picks up all active workers on startup | Poll tasks created for all worker JSONs |
| 9 | No `sources` in config | Monitor behaves identically to before | No reconciliation loop started |

### Performance Targets

| Metric | Target |
|--------|--------|
| Reconciliation overhead | < 10ms per cycle (filesystem reads only) |
| Memory per foreman subscription | Same as static subscription (~2KB) |
| Max workers supported | 50 (limited by ADO API rate) |
| Detection latency (WI comment) | ≤ poll_interval (default 60s) |

---

## 11. Implementation Phases

### Phase 1: SubscriptionSource Protocol + Reconciliation (This Spec)

**Deliverables:**

1. `src/ado_monitor/sources/__init__.py` — `SubscriptionSource` protocol
2. `src/ado_monitor/sources/yaml_source.py` — Wraps existing `Config.subscriptions`
3. `src/ado_monitor/sources/foreman.py` — Reads worker JSONs
4. `src/ado_monitor/sources/composite.py` — Merges multiple sources
5. `src/ado_monitor/monitor.py` — Add reconciliation loop, refactor `start()`
6. `src/ado_monitor/config.py` — Parse `sources` key
7. `docker-foreman.yaml` — Update bundle reference to `ado-pr`
8. `docker-worker.md` — Add PR lifecycle capabilities
9. Tests for all new modules

**Changes to existing files:**

| File | Change |
|------|--------|
| `monitor.py` | Replace static task creation with reconciliation loop |
| `config.py` | Add `SourceConfig` dataclass, parse `sources` key |
| `models.py` | No changes (Subscription model already sufficient) |
| `dispatcher.py` | Add `resume-from-response` behavior instruction |

### Phase 2: PR Discovery (Deferred)

- Query ADO for PRs targeting worker branches
- Generate PR subscriptions dynamically (like WI subscriptions)
- Detect `PR_COMMENT_NEW`, `PR_VOTE_CHANGED` for worker PRs
- Requires ADO API: `GET /pullrequests?searchCriteria.sourceRefName=refs/heads/{branch}`

### Phase 3: Direct Container Signaling (Deferred)

- Instead of starting a new agent session, signal the existing worker
- Options: `docker exec`, Unix socket, HTTP endpoint inside container
- Eliminates duplicate detection (monitor + worker polling)

---

## 12. Open Questions

| # | Question | Current Assumption | Impact if Wrong |
|---|----------|--------------------|-----------------|
| 1 | How does the monitor invoke an agent *inside* a specific container? | v1: External CLI invocation (new session). Worker's own polling provides the real response channel. | Worker gets response via polling (30s–5min delay) instead of instant dispatch. Acceptable for v1. |
| 2 | Should the monitor clean up SQLite state when a worker is destroyed? | No — retain for audit. Existing retention policy (spec 005) handles cleanup. | Slight storage growth over time. Negligible. |
| 3 | What if two monitors run simultaneously with overlapping foreman sources? | Not supported. Single-instance assumption. | Duplicate event detection and dispatch. Add leader election in future if needed. |
| 4 | Should `ForemanSubscriptionSource` read `config.yaml` directly or receive values via constructor? | Constructor injection. Config.yaml is parsed once at startup, values passed in. | Simpler testing, no file I/O in source constructor. |
| 5 | Should foreman subscriptions have different `ignore_authors` than static ones? | No. Global `ignore_authors` applies to all sources. | Workers using `🤖 [Amplifier]` prefix are already filtered. |

---

## Appendix A: CompositeSubscriptionSource

```python
class CompositeSubscriptionSource:
    """Merges subscriptions from multiple sources."""

    source_id: str = "composite"

    def __init__(self, sources: list[SubscriptionSource]) -> None:
        self.sources = sources

    async def get_subscriptions(self) -> list[Subscription]:
        results: list[Subscription] = []
        for source in self.sources:
            try:
                subs = await source.get_subscriptions()
                results.extend(subs)
            except Exception:
                logger.exception(f"Source {source.source_id} failed")
        return results
```

## Appendix B: YamlSubscriptionSource

```python
class YamlSubscriptionSource:
    """Wraps static subscriptions from subscriptions.yaml."""

    source_id: str = "yaml"

    def __init__(self, subscriptions: list[Subscription]) -> None:
        self._subscriptions = subscriptions

    async def get_subscriptions(self) -> list[Subscription]:
        return self._subscriptions
```

## Appendix C: File Structure After Implementation

```
src/ado_monitor/
├── __init__.py
├── cli.py
├── config.py              # Modified: parse sources key
├── differ.py
├── dispatcher.py           # Modified: add foreman behaviors
├── models.py
├── monitor.py              # Modified: reconciliation loop
├── poller.py
├── state.py
├── webhook.py
└── sources/                # NEW
    ├── __init__.py         # SubscriptionSource protocol + exports
    ├── yaml_source.py      # YamlSubscriptionSource
    ├── foreman.py          # ForemanSubscriptionSource
    └── composite.py        # CompositeSubscriptionSource
```
