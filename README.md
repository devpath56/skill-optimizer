# skill-optimizer

Score, iterate, and ship-gate a **skill file** against an **authoritative source** (a book,
blog, or expert text). Generic **engine** + per-skill **cartridge**. Shipping a new skill =
writing a new cartridge; the engine never changes.

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

## Status
Tenant #1 `ousterhout-guru`: efficacy SHIP-eligible on a 3-doc probe slice; fidelity F2 8/8, F3
PASS after one iterate round (fixed 6 fabricated quotes in the distillation). Not yet at full gate
— judge axes (E5/E3-validity) pending, golden set not scaled to 15. See `RUN-01.md`.
