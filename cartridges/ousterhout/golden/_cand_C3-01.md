# Ousterhout Guru Review — Account Activity Service (v1)

> Sub-section lever variant: each red flag carries a one-line **Severity** tag
> (HIGH / MED / LOW) so the PM can triage findings, not just read them.

## 1. Complexity Diagnosis

All three of Ousterhout's symptoms are present, and each maps to a named component.

- **Change amplification** — dominant. Adding one event type forces a new method on
  `MetricsFacade`; bumping the profile schema forces edits at two independent call sites;
  adding one endpoint forces a new pass-through method on `ReportController`. A single
  conceptual change fans out into many mechanical edits.
- **Cognitive load** — elevated. Callers must learn N near-identical method names instead
  of one method plus a parameter, and must carry the cache-key format
  (`user:{user_id}:profile:v2`) in their head and re-type it correctly everywhere.
- **Unknown unknowns** — present and most dangerous; the doc admits it: bump to v3 and
  "both call sites must be edited to match, or reads silently miss the cache." Nothing at
  the writer's site signals that a reader depends on a byte-identical key.

## 2. Red Flags Found

- **Shallow module** — `MetricsFacade`.
  - **Severity: HIGH** — grows a method per event forever; every event type ships a code
    change to a shared file.
  - The interface (six-plus named methods) is nearly as large as the implementation, and
    each method is a one-line wrapper over `self.counter.add(name, 1)`. Almost no
    functionality is abstracted away — the module adds surface area without hiding much.
    Callers could call `counter.add` directly at the same cognitive cost.

- **Pass-through method** — `ReportController.generate_report`.
  - **Severity: MED** — pure indirection; harmful mainly as a pattern that repeats per
    endpoint into a forwarding-only controller layer.
  - It takes `params` and hands them, unchanged, to `report_service.generate_report(params)`
    — same signature, same name, no validation, transformation, or auth. A pass-through
    adds a call-stack layer while adding zero abstraction and couples the two classes.

- **Information leakage / duplicated knowledge** — the profile cache key.
  - **Severity: HIGH** — the failure mode is *silent*: a v3 bump that updates only one side
    produces no error, just cache misses that degrade performance (or correctness) months
    later. This is the single most severe issue in the doc.
  - The key format is a design decision hard-coded in `ProfileWriter` and independently
    re-derived in `ProfileReader` with "no shared helper." The same knowledge leaks across
    two modules; change amplification (v3 = edit both) plus the unknown-unknown of a silent
    miss when they drift.

- **Special-general mixture / overexposure** — `MetricsFacade` again.
  - **Severity: MED** — couples the interface to the event taxonomy, so the taxonomy cannot
    evolve without an interface change.
  - "Increment a counter for an event" is one general operation; encoding each specific
    event as its own method mixes the specific (event name) into the general mechanism and
    exposes the full event list on the interface when the caller only ever names one.

- **Vague / repetitive naming** — the `increment_*_count` family.
  - **Severity: LOW** — a symptom, not a root cause; it flags the abstraction level, not a
    standalone defect.
  - Six names carrying information (the event type) that should be a parameter, not part of
    the identifier — a signal the abstraction sits at the wrong level.

## 3. Tactical vs. Strategic Assessment

This is **tactical programming** across the board — each component is shaped to make the
next single addition trivially easy ("just add another method / endpoint / key string") at
the cost of the overall design. Ousterhout's tactical-tornado warning applies directly:
fast local progress while system complexity compounds.

Compounding cost if this becomes house style: `MetricsFacade` ("twelve methods today, more
coming") becomes a wall of near-identical one-liners with merge contention on a shared file
for what should be a data change; the pass-through controller pattern produces a layer that
exists only to forward calls; the duplicated cache key guarantees a recurring class of
silent-miss production bugs on every cached-schema bump. Strategic programming spends a
small design investment now — one deep method, one real key abstraction — to stop all three
fan-out patterns before they calcify.

## 4. Design it Twice

**MetricsFacade — collapse N methods into one deep method.**
```
class Metrics:
    def record(self, event_type):
        self.counter.add(event_type, 1)
```
New event types become *data*, not code — no interface change, no new method, no edit to a
shared file. The interface shrank while the capability held: the mark of a deeper module.

**ReportController — add real value or remove the layer.** If it is meant to own HTTP
concerns, then validation, auth, and request→domain mapping belong here, justifying its
existence. If it will never do that, delete it and route straight to the service. A layer
earns its cost only when it changes the abstraction.

**Profile cache — make the key an abstraction, not a shared literal.**
```
def profile_cache_key(user_id, version=CURRENT_PROFILE_VERSION):
    return f"user:{user_id}:profile:{version}"
```
Both writer and reader call `profile_cache_key(user_id)`. Format and current version live in
one place; a v3 bump is one line; the two sides cannot drift; the silent-miss mode is
designed out. The alternative is strictly smaller in interface, strictly lower in change
amplification, and removes the admitted unknown-unknown.

## 5. PM Actions

**What to ask engineers**
- "What does a caller need to record an event? If it's just the event name, why is it in the
  method name instead of a parameter?"
- "For `ReportController`: what does this layer hide from its caller? If nothing, what is it
  buying us?"
- "The doc says both cache call sites must be edited in lockstep or reads silently miss.
  What is our single source of truth for that key, and where does it live?"

**What to protect even under time pressure**
- The single cache-key abstraction (HIGH-severity finding) — cheap now, prevents a whole
  class of silent production bugs; do not let dogfood-then-GA ship the duplicated literal.
- The one-method metrics interface — it is *less* code than the N-method version, so there
  is no schedule argument against it.

**What to include in the PRD or technical spec**
- A stated rule: shared string formats (cache keys, event names, routing keys) live in
  exactly one function/constant, never duplicated. Call out the profile key as instance #1.
- An interface-review gate: any component whose methods are one-line wrappers over a single
  downstream call must justify why the layer exists before it merges.
- A Rollout note: flag/dogfood/GA tests *behavior*, not *design*. Dogfooding will not
  surface change amplification or the silent-miss risk — bank the design fix before GA.
