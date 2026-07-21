# The Ousterhout Advisor — prototype

`advisor-demo.html` is the **prototype-as-spec** for the pipeline's payoff: a highly opinionated
software-design guru you invoke on a stuck decision. It doesn't validate your plan — it **reframes**
it, cites its own principles and the book's real anecdotes, and hands you a contrarian question.

## What it demos
- **The total workflow** — the rail at top: `source → progressive scoring checks → verified artifacts → advisor`.
- **The aha moments** — four stuck decisions (feature-flag endpoints, error handling, comments, ship-now),
  each answered with a contrarian reframe grounded in a real principle + anecdote + quote.
- **The grounding payoff** — every citation carries a `✓ verbatim · APOSD, Ch N` badge. The aha is that
  the contrarian take is *also grounded*, never invented — because the artifacts it cites
  (DEEP dossier, `tradeoff_decisions`, signature quotes) were verbatim-verified upstream by the gate.

## How it's built
- Content is composed from the pipeline's **real grounded artifacts** (staged demo, not a live model
  call — so the aha moments and citations are reproducible). A live advisor retrieves the same verified
  chunks (`book.index.jsonl`) at invoke time.
- Design follows `design-loop`'s house-style and **passes its deterministic `design-gate`**
  (axe contrast/names/roles/target-size · no horizontal overflow · no console errors · no spaced dashes),
  at 375px and 1280px, both themes.

## View / re-gate
```
open cartridges/ousterhout/advisor/advisor-demo.html
# re-run the design-loop gate (from a design-loop checkout):
node checks/design-gate.mjs <path>/advisor-demo.html
```
