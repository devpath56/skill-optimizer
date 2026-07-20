#!/usr/bin/env python3
"""
Co-mutation guard — the skill-builder governance check (the answer to "separate version control for
the skill vs its derived checks?"). Verdict: one repo, but the ACCEPTANCE BAR is an independent
authority over the skill — it must not move silently in the same change that edits the skill it grades
(else an author can quietly relax the goalposts while regressing the player — the co-mutation failure).

This guard FLAGS any change that touches BOTH a skill-side file AND a bar-side file without an explicit
`BAR-CHANGE-RATIFIED:` marker in a commit message. Same mechanism as the truthfulness gate's
silent-edit detector, applied to the skill<->bar coupling.

  skill-side : the vendored skill bundle (manifest.skill_file's directory, e.g. skill/)
  bar-side   : the acceptance criteria — manifest.json, BAR.md, validation/, truthfulness/

  python3 engine/comutation_guard.py cartridges/<name>            # check origin/main...HEAD (NOT-RUN safe)
  python3 engine/comutation_guard.py cartridges/<name> --range A..B
  python3 engine/comutation_guard.py cartridges/<name> --selftest  # negative control (logic is non-vacuous)

Exit: 0 clean / NOT-RUN · 1 co-mutation without ratification.
"""
import json
import os
import subprocess
import sys

RATIFY_MARKER = "BAR-CHANGE-RATIFIED"
BAR_FILES = ("manifest.json", "BAR.md")
BAR_DIRS = ("validation/", "truthfulness/")


def classify(path, cart_rel, skill_dir_rel):
    """skill | bar | None (engine/CI/docs are neither — the generic grader is a separate concern)."""
    if not path.startswith(cart_rel + "/"):
        return None
    rel = path[len(cart_rel) + 1:]
    if skill_dir_rel and rel.startswith(skill_dir_rel):
        return "skill"
    if rel in BAR_FILES or rel.startswith(BAR_DIRS):
        return "bar"
    return None


def comutation(changed, commit_msgs, cart_rel, skill_dir_rel):
    """Pure/testable. Return a list of violations (empty = clean)."""
    skill_hits = [p for p in changed if classify(p, cart_rel, skill_dir_rel) == "skill"]
    bar_hits = [p for p in changed if classify(p, cart_rel, skill_dir_rel) == "bar"]
    if skill_hits and bar_hits and RATIFY_MARKER not in (commit_msgs or ""):
        return [f"co-mutation: this change edits the SKILL {skill_hits} AND its BAR {bar_hits} together "
                f"with no '{RATIFY_MARKER}:' marker. The acceptance bar must not move silently in the same "
                "change that edits the skill it grades. Split the change, or add "
                f"'{RATIFY_MARKER}: <why the contract genuinely changed>' to the commit message."]
    return []


def _git(args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True).stdout
    except Exception:
        return ""


def main(cart, rng=None):
    man = json.load(open(os.path.join(cart, "manifest.json"), encoding="utf-8"))
    cart_rel = os.path.relpath(cart).replace(os.sep, "/").rstrip("/")
    sf = man.get("skill_file", "")
    skill_dir_rel = (os.path.dirname(sf) + "/") if sf and not sf.startswith(("~", "/")) else ""
    rng = rng or "origin/main...HEAD"
    changed = [l for l in _git(["diff", "--name-only", rng]).splitlines() if l.strip()]
    msgs = _git(["log", "--format=%B", rng.replace("...", "..")])
    if not changed:
        print(f"=== CO-MUTATION GUARD · {cart_rel} ===\n  NOT-RUN — empty/undeterminable range ({rng}); "
              "runs as a PR/pre-commit check where a base ref is available.")
        return 0
    violations = comutation(changed, msgs, cart_rel, skill_dir_rel)
    print(f"=== CO-MUTATION GUARD · {cart_rel} (range {rng}) ===")
    if not violations:
        print("  ok — no un-ratified skill+bar co-mutation")
        return 0
    for v in violations:
        print(f"  FAIL {v}")
    return 1


def selftest(cart):
    man = json.load(open(os.path.join(cart, "manifest.json"), encoding="utf-8"))
    cr = os.path.relpath(cart).replace(os.sep, "/").rstrip("/")
    sd = (os.path.dirname(man.get("skill_file", "")) + "/")
    S, B = cr + "/skill/SKILL.md", cr + "/manifest.json"
    cases = [
        ("skill+bar together, NOT ratified -> FLAG", [S, B], "improve skill and tweak thresholds",
         True),
        ("skill+bar together, RATIFIED -> pass", [S, B], f"contract change\n\n{RATIFY_MARKER}: added a section",
         False),
        ("skill only -> pass", [S], "improve the skill wording", False),
        ("bar only -> pass", [B], "tighten the bar", False),
    ]
    print("=== CO-MUTATION GUARD · negative control ===")
    failed = 0
    for name, changed, msg, want_flag in cases:
        flagged = bool(comutation(changed, msg, cr, sd))
        ok = flagged == want_flag
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        failed += 0 if ok else 1
    print(f"\n  VERDICT: {'NON-VACUOUS' if not failed else 'BROKEN'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(2)
    if "--selftest" in args:
        sys.exit(selftest(args[0]))
    rng = args[args.index("--range") + 1] if "--range" in args else None
    sys.exit(main(args[0], rng))
