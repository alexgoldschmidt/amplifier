---
bundle:
  name: amplifier-azure-devops
  version: 1.0.0
  description: |
    Root bundle for Azure DevOps integration.
    Re-exports the full azure-devops bundle for simpler git references.

includes:
  - bundle: foundation
  - bundle: azure-devops:bundle

sources:
  azure-devops: ./amplifier-bundle-azure-devops
  ado-pr: ./amplifier-bundle-ado-pr
  ado-work-items: ./amplifier-bundle-ado-work-items
  ado-research: ./amplifier-bundle-ado-research
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

See [amplifier-bundle-azure-devops/bundle.md](./amplifier-bundle-azure-devops/bundle.md) for full details.
