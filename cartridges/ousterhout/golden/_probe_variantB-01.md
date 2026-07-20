# Ousterhout Guru Review: Account Activity Service (v1)

## 1. Complexity Diagnosis

The dominant symptom here is **change amplification**: a single conceptual change forces edits in many places. Adding one new event type is not one edit — it is a new method on `MetricsFacade`, and the doc admits this is a growing set ("Twelve methods today, more coming"). Bumping the profile cache schema from v2 to v3 is not one edit either — it is two independent edits, in two modules, that must stay in lockstep or reads silently miss.

There is also **cognitive load**: a reader cannot understand the profile cache by looking at one place, because the key format lives in two modules with no shared owner. And there is a lurking **unknown unknown**: nothing tells a future engineer that changing the writer's key requires a matching change to the reader — the coupling is invisible until the cache silently stops hitting in production.

The through-line: this design spreads knowledge that should live behind a single interface across many call sites.

## 2. Red Flags Found

**Information Leakage — the profile cache key format is duplicated across `ProfileWriter` and `ProfileReader`.**

- *What triggered it:* The same design decision — the Redis key format `user:{user_id}:profile:v2` — is embedded independently in two separate modules, with the doc explicitly noting "separate module, no shared helper." A single piece of knowledge (how a profile is addressed in the cache) has leaked into two places.
- *Consequence:* This is Ousterhout's information leakage in its purest form, and it is the most severe issue in this doc because the failure mode is *silent*. When the schema moves to v3, if only one call site is updated, there is no exception, no compile error, no failed test — reads simply miss the cache and fall through, degrading performance (or worse, correctness if the fallback path differs) with no signal. The knowledge should live behind one function — e.g. `profile_cache_key(user_id)` — that both writer and reader call, so the format is defined exactly once. As written, every schema bump is a change-amplification event with a built-in silent-failure trap.

## 3. Tactical vs. Strategic Assessment

This is **tactical programming**. Each component takes the path that is fastest to write right now: expose one method per event type, forward the controller call verbatim, inline the cache key wherever it is needed. Nothing here is wrong in the "it doesn't work" sense — it works today. That is exactly the trap Ousterhout warns about: tactical tornadoes leave working code that quietly raises the cost of every future change.

The compounding cost, if this becomes the team's pattern: the metrics API grows a new method per event forever; the cache-key duplication becomes the template other cached entities copy; and each of these "small" shortcuts individually looks too minor to fix, so none of them ever gets fixed. Complexity accrues in increments no one blocks on, and eighteen months later the service is the one nobody wants to touch. Strategic programming would spend the extra hour now to design an interface that absorbs future change instead of amplifying it.

## 4. Design it Twice

**Alternative for the metrics API:** Instead of `increment_login_count`, `increment_signup_count`, and a new method per event forever, expose a single deep method: `record_event(event_type)`. The event type becomes a parameter, not a method name. One method handles all current and future event types; adding an event becomes zero API changes rather than one. The interface gets *simpler* as the system grows, which is the signature of a deep module.

**Alternative for the cache key (directly addressing the reported red flag):** Introduce one owner of the key format — a `ProfileCacheKey.build(user_id)` helper (or a small `ProfileCache` module that owns both get and set). Both writer and reader call it. The v2→v3 bump becomes a one-line change in exactly one place, and it is impossible for the two sides to drift out of sync because there is only one side.

Forcing this comparison is the point: the "one method per event / inline the key" design is the first thing that comes to mind, and it is measurably worse on change cost than the second design, which costs roughly the same to build.

## 5. PM Actions

**What to ask engineers:**
- "When we add the next event type, how many files change? Can we get that to zero?"
- "Who owns the profile cache key format? If the answer is 'both the reader and the writer,' that's a bug waiting to happen — can one function own it?"
- "Is `ReportController.generate_report` doing anything the service isn't? If not, what is the layer buying us?"

**What to protect even under time pressure:**
- The single-owner rule for the cache key. This is cheap now and a silent production incident later; do not let it ship duplicated to save an hour.

**What to include in the PRD / technical spec:**
- A stated interface principle: knowledge that appears in two places (key formats, event enumerations, serialization schemes) must have exactly one owner behind a function or module.
- An explicit "cost of adding an event type" acceptance criterion — target zero API surface changes — so the metrics interface is designed for growth rather than accreting a method per event.
