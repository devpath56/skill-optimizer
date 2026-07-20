#!/usr/bin/env python3
"""
E5 judge calibration harness (deterministic scorer — NO model here).

Purpose
-------
The STAGE 2 E5 judge scores "PM-action soundness". Until we know the judge
agrees with ground truth, its verdict (and any STAGE 2 winner resting on it)
is PROVISIONAL. This script measures that agreement and emits a VERDICT.

Non-circularity (the load-bearing property)
-------------------------------------------
Ground-truth labels in e5_labeled_set.jsonl are BY CONSTRUCTION: each PM Actions
snippet was written to be clearly sound (PASS) or clearly generic/wrong (FAIL),
and the label is metadata about how it was authored -- NOT any model's reading.
The judge's own labels arrive separately in e5_judge_verdicts.jsonl (produced by
a different model, outside this file). Builder != judge, so calibration is real.

Inputs (both alongside this script; no absolute paths baked in)
---------------------------------------------------------------
  e5_labeled_set.jsonl     : {id, pm_actions_text, label, why_constructed, ...}
  e5_judge_verdicts.jsonl  : {id, judge_label}   <- written by the judge, separately

Metrics
-------
  Positive class = PASS.
  TP = true PASS & judge PASS      FN = true PASS & judge FAIL
  TN = true FAIL & judge FAIL      FP = true FAIL & judge PASS
  TPR (sensitivity) = TP / (TP + FN) = P(judge=PASS | true=PASS)
  TNR (specificity) = TN / (TN + FP) = P(judge=FAIL | true=FAIL)

VERDICT: judge is VALIDATED iff TPR >= 0.85 AND TNR >= 0.85.
Until VALIDATED, the E5 verdict stays PROVISIONAL.

Run:  python3 calibrate.py
Exit: 0 VALIDATED · 1 NOT VALIDATED · 2 input/consistency error
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LABELED = os.path.join(HERE, "e5_labeled_set.jsonl")
VERDICTS = os.path.join(HERE, "e5_judge_verdicts.jsonl")

THRESHOLD = 0.85
VALID_LABELS = {"PASS", "FAIL"}
EXIT_INPUT_ERROR = 2


def die(msg):
    """Input/consistency failure -> documented exit code 2 (sys.exit(str) would be 1)."""
    print(msg, file=sys.stderr)
    sys.exit(EXIT_INPUT_ERROR)


def load_jsonl(path):
    if not os.path.exists(path):
        die(f"ERROR: missing input file: {os.path.basename(path)} "
            f"(expected next to calibrate.py)")
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                die(f"ERROR: {os.path.basename(path)} line {i}: bad JSON ({e})")
    return rows


def norm_label(val, where):
    if not isinstance(val, str):
        die(f"ERROR: {where}: label must be a string, got {val!r}")
    up = val.strip().upper()
    if up not in VALID_LABELS:
        die(f"ERROR: {where}: label must be PASS or FAIL, got {val!r}")
    return up


def build_index(rows, key, path):
    idx = {}
    for r in rows:
        rid = r.get("id")
        if rid is None:
            die(f"ERROR: {os.path.basename(path)}: a row is missing 'id'")
        if rid in idx:
            die(f"ERROR: {os.path.basename(path)}: duplicate id {rid!r}")
        if key not in r:
            die(f"ERROR: {os.path.basename(path)}: id {rid!r} missing {key!r}")
        idx[rid] = norm_label(r[key], f"{os.path.basename(path)} id {rid!r}")
    return idx


def pct(n, d):
    return "n/a (0 cases)" if d == 0 else f"{n / d:.3f}"


def main():
    truth = build_index(load_jsonl(LABELED), "label", LABELED)
    judge = build_index(load_jsonl(VERDICTS), "judge_label", VERDICTS)

    # ---- id set must match exactly (no silent partial calibration) ----
    missing = sorted(set(truth) - set(judge))
    extra = sorted(set(judge) - set(truth))
    if missing:
        die(f"ERROR: judge verdicts missing ids from the labeled set: {missing}")
    if extra:
        die(f"ERROR: judge verdicts contain unknown ids not in the labeled set: {extra}")

    TP = FN = TN = FP = 0
    print("=" * 72)
    print("E5 JUDGE CALIBRATION  (positive class = PASS)")
    print("=" * 72)
    print(f"{'id':<6}{'truth':<7}{'judge':<7}{'agree':<7}cell")
    print("-" * 72)
    for rid in sorted(truth):
        t, j = truth[rid], judge[rid]
        if t == "PASS" and j == "PASS":
            cell = "TP"; TP += 1
        elif t == "PASS" and j == "FAIL":
            cell = "FN"; FN += 1
        elif t == "FAIL" and j == "FAIL":
            cell = "TN"; TN += 1
        else:
            cell = "FP"; FP += 1
        agree = "OK" if t == j else "MISS"
        print(f"{rid:<6}{t:<7}{j:<7}{agree:<7}{cell}")

    n = TP + FN + TN + FP
    pos = TP + FN   # true PASS
    neg = TN + FP   # true FAIL

    print("-" * 72)
    print("CONFUSION MATRIX")
    print("                 judge=PASS   judge=FAIL")
    print(f"  true=PASS        {TP:>6}       {FN:>6}     (TP / FN)")
    print(f"  true=FAIL        {FP:>6}       {TN:>6}     (FP / TN)")
    print("-" * 72)
    print(f"  examples          : {n}   (true PASS={pos}, true FAIL={neg})")
    print(f"  accuracy          : {pct(TP + TN, n)}")
    print(f"  TPR  (sensitivity): {pct(TP, pos)}   = P(judge=PASS | true=PASS)")
    print(f"  TNR  (specificity): {pct(TN, neg)}   = P(judge=FAIL | true=FAIL)")
    print("-" * 72)

    tpr_ok = pos > 0 and (TP / pos) >= THRESHOLD
    tnr_ok = neg > 0 and (TN / neg) >= THRESHOLD

    if pos == 0 or neg == 0:
        print("VERDICT: NOT VALIDATED — labeled set lacks both classes; "
              "cannot measure TPR and TNR.")
        return 2

    validated = tpr_ok and tnr_ok
    if validated:
        print(f"VERDICT: VALIDATED  (TPR & TNR both >= {THRESHOLD:.2f})")
        print("  PROVISIONAL, though: a small by-construction set. Widen to ~100 human-labeled")
        print("  real cases + a train/test split before trusting this judge at scale.")
        print("  -> The E5 judge verdict is now a GATE, not a hint. STAGE 2 winners")
        print("     resting on it may drop the PROVISIONAL label.")
        rc = 0
    else:
        fails = []
        if not tpr_ok:
            fails.append(f"TPR={pct(TP, pos)} < {THRESHOLD:.2f} (judge misses sound PM actions)")
        if not tnr_ok:
            fails.append(f"TNR={pct(TN, neg)} < {THRESHOLD:.2f} (judge passes generic/wrong PM actions)")
        print(f"VERDICT: NOT VALIDATED  (need TPR & TNR both >= {THRESHOLD:.2f})")
        for msg in fails:
            print(f"  - {msg}")
        print("  -> The E5 judge verdict stays PROVISIONAL. Any STAGE 2 winner")
        print("     resting on it stays PROVISIONAL until this passes.")
        rc = 1

    print("=" * 72)
    return rc


if __name__ == "__main__":
    sys.exit(main())
