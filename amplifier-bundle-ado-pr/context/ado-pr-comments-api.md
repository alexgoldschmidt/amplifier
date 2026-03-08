# Azure DevOps PR Comments REST API

The `az repos` CLI doesn't cover PR comment threads well. Use `az rest` with the Azure DevOps resource ID.

## Preferred Method: az rest

**Always use `az rest` with `--resource` for Azure DevOps API calls** — curl has HTTP/2 protocol issues with ADO.

```bash
# List threads
az rest --method get \
  --resource "499b84ac-1321-427f-aa17-267ca6975798" \
  --uri "https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{prId}/threads?api-version=7.1"

# Add reply to thread
az rest --method post \
  --resource "499b84ac-1321-427f-aa17-267ca6975798" \
  --uri "https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{prId}/threads/{threadId}/comments?api-version=7.1" \
  --body '{"content": "🤖 [Amplifier] Fixed in commit abc123 - description of fix.", "commentType": 1}'
```

**Note:** The resource ID `499b84ac-1321-427f-aa17-267ca6975798` is the Azure DevOps API resource.

## AI-Generated Comment Indicator

**All AI-generated comments MUST include the `🤖 [Amplifier]` prefix** to clearly indicate automated responses:

```
🤖 [Amplifier] Fixed in commit dc0017b - added example showing how to get pipeline ID by name.
```

This ensures:
- Reviewers know the response is AI-generated
- Transparency about automated PR management
- Easy filtering/searching for AI comments

## Base URL Pattern

```
https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{prId}/threads
```

## Alternative: curl (not recommended)

If you must use curl, be aware of HTTP/2 protocol issues with ADO:

```bash
TOKEN=$(az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{prId}/threads?api-version=7.1"
```

**Response structure:**
```json
{
  "value": [
    {
      "id": 12345,
      "status": "active",
      "threadContext": {
        "filePath": "/src/example.py",
        "rightFileStart": { "line": 42, "offset": 1 },
        "rightFileEnd": { "line": 42, "offset": 10 }
      },
      "comments": [
        {
          "id": 1,
          "author": { "displayName": "Reviewer Name" },
          "content": "Please add another example here",
          "commentType": "text",
          "publishedDate": "2024-01-15T10:30:00Z"
        }
      ]
    }
  ]
}
```

## Thread Types: File-Level vs PR-Level

**Critical distinction for filtering:**

| Type | `threadContext` | Example |
|------|-----------------|---------|
| File-level comments | `{ "filePath": "/src/file.py", ... }` | Inline code review comments |
| PR-level comments | `null` | Main thread, general feedback |

**Always handle both when fetching comments:**

```bash
# Filter function that handles both types
file_path = thread.get('threadContext', {}).get('filePath') if thread.get('threadContext') else '(PR main thread)'
```

## Parsing Warning: az rest Output

**IMPORTANT:** `az rest` may emit warnings to stdout before JSON:

```
WARNING: Unable to encode the output with cp1252 encoding. Unsupported characters are discarded.
{"count": 5, "value": [...]}
```

**Solutions:**
```bash
# Option 1: Redirect stderr (doesn't help - warning is on stdout)
# Option 2: Use python to safely parse
az rest ... 2>/dev/null | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)))"

# Option 3: Skip non-JSON lines
az rest ... | grep -v "^WARNING:" | jq '...'
```

## Filter Active (Unresolved) Threads

**Basic filter (file-level only):**
```bash
az rest ... | jq '.value[] | select(.status == "active" and .threadContext != null)'
```

**Complete filter (both file-level and PR-level):**
```bash
az rest --method get \
  --resource "499b84ac-1321-427f-aa17-267ca6975798" \
  --uri "https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{prId}/threads?api-version=7.1" \
  2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
for t in data.get('value', []):
    comments = t.get('comments', [])
    if comments and comments[0].get('commentType') == 'text' and t.get('status') == 'active':
        file_path = t.get('threadContext', {}).get('filePath') if t.get('threadContext') else '(PR main thread)'
        print(f'Thread {t[\"id\"]}: {file_path}')
        print(f'  {comments[0][\"author\"][\"displayName\"]}: {comments[0][\"content\"][:200]}')
"
```

## Add Reply to Thread

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{prId}/threads/{threadId}/comments?api-version=7.1" \
  -d '{
    "content": "Fixed in commit abc123 — added another example",
    "commentType": "text"
  }'
```

## Update Thread Status

```bash
curl -s -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{prId}/threads/{threadId}?api-version=7.1" \
  -d '{"status": "fixed"}'
```

## Thread Status Values

| Status | Meaning |
|--------|---------|
| `active` | Open, needs attention |
| `fixed` | Author indicates it's fixed (reviewer can reopen) |
| `wontFix` | Author won't address this |
| `closed` | Resolved, no further action |
| `byDesign` | Intentional behavior |
| `pending` | Waiting for something |

## Common Patterns

### Get all unresolved comments with file context

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://dev.azure.com/$ORG/$PROJECT/_apis/git/repositories/$REPO/pullRequests/$PR_ID/threads?api-version=7.1" \
  | jq '[.value[] | select(.status == "active") | {
      threadId: .id,
      file: .threadContext.filePath,
      line: .threadContext.rightFileStart.line,
      author: .comments[0].author.displayName,
      comment: .comments[0].content
    }]'
```

### Reply and mark as fixed in one flow

```bash
# Reply first
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://dev.azure.com/$ORG/$PROJECT/_apis/git/repositories/$REPO/pullRequests/$PR_ID/threads/$THREAD_ID/comments?api-version=7.1" \
  -d '{"content": "Fixed in commit xyz", "commentType": "text"}'

# Then update status (only if user confirms)
curl -s -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://dev.azure.com/$ORG/$PROJECT/_apis/git/repositories/$REPO/pullRequests/$PR_ID/threads/$THREAD_ID?api-version=7.1" \
  -d '{"status": "fixed"}'
```
