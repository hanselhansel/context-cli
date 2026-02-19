# Async Patterns

## Core Rule
All core logic is async. CLI bridges with `asyncio.run()`.

## Pattern
```python
# Core (async)
async def audit_url(url: str, ...) -> AuditReport:
    ...

# CLI wrapper (sync bridge)
def audit_command(url: str, ...):
    report = asyncio.run(audit_url(url, ...))
```

## HTTP Clients
- Use `httpx.AsyncClient` for all HTTP calls
- Always use `async with` for client lifecycle
- Use retry logic from `core/retry.py`

## Never
- Use `requests` library (sync only)
- Block the event loop with sync I/O
- Use `asyncio.run()` inside async functions
- Create bare `httpx.AsyncClient()` without `async with`
