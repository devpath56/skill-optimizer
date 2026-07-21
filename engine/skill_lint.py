#!/usr/bin/env python3
"""
skill_lint.py — the FOUNDATION layer. The craft checks (S1-S15) grade what the skill teaches; they
assume the skill is even discoverable and well-formed. This grades that assumption, against the
authoritative skill-authoring guidance (Anthropic Agent Skills: the `description` is the field that
drives discovery; keep SKILL.md lean with progressive disclosure; state limits/guardrails).

Deterministic, generic (no cartridge knowledge beyond optional thresholds), machine-readable --json.

  L1 HARD      frontmatter valid   — a name + description exist and the block parses
  L2 HARD      name format         — lowercase, [a-z0-9-], <= 64 chars
  L3 HARD      description ready    — THIRD-PERSON + has WHEN/trigger language + within word bounds
                                      (this is the discovery field; a vague one means the skill never fires)
  L4 ADVISORY  progressive disclosure — SKILL.md body within the line budget (heavy detail belongs in
                                        referenced files, not the always-loaded body)
  L5 ADVISORY  guardrails stated   — the skill names its limits / when NOT to use it
  L6 ADVISORY  verification loop    — the skill tells the agent how to check its own output

  python3 engine/skill_lint.py cartridges/<name>          # table + exit 0/1/6
  python3 engine/skill_lint.py cartridges/<name> --json
  python3 engine/skill_lint.py cartridges/<name> --selftest  # negative control

Exit: 0 all HARD pass · 1 a HARD check failed · 6 skill_file absent/external.
"""
import json
import os
import re
import sys

FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def _field(fm, name):
    m = re.search(rf"^{name}:\s*(.+)$", fm, re.M)
    return m.group(1).strip() if m else None


def load_skill(cart):
    man = json.load(open(os.path.join(cart, "manifest.json"), encoding="utf-8"))
    sf = man.get("skill_file", "")
    if not sf or sf.startswith(("~", "/")):
        return None, None, "external"
    p = os.path.join(cart, sf)
    if not os.path.exists(p):
        return None, None, "missing"
    return open(p, encoding="utf-8").read(), man, "ok"


def evaluate(text, man):
    lint = (man or {}).get("skill_lint", {})
    max_lines = lint.get("max_body_lines", 500)
    dmin, dmax = lint.get("desc_words_min", 10), lint.get("desc_words_max", 500)
    checks = []

    def add(cid, name, kind, ok, detail):
        checks.append({"id": cid, "name": name, "kind": kind, "pass": bool(ok), "detail": detail})

    fmm = FM.match(text)
    fm = fmm.group(1) if fmm else ""
    body = text[fmm.end():] if fmm else text
    nm = _field(fm, "name")
    desc = _field(fm, "description")

    add("L1", "frontmatter valid (name + description present)", "hard",
        bool(fmm and nm and desc),
        "name + description present" if (fmm and nm and desc)
        else ("no YAML frontmatter block" if not fmm else f"missing {'name' if not nm else 'description'}"))

    add("L2", "name format (lowercase, [a-z0-9-], <= 64)", "hard",
        bool(nm and re.fullmatch(r"[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?", nm)),
        f"'{nm}' ok" if (nm and re.fullmatch(r"[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?", nm))
        else f"name {nm!r} is not lowercase-hyphen <= 64")

    if desc:
        third = not desc.lower().lstrip().startswith(("i ", "you ", "i'm", "we "))
        when = bool(re.search(r"use when|trigger on|when you|use this|invoke when", desc, re.I))
        wc = len(desc.split())
        ok = third and when and dmin <= wc <= dmax
        why = []
        if not third: why.append("not third-person")
        if not when: why.append("no WHEN/trigger language")
        if not (dmin <= wc <= dmax): why.append(f"{wc} words outside [{dmin},{dmax}]")
        add("L3", "description is discovery-ready (third-person + when-to-use + bounded)", "hard",
            ok, "what + when, third-person, well-sized" if ok else "; ".join(why))
    else:
        add("L3", "description is discovery-ready", "hard", False, "no description to grade")

    nlines = len(body.splitlines())
    add("L4", f"progressive disclosure (body <= {max_lines} lines)", "advisory",
        nlines <= max_lines, f"{nlines} body lines" + ("" if nlines <= max_lines else " — move detail to referenced files"))

    add("L5", "guardrails stated (limits / when NOT to use)", "advisory",
        bool(re.search(r"^#+.*(limit|caveat|constraint|do not|don't|avoid|when not|not for)", body, re.I | re.M)),
        "a limits/guardrails section is present" if re.search(r"^#+.*(limit|caveat|constraint|do not|don't|avoid|when not|not for)", body, re.I | re.M)
        else "no limits/guardrails section — a skill should say when NOT to use it and what it won't do")

    add("L6", "verification loop (tells the agent to check its output)", "advisory",
        bool(re.search(r"verify|self-check|double-check|sanity-check|confirm that", body, re.I)),
        "a verification instruction is present" if re.search(r"verify|self-check|double-check|sanity-check|confirm that", body, re.I)
        else "no verification/self-check instruction")

    return checks


def _cart(cart):
    return os.path.basename(cart.rstrip("/"))


def emit(cart, as_json=False):
    text, man, status = load_skill(cart)
    if status != "ok":
        note = ("skill_file external (not vendored) — NOT-RUN" if status == "external"
                else "vendored skill_file missing (repo integrity)")
        if as_json:
            print(json.dumps({"cartridge": _cart(cart), "status": status, "checks": [], "note": note}))
        else:
            print(f"\n=== SKILL LINT (foundation) · {_cart(cart)} ===\n  "
                  f"{'INCOMPLETE' if status == 'missing' else 'NOT-RUN'}: {note}")
        sys.exit(6 if status == "missing" else 0)
    checks = evaluate(text, man)
    hard_fail = [c["id"] for c in checks if c["kind"] == "hard" and not c["pass"]]
    adv_fail = [c["id"] for c in checks if c["kind"] == "advisory" and not c["pass"]]
    if as_json:
        print(json.dumps({"cartridge": _cart(cart), "checks": checks,
                          "hard_fail": hard_fail, "advisory_fail": adv_fail,
                          "verdict": "OK" if not hard_fail else "BLOCK"}, indent=2))
        sys.exit(1 if hard_fail else 0)
    print(f"\n=== SKILL LINT (foundation) · is the skill well-formed + discoverable? ===")
    for c in checks:
        mark = "ok      " if c["pass"] else ("HARD FAIL" if c["kind"] == "hard" else "ADVISORY ")
        print(f"  {mark} {c['id']} {c['name']}\n            {c['detail']}")
    print("\n  VERDICT: " + ("OK — foundation is sound." + (f"  ({len(adv_fail)} advisory: {','.join(adv_fail)})" if adv_fail else "")
                             if not hard_fail else f"BLOCK — HARD {','.join(hard_fail)}"))
    sys.exit(1 if hard_fail else 0)


def selftest(cart):
    text, man, status = load_skill(cart)
    if status != "ok":
        print(f"  skill_lint --selftest: skill not vendored ({status})")
        sys.exit(1)
    base_ok = all(c["pass"] for c in evaluate(text, man) if c["kind"] == "hard")
    # degrade: blank the description -> L3 must fail
    degraded = re.sub(r"^description:.*$", "description:", text, count=1, flags=re.M)
    l3 = next(c for c in evaluate(degraded, man) if c["id"] == "L3")
    caught = not l3["pass"]
    print("\n=== SKILL LINT negative control ===")
    print(f"  baseline HARD checks pass         : {base_ok}")
    print(f"  blanked description -> L3 fails    : {caught}")
    ok = base_ok and caught
    print("\n  VERDICT: " + ("NON-VACUOUS" if ok else "BROKEN"))
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
