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

Grader principle (Hamel / llm-evals): every criterion is an ADVERSARIAL, DETERMINISTIC, BINARY
pass/fail. Default to FAIL and make the skill PROVE the pass — no Likert, no scores, no fuzzy judge
where code can decide. A green tick is earned, never assumed.

Input contract: the skill-builder grades a skill file AGAINST an authoritative resource. Both are
first-class inputs (manifest.skill_file + manifest.authoritative_source / manifest.craft.grounding).
Checks that need the resource run when it is present and are NOT-RUN (loud) when it is absent — never
a bare pass.

Checks (HARD = ship-blocking; ADVISORY = reported, not blocking):
  S1 HARD      vocab codified        — every closed_vocab red-flag name appears in the skill
  S2 HARD      contract codified     — every expected_section is declared in the skill
  S3 HARD      framework codified    — the craft's analytical core (manifest.craft.framework_terms)
  S4 HARD      source grounding      — the skill points at its authoritative source (any source_marker)
  S5 ADVISORY  refusal codified      — decline-on-empty is INSTRUCTED, not left to model default
  S6 ADVISORY  worked example        — the craft is shown, not only told
  S7 HARD      grounding travels     — promised anecdotes are DELIVERABLE: the bundle carries reachable
                                       grounding (else a downstream teaching agent must fabricate)
  S8 HARD*     grounding is real     — the bundled grounding's anecdotes are VERBATIM in the authoritative
                                       resource and none are fabricated (*NOT-RUN + loud when the book is absent)

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


def evaluate(text, man, cart="."):
    """Deterministic craft checks over the skill text + the authoritative resource. Returns check dicts."""
    craft = man.get("craft", {})
    checks = []

    def add(cid, name, kind, ok, detail, notrun=False):
        checks.append({"id": cid, "name": name, "kind": kind, "pass": bool(ok),
                       "detail": detail, "notrun": bool(notrun)})

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

    # S7/S8 grounding — adversarial: a skill that PROMISES book anecdotes but ships no reachable,
    # book-verified grounding forces a downstream teaching agent to fabricate. Graded against the
    # authoritative resource (the book you supplied); NOT-RUN + loud when that resource is absent.
    g = craft.get("grounding", {})
    if any(p.lower() in text.lower() for p in g.get("promises", [])):
        bundle_rel = g.get("bundle", "")
        bundle_path = os.path.join(cart, bundle_rel) if bundle_rel else ""
        reachable = bool(bundle_rel) and os.path.exists(bundle_path)
        add("S7", "grounding travels with the skill (promised anecdotes are deliverable)", "hard",
            reachable,
            f"bundle carries reachable grounding: {bundle_rel}" if reachable else
            f"skill PROMISES book anecdotes but the bundle carries NO reachable grounding "
            f"({bundle_rel or 'none declared'}) — a downstream agent must fabricate them")

        book_rel = g.get("authoritative_resource", "")
        book_path = os.path.join(cart, book_rel) if book_rel else ""
        probes = g.get("anecdote_probes", [])
        fabricated = g.get("fabricated_probes", [])
        if reachable and book_rel and os.path.exists(book_path):
            gt = open(bundle_path, encoding="utf-8", errors="ignore").read().lower()
            bk = open(book_path, encoding="utf-8", errors="ignore").read().lower()
            ungrounded = [p for p in probes if p.lower() not in gt or p.lower() not in bk]
            invented = [p for p in fabricated if p.lower() in gt]
            add("S8", "grounding is real (anecdotes verbatim in the authoritative resource, none fabricated)",
                "hard", not ungrounded and not invented,
                "all probe anecdotes are book-present and no fabrications leaked"
                if not ungrounded and not invented
                else f"ungrounded/missing {ungrounded} · fabricated present {invented}")
        else:
            why = ("authoritative resource absent (book gitignored on this checkout)"
                   if reachable else "no reachable grounding to verify")
            add("S8", "grounding is real (vs the authoritative resource)", "hard", True,
                f"NOT-RUN — {why}; verified only where the book is present, never a bare pass", notrun=True)

    # S9/S10 memory hook — a memorable, GROUNDED mnemonic so a teaching agent can make the key
    # principles STICK (the EPIC-style recall aid). Adversarial: a fabricated acronym whose letters
    # are not real book principles must FAIL; a real one the skill never teaches must FAIL too.
    mn = craft.get("mnemonic", {})
    if mn.get("acronym"):
        acronym = mn["acronym"]
        exp = mn.get("expansion", [])
        letters = "".join(e.get("letter", "") for e in exp)
        well_formed = letters.upper() == acronym.upper() and acronym.isalpha() and 3 <= len(acronym) <= 7
        # S9 (book-free): well-formed AND actually TAUGHT. "Taught" requires the acronym as a standalone
        # ALL-CAPS token (the mnemonic), never the incidental lowercase word ('deep module' must NOT
        # count) — the substring-match false-positive this axis keeps having to guard against.
        taught_blob = text
        gpath = os.path.join(cart, (craft.get("grounding") or {}).get("bundle", ""))
        if (craft.get("grounding") or {}).get("bundle") and os.path.exists(gpath):
            taught_blob += "\n" + open(gpath, encoding="utf-8", errors="ignore").read()
        taught = well_formed and re.search(rf"\b{re.escape(acronym)}\b", taught_blob) is not None
        add("S9", "recall mnemonic is taught (a memorable acronym the agent can teach for recall)", "advisory",
            taught,
            f"'{acronym}' is taught in the skill/grounding" if taught else
            (f"mnemonic '{acronym}' is declared but NOT taught — a teaching agent can't deliver it"
             if well_formed else f"mnemonic '{acronym}' is malformed (letters {letters!r})"))
        # S10 (book-gated, HARD): every letter maps to a REAL book principle — no fabricated mnemonic
        book_rel = (craft.get("grounding") or {}).get("authoritative_resource", "")
        book_path = os.path.join(cart, book_rel) if book_rel else ""
        if book_rel and os.path.exists(book_path):
            bk = open(book_path, encoding="utf-8", errors="ignore").read().lower()
            ungrounded = [e.get("letter") for e in exp if e.get("ground_probe", "").lower() not in bk]
            add("S10", "recall mnemonic is grounded (each letter is a real book principle, not invented)",
                "hard", not ungrounded,
                "every letter maps to a book-grounded principle" if not ungrounded
                else f"UNGROUNDED letters {ungrounded} — fabricated mnemonic")
        else:
            add("S10", "recall mnemonic is grounded (vs the authoritative resource)", "hard", True,
                "NOT-RUN — authoritative resource absent; the mnemonic's grounding is verified only "
                "where the book is present, never a bare pass", notrun=True)

    # S11/S12 authorial voice — can a teaching agent speak in the EXPERT'S voice? Does the bundle carry
    # the author's signature/quotable lines? Adversarial: a "quote" not verbatim in the source is a
    # fabricated/misattributed voice and must FAIL (the failure that started this whole project).
    voice = craft.get("voice", {})
    quotes = voice.get("signature_quotes", [])
    if quotes:
        min_q = voice.get("min_quotes", 3)
        # skill-FILE level (the ask): the skill's OWN persona must surface the author's signature lines,
        # not merely have them reachable in the grounding bundle.
        blob = text.lower()
        carried = [q for q in quotes if q.lower() in blob]
        add("S11", f"authorial voice is taught (the skill surfaces >= {min_q} signature quotes)", "advisory",
            len(carried) >= min_q,
            f"{len(carried)}/{len(quotes)} signature quotes in the skill (>= {min_q} needed)" if len(carried) >= min_q
            else f"only {len(carried)}/{len(quotes)} signature quotes in the skill — the persona can't speak "
                 f"in the author's voice (needs >= {min_q}; the rest sit in the grounding, not the persona)")
        book_rel = (craft.get("grounding") or {}).get("authoritative_resource", "")
        book_path = os.path.join(cart, book_rel) if book_rel else ""
        if book_rel and os.path.exists(book_path):
            bk = open(book_path, encoding="utf-8", errors="ignore").read().lower()
            fabricated = [q for q in quotes if q.lower() not in bk]
            add("S12", "authorial voice is real (every signature quote is verbatim in the source)", "hard",
                not fabricated,
                "every signature quote is verbatim in the book" if not fabricated
                else f"NOT verbatim in the source (fabricated/misattributed voice): {fabricated}")
        else:
            add("S12", "authorial voice is real (vs the authoritative resource)", "hard", True,
                "NOT-RUN — authoritative resource absent; signature quotes verified verbatim only where "
                "the book is present, never a bare pass", notrun=True)

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

    checks = evaluate(text, man, cart)
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
        if c.get("notrun"):
            mark = "NOT-RUN "
        elif c["pass"]:
            mark = "ok      "
        else:
            mark = "HARD FAIL" if c["kind"] == "hard" else "ADVISORY "
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
    base = evaluate(text, man, cart)
    base_hard_ok = all(c["pass"] for c in base if c["kind"] == "hard")
    term = (man.get("closed_vocab") or [""])[0]
    degraded = re.sub(re.escape(term), "XXXX", text, flags=re.I)
    deg = evaluate(degraded, man, cart)
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
