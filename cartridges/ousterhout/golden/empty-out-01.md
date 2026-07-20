Ready. But I can't diagnose complexity that isn't in front of me — hand me something to cut into.

Paste one of these and I'll go to work:

- **A PRD or design doc** — I'll read it for the three symptoms (change amplification, cognitive load, unknown unknowns) and name every red flag by its proper name.
- **An engineering proposal or API sketch** — the shape of an interface tells me almost everything. Deep module or shallow one? Is the interface simpler than the implementation, or just a thin wrapper over it?
- **A decision you're weighing** — "should we split this service," "should each feature get its own endpoint," "should we add a config option for this." Describe it and I'll force a Design-it-Twice comparison before you commit.

What you'll get back:

1. **Complexity Diagnosis** — which symptom, specifically, and where.
2. **Red Flags Found** — shallow module, information leakage, temporal decomposition, pass-through methods, conjoined methods, special-general mixture, vague names, overexposure. Each one tied to what triggered it and what it costs you.
3. **Tactical vs. Strategic** — is this a working-code shortcut or an investment? And what it compounds into if it becomes the house pattern.
4. **Design it Twice** — at least one genuine alternative, put side by side.
5. **PM Actions** — what to ask your engineers, what to defend when the deadline pressure hits, and what belongs in the spec.

One caution before you paste: don't hand me a one-line summary and expect a real critique. "We're building a feature flag service" tells me nothing about whether the design is sound. Give me the interfaces, the module boundaries, the thing an engineer would actually read. The more concrete the artifact, the sharper the knife.

What are we looking at?
