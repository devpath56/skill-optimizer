# PARKED — the calibrated contrarian / reframe judge (v2)

`engine/contrarian.py` ships the **deterministic floor**: lexical divergence from consensus + reframe
markers + verbatim grounding. It is fast and non-vacuous, but it is a **proxy** — it cannot certify true
*semantic stance-divergence* (a paraphrase of consensus with different words would slip 4a; genuine
contrarianism in consensus vocabulary would be missed). That is the honest boundary (loop-log D37).

The real metric is a **calibrated LLM judge**, parked here until built via the `validate-evaluator` method:

- **positive class = CONTRARIAN** (the answer meaningfully departs from the stock/consensus stance) and,
  separately, **REFRAME** (the question forces a new frame).
- **calibration bar: TPR ≥ 0.85 AND TNR ≥ 0.85** against a human-labeled set (same bar as the E5 judge in
  `validation/calibrate.py`, which is the template to copy).
- **inversion control**: relabel the set with the definition inverted; a real judge's TPR/TNR must collapse.
  A judge that scores the same on inverted labels is measuring fluency, not stance.
- **gate when live**: `contrarian_degree ≥ threshold AND grounded` — contrarian-but-ungrounded is a *crank*
  (the failure quadrant), grounded-but-consensus is *dull*; only grounded + contrarian is worth listening to.

## Template files (schemas, not yet a running gate)
- `c_labeled_set.jsonl` — `{id, problem, consensus, candidate, kind: "answer"|"question", label: "CONTRARIAN"|"REFRAME"|"CONSENSUS"}`
- `c_blind.jsonl` — the same rows with `label` stripped (what the judge sees).
- `c_judge_verdicts.jsonl` — `{id, verdict, rationale}` the judge emits; `calibrate.py` scores verdicts vs labels.

When built: copy `validation/calibrate.py`, set the positive class, add one CI step (+ the inversion control),
and add a `loop_coverage` route for any new signal id. Until then this stays parked — declared, not faked.
