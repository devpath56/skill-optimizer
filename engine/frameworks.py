#!/usr/bin/env python3
"""
frameworks.py — signals S18/S19: the book's skimmable infographics become the advisor's TOOLS. A
framework card (frameworks/cards.jsonl) is a reusable diagram/heuristic the advisor deploys on a
problem. CITED cards are grounded in a REAL book figure; DERIVED cards are synthesized and MUST be
labeled "derived, not cited" so an agent never mistakes one for a book citation.

  S18  frameworks are TAUGHT (advisory, LOOP)      — the skill surfaces >= min_cards cards; a deficiency
                                                     is closed by loop.py injecting a "Frameworks to
                                                     deploy" section from the authored cards (cited first).
  S19  frameworks are REAL (hard, book-gated,       — every card is schema-complete; every CITED card's
       verification-twin of S18)                      figure appears in the book AND its verbatim_probe is
                                                       in the source; every DERIVED card is labeled and
                                                       carries no figure; cited cards OUTRANK derived
                                                       (listed first). NOT-RUN (loud) when the book absent.

  python3 engine/frameworks.py cartridges/<name>          # PASS (0) / GAP (1) / INCOMPLETE (6)
  python3 engine/frameworks.py cartridges/<name> --json   # the agent-reasonable catalog + verdict
  python3 engine/frameworks.py --selftest                 # negative controls: each known-bad must fail

Exit: 0 all HARD pass · 1 a HARD check failed · 6 cards/schema missing (repo integrity).
"""
import json, os, sys

ENG = os.path.dirname(os.path.abspath(__file__))
PASS, GAP, INCOMPLETE = 0, 1, 6
SIGNAL_IDS = ["S18", "S19"]  # loop_coverage enumerates these


def _norm_typo(s):
    return str(s).translate({0x2019: 0x27, 0x2018: 0x27, 0x201c: 0x22, 0x201d: 0x22,
                             0x2013: 0x2d, 0x2014: 0x2d, 0xa0: 0x20})


def _book_low(cart, man):
    rel = (man.get("craft", {}).get("grounding") or {}).get("authoritative_resource", "")
    path = os.path.join(cart, rel) if rel else ""
    if rel and os.path.exists(path):
        return _norm_typo(open(path, encoding="utf-8", errors="ignore").read()).lower()
    return None


def load_cards(cart, man):
    rel = man.get("frameworks", {}).get("cards", os.path.join("frameworks", "cards.jsonl"))
    path = os.path.join(cart, rel)
    if not os.path.exists(path):
        return None
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _schema_required(cart):
    p = os.path.join(cart, "frameworks", "schema.json")
    if os.path.exists(p):
        return json.load(open(p)).get("required", [])
    return ["id", "name", "provenance", "grounding"]


def card_reality(card, book_low, required):
    """Return a list of reasons this card is not REAL/complete (empty = ok). book_low None => grounding
    checks are skipped by the caller (NOT-RUN)."""
    reasons = []
    for k in required:
        if k not in card:
            reasons.append(f"{card.get('id','?')}: missing required key {k!r}")
    prov = card.get("provenance", {})
    kind = prov.get("kind")
    if kind == "cited":
        fig = prov.get("figure")
        if not fig:
            reasons.append(f"{card.get('id')}: cited card has no provenance.figure")
        elif book_low is not None and f"figure {str(fig).lower()}" not in book_low:
            reasons.append(f"{card.get('id')}: provenance.figure {fig!r} is not a real figure in the source")
    elif kind == "derived":
        if "derived, not cited" not in str(prov.get("note", "")).lower():
            reasons.append(f"{card.get('id')}: derived card not labeled 'derived, not cited'")
        if prov.get("figure"):
            reasons.append(f"{card.get('id')}: derived card must not claim a figure ({prov.get('figure')!r})")
    else:
        reasons.append(f"{card.get('id')}: provenance.kind must be 'cited' or 'derived' (got {kind!r})")
    probe = (card.get("grounding") or {}).get("verbatim_probe", "")
    if book_low is not None and probe and _norm_typo(probe).lower() not in book_low:
        reasons.append(f"{card.get('id')}: verbatim_probe not found in the source (ungrounded)")
    return reasons


def cited_outrank_derived(cards):
    """Cited cards must be listed before derived ones (selection priority). Return True if ordered."""
    kinds = [c.get("provenance", {}).get("kind") for c in cards]
    last_cited = max((i for i, k in enumerate(kinds) if k == "cited"), default=-1)
    first_derived = min((i for i, k in enumerate(kinds) if k == "derived"), default=len(kinds))
    return last_cited < first_derived


def evaluate(skill_text, man, cart="."):
    """craft-shaped checks so loop.py can merge S18 into its deficiency list."""
    cards = load_cards(cart, man)
    if cards is None:
        return [{"id": "S18", "name": "frameworks taught", "kind": "advisory", "pass": True,
                 "detail": "NOT-RUN — cards file absent", "notrun": True},
                {"id": "S19", "name": "frameworks real", "kind": "hard", "pass": True,
                 "detail": "NOT-RUN — cards file absent", "notrun": True}]
    conf = man.get("frameworks", {})
    min_cards = conf.get("min_cards", 3)
    low = skill_text.lower()
    surfaced = [c for c in cards if c.get("name", "###").lower() in low or c.get("id", "###") in skill_text]
    checks = [{"id": "S18", "name": f"frameworks are taught (skill surfaces >= {min_cards} cards)",
               "kind": "advisory", "pass": len(surfaced) >= min_cards, "notrun": False,
               "detail": f"{len(surfaced)}/{len(cards)} framework cards surfaced in the skill (>= {min_cards})"
               if len(surfaced) >= min_cards else
               f"only {len(surfaced)}/{len(cards)} cards surfaced — the loop injects a 'Frameworks to deploy' section"}]
    book_low = _book_low(cart, man)
    required = _schema_required(cart)
    if book_low is None:
        checks.append({"id": "S19", "name": "frameworks are real (vs the authoritative resource)",
                       "kind": "hard", "pass": True, "notrun": True,
                       "detail": "NOT-RUN — authoritative resource absent; figures/probes verified only where the book is present"})
    else:
        bad = [r for c in cards for r in card_reality(c, book_low, required)]
        if not cited_outrank_derived(cards):
            bad.append("cited cards must be listed BEFORE derived cards (selection priority)")
        checks.append({"id": "S19", "name": "frameworks are real (cited figures verbatim; derived labeled)",
                       "kind": "hard", "pass": not bad, "notrun": False,
                       "detail": "every cited card maps to a real figure + verbatim probe; every derived card is labeled"
                       if not bad else "; ".join(bad)})
    return checks


def selftest():
    book = "figure 4.1: deep and shallow modules ... change amplification ... more text"
    req = ["id", "name", "provenance", "grounding"]
    good = {"id": "deep", "name": "Deep vs Shallow", "provenance": {"kind": "cited", "figure": "4.1", "note": "cited"},
            "grounding": {"chapter": "4", "verbatim_probe": "deep and shallow modules"}}
    der = {"id": "sym", "name": "Symptoms", "provenance": {"kind": "derived", "note": "derived, not cited"},
           "grounding": {"chapter": "2", "verbatim_probe": "change amplification"}}
    cases = [
        ("a real cited card passes", card_reality(good, book, req), False),
        ("a labeled derived card passes", card_reality(der, book, req), False),
        ("a cited card with a FAKE figure fails", card_reality({**good, "provenance": {"kind": "cited", "figure": "99.9", "note": "x"}}, book, req), True),
        ("a cited card with a bad verbatim_probe fails", card_reality({**good, "grounding": {"chapter": "4", "verbatim_probe": "not in the book"}}, book, req), True),
        ("an UNLABELED derived card fails", card_reality({**der, "provenance": {"kind": "derived", "note": "whatever"}}, book, req), True),
        ("a derived card CLAIMING a figure fails", card_reality({**der, "provenance": {"kind": "derived", "figure": "4.1", "note": "derived, not cited"}}, book, req), True),
        ("a card missing a required key fails", card_reality({k: v for k, v in good.items() if k != "name"}, book, req), True),
    ]
    ok = True
    print("=== frameworks negative controls (S18/S19) ===")
    for name, reasons, want_bad in cases:
        good_case = bool(reasons) == want_bad
        ok = ok and good_case
        print(f"  {'ok  ' if good_case else 'FAIL'} {name}" + ("" if good_case else f"  ({reasons})"))
    order_ok = cited_outrank_derived([good, der]) and not cited_outrank_derived([der, good])
    print(f"  {'ok  ' if order_ok else 'FAIL'} cited-outrank-derived ordering enforced")
    ok = ok and order_ok
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__); sys.exit(2)
    if args[0] == "--selftest":
        selftest()
    cart = args[0]
    man = json.load(open(os.path.join(cart, "manifest.json"), encoding="utf-8"))
    if load_cards(cart, man) is None:
        print(f"frameworks: cards file missing for {cart} (repo integrity)"); sys.exit(INCOMPLETE)
    sf = man.get("skill_file", "")
    skill_text = open(os.path.join(cart, sf), encoding="utf-8").read() if sf and not sf.startswith(("~", "/")) and os.path.exists(os.path.join(cart, sf)) else ""
    checks = evaluate(skill_text, man, cart)
    if "--json" in args:
        print(json.dumps({"cards": load_cards(cart, man), "checks": checks,
                          "verdict": "CODIFIED" if all(c["pass"] for c in checks if c["kind"] == "hard") else "GAP"}, indent=2))
    else:
        print(f"\n=== FRAMEWORKS · {os.path.basename(cart.rstrip('/'))} (S18 taught / S19 real) ===")
        for c in checks:
            mark = "NOT-RUN " if c.get("notrun") else ("PASS " if c["pass"] else "FAIL ")
            print(f"  {mark}{c['id']} [{c['kind']}] {c['name']}\n        {c['detail']}")
    hard_fail = [c["id"] for c in checks if c["kind"] == "hard" and not c["pass"]]
    sys.exit(GAP if hard_fail else PASS)
