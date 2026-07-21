#!/usr/bin/env python3
"""
contrarian.py — signals 4a/4b: an advisor is worth listening to when it does NOT hand back the
consensus answer. Two independent, deterministic signals over cited problem→answer pairs:

  4a  CONTRARIAN ANSWER   — the advisor's answer diverges from the stock/consensus answer AND flips the
                            frame (a reversal move), not a restatement.
  4b  REFRAME QUESTION    — the advisor returns a QUESTION that reframes the problem (interrogative +
                            introduces new framing vs consensus + tied to a named principle).

  gate (per pair) = (4a OR 4b) AND grounded         # worth listening to AND trustworthy
  grounded        = the cited quote is VERBATIM in the authoritative source (book-gated; NOT-RUN loud
                    when the book is absent — never a bare pass).

HONEST SCOPE (mirrors loop-log D37): 4a/4b are a DETERMINISTIC PROXY — lexical divergence from consensus
+ reframe/reversal markers, NOT semantic stance. The calibrated contrarian/reframe judge (positive class
CONTRARIAN, TPR/TNR>=0.85 via validate-evaluator) is the real metric and is PARKED (contrarian/ templates).
This gate is the fast, non-vacuous floor; it cannot certify true stance-divergence.

  python3 engine/contrarian.py cartridges/<name>            # PASS (0) / FAIL (1) / INCOMPLETE (6)
  python3 engine/contrarian.py cartridges/<name> --json
  python3 engine/contrarian.py --selftest                   # negative controls: each known-bad must fail

Exit: 0 gate holds · 1 a pair fails the gate · 6 pairs file missing (repo integrity).
"""
import json, os, re, sys

ENG = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENG)
PASS, FAIL, INCOMPLETE = 0, 1, 6

# loop_coverage.py enumerates this; both route to the parked model-iterate step (generative, not loop-authorable).
SIGNAL_IDS = ["C4a", "C4b"]

_STOP = set("a an the of to for and or in on is it its be by with as at from that this you your they their "
            "give each own read clean it's done so add write case return log them not do i we he".split())
_REVERSAL = ("instead", "redefine", "redesign", "becomes", "disappear", "no longer", "cannot arise",
             "downward", "idempotent", "one ", " not ", "reframe", "flip", "rather than")
_INTERROG = ("what if", "what would", "what complexity", "which ", "why ", "how ", "who ", "what ")
DIV_MIN = 0.55          # 4a: answer must share < 45% content words with consensus
Q_DIV_MIN = 0.45        # 4b: question introduces new framing (shares < 55% with consensus)


def _cw(s):
    return {w for w in re.findall(r"[a-z0-9]+", str(s).lower()) if w not in _STOP and len(w) > 2}


def divergence(consensus, text):
    """1 - Jaccard overlap of content words. 1.0 = totally different, 0.0 = same words."""
    a, b = _cw(consensus), _cw(text)
    if not a or not b:
        return 1.0
    return 1.0 - len(a & b) / len(a | b)


def is_contrarian_answer(consensus, answer):
    """4a — far from consensus AND a reversal move."""
    low = str(answer).lower()
    return divergence(consensus, answer) >= DIV_MIN and any(m in low for m in _REVERSAL)


def is_reframe_question(consensus, question, principle):
    """4b — a question that reframes: interrogative + new framing vs consensus + tied to a principle."""
    low = str(question).strip().lower()
    interrogative = low.endswith("?") or low.startswith(_INTERROG)
    return (interrogative and divergence(consensus, question) >= Q_DIV_MIN and bool(str(principle).strip()))


def _norm_typo(s):
    """Normalize typographic apostrophes/quotes/dashes so a verbatim check is not defeated by curly vs
    straight glyphs (the source is typeset; the pair JSON is ASCII). This is glyph normalization, NOT
    fuzzy matching — the words must still match exactly."""
    return (str(s).translate({0x2019: 0x27, 0x2018: 0x27, 0x201c: 0x22, 0x201d: 0x22,
                              0x2013: 0x2d, 0x2014: 0x2d, 0xa0: 0x20}))


def grounded(quote, book_low):
    """Verbatim in the source (typography-normalized). True/False, or None when the book is absent."""
    if book_low is None:
        return None
    return _norm_typo(quote).strip().lower() in book_low


def evaluate_pair(p, book_low):
    a4a = is_contrarian_answer(p.get("consensus", ""), p.get("advisor_answer", ""))
    a4b = is_reframe_question(p.get("consensus", ""), p.get("reframe_question", ""), p.get("principle", ""))
    g = grounded(p.get("quote", ""), book_low)
    # gate: (4a OR 4b) AND grounded. When grounded is NOT-RUN (None), the gate is NOT-RUN (structure only).
    gate = (a4a or a4b) and (g is True) if g is not None else None
    return {"id": p.get("id"), "4a": a4a, "4b": a4b, "grounded": g, "gate": gate}


def _book_low(cart):
    man = json.load(open(os.path.join(cart, "manifest.json"), encoding="utf-8"))
    rel = (man.get("craft", {}).get("grounding") or {}).get("authoritative_resource", "")
    path = os.path.join(cart, rel) if rel else ""
    if rel and os.path.exists(path):
        return _norm_typo(open(path, encoding="utf-8", errors="ignore").read()).lower(), man
    return None, man


def run(cart):
    book_low, man = _book_low(cart)
    conf = man.get("contrarian", {})
    pairs_rel = conf.get("pairs", os.path.join("contrarian", "pairs.jsonl"))
    pairs_path = os.path.join(cart, pairs_rel)
    if not os.path.exists(pairs_path):
        return INCOMPLETE, [], {"error": f"pairs file missing: {pairs_rel}"}
    pairs = [json.loads(l) for l in open(pairs_path, encoding="utf-8") if l.strip()]
    results = [evaluate_pair(p, book_low) for p in pairs]
    notrun = book_low is None
    if notrun:
        # structure-only: (4a OR 4b) must hold for every pair; grounding NOT-RUN (loud)
        failed = [r["id"] for r in results if not (r["4a"] or r["4b"])]
    else:
        failed = [r["id"] for r in results if not r["gate"]]
    code = FAIL if failed else PASS
    return code, failed, {"results": results, "notrun_grounding": notrun,
                          "pairs": len(pairs), "failed": failed}


def selftest():
    """Negative controls: each known-bad pair must fail its signal; a real pair must pass."""
    book = "define errors out of existence"  # a tiny synthetic 'book' containing one real quote
    real = {"id": "real", "consensus": "Add error handling: catch the already-gone case and return a 404.",
            "advisor_answer": "Redefine the operation so already-gone is success; the error path disappears.",
            "reframe_question": "What would it take to redefine already-gone as success so the error cannot arise?",
            "principle": "Define errors out of existence", "quote": "define errors out of existence"}
    restated = {**real, "id": "restated", "advisor_answer": "Add error handling: catch the already-gone case and return a 404.",
                "reframe_question": "Add error handling: catch the already-gone case and return a 404."}
    declarative = {**real, "id": "declarative", "advisor_answer": "Same as consensus, more or less.",
                   "reframe_question": "This is a statement, not a question, and it echoes the consensus."}
    fabricated = {**real, "id": "fabricated", "quote": "this exact sentence is not in the book at all"}
    cases = [
        ("real pair passes the gate (positive control)", evaluate_pair(real, book)["gate"], True),
        ("a consensus RESTATEMENT fails 4a", is_contrarian_answer(restated["consensus"], restated["advisor_answer"]), False),
        ("a consensus-echo question fails 4b", is_reframe_question(restated["consensus"], restated["reframe_question"], restated["principle"]), False),
        ("a declarative 'question' fails 4b", is_reframe_question(declarative["consensus"], declarative["reframe_question"], declarative["principle"]), False),
        ("a fabricated quote fails grounded", evaluate_pair(fabricated, book)["grounded"], False),
        ("book absent -> grounded is NOT-RUN (None), never a bare pass", grounded("anything", None), None),
    ]
    ok = True
    print("=== contrarian negative controls (4a/4b + grounded) ===")
    for name, got, want in cases:
        good = got == want
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} {name}" + ("" if good else f"  (got={got!r}, want={want!r})"))
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__); sys.exit(2)
    if args[0] == "--selftest":
        selftest()
    cart = args[0]
    code, failed, detail = run(cart)
    if "--json" in args:
        verdict = "INCOMPLETE" if code == INCOMPLETE else ("WORTH-LISTENING" if code == PASS else "CONSENSUS/UNGROUNDED")
        print(json.dumps({"verdict": verdict, "exit": code, **detail}, indent=2))
    else:
        print(f"\n=== CONTRARIAN · {os.path.basename(cart.rstrip('/'))} (4a answer / 4b reframe, grounded) ===")
        if code == INCOMPLETE:
            print(f"  INCOMPLETE: {detail.get('error')}")
        else:
            for r in detail["results"]:
                g = {True: "grounded", False: "UNGROUNDED", None: "NOT-RUN"}[r["grounded"]]
                print(f"  {r['id']:<10} 4a={'Y' if r['4a'] else '·'} 4b={'Y' if r['4b'] else '·'}  {g}"
                      f"  ->  {'gate ok' if (r['gate'] or (detail['notrun_grounding'] and (r['4a'] or r['4b']))) else 'GATE FAIL'}")
            if detail["notrun_grounding"]:
                print("  NOTE: grounding NOT-RUN (book absent) — structure (4a OR 4b) checked only, never a bare pass")
            print(f"\n  VERDICT: {'WORTH LISTENING' if code == PASS else 'FAIL — ' + ','.join(failed)}")
    sys.exit(code)
