# Skill Optimizer — AI-native handoff

> Principle: **if it can't be run and measured, it isn't done.** An agent picks up this
> file and can score, iterate, and ship-gate any skill file against an authoritative source.
> Generic **engine** + per-skill **cartridge**. Shipping a new skill = writing a new cartridge;
> the engine never changes.

## What it does
Optimizes a skill file until it meets a numeric acceptance bar, then gates shipping.
Loop: **define bar → score → (if RED) iterate skill → re-score → SHIP or RED (max 3 rounds).**

## Layout
```
engine/            GENERIC — knows nothing about any specific skill
  score.py         cartridge-driven scorer: deterministic checks first, states what it did NOT check
cartridges/
  ousterhout/      tenant #1 (proof)
    manifest.json  vocab, sections, concept checklist, thresholds, golden_set index
    BAR.md         the quality bar (contract + state matrix + acceptance numbers)
    golden/        design docs + by-construction answer keys + captured skill outputs
```

## Run
```
python3 engine/preflight.py cartridges/<name>  # → readiness: what runs clean vs what needs the book (run FIRST)
python3 engine/score.py cartridges/<name>      # → scorecard + SHIP/RED/INCOMPLETE (deterministic axes)
```
A fresh clone runs clean or fails loud: missing committed files → INCOMPLETE (exit 6);
the book (external licensed dep) absent → full-book F3 NOT-RUN (loud), never a bare PASS.

## To ship a NEW skill (the generalization)
1. Create `cartridges/<skill>/manifest.json` with:
   - `skill_file` (path), `authoritative_source` {book/blog, on_disk_proxy, text},
   - `closed_vocab` (the skill's named concepts), `expected_sections` (its output contract),
   - `concept_checklist` (load-bearing ideas from the source), `thresholds`, `golden_set`.
2. Author the golden set to cover EVERY state-matrix row (see below). Each flaw-laden doc gets a
   **by-construction** answer key — flaws you planted, listed as metadata, NOT a model's reading.
   (This non-circularity is the load-bearing property; it was the Phase-0 gate.)
3. Invoke the skill on each golden doc; capture output to `golden/<out>.md`.
4. `python3 engine/score.py cartridges/<skill>` → read the RED checks.
5. Edit the skill file to fix RED checks; re-run; repeat ≤3 rounds; ship when the gate is green.

## State matrix (every cartridge's golden set must cover all rows)
| State | Designed skill behavior | Check |
|---|---|---|
| flaw-laden | find ≥90% of planted flaws, name by vocab | E2 recall (deterministic vs key) |
| clean | ≤1 flag ASSERTED (negation-aware) | E4 restraint (deterministic) |
| ambiguous | flag it AND state the tradeoff | E5 (validated judge) |
| off-domain | decline; do not force the output contract | E-ref (deterministic) |
| empty | ask for the artifact | E-ref (deterministic) |

## Check library (which axis needs what — the ladder: deterministic > judge > source)
| Check | What | Grounding |
|---|---|---|
| E1 structure | output emits the fixed sections in order | deterministic (regex) |
| E2 recall | planted flaws found, negation-aware, scoped to findings section | deterministic vs by-construction key |
| E3 precision | named flags ∈ closed vocab (deterministic) + each is valid (judge) | deterministic + judge |
| E4 restraint | clean doc raises ≤1 asserted flag | deterministic (negation-aware) |
| E-ref | off-domain/empty → declines | deterministic |
| E5 soundness | PM-action soundness | LLM-judge, validated at TPR/TNR ≥ 0.85 first |
| F1/F3 fidelity | concept coverage; no invented principle; anecdotes correct | judge vs authoritative source text |
| F2 vocab | all named concepts present in skill | deterministic (grep) |
| F4 hop-attribution | defect tagged source→proxy vs proxy→skill | manual, needs source text |

## Ship gate
```
SHIP iff  E1=100% ∧ E2≥thr.recall ∧ E3(0 out-of-vocab ∧ validity≥0.85) ∧ E4 ∧ E-ref=100%
          ∧ F1≥thr.concept_coverage ∧ F2=full ∧ F3=0 invented ∧ (E5≥0.80 once judge validated)
else → RED: return failing check to the iterate step.
```

## generate → re-rank (box 4-5)  ·  `engine/rerank.py`
The scored iterate step: take N captured candidate outputs, rank them, and STAGE a winner —
without touching the live skill. Generic and cartridge-driven, same as `score.py`; reuses its
deterministic primitives (`red_flags_section`, `term_asserted`, `sections_present`,
`vocab_raised`). `score.py` is never modified.

### Protocol
```
python3 engine/rerank.py cartridges/<name> [--top-k N]     # default K=2
```
- **Input**: `cartridges/<name>/candidates.json` — each candidate is
  `{candidate_id, generator_model, checker_model, variant, outputs:{<doc>:<captured-output-path>}}`.
- **Output**: a leaderboard table + `staging/survivors.json` + the staged winner at
  `staging/<candidate_id>/` (copied outputs + `scorecard.json`).

### The ONE lever
- **tune skill sub-sections** — candidates differ only in how the output sub-sections are shaped
  (e.g. adding a one-line Severity tag per red flag). `restructure-output-contract` was **DROPPED**
  and is **not** a lever.

### Two-stage scoring
| Stage | What | Who | Decides |
|---|---|---|---|
| STAGE 1 (in `rerank.py`) | cheap **deterministic** proxy ranks **ALL N** → top-K survivors | code (no model) | efficacy ordering + provisional winner |
| STAGE 2 (**implemented consumer**, in `rerank.py`) | fold the judge's `staging/survivors_judged.json` verdict into a final weighted 0-100 | judge runs outside; the **consumer is code** | **fidelity** + final winner |
- STAGE 1 proxy weighted 0-100 = `recall·70 + structure·20 + vocab_breadth·10` (flaw-laden).
- STAGE 2 is **implemented** (`run_full_bar()` / `emit_stage2()`): it **consumes `survivors_judged.json`**
  (the model-run judge's per-survivor axes) — it does not itself call a model. Final score =
  `proxy·0.40 + judge·0.60`, where `judge = e5_pm_action·0.60 + critique_quality·0.40` and
  `fidelity_parity` is a **hard gate** (parity=false → judge portion 0, cannot win). The proxy is an
  entry gate (ties at 100 among survivors), so the **judge breaks the tie**. It enforces model
  separation (`judge_model != generator_model`, neither Fable; else **exit 3**), confirms the
  computed winner matches the judge's stated winner (surfaces disagreement, never overrides), and —
  because the ousterhout **judge is unvalidated (`validated=false`) → the winner is PROVISIONAL** until
  calibrated at TPR/TNR ≥ 0.85. Writes `staging/final-scorecard.json`; the live skill_file is untouched.

### The fidelity-blind boundary (load-bearing)
- The proxy is **efficacy-only** and **provably fidelity-blind**:
  - it is handed an **efficacy view** of the manifest — `closed_vocab` + `expected_sections` +
    `thresholds` **only** — with `authoritative_source` **stripped out**, and it **asserts** that
    key is absent before scoring.
  - it therefore **cannot** read the book, so it **cannot** judge fidelity (concept coverage,
    invented principles, anecdote correctness). That is STAGE 2's job.
  - **consequence, seen in the demo**: two efficacy-equivalent candidates (same recall/structure/
    vocab) are **indistinguishable to the proxy on purpose** → both survive to the stage that can
    actually tell them apart. The proxy never fakes a fidelity verdict.

### Model separation (hard gate, checked BEFORE ranking)
- Candidate **generator_model ≠ checker_model**, and **neither** may be Fable (`claude-fable-5`).
  The proxy itself is **code** (no model).
- `{generator_model, checker}` is recorded per candidate; the ranker **REFUSES** to rank
  (exit 3, explains each violation, stages nothing) if any candidate's generator == its checker,
  or either is `claude-fable-5`.

### Promotion (staging, not apply)
- The winner is **STAGED** into `cartridges/<name>/staging/<candidate_id>/` (a slot **distinct**
  from the live `skill_file`) with a `scorecard.json`. **Nothing auto-applies** to the real skill —
  a human / next step promotes from staging.

### To add candidates
1. Capture each candidate's skill output to `golden/<file>.md` (one per golden doc it covers).
2. Add an entry to `candidates.json`: `candidate_id`, `generator_model`, `checker_model`,
   `variant` note, and `outputs:{<doc>:<file>}`. Keep the generator ≠ checker and avoid Fable.
3. Re-run `python3 engine/rerank.py cartridges/<name>`; read the leaderboard; inspect
   `staging/<winner>/scorecard.json`.

### Demo result (ousterhout, N=3, K=2)
| rank | candidate | proxy | survivor | why |
|---|---|---|---|---|
| 1 | C1-good | 100.0 | YES | recall 3/3, 5/5 sections, 5 vocab |
| 2 | C3-severity | 100.0 | YES | recall 3/3, 5/5 sections, 5 vocab (sub-section severity tag) |
| 3 | C2-degraded | 46.7 | drop | recall 1/3 (collapsed Red Flags to one flag) |
- C1 and C3 **tie at 100** — the severity-tag difference is a fidelity/quality dimension the proxy
  is blind to, so both survive; the tie is broken by STAGE 2.
- **STAGE 2 (implemented) breaks the tie** by consuming `staging/survivors_judged.json`:

  | rank | candidate | proxy | e5 | critique | parity | FINAL |
  |---|---|---|---|---|---|---|
  | 1 | C1-good | 100.0 | 0.93 | 0.85 | YES | **93.88** |
  | 2 | C3-severity | 100.0 | 0.85 | 0.88 | YES | 91.72 |

  Final winner **C1-good [PROVISIONAL]** — matches the judge's stated winner (margin 0.03). Because
  the judge is **unvalidated (`validated=false`)** the winner is PROVISIONAL, not a settled gate,
  until TPR/TNR ≥ 0.85. Recorded in `staging/final-scorecard.json`; live skill file untouched.

## Standing disciplines (earned from real runs, not hypotheticals)
- **The eval can be the thing that's wrong.** First full run: the clean-restraint check counted
  "No information leakage" as a raised flag → false FAIL. Fix: negation-aware + scoped to the
  findings section. Always audit a surprising verdict against the trace before trusting it (CF-010).
- **Deterministic before judge** (Hamel / Trident house-rule). A judge is a vanity metric until
  validated against human labels.
- **State what you did NOT check.** The scorer prints PENDING for judge + fidelity axes rather than
  implying green.
- **Non-circular keys only.** If the answer key is written by the same model family being graded,
  recall is theatre.
```
```
