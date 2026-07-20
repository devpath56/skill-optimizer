# RUN-01 — ousterhout-guru (first full loop)

Run under the Trident harness. Sequence: define bar → score → iterate to bar.

## Phase 0 — riskiest-assumption gate
- Riskiest assumption (Auditor): the efficacy answer key could be **circular** (written by the
  same model family being graded) → recall would be theatre.
- Probe: author one design doc with 3 flaws planted **by construction**, invoke the skill, score
  deterministically. Falsified a 7-assumption cluster in one invocation. **PASS.**

## Step 1 — quality bar
- Defined as prompt contract + 5-row state matrix + numeric ship gate (see BAR.md).

## Step 2 — score current skill
- Efficacy (deterministic, 3-doc slice): structure 5/5 · recall 3/3 · clean restraint 0 asserted ·
  off-domain declined → **SHIP-eligible on the slice.**
- Fidelity F2 (vocab real in book): **8/8 PASS.**
- Fidelity F3 (grounded accuracy): **FAIL** — hop-1 (reference.md distillation) contained 6
  fabricated items incl. 4 quotation-marked "quotes" absent from the book (2 inverting the book's
  actual TDD stance), a wrong Tcl example, an invented framework, a fabricated anecdote. The skill
  (hop-2) added none; it inherited them by auto-loading the poisoned distillation.

## Step 3 — iterate to bar
- Built `source/reference.verified.md`: 6 fabrications removed, 19 quotes verbatim-confirmed,
  structure + PM-framing preserved.
- Fresh Auditor (different model) re-ran F3 → **PASS** (0 fabricated quotes, 0 invented, 0 new).
- Repointed `ousterhout-guru/SKILL.md` to the verified reference (durable, verified by grep).

## Eval bugs caught before they became verdicts (the loop earning its keep)
1. clean-restraint counted "No information leakage" as a raised flag → fixed: negation-aware.
2. book phrase search failed on tabs between words → fixed: whitespace-normalized copy.
3. "vague names" (plural) missed the book's "Vague Name" (singular) → not a defect.
4. Σ formula "missing" was lost-unicode in PDF extraction → not a defect.

## Not done (honest gaps)
- Efficacy is n=3, recall n=1 flaw-laden. Not statistically robust.
- Judge axes E3-validity, E5 (PM-action soundness) — not built/validated.
- Golden set not scaled to 15 (all 8 flags × 5 states).
- Repo-wide reference.md fix (feeds 3 other skills) — separate flagged task.
