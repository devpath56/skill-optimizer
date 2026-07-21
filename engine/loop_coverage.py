#!/usr/bin/env python3
"""
loop_coverage.py — the CF-076 guard: the progressive loop is the SPINE, and every gating signal is
either loop-driven or has a DOCUMENTED non-loop route. Never again a signal the loop silently stopped
driving (the loop-drop failure).

It cross-checks three things that must agree:
  1. every signal an evaluator GATES ON is declared in signal_routes.ROUTES (no ungoverned signal);
  2. every ROUTES `loop` signal has a REAL handler in loop.py (RETRIEVAL_QUERY entry + apply_fix branch),
     and every RETRIEVAL_QUERY handler maps back to a `loop` signal (no orphan handler);
  3. every signal is documented in SIGNALS.md (no doc drift — the spine stays written down).

  python3 engine/loop_coverage.py cartridges/<name>            # PASS (0) / GAP (1) / INCOMPLETE (6)
  python3 engine/loop_coverage.py cartridges/<name> --json     # machine view
  python3 engine/loop_coverage.py --selftest                   # negative controls: prove each branch fires

Exit: 0 covered · 1 coverage GAP · 6 repo integrity (cannot enumerate).
"""
import json, os, re, sys

ENG = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENG)
import signal_routes  # the SSOT registry
PASS, GAP, INCOMPLETE = 0, 1, 6


def _apply_fix_ids(loop_src):
    """The signal ids loop.py's apply_fix actually branches on (did == "Sxx")."""
    return set(re.findall(r'did\s*==\s*"([^"]+)"', loop_src))


def coverage_gaps(signal_ids, routes, retrieval_query, apply_fix_ids, doc_text):
    """PURE core. Return a list of coverage-gap strings (empty = fully covered). Every input is data so
    --selftest can drive each branch with a synthetic value."""
    gaps = []
    loop_declared = {i for i, r in routes.items() if r.get("route") == "loop"}

    # 1. every gated signal is governed by a route
    for sid in sorted(signal_ids):
        if sid not in routes:
            gaps.append(f"signal {sid} is gated by an evaluator but has NO route in signal_routes.ROUTES "
                        "(ungoverned — the loop-drop failure). Declare loop | pre-populated | "
                        "verification-twin | model-iterate.")

    # 2a. a `loop` route must have a real handler (query + apply_fix branch)
    for sid in sorted(loop_declared):
        if sid not in retrieval_query:
            gaps.append(f"{sid} is declared route=loop but has NO RETRIEVAL_QUERY entry in loop.py "
                        "(the loop cannot retrieve for it).")
        if sid not in apply_fix_ids:
            gaps.append(f"{sid} is declared route=loop but apply_fix has no `did == \"{sid}\"` branch "
                        "(the loop cannot inject its fix).")
    # 2b. no orphan handler: every RETRIEVAL_QUERY key is a `loop` signal
    for sid in sorted(retrieval_query):
        if sid not in loop_declared:
            gaps.append(f"loop.py RETRIEVAL_QUERY has a handler for {sid} but it is not declared "
                        "route=loop in signal_routes.ROUTES (orphan handler — drift).")

    # 2c. a verification-twin must name a twin that exists
    for sid, r in sorted(routes.items()):
        if r.get("route") == "verification-twin" and r.get("twin_of") not in routes:
            gaps.append(f"{sid} is a verification-twin of {r.get('twin_of')!r}, which is not a known signal.")

    # 3. every signal is written down in the spine doc
    for sid in sorted(signal_ids):
        if not re.search(rf"\b{re.escape(sid)}\b", doc_text):
            gaps.append(f"signal {sid} is not documented in SIGNALS.md (the spine must stay written down).")
    return gaps


# ── live wiring ───────────────────────────────────────────────────────────────
def _gated_signal_ids(cart):
    """Every signal id the present evaluators GATE ON. craft.py always; contrarian/frameworks when they
    exist and expose SIGNAL_IDS (the hook that forces a new evaluator to register its routes)."""
    import craft
    man = craft.load_manifest(cart)
    txt, _path, _status = craft.load_skill(cart, man)
    ids = {c["id"] for c in craft.evaluate(txt or "", man, cart)}
    for mod_name in ("contrarian", "frameworks"):
        try:
            mod = __import__(mod_name)
            ids |= set(getattr(mod, "SIGNAL_IDS", []))
        except Exception:
            pass  # evaluator not built yet — its signals will be governed once it exists
    return ids


def run(cart):
    import loop  # the handlers under test
    doc = os.path.join(cart, "SIGNALS.md")
    if not os.path.exists(doc):
        doc = os.path.join(ENG, "..", "cartridges", os.path.basename(cart.rstrip("/")), "SIGNALS.md")
    doc_text = open(doc, encoding="utf-8").read() if os.path.exists(doc) else ""
    if not doc_text:
        return INCOMPLETE, [f"SIGNALS.md not found for {cart} (the spine doc is required)"], {}
    signal_ids = _gated_signal_ids(cart)
    loop_src = open(os.path.join(ENG, "loop.py"), encoding="utf-8").read()
    gaps = coverage_gaps(signal_ids, signal_routes.ROUTES, loop.RETRIEVAL_QUERY,
                         _apply_fix_ids(loop_src), doc_text)
    detail = {"signals": sorted(signal_ids), "loop_signals": signal_routes.LOOP_SIGNALS,
              "retrieval_query": sorted(loop.RETRIEVAL_QUERY), "gaps": gaps}
    return (PASS if not gaps else GAP), gaps, detail


def selftest():
    """Negative controls — each known-bad input MUST produce a gap; the clean input must not."""
    routes = {"S5": {"route": "loop"}, "S9": {"route": "verification-twin", "twin_of": "S5"}}
    rq = {"S5": "q"}
    afx = {"S5"}
    doc = "S5 S9 documented here"
    cases = [
        ("clean input has no gap (positive control)",
         coverage_gaps({"S5", "S9"}, routes, rq, afx, doc), False),
        ("ungoverned signal fires",
         coverage_gaps({"S5", "S9", "S99"}, routes, rq, afx, doc + " S99"), True),
        ("loop signal with no RETRIEVAL_QUERY fires",
         coverage_gaps({"S5"}, {"S5": {"route": "loop"}}, {}, {"S5"}, "S5"), True),
        ("loop signal with no apply_fix branch fires",
         coverage_gaps({"S5"}, {"S5": {"route": "loop"}}, {"S5": "q"}, set(), "S5"), True),
        ("orphan RETRIEVAL_QUERY handler fires",
         coverage_gaps({"S5"}, {"S5": {"route": "loop"}}, {"S5": "q", "S7": "q"}, {"S5"}, "S5 S7"), True),
        ("undocumented signal fires (doc drift)",
         coverage_gaps({"S5", "S9"}, routes, rq, afx, "only S5 here"), True),
        ("verification-twin naming a ghost twin fires",
         coverage_gaps({"S5"}, {"S5": {"route": "verification-twin", "twin_of": "GHOST"}}, {}, set(), "S5"), True),
    ]
    ok = True
    print("=== loop_coverage negative controls (CF-076 guard) ===")
    for name, gaps, want_gap in cases:
        fired = bool(gaps)
        good = fired == want_gap
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} {name}" + ("" if good else f"  (fired={fired}, want={want_gap})"))
    # the REAL registry must be internally consistent (twins resolve, loop signals declared)
    real_gaps = coverage_gaps(set(signal_routes.ROUTES), signal_routes.ROUTES,
                              {i: "q" for i in signal_routes.LOOP_SIGNALS},
                              set(signal_routes.LOOP_SIGNALS),
                              " ".join(signal_routes.ROUTES))
    twin_or_orphan = [g for g in real_gaps if "verification-twin" in g or "orphan" in g]
    print(f"  {'ok  ' if not twin_or_orphan else 'FAIL'} the shipped ROUTES registry is internally consistent")
    ok = ok and not twin_or_orphan
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__); sys.exit(2)
    if args[0] == "--selftest":
        selftest()
    cart = args[0]
    as_json = "--json" in args
    code, gaps, detail = run(cart)
    if as_json:
        print(json.dumps({"verdict": "COVERED" if code == PASS else ("INCOMPLETE" if code == INCOMPLETE else "GAP"),
                          "exit": code, **detail}, indent=2))
    else:
        print(f"\n=== LOOP COVERAGE · {os.path.basename(cart.rstrip('/'))} (CF-076 guard) ===")
        if code == INCOMPLETE:
            for g in gaps: print(f"  INCOMPLETE: {g}")
        elif not gaps:
            print(f"  COVERED — {len(detail['signals'])} gated signal(s); "
                  f"loop drives {detail['loop_signals']}; the rest are pre-populated / verification-twins.")
        else:
            for g in gaps: print(f"  GAP: {g}")
    sys.exit(code)
