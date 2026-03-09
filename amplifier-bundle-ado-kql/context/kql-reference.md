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
