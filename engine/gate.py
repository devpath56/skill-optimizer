#!/usr/bin/env python3
"""
Pre-ship gate — the point of the whole tool: would this skill SHIP to the team?

Runs preflight + score.py, aggregates their verdicts, and answers SHIP / BLOCK with an
exit code, so it drops into CI or a pre-commit hook. A "fresh-clone smoke test" is just
the degenerate case of this (the gate runs in any environment and fails loud).

  python3 engine/gate.py cartridges/<name>              # SHIP (0) / BLOCK (1) / INCOMPLETE (6)
  python3 engine/gate.py --selftest cartridges/<name>   # NEGATIVE CONTROL: prove the gate BLOCKS
                                                          # a known-bad skill and SHIPS a good one

Why the negative control matters: a gate that only ever says SHIP is vacuous (CF-065/CF-067).
--selftest degrades the flaw-laden output (recall drops below bar) and REQUIRES the gate to
flip to BLOCK; if it still ships, the gate is broken, not the skill.
"""
import os, sys, subprocess, shutil, tempfile, json

ENG = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
SHIP, BLOCK, INCOMPLETE = 0, 1, 6

def run(script, cart, *extra):
    r = subprocess.run([PY, os.path.join(ENG, script), cart, *extra], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr

def gate(cart):
    """Return (decision, exit_code, reasons[])."""
    reasons = []
    pf_rc, pf_out = run("preflight.py", cart)
    if pf_rc == INCOMPLETE:
        return "BLOCK", INCOMPLETE, ["preflight: committed-required file missing (repo integrity)"]
    sc_rc, sc = run("score.py", cart)
    if sc_rc == INCOMPLETE:
        return "BLOCK", INCOMPLETE, ["score: INCOMPLETE — a committed golden output is missing"]
    if "EFFICACY (deterministic part): RED" in sc:
        reasons.append("efficacy RED (structure/recall/restraint/refusal below bar)")
    for line in sc.splitlines():
        if ("F2" in line or "F3  lightweight" in line) and "FAIL" in line:
            reasons.append("committed fidelity FAIL:" + line.strip())
    if any("full book" in l and "NOT-RUN" in l for l in sc.splitlines()):
        reasons.append("NOTE: full-book F3 NOT-RUN (book absent) — shipping on committed checks only")
    # craft axis (S): is the architect's craft codified in the skill file itself?
    cr_rc, cr_out = run("craft.py", cart, "--json")
    if cr_rc == INCOMPLETE:
        return "BLOCK", INCOMPLETE, ["craft: vendored skill_file missing (repo integrity)"]
    try:
        craft = json.loads(cr_out)
    except Exception:
        craft = None
    if craft and craft.get("status") == "ok":
        if craft.get("hard_fail"):
            reasons.append("craft GAP (skill file does not codify what it applies): HARD "
                           + ",".join(craft["hard_fail"]))
        for cid in craft.get("advisory_fail", []):
            reasons.append(f"NOTE: craft advisory {cid} not codified in the skill")
    elif craft and craft.get("status") == "external":
        reasons.append("NOTE: craft axis NOT-RUN (skill_file external, not vendored)")
    hard = [r for r in reasons if not r.startswith("NOTE:")]
    return ("BLOCK", BLOCK, reasons) if hard else ("SHIP", SHIP, reasons)

def emit(cart):
    decision, code, reasons = gate(cart)
    print(f"\n=== PRE-SHIP GATE · {cart} ===")
    for r in reasons:
        print(f"  - {r}")
    print(f"\n  DECISION: {decision}" + ("" if decision == "SHIP" else "  (do not ship)"))
    sys.exit(code)

def selftest(cart):
    """Negative control: the gate must BLOCK a degraded skill and SHIP the real one."""
    good_dec, good_code, _ = gate(cart)
    # Build a known-BAD copy: overwrite the flaw-laden output with the degraded variant.
    import json
    man = json.load(open(os.path.join(cart, "manifest.json")))
    flaw = next((i for i in man["golden_set"] if i.get("state") == "flaw-laden" and i.get("output")), None)
    degraded = os.path.join(cart, "golden", "_probe_variantB-01.md")
    ok = True
    if not flaw or not os.path.exists(degraded):
        print("  selftest: cannot build the bad case (no flaw-laden output or degraded fixture)"); ok = False
        bad_dec, bad_code = "N/A", None
    else:
        tmp = tempfile.mkdtemp(prefix="gate-neg-")
        dst = os.path.join(tmp, "cart")
        shutil.copytree(cart, dst)
        shutil.copyfile(degraded, os.path.join(dst, "golden", flaw["output"]))  # degrade recall 3/3 -> 1/3
        bad_dec, bad_code, _ = gate(dst)
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n=== GATE NEGATIVE CONTROL (is the gate vacuous?) ===")
    print(f"  GOOD cartridge -> {good_dec:<6}  (want SHIP)")
    print(f"  BAD  cartridge -> {bad_dec:<6}  (want BLOCK — recall degraded below bar)")
    good_ok = good_dec == "SHIP"
    bad_ok = bad_dec == "BLOCK"
    verdict = good_ok and bad_ok
    print(f"\n  gate distinguishes good from bad: {'YES — non-vacuous' if verdict else 'NO — GATE IS BROKEN'}")
    if not good_ok: print("    x the real skill did NOT ship (gate too strict, or skill regressed)")
    if not bad_ok:  print("    x a degraded skill would SHIP (gate is vacuous — the failure this control exists to catch)")
    sys.exit(0 if verdict else 1)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    if not args or "-h" in args or "--help" in args:
        print(__doc__); sys.exit(2)
    if args[0] == "--selftest":
        if len(args) < 2: print("usage: gate.py --selftest cartridges/<name>"); sys.exit(2)
        selftest(args[1])
    else:
        emit(args[0])
