# Research Cache Schema

## Location

```
~/.amplifier/ado-research-cache/{org}/{project}/{repo}.yaml
```

One file per configured repository. Created on first access, grows as pages are visited.

## Schema

```yaml
version: 1
repo: cloudfit-docs
org: msazure
project: one

entries:
  "/toc.yaml":
    type: toc            # toc | content
    fetched_at: "2026-03-07T21:00:00Z"
    commit: "abc123"
    content: |           # Full content for TOC files (small, structural)
      - name: Getting Started
        href: getting-started/
      - name: Guides
        href: guides/

  "/guides/toc.yaml":
    type: toc
    fetched_at: "2026-03-07T21:01:00Z"
    commit: "abc123"
    content: |
      - name: Deployment Rings
        href: deployment-rings.md
      - name: Safe Rollout
        href: safe-rollout.md

  "/guides/deployment-rings.md":
    type: content
    fetched_at: "2026-03-07T21:02:00Z"
    commit: "abc123"
    title: "Deployment Rings"
    summary: "Progressive ring-based deployment: Ring 0 (canary) → Ring 3 (full). Each ring has health gates..."
    # Full content NOT stored — refetch on demand when needed
```

## Entry Types

### `toc` entries
- **Stored**: Full YAML content (typically <1KB)
- **Purpose**: Enable navigation without refetching
- **Invalidation**: Explicit refresh command or 404 on child lookup

### `content` entries
- **Stored**: Title + summary (2-3 sentences)
- **NOT stored**: Full file content
- **Purpose**: Enable search/relevance matching without refetching
- **Full content**: Refetched on demand when user needs details

## Cache Operations

### Read-through (on cache miss)
```
fetch(repo, path):
  1. Check cache for path
  2. If hit → return cached entry
  3. If miss → fetch from ADO API
  4. Determine type (toc vs content)
  5. For toc: store full content
  6. For content: store title + summary, return full content
  7. Write cache file
```

### Invalidation
- **No TTL** — cache entries persist until explicitly refreshed
- **Refresh command**: "refresh {repo-alias}" clears all entries for that repo
- **404 handling**: If a cached path returns 404, remove entry and re-navigate from parent TOC
- **Stale detection**: Compare commit SHA on refetch; if changed, update entry

## Cache Size

Typical research session caches ~10-20 entries per repo:
- 3-5 TOC files (~5KB total)
- 5-15 content summaries (~3KB total)
- Total: <10KB per repo — negligible

## Directory Creation

```bash
mkdir -p ~/.amplifier/ado-research-cache/{org}/{project}
```
