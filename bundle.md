---
bundle:
  name: amplifier-azure-devops
  version: 1.0.0
  description: |
    Root bundle for Azure DevOps integration.
    Re-exports the full azure-devops bundle for simpler git references.

includes:
  - bundle: git+https://github.com/alexgoldschmidt/amplifier@master#subdirectory=amplifier-bundle-azure-devops

tools:
  - module: tool-filesystem
    source: git+https://github.com/microsoft/amplifier-module-tool-filesystem@main
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@main
  - module: tool-web
    source: git+https://github.com/microsoft/amplifier-module-tool-web@main
  - module: tool-search
    source: git+https://github.com/microsoft/amplifier-module-tool-search@main
---

# Amplifier Azure DevOps

Root bundle that re-exports the full Azure DevOps integration.

## Usage

```yaml
bundles:
  - git+https://github.com/alexgoldschmidt/amplifier@master
```

No `#subdirectory` needed - this root bundle includes everything.

## What's Included

See [amplifier-bundle-azure-devops/bundle.md](git+https://github.com/alexgoldschmidt/amplifier@master#subdirectory=amplifier-bundle-azure-devops/bundle.md) for full details.
