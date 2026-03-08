# ADO Event Monitor Service — Design Notes

## Problem Statement

The existing `amplifier-bundle-azure-devops` has agents that respond to human commands. We need an autonomous service that **detects changes** in Azure DevOps (PR updates, work item changes, pipeline completions) and **triggers Amplifier agents** without human intervention.

## Event Detection: Recommendation

### ADO Service Hooks (Webhooks) vs Polling

| Factor | Service Hooks (Webhooks) | Polling |
|--------|--------------------------|---------|
| Latency | Near real-time (~seconds) | Minutes (depends on interval) |
| Cloud ADO support | ✅ Full | ✅ Full |
| On-premises ADO | ✅ Supported (ADO Server 2019+) | ✅ Always works |
| Setup complexity | Needs public endpoint or tunnel | Zero infrastructure |
| Reliability | Can miss events (no retry guarantee) | Never misses (reads current state) |
| API quota usage | Zero (push model) | Proportional to poll frequency |
| Admin permission needed | Yes (project-level) | No (read access only) |

### **Recommendation: Polling-first, Webhooks as accelerator**

**Why polling-first:**
1. **Zero infrastructure** — no public endpoint needed, works behind firewalls
2. **Works everywhere** — cloud, on-prem, restricted environments
3. **Guaranteed consistency** — reads actual state, never misses events
4. **No admin permissions** — only needs read access via PAT/Azure AD token
5. **Simpler to debug** — deterministic behavior

**Webhooks as optional accelerator:**
- When available, webhooks trigger an immediate poll (instead of waiting for next interval)
- This gives near-real-time response without depending on webhooks for correctness

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│              ADO Event Monitor Service              │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌─────────────┐     │
│  │  Poller  │──▶│  Differ  │──▶│  Dispatcher │     │
│  │ (per sub)│   │          │   │             │     │
│  └──────────┘   └──────────┘   └──────┬──────┘     │
│       ▲                               │            │
│       │ (optional)                    ▼            │
│  ┌──────────┐              ┌─────────────────────┐ │
│  │ Webhook  │              │ Amplifier Agent     │ │
│  │ Receiver │              │   Invocation        │ │
│  └──────────┘              └─────────────────────┘ │
│                                                     │
│  ┌────────────────────────────────────────────────┐ │
│  │          State Store (SQLite/JSON)            │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
           │                        │
           ▼                        ▼
    Azure DevOps APIs        Amplifier Agents
    (REST API 7.1)           (ado-pr-manager,
                              ado-work-items, etc.)
```

## Component Breakdown

### 1. Subscription Config (`subscriptions.yaml`)

Defines what to watch. Each subscription = one ADO entity being tracked.

```yaml
subscriptions:
  - id: pr-123
    type: pull-request
    org: myorg
    project: myproject
    repo: myrepo
    pr_id: 123
    poll_interval: 60s        # how often to check
    events:                    # what triggers action
      - new-comments
      - status-change
      - vote-change
      - push-update
    actions:                   # what to do
      - agent: ado-pr-manager
        trigger: new-comments
        behavior: address-feedback
      - agent: ado-pipelines
        trigger: push-update
        behavior: monitor-build

  - id: wi-456
    type: work-item
    org: myorg
    project: myproject
    work_item_id: 456
    poll_interval: 120s
    events:
      - state-change
      - field-update
      - comment-added
    actions:
      - agent: ado-work-items
        trigger: state-change
        behavior: sync-status
```

### 2. Poller

One polling loop per subscription. Calls ADO REST APIs on interval.

**PR polling** — fetches:
- Thread list (comment count + statuses)
- PR metadata (status, votes, merge status)
- Push/iteration list (new commits)

**Work item polling** — fetches:
- Revision history (via `_apis/wit/workitems/{id}/revisions`)
- Comment list

**Key design: poll returns full current state, differ detects changes.**

```
GET /git/repositories/{repo}/pullRequests/{prId}/threads
GET /git/repositories/{repo}/pullRequests/{prId}/iterations
GET /git/repositories/{repo}/pullRequests/{prId}
GET /wit/workitems/{id}/revisions?$top=1
```

### 3. Differ

Compares current poll result against stored state. Produces typed events:

```
Event Types:
  pr.comment.new          — new thread or reply appeared
  pr.comment.resolved     — thread status changed to fixed/closed
  pr.vote.changed         — reviewer vote changed
  pr.status.changed       — PR status changed (active→completed)
  pr.push                 — new iteration/push detected
  pr.policy.changed       — build policy status changed
  wi.state.changed        — work item state transition
  wi.field.updated        — field value changed
  wi.comment.added        — new comment on work item
```

**Differ is stateless** — takes (previous_snapshot, current_snapshot) → events[].

### 4. State Store

Minimal persistence. Stores last-seen snapshot per subscription.

```
state/
  pr-123.json         # last poll result for PR 123
  wi-456.json         # last poll result for WI 456
  events.log          # append-only event log (for debugging)
```

**SQLite alternative** for larger deployments:
```sql
CREATE TABLE snapshots (
  subscription_id TEXT PRIMARY KEY,
  last_snapshot TEXT,          -- JSON blob
  last_poll_at TEXT,
  last_event_at TEXT
);

CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  subscription_id TEXT,
  event_type TEXT,
  payload TEXT,
  created_at TEXT,
  processed_at TEXT,
  status TEXT DEFAULT 'pending'  -- pending, processing, done, failed
);
```

### 5. Dispatcher

Takes events from differ, matches against subscription actions, invokes Amplifier agents.

**Dispatch logic:**
1. Event arrives (e.g., `pr.comment.new`)
2. Look up subscription actions where `trigger` matches event type
3. Build agent context (event payload + subscription config)
4. Invoke Amplifier agent (e.g., `ado-pr-manager` with "address feedback" intent)
5. Record result in event log

**Concurrency model:** One event at a time per subscription (prevents race conditions on the same PR). Different subscriptions process in parallel.

### 6. Webhook Receiver (Optional)

Thin HTTP endpoint that converts ADO Service Hook payloads into "poll now" signals.

```
POST /webhook/ado
  → Parse event type
  → Find matching subscription
  → Trigger immediate poll (skip waiting for interval)
```

**Not a primary event source** — just an accelerator. If webhook is missed, next poll catches it.

## Data Flow

```
Normal flow (polling):
  Timer fires → Poller hits ADO API → Differ compares → Events emitted → Dispatcher invokes agent

Accelerated flow (webhook + polling):
  ADO Service Hook → Webhook Receiver → Poller triggered immediately → same as above
```

**Example: New PR comment appears**

1. Poll fetches `/pullRequests/{id}/threads` → gets 5 threads
2. State store has 4 threads from last poll
3. Differ produces `pr.comment.new` event with thread details
4. Dispatcher matches event → invokes `ado-pr-manager` agent
5. Agent reads comment, implements fix, replies to thread
6. Next poll sees the agent's reply (ignores it via author filter)

## Implementation Plan

### Phase 1: Minimal Viable Monitor (polling only)

**New files in bundle:**

```
amplifier-bundle-azure-devops/
  service/
    monitor.py              # Main loop — reads config, runs pollers
    poller.py               # ADO API polling (PR + WI)
    differ.py               # Snapshot comparison → events
    dispatcher.py           # Event → agent invocation
    state.py                # JSON file-based state store
    config.py               # Subscription config parser
  service/subscriptions.yaml  # User-edited config
```

**Language: Python** — aligns with Amplifier ecosystem, good async support, simple deployment.

**Dependencies:** `httpx` (async HTTP), `pyyaml`, `schedule` or `asyncio` timers. No framework.

### Phase 2: Robustness
- SQLite state store for crash recovery
- Exponential backoff on API failures
- Dead letter queue for failed dispatches
- Agent output capture and logging

### Phase 3: Webhook Accelerator
- FastAPI/Flask thin endpoint
- ADO Service Hook registration helper
- Ngrok/tunnel support for local dev

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary detection | Polling | Works everywhere, no infra needed |
| State format | JSON files → SQLite | Start simple, upgrade when needed |
| Poll interval | 60s PRs, 120s WIs | Balance responsiveness vs API quota |
| Concurrency | asyncio per subscription | Lightweight, no threading complexity |
| Agent invocation | Amplifier CLI/API | Uses existing agent definitions |
| Author filtering | Skip own comments | Prevents infinite loops |
| Error handling | Log + retry with backoff | Don't crash on transient failures |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limiting | Polls blocked | Adaptive intervals — back off when 429 received; batch API calls |
| Token expiry (1hr Azure AD) | Auth failures | Token refresh before each poll cycle |
| Agent infinite loop | Agent responds to own comments, triggers new event | **Author filter** — differ ignores changes made by the service's identity |
| Missed events during downtime | Stale state | On startup, diff against last known state catches everything |
| Concurrent agent runs on same PR | Race conditions | **Mutex per subscription** — one dispatch at a time per entity |
| Large PRs with many threads | Slow polls, high memory | Pagination + incremental diffing (only fetch threads newer than watermark) |
| On-prem ADO with old API versions | API calls fail | Version negotiation on first poll; fallback to older endpoints |

## Anti-Loop Safety

Critical: the service must never react to its own actions.

```python
IGNORE_AUTHORS = {"Amplifier Bot", "service-principal-name"}

def filter_events(events):
    return [e for e in events if e.author not in IGNORE_AUTHORS]
```

Additionally, all agent replies already include the `🤖 [Amplifier]` prefix (from ado-pr-manager.md), making them easy to identify and skip.

## Deployment Model

**Local/Dev:** `python -m ado_monitor --config subscriptions.yaml` — runs on developer machine, uses their Azure CLI credentials.

**Server:** Container or systemd service with managed identity or PAT. Single instance per org (subscriptions fan out internally).

**No cloud dependencies** beyond ADO itself. No message queue, no database server, no web framework (for Phase 1).

## Success Criteria

1. Service detects new PR comment within 60 seconds and invokes `ado-pr-manager`
2. Service detects work item state change within 120 seconds
3. Service survives restart without re-processing old events
4. Service never triggers infinite loops from its own actions
5. Service works with both cloud ADO and on-premises ADO Server

## Questions for Dev-Machine Bundle Review

1. Does this polling-first architecture align with dev-machine patterns for autonomous services?
2. Is the subscription config schema appropriate for recipe-driven infrastructure?
3. Should the dispatcher use Amplifier's recipe system instead of direct agent invocation?
4. What's the recommended pattern for state persistence in dev-machine workflows?
5. How should agent results be captured and fed back into the system?
