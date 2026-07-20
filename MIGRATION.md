# Migration map: DSPy as the search engine, our rigor as the metric + gate

Our optimizer's WEAK part is the search (N=3 hand levers, no theory). DSPy (Stanford, MIT)
does principled search (MIPROv2 / GEPA). The migration is compositional, not a rewrite:
**DSPy inside (search), our discipline outside (metric, calibration, gate).**

## REPLACE with DSPy
- box 4-5 generate->re-rank (N=3 levers + proxy + judge-rerank)  ->  MIPROv2 / GEPA optimizer
- "tune-sub-sections" lever                                       ->  DSPy instruction proposal (COPRO/MIPRO)
- proxy -> full-bar-on-survivors staging                          ->  DSPy evaluate-against-metric selection

## KEEP (DSPy does not do these)
- the bar (efficacy + fidelity + truthfulness T1/T2/T4)  ->  becomes DSPy's `metric` function
- non-circular by-construction golden keys               ->  DSPy trainset/valset (ours enforces non-circularity)
- judge calibration (TPR/TNR vs labels)                  ->  DSPy does not calibrate the metric's judge
- prove-durable / negative-control-on-gate / no-silent-green
- ship-gate (SHIP/BLOCK, gate.py)                        ->  DeepEval-style CI gate; DSPy optimizes, does not gate shipping

## Shape
    def bar_metric(example, pred, trace=None):   # our rigor layer
        return efficacy(pred) and fidelity(pred) and truthful(pred)
    program   = dspy.ChainOfThought("design_doc -> critique")
    optimized = dspy.MIPROv2(metric=bar_metric, auto="medium").compile(program, trainset=golden, valset=heldout)

## Decision (loop-log D19): KEEP — as a *triggered* plan, not "someday"
Keep-or-kill verdict: **KEEP**. The compositional insight — DSPy inside for search, our rigor
outside as metric + calibration + gate — is the correct growth path and worth documenting; the
selector+gate is honest and adequate at the current N. What we KILL is the *open-ended promise*:
this plan now carries an explicit adoption trigger, so it either fires on a named condition or stays
a deliberately-parked plan — never a vague aspiration.

**Adopt DSPy when EITHER bites** (until then, N=3 hand-levers + gate is adequate and DSPy's setup
cost isn't worth it):
1. **Search outgrows hand-levers** — a cartridge needs a candidate space larger than a handful of
   hand-authored levers, shown concretely by a re-rank round whose winner is capped by the lever
   set rather than by the bar.
2. **Enough labeled data for a real split** — ~100+ non-circular labeled examples, enough to form a
   genuine DSPy trainset/valset (the same threshold the judge-calibration relabel named).

Neither holds today (recall n=1, judge n=18), so DSPy stays parked — correctly.

## Status: PLAN ONLY (honest / ungated)
This file is a decision record, NOT gated code — prove-durable will (correctly) report it as
UNGATED. A migration map is a promise; it becomes durable only when the DSPy adapter exists and a
check fails if it is reverted. Parked-with-a-trigger is the honest state until a trigger fires.
