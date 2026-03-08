# Feature Spec: Exponential Backoff on API Failures

## Overview

When ADO API calls fail due to transient errors (rate limiting, network issues, service unavailable), the poller should retry with exponential backoff instead of failing immediately or retrying at a fixed interval.

## Acceptance Criteria

1. **Retryable errors are identified**: HTTP 429 (rate limit), 500, 502, 503, 504, and network timeouts
2. **Non-retryable errors fail fast**: HTTP 400, 401, 403, 404 should not retry
3. **Backoff timing**: Initial delay 1s, doubles each retry, max 5 retries, max delay 60s
4. **Jitter**: Add ±20% random jitter to prevent thundering herd
5. **Logging**: Each retry logs the attempt number, delay, and error
6. **429 handling**: If 429 includes `Retry-After` header, use that instead of calculated delay
7. **Per-subscription isolation**: One subscription's backoff doesn't affect others

## Interface

```python
# New module: src/ado_monitor/retry.py

@dataclass
class RetryConfig:
    max_retries: int = 5
    initial_delay: float = 1.0
    max_delay: float = 60.0
    jitter_factor: float = 0.2
    retryable_statuses: set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})

async def with_retry(
    func: Callable[[], Awaitable[T]],
    config: RetryConfig = RetryConfig(),
) -> T:
    """Execute an async function with exponential backoff retry."""
```

## Files to Modify

| File | Change |
|------|--------|
| `src/ado_monitor/retry.py` | **NEW** - Retry logic with backoff |
| `src/ado_monitor/poller.py` | Wrap API calls with `with_retry()` |
| `tests/test_retry.py` | **NEW** - Unit tests for retry behavior |

## Test Cases

1. `test_no_retry_on_success` - Successful call returns immediately
2. `test_retry_on_429` - 429 triggers retry with backoff
3. `test_retry_on_500` - Server errors trigger retry
4. `test_no_retry_on_401` - Auth errors fail fast
5. `test_respects_retry_after_header` - Uses Retry-After when present
6. `test_max_retries_exceeded` - Raises after max attempts
7. `test_jitter_applied` - Delays vary by jitter factor
8. `test_backoff_doubles` - Each retry doubles delay (up to max)

## Edge Cases

- Retry-After header with value > max_delay: Use max_delay
- Network timeout (no response): Treat as retryable
- Partial response before failure: Start fresh on retry

## Dependencies

None - pure Python async implementation.

## Estimated Complexity

Low - isolated module, well-defined behavior, easy to test.
