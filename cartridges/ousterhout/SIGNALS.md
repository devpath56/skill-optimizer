# SIGNALS — the progressive loop and the signals it drives

This is the **spine doc**. The advisor-builder is a *progressive scoring loop* (`engine/loop.py`):

> ingest source → **eval all signals** → pick a deficiency → **gated retrieval** from the authoritative
> source → **grounded fix** (inject) → re-eval → repeat until the bar → output = the grounded advisor.

Every signal below is closed by that loop **or** has a documented non-loop route. The mapping is the
SSOT in `engine/signal_routes.py`; **`engine/loop_coverage.py` fails CI** if any gated signal is
ungoverned, if a `loop` signal lacks a real handler, or if a signal drops out of this doc (CF-076 — the
loop-drop failure — must not recur).

## Route kinds
- **loop** — a deficiency forces a gated retrieval + a grounded injection; the loop drives the metric to bar.
- **pre-populated** — authored up front (skill / manifest / `GROUNDING.md`); the loop does not synthesize it.
- **verification-twin** — an *is-real* gate that passes iff its injecting sibling's grounding is verbatim.
- **model-iterate** — generative; no deterministic handler. The loop *flags* it and routes to the parked
  model-iterate step. Any loop-closable *grounding* sub-part is split out as its own `loop` signal.

## The signal set (`engine/craft.py`)

| Signal | Gate | Route | How it closes |
|---|---|---|---|
| **S1** vocab codified | hard | pre-populated | red-flag names authored in the skill |
| **S2** output contract | hard | pre-populated | response sections declared |
| **S3** diagnostic framework | hard | pre-populated | the analytical core authored |
| **S4** source grounding declared | hard | pre-populated | the skill points at its authority |
| **S5** refusal codified | advisory | **loop** | inject the refusal block ← *"define errors out of existence"* |
| **S6** worked example | advisory | pre-populated | craft shown, authored |
| **S7** grounding travels | hard | pre-populated | `GROUNDING.md` deliverable; S14's handler extends it |
| **S8** grounding is real | hard | verification-twin of **S7** | anecdotes verbatim in the source |
| **S9** recall mnemonic taught | advisory | **loop** | inject the DEEP block ← *"deep module"* |
| **S10** mnemonic is grounded | hard | verification-twin of **S9** | each letter a real book principle |
| **S11** authorial voice taught | advisory | **loop** | inject SHARP signature quotes |
| **S12** voice is real | hard | verification-twin of **S11** | every quote verbatim |
| **S13** voice-bar integrity | hard | verification-twin of **S11** | no platitude declared a signature quote |
| **S14** trade-off recall | advisory | **loop** | inject each missing case study ← *"exception masking"*, until recall ≥ bar |
| **S15** trade-off key is real | hard | verification-twin of **S14** | each case study verbatim |

**Loop-driven today: S5, S9, S11, S14.** Everything else is authored (pre-populated) or a verification
twin that closes when its sibling's injected grounding is real. That is the whole spine — visible,
guarded, and driven.

## Future signals (wired the same way when built)
- **Contrarian (`engine/contrarian.py`)** — *4a* contrarian answer, *4b* reframe question. Both route
  **model-iterate** (the loop cannot author a contrarian answer). Their cited anecdote/quote *grounding*
  is loop-closable and split out. Parked v2: calibrated contrarian/reframe judges (doc-only templates).
- **Frameworks-as-tools (`engine/frameworks.py`)** — *S18* card grounded + schema-complete (**loop**:
  retrieve each card's grounding), *S19* advisor deploys a relevant card (advisory / model-iterate).
  Cited cards (real book figures) outrank derived cards, which must be labeled `provenance: derived, not cited`.

When any of these lands, its `SIGNAL_IDS` are enumerated by `loop_coverage.py` and **must** appear in
`signal_routes.ROUTES` and in this table, or CI blocks — the guard forces the wiring.
