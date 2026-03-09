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
