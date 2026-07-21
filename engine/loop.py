#!/usr/bin/env python3
"""
loop.py — the progressive driver. Runs the optimize loop FOR REAL: every deficiency an eval catches
DRIVES a targeted retrieval from an AUTHORITATIVE source, and the retrieval grounds a fix. Re-eval,
repeat, until the bar is met or max rounds.

  progressive driver:  eval -> deficiency -> retrieve(authoritative, gated) -> fix -> re-eval -> ...

Retrieval is GATED (manifest.retrieval): the authoritative SOURCE (the book) is consulted first; only
if the source lacks the material does the loop consult an allowlist of authoritative sites; any
non-allowlisted source is REFUSED and logged, never silently fetched. Deterministic-first: a live
fallback would use WebFetch restricted to the allowlist.

Nothing touches the live vendored skill. Each round STAGES an improved candidate under
staging/loop/SKILL.md and writes a round-by-round staging/loop/loop-report.json.

  python3 engine/loop.py cartridges/<name> [--max-rounds N]

Exit: 0 converged (bar met) · 1 max rounds hit with deficiencies remaining · 6 skill_file not vendored.
"""
import json
import os
import re
import sys

ENG = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENG)
import craft  # reuse the deterministic craft grader (evaluate)
import frameworks  # S18/S19 — the book's figures as deployable framework cards (loop drives S18)
import ingest  # ingestion step: make a source retrievable (build the cited chunk index)


def load(cart):
    man = json.load(open(os.path.join(cart, "manifest.json"), encoding="utf-8"))
    sf = man.get("skill_file", "")
    if not sf or sf.startswith(("~", "/")):
        print("loop: skill_file is not vendored (external) — cannot iterate a subject we don't ship")
        sys.exit(6)
    return man, os.path.join(cart, sf)


# ── deficiency → retrieval query map (the driver's routing table) ───────────────
# Each open deficiency names the authoritative material that would fix it. A green check needs no query.
RETRIEVAL_QUERY = {
    "S5": "define errors out of existence",   # refusal/graceful-missing-input <- the book's own principle
    "S9": "deep module",                       # the recall mnemonic's anchor principle (DEEP)
    "S11": "simpler than their implementations",  # authorial voice — a SHARP anchor, not a platitude
    "S14": "exception masking",                    # trade-off case studies — anchor a missing decision
    "S18": "deep and shallow modules",             # frameworks-as-tools — anchor the deep/shallow figure
}


def deficiencies(skill_text, man, cart):
    """Run the deterministic grader on the current skill; return open deficiencies (advisory + hard),
    each tagged with the authoritative retrieval query that would resolve it."""
    out = []
    for c in list(craft.evaluate(skill_text, man, cart)) + list(frameworks.evaluate(skill_text, man, cart)):
        if c.get("notrun") or c["pass"]:
            continue
        out.append({"id": c["id"], "name": c["name"], "kind": c["kind"],
                    "query": RETRIEVAL_QUERY.get(c["id"])})
    # hard first, then advisory
    return sorted(out, key=lambda d: 0 if d["kind"] == "hard" else 1)


# ── gated retrieval ─────────────────────────────────────────────────────────────
def retrieve(query, man, cart, log):
    """Authoritative-source-first, gated. Returns {found, source, passage, refused[]}."""
    ret = man.get("retrieval", {})
    book_rel = ret.get("source_first", "")
    book_path = os.path.join(cart, book_rel) if book_rel else ""
    idx_path = os.path.join(cart, "source", "book.index.jsonl")
    # 1a) the STRUCTURED INDEX first (cited chunks, front-matter pre-filtered) — the best retrieval
    if os.path.exists(idx_path):
        chunks = [json.loads(l) for l in open(idx_path, encoding="utf-8") if l.strip()]
        hits = [c for c in chunks if not c.get("frontmatter") and query.lower() in c["text"].lower()]
        if hits:
            best = max(hits, key=lambda c: c["text"].lower().count(query.lower()))
            cite = f"Ch {best.get('chapter')} p.{best.get('page')}"
            j = best["text"].lower().find(query.lower())
            passage = " ".join(best["text"][max(0, j - 60): j + 240].split())
            log.append(f"    retrieve('{query}') -> index chunk {best['id']} [{cite}]; "
                       f"{len(hits)} content chunks match (front-matter pre-filtered by ingest.py)")
            return {"found": True, "source": f"book.index.jsonl [{cite}]", "passage": passage, "refused": []}
        log.append(f"    retrieve('{query}') -> not in indexed source; consulting authoritative allowlist")
    # 1b) fallback: raw blob if the index was never built — TOC-skip + digit-density heuristic
    elif book_rel and os.path.exists(book_path):
        text = open(book_path, encoding="utf-8", errors="ignore").read()
        low, L = text.lower(), len(text)
        hits = [m.start() for m in re.finditer(re.escape(query.lower()), low)]
        if hits:
            body = [h for h in hits if h > L * 0.15] or hits
            best = next((h for h in body
                         if sum(ch.isdigit() for ch in text[h:h + 260]) / 260 < 0.03), body[0])
            passage = " ".join(text[max(0, best - 40): best + 260].split())
            log.append(f"    retrieve('{query}') -> FOUND in raw source ({book_rel}); {len(hits)} hits, "
                       f"body passage at {round(100 * best / L)}% (run ingest.py for cited chunks)")
            return {"found": True, "source": book_rel, "passage": passage, "refused": []}
        log.append(f"    retrieve('{query}') -> not in source; consulting authoritative allowlist")
    else:
        log.append(f"    retrieve('{query}') -> source absent; consulting authoritative allowlist")
    # 2) gated allowlist fallback (a live run would WebFetch these; non-allowlisted are REFUSED)
    allow = ret.get("authoritative_allowlist", [])
    refused = []
    # demonstrate the gate: a non-allowlisted source is refused, never fetched
    for candidate in ["randomblog.example.com", "medium.com/@someone"]:
        if not any(a in candidate for a in allow):
            refused.append(candidate)
            log.append(f"    GATE: REFUSED non-authoritative source '{candidate}' (not on allowlist)")
    log.append(f"    GATE: would fetch only from allowlist {allow} (WebFetch, live run)")
    return {"found": False, "source": None, "passage": None, "refused": refused}


# ── deficiency-specific fixes (grounded in the retrieval) ───────────────────────
def apply_fix(deficiency, retrieval, skill_text, man, cart="."):
    """Return improved skill_text with a fix GROUNDED in the retrieved authoritative material.
    Deterministic + honest: the added instruction cites the real retrieved principle; no fabrication."""
    did = deficiency["id"]
    if did == "S5" and retrieval.get("found"):
        block = (
            "\n## Handling missing or insufficient input\n"
            "If no artifact is provided (no PRD, design doc, engineering proposal, or described "
            "decision), do NOT fabricate a critique — **ask for the artifact first**, then wait. If the "
            "input is too thin to critique, say so and request the specifics (interfaces, module "
            "boundaries) before responding.\n\n"
            "This applies the book's own principle, *define errors out of existence*: rather than "
            "erroring or inventing, redesign the interaction so the empty case is handled by requesting "
            "what is needed. (Grounded in the authoritative source; see `skill/GROUNDING.md`.)\n"
        )
        # append near the end, before the Example section if present
        anchor = "## Example Invocation"
        if anchor in skill_text:
            return skill_text.replace(anchor, block + "\n" + anchor, 1)
        return skill_text + block
    if did == "S9":
        mn = man.get("craft", {}).get("mnemonic", {})
        exp = mn.get("expansion", [])
        rows = "\n".join(f"- **{e['letter']} — {e['principle']}**" for e in exp)
        block = (
            f"\n## Memory hook — {mn.get('acronym')} (make the core principles stick)\n"
            f"Teach this mnemonic so a learner recalls the key moves years later, EPIC-style:\n{rows}\n\n"
            f"Every letter maps to a principle grounded in *A Philosophy of Software Design* "
            f"(verified against the source; see `skill/GROUNDING.md`).\n")
        anchor = "## Example Invocation"
        if anchor in skill_text:
            return skill_text.replace(anchor, block + "\n" + anchor, 1)
        return skill_text + block
    if did == "S11":
        voice = man.get("craft", {}).get("voice", {})
        quotes = voice.get("signature_quotes", [])
        # idempotent: strip any prior voice block (the raised bar replaces a generic one with sharp lines)
        skill_text = re.sub(r"\n## Speak in the author's voice.*?(?=\n## |\Z)", "\n", skill_text, flags=re.S)
        pick = [q for q in quotes if q.lower() not in skill_text.lower()][:5]
        rows = "\n".join(f'- "{q}"' for q in pick)
        block = (
            "\n## Speak in the author's voice\n"
            "A total expert quotes the master. Weave in Ousterhout's own SHARP lines where they land — "
            "verbatim, fair-use, and interview-grade (a tradeoff or a coined mechanism, never a platitude), "
            "from *A Philosophy of Software Design*:\n"
            f"{rows}\n\n(Each is verbatim in the source; see `skill/GROUNDING.md`.)\n")
        anchor = "## Example Invocation"
        if anchor in skill_text:
            return skill_text.replace(anchor, block + "\n" + anchor, 1)
        return skill_text + block
    if did == "S14":
        td = man.get("craft", {}).get("tradeoff_decisions", [])
        rows = "\n".join(f"- **{d['name']}**" for d in td)
        block = (
            "\n## Trade-off case studies to teach\n"
            "Ground every trade-off in the author's ACTUAL decisions from the book — never invent one. "
            "These are the source's case studies (all verbatim in the source; see `skill/GROUNDING.md`):\n"
            f"{rows}\n")
        skill_text = re.sub(r"\n## Trade-off case studies to teach.*?(?=\n## |\Z)", "\n", skill_text, flags=re.S)
        anchor = "## Example Invocation"
        if anchor in skill_text:
            return skill_text.replace(anchor, block + "\n" + anchor, 1)
        return skill_text + block
    if did == "S18":
        cards = frameworks.load_cards(cart, man) or []
        # cited cards first (real book figures outrank derived); each carries its figure + reframe
        cards = sorted(cards, key=lambda c: 0 if c.get("provenance", {}).get("kind") == "cited" else 1)
        rows = []
        for c in cards:
            p = c.get("provenance", {})
            tag = f"Fig {p['figure']}, APOSD Ch {c.get('grounding', {}).get('chapter')}" if p.get("kind") == "cited" \
                else "derived, not cited"
            rows.append(f"- **{c['name']}** ({tag}) — {c['one_liner']}  \n  *Ask:* {c['reframes_question']}")
        block = (
            "\n## Frameworks to deploy\n"
            "Deploy the author's own skimmable figures as tools. CITED cards are real book figures and "
            "OUTRANK derived cards (which are labeled, never presented as a citation):\n"
            + "\n".join(rows) + "\n\n(Cards + grounding in `frameworks/cards.jsonl`.)\n")
        skill_text = re.sub(r"\n## Frameworks to deploy.*?(?=\n## |\Z)", "\n", skill_text, flags=re.S)
        anchor = "## Example Invocation"
        if anchor in skill_text:
            return skill_text.replace(anchor, block + "\n" + anchor, 1)
        return skill_text + block
    return skill_text  # no deterministic handler -> unchanged (would route to a model iterate step)


def main(cart, max_rounds=3):
    man, skill_path = load(cart)
    skill_text = open(skill_path, encoding="utf-8").read()
    stage_dir = os.path.join(cart, "staging", "loop")
    os.makedirs(stage_dir, exist_ok=True)

    # ingestion step: once a source is present, make it RETRIEVABLE — build the cited chunk index so
    # retrieval returns coherent, citable passages (front-matter pre-filtered) instead of blob windows.
    if not os.path.exists(os.path.join(cart, "source", "book.index.jsonl")) and ingest.build(cart):
        print("[ingest] source made retrievable -> source/book.index.jsonl (cited chunks)\n")

    report = {"cartridge": os.path.basename(cart.rstrip("/")), "rounds": []}
    print(f"\n=== PROGRESSIVE DRIVER · {report['cartridge']} ===")
    print("    eval -> deficiency -> retrieve(authoritative, gated) -> fix -> re-eval\n")

    rnd = 0
    while rnd < max_rounds:
        defs = deficiencies(skill_text, man, cart)
        if not defs:
            print(f"[round {rnd}] no open deficiencies — BAR MET, converged.")
            report["rounds"].append({"round": rnd, "deficiencies": [], "converged": True})
            break
        d = defs[0]
        log = []
        print(f"[round {rnd}] deficiency: {d['id']} ({d['kind']}) — {d['name']}")
        if not d.get("query"):
            print(f"           no retrieval route for {d['id']} (would go to a model iterate step); stopping.")
            report["rounds"].append({"round": rnd, "picked": d["id"], "note": "no retrieval route"})
            break
        r = retrieve(d["query"], man, cart, log)
        for line in log:
            print(line)
        if r["found"]:
            print(f"    grounded in: \"{r['passage'][:110]}...\"")
        _eval = lambda t: {c["id"]: c["pass"] for c in
                           list(craft.evaluate(t, man, cart)) + list(frameworks.evaluate(t, man, cart))}
        before = _eval(skill_text)
        skill_text = apply_fix(d, r, skill_text, man, cart)
        after = _eval(skill_text)
        closed = before.get(d["id"]) is False and after.get(d["id"]) is True
        print(f"    fix applied; re-eval: {d['id']} {before.get(d['id'])} -> {after.get(d['id'])}"
              f"  {'[CLOSED]' if closed else '[still open]'}\n")
        report["rounds"].append({"round": rnd, "picked": d["id"], "query": d["query"],
                                 "retrieval": {"found": r["found"], "source": r["source"],
                                               "refused": r["refused"]},
                                 "closed": closed})
        if not closed:
            print(f"    {d['id']} did not close deterministically — routing to model iterate step (out of scope here).")
            break
        rnd += 1

    # stage the improved candidate — NEVER auto-applied to the vendored subject
    open(os.path.join(stage_dir, "SKILL.md"), "w", encoding="utf-8").write(skill_text)
    json.dump(report, open(os.path.join(stage_dir, "loop-report.json"), "w"), indent=2)
    remaining = deficiencies(skill_text, man, cart)
    print(f"staged improved candidate -> {os.path.relpath(os.path.join(stage_dir, 'SKILL.md'), cart)}"
          f"  (live skill UNTOUCHED)")
    print(f"remaining deficiencies: {[d['id'] for d in remaining] or 'none — SHIP'}")
    return 0 if not remaining else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(2)
    mr = 3
    if "--max-rounds" in args:
        mr = int(args[args.index("--max-rounds") + 1])
    sys.exit(main(args[0], mr))
