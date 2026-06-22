from __future__ import annotations

from .lvs_failure_taxonomy import classify_lvs_summary


def decide_sample_trust(evidence: dict) -> dict:
    drc_clean = bool(evidence.get("drc_clean"))
    lvs_match = bool(evidence.get("lvs_match"))
    pex_available = bool(evidence.get("pex_available"))
    post_sim_valid = bool(evidence.get("post_sim_valid"))
    pvt_valid = bool(evidence.get("pvt_valid"))
    scope = evidence.get("evidence_scope") or "unknown"

    usable_for_post_sim = drc_clean and lvs_match and pex_available
    usable_for_training = (
        usable_for_post_sim
        and post_sim_valid
        and pvt_valid
        and scope == "full_passive_inclusive_gds_lvs"
    )
    reasons = []
    if not drc_clean:
        reasons.append("drc_not_clean")
    if not lvs_match:
        reasons.append("lvs_not_matched")
    if not pex_available:
        reasons.append("pex_missing")
    if not post_sim_valid:
        reasons.append("post_sim_invalid")
    if not pvt_valid:
        reasons.append("pvt_invalid")
    if scope != "full_passive_inclusive_gds_lvs":
        reasons.append("scope_not_full_passive_inclusive_gds_lvs")

    return {
        "candidate_id": evidence.get("candidate_id"),
        "evidence_scope": scope,
        "usable_for_reward": usable_for_post_sim and post_sim_valid,
        "usable_for_post_sim": usable_for_post_sim,
        "usable_for_training": usable_for_training,
        "usable_for_parasitic_modeling": drc_clean and pex_available,
        "usable_only_as_failure_case": not usable_for_training,
        "reasons": reasons,
    }


def decide_sample_trust_from_lvs_text(evidence: dict, lvs_text: str) -> dict:
    diagnosis = classify_lvs_summary(lvs_text)
    trust_input = dict(evidence)
    trust_input["lvs_match"] = diagnosis["lvs_match"]
    return {
        "lvs_diagnosis": diagnosis,
        "trust_decision": decide_sample_trust(trust_input),
    }


def decide_sample_trust_from_state(state: dict) -> dict:
    packets = state.get("evidence") or []
    by_stage = {packet.get("stage"): packet for packet in packets}

    layout = by_stage.get("layout_verification") or {}
    layout_metrics = layout.get("metrics") or {}
    passive = by_stage.get("passive_aware_lvs") or {}
    passive_metrics = passive.get("metrics") or {}
    post_sim = by_stage.get("post_sim") or {}
    pvt_sim = by_stage.get("pvt_sim") or {}
    pvt_metrics = pvt_sim.get("metrics") or {}

    passive_scope = passive.get("verification_scope")
    layout_scope = layout.get("verification_scope")
    evidence_scope = passive_scope or layout_scope or "unknown"

    lvs_match = layout_metrics.get("lvs_match") in (True, "yes", "pass")
    pvt_passed = pvt_metrics.get("pvt_passed_corners")
    pvt_total = pvt_metrics.get("pvt_total_corners")

    return decide_sample_trust(
        {
            "candidate_id": state.get("candidate_id"),
            "drc_clean": layout_metrics.get("drc_count") == 0,
            "lvs_match": lvs_match,
            "pex_available": bool(layout_metrics.get("pex_caps")),
            "post_sim_valid": post_sim.get("status") == "pass",
            "pvt_valid": (
                pvt_sim.get("status") == "pass"
                and pvt_passed is not None
                and pvt_passed == pvt_total
            ),
            "evidence_scope": (
                "full_passive_inclusive_gds_lvs"
                if passive_metrics.get("full_passive_inclusive_gds_lvs_proven")
                else evidence_scope
            ),
        }
    )
