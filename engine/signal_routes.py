#!/usr/bin/env python3
"""
signal_routes.py — the SSOT for HOW each gating signal is closed by the progressive loop.

This is the spine registry behind CF-076 (the progressive loop leaking away from the plan). Every
signal an evaluator gates on must have a declared ROUTE here, and `engine/loop_coverage.py` verifies
the declaration matches reality (a `loop` route MUST have a real handler in loop.py; a handler with no
signal is an orphan). A signal with no route is an ungoverned signal — exactly how the loop silently
stopped driving something.

Route kinds:
  loop              — closed by a loop handler: RETRIEVAL_QUERY[id] retrieves from the source and
                      apply_fix injects the grounded block. The loop drives the metric to the bar.
  pre-populated     — authored up front (in the skill / manifest / GROUNDING.md), not loop-generated.
                      Foundational structure the loop does not synthesize (vocab, contract, framework).
  verification-twin — an "is-real" gate that passes iff its injecting sibling's grounding is verbatim
                      in the source. No separate handler: it closes when the sibling's content is real.
  model-iterate     — generative; no deterministic handler. The loop FLAGS it and routes to the parked
                      model-iterate step (it cannot deterministically author, e.g., a contrarian answer).
                      Any loop-closable GROUNDING sub-part is a separate `loop` signal.
"""

# id -> {route, why, twin_of? }  — every signal any evaluator gates on lives here.
ROUTES = {
    # craft.py — foundational structure (authored, not loop-synthesized)
    "S1":  {"route": "pre-populated", "why": "red-flag vocabulary is authored in the skill up front"},
    "S2":  {"route": "pre-populated", "why": "the output/response contract is authored up front"},
    "S3":  {"route": "pre-populated", "why": "the diagnostic framework is authored up front"},
    "S4":  {"route": "pre-populated", "why": "the source-grounding pointer is authored up front"},
    "S6":  {"route": "pre-populated", "why": "the worked example is authored up front"},
    "S7":  {"route": "pre-populated", "why": "GROUNDING.md (deliverable anecdotes) is authored; S14's handler extends it"},
    # craft.py — loop-driven (a deficiency here forces a gated retrieval + grounded injection)
    "S5":  {"route": "loop", "why": "refusal block injected from the book's 'define errors out of existence'"},
    "S9":  {"route": "loop", "why": "DEEP mnemonic block injected, anchored on 'deep module'"},
    "S11": {"route": "loop", "why": "signature-voice quotes injected from SHARP anchors in the source"},
    "S14": {"route": "loop", "why": "trade-off case-study section injected per missing decision, until recall>=bar"},
    # craft.py — verification twins (close when the sibling's injected grounding is real/verbatim)
    "S8":  {"route": "verification-twin", "twin_of": "S7",  "why": "grounding is REAL — verbatim check on S7's anecdotes"},
    "S10": {"route": "verification-twin", "twin_of": "S9",  "why": "each DEEP letter is a real book principle (S9)"},
    "S12": {"route": "verification-twin", "twin_of": "S11", "why": "every signature quote is verbatim (S11)"},
    "S13": {"route": "verification-twin", "twin_of": "S11", "why": "voice-bar integrity — no platitude declared a quote (S11)"},
    "S15": {"route": "verification-twin", "twin_of": "S14", "why": "each trade-off case study is verbatim (S14)"},
}

# Signals whose route is `loop` MUST have exactly these handler ids in loop.py (RETRIEVAL_QUERY + apply_fix).
LOOP_SIGNALS = sorted(i for i, r in ROUTES.items() if r["route"] == "loop")

if __name__ == "__main__":
    import json, sys
    print(json.dumps({"routes": ROUTES, "loop_signals": LOOP_SIGNALS}, indent=2)); sys.exit(0)
