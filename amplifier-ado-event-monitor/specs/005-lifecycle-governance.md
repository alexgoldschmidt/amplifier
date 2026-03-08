# Feature Spec: Work Item Lifecycle Governance

## Overview

Enforce rigid lifecycle rules for high-level work items (Releases, Epics, Features). State transitions are blocked unless gates pass. Risk conditions (approaching dates, stale fields) are automatically detected and escalated.

## Problem Statement

Release work items must follow a controlled lifecycle:
- State transitions only allowed when prerequisites are met
- Fields must have specific values (or *sufficiently detailed* content)
- Work items must be correctly linked/parented
- Risk conditions (dates nearing, stale content) must be surfaced

Without enforcement, releases progress without proper gates, leading to incomplete releases and missed deadlines.

## Acceptance Criteria

### Gate Enforcement

1. **State transition detection**: Detect when a work item changes state
2. **Gate evaluation**: Check all gates defined for that transition
3. **Blocking**: If any gate fails, take enforcement action (comment, revert, escalate)
4. **Pass-through**: If all gates pass, allow the transition silently
5. **Audit trail**: Log all gate evaluations with pass/fail reasons

### Gate Types

| Gate Type | Description |
|-----------|-------------|
| `field_required` | Field exists and meets minimum length |
| `field_value` | Field matches one of allowed values |
| `field_pattern` | Field matches regex pattern |
| `linked_items` | Required relationships exist (min count, target type) |
| `parent_state` | Parent work item is in specified state(s) |
| `all_children_state` | All children are in specified state(s) |
| `semantic_quality` | LLM-evaluated content quality score |
| `date_not_past` | Date field hasn't passed |
| `custom_query` | ADO WIQL query returns expected results |

### Risk Assessment

6. **Continuous monitoring**: Check risk rules on every poll (not just state changes)
7. **Date proximity**: Warn when target dates approach
8. **Field staleness**: Flag fields unchanged for too long
9. **Risk escalation**: Create escalation work items or notify stakeholders

### Enforcement Actions

10. **Comment**: Add comment explaining gate failure with remediation guidance
11. **Tag**: Add risk/warning tag to work item
12. **Notify**: Send webhook notification to external system
13. **Escalate**: Create escalation work item linked to original
14. **Revert** (optional): Attempt to revert state via ADO API

## Interface

```python
# New module: src/ado_monitor/governor.py

@dataclass
class GateResult:
    passed: bool
    gate_type: str
    message: str
    details: dict[str, Any] | None = None

@dataclass
class GovernanceResult:
    allowed: bool
    gates_evaluated: list[GateResult]
    enforcement_actions: list[str]
    risks_detected: list[dict]

class LifecycleGovernor:
    def __init__(self, rules: GovernanceRules) -> None:
        """Initialize with governance rules."""

    async def evaluate_transition(
        self,
        work_item: dict,
        previous_state: str,
        current_state: str,
    ) -> GovernanceResult:
        """Evaluate if a state transition is allowed."""

    async def assess_risks(
        self,
        work_item: dict,
    ) -> list[RiskAssessment]:
        """Check for risk conditions on a work item."""
```

```python
# New module: src/ado_monitor/gates.py

class Gate(Protocol):
    async def evaluate(
        self,
        work_item: dict,
        config: dict,
        ado_client: ADOClient,
    ) -> GateResult:
        """Evaluate if gate passes."""

# Implementations
class FieldRequiredGate(Gate): ...
class FieldValueGate(Gate): ...
class LinkedItemsGate(Gate): ...
class SemanticQualityGate(Gate): ...
class DateNotPastGate(Gate): ...
```

## Configuration Schema

```yaml
# lifecycle-rules.yaml

# Global settings
settings:
  default_enforcement: comment  # comment | tag | notify | escalate | revert
  semantic_agent: ado-content-reviewer  # Agent for LLM evaluations
  notify_webhook: https://hooks.example.com/ado-governance

# Work item type rules
work_item_types:
  Release:
    # State machine with gates
    states:
      Planning:
        transitions:
          - to: Development
            gates:
              # Field must exist with meaningful content
              - type: field_required
                field: System.Description
                min_length: 200
                message: "Release description must be at least 200 characters"

              # Field must have specific value
              - type: field_value
                field: Custom.RiskAssessment
                allowed_values: ["Low", "Medium", "High"]
                message: "Risk assessment must be completed"

              # Must have child Features
              - type: linked_items
                link_type: Child
                target_type: Feature
                min_count: 1
                message: "Release must have at least one linked Feature"

              # LLM-evaluated content quality
              - type: semantic_quality
                field: System.AcceptanceCriteria
                criteria: |
                  The acceptance criteria must include:
                  - Clear, measurable success conditions
                  - At least 3 specific criteria
                  - No vague language like "should work well"
                min_score: 0.7
                message: "Acceptance criteria not sufficiently detailed"

      Development:
        transitions:
          - to: Testing
            gates:
              # All child Features must be Done
              - type: all_children_state
                target_type: Feature
                required_states: ["Done", "Closed"]
                message: "All Features must be completed before Testing"

              # Parent Epic must be in Development or later
              - type: parent_state
                required_states: ["Development", "Testing", "Release", "Closed"]
                message: "Parent Epic must be in Development or later"

      Testing:
        transitions:
          - to: Release
            gates:
              # Target date must not be past
              - type: date_not_past
                field: Custom.TargetReleaseDate
                message: "Cannot release after target date has passed"

              # All test work items must be Done
              - type: custom_query
                wiql: |
                  SELECT [System.Id] FROM WorkItems
                  WHERE [System.WorkItemType] = 'Test Case'
                  AND [System.State] <> 'Done'
                  AND [System.Parent] = {work_item_id}
                expect_count: 0
                message: "All test cases must be completed"

    # Risk rules (checked on every poll)
    risks:
      - type: date_proximity
        field: Custom.TargetReleaseDate
        thresholds:
          - days: 3
            severity: critical
            action: escalate
            message: "Release date is in 3 days or less"
          - days: 7
            severity: warning
            action: notify
            message: "Release date is within 1 week"
          - days: 14
            severity: info
            action: comment
            message: "Release date is within 2 weeks"

      - type: field_staleness
        field: System.Description
        max_days_unchanged: 30
        severity: warning
        action: tag
        tag: "stale-description"
        message: "Description unchanged for 30+ days"

      - type: blocked_duration
        max_days_in_state: 14
        states: ["Planning", "Development"]
        severity: warning
        action: notify
        message: "Work item stuck in {state} for {days} days"
```

## Semantic Quality Gate (LLM-Powered)

For "sufficiently detailed" requirements:

```python
# In gates.py
class SemanticQualityGate(Gate):
    async def evaluate(
        self,
        work_item: dict,
        config: dict,
        ado_client: ADOClient,
    ) -> GateResult:
        field_value = work_item.get("fields", {}).get(config["field"], "")

        # Invoke Amplifier agent
        result = await invoke_agent(
            agent=config.get("agent", "ado-content-reviewer"),
            instruction=f"""
                Evaluate the following content against these criteria:
                {config["criteria"]}

                Content to evaluate:
                ---
                {field_value}
                ---

                Return a JSON object with:
                - score: 0.0 to 1.0 quality score
                - reasoning: explanation of the score
                - suggestions: list of improvements if score < threshold
            """,
        )

        score = result.get("score", 0)
        passed = score >= config.get("min_score", 0.7)

        return GateResult(
            passed=passed,
            gate_type="semantic_quality",
            message=config.get("message", "Content quality check"),
            details={
                "score": score,
                "threshold": config.get("min_score", 0.7),
                "reasoning": result.get("reasoning"),
                "suggestions": result.get("suggestions", []),
            },
        )
```

## Integration with Monitor

```python
# In monitor.py - extend _poll_once

async def _poll_once(self, subscription: Subscription, poller: Poller) -> None:
    # ... existing polling code ...

    for event in events:
        # NEW: Governance check for state changes
        if event.event_type == EventType.WI_STATE_CHANGED:
            governance_result = await self.governor.evaluate_transition(
                work_item=current_snapshot.data,
                previous_state=event.payload["previous_state"],
                current_state=event.payload["current_state"],
            )

            if not governance_result.allowed:
                # Execute enforcement actions
                await self.enforcer.execute(
                    work_item_id=subscription.work_item_id,
                    result=governance_result,
                )
                # Skip normal dispatch for blocked transitions
                continue

        # ... existing dispatch code ...

    # NEW: Periodic risk assessment (every poll, not just on events)
    risks = await self.governor.assess_risks(current_snapshot.data)
    for risk in risks:
        await self.enforcer.handle_risk(
            work_item_id=subscription.work_item_id,
            risk=risk,
        )
```

## Database Schema Extensions

```sql
-- Gate evaluation history
CREATE TABLE gate_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_item_id INTEGER NOT NULL,
    transition_from TEXT NOT NULL,
    transition_to TEXT NOT NULL,
    gate_type TEXT NOT NULL,
    passed INTEGER NOT NULL,
    message TEXT,
    details TEXT,  -- JSON
    evaluated_at TEXT NOT NULL
);

CREATE INDEX idx_gate_work_item ON gate_evaluations(work_item_id);

-- Risk assessments
CREATE TABLE risk_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_item_id INTEGER NOT NULL,
    risk_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    action_taken TEXT,
    detected_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE INDEX idx_risk_work_item ON risk_assessments(work_item_id);
CREATE INDEX idx_risk_severity ON risk_assessments(severity);
```

## Files to Create/Modify

| File | Change |
|------|--------|
| `src/ado_monitor/governor.py` | **NEW** - Lifecycle state machine and gate orchestration |
| `src/ado_monitor/gates.py` | **NEW** - Gate type implementations |
| `src/ado_monitor/risks.py` | **NEW** - Risk detection rules |
| `src/ado_monitor/enforcement.py` | **NEW** - Action handlers (comment, tag, notify, escalate) |
| `src/ado_monitor/config.py` | Parse `lifecycle-rules.yaml` |
| `src/ado_monitor/monitor.py` | Integrate Governor into poll loop |
| `src/ado_monitor/state.py` | Add gate_evaluations and risk_assessments tables |
| `lifecycle-rules.yaml.example` | Example configuration |
| `tests/test_governor.py` | **NEW** - Gate evaluation tests |
| `tests/test_gates.py` | **NEW** - Individual gate type tests |
| `tests/test_risks.py` | **NEW** - Risk detection tests |

## Test Cases

### Gate Evaluation

1. `test_field_required_passes_with_sufficient_content`
2. `test_field_required_fails_with_empty_field`
3. `test_field_value_passes_with_allowed_value`
4. `test_field_value_fails_with_invalid_value`
5. `test_linked_items_passes_with_enough_links`
6. `test_linked_items_fails_with_missing_links`
7. `test_semantic_quality_passes_detailed_content`
8. `test_semantic_quality_fails_vague_content`
9. `test_date_not_past_passes_future_date`
10. `test_date_not_past_fails_past_date`
11. `test_all_children_state_passes_when_all_done`
12. `test_all_children_state_fails_with_incomplete_children`

### Risk Assessment

13. `test_date_proximity_critical_within_3_days`
14. `test_date_proximity_warning_within_7_days`
15. `test_field_staleness_detected_after_threshold`
16. `test_blocked_duration_detected_when_stuck`

### Enforcement

17. `test_comment_action_posts_to_work_item`
18. `test_tag_action_adds_tag`
19. `test_escalate_action_creates_linked_work_item`
20. `test_notify_action_sends_webhook`

### Integration

21. `test_blocked_transition_prevents_dispatch`
22. `test_allowed_transition_proceeds_normally`
23. `test_risks_assessed_on_every_poll`

## Edge Cases

- Work item type not in rules: Allow all transitions (pass-through)
- Transition not defined in rules: Allow (only explicit transitions are gated)
- Gate fails due to ADO API error: Log and treat as "cannot evaluate" (configurable: block or allow)
- Semantic agent unavailable: Fall back to basic length/pattern check
- Circular parent-child relationships: Detect and skip with warning
- Work item deleted during evaluation: Handle gracefully
- Multiple simultaneous state changes: Process sequentially per work item

## Dependencies

- Existing: `ADOClient` for link queries, `StateStore` for history
- New: Amplifier agent for semantic quality evaluation (`ado-content-reviewer`)
- Optional: Webhook endpoint for notifications

## Estimated Complexity

High - multiple new components with significant integration points.

**Recommended implementation order:**
1. `gates.py` with simple gates (field_required, field_value, date_not_past)
2. `governor.py` with basic evaluation loop
3. `enforcement.py` with comment action only
4. Integration tests
5. Add complex gates (linked_items, semantic_quality)
6. Add risk assessment
7. Add remaining enforcement actions
