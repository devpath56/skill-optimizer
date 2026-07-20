# skill-optimizer

Score, iterate, and ship-gate a **skill file** against an **authoritative source** (a book,
blog, or expert text). Generic **engine** + per-skill **cartridge**. Shipping a new skill =
writing a new cartridge; the engine never changes.

> **What this honestly is:** a small-N **selector** + a rigorous eval/**ship-gate** — it ranks a
> handful of candidates you hand it and gates shipping. It is **not** a DSPy-class *optimizer*
> (it does not search a candidate space). The keeper is the rigor layer (metric, calibration,
> gate); for real search, see [`MIGRATION.md`](./MIGRATION.md).

> Principle: **if it can't be run and measured, it isn't done.** Acceptance is a behavioral
> number, not a resemblance. The agent contract is [`HANDOFF.md`](./HANDOFF.md).

## Two axes
- **Efficacy** (north star) — when invoked, does the skill *behave* well? (recall of planted
  flaws, precision, structure, refusal on off-domain). Deterministic, scored by `engine/score.py`.
- **Fidelity** (diagnostic) — does the skill's content *match the source*, across two hops
  (source → distillation → skill)? Vocab presence is deterministic; accuracy/no-distortion is a
  grounded judge that must quote the source.

They fail independently: a skill can behave well while misquoting its source. Check both.

## Layout
```
engine/preflight.py     GENERIC readiness check — run FIRST; classifies committed-required vs external-licensed
engine/score.py         GENERIC scorer — knows nothing about any skill; states what it did NOT check
engine/rerank.py        GENERIC generate→re-rank (STAGE 1 proxy + STAGE 2 judge consumer)
cartridges/<skill>/
  manifest.json         vocab, sections, concept checklist, thresholds, golden_set, fidelity block
  BAR.md                the quality bar (prompt contract · state matrix · numeric ship gate)
  FIDELITY-FINDINGS.md  grounded audit results
  golden/               design docs + by-construction answer keys + captured skill outputs (committed)
  validation/           E5 judge calibration + fidelity-fixtures.json (fair-use committed ground truth)
  source/               authoritative source (book text = LOCAL ONLY, gitignored for copyright)
```

## Run
```
python3 engine/score.py cartridges/ousterhout
```

## Fresh clone / new session
A fresh clone either **runs clean** or **fails loud** — it never shows a silent pass or a false
green. Run preflight FIRST; it tells you exactly what is evaluable in this checkout.
```
python3 engine/preflight.py cartridges/ousterhout     # readiness report (run this first)
python3 engine/score.py     cartridges/ousterhout     # efficacy + presence-checked fidelity
python3 engine/rerank.py    cartridges/ousterhout      # STAGE 1 proxy + STAGE 2 consumer
python3 cartridges/ousterhout/validation/calibrate.py  # E5 judge calibration
```

**What runs clean with no extra setup** (everything needed is committed):
- **Efficacy** — E1 structure, E2 recall, E4 clean-restraint, E-ref off-domain. The golden
  outputs (`golden/*-out-*.md`, `guru-output-*.md`) are the skill's OWN critiques (not
  copyrighted) and are committed, so these axes get real verdicts, not a missing-data FAIL.
- **Lightweight fidelity** — F2 (all 8 named red flags present) and F3-lightweight (the
  confirmed short quotes are present in the committed distillation `source/reference.verified.md`).
  Ground truth for these lives in `validation/fidelity-fixtures.json` (fair-use short quotes).

**What needs the book — intentionally NOT committed (copyright):**
- **Full-book F3** verifies the confirmed quotes appear verbatim in the *actual book* and that
  the known-fabricated quotes are absent from it. This requires the book text, which is **not**
  in the repo by design. Until you supply it, `score.py` prints full-book F3 as
  **NOT-RUN (book absent)** and **never a bare PASS** — a result recorded on another machine is
  not a live verdict here.

**Bring your own licensed copy** (to enable full-book F3):
1. Obtain your own copy of *A Philosophy of Software Design* (John Ousterhout).
2. Extract its text and normalize whitespace into a single file at:
   `cartridges/ousterhout/source/book.norm.txt`  (this path is gitignored — it stays local).
3. Re-run `python3 engine/preflight.py cartridges/ousterhout`; it will now report the book
   PRESENT, and `score.py` will run full-book F3 as a live verdict.

The full book is **never committed** and the repo does not distribute it. Only short,
attributed, fair-use quotes (each < 15 words) live in `fidelity-fixtures.json`.

## Add a new skill (the generalization)
See `HANDOFF.md` §"To ship a NEW skill". In short: write a `manifest.json`, author a golden set
covering all 5 state-matrix rows with **by-construction** answer keys (non-circular — this is the
load-bearing property), invoke the skill on each, run the scorer, fix RED checks, ship when green.

## Disciplines (earned from real runs, see cartridges/ousterhout/RUN-01.md)
- **The eval can be the thing that's wrong.** Four false-fails were caught before they became
  verdicts (negation, tabs, plural/singular, lost unicode). Always audit a surprising verdict
  against the trace before trusting it.
- **Deterministic before judge.** A judge is a vanity metric until validated against human labels.
- **Non-circular keys only.** If the answer key is written by the same model family being graded,
  recall is theatre. Plant flaws by construction.
- **Two hops, not one.** Checking skill-vs-distillation misses errors the distillation inherited
  from the source. Ground against the real source.

## Status (honest, provisional)
Tenant #1 `ousterhout-guru`:
- **package**: self-contained — the **skill-under-test is vendored** (`cartridges/ousterhout/skill/`,
  byte-faithful snapshot, copyright-vetted) and preflight fails loud if it goes missing. An agent can
  read, invoke, and iterate the real subject, not just re-score frozen outputs.
- **state matrix**: **4/5 rows live** (flaw-laden, clean, off-domain, empty — all deterministic E-ref/E2/E4).
  `ambiguous` remains PENDING (it needs the validated E5 judge). The `empty` row also doubles as the
  regression guard for the `sections_present` heading-vs-mention fix (revert it → empty E-ref re-fails → gate BLOCKs).
- **efficacy**: SHIP-eligible on a **4-doc probe slice (recall n=1 flaw-laden — NOT statistically
  robust)**. Not a full verdict; scale the golden set to ~15 for real recall/precision.
- **fidelity**: F2 8/8, F3 PASS after one iterate round (fixed 6 fabricated quotes).
- **E5 judge**: VALIDATED but **PROVISIONAL (n=18 by-construction, one-shot, no train/test split)** —
  read "smoke-tested", not "production-calibrated".
Treat every number here as provisional until the sets are scaled + human-labeled. See `RUN-01.md`.

## Pre-ship gate (the main entry point)
`gate.py` answers the real question — **would this skill ship to the team?** — and drops into CI / a pre-commit hook.
```
python3 engine/gate.py cartridges/ousterhout            # SHIP (0) / BLOCK (1) / INCOMPLETE (6)
python3 engine/gate.py --selftest cartridges/ousterhout # NEGATIVE CONTROL: gate must BLOCK a degraded
                                                         # skill and SHIP the real one (else it is vacuous)
python3 engine/gate_durability.py cartridges/ousterhout # SELF-DURABILITY: --selftest must itself catch a
                                                         # neutered gate (mutate -> run -> restore; CF-067)
```
`gate_durability.py` closes the last loop: `--selftest` proves the gate isn't vacuous, and this proves
`--selftest` isn't vacuous — it mutates `gate.py`'s decision logic (always-SHIP; drop the efficacy
reason) and **requires** `--selftest` to flip to failure, restoring the file byte-for-byte. A stale
mutation whose target text is missing is a HARD FAIL, never a silent skip (the census-incident class).
A gate that only ever says SHIP is worthless (CF-065/CF-067), so `--selftest` degrades the flaw-laden output
(recall drops below bar) and **requires the gate to flip to BLOCK**. The "fresh-clone smoke test" is just the
degenerate case: the gate runs in any environment and fails loud.

## Loop ledger (SSOT for visibility)
`cartridges/<skill>/loop-log.jsonl` — append-only record of every **run**, **decision**, and **self-correction**
in the self-improving loop (mirrors Trident's `failures.jsonl`; schema in `loop-log.schema.json`). This is the
visibility layer: how many runs, what was decided, what got reversed — one line each, never rewritten.
