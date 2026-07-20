#!/usr/bin/env python3
"""
Generic skill-optimizer scorer. Skill-agnostic: all specifics come from a cartridge.

Usage:  python3 engine/score.py cartridges/<name>

Reads <cartridge>/manifest.json, scores each captured skill output against its
by-construction key using DETERMINISTIC checks only (Hamel: deterministic before judge).
Emits a per-doc table + axis rollups + an efficacy SHIP/RED verdict.

Fidelity checks (F*) and judge checks (E5, E3-validity) are reported as PENDING here on
purpose: they need the authoritative source text and a validated judge, not grep. The
engine states what it did NOT check rather than pretending green.
"""
import json, os, re, sys

# exit codes: 0 = ran (efficacy computed; book-absent fidelity NOT-RUN is NOT an error).
#             6 = INCOMPLETE — a committed, manifest-referenced file is missing (repo-integrity).
EXIT_OK = 0
EXIT_INCOMPLETE = 6

def load(p):
    with open(p) as f:
        return f.read()

def load_json(p):
    with open(p) as f:
        return json.load(f)

NEG = re.compile(r"\b(no|not|without|isn'?t|aren'?t|never|opposite)\b", re.I)

def sections_present(text, expected):
    return [s for s in expected if re.search(re.escape(s), text, re.I)]

def red_flags_section(text, expected):
    """Scope flag detection to the 'Red Flags Found' section so mentions in other
    sections (or the diagnosis) don't count. Falls back to whole text if not found."""
    start = re.search(r"Red Flags? (Found|Identified)", text, re.I)
    if not start:
        return text
    rest = text[start.end():]
    # cut at the next known section header
    ends = [m.start() for h in expected[2:] for m in [re.search(re.escape(h), rest, re.I)] if m]
    return rest[:min(ends)] if ends else rest

def term_asserted(section, terms):
    """A flag counts as RAISED only if it appears as an assertion, not a negation.
    Negation-aware: 'No information leakage' / 'Not a shallow module' do NOT count."""
    pat = "(" + "|".join(t.replace(" ", r"[- ]?") for t in terms) + ")"
    for line in section.splitlines():
        for m in re.finditer(pat, line, re.I):
            window = line[max(0, m.start() - 45):m.start()]      # look just before the term
            lead = re.sub(r"^[\s\-*#>_]+", "", line)[:6]          # bullet lead, markdown stripped
            if NEG.search(window) or NEG.match(lead):
                continue
            return True
    return False

def vocab_raised(section, vocab):
    return [v for v in vocab if term_asserted(section, [v])]

# ---------------------------------------------------------------------------
# Repo-integrity: which committed, manifest-referenced files must be present.
# A missing one is NOT-EVALUATED / INCOMPLETE (loud, exit 6) — never folded into FAIL.
# The book (authoritative source text) is EXCLUDED here: it is an expected EXTERNAL
# dependency, handled separately by the fidelity section (absent => NOT-RUN, not error).
# ---------------------------------------------------------------------------
def required_committed_files(cart, man):
    req = []
    gdir = os.path.join(cart, "golden")
    for item in man.get("golden_set", []):
        req.append(("golden doc", os.path.join(gdir, item["doc"])))
        if item.get("key"):
            req.append(("answer key", os.path.join(gdir, item["key"])))
        if item.get("output"):
            req.append(("golden output", os.path.join(gdir, item["output"])))
    fid = man.get("fidelity", {})
    if fid.get("fixtures"):
        req.append(("fidelity fixtures", os.path.join(cart, fid["fixtures"])))
    if fid.get("distillation"):
        req.append(("distillation", os.path.join(cart, fid["distillation"])))
    return [(kind, p) for kind, p in req if not os.path.exists(p)]

def normalize(s):
    return re.sub(r"\s+", " ", s).strip().lower()

def phrase_present(phrase, text):
    """Tolerant phrase match for NAMED CONCEPTS (not quotes): hyphen/space interchangeable
    and a trailing plural 's' on the last word is optional. This is the documented
    'Vague Name' (singular in the book) vs 'vague names' (plural in the vocab) case —
    RUN-01 logs it as NOT a defect, so F2 must not false-fail on it."""
    words = re.split(r"[-\s]+", phrase.strip())
    esc = [re.escape(w) for w in words]
    last = words[-1]
    esc[-1] = (re.escape(last[:-1]) if last.lower().endswith("s") else re.escape(last)) + "s?"
    return re.search(r"[-\s]+".join(esc), text, re.I) is not None

def fidelity_section(cart, man):
    """Report the fidelity axis with PRESENCE CHECKED ground truth.

    Returns (lines, integrity_ok). NEVER prints a bare fidelity PASS when the
    ground truth (the book) is absent: full-book F3 then reads RECORDED / NOT-verifiable.
    Lightweight F2 (vocab) and F3 (confirmed quotes in the committed distillation) DO run
    clean without the book, against committed files only."""
    lines = []
    fid = man.get("fidelity")
    if not fid:
        rec = man.get("fidelity_status")
        lines.append("  FIDELITY: no `fidelity` block in manifest — cannot presence-check.")
        if rec:
            lines.append(f"    RECORDED (not live): F2 {rec.get('F2_vocab')} · F3 {rec.get('F3_grounded')}")
        return lines, True

    fixtures_path = os.path.join(cart, fid["fixtures"])
    dist_path = os.path.join(cart, fid["distillation"])
    book_path = os.path.join(cart, fid["book_ground_truth"])

    if not os.path.exists(fixtures_path) or not os.path.exists(dist_path):
        lines.append("  FIDELITY: INCOMPLETE — committed fixtures or distillation missing "
                     "(repo-integrity error, not a fidelity FAIL).")
        return lines, False

    fx = load_json(fixtures_path)
    dist = normalize(load(dist_path))

    # ---- F2 (deterministic, committed): named red flags present in the distillation ----
    flags = fx["named_red_flags"]
    f2_present = [f for f in flags if phrase_present(f, dist)]
    f2_pass = len(f2_present) == len(flags)
    lines.append(f"  F2  vocab (committed, live) : {'PASS' if f2_pass else 'FAIL'} "
                 f"{len(f2_present)}/{len(flags)} named red flags in distillation")

    # ---- F3 lightweight (deterministic, committed): confirmed quotes in the distillation ----
    cq = fx["confirmed_quotes"]
    cq_in_dist = [q for q in cq if normalize(q["quote"]) in dist]
    f3l_pass = len(cq_in_dist) == len(cq)
    lines.append(f"  F3  lightweight (committed, live): {'PASS' if f3l_pass else 'FAIL'} "
                 f"{len(cq_in_dist)}/{len(cq)} confirmed quotes present in distillation")
    # fair-use guard: each committed quote is short (< 15 words)
    over = [q["quote"] for q in cq if len(q["quote"].split()) >= 15]
    if over:
        lines.append(f"    WARN fair-use: {len(over)} committed quote(s) >= 15 words: {over}")

    # ---- F3 full (gated on the book being present) ----
    if not os.path.exists(book_path):
        rec = man.get("fidelity_status", {})
        lines.append("  F3  full book (ground truth) : NOT-RUN — book ABSENT in this clone "
                     f"({fid['book_ground_truth']}).")
        lines.append("      This is EXPECTED (external licensed dependency, gitignored by design), "
                     "not an error.")
        lines.append(f"      RECORDED elsewhere (NOT verifiable here): F3 = "
                     f"{rec.get('F3_grounded', 'n/a')!r}. A recorded result from another")
        lines.append("      machine is NOT a live verdict. Supply your own copy at "
                     f"{fid['book_ground_truth']} to verify (see README).")
    else:
        book = normalize(load(book_path))
        cq_in_book = [q for q in cq if normalize(q["quote"]) in book]
        fab = fx.get("fabricated_removed", [])
        fab_absent = [s for s in fab if normalize(s) not in book]
        conf_ok = len(cq_in_book) == len(cq)
        fab_ok = len(fab_absent) == len(fab)
        f3f_pass = conf_ok and fab_ok
        lines.append(f"  F3  full book (live) : {'PASS' if f3f_pass else 'FAIL'} "
                     f"— {len(cq_in_book)}/{len(cq)} confirmed quotes verbatim in book · "
                     f"{len(fab_absent)}/{len(fab)} fabricated quotes correctly ABSENT")
        if not f3f_pass:
            missing_q = [q['quote'] for q in cq if normalize(q['quote']) not in book]
            present_fab = [s for s in fab if normalize(s) in book]
            if missing_q:
                lines.append(f"      confirmed-but-missing from book: {missing_q}")
            if present_fab:
                lines.append(f"      fabricated-but-present in book: {present_fab}")
    return lines, True

def main(cart):
    man = json.loads(load(os.path.join(cart, "manifest.json")))
    vocab = man["closed_vocab"]
    expected = man["expected_sections"]
    th = man["thresholds"]
    gdir = os.path.join(cart, "golden")

    # ---- repo-integrity: committed, manifest-referenced files that are MISSING ----
    # Missing here == NOT-EVALUATED / INCOMPLETE (loud), NOT a FAIL and NOT a PASS.
    missing_committed = required_committed_files(cart, man)

    rows, recalls, not_evaluated = [], [], []
    for item in man["golden_set"]:
        state = item["state"]
        opath = os.path.join(gdir, item["output"]) if item.get("output") else None
        if not opath or not os.path.exists(opath):
            # a manifest-referenced committed output is absent -> NOT-EVALUATED (not FAIL)
            rows.append((item["doc"], state, "NOT-EVAL", "committed golden output MISSING (not run, not a fail)"))
            not_evaluated.append((item["doc"], state))
            continue
        out = load(opath)
        secs = sections_present(out, expected)
        n_sec = len(secs)
        rf = red_flags_section(out, expected)   # negation-aware, section-scoped
        if state == "flaw-laden":
            key = json.loads(load(os.path.join(gdir, item["key"])))
            planted = key["planted_flaws"]
            found = [p for p in planted if term_asserted(rf, p["match_terms"])]
            recall = len(found) / len(planted)
            recalls.append(recall)
            e1 = "PASS" if n_sec == len(expected) else "FAIL"
            e2 = "PASS" if recall >= th["recall"] else "FAIL"
            detail = f"E1 {n_sec}/{len(expected)} · E2 recall {len(found)}/{len(planted)}={recall:.2f} · vocab_raised={len(vocab_raised(rf,vocab))}"
            verdict = "PASS" if e1=="PASS" and e2=="PASS" else "FAIL"
            rows.append((item["doc"], state, verdict, detail))
        elif state == "clean":
            raised = vocab_raised(rf, vocab)
            e4 = "PASS" if len(raised) <= th["clean_restraint_max"] else "FAIL"
            rows.append((item["doc"], state, e4, f"E4 restraint: {len(raised)} flags ASSERTED (max {th['clean_restraint_max']}) {raised}"))
        elif state in ("off-domain", "empty"):
            # declined == did NOT emit the full fixed structure
            eref = "PASS" if n_sec < len(expected) else "FAIL"
            rows.append((item["doc"], state, eref, f"E-ref: {n_sec}/{len(expected)} sections emitted (want <{len(expected)} = declined)"))
        elif state == "ambiguous":
            rows.append((item["doc"], state, "JUDGE", f"E5 needs validated judge · {n_sec}/{len(expected)} sections"))
        else:
            rows.append((item["doc"], state, "?", f"unknown state '{state}'"))

    # ---- report ----
    print(f"\n=== SKILL OPTIMIZER · scorecard · cartridge: {man['skill']} ===\n")
    w = max(len(r[0]) for r in rows) if rows else 12
    print(f"{'doc'.ljust(w)}  {'state'.ljust(11)}  verdict  detail")
    print("-" * (w + 60))
    for d, s, v, det in rows:
        print(f"{d.ljust(w)}  {s.ljust(11)}  {v.ljust(8)}  {det}")

    # helper: a rollup axis is PASS only if every relevant row PASSED; NOT-EVAL rows make it
    # NOT-RUN (never silently FAIL). Distinguishes the three states CF-065 demands.
    def rollup(states):
        rel = [(d, s, v) for d, s, v, _ in rows if s in states]
        if not rel:
            return "n/a"
        if any(v == "NOT-EVAL" for _, _, v in rel):
            return "NOT-RUN"
        return "PASS" if all(v == "PASS" for _, _, v in rel) else "FAIL"

    mean_recall = sum(recalls)/len(recalls) if recalls else None
    print("\n--- axis rollup (efficacy, deterministic) ---")
    print(f"  E1 structure      : {rollup(('flaw-laden',))}")
    print(f"  E2 recall (mean)  : {mean_recall if mean_recall is None else round(mean_recall,3)}  (bar {th['recall']})")
    print(f"  E4 clean restraint: {rollup(('clean',))}")
    print(f"  E-ref off-domain  : {rollup(('off-domain','empty'))}")

    # SHIP-eligible requires PASS (not NOT-RUN, not FAIL) on each present axis.
    def axis_ship(states):
        r = rollup(states)
        return r in ("PASS", "n/a")
    flaw_ok = axis_ship(('flaw-laden',)) and (mean_recall or 0) >= th["recall"]
    efficacy_ship = flaw_ok and axis_ship(('clean',)) and axis_ship(('off-domain','empty'))

    # INCOMPLETE dominates: missing committed files or NOT-EVAL rows mean we cannot
    # pronounce SHIP or RED — the run is INCOMPLETE (loud), and exits non-zero.
    incomplete = bool(missing_committed) or bool(not_evaluated)

    # ---- fidelity (presence-checked; never a bare PASS while the book is absent) ----
    print("\n--- fidelity (presence-checked ground truth) ---")
    fid_lines, fid_integrity_ok = fidelity_section(cart, man)
    for ln in fid_lines:
        print(ln)
    if not fid_integrity_ok:
        incomplete = True

    # ---- verdict ----
    print("\n--- verdict ---")
    if incomplete:
        print("  OVERALL: INCOMPLETE — cannot pronounce SHIP or RED (missing evaluable inputs).")
        if missing_committed:
            print("  repo-integrity: MISSING committed, manifest-referenced files (hard error):")
            for kind, p in missing_committed:
                print(f"    x {kind}: {p}")
        if not_evaluated:
            print("  NOT-EVALUATED golden rows (committed output absent — not a FAIL):")
            for d, s in not_evaluated:
                print(f"    · {d} ({s})")
    else:
        print(f"  EFFICACY (deterministic part): {'SHIP-eligible' if efficacy_ship else 'RED'}")
    print(f"  E3-validity / E5 (judge)     : PENDING — needs validated LLM-judge")
    print(f"  FIDELITY (full book F3)      : see fidelity block above "
          f"(NOT-RUN and loud if the book is absent — never a hidden PASS).")
    print("\n  NOT-CHECKED (stated, not hidden): judge axes (E3-validity, E5) + full-book F3 when "
          "book absent + golden-set coverage of all 5 states / 8 flags.\n")

    return EXIT_INCOMPLETE if incomplete else EXIT_OK

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 engine/score.py cartridges/<name>"); sys.exit(2)
    sys.exit(main(sys.argv[1]))
