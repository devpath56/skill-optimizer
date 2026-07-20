# Ousterhout Guru Review — Account Activity Service (v1)

## 1. Complexity Diagnosis

All three symptoms are present, and each maps to a specific component.

- **Change amplification** — the dominant symptom. Adding one new event type forces a
  new method in `MetricsFacade`. Bumping the profile schema forces edits at *two*
  independent call sites. Adding one endpoint forces a new pass-through method in
  `ReportController` plus a routing entry. In every case, a single conceptual change
  fans out into multiple mechanical edits. This is the definition of change
  amplification: the amount of code that must change is disproportionate to the size
  of the conceptual change.

- **Cognitive load** — elevated. To use `MetricsFacade` a caller must learn N method
  names that differ only by the event noun embedded in them, instead of learning one
  method and passing the noun as data. The profile-cache key format
  (`user:{user_id}:profile:v2`) is knowledge a developer must carry in their head and
  re-type correctly in every module that touches the cache.

- **Unknown unknowns** — present and the most dangerous, because the doc itself admits
  it: "If we bump the profile schema to v3, both call sites must be edited to match,
  or reads silently miss the cache." Nothing at the writer's call site signals that a
  reader elsewhere depends on a byte-identical key. A developer editing one side has no
  way to know the other side exists. Silent cache misses are exactly the failure that
  costs a debugging afternoon and a confused oncall page.

## 2. Red Flags Found

- **Shallow module** — `MetricsFacade`. The interface (six-plus named methods) is
  nearly as large as the implementation behind it. Each method is a one-line wrapper
  over `self.counter.add(name, 1)`. There is almost no functionality being abstracted
  away; the module adds surface area without hiding much. Consequence: the abstraction
  earns nothing — callers could call `counter.add` directly with the same cognitive
  cost, but now there is an extra class to maintain that grows one method per event
  forever.

- **Pass-through method** — `ReportController.generate_report`. It takes `params` and
  hands them, unchanged, to `report_service.generate_report(params)`. Same signature,
  same name, no validation, no transformation, no auth. The doc states this explicitly.
  A pass-through method adds a layer to the call stack while adding zero abstraction; it
  couples the two classes (both must change if the signature changes) and gives the
  reader nothing for the extra hop. Consequence: more code, more indirection, no
  information hidden.

- **Information leakage / duplicated knowledge** — the profile cache key. The key format
  is a design decision that is now hard-coded in `ProfileWriter` and independently
  re-derived in `ProfileReader` with "no shared helper." The same piece of knowledge
  leaks across two modules. Consequence: change amplification (v3 = edit both) plus the
  unknown-unknown of a silent miss when the two drift out of sync.

- **Special-general mixture / overexposure** — `MetricsFacade` again. "Increment a
  counter for an event" is a single general operation. Encoding each specific event as
  its own method mixes the specific (the event name) into the general mechanism
  (incrementing), and exposes the full list of event types on the interface when the
  caller only ever needs to name one. Consequence: the interface is coupled to the event
  taxonomy, so the taxonomy cannot evolve without an interface change.

- **Vague / repetitive naming** — the `increment_*_count` family is a naming smell in
  itself: six names that carry information (the event type) that should be a parameter,
  not part of the identifier. It signals the abstraction is at the wrong level.

## 3. Tactical vs. Strategic Assessment

This is **tactical programming** across the board — each component is shaped to make the
next single addition trivially easy ("just add another method," "just add another
endpoint," "just copy the key string") at the cost of the overall design. Ousterhout's
warning applies directly: tactical tornadoes make fast local progress while the system's
complexity compounds.

The compounding cost if this becomes the team's pattern:

- `MetricsFacade` is stated to be "twelve methods today, more coming." At this rate the
  class becomes a wall of near-identical one-liners. Every event type ships a code change
  to a shared file, creating merge contention and review overhead for what should be a
  data change.
- The pass-through controller pattern, repeated per endpoint, produces a controller layer
  that exists only to forward calls — pure ceremony that every future engineer must read
  through to find where logic actually lives.
- The duplicated cache key, generalized as "we build keys inline where we need them,"
  guarantees a recurring class of silent-miss production bugs whenever any cached schema
  version changes.

Strategic programming would spend a small amount of design investment now — a single
deep method, a real abstraction for the key — to stop all three fan-out patterns before
they calcify into house style.

## 4. Design it Twice

Consider the alternative before committing to what's written.

**MetricsFacade — collapse N methods into one deep method.**
```
class Metrics:
    def record(self, event_type):
        self.counter.add(event_type, 1)
```
One method. New event types become *data*, not code — no interface change, no new
method, no edit to a shared file. The interface shrank while the capability stayed the
same: the mark of a deeper module. (If you want compile-time safety on event names, the
event types live in one enum that the taxonomy owns, not in the method surface.)

**ReportController — either add real value or remove the layer.** If the controller is
meant to own HTTP concerns, then validation, auth, and request→domain mapping belong
*here*, which would justify its existence and let `ReportService` speak in clean domain
types. If it is genuinely never going to do any of that, delete it and route straight to
the service. A layer is worth its cost only when it changes the abstraction; a
pass-through does not.

**Profile cache — make the key an abstraction, not a shared literal.**
```
def profile_cache_key(user_id, version=CURRENT_PROFILE_VERSION):
    return f"user:{user_id}:profile:{version}"
```
Both writer and reader call `profile_cache_key(user_id)`. The key format and the current
version live in exactly one place. A bump to v3 is a one-line change; the two sides
cannot drift, and the silent-miss failure mode is designed out entirely.

Comparing the two designs: the alternative is strictly smaller in interface, strictly
lower in change amplification, and removes the admitted unknown-unknown. There is no
axis on which the original wins except "requires no thought right now."

## 5. PM Actions

**What to ask engineers**
- "What does a caller actually need to know to record an event? If the answer is just
  the event name, why is it in the method name instead of a parameter?"
- "For `ReportController`: what does this layer hide from its caller? If the answer is
  'nothing,' what is it buying us?"
- "The doc says both cache call sites must be edited in lockstep or reads silently miss.
  What is our single source of truth for that key, and where does it live?"
- "How many files change when we add the *next* event type? What would it take to make
  that a data change instead of a code change?"

**What to protect even under time pressure**
- The single cache-key abstraction. This is cheap to build now and prevents a whole
  class of silent production bugs; do not let "dogfood for a week then GA" ship the
  duplicated literal.
- The one-method metrics interface. It is *less* code than what's proposed, so there is
  no schedule argument for the N-method version.

**What to include in the PRD or technical spec**
- A stated rule: shared string formats (cache keys, event names, routing keys) live in
  exactly one function/constant, never duplicated across modules. Call out the profile
  key as the first instance.
- An interface-review gate: any new component whose methods are one-line wrappers over a
  single downstream call must justify why the layer exists before it merges (guards
  against pass-through controllers and shallow facades becoming house style).
- A note in the Rollout section: the flag/dogfood/GA plan tests *behavior*, not *design*.
  Dogfooding will not surface change amplification or the silent-miss risk — those show
  up months later as velocity drag and oncall pages. Bank the design fix before GA, not
  after.
