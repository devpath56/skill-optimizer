#!/usr/bin/env python3
"""
Generic scored generate -> re-rank iterate step (diagram box 4-5) for the skill-optimizer.
Skill-agnostic: all specifics come from the cartridge, exactly like score.py.

Usage:  python3 engine/rerank.py cartridges/<name> [--top-k N]

TWO-STAGE SCORING (this file implements STAGE 1 only):
  STAGE 1  cheap DETERMINISTIC proxy ranks ALL N candidates  -> pick top-K survivors   [HERE]
  STAGE 2  full BAR (validated LLM-judge) on the K survivors  -> weighted 0-100 winner  [HOOK,
           outside this file: it needs a model. See run_full_bar() stub + HANDOFF.md.]

THE FIDELITY-BLIND BOUNDARY (load-bearing):
  The proxy is EFFICACY-ONLY and PROVABLY FIDELITY-BLIND. It is handed an "efficacy view"
  of the cartridge with `authoritative_source` STRIPPED OUT, and it asserts that key is
  absent before scoring. It therefore CANNOT read the book, so it CANNOT judge fidelity
  (concept coverage, invented principles, anecdote correctness). Fidelity is decided later,
  by the full-bar-on-survivors stage. Two efficacy-equivalent candidates (e.g. same recall,
  structure, vocab) are INDISTINGUISHABLE to the proxy on purpose -> both survive to the
  stage that can actually tell them apart.

MODEL SEPARATION (hard gate):
  Candidate GENERATOR model must differ from the CHECKER (full-bar judge) model, and NEITHER
  may be Fable (claude-fable-5). The proxy itself is CODE (no model). The ranker REFUSES to
  rank (exit 3) if any candidate's generator == its checker, or either is claude-fable-5.

PROMOTION:
  The winner is STAGED into cartridges/<name>/staging/<candidate_id>/ with a scorecard.json.
  Staging is DISTINCT from the live skill_file: nothing here touches the real skill.

Reuses score.py verbatim (red_flags_section, term_asserted, sections_present, vocab_raised).
score.py is NOT modified.
"""
import json, os, sys, shutil, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score  # reuse the deterministic primitives; do NOT reimplement them

FABLE = "claude-fable-5"

# Efficacy proxy weights (sum to 100). Efficacy-only by construction.
W_RECALL, W_STRUCTURE, W_VOCAB = 70, 20, 10

# --------------------------------------------------------------------------------------
# STAGE 2 (full-bar) weights — how the validated-judge axes fold into a final 0-100.
# --------------------------------------------------------------------------------------
# Rationale (defensible, documented on purpose):
#   * The STAGE 1 proxy is an ENTRY GATE, not a differentiator. Every survivor reached
#     STAGE 2 by scoring at (or near) 100 on the efficacy proxy; among proxy-tied survivors
#     the proxy carries ZERO separating power. So the proxy gets a modest share of the final
#     score (it anchors the absolute number) and the JUDGE breaks the tie.
#   * Within the judge portion, e5_pm_action (PM-action soundness) is the PRIMARY axis — it is
#     the ship-gate's E5 and the whole point of the skill (actionable PM guidance). critique_quality
#     is a real but SECONDARY signal, so it is weighted lower.
#   * fidelity_parity is a HARD boolean gate, not a weighted term: a survivor that FAILS parity
#     cannot win (its judge portion collapses to 0). Both ousterhout survivors pass parity.
W_PROXY_FINAL = 0.40     # STAGE 1 efficacy proxy share of the final score (entry gate; ties here)
W_JUDGE_FINAL = 0.60     # STAGE 2 judge share (this is what actually separates proxy-tied survivors)
W_E5, W_CRITIQUE = 0.60, 0.40   # judge-portion split: PM-action soundness primary, critique secondary
assert abs((W_PROXY_FINAL + W_JUDGE_FINAL) - 1.0) < 1e-9
assert abs((W_E5 + W_CRITIQUE) - 1.0) < 1e-9


def load_json(p):
    with open(p) as f:
        return json.load(f)


# --------------------------------------------------------------------------------------
# STAGE 1: deterministic, EFFICACY-ONLY, PROVABLY FIDELITY-BLIND proxy
# --------------------------------------------------------------------------------------
def proxy_score_doc(output_text, state, key, efficacy_view):
    """Score ONE captured output for ONE golden doc. Weighted 0-100 efficacy score + parts.

    `efficacy_view` is a restricted slice of the manifest: closed_vocab, expected_sections,
    thresholds ONLY. It MUST NOT contain `authoritative_source` -- that is what makes this
    proxy fidelity-blind, and it is asserted below."""
    assert "authoritative_source" not in efficacy_view, (
        "FIDELITY-BLIND VIOLATION: the proxy was handed the authoritative source. "
        "The proxy must never see the book; fidelity is the full-bar stage's job.")

    vocab = efficacy_view["closed_vocab"]
    expected = efficacy_view["expected_sections"]
    th = efficacy_view["thresholds"]

    secs = score.sections_present(output_text, expected)
    structure_frac = len(secs) / len(expected)
    rf = score.red_flags_section(output_text, expected)       # negation-aware, section-scoped
    raised = score.vocab_raised(rf, vocab)

    parts = {"sections": f"{len(secs)}/{len(expected)}", "vocab_raised": len(raised)}

    if state == "flaw-laden":
        planted = key["planted_flaws"]
        found = [p for p in planted if score.term_asserted(rf, p["match_terms"])]
        recall = len(found) / len(planted)
        vocab_breadth = min(len(raised) / len(planted), 1.0)   # name at least the planted set
        s = recall * W_RECALL + structure_frac * W_STRUCTURE + vocab_breadth * W_VOCAB
        parts.update(recall=f"{len(found)}/{len(planted)}={recall:.2f}", recall_val=recall)
    elif state == "clean":
        # efficacy proxy for restraint: fewer asserted flags is better (capped at max)
        cap = th["clean_restraint_max"]
        restraint = 1.0 if len(raised) <= cap else max(0.0, 1 - (len(raised) - cap) / 3)
        s = restraint * (W_RECALL + W_VOCAB) + structure_frac * 0  # structure not expected
        parts.update(restraint=f"{len(raised)} asserted (max {cap})")
    elif state in ("off-domain", "empty"):
        declined = len(secs) < len(expected)
        s = (100.0 if declined else 0.0)
        parts.update(declined=declined)
    else:  # ambiguous / unknown -> proxy cannot score deterministically
        s = structure_frac * W_STRUCTURE
        parts.update(note="proxy-blind state (needs judge)")

    return round(s, 2), parts


def proxy_score_candidate(cand, man, gdir, efficacy_view):
    """Aggregate proxy score across every golden doc this candidate captured (mean)."""
    state_of = {g["doc"]: g for g in man["golden_set"]}
    per_doc, scores = [], []
    outputs = cand.get("outputs") or ({cand["doc"]: cand["output"]} if cand.get("output") else {})
    for doc, opath_rel in outputs.items():
        g = state_of.get(doc)
        if not g:
            per_doc.append((doc, None, {"note": "doc not in golden_set"})); continue
        opath = os.path.join(gdir, opath_rel)
        if not os.path.exists(opath):
            per_doc.append((doc, None, {"note": "output missing"})); continue
        key = load_json(os.path.join(gdir, g["key"])) if g.get("key") else None
        s, parts = proxy_score_doc(score.load(opath), g["state"], key, efficacy_view)
        per_doc.append((doc, s, parts)); scores.append(s)
    agg = round(sum(scores) / len(scores), 2) if scores else None
    return agg, per_doc


# --------------------------------------------------------------------------------------
# MODEL SEPARATION gate (hard)
# --------------------------------------------------------------------------------------
def check_model_separation(candidates, default_checker):
    """Return list of violation strings. Empty list == clean."""
    v = []
    for c in candidates:
        cid = c.get("candidate_id", "?")
        gen = c.get("generator_model")
        chk = c.get("checker_model", default_checker)
        if not gen:
            v.append(f"{cid}: missing generator_model"); continue
        if not chk:
            v.append(f"{cid}: no checker_model (and no cartridge default)"); continue
        if gen == chk:
            v.append(f"{cid}: generator == checker ('{gen}') -- a model may not grade its own output")
        if gen == FABLE:
            v.append(f"{cid}: generator is Fable ('{FABLE}') -- Fable is barred from generation")
        if chk == FABLE:
            v.append(f"{cid}: checker is Fable ('{FABLE}') -- Fable is barred from checking")
    return v


# --------------------------------------------------------------------------------------
# STAGE 2 (full-bar) CONSUMER — reads the judge's output, folds it into a final 0-100.
# --------------------------------------------------------------------------------------
# The judge itself (a model + the authoritative source) runs OUTSIDE this file; its verdict
# lands in staging/survivors_judged.json. This function is the deterministic CONSUMER of that
# verdict: it does NOT call a model. It combines the STAGE 1 proxy (already computed) with the
# STAGE 2 judge axes into a final weighted score, enforces model separation, honors the
# validated flag (unvalidated judge -> PROVISIONAL winner), and confirms the computed winner
# matches the judge's stated winner (surfacing, never silently overriding, any disagreement).
def judge_composite(row):
    """Fold one survivor's judge axes into a 0-1 quality number, with fidelity_parity as a
    hard gate (parity failure -> 0, i.e. cannot win)."""
    e5 = float(row["e5_pm_action"])
    cq = float(row["critique_quality"])
    parity_ok = bool(row.get("fidelity_parity", False))
    composite = (W_E5 * e5 + W_CRITIQUE * cq) if parity_ok else 0.0
    return composite, parity_ok


def run_full_bar(cart, proxy_by_id=None):
    """STAGE 2 consumer. Reads staging/survivors_judged.json (the judge's per-survivor axes)
    and staging/survivors.json (STAGE 1 proxy scores), computes a FINAL weighted 0-100 per
    survivor, writes staging/final-scorecard.json, and returns (exit_code, payload).

    REFUSES (returns exit 3) on a model-separation violation. Labels the winner PROVISIONAL if
    the judge is not yet validated. Surfaces (does not override) any winner disagreement."""
    staging_dir = os.path.join(cart, "staging")
    judged_path = os.path.join(staging_dir, "survivors_judged.json")
    if not os.path.exists(judged_path):
        return 4, {"error": "no survivors_judged.json — run the STAGE 2 judge first"}
    judged = load_json(judged_path)

    # proxy scores: prefer what STAGE 1 just computed in-process; else read survivors.json
    if proxy_by_id is None:
        surv_path = os.path.join(staging_dir, "survivors.json")
        proxy_by_id = {}
        if os.path.exists(surv_path):
            for s in load_json(surv_path).get("survivors", []):
                proxy_by_id[s["candidate_id"]] = s.get("proxy_score")

    # ---- HARD GATE: model separation (judge != generator, neither is Fable) ----
    judge_model = judged.get("judge_model")
    generator_model = judged.get("generator_model")
    sep_violations = []
    if not judge_model:
        sep_violations.append("survivors_judged.json missing judge_model")
    if not generator_model:
        sep_violations.append("survivors_judged.json missing generator_model")
    if judge_model and generator_model and judge_model == generator_model:
        sep_violations.append(
            f"judge_model == generator_model ('{judge_model}') — a model may not grade its own output")
    if judge_model == FABLE:
        sep_violations.append(f"judge_model is Fable ('{FABLE}') — Fable is barred from checking")
    if generator_model == FABLE:
        sep_violations.append(f"generator_model is Fable ('{FABLE}') — Fable is barred from generation")
    if sep_violations:
        print("\n*** STAGE 2 REFUSED — model-separation rule violated ***")
        for m in sep_violations:
            print(f"  x {m}")
        return 3, {"error": "model-separation violation", "violations": sep_violations}
    # the task's explicit contract, as asserts (belt-and-suspenders over the printed refusal)
    assert judge_model != generator_model, "judge_model must differ from generator_model"
    assert judge_model != FABLE and generator_model != FABLE, "neither model may be claude-fable-5"

    validated = bool(judged.get("validated", False))
    label = "SETTLED" if validated else "PROVISIONAL"

    # ---- compute FINAL weighted 0-100 per survivor ----
    final_rows = []
    for row in judged["survivors"]:
        cid = row["candidate_id"]
        proxy = proxy_by_id.get(cid)
        comp, parity_ok = judge_composite(row)
        # proxy anchors the absolute score; judge (0-1) breaks the proxy tie. proxy defaults to
        # 0 if this survivor somehow lacks a STAGE 1 score (should not happen for a real survivor).
        proxy_term = (proxy if proxy is not None else 0.0)
        final = W_PROXY_FINAL * proxy_term + W_JUDGE_FINAL * (100.0 * comp)
        final_rows.append({
            "candidate_id": cid,
            "stage1_proxy": proxy,
            "stage2_e5_pm_action": row["e5_pm_action"],
            "stage2_critique_quality": row["critique_quality"],
            "stage2_fidelity_parity": parity_ok,
            "judge_composite_0_1": round(comp, 4),
            "final_weighted_0_100": round(final, 2),
        })

    # rank: higher final first; stable tie-break on candidate order in judged file
    order_index = {r["candidate_id"]: i for i, r in enumerate(judged["survivors"])}
    final_rows.sort(key=lambda r: (-r["final_weighted_0_100"], order_index[r["candidate_id"]]))
    computed_winner = final_rows[0]["candidate_id"]
    judge_winner = judged.get("winner")

    agreement = (computed_winner == judge_winner)
    disagreement_note = None
    if not agreement:
        disagreement_note = (
            f"DISAGREEMENT: this consumer's weighted math ranks '{computed_winner}' first, but the "
            f"judge's stated winner is '{judge_winner}'. NOT overriding — surfaced for a human. "
            f"(weights: proxy {W_PROXY_FINAL}, judge {W_JUDGE_FINAL}; judge split e5 {W_E5}/critique {W_CRITIQUE}.)")

    return 0, {
        "cartridge": judged.get("cartridge"),
        "judge_model": judge_model,
        "generator_model": generator_model,
        "model_separation": "PASS (judge != generator, neither is Fable)",
        "validated": validated,
        "winner_label": label,
        "weights": {
            "final_proxy_share": W_PROXY_FINAL, "final_judge_share": W_JUDGE_FINAL,
            "judge_e5": W_E5, "judge_critique": W_CRITIQUE,
            "fidelity_parity": "hard gate (parity=false -> judge portion 0, cannot win)",
        },
        "leaderboard": final_rows,
        "computed_winner": computed_winner,
        "judge_stated_winner": judge_winner,
        "winner_agreement": agreement,
        "disagreement_note": disagreement_note,
        "judge_margin": judged.get("margin"),
        "judge_rationale": judged.get("rationale"),
        "validation_required": judged.get("validation_required"),
    }


def emit_stage2(cart):
    """Run the STAGE 2 consumer, print the final leaderboard, and write final-scorecard.json.
    Returns the process exit code."""
    staging_dir = os.path.join(cart, "staging")
    code, res = run_full_bar(cart)
    if code == 4:
        # judge has not run yet: STAGE 2 stays an honest, stated hook (not an error).
        print("\n--- STAGE 2 full-bar: PENDING ---")
        print("  no staging/survivors_judged.json yet — run the validated LLM-judge (checker model +")
        print("  authoritative source) to produce it; then re-run to fold it into a final winner.")
        return 0
    if code != 0:
        print("\nSTAGE 2 halted; nothing finalized.")
        return code

    label = res["winner_label"]
    print("\n--- STAGE 2 leaderboard (full bar = validated-judge axes folded into final 0-100) ---\n")
    hdr = (f"{'rank':<5} {'candidate_id':<14} {'proxy':>6} {'e5':>6} {'critique':>9} "
           f"{'parity':<7} {'FINAL':>7}")
    print(hdr); print("-" * len(hdr))
    for i, r in enumerate(res["leaderboard"], 1):
        print(f"{i:<5} {r['candidate_id']:<14} {(r['stage1_proxy'] or 0):>6.1f} "
              f"{r['stage2_e5_pm_action']:>6.2f} {r['stage2_critique_quality']:>9.2f} "
              f"{('YES' if r['stage2_fidelity_parity'] else 'FAIL'):<7} {r['final_weighted_0_100']:>7.2f}")

    print(f"\nweights: final = proxy·{W_PROXY_FINAL} + judge·{W_JUDGE_FINAL}   |   "
          f"judge = e5·{W_E5} + critique·{W_CRITIQUE}   |   fidelity_parity = hard gate")
    print(f"model separation: judge='{res['judge_model']}' != generator='{res['generator_model']}'  "
          f"(neither is {FABLE})  -> PASS")

    if res["winner_agreement"]:
        print(f"\nWINNER [{label}]: {res['computed_winner']}   "
              f"(computed winner MATCHES judge's stated winner; judge margin {res['judge_margin']})")
    else:
        print(f"\n*** {res['disagreement_note']} ***")
        print(f"WINNER [{label}]: judge says '{res['judge_stated_winner']}', "
              f"consumer math says '{res['computed_winner']}' — HUMAN must reconcile.")

    if label == "PROVISIONAL":
        print(f"\nHONESTY GATE: judge is UNVALIDATED (validated=false) -> winner is PROVISIONAL, "
              f"NOT a settled gate.")
        print(f"  {res['validation_required']}")

    # ---- write final-scorecard.json (staging only; live skill_file untouched) ----
    final_scorecard = {
        "stage": "2-full-bar-consumer",
        "finalized_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "cartridge": res["cartridge"],
        "judge_model": res["judge_model"],
        "generator_model": res["generator_model"],
        "model_separation": res["model_separation"],
        "validated": res["validated"],
        "winner_label": label,
        "winner": res["computed_winner"],
        "judge_stated_winner": res["judge_stated_winner"],
        "winner_agreement": res["winner_agreement"],
        "disagreement_note": res["disagreement_note"],
        "judge_margin": res["judge_margin"],
        "judge_rationale": res["judge_rationale"],
        "weights_used": res["weights"],
        "leaderboard": res["leaderboard"],
        "validation_required": res["validation_required"],
        "promotion": "STAGED ONLY — final-scorecard.json records the winner; the live skill_file is "
                     "NOT touched. A PROVISIONAL winner must NOT be auto-applied until the judge is "
                     "calibrated at TPR/TNR >= 0.85.",
    }
    fs_path = os.path.join(staging_dir, "final-scorecard.json")
    with open(fs_path, "w") as f:
        json.dump(final_scorecard, f, indent=2)
    print(f"\n  final scorecard written: {fs_path}")
    print(f"  live skill_file        : UNTOUCHED (staging only)")
    return 0


# --------------------------------------------------------------------------------------
def main(cart, top_k_cli=None):
    man = load_json(os.path.join(cart, "manifest.json"))
    cand_cfg = load_json(os.path.join(cart, "candidates.json"))
    gdir = os.path.join(cart, "golden")
    candidates = cand_cfg["candidates"]
    default_checker = cand_cfg.get("checker_model")
    top_k = top_k_cli or cand_cfg.get("top_k", 2)

    print(f"\n=== SKILL OPTIMIZER · re-rank (box 4-5) · cartridge: {man['skill']} ===")
    print(f"lever: {cand_cfg.get('lever','?')}   |   N candidates: {len(candidates)}   |   top-K: {top_k}")

    # ---- HARD GATE: model separation, BEFORE any ranking ----
    violations = check_model_separation(candidates, default_checker)
    if violations:
        print("\n*** RANK REFUSED -- model-separation rule violated ***")
        for msg in violations:
            print(f"  x {msg}")
        print("\nRule: candidate generator_model != checker_model, and NEITHER may be "
              f"'{FABLE}'. Fix candidates.json and re-run. Nothing ranked, nothing staged.")
        return 3

    # ---- STAGE 1: proxy-score every candidate (fidelity-blind efficacy view) ----
    efficacy_view = {
        "closed_vocab": man["closed_vocab"],
        "expected_sections": man["expected_sections"],
        "thresholds": man["thresholds"],
    }  # NOTE: authoritative_source deliberately absent -> proxy is fidelity-blind
    scored = []
    for c in candidates:
        agg, per_doc = proxy_score_candidate(c, man, gdir, efficacy_view)
        scored.append({"cand": c, "score": agg, "per_doc": per_doc})

    # stable sort: higher score first, ties keep candidates.json order (index)
    order = list(enumerate(scored))
    order.sort(key=lambda t: (-(t[1]["score"] if t[1]["score"] is not None else -1), t[0]))
    ranked = [s for _, s in order]

    # top-K survivors (only positively-scored candidates are eligible)
    survivors = [r for r in ranked if r["score"] is not None][:top_k]
    survivor_ids = {r["cand"]["candidate_id"] for r in survivors}
    winner = survivors[0] if survivors else None

    # ---- leaderboard ----
    print("\n--- STAGE 1 leaderboard (deterministic proxy · EFFICACY-ONLY · fidelity-blind) ---\n")
    hdr = f"{'rank':<5} {'candidate_id':<14} {'generator':<16} {'checker':<16} {'proxy':>6}  {'survivor':<8} detail"
    print(hdr); print("-" * len(hdr))
    for i, r in enumerate(ranked, 1):
        c = r["cand"]
        d0 = r["per_doc"][0][2] if r["per_doc"] else {}
        detail = " · ".join(f"{k}={v}" for k, v in d0.items() if k != "recall_val")
        surv = "YES" if c["candidate_id"] in survivor_ids else "drop"
        sc = "n/a" if r["score"] is None else f"{r['score']:.1f}"
        print(f"{i:<5} {c['candidate_id']:<14} {c.get('generator_model',''):<16} "
              f"{c.get('checker_model', default_checker):<16} {sc:>6}  {surv:<8} {detail}")

    print(f"\nfidelity-blind boundary: proxy loaded closed_vocab + expected_sections + thresholds only; "
          f"authoritative_source NOT loaded. Efficacy ties are decided by STAGE 2, not here.")

    if not winner:
        print("\nNo positively-scored candidate; nothing staged."); return 1

    # tie note
    tied = [r["cand"]["candidate_id"] for r in survivors if r["score"] == winner["score"]]
    tie_note = (f"proxy TIE at {winner['score']:.1f} among {tied}; provisional winner = "
                f"{winner['cand']['candidate_id']} (stable order). Full-bar (STAGE 2) breaks the tie."
                if len(tied) > 1 else "clear proxy winner")

    # ---- write survivors.json ----
    staging_dir = os.path.join(cart, "staging")
    os.makedirs(staging_dir, exist_ok=True)
    survivors_payload = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "cartridge": man["skill"],
        "lever": cand_cfg.get("lever"),
        "top_k": top_k,
        "stage1_proxy": {"weights": {"recall": W_RECALL, "structure": W_STRUCTURE, "vocab": W_VOCAB},
                         "fidelity_blind": True, "model": None, "kind": "deterministic-code"},
        "stage2_full_bar": {"status": "PENDING-HOOK", "needs": ["checker_model", "authoritative_source"],
                            "decides": "fidelity + final weighted 0-100 winner"},
        "survivors": [
            {"candidate_id": r["cand"]["candidate_id"],
             "generator_model": r["cand"].get("generator_model"),
             "checker_model": r["cand"].get("checker_model", default_checker),
             "proxy_score": r["score"],
             "per_doc": [{"doc": d, "score": s, "parts": {k: v for k, v in p.items() if k != "recall_val"}}
                         for d, s, p in r["per_doc"]]}
            for r in survivors],
        "provisional_winner": winner["cand"]["candidate_id"],
        "tie_note": tie_note,
    }
    survivors_path = os.path.join(staging_dir, "survivors.json")
    with open(survivors_path, "w") as f:
        json.dump(survivors_payload, f, indent=2)

    # ---- STAGE winner into staging/<candidate_id>/ (distinct from the live skill_file) ----
    wc = winner["cand"]
    wid = wc["candidate_id"]
    win_dir = os.path.join(staging_dir, wid)
    os.makedirs(win_dir, exist_ok=True)
    staged_outputs = {}
    outputs = wc.get("outputs") or ({wc["doc"]: wc["output"]} if wc.get("output") else {})
    for doc, opath_rel in outputs.items():
        src = os.path.join(gdir, opath_rel)
        dst = os.path.join(win_dir, os.path.basename(opath_rel))
        if os.path.exists(src):
            shutil.copyfile(src, dst)
            staged_outputs[doc] = os.path.basename(opath_rel)

    scorecard = {
        "candidate_id": wid,
        "staged_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "cartridge": man["skill"],
        "lever": cand_cfg.get("lever"),
        "variant": wc.get("variant"),
        "generator_model": wc.get("generator_model"),
        "checker_model": wc.get("checker_model", default_checker),
        "model_separation": "PASS (generator != checker, neither is Fable)",
        "stage1_proxy_score": winner["score"],
        "stage1_kind": "deterministic-code (efficacy-only, fidelity-blind)",
        "stage1_parts": [{"doc": d, "score": s, "parts": {k: v for k, v in p.items() if k != "recall_val"}}
                         for d, s, p in winner["per_doc"]],
        "staged_outputs": staged_outputs,
        "tie_note": tie_note,
        "stage2_full_bar": "PENDING-HOOK — fidelity (concept coverage / invented principles / "
                           "anecdote correctness) NOT yet checked; needs the checker model. "
                           "Full-bar may re-order tied survivors.",
        "promotion": "STAGED ONLY — the live skill_file is untouched; a human/next step applies.",
        "live_skill_file": man.get("skill_file"),
    }
    with open(os.path.join(win_dir, "scorecard.json"), "w") as f:
        json.dump(scorecard, f, indent=2)

    print("\n--- STAGE 1 promotion (proxy winner, do NOT auto-apply) ---")
    print(f"  survivors written : {survivors_path}")
    print(f"  provisional winner: {wid}   ({tie_note})")
    print(f"  staged at         : {win_dir}/  (+ scorecard.json)")
    print(f"  live skill_file   : UNTOUCHED ({man.get('skill_file')})")

    # ---- STAGE 2: consume the judge's verdict (if it has run) into a final weighted winner ----
    # The judge (checker model + authoritative source) runs OUTSIDE this file and drops its
    # verdict in staging/survivors_judged.json. If present, fold it in now; else STAGE 2 stays a
    # stated PENDING hook. STAGE 2 breaks the proxy tie among survivors.
    return emit_stage2(cart)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    top_k = None
    if "--top-k" in args:
        i = args.index("--top-k"); top_k = int(args[i + 1]); del args[i:i + 2]
    if len(args) != 1:
        print("usage: python3 engine/rerank.py cartridges/<name> [--top-k N]"); sys.exit(2)
    sys.exit(main(args[0], top_k))
