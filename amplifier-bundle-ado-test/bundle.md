---
bundle:
  name: ado-test
  version: 1.0.0
  description: |
    Local test execution and pipeline test result analysis for .NET projects.
    
    Runs unit tests locally, starts services for integration testing,
    parses TRX results from pipelines, and links failures to work items.
    
    Prerequisites:
    - .NET SDK installed: dotnet --version
    - Azure CLI for pipeline queries: az login
    - Optional: Docker for docker-compose testing

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

agents:
  include:
    - ado-test:agents/ado-test-runner

context:
  include:
    - ado-test:context/test-config-schema.md
    - ado-test:context/trx-parsing.md

tools:
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@v1.0.0
---

# ADO Test Bundle

Local test execution and pipeline result analysis.

## Quick Start

```bash
# Run unit tests
"run the unit tests"

# Start local service and run smoke tests
"start the service locally and test it"

# Analyze recent pipeline test results
"show me test failures from the last pipeline run"
```

## Configuration

Create `.amplifier/ado-test-config.yaml`:

```yaml
version: 1
unit_tests:
  project: tests/MyService.Tests/MyService.Tests.csproj
  logger: trx
  results_dir: TestResults/

local_service:
  methods:
    dotnet:
      project: src/MyService/MyService.csproj
      args: ["--urls", "http://localhost:5000"]
```
