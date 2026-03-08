# DocFX Navigation Structure

EngHub repositories use [DocFX](https://dotnet.github.io/docfx/) for documentation. The key navigation primitive is `toc.yaml` (Table of Contents).

## TOC Hierarchy

```
repo-root/
├── toc.yaml                 ← Root: top-level sections
├── getting-started/
│   ├── toc.yaml             ← Section: pages within getting-started
│   ├── overview.md
│   └── quickstart.md
├── guides/
│   ├── toc.yaml             ← Section: pages within guides
│   ├── deployment-rings.md
│   └── safe-rollout.md
└── reference/
    ├── toc.yaml
    └── api.md
```

## TOC Format

### Section reference (points to subdirectory)
```yaml
- name: Getting Started
  href: getting-started/
  
- name: Guides
  href: guides/
```

### Leaf reference (points to content file)
```yaml
- name: Deployment Rings
  href: deployment-rings.md

- name: Safe Rollout
  href: safe-rollout.md
```

### Nested inline (items within a section)
```yaml
- name: Guides
  items:
    - name: Deployment Rings
      href: deployment-rings.md
    - name: Safe Rollout
      href: safe-rollout.md
```

## Navigation Rules

1. **Root toc.yaml is always the entry point** — fetch this first
2. **href ending in `/`** → subdirectory with its own toc.yaml
3. **href ending in `.md` or `.yml`** → leaf content file
4. **`items:` array** → inline children (no separate toc.yaml needed)
5. **`homepage:` field** → default page for a section
6. **Relative paths** — all hrefs are relative to the toc.yaml's directory

## Fetching a TOC via ADO REST API

```bash
# Get file content from a repo at a specific path
az rest --method get \
  --uri "https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/items?path={path}&api-version=7.1" \
  --query "content" -o tsv
```

Or for raw content:

```bash
az rest --method get \
  --uri "https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/items?path=/toc.yaml&api-version=7.1&includeContent=true" \
  2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['content'])"
```

## EngHub URL Construction

Given config:
```yaml
enghub:
  base_url: "https://eng.ms/docs/products/cloudfit"
  path_prefix: "/docs"
```

And file path `/docs/guides/deployment-rings.md`:

1. Strip `path_prefix` → `guides/deployment-rings.md`
2. Strip `.md` extension → `guides/deployment-rings`
3. Append to `base_url` → `https://eng.ms/docs/products/cloudfit/guides/deployment-rings`
