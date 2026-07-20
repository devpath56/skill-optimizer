# Design Doc: Rate Limiter (v2)

**Author:** platform team · **Status:** for review

## Goal
Add a reusable rate limiter that any service can call to cap requests per client.

## Interface
One deep method behind a narrow interface:

```
class RateLimiter:
    def allow(self, client_id: str) -> bool:
        """Return True if this client is under its limit, False otherwise.
        Caller needs to know nothing about windows, buckets, or storage."""
```

All policy (window size, burst, backing store, clock) lives inside the module and is
configured once at construction. Callers pass a `client_id` and get a boolean. Swapping
the algorithm (fixed window → token bucket) changes nothing for any caller.

## Storage
State is held behind a `Store` port with a single `incr(key, ttl)` method, so the
in-memory implementation used in tests and the Redis implementation used in prod are
interchangeable and neither leaks into the limiter's interface.

## Rollout
Ship behind a flag, load-test at 2x peak, then GA.
