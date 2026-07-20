# A Philosophy of Software Design — Master Reference (Verified)
**Source:** John Ousterhout, *A Philosophy of Software Design* (Yaknyam Press, 2018)
**PM Relevance:** Vocabulary and frameworks for high-fidelity engineering conversations, design reviews, and tech debt decisions.

> **Fidelity note:** This edition was verified against the book text on the specific points in `FIDELITY-FINDINGS.md`. Every passage inside quotation marks below has been grep-confirmed verbatim in the source. Fabricated quotes, invented frameworks, and false-precision anecdotes from the earlier draft have been removed or replaced with grounded equivalents. Where the book has no exact quote, the point is stated as an unquoted paraphrase.

---

## The Central Thesis

The book is about one thing: complexity. As Ousterhout puts it, "This book is about one thing: complexity." and "Dealing with complexity is the most important challenge in software design." Software design is the ongoing work of reducing that complexity. Every design decision either adds or subtracts complexity, and complexity accrues incrementally — you have to sweat the small stuff.

---

## Ch 2: The Nature of Complexity

### Definition
Ousterhout defines complexity practically: "Complexity is anything related to the structure of a software system that makes it hard to understand and modify the system."

He also offers a rough weighting model. Note his own hedge — he introduces it as "a crude mathematical way" of characterizing complexity, not a precise formula:

**C = Σ(c_p × t_p)** — the overall complexity of a system (C) is the complexity of each part p (c_p) weighted by the fraction of developer time spent working on that part (t_p). A very complicated part that almost never gets touched contributes little to overall complexity.

### Three Symptoms of Complexity
| Symptom | What it means | PM signal |
|---------|--------------|-----------|
| **Change amplification** | A seemingly simple change requires code modifications in many different places | "Why does a copy change require edits in a dozen files?" |
| **Cognitive load** | The developer must accumulate a large amount of information to make a change | "Why does onboarding take 3 months?" |
| **Unknown unknowns** | It's unclear what code must be changed or what information matters; bugs hide | "Why do we keep getting surprised by regressions?" |

Ousterhout is explicit that of the three, unknown unknowns are the worst.

### Change Amplification Example (from the book)
Ousterhout's illustration is a Web site whose pages each display a banner with a background color. In early sites the color was specified explicitly on every page, so changing the color meant editing every page. Centralizing the color removes the amplification. (This is the book's real example; the earlier draft's "10+ files for a 1-line feature / any feature touching N>3 files" rule is not in the book and has been removed.)

### Two Causes of Complexity
- **Dependencies** — when a piece of code can't be understood or modified in isolation; leads to change amplification and cognitive load.
- **Obscurity** — when important information is not obvious; creates unknown unknowns and adds to cognitive load.

### Complexity Is Incremental
No single dependency or obscurity causes the problem; hundreds or thousands of small ones build up over time. The remedy is a "zero tolerance" philosophy.

---

## Ch 3: Working Code Isn't Enough (Tactical vs. Strategic Programming)

### Core Distinction
The first step toward good design is to realize that "working code isn’t enough."

| Tactical | Strategic |
|----------|-----------|
| Get something working quickly, accept added complexity | The most important goal is a great system design |
| Short-term velocity | Long-term structure of the system |
| Accumulates complexity | Reduces complexity |

### The Tactical Tornado
A prolific developer who churns out code far faster than others but leaves a wake of complexity that slows everyone else down. Often rewarded by management; not appreciated by the engineers who inherit the code.

### Investment Rate
Ousterhout suggests spending roughly **10–20% of development time** on continuous design improvement — not a big up-front (waterfall) design, but continual small investments.

### Startups and Investment (Facebook)
Facebook long used the motto "Move fast and break things," encouraging tactical programming; new engineers pushed commits to production in their first week and the codebase degraded. The company eventually changed its motto to "Move fast with solid infrastructure" to push more investment in good design. Ousterhout contrasts this with Google and VMware, which he cites as companies that emphasized good design and strong engineering cultures.

### PM Takeaway
When you push engineers to ship in 2 weeks what needs 3, you are making a tactical choice with a strategic cost. Tech debt compounds. The 10–20% guideline is your budget for paying that interest down continuously.

---

## Ch 4: Modules Should Be Deep

### The Depth Concept
A module (class, function, service) has an **interface** (what callers must know — the cost) and an **implementation** (what it does internally — the benefit).

"The best modules are those whose interfaces are much simpler than their implementations."

- **Deep module:** small/simple interface, substantial functionality behind it.
- **Shallow module:** interface nearly as complex as the little functionality it provides — adds complexity without paying for it.

### Classitis
Ousterhout pushes back on the conventional wisdom that classes should be small rather than deep, and that the main job in class design is breaking large classes into smaller ones. Taken to the extreme — many tiny classes, thin wrappers everywhere — this produces a syndrome he calls **classitis**, where the proliferation of shallow classes raises overall system complexity.

### Examples
- **Unix file I/O:** a handful of calls (open, read, write, lseek, close) hide enormous functionality — buffering, disk layout, concurrency, device details. **Deep.**
- **Java I/O:** the need to explicitly wrap streams (e.g., a `BufferedInputStream` around a `FileInputStream`) exposes a shallow, boilerplate-heavy interface.

### PM Takeaway
When an engineer says "we need to refactor the API," they often mean it has too many shallow modules. Refactors that consolidate interfaces pay down cognitive debt.

---

## Ch 5: Information Hiding (and Leakage)

### Principle
The most important technique for deep modules is **information hiding** (from David Parnas). Each module should encapsulate a few pieces of knowledge that represent design decisions, embedded in its implementation but not exposed in its interface.

### Information Leakage
When a design decision is reflected in multiple modules — e.g., two modules that both "know" a file format — a change to it forces changes in both. Ousterhout calls information leakage one of the most important red flags in design.

### Temporal Decomposition (Anti-Pattern)
Structuring a system around the time order of operations rather than around information. Example: one class reads a file, another parses it, another processes it — the file format then leaks across all three. Better: one module owns the file-format knowledge.

### PM Takeaway
When engineers debate where logic should live, they're often arguing about information ownership. Ask: "Who should own that decision, and what breaks if it changes?"

---

## Ch 6: General-Purpose Modules Are Deeper

### The Sweet Spot
Ousterhout's finding: make new modules "somewhat general-purpose." The module's functionality should reflect your current needs, but its interface should be general enough to support other uses. This tends to produce simpler, deeper interfaces than a special-purpose approach, and better information hiding.

Don't overshoot: don't build something so general-purpose that it's hard to use for the task at hand.

### Text Editor Example
For storing text in an editor, a general-purpose interface built on primitives like inserting and deleting ranges of characters is simpler and deeper than a pile of special-purpose operations tied to specific UI actions. The UI layer composes the primitives.

### PM Takeaway
Resist feature-specific API requests from your own team. Push for general primitives that serve the specific flow as one case among several.

---

## Ch 7: Different Layer, Different Abstraction

### Principle
Each layer should provide a different abstraction from the layer below it. If adjacent layers have similar abstractions, that's a sign of a problem.

### Pass-Through Method Anti-Pattern
A method that does little but call another method with mostly the same signature adds a layer without adding abstraction — complexity for no benefit.

### Decorators
Ousterhout warns that the decorator pattern tends to spawn shallow classes; overuse is a smell.

### PM Takeaway
When "there are 7 layers between the UI and the database," ask whether each layer adds a genuinely different abstraction. Layers that don't are tech debt.

---

## Ch 8: Pull Complexity Downwards

### Principle
When you face complexity, it's usually better to handle it inside the module (pull it down) than to expose it to callers (push it up). It's more important for a module to have a simple interface than a simple implementation.

### Configuration Parameters
Exposing a configuration parameter is often a way of pushing complexity up to callers, forcing them to determine the right value. Prefer computing a sensible value automatically; where configuration is genuinely needed, pick defaults so most callers never have to set it.

### PM Takeaway
When engineers say "we'll expose it as a config option," probe whether that's a real product decision or a technical decision the engineer is punting to the caller. If the latter, push back.

---

## Ch 9: Better Together or Better Apart?

### When to Combine
- The pieces share information.
- Combining simplifies the interface.
- It eliminates duplication.
- It removes awkward back-and-forth between the pieces.

### When to Separate
- General-purpose and special-purpose code.
- Genuinely unrelated concerns.

### Splitting Methods
Split a method only if it produces cleaner abstractions; don't split if it yields shallow methods. Each method should do one thing completely.

### PM Takeaway
Microservices debates are often this question at the infrastructure level. Ask whether the boundary reduces or adds complexity given the information each side owns.

---

## Ch 10: Define Errors Out of Existence

### Principle
Exception handling is one of the worst sources of complexity. The best way to reduce it is to design APIs so the exceptions don't exist in the first place — "define errors out of existence."

### Example 1: file deletion (the book's lead example)
Windows refuses to delete a file that is open in a process, so callers hit an error and have to hunt down whatever holds the file open. Unix defines that error out of existence: deleting an open file returns success immediately. Unix removes the name from the directory and defers the real deletion until the file is closed. Same operation, no error case to handle. Unix is the design to copy here, Windows is the frustration to avoid.

### Example 2: Java `substring`
Java's `substring` throws `IndexOutOfBoundsException` when an index is out of range, which complicates callers who legitimately want a clamped result. Redefining it to return the in-range (overlapping) characters instead of throwing defines the exception out of existence.

### Example 3: Tcl `unset`, Ousterhout's own mistake
He flags this as a mistake he made himself. He defined Tcl's `unset` (which removes a variable) to throw an error if the variable did not exist. But a common use of `unset` is cleanup, where you cannot be sure the variable exists, so developers ended up wrapping `unset` in `catch`. The fix: redefine `unset` so deleting an absent variable is a no-op, not an error.

(Correction note: an earlier draft mis-framed `unset` as a positive example and once attributed the substring case to Tcl. Corrected here, `unset` is the *mistake*, the `substring` example is *Java's*, and the clean positive design is Unix file deletion. Caught by the truthfulness gate, logged C04.)

### Design Special Cases Out of Existence
The same reasoning applies beyond errors: eliminating special cases removes the `if` statements that riddle code and create bugs.

### PM Takeaway
When engineers say "we need error handling for X," ask whether the feature can be defined so X can't occur. This applies to product design too.

---

## Ch 11: Design It Twice

### Principle
For any nontrivial design decision, sketch at least two genuinely different alternatives before committing. Pick approaches that are radically different from each other — you learn more that way.

### Why Developers Skip It
Time pressure and the sense that the first idea is good enough. But comparing alternatives is how you find the deeper interface.

### What to Compare
- Interface simplicity (ease of use for higher-level code is the most important consideration)
- Information hiding
- Number of dependencies
- Which option makes callers simpler

### PM Takeaway
This is product design. Sketching the alternative often reveals the superior path. Apply it to every nontrivial product decision.

---

## Ch 12: Why Write Comments?

### The Excuses Engineers Give
Ousterhout catalogs the common rationalizations for not writing comments: good code is self-documenting; I don't have time; comments get out of date and become misleading; and the claim that all the comments one has seen are worthless. He argues each is mistaken, and that well-written comments materially improve a system.

### What Comments Actually Do
Comments capture information the designer had in mind that isn't obvious from the code — the abstractions, the intent, the non-obvious constraints. They are how you fully capture an abstraction.

### PM Takeaway
If no one can explain why a design decision was made, that's an unknown unknown. Push for decision logs, ADRs, and interface documentation.

---

## Ch 13: Comments Should Describe What's Not Obvious

### Types of Comments That Add Value
- **Interface comments:** what a method does, its arguments, return values, and side effects — the abstraction callers rely on.
- **Implementation comments:** what and why, not how.
- **Cross-module comments:** dependencies that cross module boundaries (rare but important).

### Red Flag: Comment Repeats Code
Ousterhout names this red flag directly: "Comment Repeats Code." If the information in a comment is already obvious from the adjacent code, the comment adds nothing. His real example is a comment at the same level of detail as the code it sits on:

```
// Add a horizontal scroll bar
hScrollBar = new JScrollBar(JScrollBar.HORIZONTAL);
```

The comment just restates the code. (The earlier draft's `// increment i by 1` snippet was invented; this is the book's actual illustration.) Useful comments instead operate at a different level than the code — either more precise (lower level) or more intuitive (higher level).

### The "Obvious to Whom?" Test
Obvious to the author is not obvious to the next reader. Write for the reader.

---

## Ch 14: Choosing Names

### The Two Properties
"Good names have two properties: precision and consistency."

- **Precision:** the most common problem is names that are too generic or vague, so readers can't tell what the name refers to. A precise name creates a clear mental image of the underlying entity.
- **Consistency:** use a given name to mean the same thing throughout, and use the same name for the same concept everywhere.

Names are a form of abstraction: a good name focuses attention on what's most important about the entity while omitting less important detail. Names should be short (a few words); more than two or three becomes unwieldy.

(The earlier draft's specific "vague word" lists and its "two different names" heuristic are not in the book and have been removed. The grounded properties are precision and consistency.)

### PM Takeaway
Naming is an early signal of whether an engineer has thought a thing through. The same holds for product: if you can't name the feature in a few words, it isn't designed yet.

---

## Ch 15: Write the Comments First

### Comments as a Design Tool
Ousterhout writes interface comments at the very beginning — the class interface comment first, then interface comments and signatures for the most important methods, before filling in bodies. If you can't write a clean interface comment, the abstraction is probably wrong; the comment surfaces the design flaw early. He calls comments a "canary in the coal mine" for design.

### Relation to TDD — the book's actual stance
Do **not** frame comments-first as a complement to test-driven development. Ousterhout explicitly rejects TDD: "Although I am a strong advocate of unit testing, I am not a fan of test-driven development." His objection is that TDD fixates on getting individual features working rather than finding the best design — "This is tactical programming pure and simple, with all of its disadvantages." His broader point: "the units of development should be abstractions, not features." Comments-first is a design discipline; TDD, in his view, is tactical.

### PM Takeaway
Write the user-facing framing before the requirements. If you can't state it in one clean sentence, the feature isn't designed yet.

---

## Ch 16: Modifying Existing Code

### Stay Strategic
Every change is an opportunity to improve the system's structure. When you touch code to add a feature, try to leave the design a little better than you found it, rather than just bolting the feature on.

### Keep Comments Near Code
Put design documentation where developers will actually see it — in the code near what it describes — so it stays current.

### Avoid the Duct-Tape Fix
Adding a special case to make a new feature work is tempting but leaves one more exception for future engineers to understand.

### PM Takeaway
When an estimate includes cleanup of messy code, that's strategic investment, not padding. Protect it.

---

## Ch 17: Consistency

### Forms of Consistency
Names, coding style, interface patterns, and design conventions. Consistency reduces complexity and makes behavior more obvious: if similar things are done in similar ways, a reader can apply prior understanding to new code.

### Ensuring Consistency
Document the conventions, put the document where developers will see it, and enforce it in code review. "When in Rome, do as the Romans do" — in a new file, match the conventions already there.

### PM Takeaway
Style guides, API conventions, and component libraries are complexity reduction, not bureaucracy. Support standardization efforts.

---

## Ch 18: Code Should Be Obvious

### Obviousness
Obvious code lets a reader understand what it does and why, quickly, without much effort. Non-obviousness is the opposite of an obvious system; it drives cognitive load and unknown unknowns.

### What Makes Code Less Obvious
- Generic containers passed around instead of named types.
- Behavior that depends on code in distant locations.
- Side effects not signaled by the interface.
- Non-standard or surprising patterns.

### PM Takeaway
When engineers weigh "clean architecture" vs. event-driven vs. reactive, obviousness at team scale is the tradeoff they're navigating.

---

## Ch 19: Software Trends

Ousterhout evaluates trends by whether they provide leverage against complexity.
- **Object-oriented programming / inheritance:** encapsulation is valuable; implementation inheritance creates dependencies and information leakage between parent and subclasses, so use it carefully.
- **Agile:** its emphasis on incremental, iterative development is valuable, but incremental development should be of abstractions, not features.
- **Unit tests:** he's a strong advocate; good test suites make risky changes safe (he cites the Tcl byte-code rewrite).
- **Test-driven development:** he is not a fan — it's tactical programming that fixates on features rather than design.
- **Design patterns:** useful, but overuse (forcing patterns where they don't fit) adds complexity.
- **Getters and setters:** an example of a convention that's often shallow.

### PM Takeaway
"We're doing microservices" (or any trend) is not a design decision. Ask what problem it solves and whether it's the right tool.

---

## Ch 20: Designing for Performance

### The Core Idea
Simplicity is still the most important thing: simple designs are usually faster, and clean design and high performance are compatible.

### Ousterhout's Process
1. **Measure before modifying** — don't guess where the bottleneck is.
2. **Design around the critical path** — the code that runs most often; remove special cases from it.
3. Simplify that path as much as possible.

He illustrates with the RAMCloud Buffer rewrite, which roughly doubled performance while making the code cleaner. His summary: clean design and high performance are compatible.

### PM Takeaway
"Make the app faster" is not a ticket. Push for specifics: current P95, target, and a hypothesis about the bottleneck. Specificity enables measurement.

---

## Ch 21: Conclusion

The book reduces to one theme. In Ousterhout's words: "This book is about one thing: complexity." and "Dealing with complexity is the most important challenge in software design." Better design skills produce higher-quality software faster, and make the work more enjoyable.

(There is no separate "Decide What Matters" chapter and no "three dimensions in tension" framework in the book; the earlier draft invented both, and they have been removed. Chapter 21 is the Conclusion.)

### Summary of Red Flags (from the book)
- **Shallow Module** — interface complexity nearly as high as the functionality it provides.
- **Information Leakage** — the same design knowledge appears in multiple modules.
- **Temporal Decomposition** — structure mirrors the order of operations, not information.
- **Overexposure** — the interface forces callers to learn rarely-used features.
- **Pass-Through Method** — does nothing but pass work to another method.
- **Repetition** — the same code repeated.
- **Special-General Mixture** — a general-purpose mechanism entangled with special-purpose code.
- **Conjoined Methods** — two methods so interdependent you can't understand one without the other.
- **Comment Repeats Code** — the comment restates what the adjacent code already says.
- **Implementation Documentation Contaminates Interface** — an interface comment describes implementation details.
- **Vague Name** — a name too imprecise to convey useful information.
- **Hard to Pick Name** — difficulty naming something signals an unclear design.
- **Hard to Describe** — an interface comment that must be long and complicated signals a design problem.

---

## Verbatim Quotes (all grep-confirmed in the source)

> "working code isn’t enough"

> "Complexity is anything related to the structure of a software system that makes it hard to understand and modify the system."

> "The best modules are those whose interfaces are much simpler than their implementations."

> "Good names have two properties: precision and consistency."

> "Although I am a strong advocate of unit testing, I am not a fan of test-driven development."

> "This is tactical programming pure and simple, with all of its disadvantages."

> "the units of development should be abstractions, not features"

> "This book is about one thing: complexity."

> "Dealing with complexity is the most important challenge in software design."

*(The earlier draft's "Key Quotes" section listed passages that are not verbatim in the book — e.g., "The most important skill for a software designer is the ability to recognize complexity," "Good design is the accumulation of thousands of small decisions…," "If the interface of a module doesn't tell you what you need to know to use it, then the interface is wrong," "You can't design your way out of bad code by adding comments," "The whole point of comments is to capture things that can't be expressed in the code," and the conclusion line about the designer taking "ownership of the design decisions." None could be confirmed and all have been dropped.)*

---

## PM Vocabulary Cheat Sheet

| Term | Definition | Use in conversation |
|------|-----------|---------------------|
| Deep module | Substantial functionality behind a simple interface | "Is this API deep or shallow?" |
| Shallow module | Little functionality, interface nearly as complex — net negative | "This looks like a shallow wrapper." |
| Complexity tax | The ongoing cost of accumulated complexity | "What's the complexity tax on this shortcut?" |
| Information leakage | A design decision reflected in more than one module | "Are we leaking our data model through the API?" |
| Tactical tornado | Developer who ships fast but leaves messes for others | "Are we rewarding tactical tornadoes?" |
| Change amplification | A simple change requires edits in many places | "How much change amplification does this create?" |
| Unknown unknowns | You can't tell what needs changing or what matters | "What are the unknown unknowns here?" |
| Cognitive load | Amount of information needed to make a change | "What's the cognitive load on our oncall engineers?" |
| Pass-through | A layer/method that adds no abstraction | "Is this service a pass-through?" |
| Temporal decomposition | Structured by order of operations, not information | "We've built temporal decomposition into the pipeline." |
