#!/usr/bin/env python3
"""
Craft axis (S) — deterministic checks that the ARCHITECT'S CRAFT IS CODIFIED IN THE SKILL FILE itself.

Efficacy (`score.py`) checks the skill's OUTPUTS; fidelity checks its content vs the SOURCE. Neither
looks at whether the skill FILE, as written, actually encodes the craft it must apply. This axis does —
statically, deterministically, at zero model cost. Hand it to an agent instead of asking it to read the
skill and fuzzily judge "is this well-crafted?": `craft.py --json` returns per-requirement PASS/FAIL and
exactly what is missing, so the judgement is cheap, reproducible, and localizable.

Cartridge-driven: WHAT must be codified is declared in `manifest.craft` and reused from `closed_vocab` /
`expected_sections`. The engine holds no skill knowledge.

Checks (HARD = ship-blocking; ADVISORY = reported, not blocking):
  S1 HARD      vocab codified        — every closed_vocab red-flag name appears in the skill
  S2 HARD      contract codified     — every expected_section is declared in the skill
  S3 HARD      framework codified    — the craft's analytical core (manifest.craft.framework_terms)
  S4 HARD      source grounding      — the skill points at its authoritative source (any source_marker)
  S5 ADVISORY  refusal codified      — decline-on-empty is INSTRUCTED, not left to model default
  S6 ADVISORY  worked example        — the craft is shown, not only told

  python3 engine/craft.py cartridges/<name>            # human table  · exit 0 ok / 1 HARD gap / 6 missing
  python3 engine/craft.py cartridges/<name> --json     # machine-readable scorecard for agents (stdout)
  python3 engine/craft.py cartridges/<name> --selftest  # negative control: degrade skill -> S1 must FAIL

Exit: 0 all HARD pass · 1 a HARD check failed · 6 vendored skill_file missing (INCOMPLETE, fail-loud).
A skill_file that is EXTERNAL (~/absolute, not vendored) is NOT-RUN (exit 0) — not gradeable here.
"""
import json
import os
import re
import sys


def load_manifest(cart):
    return json.load(open(os.path.join(cart, "manifest.json"), encoding="utf-8"))


def load_skill(cart, man):
    """Return (text, path, status). status: 'ok' | 'external' (not vendored) | 'missing'."""
    sf = man.get("skill_file", "")
    if not sf or sf.startswith(("~", "/")):
        return None, sf, "external"
    p = os.path.join(cart, sf)
    if not os.path.exists(p):
        return None, p, "missing"
    return open(p, encoding="utf-8").read(), p, "ok"


def _missing(text, terms):
    low = text.lower()
    return [t for t in terms if t.lower() not in low]


def _hits(text, terms):
    low = text.lower()
    return [t for t in terms if t.lower() in low]


def evaluate(text, man):
    """Deterministic craft checks over the skill text. Returns a list of check dicts."""
    craft = man.get("craft", {})
    checks = []

    def add(cid, name, kind, ok, detail):
        checks.append({"id": cid, "name": name, "kind": kind, "pass": bool(ok), "detail": detail})

    miss = _missing(text, man.get("closed_vocab", []))
    add("S1", "vocab codified (all red-flag names present in the skill)", "hard",
        not miss, "all present" if not miss else f"MISSING {miss}")

    miss = _missing(text, man.get("expected_sections", []))
    add("S2", "output contract codified (all response sections declared)", "hard",
        not miss, "all present" if not miss else f"MISSING {miss}")

    fw = craft.get("framework_terms", [])
    miss = _missing(text, fw)
    add("S3", "diagnostic framework codified (the craft's analytical core)", "hard",
        bool(fw) and not miss,
        ("all present" if fw else "no framework_terms declared in manifest.craft")
        if not miss else f"MISSING {miss}")

    hits = _hits(text, craft.get("source_markers", []))
    add("S4", "source grounding declared (skill points at its authority)", "hard",
        bool(hits), f"grounds via {hits}" if hits else "NO reference to the authoritative source")

    hits = _hits(text, craft.get("refusal_markers", []))
    add("S5", "refusal codified (declines empty/insufficient input by instruction)", "advisory",
        bool(hits), f"codified via {hits}" if hits
        else "NOT codified — decline behavior is emergent (model default), not instructed by the skill")

    hits = _hits(text, craft.get("example_markers", []))
    add("S6", "worked example present (craft shown, not only told)", "advisory",
        bool(hits), f"present via {hits}" if hits else "no worked example found")

    return checks


def _cart_name(cart):
    return os.path.basename(cart.rstrip("/"))


def emit(cart, as_json=False):
    man = load_manifest(cart)
    text, path, status = load_skill(cart, man)
    if status != "ok":
        note = ("skill_file is EXTERNAL (not vendored) — craft axis NOT-RUN (not gradeable in this checkout)"
                if status == "external" else f"vendored skill_file MISSING at {path} (repo integrity)")
        if as_json:
            print(json.dumps({"cartridge": _cart_name(cart), "status": status, "checks": [], "note": note}))
        else:
            print(f"\n=== CRAFT AXIS (S) · {_cart_name(cart)} ===\n  "
                  f"{'INCOMPLETE' if status == 'missing' else 'NOT-RUN'}: {note}")
        sys.exit(6 if status == "missing" else 0)

    checks = evaluate(text, man)
    hard_fail = [c["id"] for c in checks if c["kind"] == "hard" and not c["pass"]]
    adv_fail = [c["id"] for c in checks if c["kind"] == "advisory" and not c["pass"]]

    if as_json:
        print(json.dumps({
            "cartridge": _cart_name(cart), "skill_file": path, "status": "ok",
            "checks": checks, "hard_fail": hard_fail, "advisory_fail": adv_fail,
            "verdict": "CODIFIED" if not hard_fail else "GAP",
        }, indent=2))
        sys.exit(1 if hard_fail else 0)

    print("\n=== CRAFT AXIS (S) · is the architect's craft codified in the skill file? ===")
    print(f"  skill: {path}\n")
    for c in checks:
        mark = "ok      " if c["pass"] else ("HARD FAIL" if c["kind"] == "hard" else "ADVISORY ")
        print(f"  {mark} {c['id']} {c['name']}")
        print(f"            {c['detail']}")
    print()
    if hard_fail:
        print(f"  VERDICT: GAP — {len(hard_fail)} HARD craft check(s) failed ({','.join(hard_fail)}): "
              "the skill does not codify what it is supposed to apply.")
    else:
        tail = f"  ({len(adv_fail)} advisory gap(s) noted: {','.join(adv_fail)})" if adv_fail else ""
        print("  VERDICT: CODIFIED — all HARD craft checks pass." + tail)
    sys.exit(1 if hard_fail else 0)


def selftest(cart):
    """Negative control: a craft check that never fails is vacuous. Degrade the skill (strip the first
    red-flag name everywhere) and REQUIRE S1 to flip to fail."""
    man = load_manifest(cart)
    text, path, status = load_skill(cart, man)
    if status != "ok":
        print(f"  craft --selftest: skill not vendored ({status}) — cannot run the control")
        sys.exit(1)
    base = evaluate(text, man)
    base_hard_ok = all(c["pass"] for c in base if c["kind"] == "hard")
    term = (man.get("closed_vocab") or [""])[0]
    degraded = re.sub(re.escape(term), "XXXX", text, flags=re.I)
    deg = evaluate(degraded, man)
    s1_caught = not next(c for c in deg if c["id"] == "S1")["pass"]
    print("\n=== CRAFT NEGATIVE CONTROL (is the craft check non-vacuous?) ===")
    print(f"  baseline: HARD checks pass on the real skill        : {base_hard_ok}")
    print(f"  degraded (removed red-flag '{term}') -> S1 fails     : {s1_caught}")
    ok = base_hard_ok and s1_caught
    print("\n  VERDICT: " + ("NON-VACUOUS — the check catches a stripped craft element"
                             if ok else "BROKEN — a degraded skill still passes S1 (vacuous)"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(2)
    if "--selftest" in args:
        selftest(args[0])
    else:
        emit(args[0], as_json="--json" in args)
