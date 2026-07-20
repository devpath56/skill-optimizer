#!/usr/bin/env python3
"""
Preflight readiness check — run this FIRST in a fresh clone / new session:

    python3 engine/preflight.py cartridges/<name>

It answers one question honestly: in THIS checkout, what can run clean, and what
is blocked? It classifies every requirement into two kinds and treats them differently
(the repo's whole ethos, CF-065: distinguish holds / fails / never-evaluated):

  COMMITTED-REQUIRED  — ships with the repo. If MISSING => a hard repo-integrity error
                        (exit non-zero). A fresh clone must have every one of these.
  EXTERNAL-LICENSED   — intentionally NOT committed (copyright), e.g. the book text. If
                        absent it is reported LOUD as "full-book F3 unavailable until you
                        supply your own copy" — but it is NOT an error; the repo is still
                        usable for everything that doesn't need the book.

Exit: 0 = ready (all committed-required present; book may be absent -> loud, still ready)
      6 = INCOMPLETE (a committed-required file is missing -> hard error)
"""
import json, os, sys

EXIT_OK = 0
EXIT_INCOMPLETE = 6


def load_json(p):
    with open(p) as f:
        return json.load(f)


def check(path):
    return "PRESENT" if os.path.exists(path) else "MISSING"


def main(cart):
    man_path = os.path.join(cart, "manifest.json")
    if not os.path.exists(man_path):
        print(f"x COMMITTED-REQUIRED MISSING: {man_path}")
        print("\nREADINESS: INCOMPLETE — no manifest; nothing can run.")
        return EXIT_INCOMPLETE
    man = load_json(man_path)
    gdir = os.path.join(cart, "golden")
    fid = man.get("fidelity", {})

    # ---- build the requirement lists ----
    committed = [("manifest", man_path)]
    for name in ("BAR.md",):
        committed.append((name, os.path.join(cart, name)))
    # the skill-under-test itself: required ONLY when vendored (a cartridge-relative path). An external
    # ~/absolute path is a not-committed subject (back-compat) and is not enforced here.
    sf = man.get("skill_file", "")
    if sf and not sf.startswith(("~", "/")):
        committed.append(("skill-under-test (vendored)", os.path.join(cart, sf)))
    if os.path.exists(os.path.join(cart, "candidates.json")):
        committed.append(("candidates.json", os.path.join(cart, "candidates.json")))
    for item in man.get("golden_set", []):
        committed.append((f"golden doc [{item['state']}]", os.path.join(gdir, item["doc"])))
        if item.get("key"):
            committed.append((f"answer key [{item['state']}]", os.path.join(gdir, item["key"])))
        if item.get("output"):
            committed.append((f"golden output [{item['state']}]", os.path.join(gdir, item["output"])))
    if fid.get("fixtures"):
        committed.append(("fidelity fixtures", os.path.join(cart, fid["fixtures"])))
    if fid.get("distillation"):
        committed.append(("distillation (hop-1)", os.path.join(cart, fid["distillation"])))
    # engine (generic) — required to run anything
    engine_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    for f in ("score.py", "rerank.py"):
        committed.append((f"engine/{f}", os.path.join(engine_dir, f)))

    external = []
    if fid.get("book_ground_truth"):
        external.append(("book ground truth (full-book F3)", os.path.join(cart, fid["book_ground_truth"])))

    # ---- report ----
    print("=" * 74)
    print(f"PREFLIGHT · cartridge: {man.get('skill', cart)}")
    print("=" * 74)

    print("\nCOMMITTED-REQUIRED (must ship with the repo; MISSING = hard error):")
    missing_committed = []
    for label, path in committed:
        st = check(path)
        if st == "MISSING":
            missing_committed.append((label, path))
        mark = "ok " if st == "PRESENT" else "XX "
        print(f"  {mark}[{st:<7}] {label:<28} {path}")

    print("\nEXTERNAL-LICENSED (intentionally NOT committed; absent = LOUD, not an error):")
    book_absent = []
    for label, path in external:
        st = check(path)
        if st == "MISSING":
            book_absent.append((label, path))
        mark = "ok " if st == "PRESENT" else "-- "
        print(f"  {mark}[{st:<7}] {label:<28} {path}")

    # ---- readiness summary ----
    print("\n" + "-" * 74)
    print("READINESS SUMMARY")
    print("-" * 74)
    if missing_committed:
        print("  STATUS: INCOMPLETE — committed-required file(s) missing (hard error):")
        for label, path in missing_committed:
            print(f"    x {label}: {path}")
        print("  Fix: this should never happen in a clean clone; the repo is broken/incomplete.")
        print("=" * 74)
        return EXIT_INCOMPLETE

    print("  RUNS CLEAN in this checkout (no book needed):")
    print("    - engine/score.py  : efficacy axes (E1/E2/E4/E-ref) on committed golden outputs")
    print("    - engine/score.py  : fidelity F2 (vocab) + F3-lightweight (confirmed quotes in distillation)")
    print("    - engine/rerank.py : STAGE 1 proxy + STAGE 2 consumer (fidelity-blind; no book)")
    print("    - validation/calibrate.py : E5 judge calibration (deterministic, committed jsonl)")

    if book_absent:
        print("\n  LOUD — needs the book (NOT an error, expected external dependency):")
        for label, path in book_absent:
            print(f"    ! {label}: full-book F3 UNAVAILABLE until you supply your own licensed")
            print(f"      copy at {path} (see README 'Fresh clone / new session').")
        print("    Until then, full-book F3 is NOT-RUN (loud) — never reported as a PASS.")
        print("\n  STATUS: READY (efficacy + lightweight fidelity run clean; full-book F3 gated).")
    else:
        print("\n  STATUS: READY (book present — full-book F3 can also run live).")
    print("=" * 74)
    return EXIT_OK


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 engine/preflight.py cartridges/<name>"); sys.exit(2)
    sys.exit(main(sys.argv[1]))
