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
