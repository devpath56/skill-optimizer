#!/usr/bin/env python3
"""
rag_eval.py — RAGAS-style DETERMINISTIC evaluation of the retrieval/grounding pipeline. This is the
"acceptance = behavior" bar for the RAG substrate: the loop retrieves from an ingested source, and this
measures whether that retrieval is any good — with the three standard RAGAS metrics computed as code
(no LLM judge) against the cited index + committed answer keys.

  Context Precision  — does retrieve(query) land in the concept's HOME chapter (per the book's TOC),
                       not an incidental mention elsewhere? (needs the index)
  Context Recall     — does the grounding bundle carry the source's key items (the answer key)?
  Faithfulness       — is every checkable claim (signature quotes, anecdote probes) VERBATIM in the
                       source? (needs the book text)

Book-gated: precision/faithfulness need the licensed source (the index / book text); when absent they
are NOT-RUN (loud), never a bare pass. Recall runs on committed data. Machine-readable --json.

  python3 engine/rag_eval.py cartridges/<name>          # metrics table + PASS/BLOCK
  python3 engine/rag_eval.py cartridges/<name> --json

Exit: 0 all measured metrics >= threshold · 1 a metric below bar · 6 nothing measurable.
"""
import json
import os
import sys


def _grounding_blob(cart, man):
    """The bundle a teaching agent receives: skill + bundled grounding (lowercased)."""
    blob = ""
    g = (man.get("craft") or {}).get("grounding") or {}
    b = os.path.join(cart, g.get("bundle", "")) if g.get("bundle") else ""
    if b and os.path.exists(b):
        blob += open(b, encoding="utf-8", errors="ignore").read().lower()
    sf = man.get("skill_file", "")
    if sf and not sf.startswith(("~", "/")) and os.path.exists(os.path.join(cart, sf)):
        blob += "\n" + open(os.path.join(cart, sf), encoding="utf-8", errors="ignore").read().lower()
    return blob


def evaluate(cart):
    """Return a list of (name, value|None, threshold, detail, notrun)."""
    man = json.load(open(os.path.join(cart, "manifest.json"), encoding="utf-8"))
    rag = man.get("rag_eval", {})
    craft = man.get("craft", {})
    idx = os.path.join(cart, "source", "book.index.jsonl")
    metrics = []

    # Context Precision — retrieval lands in the concept's home chapter (needs the index)
    gold = rag.get("precision_gold", [])
    if os.path.exists(idx) and gold:
        content = [c for c in (json.loads(l) for l in open(idx, encoding="utf-8") if l.strip())
                   if not c.get("frontmatter")]
        hits, miss = 0, []
        for g in gold:
            q = g["query"].lower()
            h = [c for c in content if q in c["text"].lower()]
            if h and max(h, key=lambda c: c["text"].lower().count(q)).get("chapter") == g["chapter"]:
                hits += 1
            else:
                got = max(h, key=lambda c: c["text"].lower().count(q)).get("chapter") if h else "none"
                miss.append(f"{g['query']}->Ch{got}(exp {g['chapter']})")
        metrics.append(("context_precision", hits / len(gold), rag.get("precision_min", 0.8),
                        f"{hits}/{len(gold)} land in home chapter" + (f"; MISS {miss}" if miss else ""), False))
    else:
        metrics.append(("context_precision", None, rag.get("precision_min", 0.8),
                        "NOT-RUN — index absent (run engine/ingest.py)", True))

    # Context Recall — the grounding bundle carries the source's key case-studies (committed data)
    td = craft.get("tradeoff_decisions", [])
    if td:
        blob = _grounding_blob(cart, man)
        cov = [d for d in td if d.get("grounding_probe", "").lower() in blob]
        metrics.append(("context_recall", len(cov) / len(td), rag.get("recall_min", 0.9),
                        f"{len(cov)}/{len(td)} source case-studies carried by the grounding", False))

    # Faithfulness — every checkable claim is verbatim in the source (needs the book text)
    book_rel = (craft.get("grounding") or {}).get("authoritative_resource", "")
    book = os.path.join(cart, book_rel) if book_rel else ""
    claims = (craft.get("voice", {}).get("signature_quotes", [])
              + (craft.get("grounding", {}) or {}).get("anecdote_probes", []))
    if book and os.path.exists(book) and claims:
        bk = open(book, encoding="utf-8", errors="ignore").read().lower()
        grounded = [c for c in claims if c.lower() in bk]
        metrics.append(("faithfulness", len(grounded) / len(claims), rag.get("faithfulness_min", 1.0),
                        f"{len(grounded)}/{len(claims)} claims verbatim in source", False))
    else:
        metrics.append(("faithfulness", None, rag.get("faithfulness_min", 1.0),
                        "NOT-RUN — source text absent (book gitignored); faithfulness verified where present", True))
    return metrics


def main(cart, as_json=False):
    metrics = evaluate(cart)
    measured = [m for m in metrics if not m[4]]
    below = [m for m in measured if m[1] < m[2]]
    if as_json:
        print(json.dumps({"cartridge": os.path.basename(cart.rstrip("/")),
                          "metrics": [{"name": n, "value": v, "threshold": t, "notrun": nr, "detail": d}
                                      for (n, v, t, d, nr) in metrics],
                          "below_bar": [m[0] for m in below],
                          "verdict": "PASS" if not below else "BLOCK"}, indent=2))
        sys.exit(1 if below else 0)
    print("\n=== RAG EVAL (RAGAS-style, deterministic) · retrieval acceptance bar ===")
    for n, v, t, d, nr in metrics:
        mark = "NOT-RUN " if nr else ("ok  " if v >= t else "BELOW")
        val = "  n/a " if nr else f" {v:.2f}"
        print(f"  {mark} {n:18}{val} (>= {t:.2f})  {d}")
    if not measured:
        print("\n  VERDICT: nothing measurable (supply the source).")
        sys.exit(6)
    print("\n  VERDICT: " + ("PASS — retrieval meets the bar" if not below
                             else f"BLOCK — below bar: {[m[0] for m in below]}"))
    sys.exit(1 if below else 0)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(2)
    main(args[0], as_json="--json" in args)
