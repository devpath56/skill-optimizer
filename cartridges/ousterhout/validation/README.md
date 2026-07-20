# E5 judge calibration — validation harness

The STAGE 2 **E5 judge** scores *PM-action soundness* (is the skill's `PM Actions`
section specific/correct/actionable, or generic/vague/wrong?). Its verdict — and any
STAGE 2 winner that rests on it — is **PROVISIONAL** until the judge is proven to agree
with ground truth. This folder measures that agreement.

## Files

| File | Who writes it | What it is |
|---|---|---|
| `e5_labeled_set.jsonl` | the **set-builder** (here) | 18 `PM Actions` snippets, each with a **by-construction** `label` (PASS/FAIL) |
| `e5_judge_verdicts.jsonl` | the **judge** (separately, a different model) | same `id`s, each `{id, judge_label}` |
| `calibrate.py` | the **set-builder** (here) | deterministic scorer — TPR/TNR/confusion matrix + VERDICT |

**Builder != judge (non-circular).** The labels are metadata about *how each example
was authored* — each snippet was written to be clearly sound or clearly generic/wrong —
**not** any model's opinion. The judge never sees the labels; the builder never writes
the verdicts. That separation is what makes the calibration real rather than theatre.

Row schema (`e5_labeled_set.jsonl`):
```json
{"id": "L01", "label": "PASS", "ambiguous": false, "pm_actions_text": "...", "why_constructed": "..."}
```
Composition: **9 PASS / 9 FAIL**, of which **4 are deliberately ambiguous/borderline**
(2 PASS-intent, 2 FAIL-intent) — labeled with best construction intent to probe the
judge at the margin.

## How to run the calibration

1. **Judge scores the set.** A model that is *not* the generator and *not* Fable reads
   each `pm_actions_text` in `e5_labeled_set.jsonl` and decides PASS/FAIL **on its own**
   (it must not see the `label` / `why_constructed` fields). It writes one line per id to
   `e5_judge_verdicts.jsonl`:
   ```json
   {"id": "L01", "judge_label": "PASS"}
   ```
   Every id in the labeled set must appear exactly once; no extra ids.
2. **Score the agreement** (deterministic, no model):
   ```
   python3 calibrate.py
   ```
   It prints per-example agreement, the confusion matrix, TPR, TNR, and the VERDICT.

`calibrate.py` resolves both inputs relative to its own location, so run it from anywhere.

## What the numbers mean

- Positive class = **PASS**.
- **TPR** = P(judge=PASS | true=PASS) — does the judge recognize sound PM actions?
- **TNR** = P(judge=FAIL | true=FAIL) — does the judge reject generic/wrong PM actions?
- **VERDICT: VALIDATED iff `TPR >= 0.85` AND `TNR >= 0.85`.**

Exit codes: `0` VALIDATED · `1` NOT VALIDATED · `2` input/consistency error.

## The honesty rule

Until the VERDICT is **VALIDATED**, the E5 judge is an *unvalidated* judge: its
`e5_pm_action` score, the STAGE 2 final score that consumes it, and the staged
**winner** are all **PROVISIONAL** — a hint, not a gate. This matches
`survivors_judged.json` (`validated: false`) and the STAGE 2 consumer in
`engine/rerank.py`, which labels the winner PROVISIONAL until this harness passes.
Do not promote a PROVISIONAL winner to the live skill file on the strength of the
E5 verdict alone.

> Deterministic before judge; a judge is a vanity metric until validated against
> non-circular human/by-construction labels. This folder is that gate for E5.
