#!/usr/bin/env python3
"""
dossier.py — the DEEP dossier: a principle-keyed SEMANTIC view over the page-index substrate.

The book index is chunked by PAGE (physical — the right grain for retrieval, citation, and verbatim
verification). But teaching the DEEP mnemonic needs a different grain: for each principle, its
{lesson, anecdotes, quote}, together. This composes that view DETERMINISTICALLY by joining
  mnemonic principle  ×  tradeoff-decisions  ×  signature-quotes  ×  the index's chapter tags
— no re-chunking of the book, no model. The page-chunks stay the substrate; this is the query-time
assembly a mature RAG system separates from the raw store.

Answering "is by-chapter chunking the best way to encode DEEP?": the chunking is the right SUBSTRATE;
this dossier is the right VIEW. It also surfaces coverage gaps a flat mnemonic hides (e.g. a principle
whose home chapter carries no trade-off anecdote).

  python3 engine/dossier.py cartridges/<name>          # markdown dossier
  python3 engine/dossier.py cartridges/<name> --json
"""
import json
import os
import sys


def build(cart):
    man = json.load(open(os.path.join(cart, "manifest.json"), encoding="utf-8"))
    craft = man.get("craft", {})
    idx = os.path.join(cart, "source", "book.index.jsonl")
    content = []
    if os.path.exists(idx):
        content = [c for c in (json.loads(l) for l in open(idx, encoding="utf-8") if l.strip())
                   if not c.get("frontmatter")]

    def chapter_of(probe):
        h = [c for c in content if probe and probe.lower() in c["text"].lower()]
        return max(h, key=lambda c: c["text"].lower().count(probe.lower())).get("chapter") if h else None

    def lesson(ch, probe):
        h = [c for c in content if c.get("chapter") == ch and probe and probe.lower() in c["text"].lower()]
        h = h or [c for c in content if c.get("chapter") == ch]
        if not h:
            return None
        c = h[0]
        i = max(0, c["text"].lower().find(probe.lower())) if probe else 0
        return " ".join(c["text"][i:i + 200].split())

    tds = craft.get("tradeoff_decisions", [])
    quotes = craft.get("voice", {}).get("signature_quotes", [])
    dossier = []
    for e in craft.get("mnemonic", {}).get("expansion", []):
        probe = e.get("ground_probe", "")
        ch = e.get("home_chapter") or chapter_of(probe)
        anec = [d["name"] for d in tds if chapter_of(d.get("book_probe", "")) == ch]
        key = probe.split()[0] if probe else ""
        q = next((x for x in quotes if key and key in x.lower()), None)
        dossier.append({"letter": e.get("letter"), "principle": e.get("principle"), "chapter": ch,
                        "lesson": lesson(ch, probe), "anecdotes": anec, "quote": q,
                        "gap": not anec})
    return man, dossier, bool(content)


def main(cart, as_json=False):
    man, dossier, have_index = build(cart)
    acr = man.get("craft", {}).get("mnemonic", {}).get("acronym", "?")
    if as_json:
        print(json.dumps({"acronym": acr, "have_index": have_index, "dossier": dossier}, indent=2))
        return
    print(f"\n=== {acr} DOSSIER · principle-keyed view over the page substrate "
          f"{'(index present)' if have_index else '(NO index — run ingest.py; lessons/anecdotes limited)'} ===\n")
    for d in dossier:
        print(f"  {d['letter']} — {d['principle']}   [Ch {d['chapter']}]")
        if d["quote"]:
            print(f"      quote:    \"{d['quote']}\"")
        print(f"      anecdotes: {d['anecdotes'] or 'NONE in this chapter — a coverage gap the flat mnemonic hid'}")
        if d["lesson"]:
            print(f"      lesson:   {d['lesson'][:120]}...")
        print()
    gaps = [d["letter"] for d in dossier if d["gap"]]
    if gaps:
        print(f"  NOTE: principle(s) {gaps} carry no trade-off anecdote in their home chapter — "
              "richer teaching means finding one or re-homing the principle.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(2)
    main(args[0], as_json="--json" in args)
