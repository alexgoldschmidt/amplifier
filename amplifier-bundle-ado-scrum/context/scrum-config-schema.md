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
