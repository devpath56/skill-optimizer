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

def load(p):
    with open(p) as f:
        return f.read()

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

def main(cart):
    man = json.loads(load(os.path.join(cart, "manifest.json")))
    vocab = man["closed_vocab"]
    expected = man["expected_sections"]
    th = man["thresholds"]
    gdir = os.path.join(cart, "golden")

    rows, recalls = [], []
    for item in man["golden_set"]:
        state = item["state"]
        opath = os.path.join(gdir, item["output"]) if item.get("output") else None
        if not opath or not os.path.exists(opath):
            rows.append((item["doc"], state, "NO-OUTPUT", "skill not yet invoked"))
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
        print(f"{d.ljust(w)}  {s.ljust(11)}  {v.ljust(7)}  {det}")

    mean_recall = sum(recalls)/len(recalls) if recalls else None
    print("\n--- axis rollup (efficacy, deterministic) ---")
    print(f"  E1 structure     : {'PASS' if all(v in ('PASS',) for d,s,v,_ in rows if s=='flaw-laden') else 'CHECK'}")
    print(f"  E2 recall (mean) : {mean_recall if mean_recall is None else round(mean_recall,3)}  (bar {th['recall']})")
    print(f"  E4 clean restraint: {'PASS' if all(v=='PASS' for d,s,v,_ in rows if s=='clean') else ('n/a' if not any(s=='clean' for _,s,_,_ in rows) else 'FAIL')}")
    print(f"  E-ref off-domain : {'PASS' if all(v=='PASS' for d,s,v,_ in rows if s in ('off-domain','empty')) else ('n/a' if not any(s in ('off-domain','empty') for _,s,_,_ in rows) else 'FAIL')}")

    flaw_ok = all(v=='PASS' for d,s,v,_ in rows if s=='flaw-laden') and (mean_recall or 0) >= th["recall"]
    clean_ok = all(v=='PASS' for d,s,v,_ in rows if s=='clean') or not any(s=='clean' for _,s,_,_ in rows)
    ref_ok = all(v=='PASS' for d,s,v,_ in rows if s in ('off-domain','empty')) or not any(s in ('off-domain','empty') for _,s,_,_ in rows)
    efficacy_ship = flaw_ok and clean_ok and ref_ok

    fid = man.get("fidelity_status")
    fid_line = (f"F2 {fid.get('F2_vocab')} · F3 {fid.get('F3_grounded')}" if fid
                else f"PENDING — needs authoritative source text ({man['authoritative_source'].get('book')})")
    print("\n--- verdict ---")
    print(f"  EFFICACY (deterministic part): {'SHIP-eligible' if efficacy_ship else 'RED'}")
    print(f"  E3-validity / E5 (judge)     : PENDING — needs validated LLM-judge")
    print(f"  FIDELITY (F2/F3)             : {fid_line}")
    print(f"\n  NOT-CHECKED (stated, not hidden): judge axes + fidelity axis + golden-set coverage of all 5 states/8 flags.\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 engine/score.py cartridges/<name>"); sys.exit(2)
    main(sys.argv[1])
