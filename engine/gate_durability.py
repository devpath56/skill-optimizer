#!/usr/bin/env python3
"""
Self-durability control for the gate (CF-067 class): prove `gate.py --selftest` is NOT vacuous.

`gate.py --selftest` proves the gate distinguishes a good skill from a degraded one. But a selftest
that would pass no matter what the gate does is theatre — the census-incident class, where a control
is green for the wrong reason (an early exit, a swallowed error, a branch that stopped being
load-bearing). This harness proves the selftest is load-bearing by prove-durable: it MUTATES gate.py's
decision logic to a known-broken form and REQUIRES --selftest to flip to failure. If a neutered gate
still passes its own selftest, the selftest is the thing that's broken.

Mechanism mirrors Trident's prove-durable: mutate the real file in place, run the real selftest,
then RESTORE it (immediately after each run, plus a try/finally backstop, plus a final byte-for-byte
hash check). A mutation whose target text is NOT found is a HARD FAIL — a stale harness that silently
matches nothing is exactly the no-op this guards against — never a skipped-and-green.

  python3 engine/gate_durability.py cartridges/<name>   # 0 = selftest is durable · 1 = vacuous/broken
"""
import hashlib
import os
import subprocess
import sys

ENG = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(ENG, "gate.py")
PY = sys.executable

# Each mutation is (label, find, replace). `find` MUST be present (else stale-harness HARD FAIL).
# Applying it must make gate.py's --selftest FAIL — a degraded skill would ship, or a good one would
# not — so each mutation proves a specific piece of the gate's decision logic is load-bearing.
MUTATIONS = [
    ("always-SHIP (neuter the BLOCK branch)",
     'return ("BLOCK", BLOCK, reasons) if hard else ("SHIP", SHIP, reasons)',
     'return ("SHIP", SHIP, reasons)  # MUTANT'),
    ("drop the efficacy-RED reason (make the recall check non-load-bearing)",
     'reasons.append("efficacy RED (structure/recall/restraint/refusal below bar)")',
     'pass  # MUTANT: efficacy RED no longer blocks'),
]


def run_selftest(cart):
    r = subprocess.run([PY, GATE, "--selftest", cart], capture_output=True, text=True)
    return r.returncode


def main(cart):
    original = open(GATE, "rb").read()
    orig_hash = hashlib.sha256(original).hexdigest()
    src = original.decode()
    results = []  # (name, ok, detail)
    try:
        # 0) baseline: the real gate must PASS its own --selftest, else nothing below has meaning.
        base = run_selftest(cart)
        results.append(("baseline: the real gate passes --selftest", base == 0, f"exit {base}, want 0"))

        # 1) each mutation must be CAUGHT — the selftest must flip to failure.
        for label, find, repl in MUTATIONS:
            if find not in src:
                results.append((f"mutation '{label}' applies",
                                False, "STALE HARNESS: target text not found in gate.py"))
                continue
            open(GATE, "w").write(src.replace(find, repl, 1))
            rc = run_selftest(cart)
            open(GATE, "wb").write(original)  # restore immediately after the run
            results.append((f"mutation '{label}' is CAUGHT by --selftest",
                            rc != 0, f"mutant --selftest exit {rc}, want !=0"))
    finally:
        open(GATE, "wb").write(original)  # belt-and-suspenders restore even on exception

    restored = hashlib.sha256(open(GATE, "rb").read()).hexdigest() == orig_hash
    results.append(("gate.py restored byte-for-byte after mutation", restored, ""))

    print("\n=== GATE SELF-DURABILITY (is --selftest load-bearing?) ===")
    failed = 0
    for name, ok, detail in results:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f"  [{detail}]" if detail else ""))
        failed += 0 if ok else 1
    verdict = failed == 0
    print("\n  VERDICT: " + ("DURABLE — a neutered gate cannot silently pass its own selftest"
                             if verdict else
                             "BROKEN — --selftest does not catch a neutered gate (it is vacuous)"))
    sys.exit(0 if verdict else 1)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1])
