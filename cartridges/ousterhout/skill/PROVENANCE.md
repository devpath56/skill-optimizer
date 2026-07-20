# Vendored skill-under-test — provenance

`SKILL.md` here began as a byte-faithful snapshot of the subject and is now the **optimizer-improved
version** — the progressive driver (`engine/loop.py`) closed two eval deficiencies against the
authoritative source and those grounded fixes were **promoted** here (loop-log D24/D25):

- **Source (original):** `~/Downloads/PM-OS/.claude/skills/ousterhout-guru/SKILL.md` (the author's own
  work — a PM coaching persona, not the copyrighted book).
- **Improvements promoted from the loop:** (1) *Handling missing or insufficient input* — a refusal
  instruction grounded in the book's own *"define errors out of existence"*; (2) *Memory hook — DEEP* —
  a recall mnemonic whose four letters are each verified verbatim in the book. Both are book-grounded,
  not invented.
- **Diverged from PM-OS:** this copy is now ahead of the PM-OS original. **Flow it back** (re-vendor to
  PM-OS) so the live skill and this improved subject reconverge.
- **Snapshot date:** 2026-07-20 (loop-log D21, improved D24/D25). The committed golden outputs were
  captured against the pre-improvement skill; the added sections are additive and do not change how it
  critiques the existing golden docs.
- **Copyright vet:** scanned for verbatim book passages — none. The only long quoted span is a
  synthetic "feature flag service" example the skill authored itself. Short named concepts (red-flag
  vocabulary) are ideas, not expression. Safe to commit.

## One resolution caveat (by design)
The live skill's *Automatic Context Checks* read
`context-library/strategy/philosophy-of-software-design-reference.md` — a **PM-OS-relative** path that
does **not** resolve inside skill-optimizer. The cartridge's vendored equivalent of that distillation is
`source/reference.verified.md` (hop-1, the fidelity distillation). An agent re-generating golden outputs
inside this repo should point the skill's context-check at `source/reference.verified.md`.

## Why it's here
Pillar ① (prototype-as-spec): the package now ships the **subject**, not just its captured outputs — so
an agent can read, invoke, and iterate the real skill, and `preflight.py` fails loud if it goes missing.
The engine does **not** score from this file (no gate changed); it enables re-generation and iteration.

## Bundled grounding (`GROUNDING.md`)
The skill *promises* "reference specific anecdotes from the book," but `SKILL.md` alone carries none —
handed standalone, a downstream teaching agent would **fabricate** them (caught deterministically by
craft check **S7**). `GROUNDING.md` fixes this: it is the book-verified distillation (fair-use), bundled
so the anecdotes (Tcl `unset`, RAMCloud, Unix file I/O, information leakage, temporal decomposition)
**travel with the skill**. Craft **S8** verifies, against the authoritative book text, that every bundled
anecdote is verbatim-real and none are fabricated (NOT-RUN + loud where the book is absent).

**Residual (skill-side improvement):** `SKILL.md`'s Automatic Context Check still points at the PM-OS
path `context-library/.../philosophy-of-software-design-reference.md`. To fully close the loop, that
line should be re-pointed at the bundled `GROUNDING.md` and re-vendored from PM-OS — a skill edit, not a
package edit. Until then the grounding is *present in the bundle* (S7/S8 pass) even if the skill's own
pointer is stale.
