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

## Status
PLAN ONLY. This file is a decision record, NOT gated code — prove-durable will (correctly)
report it as UNGATED. A migration map is a promise; it becomes durable only when the DSPy
adapter exists and a check fails if it is reverted.
