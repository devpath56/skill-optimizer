# Vendored skill-under-test — provenance

`SKILL.md` here is a **byte-faithful snapshot** of the subject this cartridge optimizes:

- **Source:** `~/Downloads/PM-OS/.claude/skills/ousterhout-guru/SKILL.md` (the author's own work — a PM
  coaching persona, not the copyrighted book).
- **Snapshot date:** 2026-07-20 (loop-log D21). Re-vendor if the live skill changes; this copy is what
  the committed golden outputs were captured against.
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
