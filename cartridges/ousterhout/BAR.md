# Quality Bar — `ousterhout-guru` skill (AI-native handoff, v1)

> **Principle (yours):** if it can't be *run and measured*, it isn't done.
> Acceptance is a behavioral number, not a resemblance. This file is the contract an
> agent executes to decide **ship / don't ship** the skill to the team.

Two axes, both mechanized. **Efficacy** is the north star (does invoking it produce
Ousterhout-grade critique). **Fidelity** is the diagnostic (does its content match the book).

---

## 1. Prompt contract (the skill's stable interface)

| Field | Contract |
|---|---|
| **Input** | One software design artifact: PRD, API design, eng proposal, or a described decision. |
| **Output shape** | Exactly 5 sections, fixed order: `Complexity Diagnosis · Red Flags Found · Tactical vs. Strategic · Design it Twice · PM Actions`. |
| **Flag vocabulary** | Closed set of 8 named red flags: shallow module, information leakage, temporal decomposition, pass-through, conjoined methods, special-general mixture, vague names, overexposure. A flag presented as a named Ousterhout flag MUST be in this set. |
| **Edge / refusal behavior** | Clean doc → states "no material red flags," invents none. Off-domain / non-design input → declines, does not force a critique. |
| **Never** | Invent a red flag outside the closed vocab and present it as Ousterhout's; fabricate an anecdote; skip a section. |

---

## 2. State matrix (every input state + designed treatment — the unhappy rows on the page)

| State | Input | Designed treatment | Graded by |
|---|---|---|---|
| **flaw-laden** | doc with N planted flaws | find ≥90% of planted flaws, name each by vocab | E2 recall |
| **clean** | doc with no real flaws | raise ≤1 flag; do not hallucinate | E4 restraint |
| **ambiguous** | doc where a flag is arguable | flag it AND state the tradeoff, not a false certainty | E5 judge |
| **off-domain** | non-design text (e.g. a memo) | decline / redirect, no forced 5 sections | E-refuse |
| **empty / underspecified** | one-line stub | ask for the artifact, do not invent one | E-refuse |

The golden set MUST cover every row. Composition (v1): **8 flaw-laden** (planted keys spanning all 8 vocab flags), **3 clean**, **2 ambiguous**, **1 off-domain**, **1 empty** = 15 docs. Each flaw-laden doc ships with a `by-construction` answer key (non-circular — proven in the Phase-0 probe).

---

## 3. Acceptance = behavior ("what number ships it")

### Efficacy (dynamic — run skill on the golden set)
| ID | Check | Type | Ship threshold |
|---|---|---|---|
| **E1** | 5 sections present, correct order | deterministic (regex) | **100%** of runs |
| **E2** | Planted-flaw recall | deterministic vs by-construction key | **mean ≥ 0.90** across flaw-laden docs |
| **E3** | Precision: every named flag ∈ closed vocab AND defensible | deterministic (vocab map) + judge (validity) | **0** out-of-vocab named flags; validity **≥ 0.85** |
| **E4** | Clean-doc restraint | deterministic | **≤ 1** flag on each clean doc |
| **E-ref** | Off-domain / empty → declines | deterministic (no 5-section output) | **100%** |
| **E5** | PM-action soundness | LLM-judge, **only after E1–E4 pass** | **≥ 0.80**, judge itself validated at TPR & TNR **≥ 0.85** |

### Fidelity (static — skill vs book, two hops)
| ID | Check | Type | Ship threshold |
|---|---|---|---|
| **F1** | Load-bearing concept coverage (complexity def, deep modules, tactical/strategic, design-it-twice, the 8 flags, obscurity/comments) | checklist vs book | **≥ 0.90** present |
| **F2** | All 8 named red flags appear in skill | deterministic (grep) | **8 / 8** |
| **F3** | No invented principle; anecdotes correct | judge vs book, human spot-check | **0** violations |
| **F4** | Defect hop-attributed (book→reference.md vs reference.md→skill) | manual, needs book | every fidelity defect tagged |

### Composite ship gate
```
SHIP  iff  E1=100% ∧ E2≥0.90 ∧ E3(0 out-of-vocab ∧ validity≥0.85) ∧ E4 pass
           ∧ E-ref=100% ∧ F1≥0.90 ∧ F2=8/8 ∧ F3=0
           ∧ (E5≥0.80 once its judge is validated)
else  →  RED: return failing check(s) to Step 3 (iterate skill), re-run, max 3 rounds.
```

Hamel guardrails baked in: binary checks not Likert; deterministic before any judge; a
judge is a vanity metric until validated against human labels; 100% pass on E2 would mean
the golden docs are too easy, not that the skill is perfect (target hard docs).

---

## 4. Runnable surface (what an agent executes)
- `design-doc-NN.md` + `answer-key-NN.json` — golden set (state matrix rows).
- invoke `/ousterhout-guru` on each → capture to `guru-output-NN.md`.
- `score.sh` — deterministic scorer (E1, E2, E3-vocab, E4, E-ref) → per-doc pass/fail table. (Phase-0 probe is its seed.)
- judge step (E3-validity, E5) — only after deterministic checks are green.
- gate evaluator → emits `SHIP` or `RED + failing checks`.

## 5. Status
- **Step 1 (define bar): DONE** — this file.
- **Step 2 (score current skill): partial.** Phase-0 probe = n=1 flaw-laden run: E1 = 5/5 ✅, E2 = 3/3 recall ✅, E3 = 0 out-of-vocab ✅, E4 not yet (need clean doc). Needs full golden set + book (F-axis).
- **Step 3 (iterate to bar): not started** — gated on Step 2 scores.
