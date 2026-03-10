# PR Summary Table Formatting

When presenting a summary of active PRs, use a rich, interactive table that enables quick navigation and decision-making.

## Rendering Rule: No Code Fences

**Output markdown tables directly — do NOT wrap in code fences.**

Amplifier's streaming UI renders markdown tables with clickable hyperlinks. Wrapping in triple backticks turns the table into plain text and breaks link interactivity.

✅ Correct — raw markdown, links are clickable:

| PR | Title | Author | Status | Age |
|----|-------|--------|--------|-----|
| [14892](https://dev.azure.com/contoso/web/_git/app/pullrequest/14892) | Add OAuth2 refresh token handling | J. Smith | 🟢 | 1d |

❌ Wrong — code fence disables link rendering:

```
| PR | Title | ...
```

## Required Columns

| Column | Content | Format |
|--------|---------|--------|
| **PR** | PR number with link | `[12345](https://dev.azure.com/org/project/_git/repo/pullrequest/12345)` |
| **Title** | PR title (truncate at ~50 chars) | Plain text with `...` if truncated |
| **Author** | Who created it | Display name |
| **Status** | Review state | Use emoji indicators (see below) |
| **Comments** | Active thread count | `💬 3` or `✅` if none |
| **Age** | Time since creation | `2d`, `1w`, `3mo` |
| **Target** | Target branch | `main`, `release/v2` |

## Status Emoji Indicators

| Emoji | Meaning |
|-------|---------|
| 🟢 | Approved, ready to merge |
| 🟡 | Waiting for review |
| 🔴 | Changes requested |
| 🟣 | Draft |
| ⏳ | Has pending checks |
| 🔀 | Has merge conflicts |

## Example Output

## Active PRs — contoso/web-app

| PR | Title | Author | Status | Comments | Age | Target |
|----|-------|--------|--------|----------|-----|--------|
| [14892](https://dev.azure.com/contoso/web/_git/web-app/pullrequest/14892) | Add OAuth2 refresh token handling | J. Smith | 🟢 | ✅ | 1d | main |
| [14887](https://dev.azure.com/contoso/web/_git/web-app/pullrequest/14887) | Fix race condition in cache inv... | A. Chen | 🔴 | 💬 2 | 3d | main |
| [14879](https://dev.azure.com/contoso/web/_git/web-app/pullrequest/14879) | [DRAFT] Experiment: Redis cluster | M. Kumar | 🟣 | 💬 5 | 1w | feature/redis |

📊 **3 active PRs** — 1 ready to merge, 1 needs revision, 1 draft

---

## Multi-Repo Summary

When summarizing across multiple repositories, group by repo with a sub-heading:

### web-app (2 PRs)

| PR | Title | Author | Status | Comments | Age |
|----|-------|--------|--------|----------|-----|
| [14892](https://dev.azure.com/contoso/web/_git/web-app/pullrequest/14892) | Add OAuth2 refresh token handling | J. Smith | 🟢 | ✅ | 1d |
| [14887](https://dev.azure.com/contoso/web/_git/web-app/pullrequest/14887) | Fix race condition... | A. Chen | 🔴 | 💬 2 | 3d |

### api-gateway (1 PR)

| PR | Title | Author | Status | Comments | Age |
|----|-------|--------|--------|----------|-----|
| [156](https://dev.azure.com/contoso/web/_git/api-gateway/pullrequest/156) | Rate limiting middleware | S. Patel | 🟡 | 💬 1 | 5d |

---
📊 **Summary:** 3 PRs across 2 repos — 1 approved, 1 needs changes, 1 awaiting review

## Formatting Rules

1. **No code fences** — Output raw markdown so Amplifier's streaming UI renders clickable links
2. **No `!` prefix on PR numbers** — Just the number: `14892`, not `!14892`
3. **Always use clickable links** — The PR number column must link directly to the PR URL
4. **Truncate long titles** — Keep table scannable; use `...` for titles > 50 chars
5. **Sort by urgency** — Approved first (ready to act), then changes requested, then waiting, then drafts
6. **Relative ages** — Use human-readable durations (`2d`, `1w`) not timestamps
7. **Include summary line** — End with a count and status breakdown

## API Call to Fetch PR List

```bash
az repos pr list \
  --organization "https://dev.azure.com/{org}" \
  --project "{project}" \
  --repository "{repo}" \
  --status active \
  --output json
```

Or via REST for more control:

```bash
az rest --method get \
  --resource "499b84ac-1321-427f-aa17-267ca6975798" \
  --uri "https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pullrequests?searchCriteria.status=active&api-version=7.1"
```
