# Fidelity findings — ousterhout cartridge (F3 axis)

**Verdict: F3 FAIL** (threshold: 0 invented principles). Grounded judge + independent grep verification against `source/book.norm.txt`. **All defects are hop-1 (reference.md); the skill (hop-2) adds none.**

> This is the two-hop design working: a skill-vs-reference-only check would score GREEN — the
> skill faithfully mirrors reference.md. Both are wrong together. Only checking against the real
> book surfaced it. Efficacy passed while fidelity failed → the two axes are independent, as designed.

## Verified defects (in reference.md)
| # | Defect | Book truth | Severity |
|---|---|---|---|
| 1 | 4 "Key Quotes" in quotation marks | 3 of 4 not in book in any form (1 partial); rest are paraphrases mispresented as verbatim | **severe** (fabricated quotes) |
| 2 | "define errors out of existence" → "Tcl `substring()`" | book's example is Tcl **`unset`** (remove a variable) | severe (wrong example) |
| 3 | "Three dimensions in tension" + "Decide What Matters" chapter | no such framework/chapter in book | severe (invented framework) |
| 4 | "10+ files for a 1-line feature… N>3 unrelated files" rule | no such numeric anecdote/rule in book | moderate (fabricated specificity) |
| 5 | vague-name word-lists + "two different names" heuristic | book's naming ch. = "precise" + "consistent"; no such lists | moderate (invented heuristic) |
| 6 | red-flag comment snippet `// increment i by 1` | real concept, but book's snippet is a different example | minor (fabricated illustration) |
| 7 | "write comments first" framed as TDD-complementary | book explicitly criticizes TDD as "tactical programming" | moderate (stance inversion) |
| 8 | formula stated as clean equation | book calls it "a **crude** mathematical way" (hedge dropped) | minor (over-precision) |
| 9 | Facebook "stable infra"; Java `StringIndexOutOfBounds` | book: "solid infrastructure"; `IndexOutOfBoundsException` | minor (wording) |

## Verified-CLEAN (independent search confirmed these are faithful, despite looking suspect)
- All 8 red-flag NAMES are real Ousterhout terms (incl. "Vague Name", singular).
- The complexity formula C=Σ(c_p·t_p) IS in the book (Σ symbol lost in PDF extraction).
- tactical tornado, 10–20% investment, deep/shallow, Unix 5-call I/O, classitis, pass-through,
  design-it-twice, sweet-spot generality, text-editor example, event-driven warning — all SUPPORTED.

## Hop attribution
- **hop-1 (reference.md → the distillation): FAIL** — every defect originates here (AI-hallucination signatures: fabricated quotes, invented framework, false-precision anecdotes).
- **hop-2 (reference.md → SKILL.md): CLEAN** — the skill repeats only real, correctly-named concepts; it inherits reference.md's errors only where it pulls from the poisoned sections at runtime.

## Implication for shipping
The skill can't ship at the bar while it auto-loads a distillation containing fabricated quotes.
The fix target is **reference.md**, not the skill's instructions. (Blast radius: the same reference.md
feeds complexity-radar, tactical-vs-strategic, design-audit — out of today's scope but flagged.)
