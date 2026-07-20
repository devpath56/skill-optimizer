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
engine/score.py         GENERIC scorer — knows nothing about any skill; states what it did NOT check
cartridges/<skill>/
  manifest.json         vocab, sections, concept checklist, thresholds, golden_set, fidelity_status
  BAR.md                the quality bar (prompt contract · state matrix · numeric ship gate)
  FIDELITY-FINDINGS.md  grounded audit results
  golden/               design docs + by-construction answer keys + captured skill outputs
  source/               authoritative source (book text = LOCAL ONLY, gitignored for copyright)
```

## Run
```
python3 engine/score.py cartridges/ousterhout
```

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
