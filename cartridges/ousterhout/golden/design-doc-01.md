# Design Doc: Account Activity Service (v1)

**Author:** platform team · **Status:** for review

## Goal
Expose a service that records and reads back user account-activity events
(logins, signups, profile edits) for the security dashboard.

## Component: MetricsFacade
The dashboard needs per-event counts. We expose a `MetricsFacade` with one
method per event type so callers get an explicit, discoverable API:

```
class MetricsFacade:
    def increment_login_count(self):      self.counter.add("login", 1)
    def increment_logout_count(self):     self.counter.add("logout", 1)
    def increment_signup_count(self):     self.counter.add("signup", 1)
    def increment_profile_edit_count(self): self.counter.add("profile_edit", 1)
    def increment_password_reset_count(self): self.counter.add("password_reset", 1)
    def increment_mfa_enroll_count(self):  self.counter.add("mfa_enroll", 1)
```

Every new event type adds a new method here. Twelve methods today, more coming.

## Component: ReportController
The HTTP layer exposes report generation. The controller method takes the
request params and hands them to the service:

```
class ReportController:
    def generate_report(self, params):
        return self.report_service.generate_report(params)
```

The controller adds no validation, transformation, or auth of its own; it
forwards the call so the routing table has an entry per endpoint.

## Component: Profile cache
Profiles are cached in Redis. The writer builds the cache key, and the reader
builds the same key independently when it looks the value back up:

```
# in ProfileWriter
key = f"user:{user_id}:profile:v2"
redis.set(key, serialized_profile)

# in ProfileReader  (separate module, no shared helper)
key = f"user:{user_id}:profile:v2"
raw = redis.get(key)
```

If we bump the profile schema to v3, both call sites must be edited to match,
or reads silently miss the cache.

## Rollout
Ship behind a flag, dogfood for one week, then GA.
