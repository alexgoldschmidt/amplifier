# Test Config Schema

## File: `.amplifier/ado-test-config.yaml`

```yaml
version: 1

# Unit test configuration
unit_tests:
  project: tests/MyService.Tests/MyService.Tests.csproj  # Path to test project
  logger: trx                    # Output format (trx for .NET)
  results_dir: TestResults/      # Where to store results

# Local service testing
local_service:
  methods:
    # dotnet run method
    dotnet:
      project: src/MyService/MyService.csproj
      args: ["--urls", "http://localhost:5000"]
    
    # docker-compose method
    docker:
      compose_file: docker-compose.yml
      services: [api, db]        # Which services to start
    
    # Manual (service already running)
    manual:
      base_url: http://localhost:5000

  # Environment variables for local testing
  environment:
    ASPNETCORE_ENVIRONMENT: Development
    # Azure auth handled by DefaultAzureCredential

  # Smoke tests to run after service starts
  smoke_tests:
    - name: health
      method: GET
      url: /health
      expect_status: 200
    - name: api-version
      method: GET
      url: /api/version
      expect_status: 200

# Work item linking for failures
failure_linking:
  auto_create_bugs: false        # Create bugs for new failures
  link_existing: true            # Link to existing bugs
```

## Service Start Priority

Agent tries methods in order:
1. `dotnet` if configured
2. `docker` if configured
3. `manual` (assume already running)

User can override: "start service with docker"
