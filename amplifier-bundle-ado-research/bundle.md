---
bundle:
  name: ado-research
  version: 1.0.0
  description: |
    Research documentation across Azure DevOps repositories that serve EngHub.
    
    Uses docfx toc.yaml structure for lazy, on-demand navigation.
    Never bulk-downloads repos — fetches only what's needed, caches for reuse.
    
    Prerequisites:
    - Azure CLI with devops extension: az extension add --name azure-devops
    - Authenticated: az login
    - Config file: .amplifier/ado-research-config.yaml

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

agents:
  include:
    - ado-research:agents/ado-researcher

context:
  include:
    - ado-research:context/docfx-navigation.md
    - ado-research:context/research-cache-schema.md

---

# ADO Research Bundle

Research EngHub documentation across Azure DevOps repositories using lazy, toc-driven navigation.

## How It Works

```
Query: "how do deployment rings work?"

1. Load root toc.yaml (cache hit or fetch)
   └── "Guides" section matches → href: guides/

2. Load /guides/toc.yaml (cache hit or fetch)
   └── "Deployment Rings" → href: deployment-rings.md

3. Fetch /guides/deployment-rings.md → read, summarize, cite

Result: 3 files touched. Rest of repo never fetched.
```

## Setup

Create `.amplifier/ado-research-config.yaml` in your repo:

```yaml
version: 1
defaults:
  org: msazure
  project: one
  branch: main

repos:
  cloudfit-docs:
    description: "CloudFit engineering standards and practices"
    repo: cloudfit-docs
    docs_root: "/docs"        # where toc.yaml lives (default: "/")
    enghub:
      base_url: "https://eng.ms/docs/products/cloudfit"
      path_prefix: "/docs"

  onebranch-docs:
    description: "OneBranch build system documentation"
    repo: azure-onebranch-docs
    docs_root: "/"            # toc.yaml at repo root
    enghub:
      base_url: "https://eng.ms/docs/products/onebranch"
      path_prefix: "/docs"

  # Per-repo overrides (optional — falls back to defaults)
  external-docs:
    description: "External team documentation"
    org: msazure              # override org
    project: other-project    # override project
    branch: docs              # override branch
    repo: ext-team-docs
    docs_root: "/content"
    enghub:
      base_url: "https://eng.ms/docs/products/external"
      path_prefix: "/content"
```

## Key Agent

- `ado-researcher` — Lazy toc-driven research with EngHub citations

## Bundle Composition

```
ado-research
├── azure-devops-extras (repo read via az repos / az rest)
└── ado-researcher (toc navigation, lazy cache, citation)
```
