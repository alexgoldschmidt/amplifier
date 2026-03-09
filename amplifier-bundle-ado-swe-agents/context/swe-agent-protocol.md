# SWE Agent Protocol

GitHub Copilot's SWE Agent monitors Azure DevOps for specially-configured work items
and automatically creates pull requests to implement them.

## SWE Agent Task Requirements

A work item triggers the SWE Agent when ALL of these conditions are met:

| Requirement | Field | Value |
|-------------|-------|-------|
| Type | System.WorkItemType | `Task` |
| Assignee | System.AssignedTo | `GitHub Copilot` |
| Repository | Link OR Tag | See linking methods below |

## Repository Linking Methods

**Important:** Use only ONE method per work item. Do not combine artifact links with tags.

### Method 1: Artifact Link (Traditional)

Link a branch via ADO's native linking:
1. Go to work item → "Links" tab → "Add Link" → "Branch"
2. Or use the "Deployment" section in the "Details" tab

### Method 2: Repository Tag (Flexible)

Add a tag with format:
```
copilot:repo=<orgName>/<projectName>/<repoName>@<branchName>
```

**Examples:**
- `copilot:repo=MyOrg/MyProject/MyRepo@main`
- `copilot:repo=MyOrg/MyProject/MyRepo@feature-branch`

**Notes:**
- Branch name after `@` is **required**
- Links the target branch (usually `main` or `master`)
- Creating a new branch is NOT required
- Supports cross-organization scenarios

## SWE Agent Behavior

When a properly configured task is detected, the SWE Agent will:

1. Create a draft/WIP pull request
2. Add a comment to the work item with the PR link
3. Link the PR to the work item
4. Begin implementing the solution based on the description

## Specialized Agents

Specialized agents extend the default SWE Agent with domain-specific tools and instructions.
They are registered in the target repository via `.azuredevops/policies/*.yml` files.

### Discovering Available Agents

**Always discover available agents before creating a task.** The target repo may have
specialized agents that are better suited for specific work types.

Check `.azuredevops/policies/` directory for YAML files containing `specializedAgent:` configuration.

### Specifying an Agent

Use the `copilot:agent=<name>` tag to route the task to a specific specialized agent:

| Tag Pattern | Purpose |
|-------------|---------|
| `copilot:agent=<name>` | Route to a specific specialized agent |
| `copilot:priority=<level>` | Hint processing priority |

Example: `copilot:agent=ComponentGovernanceAgent`

### Policy Configuration Schema

Specialized agents are defined in `.azuredevops/policies/*.yml`:

```yaml
# metadata
name: Copilot pair programmer, specialized agents
description: A component governance agent that adds CG specific tools and instructions

# filters
resource: repository

# primitive configuration
configuration:
  copilotConfiguration:
    specializedAgent:
      name: ComponentGovernanceAgent          # Agent identifier (use in copilot:agent= tag)
      disable: false                          # true to disable this agent
      description: An agent specialized in... # Human-readable description
      excludeGitHubCopilotInstructions: false # true to ignore repo-level instructions
      servers:                                # MCP servers the agent can access
        - name: AzureDevOps
          tools:
            - get_component_governance_alert
            - get_component_governance_instructions
      copilotInstructions: |                  # Agent-specific instructions
        You are a specialized agent focused on...
```

### Key Configuration Properties

| Property | Description |
|----------|-------------|
| `name` | Agent identifier (e.g., `ComponentGovernanceAgent`) |
| `disable` | Set to `true` to disable, `false` to enable |
| `description` | Human-readable description of the agent's purpose |
| `excludeGitHubCopilotInstructions` | `true` to ignore repository-level `.github/copilot-instructions.md` |
| `servers` | List of MCP servers and their tools the agent can access |
| `copilotInstructions` | Direct instructions for the agent (optional if using repo-level instructions) |

### Common Specialized Agent Types

| Agent Type | Use For |
|------------|---------|
| `ComponentGovernanceAgent` | Resolving component governance / dependency alerts |
| `SecurityReviewAgent` | Security-focused code changes |
| `TestingAgent` | Test coverage improvements |
| `DocumentationAgent` | Documentation updates |
| `RefactoringAgent` | Code refactoring tasks |

## Best Practices

### Writing Effective Descriptions

The SWE Agent uses the task description to understand what to implement:

```html
<h3>Problem</h3>
<p>Brief description of what needs to be done</p>

<h3>Requirements</h3>
<ul>
  <li>Specific requirement 1</li>
  <li>Specific requirement 2</li>
</ul>

<h3>Acceptance Criteria</h3>
<ul>
  <li>How to verify the implementation is correct</li>
</ul>
```

### Task Scope

- Keep tasks focused and atomic
- One logical change per task
- Include relevant file paths if known
- Reference existing code patterns to follow
