"""Adapter around the existing Sky130/MAGICAL layout verification pipeline."""

from __future__ import annotations

import re
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import HarnessConfig
from .models import CompiledCandidate, EvidencePacket


def _fs_path(path: Path) -> Path:
    if os.name != "nt":
        return path
    text = str(path.resolve() if not path.is_absolute() else path)
    if text.startswith("\\\\?\\"):
        return Path(text)
    if text.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + text.lstrip("\\"))
    return Path("\\\\?\\" + text)


def _write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _fs_path(path).write_text(text, encoding=encoding)


TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
PASSIVE_MODEL_ALIASES = {"rppoly", "rppoly_m", "rppolywo_m", "rppolywo", "cfmom", "cfmom_2t"}
EXTRACTED_PASSIVE_MODEL_HINTS = {
    "sky130_fd_pr__res_generic_m1",
    "sky130_fd_pr__res_generic_m2",
    "sky130_fd_pr__res_generic_m3",
    "sky130_fd_pr__res_generic_m4",
    "sky130_fd_pr__res_xhigh_po",
    "sky130_fd_pr__res_high_po",
    "sky130_fd_pr__res_generic_po",
}
PASSIVE_LAYER_HINTS = {"RPO", "RPDMY", "RH", "MRDMY", "TSV_PPI", "LVS_DUMMY"}
PASSIVE_LINE_RE = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in sorted(PASSIVE_MODEL_ALIASES)) + r")\b",
    re.IGNORECASE,
)
DROPPED_PASSIVES_RE = re.compile(r"Dropped unsupported source passive devices:\s*(\d+)", re.IGNORECASE)
MAGIC_UNKNOWN_LAYER_RE = re.compile(r"Unknown layer/datatype .* layer=(\d+) type=(\d+)", re.IGNORECASE)
MAGIC_PORT_SHORT_RE = re.compile(
    r"Warning:\s*Ports\s+\"([^\"]+)\"\s+and\s+\"([^\"]+)\"\s+are electrically shorted",
    re.IGNORECASE,
)
MAGIC_DRC_COUNT_RE = re.compile(r"Total DRC errors found:\s*(\d+)", re.IGNORECASE)
PASSIVE_ABSTRACTION_STATUS_RE = re.compile(r"^- Status:\s*`([^`]+)`", re.IGNORECASE | re.MULTILINE)
MAGIC_UNIQUE_NET_SUFFIX_RE = re.compile(r"^(?P<base>.+)_uq\d+$", re.IGNORECASE)
MAGICAL_ENV_KEYS = (
    "MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER",
    "MAGICAL_SKIP_ROUTER_PARSE_GDS",
    "MAGICAL_SKIP_TOP_POWER_ROUTE",
    "MAGICAL_POWER_STRIPE_EXTRA_GRID",
    "MAGICAL_POWER_STRIPE_EXTRA_DBU",
    "MAGICAL_DISABLE_POWER_STRIPE",
    "MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES",
    "MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU",
    "MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS",
    "MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU",
    "MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_LAYERS",
    "MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_BOX_DBU",
    "MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_MARGIN_DBU",
    "MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU",
    "MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU",
    "MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES",
    "MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU",
    "MAGICAL_LOCAL_VDD_STRIPE_Y_DBU",
    "MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU",
    "MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU",
    "MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE",
    "MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_BOX_DBU",
    "MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU",
    "MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE",
    "MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE_MARGIN_DBU",
)


RESISTOR_REMAP_VARIANT_MAPS = {
    "xhigh_po_second_stage": """schema_version: 0.1
status: experiment
purpose: Preserve URPM and rewrite RPM to NPC on already Sky130-remapped pinned shapes.
layers:
- magical_layer: EXISTING_RPM
  magical_internal_number: 86
  sky130_layer_name: npc.drawing
  sky130_gds_layer: '95'
  sky130_datatype: '20'
  status: experimental
  risk: Diagnostic-only rewrite from RPM to NPC for passive-aware LVS probing.
""",
    "high_po_second_stage": """schema_version: 0.1
status: experiment
purpose: Preserve RPM and rewrite URPM to NPC on already Sky130-remapped pinned shapes.
layers:
- magical_layer: EXISTING_URPM
  magical_internal_number: 79
  sky130_layer_name: npc.drawing
  sky130_gds_layer: '95'
  sky130_datatype: '20'
  status: experimental
  risk: Diagnostic-only rewrite from URPM to NPC for passive-aware LVS probing.
""",
    "generic_po_second_stage": """schema_version: 0.1
status: experiment
purpose: Rewrite both URPM and RPM to NPC on already Sky130-remapped pinned shapes.
layers:
- magical_layer: EXISTING_URPM
  magical_internal_number: 79
  sky130_layer_name: npc.drawing
  sky130_gds_layer: '95'
  sky130_datatype: '20'
  status: experimental
  risk: Diagnostic-only rewrite from URPM to NPC for passive-aware LVS probing.
- magical_layer: EXISTING_RPM
  magical_internal_number: 86
  sky130_layer_name: npc.drawing
  sky130_gds_layer: '95'
  sky130_datatype: '20'
  status: experimental
  risk: Diagnostic-only rewrite from RPM to NPC for passive-aware LVS probing.
""",
}


def _read_json_dict_if_present(path_value: Any) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(str(path_value))
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def native_passive_device_recognition_summary(abstraction_summary: dict[str, Any]) -> dict[str, Any]:
    """Summarize whether Magic extracted source passives as direct passive devices.

    Segmented resistor chains and plate-coupling evidence are valid formal
    abstraction inputs, but they are not native passive device recognition.
    """
    source_passives = abstraction_summary.get("source_passives", [])
    if not isinstance(source_passives, list):
        source_passives = []
    source_count = int(abstraction_summary.get("source_passive_count") or len(source_passives) or 0)
    if source_count == 0:
        return {
            "status": "not_applicable",
            "claimable": False,
            "reason": "source netlist has no passive devices",
            "source_passive_count": 0,
            "recognized_source_passive_count": 0,
            "recognized_source_passive_instances": [],
            "missing_source_passive_instances": [],
            "blockers_by_instance": {},
            "scope": "native_magic_extraction_device_recognition",
        }

    compact: list[dict[str, Any]] = []
    recognized: list[str] = []
    missing: list[str] = []
    blockers_by_instance: dict[str, list[str]] = {}
    for item in source_passives:
        if not isinstance(item, dict):
            continue
        instance = str(item.get("source_instance") or "")
        blockers = [str(blocker) for blocker in item.get("blockers", [])]
        direct_device = _truthy(item.get("direct_expected_device_present"))
        native_ready = direct_device and not blockers
        if native_ready:
            recognized.append(instance)
        else:
            missing.append(instance)
            blockers_by_instance[instance] = blockers or ["direct_expected_passive_device_not_present"]
        compact.append(
            {
                "source_instance": instance,
                "source_model": item.get("source_model"),
                "expected_kind": item.get("expected_kind"),
                "direct_expected_device_present": direct_device,
                "native_ready": native_ready,
                "blockers": blockers,
            }
        )

    status = "pass" if len(recognized) == source_count and source_count > 0 else "fail"
    return {
        "status": status,
        "claimable": status == "pass",
        "reason": None
        if status == "pass"
        else "one or more source passives require formal abstraction instead of direct extracted passive devices",
        "source_passive_count": source_count,
        "recognized_source_passive_count": len(recognized),
        "recognized_source_passive_instances": recognized,
        "missing_source_passive_instances": missing,
        "blockers_by_instance": blockers_by_instance,
        "source_passives": compact,
        "scope": "native_magic_extraction_device_recognition",
    }


def summarize_resistor_remap_variants(results: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [
        result
        for result in results
        if isinstance(result.get("abstraction_summary"), dict)
    ]
    best: dict[str, Any] | None = None
    if successful:
        best = max(
            successful,
            key=lambda result: (
                int(result.get("abstraction_summary", {}).get("source_level_abstraction_candidate_count") or 0),
                int(result.get("abstraction_summary", {}).get("source_resistors_with_segmented_chain") or 0),
                int(result.get("abstraction_summary", {}).get("ext_passive_rsubckt_count") or 0),
                -int(result.get("abstraction_summary", {}).get("blocker_count") or 0),
            ),
        )
    best_summary = best.get("abstraction_summary", {}) if best else {}
    best_packet = best.get("abstraction_packet", {}) if best else {}
    best_verification = best.get("abstraction_packet_verification", {}) if best else {}
    verification_from_file = (
        _read_json_dict_if_present(best.get("abstraction_packet_verification_json"))
        if best
        else {}
    )
    if verification_from_file:
        best_verification = {**best_verification, **verification_from_file}
    best_coverage = (
        best_packet.get("source_instance_coverage", {})
        if isinstance(best_packet.get("source_instance_coverage"), dict)
        else {}
    )
    if best_verification.get("all_source_passives_have_candidate") is not None:
        best_coverage = {
            **best_coverage,
            "all_source_passives_have_candidate": best_verification.get(
                "all_source_passives_have_candidate"
            ),
            "missing_source_passive_instances": best_verification.get(
                "missing_source_passive_instances"
            ),
        }
    native_recognition = native_passive_device_recognition_summary(best_summary) if best else {}
    return {
        "status": "pass" if successful else "no_variant_abstraction_summary",
        "variant_count": len(results),
        "successful_variant_count": len(successful),
        "best_variant": best.get("variant") if best else None,
        "best_status": best_summary.get("status") if best else None,
        "best_source_level_abstraction_candidate_count": best_summary.get(
            "source_level_abstraction_candidate_count"
        )
        if best
        else None,
        "best_source_resistors_with_segmented_chain": best_summary.get(
            "source_resistors_with_segmented_chain"
        )
        if best
        else None,
        "best_source_capacitors_with_plate_coupling_evidence": best_summary.get(
            "source_capacitors_with_plate_coupling_evidence"
        )
        if best
        else None,
        "best_blocker_count": best_summary.get("blocker_count") if best else None,
        "best_ext_passive_rsubckt_count": best_summary.get("ext_passive_rsubckt_count") if best else None,
        "best_ext_passive_rsubckt_by_source_instance": best_summary.get(
            "ext_passive_rsubckt_by_source_instance"
        )
        if best
        else None,
        "best_abstraction_packet_json": best.get("abstraction_packet_json") if best else None,
        "best_extracted_netlist": best.get("extracted_netlist") if best else None,
        "best_magic_port_short_count": best.get("magic_port_short_count") if best else None,
        "best_magic_supply_short_present": best.get("magic_supply_short_present") if best else None,
        "best_magic_port_shorts": best.get("magic_port_shorts") if best else None,
        "best_abstraction_candidates": best.get("abstraction_candidates") if best else None,
        "best_abstraction_packet_verification_status": best_verification.get("status")
        or best.get("abstraction_packet_verification_status")
        if best
        else None,
        "best_formal_lvs_abstraction_ready": best_verification.get(
            "formal_lvs_abstraction_ready"
        )
        if best
        else None,
        "best_abstraction_scope": best_verification.get("abstraction_scope") if best else None,
        "best_remaining_unresolved_blockers": best_verification.get(
            "remaining_unresolved_blockers"
        )
        if best
        else None,
        "best_abstraction_packet_verification_json": best.get(
            "abstraction_packet_verification_json"
        )
        if best
        else None,
        "best_abstraction_source_passive_abs_netlist": best.get(
            "abstraction_source_passive_abs_netlist"
        )
        if best
        else None,
        "best_abstraction_candidate_passive_abs_netlist": best.get(
            "abstraction_candidate_passive_abs_netlist"
        )
        if best
        else None,
        "best_passive_abs_netgen_status": best.get("passive_abs_netgen_status") if best else None,
        "best_passive_abs_lvs_result_summary": best.get("passive_abs_lvs_result_summary")
        if best
        else None,
        "best_passive_abs_netgen_report": best.get("passive_abs_netgen_report") if best else None,
        "best_passive_aware_lvs_trial_prepare_status": best.get(
            "passive_aware_lvs_trial_prepare_status"
        )
        if best
        else None,
        "best_passive_aware_lvs_trial_formal_lvs_abstraction_ready": best.get(
            "passive_aware_lvs_trial_formal_lvs_abstraction_ready"
        )
        if best
        else None,
        "best_passive_aware_lvs_trial_abstraction_scope": best.get(
            "passive_aware_lvs_trial_abstraction_scope"
        )
        if best
        else None,
        "best_passive_aware_lvs_trial_netgen_status": best.get(
            "passive_aware_lvs_trial_netgen_status"
        )
        if best
        else None,
        "best_passive_aware_lvs_trial_result_summary": best.get(
            "passive_aware_lvs_trial_result_summary"
        )
        if best
        else None,
        "best_passive_aware_mos_connectivity_status": best.get(
            "passive_aware_mos_connectivity_status"
        )
        if best
        else None,
        "best_passive_aware_mos_connectivity_reason": best.get(
            "passive_aware_mos_connectivity_reason"
        )
        if best
        else None,
        "best_passive_aware_mos_connectivity_summary_json": best.get(
            "passive_aware_mos_connectivity_summary_json"
        )
        if best
        else None,
        "best_passive_aware_mos_connectivity_report": best.get(
            "passive_aware_mos_connectivity_report"
        )
        if best
        else None,
        "best_formal_passive_mos_repair_renames": best.get(
            "formal_passive_mos_repair_renames"
        )
        if best
        else None,
        "best_formal_passive_mos_repair_signoff_eligible": best.get(
            "formal_passive_mos_repair_signoff_eligible"
        )
        if best
        else None,
        "best_formal_passive_mos_repair_lvs_trial_prepare_status": best.get(
            "formal_passive_mos_repair_lvs_trial_prepare_status"
        )
        if best
        else None,
        "best_formal_passive_mos_repair_lvs_trial_netgen_status": best.get(
            "formal_passive_mos_repair_lvs_trial_netgen_status"
        )
        if best
        else None,
        "best_formal_passive_mos_repair_lvs_trial_result_summary": best.get(
            "formal_passive_mos_repair_lvs_trial_result_summary"
        )
        if best
        else None,
        "best_route_bridge_trial_status": best.get("route_bridge_trial_status")
        if best
        else None,
        "best_route_bridge_trial_summary_json": best.get("route_bridge_trial_summary_json")
        if best
        else None,
        "best_route_bridge_injection_status": best.get("route_bridge_injection_status")
        if best
        else None,
        "best_route_bridge_count": best.get("route_bridge_count")
        if best
        else None,
        "best_route_bridge_gds": best.get("route_bridge_gds")
        if best
        else None,
        "best_route_bridge_drc_count": best.get("route_bridge_drc_count")
        if best
        else None,
        "best_route_bridge_mos_connectivity_status": best.get(
            "route_bridge_mos_connectivity_status"
        )
        if best
        else None,
        "best_route_bridge_formal_passive_lvs_prepare_status": best.get(
            "route_bridge_formal_passive_lvs_prepare_status"
        )
        if best
        else None,
        "best_route_bridge_formal_passive_lvs_netgen_status": best.get(
            "route_bridge_formal_passive_lvs_netgen_status"
        )
        if best
        else None,
        "best_route_bridge_formal_passive_lvs_result_summary": best.get(
            "route_bridge_formal_passive_lvs_result_summary"
        )
        if best
        else None,
        "best_route_bridge_summary_json": best.get("route_bridge_summary_json")
        if best
        else None,
        "best_hybrid_mos_passive_lvs_trial_prepare_status": best.get(
            "hybrid_mos_passive_lvs_trial_prepare_status"
        )
        if best
        else None,
        "best_hybrid_mos_passive_lvs_trial_netgen_status": best.get(
            "hybrid_mos_passive_lvs_trial_netgen_status"
        )
        if best
        else None,
        "best_hybrid_mos_passive_lvs_trial_result_summary": best.get(
            "hybrid_mos_passive_lvs_trial_result_summary"
        )
        if best
        else None,
        "best_all_source_passives_have_candidate": best_coverage.get(
            "all_source_passives_have_candidate"
        )
        if best
        else None,
        "best_missing_source_passive_instances": best_coverage.get(
            "missing_source_passive_instances"
        )
        if best
        else None,
        "best_native_passive_device_recognition": native_recognition if best else None,
        "best_native_passive_device_recognition_status": native_recognition.get("status")
        if best
        else None,
        "best_native_passive_device_recognition_claimed": native_recognition.get("claimable")
        if best
        else None,
        "best_native_passive_device_recognition_missing_instances": native_recognition.get(
            "missing_source_passive_instances"
        )
        if best
        else None,
        "best_native_passive_device_recognition_blockers": native_recognition.get(
            "blockers_by_instance"
        )
        if best
        else None,
        "results": results,
    }


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "pass"}
    return bool(value)


def _native_full_passive_lvs_pass(summary: dict[str, Any]) -> bool:
    native_status = str(
        summary.get("best_native_passive_device_recognition_status")
        or summary.get("native_passive_device_recognition_status")
        or summary.get("best_full_passive_inclusive_gds_native_lvs_status")
        or summary.get("full_passive_inclusive_gds_native_lvs_status")
        or ""
    ).lower()
    native_recognition_pass = native_status in {
        "pass",
        "native_passive_device_recognition_pass",
        "full_passive_inclusive_gds_lvs_pass",
    } and _truthy(
        summary.get("best_native_passive_device_recognition_claimed")
        or summary.get("native_passive_device_recognition_claimed")
        or summary.get("full_passive_inclusive_gds_lvs_proven")
    )
    full_gds_lvs_pass = str(
        summary.get("best_passive_aware_lvs_trial_netgen_status")
        or summary.get("passive_aware_lvs_trial_netgen_status")
        or summary.get("best_full_passive_inclusive_gds_native_lvs_status")
        or summary.get("full_passive_inclusive_gds_native_lvs_status")
        or ""
    ).lower() in {"pass", "full_passive_inclusive_gds_lvs_pass"}
    return native_recognition_pass and (
        full_gds_lvs_pass or _truthy(summary.get("full_passive_inclusive_gds_lvs_proven"))
    )


def classify_passive_aware_evidence(
    resistor_variant_summary: dict[str, Any],
    fallback_reason: str,
    fallback_scope: str,
) -> dict[str, Any]:
    """Classify passive-aware evidence without over-claiming native GDS LVS closure."""
    passive_only_lvs_match = str(
        resistor_variant_summary.get("best_passive_abs_netgen_status") or ""
    ).lower() == "pass"
    hybrid_mos_reference_passive_lvs_match = str(
        resistor_variant_summary.get("best_hybrid_mos_passive_lvs_trial_netgen_status") or ""
    ).lower() == "pass"
    full_passive_inclusive_gds_lvs_match = str(
        resistor_variant_summary.get("best_passive_aware_lvs_trial_netgen_status") or ""
    ).lower() == "pass"
    native_full_passive_lvs_match = _native_full_passive_lvs_pass(resistor_variant_summary)
    route_bridge_formal_lvs_match = str(
        resistor_variant_summary.get("best_route_bridge_formal_passive_lvs_netgen_status") or ""
    ).lower() == "pass"
    route_bridge_mos_match = str(
        resistor_variant_summary.get("best_route_bridge_mos_connectivity_status") or ""
    ).lower() == "pass"
    route_bridge_drc_clean = resistor_variant_summary.get("best_route_bridge_drc_count") == 0
    formal_passive_abstraction_ready = _truthy(
        resistor_variant_summary.get("best_formal_lvs_abstraction_ready")
    )
    all_source_passives_have_candidate = _truthy(
        resistor_variant_summary.get("best_all_source_passives_have_candidate")
    )
    formal_lvs_evidence_pass = _truthy(
        resistor_variant_summary.get("formal_passive_lvs_evidence_pass")
    ) or str(resistor_variant_summary.get("formal_passive_lvs_evidence_status") or "").lower() in {
        "formal_passive_lvs_evidence_pass",
        "full_passive_inclusive_gds_lvs_pass",
    }
    formal_abstraction_pass = (
        formal_lvs_evidence_pass
        or (
            formal_passive_abstraction_ready
            and all_source_passives_have_candidate
            and passive_only_lvs_match
            and hybrid_mos_reference_passive_lvs_match
        )
    )

    if native_full_passive_lvs_match:
        return {
            "packet_status": "pass",
            "passive_aware_status": "full_passive_aware_lvs_pass",
            "verification_scope": "full_passive_inclusive_gds_lvs",
            "verification_scope_detail": "full_passive_inclusive_gds_lvs",
            "reason": "Full passive-inclusive extracted GDS LVS matched the source netlist.",
            "formal_passive_abstraction_ready": formal_passive_abstraction_ready,
            "formal_passive_only_lvs_match": passive_only_lvs_match,
            "hybrid_mos_reference_passive_lvs_match": hybrid_mos_reference_passive_lvs_match,
            "full_passive_inclusive_gds_lvs_proven": True,
            "all_source_passives_have_candidate": all_source_passives_have_candidate,
        }

    if (
        full_passive_inclusive_gds_lvs_match
        and formal_passive_abstraction_ready
        and all_source_passives_have_candidate
    ):
        return {
            "packet_status": "formal_abstraction_with_full_gds_mos_pass",
            "passive_aware_status": "formal_abstraction_with_full_gds_mos_pass",
            "verification_scope": "formal_passive_abstraction_with_full_gds_mos",
            "verification_scope_detail": "formal_passive_abstraction_with_full_gds_mos",
            "reason": (
                "Full-GDS MOS extraction plus formal passive R/C abstraction LVS passed; "
                "native passive device recognition is still not claimed."
            ),
            "formal_passive_abstraction_ready": True,
            "formal_passive_only_lvs_match": passive_only_lvs_match,
            "hybrid_mos_reference_passive_lvs_match": hybrid_mos_reference_passive_lvs_match,
            "full_passive_inclusive_gds_lvs_proven": False,
            "all_source_passives_have_candidate": True,
        }

    if (
        route_bridge_formal_lvs_match
        and route_bridge_mos_match
        and route_bridge_drc_clean
        and formal_passive_abstraction_ready
        and all_source_passives_have_candidate
    ):
        return {
            "packet_status": "formal_abstraction_with_gds_mos_bridge_pass",
            "passive_aware_status": "formal_abstraction_with_gds_mos_bridge_pass",
            "verification_scope": "formal_passive_abstraction_with_gds_mos_bridge",
            "verification_scope_detail": "formal_passive_abstraction_with_gds_mos_bridge",
            "reason": (
                "Route-label plus MOS bridge GDS repair has 0 DRC, MOS connectivity passes from "
                "the repaired full-GDS extraction, and formal passive R/C abstraction LVS passes; "
                "native passive device recognition is still not claimed."
            ),
            "formal_passive_abstraction_ready": True,
            "formal_passive_only_lvs_match": passive_only_lvs_match,
            "hybrid_mos_reference_passive_lvs_match": hybrid_mos_reference_passive_lvs_match,
            "full_passive_inclusive_gds_lvs_proven": False,
            "all_source_passives_have_candidate": True,
        }

    if formal_abstraction_pass:
        return {
            "packet_status": "formal_abstraction_pass",
            "passive_aware_status": "formal_abstraction_pass",
            "verification_scope": "formal_passive_abstraction_with_mos_only_projection",
            "verification_scope_detail": "formal_passive_abstraction_with_mos_only_projection",
            "reason": (
                "Source-equivalent passive abstraction and hybrid MOS-reference plus passive LVS "
                "passed; full passive-inclusive GDS LVS is still not proven."
            ),
            "formal_passive_abstraction_ready": True,
            "formal_passive_only_lvs_match": True,
            "hybrid_mos_reference_passive_lvs_match": True,
            "full_passive_inclusive_gds_lvs_proven": False,
            "all_source_passives_have_candidate": True,
        }

    return {
        "packet_status": "unsupported",
        "passive_aware_status": "unsupported",
        "verification_scope": fallback_scope,
        "verification_scope_detail": fallback_scope,
        "reason": fallback_reason,
        "formal_passive_abstraction_ready": formal_passive_abstraction_ready,
        "formal_passive_only_lvs_match": passive_only_lvs_match,
        "hybrid_mos_reference_passive_lvs_match": hybrid_mos_reference_passive_lvs_match,
        "full_passive_inclusive_gds_lvs_proven": False,
        "all_source_passives_have_candidate": all_source_passives_have_candidate,
    }


def parse_markdown_table(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = TABLE_ROW_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key not in {"Field", "---"}:
            values[key] = value
    return values


def parse_cap_ff(raw: str | None) -> float | None:
    if not raw:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", raw)
    return None if not match else float(match.group(0))


def count_source_passives(path: Path) -> int:
    return len(source_passive_instances(path))


def source_passive_instances(path: Path) -> list[dict[str, Any]]:
    instances: list[dict[str, Any]] = []
    if not path.is_file():
        return instances
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("."):
            continue
        flattened = stripped.replace("(", " ").replace(")", " ")
        tokens = flattened.split()
        model_index = None
        for idx, token in enumerate(tokens[1:], start=1):
            if token.lower() in PASSIVE_MODEL_ALIASES:
                model_index = idx
                break
        if model_index is None:
            continue
        instances.append(
            {
                "instance": tokens[0],
                "model": tokens[model_index],
                "terminals": tokens[1:model_index],
            }
        )
    return instances


def parse_dropped_passives(path: Path) -> int | None:
    if not path.is_file():
        return None
    match = DROPPED_PASSIVES_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    return None if match is None else int(match.group(1))


def parse_remap_layer_actions(path: Path) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not path.is_file():
        return actions
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 7 or not cells[0].isdigit():
            continue
        mapping_name = cells[6].split("->", 1)[0].strip()
        actions.append(
            {
                "input_layer": int(cells[0]),
                "input_datatype": int(cells[1]),
                "element_type": cells[2],
                "output_layer": int(cells[3]),
                "output_datatype": int(cells[4]),
                "action": cells[5],
                "mapping": cells[6],
                "mapping_name": mapping_name,
            }
        )
    return actions


def passive_tbd_layers(path: Path) -> list[str]:
    layers: list[str] = []
    for action in parse_remap_layer_actions(path):
        if action["action"] != "preserved_tbd":
            continue
        if action["mapping_name"] not in PASSIVE_LAYER_HINTS:
            continue
        layers.append(f"{action['mapping_name']}:{action['input_layer']}/{action['input_datatype']}")
    return layers


def parse_magic_unknown_layers(path: Path) -> list[str]:
    if not path.is_file():
        return []
    layers: list[str] = []
    seen: set[str] = set()
    for match in MAGIC_UNKNOWN_LAYER_RE.finditer(path.read_text(encoding="utf-8", errors="replace")):
        layer = f"{match.group(1)}/{match.group(2)}"
        if layer not in seen:
            layers.append(layer)
            seen.add(layer)
    return layers


def parse_magic_drc_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    match = MAGIC_DRC_COUNT_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    return None if match is None else int(match.group(1))


def parse_magic_port_shorts(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    shorts: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in MAGIC_PORT_SHORT_RE.finditer(path.read_text(encoding="utf-8", errors="replace")):
        first, second = match.group(1), match.group(2)
        key = tuple(sorted((first, second)))
        if key in seen:
            continue
        shorts.append({"port_a": first, "port_b": second})
        seen.add(key)
    return shorts


def has_magic_port_short(shorts: list[dict[str, str]], first: str, second: str) -> bool:
    target = {first.lower(), second.lower()}
    for item in shorts:
        observed = {str(item.get("port_a", "")).lower(), str(item.get("port_b", "")).lower()}
        if observed == target:
            return True
    return False


def read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def parse_passive_abstraction_status(path: Path) -> str | None:
    if not path.is_file():
        return None
    match = PASSIVE_ABSTRACTION_STATUS_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    return None if match is None else match.group(1)


def run_lvs_preparation_diagnostic(
    *,
    repo_root: Path,
    source_netlist: Path,
    extracted_netlist: Path,
    out_dir: Path,
    top_cell: str,
    report_stem: str = "passive_lvs_preparation",
    diagnostic_dir_name: str = "lvs_prepare_diagnostic",
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / f"{report_stem}_diagnostic.md"
    log = out_dir / f"{report_stem}_diagnostic.log"
    diagnostic_dir = out_dir / diagnostic_dir_name
    if not source_netlist.is_file() or not extracted_netlist.is_file():
        reason = "source or extracted netlist missing"
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": report,
            "log": log,
            "returncode": None,
            "passive_abstraction_status": None,
        }
    script = repo_root / "tools" / "sky130_adapter" / "prepare_lvs_netlists.py"
    cmd = [
        sys.executable,
        str(script),
        "--source",
        str(source_netlist),
        "--extracted",
        str(extracted_netlist),
        "--out-dir",
        str(diagnostic_dir),
        "--prefix",
        top_cell,
        "--report",
        str(report),
    ]
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.write_text(result.stdout or "", encoding="utf-8")
    abstraction_status = parse_passive_abstraction_status(report)
    return {
        "status": "pass" if result.returncode == 0 and report.is_file() else "fail",
        "reason": None if result.returncode == 0 and report.is_file() else "prepare_lvs_netlists failed",
        "report": report,
        "log": log,
        "out_dir": diagnostic_dir,
        "returncode": result.returncode,
        "passive_abstraction_status": abstraction_status,
    }


def run_gds_structure_diagnostic(
    *,
    repo_root: Path,
    gds_path: Path,
    source_netlist: Path,
    case_dir: Path,
    out_dir: Path,
    top_cell: str,
    report_stem: str = "passive_gds_structure",
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / f"{report_stem}_diagnostic.md"
    summary_json = out_dir / f"{report_stem}_summary.json"
    log = out_dir / f"{report_stem}_diagnostic.log"
    if not gds_path.is_file():
        reason = f"GDS not found: {gds_path}"
        log.write_text(reason + "\n", encoding="utf-8")
        return {"status": "skipped", "reason": reason, "report": report, "summary_json": summary_json, "log": log}
    script = repo_root / "tools" / "sky130_adapter" / "inspect_gds_structure.py"
    cmd = [
        sys.executable,
        str(script),
        "--gds",
        str(gds_path),
        "--report",
        str(report),
        "--summary-json",
        str(summary_json),
        "--source-netlist",
        str(source_netlist),
        "--case-dir",
        str(case_dir),
        "--top-cell",
        top_cell,
    ]
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.write_text(result.stdout or "", encoding="utf-8")
    summary: dict[str, Any] = {}
    if summary_json.is_file():
        try:
            summary = json.loads(summary_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": "pass" if result.returncode == 0 and report.is_file() else "fail",
        "reason": None if result.returncode == 0 and report.is_file() else "inspect_gds_structure failed",
        "report": report,
        "summary_json": summary_json,
        "log": log,
        "returncode": result.returncode,
        "summary": summary,
    }


def run_passive_identity_reconstruction(
    *,
    repo_root: Path,
    source_netlist: Path,
    case_dir: Path,
    out_dir: Path,
    top_cell: str,
    extracted_netlist: Path | None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "passive_identity_reconstruction_report.md"
    summary_json = out_dir / "passive_identity_reconstruction_summary.json"
    log = out_dir / "passive_identity_reconstruction.log"
    pin_file = case_dir / f"{top_cell}.pin"
    gr_file = case_dir / f"{top_cell}.gr"
    placement_log = case_dir / f"run_{top_cell}_trial.log"
    missing = [
        str(path)
        for path in (source_netlist, pin_file, gr_file, placement_log)
        if not path.is_file()
    ]
    if missing:
        reason = "missing passive identity inputs: " + ", ".join(missing)
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": report,
            "summary_json": summary_json,
            "log": log,
            "returncode": None,
            "summary": {},
        }
    script = repo_root / "tools" / "sky130_adapter" / "reconstruct_passive_identity.py"
    cmd = [
        sys.executable,
        str(script),
        "--source-netlist",
        str(source_netlist),
        "--pin-file",
        str(pin_file),
        "--gr-file",
        str(gr_file),
        "--placement-log",
        str(placement_log),
        "--top-cell",
        top_cell,
        "--report",
        str(report),
        "--summary-json",
        str(summary_json),
    ]
    if extracted_netlist is not None and extracted_netlist.is_file():
        cmd.extend(["--extracted-netlist", str(extracted_netlist)])
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.write_text(result.stdout or "", encoding="utf-8")
    summary: dict[str, Any] = {}
    if summary_json.is_file():
        try:
            summary = json.loads(summary_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": "pass" if result.returncode == 0 and report.is_file() else "fail",
        "reason": None if result.returncode == 0 and report.is_file() else "reconstruct_passive_identity failed",
        "report": report,
        "summary_json": summary_json,
        "log": log,
        "returncode": result.returncode,
        "summary": summary,
    }


def run_passive_abstraction_readiness_diagnostic(
    *,
    repo_root: Path,
    source_netlist: Path,
    extracted_netlist: Path,
    out_dir: Path,
    magic_log: Path | None = None,
    ext_file: Path | None = None,
    identity_json: Path | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "passive_identity_label_abstraction_readiness_report.md"
    summary_json = out_dir / "passive_identity_label_abstraction_readiness_summary.json"
    candidate_netlist = out_dir / "passive_identity_label_abstraction_candidates.spice"
    packet_json = out_dir / "passive_identity_label_abstraction_packet.json"
    log = out_dir / "passive_identity_label_abstraction_readiness.log"
    if not source_netlist.is_file() or not extracted_netlist.is_file():
        reason = "source or extracted netlist missing"
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": report,
            "summary_json": summary_json,
            "candidate_netlist": candidate_netlist,
            "packet_json": packet_json,
            "log": log,
            "returncode": None,
            "summary": {},
            "packet": {},
        }
    script = repo_root / "tools" / "sky130_adapter" / "analyze_passive_abstraction.py"
    cmd = [
        sys.executable,
        str(script),
        "--source-netlist",
        str(source_netlist),
        "--extracted-netlist",
        str(extracted_netlist),
        "--report",
        str(report),
        "--summary-json",
        str(summary_json),
        "--candidate-netlist",
        str(candidate_netlist),
        "--packet-json",
        str(packet_json),
    ]
    if magic_log is not None and magic_log.is_file():
        cmd.extend(["--magic-log", str(magic_log)])
    if ext_file is not None and ext_file.is_file():
        cmd.extend(["--ext-file", str(ext_file)])
    if identity_json is not None and identity_json.is_file():
        cmd.extend(["--identity-json", str(identity_json)])
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.write_text(result.stdout or "", encoding="utf-8")
    summary: dict[str, Any] = {}
    if summary_json.is_file():
        try:
            summary = json.loads(summary_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = {}
    packet: dict[str, Any] = {}
    if packet_json.is_file():
        try:
            packet = json.loads(packet_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            packet = {}
    return {
        "status": "pass" if result.returncode == 0 and report.is_file() else "fail",
        "reason": None if result.returncode == 0 and report.is_file() else "analyze_passive_abstraction failed",
        "report": report,
        "summary_json": summary_json,
        "candidate_netlist": candidate_netlist,
        "packet_json": packet_json,
        "log": log,
        "returncode": result.returncode,
        "summary": summary,
        "packet": packet,
    }


def run_passive_abstraction_packet_verification(
    *,
    repo_root: Path,
    source_netlist: Path,
    packet_json: Path,
    report: Path,
    summary_json: Path,
    log: Path,
    top_cell: str = "passive_abstraction",
    source_abstraction_netlist: Path | None = None,
    candidate_abstraction_netlist: Path | None = None,
) -> dict[str, Any]:
    if not source_netlist.is_file() or not packet_json.is_file():
        reason = "source netlist or packet JSON missing"
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": report,
            "summary_json": summary_json,
            "log": log,
            "returncode": None,
            "summary": {},
        }
    script = repo_root / "tools" / "sky130_adapter" / "verify_passive_abstraction_packet.py"
    cmd = [
        sys.executable,
        str(script),
        "--source-netlist",
        str(source_netlist),
        "--packet-json",
        str(packet_json),
        "--report",
        str(report),
        "--summary-json",
        str(summary_json),
        "--top-cell",
        top_cell,
    ]
    if source_abstraction_netlist is not None:
        cmd.extend(["--source-abstraction-netlist", str(source_abstraction_netlist)])
    if candidate_abstraction_netlist is not None:
        cmd.extend(["--candidate-abstraction-netlist", str(candidate_abstraction_netlist)])
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.write_text(result.stdout or "", encoding="utf-8")
    summary: dict[str, Any] = {}
    if summary_json.is_file():
        try:
            summary = json.loads(summary_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": summary.get("status") or ("fail" if result.returncode else "pass"),
        "reason": None if result.returncode == 0 and report.is_file() else "verify_passive_abstraction_packet failed",
        "report": report,
        "summary_json": summary_json,
        "log": log,
        "returncode": result.returncode,
        "summary": summary,
        "source_abstraction_netlist": source_abstraction_netlist,
        "candidate_abstraction_netlist": candidate_abstraction_netlist,
    }


def run_passive_lvs_evidence_verification(
    *,
    repo_root: Path,
    resistor_summary_json: Path,
    report: Path,
    summary_json: Path,
    log: Path,
    require_resistor: bool,
    require_capacitor: bool,
) -> dict[str, Any]:
    if not resistor_summary_json.is_file():
        reason = "resistor remap variant summary missing"
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": str(report),
            "summary_json": str(summary_json),
            "log": str(log),
            "returncode": None,
            "summary": {},
        }
    script = repo_root / "tools" / "sky130_adapter" / "verify_passive_lvs_evidence.py"
    cmd = [
        sys.executable,
        str(script),
        "--resistor-summary-json",
        str(resistor_summary_json),
        "--report",
        str(report),
        "--summary-json",
        str(summary_json),
    ]
    if require_resistor:
        cmd.append("--require-resistor")
    if require_capacitor:
        cmd.append("--require-capacitor")
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.write_text(result.stdout or "", encoding="utf-8")
    summary: dict[str, Any] = {}
    if summary_json.is_file():
        try:
            summary = json.loads(summary_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": summary.get("status") or ("fail" if result.returncode else "pass"),
        "reason": None if result.returncode == 0 else "verify_passive_lvs_evidence did not pass",
        "report": str(report),
        "summary_json": str(summary_json),
        "log": str(log),
        "returncode": result.returncode,
        "summary": summary,
    }


def run_native_passive_capability_probe(
    *,
    repo_root: Path,
    source_netlist: Path,
    sky130a: str | None,
    report: Path,
    summary_json: Path,
    log: Path,
    wsl_distro: str | None = None,
) -> dict[str, Any]:
    if not sky130a:
        reason = "layout.sky130a is not configured"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": str(report),
            "summary_json": str(summary_json),
            "log": str(log),
            "returncode": None,
            "summary": {},
        }
    script = repo_root / "tools" / "sky130_adapter" / "probe_sky130_native_passive_capability.py"
    cmd = [
        sys.executable,
        str(script),
        "--source-netlist",
        str(source_netlist),
        "--sky130a",
        str(sky130a),
        "--repo-root",
        str(repo_root),
        "--report",
        str(report),
        "--summary-json",
        str(summary_json),
    ]
    if wsl_distro:
        cmd.extend(["--wsl-distro", str(wsl_distro)])
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout or "", encoding="utf-8")
    summary = _read_json_dict_if_present(summary_json)
    status = "pass" if result.returncode == 0 and summary else "fail"
    return {
        "status": status,
        "reason": None if status == "pass" else "native passive capability probe failed",
        "report": str(report),
        "summary_json": str(summary_json),
        "log": str(log),
        "returncode": result.returncode,
        "summary": summary,
    }


def run_native_passive_retarget_trial(
    *,
    repo_root: Path,
    packet_json: Path,
    candidate_extracted: Path,
    out_dir: Path,
    prefix: str,
    sky130a: str | None,
    report: Path,
    summary_json: Path,
    log: Path,
    wsl_distro: str | None = None,
) -> dict[str, Any]:
    if not packet_json.is_file():
        reason = f"passive abstraction packet is missing: {packet_json}"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": str(report),
            "summary_json": str(summary_json),
            "log": str(log),
            "returncode": None,
            "summary": {},
        }
    if not candidate_extracted.is_file():
        reason = f"candidate extracted netlist is missing: {candidate_extracted}"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": str(report),
            "summary_json": str(summary_json),
            "log": str(log),
            "returncode": None,
            "summary": {},
        }
    script = repo_root / "tools" / "sky130_adapter" / "prepare_native_passive_retarget_lvs.py"
    cmd = [
        sys.executable,
        str(script),
        "--packet-json",
        str(packet_json),
        "--candidate-extracted",
        str(candidate_extracted),
        "--out-dir",
        str(out_dir),
        "--prefix",
        prefix,
        "--report",
        str(report),
        "--summary-json",
        str(summary_json),
    ]
    if sky130a:
        cmd.extend(["--sky130a", str(sky130a), "--run-netgen"])
    if wsl_distro:
        cmd.extend(["--wsl-distro", str(wsl_distro)])
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout or "", encoding="utf-8")
    summary = _read_json_dict_if_present(summary_json)
    status = str(summary.get("status") or ("fail" if result.returncode else "pass"))
    if result.returncode != 0 and status not in {"native_passive_retarget_incomplete", "native_passive_retarget_ready"}:
        status = "fail"
    return {
        "status": status,
        "reason": None if result.returncode == 0 and summary else "native passive retarget trial failed",
        "report": str(report),
        "summary_json": str(summary_json),
        "log": str(log),
        "returncode": result.returncode,
        "summary": summary,
    }


def run_native_cap_gencell_probe(
    *,
    repo_root: Path,
    sky130a: str | None,
    out_dir: Path,
    report: Path,
    summary_json: Path,
    log: Path,
    wsl_distro: str | None = None,
) -> dict[str, Any]:
    if not sky130a:
        reason = "layout.sky130a is not configured"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": str(report),
            "summary_json": str(summary_json),
            "log": str(log),
            "returncode": None,
            "summary": {},
        }
    script = repo_root / "tools" / "sky130_adapter" / "probe_sky130_native_cap_gencell.py"
    cmd = [
        sys.executable,
        str(script),
        "--sky130a",
        str(sky130a),
        "--out-dir",
        str(out_dir),
        "--summary-json",
        str(summary_json),
        "--report",
        str(report),
    ]
    if wsl_distro:
        cmd.extend(["--wsl-distro", str(wsl_distro)])
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout or "", encoding="utf-8")
    summary = _read_json_dict_if_present(summary_json)
    status = str(summary.get("native_cap_gencell_extraction_status") or ("fail" if result.returncode else "pass"))
    return {
        "status": status,
        "reason": None if result.returncode == 0 and summary else "native cap gencell probe failed",
        "report": str(report),
        "summary_json": str(summary_json),
        "log": str(log),
        "returncode": result.returncode,
        "summary": summary,
    }


def run_native_cap_replacement_candidate(
    *,
    repo_root: Path,
    identity_summary: Path,
    source_gds_structure_json: Path,
    source_instance: str,
    sky130a: str | None,
    out_dir: Path,
    report: Path,
    summary_json: Path,
    log: Path,
    wsl_distro: str | None = None,
) -> dict[str, Any]:
    if not sky130a:
        reason = "layout.sky130a is not configured"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": str(report),
            "summary_json": str(summary_json),
            "log": str(log),
            "returncode": None,
            "summary": {},
        }
    required = [identity_summary, source_gds_structure_json]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        reason = "missing native cap replacement candidate inputs: " + ", ".join(missing)
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": str(report),
            "summary_json": str(summary_json),
            "log": str(log),
            "returncode": None,
            "summary": {},
        }
    script = repo_root / "tools" / "sky130_adapter" / "prepare_sky130_native_cap_replacement.py"
    cmd = [
        sys.executable,
        str(script),
        "--identity-summary",
        str(identity_summary),
        "--source-gds-structure-json",
        str(source_gds_structure_json),
        "--source-instance",
        source_instance,
        "--sky130a",
        str(sky130a),
        "--out-dir",
        str(out_dir),
        "--summary-json",
        str(summary_json),
        "--report",
        str(report),
    ]
    if wsl_distro:
        cmd.extend(["--wsl-distro", str(wsl_distro)])
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout or "", encoding="utf-8")
    summary = _read_json_dict_if_present(summary_json)
    status = str(summary.get("status") or ("fail" if result.returncode else "pass"))
    return {
        "status": status,
        "reason": None if result.returncode == 0 and summary else "native cap replacement candidate failed",
        "report": str(report),
        "summary_json": str(summary_json),
        "log": str(log),
        "returncode": result.returncode,
        "summary": summary,
    }


def run_native_cap_flat_gds_replacement(
    *,
    repo_root: Path,
    input_gds: Path,
    replacement_gds: Path,
    output_gds: Path,
    identity_summary: Path,
    source_gds_structure_json: Path,
    cell: str,
    source_instance: str,
    bridge_mode: str,
    report: Path,
    summary_json: Path,
    log: Path,
) -> dict[str, Any]:
    required = [input_gds, replacement_gds, identity_summary, source_gds_structure_json]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        reason = "missing native cap flat-GDS replacement inputs: " + ", ".join(missing)
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "output_gds": str(output_gds),
            "report": str(report),
            "summary_json": str(summary_json),
            "log": str(log),
            "returncode": None,
            "summary": {},
        }
    script = repo_root / "tools" / "sky130_adapter" / "replace_native_cap_in_flat_gds.py"
    cmd = [
        sys.executable,
        str(script),
        "--input-gds",
        str(input_gds),
        "--replacement-gds",
        str(replacement_gds),
        "--output-gds",
        str(output_gds),
        "--identity-summary",
        str(identity_summary),
        "--source-gds-structure-json",
        str(source_gds_structure_json),
        "--cell",
        cell,
        "--source-instance",
        source_instance,
        "--bridge-mode",
        bridge_mode,
        "--report",
        str(report),
        "--summary-json",
        str(summary_json),
    ]
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout or "", encoding="utf-8")
    summary = _read_json_dict_if_present(summary_json)
    status = str(summary.get("status") or ("fail" if result.returncode else "pass"))
    return {
        "status": status,
        "reason": None if result.returncode == 0 and output_gds.is_file() else "native cap flat-GDS replacement failed",
        "output_gds": str(output_gds),
        "report": str(report),
        "summary_json": str(summary_json),
        "log": str(log),
        "returncode": result.returncode,
        "summary": summary,
    }


def lvs_renames_from_config(config_path: Path) -> list[str]:
    if not config_path.is_file():
        return []
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    raw_items = data.get("lvsNetRenames", [])
    if not isinstance(raw_items, list):
        return []
    renames: list[str] = []
    for item in raw_items:
        if isinstance(item, str) and "=" in item:
            renames.append(item)
        elif isinstance(item, dict):
            old = item.get("old", item.get("from"))
            new = item.get("new", item.get("to"))
            if old and new:
                renames.append(f"{old}={new}")
    return renames


def derive_mos_connectivity_repair_plan(connectivity_summary: dict[str, Any]) -> dict[str, Any]:
    """Build a diagnostic rename plan from MOS comparator split/exact-role hints."""
    rename_map: dict[str, str] = {}
    rename_sources: dict[str, str] = {}
    conflicts: list[dict[str, str]] = []

    def add_rename(old: Any, new: Any, source: str) -> None:
        old_text = str(old or "").strip()
        new_text = str(new or "").strip()
        if not old_text or not new_text or old_text == new_text:
            return
        existing = rename_map.get(old_text)
        if existing is not None and existing != new_text:
            conflicts.append(
                {
                    "candidate_net": old_text,
                    "existing_reference_net": existing,
                    "new_reference_net": new_text,
                    "source": source,
                }
            )
            return
        rename_map[old_text] = new_text
        rename_sources[old_text] = source

    for item in connectivity_summary.get("split_net_repair_suggestions", []):
        if not isinstance(item, dict):
            continue
        reference_nets = item.get("reference_nets", [])
        if not isinstance(reference_nets, list) or len(reference_nets) != 1:
            continue
        reference_net = reference_nets[0]
        groups = item.get("candidate_net_groups", [])
        if not isinstance(groups, list) or not groups:
            continue
        first_group = groups[0] if isinstance(groups[0], dict) else {}
        for candidate_net in first_group.get("candidate_nets", []):
            add_rename(candidate_net, reference_net, "split_net_repair_hint")

    for item in connectivity_summary.get("exact_role_rename_suggestions", []):
        if not isinstance(item, dict):
            continue
        add_rename(
            item.get("candidate_net"),
            item.get("reference_net"),
            "exact_role_rename_hint",
        )

    renames = [f"{old}={new}" for old, new in rename_map.items()]
    return {
        "schema_version": "mos_connectivity_repair_plan.v1",
        "status": "ready" if renames and not conflicts else ("conflict" if conflicts else "empty"),
        "renames": renames,
        "rename_map": rename_map,
        "rename_sources": rename_sources,
        "conflicts": conflicts,
        "source": "mos_connectivity_split_and_exact_role_hints",
        "requires_reference_role_signatures": True,
        "signoff_eligible": False,
        "interpretation": (
            "Diagnostic-only repair plan derived from MOS-only/reference role signatures; "
            "a passing LVS with this plan is not native full-GDS LVS signoff."
        ),
    }


def run_passive_aware_lvs_trial_preparation(
    *,
    repo_root: Path,
    source_netlist: Path,
    extracted_netlist: Path,
    packet_json: Path,
    out_dir: Path,
    prefix: str,
    report: Path,
    summary_json: Path,
    log: Path,
    renames: list[str],
) -> dict[str, Any]:
    script = repo_root / "tools" / "sky130_adapter" / "prepare_passive_aware_lvs_netlists.py"
    cmd = [
        sys.executable,
        str(script),
        "--source",
        str(source_netlist),
        "--extracted",
        str(extracted_netlist),
        "--packet-json",
        str(packet_json),
        "--out-dir",
        str(out_dir),
        "--prefix",
        prefix,
        "--report",
        str(report),
        "--summary-json",
        str(summary_json),
    ]
    for rename in renames:
        cmd.extend(["--rename", rename])
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.write_text(result.stdout or "", encoding="utf-8")
    summary: dict[str, Any] = {}
    if summary_json.is_file():
        try:
            summary = json.loads(summary_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": summary.get("status") or ("fail" if result.returncode else "pass"),
        "reason": None if result.returncode == 0 and report.is_file() else "prepare_passive_aware_lvs_netlists failed",
        "report": str(report),
        "summary_json": str(summary_json),
        "log": str(log),
        "returncode": result.returncode,
        "summary": summary,
    }


def run_mos_connectivity_comparison(
    *,
    repo_root: Path,
    reference_netlist: Path | None,
    candidate_netlist: Path,
    netgen_report: Path,
    report: Path,
    summary_json: Path,
    log: Path,
    vdd: str,
    vss: str,
) -> dict[str, Any]:
    if reference_netlist is None or not reference_netlist.is_file() or not candidate_netlist.is_file():
        reason = "reference or candidate MOS connectivity netlist missing"
        log.write_text(reason + "\n", encoding="utf-8")
        return {
            "status": "skipped",
            "reason": reason,
            "report": str(report),
            "summary_json": str(summary_json),
            "log": str(log),
            "returncode": None,
            "summary": {},
        }
    script = repo_root / "tools" / "sky130_adapter" / "compare_mos_connectivity.py"
    cmd = [
        sys.executable,
        str(script),
        "--reference",
        str(reference_netlist),
        "--candidate",
        str(candidate_netlist),
        "--report",
        str(report),
        "--summary-json",
        str(summary_json),
        "--vdd",
        vdd,
        "--vss",
        vss,
    ]
    if netgen_report.is_file():
        cmd.extend(["--netgen-report", str(netgen_report)])
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log.write_text(result.stdout or "", encoding="utf-8")
    summary: dict[str, Any] = {}
    if summary_json.is_file():
        try:
            summary = json.loads(summary_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = {}
    return {
        "status": summary.get("status") or ("fail" if result.returncode else "pass"),
        "reason": summary.get("reason") or (None if result.returncode == 0 else "compare_mos_connectivity failed"),
        "report": str(report),
        "summary_json": str(summary_json),
        "log": str(log),
        "returncode": result.returncode,
        "summary": summary,
    }


def run_route_net_label_injection(
    *,
    repo_root: Path,
    input_gds: Path,
    gr_file: Path,
    output_gds: Path,
    report: Path,
    log: Path,
    cell: str,
    include_pin_shapes: bool,
) -> dict[str, Any]:
    for path in (output_gds, report, log):
        path.parent.mkdir(parents=True, exist_ok=True)
    if not input_gds.is_file() or not gr_file.is_file():
        reason = "input GDS or MAGICAL .gr file missing"
        _write_text(log, reason + "\n")
        return {
            "status": "skipped",
            "reason": reason,
            "output_gds": str(output_gds),
            "report": str(report),
            "log": str(log),
            "returncode": None,
        }
    script = repo_root / "tools" / "sky130_adapter" / "add_net_labels_from_gr_to_gds.py"
    cmd = [
        sys.executable,
        str(script),
        "--input-gds",
        str(input_gds),
        "--gr",
        str(gr_file),
        "--output-gds",
        str(output_gds),
        "--report",
        str(report),
        "--cell",
        cell,
    ]
    if include_pin_shapes:
        cmd.append("--include-pin-shapes")
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    _write_text(log, result.stdout or "")
    status = "pass" if result.returncode == 0 and output_gds.is_file() else "fail"
    return {
        "status": status,
        "reason": None if status == "pass" else "route net label injection failed",
        "output_gds": str(output_gds),
        "report": str(report),
        "log": str(log),
        "returncode": result.returncode,
    }


def run_mos_route_bridge_injection(
    *,
    repo_root: Path,
    input_gds: Path,
    output_gds: Path,
    cell: str,
    source_netlist: Path,
    pin_file: Path,
    gr_file: Path,
    placement_log: Path,
    mos_connectivity_summary: Path,
    top_cell: str,
    max_gap_dbu: int,
    report: Path,
    summary_json: Path,
    log: Path,
) -> dict[str, Any]:
    for path in (output_gds, report, summary_json, log):
        path.parent.mkdir(parents=True, exist_ok=True)
    required = [input_gds, source_netlist, pin_file, gr_file, placement_log, mos_connectivity_summary]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        reason = "missing MOS route bridge inputs: " + ", ".join(missing)
        _write_text(log, reason + "\n")
        return {
            "status": "skipped",
            "reason": reason,
            "output_gds": str(output_gds),
            "report": str(report),
            "summary_json": str(summary_json),
            "log": str(log),
            "returncode": None,
            "summary": {},
        }
    script = repo_root / "tools" / "sky130_adapter" / "add_mos_route_bridges_to_gds.py"
    cmd = [
        sys.executable,
        str(script),
        "--input-gds",
        str(input_gds),
        "--output-gds",
        str(output_gds),
        "--cell",
        cell,
        "--source-netlist",
        str(source_netlist),
        "--pin-file",
        str(pin_file),
        "--gr-file",
        str(gr_file),
        "--placement-log",
        str(placement_log),
        "--mos-connectivity-summary",
        str(mos_connectivity_summary),
        "--top-cell",
        top_cell,
        "--max-gap-dbu",
        str(max_gap_dbu),
        "--report",
        str(report),
        "--summary-json",
        str(summary_json),
    ]
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    _write_text(log, result.stdout or "")
    summary: dict[str, Any] = {}
    if summary_json.is_file():
        try:
            summary = json.loads(summary_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = {}
    status = summary.get("status") or ("fail" if result.returncode else "pass")
    return {
        "status": status,
        "reason": None if result.returncode == 0 and output_gds.is_file() else "MOS route bridge injection failed",
        "output_gds": str(output_gds),
        "report": str(report),
        "summary_json": str(summary_json),
        "log": str(log),
        "returncode": result.returncode,
        "summary": summary,
    }


def count_extracted_intentional_passives(path: Path | None, source_instances: list[dict[str, Any]]) -> int:
    if path is None or not path.is_file():
        return 0
    expected_names = {str(item["instance"]).lower() for item in source_instances}
    count = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("."):
            continue
        tokens = stripped.replace("(", " ").replace(")", " ").split()
        if not tokens:
            continue
        inst = tokens[0].lower()
        model_tokens = {token.lower() for token in tokens[1:]}
        if inst in expected_names:
            count += 1
        elif inst.startswith("x") and model_tokens.intersection(PASSIVE_MODEL_ALIASES):
            count += 1
    return count


def extracted_physical_passive_devices(path: Path | None) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    if path is None or not path.is_file():
        return devices
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("."):
            continue
        tokens = stripped.replace("(", " ").replace(")", " ").split()
        if not tokens:
            continue
        instance = tokens[0]
        token_set = {token.lower() for token in tokens[1:]}
        model = ""
        terminals: list[str] = []
        if instance.lower().startswith("r") and len(tokens) >= 4:
            terminals = tokens[1:3]
            model = tokens[3]
        elif instance.lower().startswith("x"):
            for idx, token in enumerate(tokens[1:], start=1):
                if token.lower() in PASSIVE_MODEL_ALIASES or token.lower() in EXTRACTED_PASSIVE_MODEL_HINTS:
                    model = token
                    terminals = tokens[1:idx]
                    break
        if model.lower() in EXTRACTED_PASSIVE_MODEL_HINTS or token_set.intersection(PASSIVE_MODEL_ALIASES):
            devices.append({"instance": instance, "model": model, "terminals": terminals})
    return devices


def passive_terminal_recovery_summary(
    *,
    source_instances: list[dict[str, Any]],
    extracted_devices: list[dict[str, Any]],
    magic_log: Path | None = None,
) -> dict[str, Any]:
    source_terminals = {
        str(terminal)
        for item in source_instances
        for terminal in item.get("terminals", [])
    }
    extracted_terminals = {
        str(terminal)
        for device in extracted_devices
        for terminal in device.get("terminals", [])
    }
    covered = sorted(source_terminals.intersection(extracted_terminals))
    missing = sorted(source_terminals - extracted_terminals)
    split_nets: list[dict[str, str]] = []
    seen_splits: set[tuple[str, str]] = set()
    for terminal in sorted(extracted_terminals):
        match = MAGIC_UNIQUE_NET_SUFFIX_RE.match(terminal)
        if not match:
            continue
        base = match.group("base")
        if base not in source_terminals:
            continue
        key = (base, terminal)
        if key in seen_splits:
            continue
        split_nets.append({"source_terminal": base, "extracted_terminal": terminal})
        seen_splits.add(key)

    touching_source = [
        device
        for device in extracted_devices
        if set(str(terminal) for terminal in device.get("terminals", [])).intersection(source_terminals)
    ]
    touching_split = []
    for device in extracted_devices:
        terminals = [str(terminal) for terminal in device.get("terminals", [])]
        if any(
            MAGIC_UNIQUE_NET_SUFFIX_RE.match(terminal)
            and MAGIC_UNIQUE_NET_SUFFIX_RE.match(terminal).group("base") in source_terminals
            for terminal in terminals
        ):
            touching_split.append(device)

    if not source_terminals:
        status = "not_applicable"
    elif len(covered) == len(source_terminals) and not split_nets:
        status = "all_source_passive_terminals_recovered"
    elif covered or split_nets:
        status = "partial_source_passive_terminal_recovery"
    else:
        status = "no_source_passive_terminal_recovery"

    port_shorts = parse_magic_port_shorts(magic_log) if magic_log is not None else []
    return {
        "status": status,
        "source_passive_terminal_count": len(source_terminals),
        "source_passive_terminals": sorted(source_terminals),
        "extracted_passive_terminal_count": len(extracted_terminals),
        "extracted_passive_terminals": sorted(extracted_terminals),
        "covered_source_passive_terminals": covered,
        "missing_source_passive_terminals": missing,
        "split_source_passive_terminals": split_nets,
        "split_source_passive_terminal_count": len(split_nets),
        "extracted_passives_touching_source_terminals": len(touching_source),
        "extracted_passives_touching_split_source_terminals": len(touching_split),
        "magic_port_shorts": port_shorts,
        "magic_port_short_count": len(port_shorts),
    }


def write_passive_terminal_recovery_report(
    path: Path,
    summary: dict[str, Any],
    extracted_devices: list[dict[str, Any]],
) -> None:
    lines = [
        "# Passive Terminal Recovery Report",
        "",
        "## Summary",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Source passive terminals: {summary.get('source_passive_terminal_count', 0)}",
        f"- Covered source passive terminals: {', '.join(summary.get('covered_source_passive_terminals', [])) or 'none'}",
        f"- Missing source passive terminals: {', '.join(summary.get('missing_source_passive_terminals', [])) or 'none'}",
        f"- Split source passive terminal candidates: {summary.get('split_source_passive_terminal_count', 0)}",
        f"- Magic port shorts: {summary.get('magic_port_short_count', 0)}",
        "",
        "## Split Net Candidates",
        "",
    ]
    splits = summary.get("split_source_passive_terminals", [])
    if splits:
        lines.extend(["| source terminal | extracted terminal |", "| --- | --- |"])
        for item in splits:
            lines.append(f"| `{item.get('source_terminal')}` | `{item.get('extracted_terminal')}` |")
    else:
        lines.append("- none")

    lines.extend(["", "## Magic Port Shorts", ""])
    shorts = summary.get("magic_port_shorts", [])
    if shorts:
        lines.extend(["| port A | port B |", "| --- | --- |"])
        for item in shorts:
            lines.append(f"| `{item.get('port_a')}` | `{item.get('port_b')}` |")
    else:
        lines.append("- none")

    lines.extend(["", "## Extracted Physical Passive Devices", ""])
    if extracted_devices:
        lines.extend(["| instance | model | terminals |", "| --- | --- | --- |"])
        for device in extracted_devices:
            terminals = " ".join(str(terminal) for terminal in device.get("terminals", []))
            lines.append(f"| `{device.get('instance')}` | `{device.get('model')}` | `{terminals}` |")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This report describes whether experimental identity labels caused Magic extraction to recover source passive terminal names. It is diagnostic evidence only; it is not a full passive-aware LVS proof.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def find_generated_passive_gds(case_dir: Path, top_cell: str, source_instances: list[dict[str, Any]]) -> dict[str, str]:
    gds_dir = case_dir / "gds"
    if not gds_dir.is_dir():
        return {}
    files = {path.name.lower(): path for path in gds_dir.glob("*.gds")}
    found: dict[str, str] = {}
    for item in source_instances:
        instance = str(item["instance"])
        expected = f"{top_cell}_{instance}.gds".lower()
        if expected in files:
            found[instance] = str(files[expected])
    return found


def write_passive_integrity_report(path: Path, integrity: dict[str, Any]) -> None:
    source_instances = integrity.get("source_passive_instances", [])
    generated = integrity.get("generated_passive_gds_paths", {})
    passive_tbd = integrity.get("passive_tbd_layers", [])
    unknown_layers = integrity.get("magic_unknown_layers", [])
    remap_report_present = "yes" if integrity.get("remap_report_present") else "no"
    magic_extract_log_present = "yes" if integrity.get("magic_extract_log_present") else "no"
    raw_extracted_present = "yes" if integrity.get("raw_extracted_netlist_present") else "no"
    lines = [
        "# Passive-Aware Extraction Integrity Report",
        "",
        "## Summary",
        "",
        f"- Probe pipeline status: {integrity.get('probe_pipeline_status')}",
        f"- Probe failed stage: {integrity.get('probe_failed_stage')}",
        f"- Probe return code: {integrity.get('probe_returncode')}",
        f"- Source passive devices: {integrity.get('source_passive_devices', 0)}",
        f"- Generated passive GDS files: {integrity.get('generated_passive_gds', 0)}",
        f"- Dropped source passives during LVS preparation: {integrity.get('dropped_source_passives')}",
        f"- Extracted physical passive devices: {integrity.get('extracted_physical_passive_devices', 0)}",
        f"- Extracted intentional passive devices: {integrity.get('extracted_intentional_passive_devices', 0)}",
        f"- Passive-related TBD remap layers: {integrity.get('passive_tbd_layer_count', 0)}",
        f"- Magic unknown layers: {integrity.get('magic_unknown_layer_count', 0)}",
        f"- GDS remap report present: {remap_report_present}",
        f"- Magic extract log present: {magic_extract_log_present}",
        f"- Raw extracted netlist present: {raw_extracted_present}",
        "",
        "## Source Passive Instances",
        "",
    ]
    if source_instances:
        lines.extend(["| instance | model | terminals | generated GDS |", "| --- | --- | --- | --- |"])
        for item in source_instances:
            instance = str(item["instance"])
            terminals = " ".join(str(token) for token in item.get("terminals", []))
            lines.append(
                f"| `{instance}` | `{item.get('model')}` | `{terminals}` | "
                f"{'yes' if instance in generated else 'no'} |"
            )
    else:
        lines.append("- none")
    physical_passives = integrity.get("extracted_physical_passive_models", {})
    lines.extend(["", "## Extracted Physical Passive Models", ""])
    if physical_passives:
        lines.extend(["| model | count |", "| --- | ---: |"])
        for model, count in sorted(physical_passives.items()):
            lines.append(f"| `{model}` | {count} |")
    else:
        lines.append("- none")
    lines.extend(["", "## Layer Remap Findings", ""])
    if passive_tbd:
        for layer in passive_tbd:
            lines.append(f"- `{layer}` remains TBD/preserved in Sky130 remap.")
    else:
        lines.append("- No passive-related TBD remap layers found.")
    lines.extend(["", "## Magic Extraction Findings", ""])
    if unknown_layers:
        for layer in unknown_layers:
            lines.append(f"- Magic reported unknown layer/datatype `{layer}`.")
    else:
        lines.append("- No Magic unknown layer/datatype messages found.")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            str(integrity.get("interpretation", "")),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


class LayoutVerificationAdapter:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self.layout_config = dict(config.data.get("layout", {}))
        sky130a = self._resolve_optional_layout_path(self.layout_config.get("sky130a"))
        if sky130a is not None:
            self.layout_config["sky130a"] = sky130a
        elif self.layout_config.get("sky130a"):
            self.layout_config.pop("sky130a", None)
        self.pipeline = config.resolve_path(
            self.layout_config.get("pipeline", "tools/sky130_adapter/run_sky130_case_pipeline.py")
        )

    def _resolve_optional_layout_path(self, value: Any) -> str | None:
        if not value:
            return None
        raw = str(value)
        expanded = os.path.expandvars(raw).strip()
        if not expanded or "$" in expanded or "%" in expanded:
            return None
        path = Path(expanded).expanduser()
        if path.is_absolute():
            return str(path.resolve())
        return str((self.config.repo_root / path).resolve())

    def run(self, compiled: CompiledCandidate, skip_layout: bool = False) -> EvidencePacket:
        if skip_layout:
            return EvidencePacket(
                candidate_id=compiled.candidate_id,
                stage="layout_verification",
                fidelity="E2",
                status="skipped",
                verification_scope=self.config.verification_scope,
                artifacts={"out_dir": str(compiled.out_dir)},
                messages=["layout execution skipped"],
            )
        preflight = self._runtime_preflight(compiled)
        if preflight is not None:
            return preflight

        cmd = self._command(compiled)
        run_log = compiled.out_dir / "layout_adapter_run.log"
        compiled.out_dir.mkdir(parents=True, exist_ok=True)
        with run_log.open("w", encoding="utf-8") as handle:
            result = subprocess.run(
                cmd,
                cwd=self.config.repo_root,
                stdout=handle,
                stderr=subprocess.STDOUT,
                check=False,
                text=True,
            )

        summary_path = compiled.out_dir / "summary.md"
        fields = parse_markdown_table(summary_path)
        metrics = self._metrics(fields)
        physical = self._physical_feedback(fields, result.returncode)
        status = self._status(result.returncode, fields)
        artifacts = {
            "summary": str(summary_path),
            "run_log": str(run_log),
            "out_dir": str(compiled.out_dir),
        }
        raw_extracted = self.find_extracted_netlist(compiled)
        if raw_extracted is not None:
            artifacts["raw_extracted_netlist"] = str(raw_extracted)
        return EvidencePacket(
            candidate_id=compiled.candidate_id,
            stage="layout_verification",
            fidelity="E2",
            status=status,
            verification_scope=self.config.verification_scope,
            metrics=metrics,
            physical_feedback=physical,
            artifacts=artifacts,
            messages=[] if status == "pass" else [f"layout pipeline exit status {result.returncode}"],
        )

    def passive_aware_probe(self, compiled: CompiledCandidate, layout_packet: EvidencePacket) -> EvidencePacket:
        passive_config = dict(self.config.data.get("verification", {}).get("passive_aware", {}))
        if not bool(passive_config.get("enabled", False)):
            return EvidencePacket(
                candidate_id=compiled.candidate_id,
                stage="passive_aware_lvs",
                fidelity="E2P",
                status="skipped",
                verification_scope=self.config.verification_scope,
                messages=["passive-aware LVS/PEX probe disabled"],
            )
        source_passives = count_source_passives(compiled.netlist_path)
        if not bool(passive_config.get("run_full_extraction_probe", False)):
            return EvidencePacket(
                candidate_id=compiled.candidate_id,
                stage="passive_aware_lvs",
                fidelity="E2P",
                status="unsupported",
                verification_scope=self.config.verification_scope,
                metrics={"source_passive_devices": source_passives},
                physical_feedback={
                    "passive_aware_requested": True,
                    "passive_aware_status": "unsupported",
                    "passive_aware_reason": "current default flow uses MOS-only connectivity projection; full passive mapping is not yet proven",
                    "layout_lvs_mode": layout_packet.metrics.get("lvs_mode"),
                    "source_passive_devices": source_passives,
                },
                artifacts=dict(layout_packet.artifacts),
                messages=["passive-aware probe scaffolded; full extraction probe is disabled in config"],
            )
        return self._run_full_extraction_probe(compiled, source_passives)

    def _run_full_extraction_probe(self, compiled: CompiledCandidate, source_passives: int) -> EvidencePacket:
        probe_dir = compiled.candidate_dir / "layout_passive_aware"
        probe_config = compiled.case_dir / f"{self.config.design_id}_{compiled.candidate_id}_passive_probe.json"
        source_data = json.loads(compiled.config_path.read_text(encoding="utf-8"))
        source_data.pop("connectivityLvsProjection", None)
        source_data.pop("lvsNetRenames", None)
        source_data["passiveAwareProbe"] = True
        passive_aware_config = self.config.data.get("verification", {}).get("passive_aware", {})
        if bool(passive_aware_config.get("experimental_passive_remap", False)):
            source_data["experimentalPassiveRemap"] = True
        probe_config.write_text(json.dumps(source_data, indent=4) + "\n", encoding="utf-8")
        probe_compiled = CompiledCandidate(
            candidate_id=compiled.candidate_id,
            candidate_dir=compiled.candidate_dir,
            case_dir=compiled.case_dir,
            out_dir=probe_dir,
            netlist_path=compiled.netlist_path,
            config_path=probe_config,
            action_normalized=compiled.action_normalized,
            values=compiled.values,
            assignments=compiled.assignments,
        )
        preflight = self._runtime_preflight(probe_compiled)
        if preflight is not None:
            preflight.stage = "passive_aware_lvs"
            preflight.fidelity = "E2P"
            return preflight
        cmd = self._command(probe_compiled)
        run_log = probe_dir / "passive_aware_probe_run.log"
        probe_dir.mkdir(parents=True, exist_ok=True)
        with run_log.open("w", encoding="utf-8") as handle:
            result = subprocess.run(
                cmd,
                cwd=self.config.repo_root,
                stdout=handle,
                stderr=subprocess.STDOUT,
                check=False,
                text=True,
            )
        summary_path = probe_dir / "summary.md"
        fields = parse_markdown_table(summary_path)
        passive_aware_config = dict(self.config.data.get("verification", {}).get("passive_aware", {}))
        if (
            result.returncode != 0
            and bool(passive_aware_config.get("reuse_existing_pinned_gds_probe", False))
            and str(fields.get("FAILED_STAGE", "")) in {"magical_place_route", "connectivity_lvs"}
        ):
            fallback = self._run_existing_pinned_gds_probe(compiled, source_passives, run_log, summary_path)
            if fallback is not None:
                return fallback
        metrics = self._metrics(fields)
        probe_failed_stage = fields.get("FAILED_STAGE")
        probe_pipeline_status = fields.get("STATUS") or ("PASS" if result.returncode == 0 else "FAIL")
        remap_report = probe_dir / "gds_remap_report.md"
        magic_extract_log = probe_dir / "magic_extract.log"
        dropped = parse_dropped_passives(probe_dir / "lvs_preparation_report.md")
        raw_extracted = self.find_extracted_netlist(probe_compiled)
        source_instances = source_passive_instances(compiled.netlist_path)
        generated_passive_gds = find_generated_passive_gds(
            compiled.case_dir, self.config.top_cell, source_instances
        )
        tbd_layers = passive_tbd_layers(remap_report)
        unknown_layers = parse_magic_unknown_layers(magic_extract_log)
        extracted_physical_passives = extracted_physical_passive_devices(raw_extracted)
        extracted_physical_model_counts: dict[str, int] = {}
        for item in extracted_physical_passives:
            model = str(item.get("model", "unknown"))
            extracted_physical_model_counts[model] = extracted_physical_model_counts.get(model, 0) + 1
        extracted_intentional_passives = count_extracted_intentional_passives(raw_extracted, source_instances)
        interpretation = _passive_integrity_interpretation(
            probe_returncode=result.returncode,
            probe_pipeline_status=probe_pipeline_status,
            probe_failed_stage=probe_failed_stage,
            remap_report_present=remap_report.is_file(),
            magic_extract_log_present=magic_extract_log.is_file(),
            raw_extracted_present=raw_extracted is not None,
            source_passives=source_passives,
            generated_passive_gds=len(generated_passive_gds),
            dropped_passives=dropped,
            extracted_physical_passives=len(extracted_physical_passives),
            extracted_intentional_passives=extracted_intentional_passives,
            passive_tbd_layer_count=len(tbd_layers),
            magic_unknown_layer_count=len(unknown_layers),
        )
        integrity = {
            "probe_pipeline_status": probe_pipeline_status,
            "probe_failed_stage": probe_failed_stage,
            "probe_returncode": result.returncode,
            "remap_report_present": remap_report.is_file(),
            "magic_extract_log_present": magic_extract_log.is_file(),
            "raw_extracted_netlist_present": raw_extracted is not None,
            "source_passive_devices": source_passives,
            "source_passive_instances": source_instances,
            "generated_passive_gds": len(generated_passive_gds),
            "generated_passive_gds_paths": generated_passive_gds,
            "dropped_source_passives": dropped,
            "extracted_physical_passive_devices": len(extracted_physical_passives),
            "extracted_physical_passive_models": extracted_physical_model_counts,
            "extracted_intentional_passive_devices": extracted_intentional_passives,
            "passive_tbd_layer_count": len(tbd_layers),
            "passive_tbd_layers": tbd_layers,
            "magic_unknown_layer_count": len(unknown_layers),
            "magic_unknown_layers": unknown_layers,
            "interpretation": interpretation,
        }
        passive_integrity_report = probe_dir / "passive_integrity_report.md"
        write_passive_integrity_report(passive_integrity_report, integrity)
        metrics.update(
            {
                "source_passive_devices": source_passives,
                "generated_passive_gds": len(generated_passive_gds),
                "dropped_source_passives": dropped,
                "extracted_physical_passive_devices": len(extracted_physical_passives),
                "extracted_intentional_passive_devices": extracted_intentional_passives,
                "passive_tbd_layer_count": len(tbd_layers),
                "magic_unknown_layer_count": len(unknown_layers),
                "probe_pipeline_status": probe_pipeline_status,
                "probe_failed_stage": probe_failed_stage,
                "probe_returncode": result.returncode,
                "remap_report_present": remap_report.is_file(),
                "magic_extract_log_present": magic_extract_log.is_file(),
                "raw_extracted_netlist_present": raw_extracted is not None,
            }
        )
        lvs_mode = str(metrics.get("lvs_mode", ""))
        lvs_match = str(metrics.get("lvs_match", "")).lower() == "yes"
        passive_preserved = (
            source_passives > 0
            and dropped == 0
            and extracted_intentional_passives >= source_passives
            and not tbd_layers
            and not unknown_layers
        )
        status = "pass" if result.returncode == 0 and lvs_match and lvs_mode == "full_extraction" and passive_preserved else "unsupported"
        reason = "passive-aware LVS passed" if status == "pass" else interpretation
        artifacts = {
            "summary": str(summary_path),
            "run_log": str(run_log),
            "out_dir": str(probe_dir),
            "probe_config": str(probe_config),
            "passive_integrity_report": str(passive_integrity_report),
        }
        if raw_extracted is not None:
            artifacts["raw_extracted_netlist"] = str(raw_extracted)
        return EvidencePacket(
            candidate_id=compiled.candidate_id,
            stage="passive_aware_lvs",
            fidelity="E2P",
            status=status,
            verification_scope="passive_aware_experimental" if status == "pass" else self.config.verification_scope,
            metrics=metrics,
            physical_feedback={
                "passive_aware_requested": True,
                "passive_aware_status": status,
                "passive_aware_reason": reason,
                "source_passive_devices": source_passives,
                "generated_passive_gds": len(generated_passive_gds),
                "dropped_source_passives": dropped,
                "extracted_physical_passive_devices": len(extracted_physical_passives),
                "extracted_physical_passive_models": extracted_physical_model_counts,
                "extracted_intentional_passive_devices": extracted_intentional_passives,
                "passive_tbd_layers": tbd_layers,
                "magic_unknown_layers": unknown_layers,
                "layout_pipeline_returncode": result.returncode,
                "probe_pipeline_status": probe_pipeline_status,
                "probe_failed_stage": probe_failed_stage,
                "remap_report_present": remap_report.is_file(),
                "magic_extract_log_present": magic_extract_log.is_file(),
                "raw_extracted_netlist_present": raw_extracted is not None,
            },
            artifacts=artifacts,
            messages=[] if status == "pass" else [reason],
        )

    def _run_existing_pinned_gds_probe(
        self,
        compiled: CompiledCandidate,
        source_passives: int,
        original_run_log: Path,
        original_summary: Path,
    ) -> EvidencePacket | None:
        pinned_gds = self._existing_pinned_shapes_gds(compiled)
        if pinned_gds is None:
            return None
        probe_dir = compiled.candidate_dir / "layout_passive_existing_gds"
        probe_dir.mkdir(parents=True, exist_ok=True)
        remapped_gds = probe_dir / f"{self.config.top_cell}.sky130.experimental_passive.pinned_shapes.gds"
        remap_report = probe_dir / "experimental_passive_remap_report.md"
        remap_cmd = [
            sys.executable,
            str(self.config.repo_root / "tools/sky130_adapter/remap_gds_to_sky130.py"),
            "--input-gds",
            str(pinned_gds),
            "--output-gds",
            str(remapped_gds),
            "--report",
            str(remap_report),
            "--allow-experimental",
        ]
        remap_result = subprocess.run(
            remap_cmd,
            cwd=self.config.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        (probe_dir / "experimental_passive_remap.log").write_text(
            remap_result.stdout or "", encoding="utf-8"
        )
        if remap_result.returncode != 0:
            return EvidencePacket(
                candidate_id=compiled.candidate_id,
                stage="passive_aware_lvs",
                fidelity="E2P",
                status="unsupported",
                verification_scope=self.config.verification_scope,
                metrics={"source_passive_devices": source_passives, "passive_probe_mode": "existing_pinned_gds_extraction"},
                physical_feedback={
                    "passive_aware_requested": True,
                    "passive_aware_status": "unsupported",
                    "passive_aware_reason": "existing pinned-GDS passive remap failed",
                    "passive_probe_mode": "existing_pinned_gds_extraction",
                },
                artifacts={
                    "out_dir": str(probe_dir),
                    "input_pinned_gds": str(pinned_gds),
                    "original_summary": str(original_summary),
                    "original_run_log": str(original_run_log),
                    "remap_log": str(probe_dir / "experimental_passive_remap.log"),
                },
                messages=["existing pinned-GDS passive remap failed"],
            )

        magic_tcl = probe_dir / "magic_extract_existing_pinned_gds.tcl"
        magic_log = probe_dir / "magic_extract_existing_pinned_gds.log"
        raw_extracted = probe_dir / f"{self.config.top_cell}_existing_pinned_gds_extracted.spice"
        ext_copy = probe_dir / f"{self.config.top_cell}_flat.ext"
        magic_cell = f"{self.config.top_cell}_flat"
        magic_tcl.write_text(
            "\n".join(
                [
                    'puts "SKY130_PASSIVE_EXISTING_GDS_PROBE: reading experimental passive-remapped pinned GDS"',
                    f"gds read {_repo_relative(self.config.repo_root, remapped_gds)}",
                    f"if {{[catch {{load {magic_cell}}} load_error]}} {{",
                    f'    puts stderr "ERROR: failed to load {magic_cell}"',
                    "    puts stderr $load_error",
                    "    quit -noprompt",
                    "}",
                    "select top cell",
                    "extract all",
                    "ext2spice lvs",
                    "ext2spice cthresh 0",
                    "ext2spice rthresh 0",
                    "ext2spice",
                    "quit -noprompt",
                    "",
                ]
            ),
            encoding="ascii",
        )
        magic_result = subprocess.run(
            self._magic_extract_command(magic_tcl, magic_log, raw_extracted, ext_copy, magic_cell),
            cwd=self.config.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        (probe_dir / "magic_extract_existing_pinned_gds.wrapper.log").write_text(
            magic_result.stdout or "", encoding="utf-8"
        )

        source_instances = source_passive_instances(compiled.netlist_path)
        generated_passive_gds = find_generated_passive_gds(
            compiled.case_dir, self.config.top_cell, source_instances
        )
        tbd_layers = passive_tbd_layers(remap_report)
        unknown_layers = parse_magic_unknown_layers(magic_log)
        magic_port_shorts = parse_magic_port_shorts(magic_log)
        ports = self.config.data.get("ports", {})
        vdd_net = str(ports.get("vdd", "vdda"))
        vss_net = str(ports.get("vss", "gnda"))
        magic_supply_short_present = has_magic_port_short(magic_port_shorts, vdd_net, vss_net)
        exclusion_probe_dir = probe_dir / "passive_remap_exclusion_probe"
        exclusion_probe_summary_path = exclusion_probe_dir / "passive_remap_exclusion_probe_summary.json"
        exclusion_group_probe_summary_path = (
            exclusion_probe_dir / "passive_remap_exclusion_group_probe_summary.json"
        )
        baseline_probe_summary_path = exclusion_probe_dir / "passive_remap_baseline_probe_summary.json"
        exclusion_probe_summary = read_json_if_present(exclusion_probe_summary_path)
        exclusion_group_probe_summary = read_json_if_present(exclusion_group_probe_summary_path)
        baseline_probe_summary = read_json_if_present(baseline_probe_summary_path)
        strip_probe_dir = probe_dir / "passive_geometry_strip_probe"
        strip_margin_probe_summary_path = strip_probe_dir / "passive_geometry_strip_margin_probe_summary.json"
        crossing_repair_probe_summary_path = (
            strip_probe_dir / "passive_geometry_crossing_repair_probe_summary.json"
        )
        strip_margin_probe_summary = read_json_if_present(strip_margin_probe_summary_path)
        crossing_repair_probe_summary = read_json_if_present(crossing_repair_probe_summary_path)
        physical_passives = extracted_physical_passive_devices(raw_extracted)
        physical_model_counts: dict[str, int] = {}
        for item in physical_passives:
            model = str(item.get("model", "unknown"))
            physical_model_counts[model] = physical_model_counts.get(model, 0) + 1
        netgen_lvs_available = self._ic_netgen_lvs_available()
        intentional_passives = count_extracted_intentional_passives(raw_extracted, source_instances)
        extraction_passed = magic_result.returncode == 0 and raw_extracted.is_file()
        interpretation = _passive_integrity_interpretation(
            probe_returncode=magic_result.returncode,
            probe_pipeline_status="PASS" if extraction_passed else "FAIL",
            probe_failed_stage=None if extraction_passed else "magic_extract",
            remap_report_present=remap_report.is_file(),
            magic_extract_log_present=magic_log.is_file(),
            raw_extracted_present=raw_extracted.is_file(),
            source_passives=source_passives,
            generated_passive_gds=len(generated_passive_gds),
            dropped_passives=None,
            extracted_physical_passives=len(physical_passives),
            extracted_intentional_passives=intentional_passives,
            passive_tbd_layer_count=len(tbd_layers),
            magic_unknown_layer_count=len(unknown_layers),
        )
        integrity = {
            "probe_pipeline_status": "PASS" if extraction_passed else "FAIL",
            "probe_failed_stage": None if extraction_passed else "magic_extract",
            "probe_returncode": magic_result.returncode,
            "remap_report_present": remap_report.is_file(),
            "magic_extract_log_present": magic_log.is_file(),
            "raw_extracted_netlist_present": raw_extracted.is_file(),
            "source_passive_devices": source_passives,
            "source_passive_instances": source_instances,
            "generated_passive_gds": len(generated_passive_gds),
            "generated_passive_gds_paths": generated_passive_gds,
            "dropped_source_passives": None,
            "extracted_physical_passive_devices": len(physical_passives),
            "extracted_physical_passive_models": physical_model_counts,
            "extracted_intentional_passive_devices": intentional_passives,
            "passive_tbd_layer_count": len(tbd_layers),
            "passive_tbd_layers": tbd_layers,
            "magic_unknown_layer_count": len(unknown_layers),
            "magic_unknown_layers": unknown_layers,
            "magic_port_short_count": len(magic_port_shorts),
            "magic_port_shorts": magic_port_shorts,
            "magic_supply_short_present": magic_supply_short_present,
            "interpretation": interpretation,
        }
        passive_integrity_report = probe_dir / "passive_integrity_report.md"
        write_passive_integrity_report(passive_integrity_report, integrity)
        gds_diagnostic = run_gds_structure_diagnostic(
            repo_root=self.config.repo_root,
            gds_path=remapped_gds,
            source_netlist=compiled.netlist_path,
            case_dir=compiled.case_dir,
            out_dir=probe_dir,
            top_cell=self.config.top_cell,
        )
        gds_summary = gds_diagnostic.get("summary", {}) if isinstance(gds_diagnostic.get("summary"), dict) else {}
        top_gds_summary = gds_summary.get("top_gds", {}) if isinstance(gds_summary.get("top_gds"), dict) else {}
        identity_diagnostic = run_passive_identity_reconstruction(
            repo_root=self.config.repo_root,
            source_netlist=compiled.netlist_path,
            case_dir=compiled.case_dir,
            out_dir=probe_dir,
            top_cell=self.config.top_cell,
            extracted_netlist=raw_extracted,
        )
        identity_summary = (
            identity_diagnostic.get("summary", {})
            if isinstance(identity_diagnostic.get("summary"), dict)
            else {}
        )
        lvs_diagnostic = run_lvs_preparation_diagnostic(
            repo_root=self.config.repo_root,
            source_netlist=compiled.netlist_path,
            extracted_netlist=raw_extracted,
            out_dir=probe_dir,
            top_cell=self.config.top_cell,
        )
        passive_config = dict(self.config.data.get("verification", {}).get("passive_aware", {}))
        label_probe = self._run_passive_identity_label_probe(
            compiled=compiled,
            probe_dir=probe_dir,
            remapped_gds=remapped_gds,
            magic_cell=magic_cell,
            identity_diagnostic=identity_diagnostic,
            source_instances=source_instances,
            enabled=bool(passive_config.get("run_passive_identity_label_probe", True)),
        )
        label_terminal_summary = (
            label_probe.get("terminal_recovery_summary", {})
            if isinstance(label_probe.get("terminal_recovery_summary"), dict)
            else {}
        )
        label_lvs_diagnostic = (
            label_probe.get("lvs_diagnostic", {})
            if isinstance(label_probe.get("lvs_diagnostic"), dict)
            else {}
        )
        label_gds_diagnostic = (
            label_probe.get("gds_diagnostic", {})
            if isinstance(label_probe.get("gds_diagnostic"), dict)
            else {}
        )
        label_gds_summary = (
            label_gds_diagnostic.get("summary", {})
            if isinstance(label_gds_diagnostic.get("summary"), dict)
            else {}
        )
        label_abstraction_diagnostic = (
            label_probe.get("abstraction_diagnostic", {})
            if isinstance(label_probe.get("abstraction_diagnostic"), dict)
            else {}
        )
        label_abstraction_summary = (
            label_abstraction_diagnostic.get("summary", {})
            if isinstance(label_abstraction_diagnostic.get("summary"), dict)
            else {}
        )
        label_abstraction_packet = (
            label_abstraction_diagnostic.get("packet", {})
            if isinstance(label_abstraction_diagnostic.get("packet"), dict)
            else {}
        )
        label_abstraction_packet_summary = (
            label_abstraction_packet.get("candidate_summary", {})
            if isinstance(label_abstraction_packet.get("candidate_summary"), dict)
            else {}
        )
        label_abstraction_packet_verification = (
            label_probe.get("abstraction_packet_verification", {})
            if isinstance(label_probe.get("abstraction_packet_verification"), dict)
            else {}
        )
        label_abstraction_packet_verification_summary = (
            label_abstraction_packet_verification.get("summary", {})
            if isinstance(label_abstraction_packet_verification.get("summary"), dict)
            else {}
        )
        resistor_variant_probe = self._run_resistor_remap_variant_probes(
            compiled=compiled,
            probe_dir=probe_dir,
            remapped_gds=remapped_gds,
            magic_cell=magic_cell,
            identity_diagnostic=identity_diagnostic,
            enabled=bool(passive_config.get("run_resistor_remap_variant_probe", False)),
        )
        resistor_variant_summary = (
            resistor_variant_probe.get("summary", {})
            if isinstance(resistor_variant_probe.get("summary"), dict)
            else {}
        )
        metrics = {
            "source_passive_devices": source_passives,
            "generated_passive_gds": len(generated_passive_gds),
            "extracted_physical_passive_devices": len(physical_passives),
            "extracted_intentional_passive_devices": intentional_passives,
            "passive_tbd_layer_count": len(tbd_layers),
            "magic_unknown_layer_count": len(unknown_layers),
            "magic_port_short_count": len(magic_port_shorts),
            "magic_supply_short_present": magic_supply_short_present,
            "passive_remap_exclusion_probe_short_removed_by_count": len(
                exclusion_probe_summary.get("vdda_gnda_short_removed_by", [])
            )
            if exclusion_probe_summary
            else None,
            "passive_remap_exclusion_group_probe_short_removed_by_count": len(
                exclusion_group_probe_summary.get("vdda_gnda_short_removed_by_groups", [])
            )
            if exclusion_group_probe_summary
            else None,
            "passive_remap_baseline_direct_input_short_present": next(
                (
                    item.get("shorted_vdda_gnda")
                    for item in baseline_probe_summary.get("results", [])
                    if item.get("name") == "direct_input_gds"
                ),
                None,
            )
            if baseline_probe_summary
            else None,
            "passive_remap_baseline_confirmed_only_short_present": next(
                (
                    item.get("shorted_vdda_gnda")
                    for item in baseline_probe_summary.get("results", [])
                    if item.get("name") == "confirmed_only_remap"
                ),
                None,
            )
            if baseline_probe_summary
            else None,
            "passive_geometry_strip_supply_short_removed_by_count": len(
                strip_margin_probe_summary.get("supply_short_removed_by", [])
            )
            if strip_margin_probe_summary
            else None,
            "passive_geometry_crossing_strip_element_count": crossing_repair_probe_summary.get(
                "crossing_stripped_element_count"
            )
            if crossing_repair_probe_summary
            else None,
            "passive_geometry_crossing_strip_supply_short_present_after": crossing_repair_probe_summary.get(
                "magic_supply_short_present_after_crossing_strip"
            )
            if crossing_repair_probe_summary
            else None,
            "passive_geometry_crossing_strip_mos_connectivity_status_after": crossing_repair_probe_summary.get(
                "mos_connectivity_status_after_crossing_strip"
            )
            if crossing_repair_probe_summary
            else None,
            "passive_gds_structure_returncode": gds_diagnostic.get("returncode"),
            "passive_gds_top_text_count": top_gds_summary.get("text_count"),
            "passive_gds_top_ref_count": top_gds_summary.get("ref_count"),
            "passive_gds_source_instance_names_present_count": gds_summary.get(
                "source_passive_instance_names_present_count"
            ),
            "passive_gds_source_terminal_names_present_count": gds_summary.get(
                "source_passive_terminal_names_present_count"
            ),
            "passive_gds_generated_passive_gds_present_count": gds_summary.get(
                "generated_passive_gds_present_count"
            ),
            "passive_identity_reconstruction_returncode": identity_diagnostic.get("returncode"),
            "passive_identity_status": identity_summary.get("status"),
            "passive_identity_exact_route_matches": identity_summary.get(
                "source_passive_pin_exact_route_matches"
            ),
            "passive_identity_missing_route_matches": identity_summary.get(
                "source_passive_pin_missing_route_matches"
            ),
            "passive_identity_pins_with_geometry": identity_summary.get("source_passive_pins_with_geometry"),
            "passive_identity_pins_without_geometry": identity_summary.get("source_passive_pins_without_geometry"),
            "passive_identity_label_injection_candidates": identity_summary.get(
                "source_passive_label_injection_candidates"
            ),
            "passive_lvs_preparation_returncode": lvs_diagnostic.get("returncode"),
            "passive_abstraction_status": lvs_diagnostic.get("passive_abstraction_status"),
            "passive_identity_label_probe_status": label_probe.get("status"),
            "passive_identity_label_injection_returncode": label_probe.get("injection_returncode"),
            "passive_identity_label_magic_extract_returncode": label_probe.get("magic_extract_returncode"),
            "passive_identity_label_recovery_status": label_terminal_summary.get("status"),
            "passive_identity_label_covered_source_terminal_count": len(
                label_terminal_summary.get("covered_source_passive_terminals", [])
            ),
            "passive_identity_label_missing_source_terminal_count": len(
                label_terminal_summary.get("missing_source_passive_terminals", [])
            ),
            "passive_identity_label_split_net_count": label_terminal_summary.get(
                "split_source_passive_terminal_count"
            ),
            "passive_identity_label_magic_port_short_count": label_terminal_summary.get("magic_port_short_count"),
            "passive_identity_label_abstraction_status": label_lvs_diagnostic.get(
                "passive_abstraction_status"
            ),
            "passive_identity_label_abstraction_readiness_returncode": label_abstraction_diagnostic.get(
                "returncode"
            ),
            "passive_identity_label_abstraction_readiness_status": label_abstraction_summary.get("status"),
            "passive_identity_label_source_passives_candidate_for_abstraction": label_abstraction_summary.get(
                "source_passives_candidate_for_abstraction"
            ),
            "passive_identity_label_source_passives_with_partial_terminal_recovery": label_abstraction_summary.get(
                "source_passives_with_partial_terminal_recovery"
            ),
            "passive_identity_label_source_resistors_with_segmented_chain": label_abstraction_summary.get(
                "source_resistors_with_segmented_chain"
            ),
            "passive_identity_label_source_capacitors_with_plate_coupling_evidence": label_abstraction_summary.get(
                "source_capacitors_with_plate_coupling_evidence"
            ),
            "passive_identity_label_source_level_abstraction_candidate_count": label_abstraction_summary.get(
                "source_level_abstraction_candidate_count"
            ),
            "passive_identity_label_abstraction_packet_proof_status": label_abstraction_packet.get(
                "proof_status"
            ),
            "passive_identity_label_full_passive_aware_lvs_proven": label_abstraction_packet.get(
                "full_passive_aware_lvs_proven"
            ),
            "passive_identity_label_abstraction_packet_unresolved_blocker_count": label_abstraction_packet_summary.get(
                "unresolved_blocker_count"
            ),
            "passive_identity_label_abstraction_packet_verification_status": label_abstraction_packet_verification_summary.get(
                "status"
            ),
            "passive_identity_label_formal_lvs_abstraction_ready": label_abstraction_packet_verification_summary.get(
                "formal_lvs_abstraction_ready"
            ),
            "passive_identity_label_abstraction_scope": label_abstraction_packet_verification_summary.get(
                "abstraction_scope"
            ),
            "passive_identity_label_remaining_unresolved_blockers": label_abstraction_packet_verification_summary.get(
                "remaining_unresolved_blockers"
            ),
            "passive_identity_label_abstraction_packet_all_source_passives_have_candidate": label_abstraction_packet_verification_summary.get(
                "all_source_passives_have_candidate"
            ),
            "passive_identity_label_abstraction_packet_all_candidate_support_verified": label_abstraction_packet_verification_summary.get(
                "all_candidate_support_verified"
            ),
            "passive_identity_label_abstraction_blocker_count": label_abstraction_summary.get("blocker_count"),
            "passive_identity_label_ext_devres_count": label_abstraction_summary.get("ext_devres_count"),
            "passive_identity_label_ext_devres_by_source_instance": label_abstraction_summary.get(
                "ext_devres_by_source_instance"
            ),
            "passive_identity_label_ext_passive_rsubckt_count": label_abstraction_summary.get(
                "ext_passive_rsubckt_count"
            ),
            "passive_identity_label_ext_passive_rsubckt_by_source_instance": label_abstraction_summary.get(
                "ext_passive_rsubckt_by_source_instance"
            ),
            "passive_identity_label_gds_source_terminal_names_present_count": label_gds_summary.get(
                "source_passive_terminal_names_present_count"
            ),
            "passive_resistor_variant_probe_status": resistor_variant_summary.get("status"),
            "passive_resistor_variant_probe_count": resistor_variant_summary.get("variant_count"),
            "passive_resistor_variant_successful_count": resistor_variant_summary.get("successful_variant_count"),
            "passive_resistor_variant_best_variant": resistor_variant_summary.get("best_variant"),
            "passive_resistor_variant_best_status": resistor_variant_summary.get("best_status"),
            "passive_resistor_variant_best_magic_port_short_count": resistor_variant_summary.get(
                "best_magic_port_short_count"
            ),
            "passive_resistor_variant_best_magic_supply_short_present": resistor_variant_summary.get(
                "best_magic_supply_short_present"
            ),
            "passive_resistor_variant_best_magic_port_shorts": resistor_variant_summary.get(
                "best_magic_port_shorts"
            ),
            "passive_resistor_variant_best_source_level_abstraction_candidate_count": resistor_variant_summary.get(
                "best_source_level_abstraction_candidate_count"
            ),
            "passive_resistor_variant_best_source_resistors_with_segmented_chain": resistor_variant_summary.get(
                "best_source_resistors_with_segmented_chain"
            ),
            "passive_resistor_variant_best_source_capacitors_with_plate_coupling_evidence": resistor_variant_summary.get(
                "best_source_capacitors_with_plate_coupling_evidence"
            ),
            "passive_resistor_variant_best_blocker_count": resistor_variant_summary.get("best_blocker_count"),
            "passive_resistor_variant_best_ext_passive_rsubckt_count": resistor_variant_summary.get(
                "best_ext_passive_rsubckt_count"
            ),
            "passive_resistor_variant_best_ext_passive_rsubckt_by_source_instance": resistor_variant_summary.get(
                "best_ext_passive_rsubckt_by_source_instance"
            ),
            "passive_resistor_variant_best_abstraction_packet_json": resistor_variant_summary.get(
                "best_abstraction_packet_json"
            ),
            "passive_resistor_variant_best_abstraction_candidates": resistor_variant_summary.get(
                "best_abstraction_candidates"
            ),
            "passive_resistor_variant_best_abstraction_packet_verification_status": resistor_variant_summary.get(
                "best_abstraction_packet_verification_status"
            ),
            "passive_resistor_variant_best_formal_lvs_abstraction_ready": resistor_variant_summary.get(
                "best_formal_lvs_abstraction_ready"
            ),
            "passive_resistor_variant_best_abstraction_scope": resistor_variant_summary.get(
                "best_abstraction_scope"
            ),
            "passive_resistor_variant_best_remaining_unresolved_blockers": resistor_variant_summary.get(
                "best_remaining_unresolved_blockers"
            ),
            "passive_resistor_variant_best_abstraction_packet_verification_json": resistor_variant_summary.get(
                "best_abstraction_packet_verification_json"
            ),
            "passive_resistor_variant_best_abstraction_source_passive_abs_netlist": resistor_variant_summary.get(
                "best_abstraction_source_passive_abs_netlist"
            ),
            "passive_resistor_variant_best_abstraction_candidate_passive_abs_netlist": resistor_variant_summary.get(
                "best_abstraction_candidate_passive_abs_netlist"
            ),
            "passive_resistor_variant_best_passive_abs_netgen_status": resistor_variant_summary.get(
                "best_passive_abs_netgen_status"
            ),
            "passive_resistor_variant_best_passive_abs_lvs_result_summary": resistor_variant_summary.get(
                "best_passive_abs_lvs_result_summary"
            ),
            "passive_resistor_variant_best_passive_abs_netgen_report": resistor_variant_summary.get(
                "best_passive_abs_netgen_report"
            ),
            "passive_resistor_variant_best_passive_aware_lvs_trial_prepare_status": resistor_variant_summary.get(
                "best_passive_aware_lvs_trial_prepare_status"
            ),
            "passive_resistor_variant_best_passive_aware_lvs_trial_formal_lvs_abstraction_ready": resistor_variant_summary.get(
                "best_passive_aware_lvs_trial_formal_lvs_abstraction_ready"
            ),
            "passive_resistor_variant_best_passive_aware_lvs_trial_abstraction_scope": resistor_variant_summary.get(
                "best_passive_aware_lvs_trial_abstraction_scope"
            ),
            "passive_resistor_variant_best_passive_aware_lvs_trial_netgen_status": resistor_variant_summary.get(
                "best_passive_aware_lvs_trial_netgen_status"
            ),
            "passive_resistor_variant_best_passive_aware_lvs_trial_result_summary": resistor_variant_summary.get(
                "best_passive_aware_lvs_trial_result_summary"
            ),
            "passive_resistor_variant_best_passive_aware_mos_connectivity_status": resistor_variant_summary.get(
                "best_passive_aware_mos_connectivity_status"
            ),
            "passive_resistor_variant_best_passive_aware_mos_connectivity_reason": resistor_variant_summary.get(
                "best_passive_aware_mos_connectivity_reason"
            ),
            "passive_resistor_variant_best_passive_aware_mos_connectivity_summary_json": resistor_variant_summary.get(
                "best_passive_aware_mos_connectivity_summary_json"
            ),
            "passive_resistor_variant_best_passive_aware_mos_connectivity_report": resistor_variant_summary.get(
                "best_passive_aware_mos_connectivity_report"
            ),
            "passive_resistor_variant_best_formal_passive_mos_repair_renames": resistor_variant_summary.get(
                "best_formal_passive_mos_repair_renames"
            ),
            "passive_resistor_variant_best_formal_passive_mos_repair_signoff_eligible": resistor_variant_summary.get(
                "best_formal_passive_mos_repair_signoff_eligible"
            ),
            "passive_resistor_variant_best_formal_passive_mos_repair_lvs_trial_prepare_status": resistor_variant_summary.get(
                "best_formal_passive_mos_repair_lvs_trial_prepare_status"
            ),
            "passive_resistor_variant_best_formal_passive_mos_repair_lvs_trial_netgen_status": resistor_variant_summary.get(
                "best_formal_passive_mos_repair_lvs_trial_netgen_status"
            ),
            "passive_resistor_variant_best_formal_passive_mos_repair_lvs_trial_result_summary": resistor_variant_summary.get(
                "best_formal_passive_mos_repair_lvs_trial_result_summary"
            ),
            "passive_resistor_variant_best_route_bridge_trial_status": resistor_variant_summary.get(
                "best_route_bridge_trial_status"
            ),
            "passive_resistor_variant_best_route_bridge_trial_summary_json": resistor_variant_summary.get(
                "best_route_bridge_trial_summary_json"
            ),
            "passive_resistor_variant_best_route_bridge_injection_status": resistor_variant_summary.get(
                "best_route_bridge_injection_status"
            ),
            "passive_resistor_variant_best_route_bridge_count": resistor_variant_summary.get(
                "best_route_bridge_count"
            ),
            "passive_resistor_variant_best_route_bridge_drc_count": resistor_variant_summary.get(
                "best_route_bridge_drc_count"
            ),
            "passive_resistor_variant_best_route_bridge_mos_connectivity_status": resistor_variant_summary.get(
                "best_route_bridge_mos_connectivity_status"
            ),
            "passive_resistor_variant_best_route_bridge_formal_passive_lvs_netgen_status": resistor_variant_summary.get(
                "best_route_bridge_formal_passive_lvs_netgen_status"
            ),
            "passive_resistor_variant_best_route_bridge_formal_passive_lvs_result_summary": resistor_variant_summary.get(
                "best_route_bridge_formal_passive_lvs_result_summary"
            ),
            "passive_resistor_variant_best_hybrid_mos_passive_lvs_trial_prepare_status": resistor_variant_summary.get(
                "best_hybrid_mos_passive_lvs_trial_prepare_status"
            ),
            "passive_resistor_variant_best_hybrid_mos_passive_lvs_trial_netgen_status": resistor_variant_summary.get(
                "best_hybrid_mos_passive_lvs_trial_netgen_status"
            ),
            "passive_resistor_variant_best_hybrid_mos_passive_lvs_trial_result_summary": resistor_variant_summary.get(
                "best_hybrid_mos_passive_lvs_trial_result_summary"
            ),
            "passive_resistor_variant_best_all_source_passives_have_candidate": resistor_variant_summary.get(
                "best_all_source_passives_have_candidate"
            ),
            "passive_resistor_variant_best_missing_source_passive_instances": resistor_variant_summary.get(
                "best_missing_source_passive_instances"
            ),
            "passive_lvs_evidence_status": resistor_variant_summary.get(
                "formal_passive_lvs_evidence_status"
            ),
            "passive_lvs_evidence_pass": resistor_variant_summary.get(
                "formal_passive_lvs_evidence_pass"
            ),
            "passive_lvs_evidence_scope": resistor_variant_summary.get(
                "formal_passive_lvs_evidence_scope"
            ),
            "passive_lvs_evidence_failed_requirements": resistor_variant_summary.get(
                "formal_passive_lvs_evidence_failed_requirements"
            ),
            "native_passive_capability_probe_status": resistor_variant_summary.get(
                "native_passive_capability_probe_status"
            ),
            "native_passive_capability_source_model_native_status": resistor_variant_summary.get(
                "native_passive_capability_source_model_native_status"
            ),
            "native_passive_capability_direct_source_model_support": resistor_variant_summary.get(
                "native_passive_capability_direct_source_model_support"
            ),
            "native_passive_capability_unsupported_source_models": resistor_variant_summary.get(
                "native_passive_capability_unsupported_source_models"
            ),
            "native_passive_capability_retarget_available": resistor_variant_summary.get(
                "native_passive_capability_retarget_available"
            ),
            "native_passive_capability_retarget_map": resistor_variant_summary.get(
                "native_passive_capability_retarget_map"
            ),
            "native_passive_capability_requires_geometry_replacement": resistor_variant_summary.get(
                "native_passive_capability_requires_geometry_replacement"
            ),
            "native_passive_capability_can_fix_current_gds_by_layer_remap_only": resistor_variant_summary.get(
                "native_passive_capability_can_fix_current_gds_by_layer_remap_only"
            ),
            "native_passive_capability_device_generation_source_status": resistor_variant_summary.get(
                "native_passive_capability_device_generation_source_status"
            ),
            "native_passive_retarget_trial_status": resistor_variant_summary.get(
                "native_passive_retarget_trial_status"
            ),
            "native_resistor_chain_status": resistor_variant_summary.get("native_resistor_chain_status"),
            "native_resistor_chain_device_count": resistor_variant_summary.get(
                "native_resistor_chain_device_count"
            ),
            "native_resistor_chain_model": resistor_variant_summary.get("native_resistor_chain_model"),
            "native_resistor_chain_netgen_status": resistor_variant_summary.get(
                "native_resistor_chain_netgen_status"
            ),
            "native_capacitor_device_recognition_status": resistor_variant_summary.get(
                "native_capacitor_device_recognition_status"
            ),
            "native_capacitor_devices": resistor_variant_summary.get("native_capacitor_devices"),
            "native_passive_device_recognition_status": resistor_variant_summary.get(
                "native_passive_device_recognition_status"
            ),
            "native_passive_device_recognition_claimed": resistor_variant_summary.get(
                "native_passive_device_recognition_claimed"
            ),
            "native_passive_device_recognition_missing_instances": resistor_variant_summary.get(
                "native_passive_device_recognition_missing_instances"
            ),
            "native_passive_device_recognition_blockers": resistor_variant_summary.get(
                "native_passive_device_recognition_blockers"
            ),
            "native_passive_retarget_missing_native_source_passive_instances": resistor_variant_summary.get(
                "native_passive_retarget_missing_native_source_passive_instances"
            ),
            "native_passive_retarget_full_native_passive_lvs_ready": resistor_variant_summary.get(
                "native_passive_retarget_full_native_passive_lvs_ready"
            ),
            "native_passive_retarget_full_native_passive_lvs_proven": resistor_variant_summary.get(
                "native_passive_retarget_full_native_passive_lvs_proven"
            ),
            "native_cap_full_gds_trial_status": resistor_variant_summary.get(
                "native_cap_full_gds_trial_status"
            ),
            "native_cap_full_gds_trial_summary_json": resistor_variant_summary.get(
                "native_cap_full_gds_trial_summary_json"
            ),
            "native_cap_replacement_status": resistor_variant_summary.get("native_cap_replacement_status"),
            "native_cap_replacement_cell_name": resistor_variant_summary.get(
                "native_cap_replacement_cell_name"
            ),
            "native_cap_replacement_terminal_bridge_status": resistor_variant_summary.get(
                "native_cap_replacement_terminal_bridge_status"
            ),
            "native_cap_replacement_top_gds_merge_status": resistor_variant_summary.get(
                "native_cap_replacement_top_gds_merge_status"
            ),
            "native_cap_replacement_bridge_mode": resistor_variant_summary.get(
                "native_cap_replacement_bridge_mode"
            ),
            "native_cap_replacement_full_gds": resistor_variant_summary.get(
                "native_cap_replacement_full_gds"
            ),
            "native_cap_replacement_extract_status": resistor_variant_summary.get(
                "native_cap_replacement_extract_status"
            ),
            "native_cap_replacement_drc_status": resistor_variant_summary.get(
                "native_cap_replacement_drc_status"
            ),
            "native_cap_replacement_drc_count": resistor_variant_summary.get(
                "native_cap_replacement_drc_count"
            ),
            "native_cap_replacement_native_passive_netgen_status": resistor_variant_summary.get(
                "native_cap_replacement_native_passive_netgen_status"
            ),
            "native_cap_replacement_native_capacitor_device_count": resistor_variant_summary.get(
                "native_cap_replacement_native_capacitor_device_count"
            ),
            "full_passive_inclusive_gds_lvs_proven": resistor_variant_summary.get(
                "full_passive_inclusive_gds_lvs_proven"
            ),
            "full_passive_inclusive_gds_native_lvs_status": resistor_variant_summary.get(
                "full_passive_inclusive_gds_native_lvs_status"
            ),
            "passive_netgen_available": netgen_lvs_available,
            "passive_netgen_lvs_available": netgen_lvs_available,
            "passive_probe_mode": "existing_pinned_gds_extraction",
            "original_probe_failed_stage": "magical_place_route",
            "magic_extract_returncode": magic_result.returncode,
        }
        artifacts = {
            "out_dir": str(probe_dir),
            "input_pinned_gds": str(pinned_gds),
            "remapped_pinned_gds": str(remapped_gds),
            "remap_report": str(remap_report),
            "magic_extract_log": str(magic_log),
            "raw_extracted_netlist": str(raw_extracted),
            "passive_integrity_report": str(passive_integrity_report),
            "passive_gds_structure_diagnostic": str(gds_diagnostic.get("report")),
            "passive_gds_structure_summary_json": str(gds_diagnostic.get("summary_json")),
            "passive_gds_structure_log": str(gds_diagnostic.get("log")),
            "passive_identity_reconstruction_report": str(identity_diagnostic.get("report")),
            "passive_identity_reconstruction_summary_json": str(identity_diagnostic.get("summary_json")),
            "passive_identity_reconstruction_log": str(identity_diagnostic.get("log")),
            "passive_lvs_preparation_diagnostic": str(lvs_diagnostic.get("report")),
            "passive_lvs_preparation_log": str(lvs_diagnostic.get("log")),
            "original_summary": str(original_summary),
            "original_run_log": str(original_run_log),
        }
        if exclusion_probe_summary_path.is_file():
            artifacts["passive_remap_exclusion_probe_summary_json"] = str(exclusion_probe_summary_path)
        if (exclusion_probe_dir / "passive_remap_exclusion_probe_report.md").is_file():
            artifacts["passive_remap_exclusion_probe_report"] = str(
                exclusion_probe_dir / "passive_remap_exclusion_probe_report.md"
            )
        if exclusion_group_probe_summary_path.is_file():
            artifacts["passive_remap_exclusion_group_probe_summary_json"] = str(
                exclusion_group_probe_summary_path
            )
        if (exclusion_probe_dir / "passive_remap_exclusion_group_probe_report.md").is_file():
            artifacts["passive_remap_exclusion_group_probe_report"] = str(
                exclusion_probe_dir / "passive_remap_exclusion_group_probe_report.md"
            )
        if baseline_probe_summary_path.is_file():
            artifacts["passive_remap_baseline_probe_summary_json"] = str(baseline_probe_summary_path)
        if (exclusion_probe_dir / "passive_remap_baseline_probe_report.md").is_file():
            artifacts["passive_remap_baseline_probe_report"] = str(
                exclusion_probe_dir / "passive_remap_baseline_probe_report.md"
            )
        if strip_margin_probe_summary_path.is_file():
            artifacts["passive_geometry_strip_margin_probe_summary_json"] = str(
                strip_margin_probe_summary_path
            )
        if (strip_probe_dir / "passive_geometry_strip_margin_probe_report.md").is_file():
            artifacts["passive_geometry_strip_margin_probe_report"] = str(
                strip_probe_dir / "passive_geometry_strip_margin_probe_report.md"
            )
        if crossing_repair_probe_summary_path.is_file():
            artifacts["passive_geometry_crossing_repair_probe_summary_json"] = str(
                crossing_repair_probe_summary_path
            )
        if (strip_probe_dir / "passive_geometry_crossing_repair_probe_report.md").is_file():
            artifacts["passive_geometry_crossing_repair_probe_report"] = str(
                strip_probe_dir / "passive_geometry_crossing_repair_probe_report.md"
            )
        for key, value in label_probe.get("artifacts", {}).items():
            artifacts[key] = str(value)
        for key, value in resistor_variant_probe.get("artifacts", {}).items():
            artifacts[key] = str(value)
        if resistor_variant_summary.get("best_abstraction_packet_json"):
            artifacts["passive_resistor_variant_best_abstraction_packet_json"] = str(
                resistor_variant_summary.get("best_abstraction_packet_json")
            )
        if resistor_variant_summary.get("best_abstraction_candidates"):
            artifacts["passive_resistor_variant_best_abstraction_candidates"] = str(
                resistor_variant_summary.get("best_abstraction_candidates")
            )
        if resistor_variant_summary.get("best_abstraction_packet_verification_json"):
            artifacts["passive_resistor_variant_best_abstraction_packet_verification_json"] = str(
                resistor_variant_summary.get("best_abstraction_packet_verification_json")
            )
        if resistor_variant_summary.get("best_abstraction_source_passive_abs_netlist"):
            artifacts["passive_resistor_variant_best_abstraction_source_passive_abs_netlist"] = str(
                resistor_variant_summary.get("best_abstraction_source_passive_abs_netlist")
            )
        if resistor_variant_summary.get("best_abstraction_candidate_passive_abs_netlist"):
            artifacts["passive_resistor_variant_best_abstraction_candidate_passive_abs_netlist"] = str(
                resistor_variant_summary.get("best_abstraction_candidate_passive_abs_netlist")
            )
        if resistor_variant_summary.get("best_passive_abs_lvs_result_summary"):
            artifacts["passive_resistor_variant_best_passive_abs_lvs_result_summary"] = str(
                resistor_variant_summary.get("best_passive_abs_lvs_result_summary")
            )
        if resistor_variant_summary.get("best_passive_abs_netgen_report"):
            artifacts["passive_resistor_variant_best_passive_abs_netgen_report"] = str(
                resistor_variant_summary.get("best_passive_abs_netgen_report")
            )
        if resistor_variant_summary.get("best_passive_aware_lvs_trial_result_summary"):
            artifacts["passive_resistor_variant_best_passive_aware_lvs_trial_result_summary"] = str(
                resistor_variant_summary.get("best_passive_aware_lvs_trial_result_summary")
            )
        if resistor_variant_summary.get("best_passive_aware_mos_connectivity_summary_json"):
            artifacts["passive_resistor_variant_best_passive_aware_mos_connectivity_summary_json"] = str(
                resistor_variant_summary.get("best_passive_aware_mos_connectivity_summary_json")
            )
        if resistor_variant_summary.get("best_passive_aware_mos_connectivity_report"):
            artifacts["passive_resistor_variant_best_passive_aware_mos_connectivity_report"] = str(
                resistor_variant_summary.get("best_passive_aware_mos_connectivity_report")
            )
        if resistor_variant_summary.get("best_formal_passive_mos_repair_lvs_trial_result_summary"):
            artifacts["passive_resistor_variant_best_formal_passive_mos_repair_lvs_trial_result_summary"] = str(
                resistor_variant_summary.get(
                    "best_formal_passive_mos_repair_lvs_trial_result_summary"
                )
            )
        if resistor_variant_summary.get("best_route_bridge_summary_json"):
            artifacts["passive_resistor_variant_best_route_bridge_summary_json"] = str(
                resistor_variant_summary.get("best_route_bridge_summary_json")
            )
        if resistor_variant_summary.get("best_route_bridge_trial_summary_json"):
            artifacts["passive_resistor_variant_best_route_bridge_trial_summary_json"] = str(
                resistor_variant_summary.get("best_route_bridge_trial_summary_json")
            )
        if resistor_variant_summary.get("best_route_bridge_formal_passive_lvs_result_summary"):
            artifacts["passive_resistor_variant_best_route_bridge_formal_passive_lvs_result_summary"] = str(
                resistor_variant_summary.get("best_route_bridge_formal_passive_lvs_result_summary")
            )
        if resistor_variant_summary.get("best_hybrid_mos_passive_lvs_trial_result_summary"):
            artifacts["passive_resistor_variant_best_hybrid_mos_passive_lvs_trial_result_summary"] = str(
                resistor_variant_summary.get("best_hybrid_mos_passive_lvs_trial_result_summary")
            )
        passive_evidence_classification = classify_passive_aware_evidence(
            resistor_variant_summary=resistor_variant_summary,
            fallback_reason=interpretation,
            fallback_scope=self.config.verification_scope,
        )
        metrics.update(
            {
                "passive_aware_status": passive_evidence_classification["passive_aware_status"],
                "passive_aware_verification_scope_detail": passive_evidence_classification[
                    "verification_scope_detail"
                ],
                "formal_passive_abstraction_ready": passive_evidence_classification[
                    "formal_passive_abstraction_ready"
                ],
                "formal_passive_only_lvs_match": passive_evidence_classification[
                    "formal_passive_only_lvs_match"
                ],
                "hybrid_mos_reference_passive_lvs_match": passive_evidence_classification[
                    "hybrid_mos_reference_passive_lvs_match"
                ],
                "full_passive_inclusive_gds_lvs_proven": passive_evidence_classification[
                    "full_passive_inclusive_gds_lvs_proven"
                ],
            }
        )
        messages = [passive_evidence_classification["reason"]]
        if passive_evidence_classification["reason"] != interpretation:
            messages.append(interpretation)
        return EvidencePacket(
            candidate_id=compiled.candidate_id,
            stage="passive_aware_lvs",
            fidelity="E2P",
            status=passive_evidence_classification["packet_status"],
            verification_scope=passive_evidence_classification["verification_scope"],
            metrics=metrics,
            physical_feedback={
                "passive_aware_requested": True,
                "passive_aware_status": passive_evidence_classification["passive_aware_status"],
                "passive_aware_reason": passive_evidence_classification["reason"],
                "passive_aware_verification_scope_detail": passive_evidence_classification[
                    "verification_scope_detail"
                ],
                "formal_passive_abstraction_ready": passive_evidence_classification[
                    "formal_passive_abstraction_ready"
                ],
                "formal_passive_only_lvs_match": passive_evidence_classification[
                    "formal_passive_only_lvs_match"
                ],
                "hybrid_mos_reference_passive_lvs_match": passive_evidence_classification[
                    "hybrid_mos_reference_passive_lvs_match"
                ],
                "full_passive_inclusive_gds_lvs_proven": passive_evidence_classification[
                    "full_passive_inclusive_gds_lvs_proven"
                ],
                "all_source_passives_have_candidate": passive_evidence_classification[
                    "all_source_passives_have_candidate"
                ],
                "passive_lvs_evidence_status": resistor_variant_summary.get(
                    "formal_passive_lvs_evidence_status"
                ),
                "passive_lvs_evidence_pass": resistor_variant_summary.get(
                    "formal_passive_lvs_evidence_pass"
                ),
                "passive_lvs_evidence_scope": resistor_variant_summary.get(
                    "formal_passive_lvs_evidence_scope"
                ),
                "passive_lvs_evidence_failed_requirements": resistor_variant_summary.get(
                    "formal_passive_lvs_evidence_failed_requirements"
                ),
                "passive_probe_mode": "existing_pinned_gds_extraction",
                "source_passive_devices": source_passives,
                "generated_passive_gds": len(generated_passive_gds),
                "extracted_physical_passive_devices": len(physical_passives),
                "extracted_physical_passive_models": physical_model_counts,
                "extracted_intentional_passive_devices": intentional_passives,
                "passive_tbd_layers": tbd_layers,
                "magic_unknown_layers": unknown_layers,
                "magic_port_shorts": magic_port_shorts,
                "magic_supply_short_present": magic_supply_short_present,
                "magic_extract_returncode": magic_result.returncode,
                "passive_remap_exclusion_probe": exclusion_probe_summary,
                "passive_remap_exclusion_group_probe": exclusion_group_probe_summary,
                "passive_remap_baseline_probe": baseline_probe_summary,
                "passive_geometry_strip_margin_probe": strip_margin_probe_summary,
                "passive_geometry_crossing_repair_probe": crossing_repair_probe_summary,
                "passive_gds_structure_returncode": gds_diagnostic.get("returncode"),
                "passive_gds_top_text_count": top_gds_summary.get("text_count"),
                "passive_gds_top_ref_count": top_gds_summary.get("ref_count"),
                "passive_gds_source_instance_names_present_count": gds_summary.get(
                    "source_passive_instance_names_present_count"
                ),
                "passive_gds_source_terminal_names_present_count": gds_summary.get(
                    "source_passive_terminal_names_present_count"
                ),
                "passive_gds_generated_passive_gds_present_count": gds_summary.get(
                    "generated_passive_gds_present_count"
                ),
                "passive_identity_reconstruction_returncode": identity_diagnostic.get("returncode"),
                "passive_identity_status": identity_summary.get("status"),
                "passive_identity_exact_route_matches": identity_summary.get(
                    "source_passive_pin_exact_route_matches"
                ),
                "passive_identity_missing_route_matches": identity_summary.get(
                    "source_passive_pin_missing_route_matches"
                ),
                "passive_identity_pins_with_geometry": identity_summary.get("source_passive_pins_with_geometry"),
                "passive_identity_pins_without_geometry": identity_summary.get("source_passive_pins_without_geometry"),
                "passive_identity_label_injection_candidates": identity_summary.get(
                    "source_passive_label_injection_candidates"
                ),
                "passive_lvs_preparation_returncode": lvs_diagnostic.get("returncode"),
                "passive_abstraction_status": lvs_diagnostic.get("passive_abstraction_status"),
                "passive_identity_label_probe_status": label_probe.get("status"),
                "passive_identity_label_probe_reason": label_probe.get("reason"),
                "passive_identity_label_injection_returncode": label_probe.get("injection_returncode"),
                "passive_identity_label_magic_extract_returncode": label_probe.get("magic_extract_returncode"),
                "passive_identity_label_recovery": label_terminal_summary,
                "passive_identity_label_abstraction_status": label_lvs_diagnostic.get(
                    "passive_abstraction_status"
                ),
                "passive_identity_label_abstraction_readiness": label_abstraction_summary,
                "passive_identity_label_abstraction_packet": label_abstraction_packet,
                "passive_resistor_variant_probe": resistor_variant_summary,
                "passive_formal_mos_repair_renames": resistor_variant_summary.get(
                    "best_formal_passive_mos_repair_renames"
                ),
                "passive_formal_mos_repair_signoff_eligible": resistor_variant_summary.get(
                    "best_formal_passive_mos_repair_signoff_eligible"
                ),
                "passive_formal_mos_repair_lvs_status": resistor_variant_summary.get(
                    "best_formal_passive_mos_repair_lvs_trial_netgen_status"
                ),
                "passive_netgen_available": netgen_lvs_available,
                "passive_netgen_lvs_available": netgen_lvs_available,
            },
            artifacts=artifacts,
            messages=messages,
        )

    def _run_passive_identity_label_probe(
        self,
        *,
        compiled: CompiledCandidate,
        probe_dir: Path,
        remapped_gds: Path,
        magic_cell: str,
        identity_diagnostic: dict[str, Any],
        source_instances: list[dict[str, Any]],
        enabled: bool,
    ) -> dict[str, Any]:
        label_probe_artifacts: dict[str, str] = {}
        if not enabled:
            return {"status": "skipped", "reason": "passive identity label probe disabled", "artifacts": label_probe_artifacts}
        identity_json = identity_diagnostic.get("summary_json")
        identity_json_path = Path(identity_json) if identity_json else probe_dir / "passive_identity_reconstruction_summary.json"
        if not remapped_gds.is_file() or not identity_json_path.is_file():
            return {
                "status": "skipped",
                "reason": "missing remapped GDS or passive identity summary",
                "artifacts": label_probe_artifacts,
            }

        labelled_gds = probe_dir / f"{self.config.top_cell}.sky130.experimental_passive.identity_labels.gds"
        injection_report = probe_dir / "passive_identity_label_injection_report.md"
        injection_log = probe_dir / "passive_identity_label_injection.log"
        injection_cmd = [
            sys.executable,
            str(self.config.repo_root / "tools" / "sky130_adapter" / "add_passive_identity_labels_to_gds.py"),
            "--input-gds",
            str(remapped_gds),
            "--identity-json",
            str(identity_json_path),
            "--output-gds",
            str(labelled_gds),
            "--report",
            str(injection_report),
            "--cell",
            magic_cell,
        ]
        injection_result = subprocess.run(
            injection_cmd,
            cwd=self.config.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        injection_log.write_text(injection_result.stdout or "", encoding="utf-8")
        label_probe_artifacts.update(
            {
                "passive_identity_label_injection_log": str(injection_log),
                "passive_identity_label_injection_report": str(injection_report),
                "passive_identity_labelled_gds": str(labelled_gds),
            }
        )
        if injection_result.returncode != 0 or not labelled_gds.is_file():
            return {
                "status": "fail",
                "reason": "passive identity label injection failed",
                "injection_returncode": injection_result.returncode,
                "artifacts": label_probe_artifacts,
            }

        labelled_gds_diagnostic = run_gds_structure_diagnostic(
            repo_root=self.config.repo_root,
            gds_path=labelled_gds,
            source_netlist=compiled.netlist_path,
            case_dir=compiled.case_dir,
            out_dir=probe_dir,
            top_cell=self.config.top_cell,
            report_stem="passive_identity_labelled_gds_structure",
        )
        magic_tcl = probe_dir / "magic_extract_identity_labels.tcl"
        magic_log = probe_dir / "magic_extract_identity_labels.log"
        raw_extracted = probe_dir / f"{self.config.top_cell}_identity_labels_extracted.spice"
        ext_copy = probe_dir / f"{self.config.top_cell}_identity_labels_flat.ext"
        magic_tcl.write_text(
            "\n".join(
                [
                    'puts "SKY130_PASSIVE_IDENTITY_LABEL_PROBE: reading identity-labelled passive GDS"',
                    f"gds read {_repo_relative(self.config.repo_root, labelled_gds)}",
                    f"if {{[catch {{load {magic_cell}}} load_error]}} {{",
                    f'    puts stderr "ERROR: failed to load {magic_cell}"',
                    "    puts stderr $load_error",
                    "    quit -noprompt",
                    "}",
                    "select top cell",
                    "extract all",
                    "ext2spice lvs",
                    "ext2spice cthresh 0",
                    "ext2spice rthresh 0",
                    "ext2spice",
                    "quit -noprompt",
                    "",
                ]
            ),
            encoding="ascii",
        )
        magic_result = subprocess.run(
            self._magic_extract_command(magic_tcl, magic_log, raw_extracted, ext_copy, magic_cell),
            cwd=self.config.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        magic_wrapper_log = probe_dir / "magic_extract_identity_labels.wrapper.log"
        magic_wrapper_log.write_text(magic_result.stdout or "", encoding="utf-8")
        extracted_devices = extracted_physical_passive_devices(raw_extracted)
        terminal_summary = passive_terminal_recovery_summary(
            source_instances=source_instances,
            extracted_devices=extracted_devices,
            magic_log=magic_log,
        )
        terminal_report = probe_dir / "passive_identity_label_terminal_recovery_report.md"
        write_passive_terminal_recovery_report(terminal_report, terminal_summary, extracted_devices)
        lvs_diagnostic = run_lvs_preparation_diagnostic(
            repo_root=self.config.repo_root,
            source_netlist=compiled.netlist_path,
            extracted_netlist=raw_extracted,
            out_dir=probe_dir,
            top_cell=self.config.top_cell,
            report_stem="passive_identity_label_lvs_preparation",
            diagnostic_dir_name="identity_label_lvs_prepare_diagnostic",
        )
        abstraction_diagnostic = run_passive_abstraction_readiness_diagnostic(
            repo_root=self.config.repo_root,
            source_netlist=compiled.netlist_path,
            extracted_netlist=raw_extracted,
            out_dir=probe_dir,
            magic_log=magic_log,
            ext_file=ext_copy,
            identity_json=identity_json_path,
        )
        abstraction_packet_verification = run_passive_abstraction_packet_verification(
            repo_root=self.config.repo_root,
            source_netlist=compiled.netlist_path,
            packet_json=Path(abstraction_diagnostic.get("packet_json", "")),
            report=probe_dir / "passive_identity_label_abstraction_packet_verification_report.md",
            summary_json=probe_dir / "passive_identity_label_abstraction_packet_verification_summary.json",
            log=probe_dir / "passive_identity_label_abstraction_packet_verification.log",
            top_cell=self.config.top_cell,
            source_abstraction_netlist=probe_dir / "passive_identity_label_source_passive_abs.spice",
            candidate_abstraction_netlist=probe_dir / "passive_identity_label_candidate_passive_abs.spice",
        )
        label_probe_artifacts.update(
            {
                "passive_identity_label_magic_tcl": str(magic_tcl),
                "passive_identity_label_magic_extract_log": str(magic_log),
                "passive_identity_label_magic_extract_wrapper_log": str(magic_wrapper_log),
                "passive_identity_label_extracted_netlist": str(raw_extracted),
                "passive_identity_label_ext": str(ext_copy),
                "passive_identity_label_terminal_recovery_report": str(terminal_report),
                "passive_identity_labelled_gds_structure_diagnostic": str(labelled_gds_diagnostic.get("report")),
                "passive_identity_labelled_gds_structure_summary_json": str(
                    labelled_gds_diagnostic.get("summary_json")
                ),
                "passive_identity_labelled_gds_structure_log": str(labelled_gds_diagnostic.get("log")),
                "passive_identity_label_lvs_preparation_diagnostic": str(lvs_diagnostic.get("report")),
                "passive_identity_label_lvs_preparation_log": str(lvs_diagnostic.get("log")),
                "passive_identity_label_abstraction_readiness_report": str(abstraction_diagnostic.get("report")),
                "passive_identity_label_abstraction_readiness_summary_json": str(
                    abstraction_diagnostic.get("summary_json")
                ),
                "passive_identity_label_abstraction_candidates": str(abstraction_diagnostic.get("candidate_netlist")),
                "passive_identity_label_abstraction_packet_json": str(
                    abstraction_diagnostic.get("packet_json")
                ),
                "passive_identity_label_abstraction_packet_verification_report": str(
                    abstraction_packet_verification.get("report")
                ),
                "passive_identity_label_abstraction_packet_verification_summary_json": str(
                    abstraction_packet_verification.get("summary_json")
                ),
                "passive_identity_label_abstraction_packet_verification_log": str(
                    abstraction_packet_verification.get("log")
                ),
                "passive_identity_label_source_passive_abs_netlist": str(
                    abstraction_packet_verification.get("source_abstraction_netlist")
                ),
                "passive_identity_label_candidate_passive_abs_netlist": str(
                    abstraction_packet_verification.get("candidate_abstraction_netlist")
                ),
                "passive_identity_label_abstraction_readiness_log": str(abstraction_diagnostic.get("log")),
            }
        )
        extraction_passed = magic_result.returncode == 0 and raw_extracted.is_file()
        return {
            "status": "pass" if extraction_passed else "fail",
            "reason": None if extraction_passed else "passive identity label Magic extraction failed",
            "injection_returncode": injection_result.returncode,
            "magic_extract_returncode": magic_result.returncode,
            "gds_diagnostic": labelled_gds_diagnostic,
            "lvs_diagnostic": lvs_diagnostic,
            "abstraction_diagnostic": abstraction_diagnostic,
            "abstraction_packet_verification": abstraction_packet_verification,
            "terminal_recovery_summary": terminal_summary,
            "artifacts": label_probe_artifacts,
        }

    def _run_resistor_remap_variant_probes(
        self,
        *,
        compiled: CompiledCandidate,
        probe_dir: Path,
        remapped_gds: Path,
        magic_cell: str,
        identity_diagnostic: dict[str, Any],
        enabled: bool,
    ) -> dict[str, Any]:
        variant_dir = probe_dir / "resistor_remap_variants"
        variant_dir.mkdir(parents=True, exist_ok=True)
        summary_json = variant_dir / "resistor_remap_variant_probe_summary.json"
        if not enabled:
            summary = {
                "status": "skipped",
                "reason": "resistor remap variant probe disabled",
                "variant_count": 0,
                "successful_variant_count": 0,
                "results": [],
            }
            summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return {"status": "skipped", "summary": summary, "summary_json": summary_json, "artifacts": {}}

        identity_json = identity_diagnostic.get("summary_json")
        identity_json_path = Path(identity_json) if identity_json else probe_dir / "passive_identity_reconstruction_summary.json"
        if not remapped_gds.is_file() or not identity_json_path.is_file():
            summary = {
                "status": "skipped",
                "reason": "missing remapped GDS or passive identity summary",
                "variant_count": 0,
                "successful_variant_count": 0,
                "results": [],
            }
            summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return {"status": "skipped", "summary": summary, "summary_json": summary_json, "artifacts": {}}

        results: list[dict[str, Any]] = []
        artifacts: dict[str, str] = {"passive_resistor_variant_probe_summary_json": str(summary_json)}
        for variant, map_text in RESISTOR_REMAP_VARIANT_MAPS.items():
            map_path = variant_dir / f"{variant}_map.yaml"
            variant_gds = variant_dir / f"{self.config.top_cell}.{variant}.gds"
            remap_report = variant_dir / f"{variant}_remap_report.md"
            remap_log = variant_dir / f"{variant}_remap.log"
            labelled_gds = variant_dir / f"{self.config.top_cell}.{variant}.identity_labels.gds"
            label_report = variant_dir / f"{variant}_label_injection_report.md"
            label_log = variant_dir / f"{variant}_label_injection.log"
            magic_tcl = variant_dir / f"{variant}_magic_extract.tcl"
            magic_log = variant_dir / f"{variant}_magic_extract.log"
            raw_extracted = variant_dir / f"{self.config.top_cell}.{variant}_extracted.spice"
            ext_copy = variant_dir / f"{self.config.top_cell}.{variant}_flat.ext"
            abstraction_report = variant_dir / f"{variant}_abstraction_report.md"
            abstraction_summary_json = variant_dir / f"{variant}_abstraction_summary.json"
            abstraction_candidates = variant_dir / f"{variant}_abstraction_candidates.spice"
            abstraction_packet_json = variant_dir / f"{variant}_abstraction_packet.json"
            abstraction_packet_verification_report = (
                variant_dir / f"{variant}_abstraction_packet_verification_report.md"
            )
            abstraction_packet_verification_summary_json = (
                variant_dir / f"{variant}_abstraction_packet_verification_summary.json"
            )
            abstraction_packet_verification_log = (
                variant_dir / f"{variant}_abstraction_packet_verification.log"
            )
            abstraction_source_abs_netlist = variant_dir / f"{variant}_source_passive_abs.spice"
            abstraction_candidate_abs_netlist = variant_dir / f"{variant}_candidate_passive_abs.spice"
            passive_abs_netgen_report = variant_dir / f"{variant}_passive_abs_netgen_report.out"
            passive_abs_netgen_log = variant_dir / f"{variant}_passive_abs_netgen.log"
            passive_abs_lvs_result_summary = variant_dir / f"{variant}_passive_abs_lvs_result_summary.md"
            passive_aware_trial_dir = variant_dir / f"{variant}_passive_aware_lvs_trial"
            passive_aware_trial_report = variant_dir / f"{variant}_passive_aware_lvs_trial_report.md"
            passive_aware_trial_summary_json = variant_dir / f"{variant}_passive_aware_lvs_trial_summary.json"
            passive_aware_trial_log = variant_dir / f"{variant}_passive_aware_lvs_trial.log"
            passive_aware_netgen_report = variant_dir / f"{variant}_passive_aware_netgen_report.out"
            passive_aware_netgen_log = variant_dir / f"{variant}_passive_aware_netgen.log"
            passive_aware_lvs_result_summary = variant_dir / f"{variant}_passive_aware_lvs_result_summary.md"
            passive_aware_mos_connectivity_report = (
                variant_dir / f"{variant}_passive_aware_mos_connectivity_report.md"
            )
            passive_aware_mos_connectivity_summary_json = (
                variant_dir / f"{variant}_passive_aware_mos_connectivity_summary.json"
            )
            passive_aware_mos_connectivity_log = (
                variant_dir / f"{variant}_passive_aware_mos_connectivity.log"
            )
            mos_repair_trial_dir = variant_dir / f"{variant}_formal_passive_mos_repair_lvs_trial"
            mos_repair_trial_report = variant_dir / f"{variant}_formal_passive_mos_repair_lvs_trial_report.md"
            mos_repair_trial_summary_json = (
                variant_dir / f"{variant}_formal_passive_mos_repair_lvs_trial_summary.json"
            )
            mos_repair_trial_log = variant_dir / f"{variant}_formal_passive_mos_repair_lvs_trial.log"
            mos_repair_netgen_report = variant_dir / f"{variant}_formal_passive_mos_repair_netgen_report.out"
            mos_repair_netgen_log = variant_dir / f"{variant}_formal_passive_mos_repair_netgen.log"
            mos_repair_lvs_result_summary = (
                variant_dir / f"{variant}_formal_passive_mos_repair_lvs_result_summary.md"
            )
            hybrid_trial_dir = variant_dir / f"{variant}_hybrid_mos_passive_lvs_trial"
            hybrid_trial_report = variant_dir / f"{variant}_hybrid_mos_passive_lvs_trial_report.md"
            hybrid_trial_summary_json = variant_dir / f"{variant}_hybrid_mos_passive_lvs_trial_summary.json"
            hybrid_trial_log = variant_dir / f"{variant}_hybrid_mos_passive_lvs_trial.log"
            hybrid_netgen_report = variant_dir / f"{variant}_hybrid_mos_passive_netgen_report.out"
            hybrid_netgen_log = variant_dir / f"{variant}_hybrid_mos_passive_netgen.log"
            hybrid_lvs_result_summary = variant_dir / f"{variant}_hybrid_mos_passive_lvs_result_summary.md"
            abstraction_log = variant_dir / f"{variant}_abstraction.log"

            map_path.write_text(map_text, encoding="ascii")
            remap_cmd = [
                sys.executable,
                str(self.config.repo_root / "tools" / "sky130_adapter" / "remap_gds_to_sky130.py"),
                "--input-gds",
                str(remapped_gds),
                "--output-gds",
                str(variant_gds),
                "--export-map",
                str(map_path),
                "--report",
                str(remap_report),
                "--allow-experimental",
            ]
            remap_result = subprocess.run(
                remap_cmd,
                cwd=self.config.repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            remap_log.write_text(remap_result.stdout or "", encoding="utf-8")
            result: dict[str, Any] = {
                "variant": variant,
                "map": str(map_path),
                "remap_returncode": remap_result.returncode,
                "remap_report": str(remap_report),
                "remap_log": str(remap_log),
            }
            if remap_result.returncode != 0 or not variant_gds.is_file():
                result["status"] = "remap_failed"
                results.append(result)
                continue

            injection_cmd = [
                sys.executable,
                str(self.config.repo_root / "tools" / "sky130_adapter" / "add_passive_identity_labels_to_gds.py"),
                "--input-gds",
                str(variant_gds),
                "--identity-json",
                str(identity_json_path),
                "--output-gds",
                str(labelled_gds),
                "--report",
                str(label_report),
                "--cell",
                magic_cell,
            ]
            injection_result = subprocess.run(
                injection_cmd,
                cwd=self.config.repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            label_log.write_text(injection_result.stdout or "", encoding="utf-8")
            result.update(
                {
                    "label_injection_returncode": injection_result.returncode,
                    "labelled_gds": str(labelled_gds),
                    "label_injection_report": str(label_report),
                    "label_injection_log": str(label_log),
                }
            )
            if injection_result.returncode != 0 or not labelled_gds.is_file():
                result["status"] = "label_injection_failed"
                results.append(result)
                continue

            magic_tcl.write_text(
                "\n".join(
                    [
                        f'puts "SKY130_PASSIVE_RESISTOR_REMAP_VARIANT: extracting {variant}"',
                        f"gds read {_repo_relative(self.config.repo_root, labelled_gds)}",
                        f"if {{[catch {{load {magic_cell}}} load_error]}} {{",
                        f'    puts stderr "ERROR: failed to load {magic_cell}"',
                        "    puts stderr $load_error",
                        "    quit -noprompt",
                        "}",
                        "select top cell",
                        "extract all",
                        "ext2spice lvs",
                        "ext2spice cthresh 0",
                        "ext2spice rthresh 0",
                        "ext2spice",
                        "quit -noprompt",
                        "",
                    ]
                ),
                encoding="ascii",
            )
            magic_result = subprocess.run(
                self._magic_extract_command(magic_tcl, magic_log, raw_extracted, ext_copy, magic_cell),
                cwd=self.config.repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            magic_wrapper_log = variant_dir / f"{variant}_magic_extract.wrapper.log"
            magic_wrapper_log.write_text(magic_result.stdout or "", encoding="utf-8")
            variant_magic_port_shorts = parse_magic_port_shorts(magic_log)
            ports = self.config.data.get("ports", {})
            variant_magic_supply_short_present = has_magic_port_short(
                variant_magic_port_shorts,
                str(ports.get("vdd", "vdda")),
                str(ports.get("vss", "gnda")),
            )
            result.update(
                {
                    "magic_extract_returncode": magic_result.returncode,
                    "magic_tcl": str(magic_tcl),
                    "magic_extract_log": str(magic_log),
                    "magic_extract_wrapper_log": str(magic_wrapper_log),
                    "magic_port_shorts": variant_magic_port_shorts,
                    "magic_port_short_count": len(variant_magic_port_shorts),
                    "magic_supply_short_present": variant_magic_supply_short_present,
                    "extracted_netlist": str(raw_extracted),
                    "ext": str(ext_copy),
                }
            )
            if magic_result.returncode != 0 or not raw_extracted.is_file():
                result["status"] = "magic_extract_failed"
                results.append(result)
                continue

            abstraction_cmd = [
                sys.executable,
                str(self.config.repo_root / "tools" / "sky130_adapter" / "analyze_passive_abstraction.py"),
                "--source-netlist",
                str(compiled.netlist_path),
                "--extracted-netlist",
                str(raw_extracted),
                "--magic-log",
                str(magic_log),
                "--ext-file",
                str(ext_copy),
                "--identity-json",
                str(identity_json_path),
                "--report",
                str(abstraction_report),
                "--summary-json",
                str(abstraction_summary_json),
                "--candidate-netlist",
                str(abstraction_candidates),
                "--packet-json",
                str(abstraction_packet_json),
            ]
            abstraction_result = subprocess.run(
                abstraction_cmd,
                cwd=self.config.repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            abstraction_log.write_text(abstraction_result.stdout or "", encoding="utf-8")
            abstraction_summary: dict[str, Any] = {}
            if abstraction_summary_json.is_file():
                try:
                    abstraction_summary = json.loads(abstraction_summary_json.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    abstraction_summary = {}
            abstraction_packet: dict[str, Any] = {}
            if abstraction_packet_json.is_file():
                try:
                    abstraction_packet = json.loads(abstraction_packet_json.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    abstraction_packet = {}
            abstraction_packet_verification = run_passive_abstraction_packet_verification(
                repo_root=self.config.repo_root,
                source_netlist=compiled.netlist_path,
                packet_json=abstraction_packet_json,
                report=abstraction_packet_verification_report,
                summary_json=abstraction_packet_verification_summary_json,
                log=abstraction_packet_verification_log,
                top_cell=self.config.top_cell,
                source_abstraction_netlist=abstraction_source_abs_netlist,
                candidate_abstraction_netlist=abstraction_candidate_abs_netlist,
            )
            abstraction_packet_verification_summary = (
                abstraction_packet_verification.get("summary", {})
                if isinstance(abstraction_packet_verification.get("summary"), dict)
                else {}
            )
            passive_abs_netgen_trial = self._run_passive_abs_netgen_trial(
                source_abs_netlist=abstraction_source_abs_netlist,
                candidate_abs_netlist=abstraction_candidate_abs_netlist,
                source_top_cell=f"{self.config.top_cell}_source_passive_abs",
                candidate_top_cell=f"{self.config.top_cell}_candidate_passive_abs",
                report=passive_abs_netgen_report,
                log=passive_abs_netgen_log,
                summary=passive_abs_lvs_result_summary,
            )
            passive_aware_prepare = run_passive_aware_lvs_trial_preparation(
                repo_root=self.config.repo_root,
                source_netlist=compiled.netlist_path,
                extracted_netlist=raw_extracted,
                packet_json=abstraction_packet_json,
                out_dir=passive_aware_trial_dir,
                prefix=self.config.top_cell,
                report=passive_aware_trial_report,
                summary_json=passive_aware_trial_summary_json,
                log=passive_aware_trial_log,
                renames=[],
            )
            passive_aware_prepare_summary = (
                passive_aware_prepare.get("summary", {})
                if isinstance(passive_aware_prepare.get("summary"), dict)
                else {}
            )
            passive_aware_source = Path(str(passive_aware_prepare_summary.get("source_output", "")))
            passive_aware_extracted = Path(str(passive_aware_prepare_summary.get("extracted_output", "")))
            passive_aware_netgen_trial = self._run_passive_abs_netgen_trial(
                source_abs_netlist=passive_aware_source,
                candidate_abs_netlist=passive_aware_extracted,
                source_top_cell=self.config.top_cell,
                candidate_top_cell=magic_cell,
                report=passive_aware_netgen_report,
                log=passive_aware_netgen_log,
                summary=passive_aware_lvs_result_summary,
            )
            hybrid_extracted = self._mos_only_projection_extracted_netlist(compiled)
            ports = self.config.data.get("ports", {})
            passive_aware_mos_connectivity = run_mos_connectivity_comparison(
                repo_root=self.config.repo_root,
                reference_netlist=hybrid_extracted,
                candidate_netlist=passive_aware_extracted,
                netgen_report=passive_aware_netgen_report,
                report=passive_aware_mos_connectivity_report,
                summary_json=passive_aware_mos_connectivity_summary_json,
                log=passive_aware_mos_connectivity_log,
                vdd=str(ports.get("vdd", "vdda")),
                vss=str(ports.get("vss", "gnda")),
            )
            passive_aware_mos_connectivity_summary = (
                passive_aware_mos_connectivity.get("summary", {})
                if isinstance(passive_aware_mos_connectivity.get("summary"), dict)
                else {}
            )
            mos_repair_plan = derive_mos_connectivity_repair_plan(
                passive_aware_mos_connectivity_summary
            )
            mos_repair_prepare: dict[str, Any]
            mos_repair_netgen_trial: dict[str, Any]
            if mos_repair_plan.get("status") == "ready":
                mos_repair_prepare = run_passive_aware_lvs_trial_preparation(
                    repo_root=self.config.repo_root,
                    source_netlist=compiled.netlist_path,
                    extracted_netlist=raw_extracted,
                    packet_json=abstraction_packet_json,
                    out_dir=mos_repair_trial_dir,
                    prefix=self.config.top_cell,
                    report=mos_repair_trial_report,
                    summary_json=mos_repair_trial_summary_json,
                    log=mos_repair_trial_log,
                    renames=list(mos_repair_plan.get("renames", [])),
                )
                mos_repair_prepare_summary = (
                    mos_repair_prepare.get("summary", {})
                    if isinstance(mos_repair_prepare.get("summary"), dict)
                    else {}
                )
                mos_repair_source = Path(str(mos_repair_prepare_summary.get("source_output", "")))
                mos_repair_extracted = Path(
                    str(mos_repair_prepare_summary.get("extracted_output", ""))
                )
                mos_repair_netgen_trial = self._run_passive_abs_netgen_trial(
                    source_abs_netlist=mos_repair_source,
                    candidate_abs_netlist=mos_repair_extracted,
                    source_top_cell=self.config.top_cell,
                    candidate_top_cell=magic_cell,
                    report=mos_repair_netgen_report,
                    log=mos_repair_netgen_log,
                    summary=mos_repair_lvs_result_summary,
                )
            else:
                mos_repair_prepare = {
                    "status": "skipped",
                    "reason": "MOS connectivity repair plan is not ready",
                    "summary": {},
                }
                mos_repair_netgen_trial = {
                    "status": "skipped",
                    "reason": "MOS connectivity repair plan is not ready",
                    "summary": str(mos_repair_lvs_result_summary),
                }
            hybrid_prepare: dict[str, Any]
            hybrid_netgen_trial: dict[str, Any]
            if hybrid_extracted is not None:
                hybrid_prepare = run_passive_aware_lvs_trial_preparation(
                    repo_root=self.config.repo_root,
                    source_netlist=compiled.netlist_path,
                    extracted_netlist=hybrid_extracted,
                    packet_json=abstraction_packet_json,
                    out_dir=hybrid_trial_dir,
                    prefix=self.config.top_cell,
                    report=hybrid_trial_report,
                    summary_json=hybrid_trial_summary_json,
                    log=hybrid_trial_log,
                    renames=[],
                )
                hybrid_prepare_summary = (
                    hybrid_prepare.get("summary", {})
                    if isinstance(hybrid_prepare.get("summary"), dict)
                    else {}
                )
                hybrid_source = Path(str(hybrid_prepare_summary.get("source_output", "")))
                hybrid_extracted_prepared = Path(str(hybrid_prepare_summary.get("extracted_output", "")))
                hybrid_netgen_trial = self._run_passive_abs_netgen_trial(
                    source_abs_netlist=hybrid_source,
                    candidate_abs_netlist=hybrid_extracted_prepared,
                    source_top_cell=self.config.top_cell,
                    candidate_top_cell=magic_cell,
                    report=hybrid_netgen_report,
                    log=hybrid_netgen_log,
                    summary=hybrid_lvs_result_summary,
                )
            else:
                hybrid_prepare = {
                    "status": "skipped",
                    "reason": "MOS-only projection extracted netlist missing",
                    "summary": {},
                }
                hybrid_netgen_trial = {
                    "status": "skipped",
                    "reason": "MOS-only projection extracted netlist missing",
                    "summary": str(hybrid_lvs_result_summary),
                }
            passive_aware_config = self.config.data.get("verification", {}).get("passive_aware", {})
            route_bridge_trial: dict[str, Any] = {
                "status": "skipped",
                "reason": "route bridge trial disabled or no split-net MOS evidence",
                "artifacts": {},
            }
            if (
                bool(passive_aware_config.get("enable_mos_route_bridge_trial", True))
                and hybrid_extracted is not None
                and passive_aware_mos_connectivity_summary.get("split_net_repair_suggestions")
            ):
                route_bridge_trial = self._run_route_bridge_full_gds_trial(
                    compiled=compiled,
                    variant=variant,
                    variant_dir=variant_dir,
                    input_gds=labelled_gds,
                    magic_cell=magic_cell,
                    abstraction_packet_json=abstraction_packet_json,
                    mos_reference_netlist=hybrid_extracted,
                )
            result.update(
                {
                    "status": "pass" if abstraction_result.returncode == 0 and abstraction_report.is_file() else "abstraction_failed",
                    "abstraction_returncode": abstraction_result.returncode,
                    "abstraction_report": str(abstraction_report),
                    "abstraction_summary_json": str(abstraction_summary_json),
                    "abstraction_candidates": str(abstraction_candidates),
                    "abstraction_packet_json": str(abstraction_packet_json),
                    "abstraction_packet_verification_status": abstraction_packet_verification_summary.get(
                        "status"
                    ),
                    "formal_lvs_abstraction_ready": abstraction_packet_verification_summary.get(
                        "formal_lvs_abstraction_ready"
                    ),
                    "abstraction_scope": abstraction_packet_verification_summary.get("abstraction_scope"),
                    "remaining_unresolved_blockers": abstraction_packet_verification_summary.get(
                        "remaining_unresolved_blockers"
                    ),
                    "abstraction_packet_verification_report": str(abstraction_packet_verification_report),
                    "abstraction_packet_verification_json": str(
                        abstraction_packet_verification_summary_json
                    ),
                    "abstraction_packet_verification_log": str(abstraction_packet_verification_log),
                    "abstraction_source_passive_abs_netlist": str(abstraction_source_abs_netlist),
                    "abstraction_candidate_passive_abs_netlist": str(abstraction_candidate_abs_netlist),
                    "passive_abs_netgen_status": passive_abs_netgen_trial.get("status"),
                    "passive_abs_netgen_report": str(passive_abs_netgen_report),
                    "passive_abs_netgen_log": str(passive_abs_netgen_log),
                    "passive_abs_lvs_result_summary": str(passive_abs_lvs_result_summary),
                    "passive_aware_lvs_trial_prepare_status": passive_aware_prepare_summary.get("status"),
                    "passive_aware_lvs_trial_formal_lvs_abstraction_ready": passive_aware_prepare_summary.get(
                        "formal_lvs_abstraction_ready"
                    ),
                    "passive_aware_lvs_trial_abstraction_scope": passive_aware_prepare_summary.get(
                        "abstraction_scope"
                    ),
                    "passive_aware_lvs_trial_prepare_report": str(passive_aware_trial_report),
                    "passive_aware_lvs_trial_prepare_summary_json": str(passive_aware_trial_summary_json),
                    "passive_aware_lvs_trial_prepare_log": str(passive_aware_trial_log),
                    "passive_aware_lvs_trial_netgen_status": passive_aware_netgen_trial.get("status"),
                    "passive_aware_lvs_trial_netgen_report": str(passive_aware_netgen_report),
                    "passive_aware_lvs_trial_netgen_log": str(passive_aware_netgen_log),
                    "passive_aware_lvs_trial_result_summary": str(passive_aware_lvs_result_summary),
                    "passive_aware_mos_connectivity_status": passive_aware_mos_connectivity.get(
                        "status"
                    ),
                    "passive_aware_mos_connectivity_reason": passive_aware_mos_connectivity.get(
                        "reason"
                    ),
                    "passive_aware_mos_connectivity_report": str(passive_aware_mos_connectivity_report),
                    "passive_aware_mos_connectivity_summary_json": str(
                        passive_aware_mos_connectivity_summary_json
                    ),
                    "passive_aware_mos_connectivity_log": str(passive_aware_mos_connectivity_log),
                    "passive_aware_mos_connectivity": passive_aware_mos_connectivity_summary,
                    "formal_passive_mos_repair_plan": mos_repair_plan,
                    "formal_passive_mos_repair_renames": mos_repair_plan.get("renames"),
                    "formal_passive_mos_repair_signoff_eligible": mos_repair_plan.get(
                        "signoff_eligible"
                    ),
                    "formal_passive_mos_repair_lvs_trial_prepare_status": mos_repair_prepare.get(
                        "status"
                    ),
                    "formal_passive_mos_repair_lvs_trial_prepare_report": str(
                        mos_repair_trial_report
                    ),
                    "formal_passive_mos_repair_lvs_trial_prepare_summary_json": str(
                        mos_repair_trial_summary_json
                    ),
                    "formal_passive_mos_repair_lvs_trial_prepare_log": str(mos_repair_trial_log),
                    "formal_passive_mos_repair_lvs_trial_netgen_status": mos_repair_netgen_trial.get(
                        "status"
                    ),
                    "formal_passive_mos_repair_lvs_trial_netgen_report": str(
                        mos_repair_netgen_report
                    ),
                    "formal_passive_mos_repair_lvs_trial_netgen_log": str(mos_repair_netgen_log),
                    "formal_passive_mos_repair_lvs_trial_result_summary": str(
                        mos_repair_lvs_result_summary
                    ),
                    "route_bridge_trial_status": route_bridge_trial.get("status"),
                    "route_bridge_trial_reason": route_bridge_trial.get("reason"),
                    "route_bridge_trial_summary_json": route_bridge_trial.get("summary_json"),
                    "route_bridge_injection_status": route_bridge_trial.get(
                        "route_bridge_injection_status"
                    ),
                    "route_bridge_summary_json": route_bridge_trial.get("route_bridge_summary_json"),
                    "route_bridge_count": route_bridge_trial.get("route_bridge_count"),
                    "route_bridge_gds": route_bridge_trial.get("route_bridge_gds"),
                    "route_bridge_drc_status": route_bridge_trial.get("route_bridge_drc_status"),
                    "route_bridge_drc_count": route_bridge_trial.get("route_bridge_drc_count"),
                    "route_bridge_mos_connectivity_status": route_bridge_trial.get(
                        "route_bridge_mos_connectivity_status"
                    ),
                    "route_bridge_mos_connectivity_summary_json": route_bridge_trial.get(
                        "route_bridge_mos_connectivity_summary_json"
                    ),
                    "route_bridge_formal_passive_lvs_prepare_status": route_bridge_trial.get(
                        "formal_passive_lvs_prepare_status"
                    ),
                    "route_bridge_formal_passive_lvs_prepare_summary_json": route_bridge_trial.get(
                        "formal_passive_lvs_prepare_summary_json"
                    ),
                    "route_bridge_formal_passive_lvs_netgen_status": route_bridge_trial.get(
                        "formal_passive_lvs_netgen_status"
                    ),
                    "route_bridge_formal_passive_lvs_result_summary": route_bridge_trial.get(
                        "formal_passive_lvs_result_summary"
                    ),
                    "route_bridge_artifacts": route_bridge_trial.get("artifacts", {}),
                    "hybrid_mos_passive_lvs_trial_prepare_status": hybrid_prepare.get("status"),
                    "hybrid_mos_passive_lvs_trial_formal_lvs_abstraction_ready": hybrid_prepare.get(
                        "formal_lvs_abstraction_ready"
                    ),
                    "hybrid_mos_passive_lvs_trial_abstraction_scope": hybrid_prepare.get(
                        "abstraction_scope"
                    ),
                    "hybrid_mos_passive_lvs_trial_prepare_report": str(hybrid_trial_report),
                    "hybrid_mos_passive_lvs_trial_prepare_summary_json": str(hybrid_trial_summary_json),
                    "hybrid_mos_passive_lvs_trial_prepare_log": str(hybrid_trial_log),
                    "hybrid_mos_passive_lvs_trial_netgen_status": hybrid_netgen_trial.get("status"),
                    "hybrid_mos_passive_lvs_trial_netgen_report": str(hybrid_netgen_report),
                    "hybrid_mos_passive_lvs_trial_netgen_log": str(hybrid_netgen_log),
                    "hybrid_mos_passive_lvs_trial_result_summary": str(hybrid_lvs_result_summary),
                    "abstraction_log": str(abstraction_log),
                    "abstraction_summary": abstraction_summary,
                    "abstraction_packet": abstraction_packet,
                    "abstraction_packet_verification": abstraction_packet_verification_summary,
                }
            )
            results.append(result)

        summary = summarize_resistor_remap_variants(results)
        summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        evidence_report = variant_dir / "passive_lvs_evidence_report.md"
        evidence_summary_json = variant_dir / "passive_lvs_evidence_summary.json"
        evidence_log = variant_dir / "passive_lvs_evidence.log"
        source_passives_for_requirements = source_passive_instances(compiled.netlist_path)
        source_passive_models = [
            str(item.get("model", "")).lower()
            for item in source_passives_for_requirements
            if isinstance(item, dict)
        ]
        evidence_verification = run_passive_lvs_evidence_verification(
            repo_root=self.config.repo_root,
            resistor_summary_json=summary_json,
            report=evidence_report,
            summary_json=evidence_summary_json,
            log=evidence_log,
            require_resistor=any(model.startswith("r") or "res" in model for model in source_passive_models),
            require_capacitor=any(model.startswith("c") or "cap" in model for model in source_passive_models),
        )
        evidence_summary = (
            evidence_verification.get("summary", {})
            if isinstance(evidence_verification.get("summary"), dict)
            else {}
        )
        summary["formal_passive_lvs_evidence_status"] = evidence_summary.get("status")
        summary["formal_passive_lvs_evidence_pass"] = evidence_summary.get(
            "formal_passive_lvs_evidence_pass"
        )
        summary["formal_passive_lvs_evidence_scope"] = evidence_summary.get("verification_scope")
        summary["formal_passive_lvs_evidence_failed_requirements"] = evidence_summary.get(
            "failed_requirements"
        )
        summary["formal_passive_lvs_evidence_summary_json"] = str(evidence_summary_json)
        summary["formal_passive_lvs_evidence_report"] = str(evidence_report)
        summary["formal_passive_lvs_evidence_log"] = str(evidence_log)
        summary["formal_passive_lvs_evidence_returncode"] = evidence_verification.get("returncode")
        capability_dir = variant_dir / "native_passive_capability"
        capability_report = capability_dir / "native_passive_capability_report.md"
        capability_summary_json = capability_dir / "native_passive_capability_summary.json"
        capability_log = capability_dir / "native_passive_capability.log"
        capability_probe = run_native_passive_capability_probe(
            repo_root=self.config.repo_root,
            source_netlist=compiled.netlist_path,
            sky130a=str(self.layout_config.get("sky130a")) if self.layout_config.get("sky130a") else None,
            report=capability_report,
            summary_json=capability_summary_json,
            log=capability_log,
            wsl_distro=self._resolved_wsl_distro(),
        )
        capability_summary = (
            capability_probe.get("summary", {})
            if isinstance(capability_probe.get("summary"), dict)
            else {}
        )
        summary["native_passive_capability_probe_status"] = capability_probe.get("status")
        summary["native_passive_capability_source_model_native_status"] = capability_summary.get(
            "source_model_native_status"
        )
        summary["native_passive_capability_direct_source_model_support"] = capability_summary.get(
            "direct_source_model_support"
        )
        summary["native_passive_capability_unsupported_source_models"] = capability_summary.get(
            "unsupported_source_models"
        )
        summary["native_passive_capability_retarget_available"] = capability_summary.get(
            "native_retarget_available"
        )
        summary["native_passive_capability_retarget_map"] = capability_summary.get(
            "native_retarget_map"
        )
        summary["native_passive_capability_requires_geometry_replacement"] = capability_summary.get(
            "native_retarget_requires_geometry_replacement"
        )
        summary["native_passive_capability_can_fix_current_gds_by_layer_remap_only"] = (
            capability_summary.get("can_fix_current_gds_by_layer_remap_only")
        )
        summary["native_passive_capability_device_generation_source_status"] = capability_summary.get(
            "device_generation_source_status"
        )
        summary["native_passive_capability_summary_json"] = str(capability_summary_json)
        summary["native_passive_capability_report"] = str(capability_report)
        summary["native_passive_capability_log"] = str(capability_log)
        retarget_dir = variant_dir / "native_passive_retarget_trial"
        retarget_report = retarget_dir / "native_passive_retarget_report.md"
        retarget_summary_json = retarget_dir / "native_passive_retarget_summary.json"
        retarget_log = retarget_dir / "native_passive_retarget.log"

        def _resolve_summary_path(path_value: Any) -> Path:
            path = Path(str(path_value or ""))
            return path if path.is_absolute() else self.config.repo_root / path

        best_packet_json = _resolve_summary_path(summary.get("best_abstraction_packet_json"))
        best_extracted_netlist = _resolve_summary_path(summary.get("best_extracted_netlist"))
        retarget_trial = run_native_passive_retarget_trial(
            repo_root=self.config.repo_root,
            packet_json=best_packet_json,
            candidate_extracted=best_extracted_netlist,
            out_dir=retarget_dir,
            prefix=self.config.top_cell,
            sky130a=str(self.layout_config.get("sky130a")) if self.layout_config.get("sky130a") else None,
            report=retarget_report,
            summary_json=retarget_summary_json,
            log=retarget_log,
            wsl_distro=self._resolved_wsl_distro(),
        )
        retarget_summary = (
            retarget_trial.get("summary", {})
            if isinstance(retarget_trial.get("summary"), dict)
            else {}
        )
        summary["native_passive_retarget_trial_status"] = retarget_trial.get("status")
        summary["native_passive_retarget_summary_json"] = str(retarget_summary_json)
        summary["native_passive_retarget_report"] = str(retarget_report)
        summary["native_passive_retarget_log"] = str(retarget_log)
        summary["native_passive_retarget_returncode"] = retarget_trial.get("returncode")
        summary["native_resistor_chain_status"] = retarget_summary.get("native_resistor_chain_status")
        summary["native_resistor_chain_source_instance"] = retarget_summary.get(
            "native_resistor_chain_source_instance"
        )
        summary["native_resistor_chain_device_count"] = retarget_summary.get(
            "native_resistor_chain_device_count"
        )
        summary["native_resistor_chain_model"] = retarget_summary.get("native_resistor_chain_model")
        summary["native_resistor_chain_netgen_status"] = retarget_summary.get(
            "native_resistor_chain_netgen_status"
        )
        summary["native_resistor_chain_netgen"] = retarget_summary.get("native_resistor_chain_netgen")
        summary["native_capacitor_device_recognition_status"] = retarget_summary.get(
            "native_capacitor_device_recognition_status"
        )
        summary["native_capacitor_devices"] = retarget_summary.get("native_capacitor_devices")
        summary["native_passive_retarget_missing_native_source_passive_instances"] = retarget_summary.get(
            "missing_native_source_passive_instances"
        )
        summary["native_passive_retarget_full_native_passive_lvs_ready"] = retarget_summary.get(
            "full_native_passive_lvs_ready"
        )
        summary["native_passive_retarget_full_native_passive_lvs_proven"] = retarget_summary.get(
            "full_native_passive_lvs_proven"
        )
        summary["native_passive_retarget_source_native_passive_netlist"] = retarget_summary.get(
            "source_native_passive_netlist"
        )
        summary["native_passive_retarget_candidate_native_passive_netlist"] = retarget_summary.get(
            "candidate_native_passive_netlist"
        )
        if isinstance(retarget_summary.get("native_resistor_chain_netgen"), dict):
            summary["native_resistor_chain_netgen_report"] = retarget_summary[
                "native_resistor_chain_netgen"
            ].get("report")
            summary["native_resistor_chain_netgen_log"] = retarget_summary[
                "native_resistor_chain_netgen"
            ].get("log")
        cap_gencell_dir = variant_dir / "native_cap_gencell_probe"
        cap_gencell_report = cap_gencell_dir / "native_cap_gencell_report.md"
        cap_gencell_summary_json = cap_gencell_dir / "native_cap_gencell_summary.json"
        cap_gencell_log = cap_gencell_dir / "native_cap_gencell.log"
        cap_gencell_probe = run_native_cap_gencell_probe(
            repo_root=self.config.repo_root,
            sky130a=str(self.layout_config.get("sky130a")) if self.layout_config.get("sky130a") else None,
            out_dir=cap_gencell_dir,
            report=cap_gencell_report,
            summary_json=cap_gencell_summary_json,
            log=cap_gencell_log,
            wsl_distro=self._resolved_wsl_distro(),
        )
        cap_gencell_summary = (
            cap_gencell_probe.get("summary", {})
            if isinstance(cap_gencell_probe.get("summary"), dict)
            else {}
        )
        summary["native_cap_gencell_probe_status"] = cap_gencell_probe.get("status")
        summary["native_cap_gencell_extraction_status"] = cap_gencell_summary.get(
            "native_cap_gencell_extraction_status"
        )
        summary["native_cap_gencell_model"] = cap_gencell_summary.get("model")
        summary["native_cap_gencell_cell_name"] = cap_gencell_summary.get("cell_name")
        summary["native_cap_gencell_recognized_device_count"] = cap_gencell_summary.get(
            "recognized_native_capacitor_device_count"
        )
        summary["native_cap_gencell_devices"] = cap_gencell_summary.get("native_capacitor_devices")
        summary["native_cap_gencell_summary_json"] = str(cap_gencell_summary_json)
        summary["native_cap_gencell_report"] = str(cap_gencell_report)
        summary["native_cap_gencell_log"] = str(cap_gencell_log)
        summary["native_cap_gencell_magic_log"] = cap_gencell_summary.get("log")
        summary["native_cap_gencell_spice"] = cap_gencell_summary.get("spice")
        summary["native_cap_gencell_mag"] = cap_gencell_summary.get("mag")
        summary["native_cap_gencell_gds"] = cap_gencell_summary.get("gds")
        summary["native_cap_gencell_ext"] = cap_gencell_summary.get("ext")
        native_cap_full_gds_trial = self._run_native_cap_full_gds_trial(
            compiled=compiled,
            variant_dir=variant_dir,
            magic_cell=magic_cell,
            identity_json_path=identity_json_path,
            resistor_summary=summary,
        )
        summary["native_cap_full_gds_trial_status"] = native_cap_full_gds_trial.get("status")
        summary["native_cap_full_gds_trial_summary_json"] = str(
            variant_dir / "native_cap_full_gds_trial" / "native_cap_full_gds_trial_summary.json"
        )
        summary["native_cap_replacement_status"] = native_cap_full_gds_trial.get(
            "replacement_candidate_status"
        )
        summary["native_cap_replacement_cell_name"] = (
            _read_json_dict_if_present(native_cap_full_gds_trial.get("replacement_candidate_summary_json")).get(
                "replacement_cell_name"
            )
        )
        summary["native_cap_replacement_gds"] = native_cap_full_gds_trial.get("replacement_gds")
        summary["native_cap_replacement_terminal_bridge_status"] = native_cap_full_gds_trial.get(
            "terminal_bridge_status"
        )
        summary["native_cap_replacement_top_gds_merge_status"] = native_cap_full_gds_trial.get(
            "top_gds_merge_status"
        )
        summary["native_cap_replacement_bridge_mode"] = native_cap_full_gds_trial.get("bridge_mode")
        summary["native_cap_replacement_full_gds"] = native_cap_full_gds_trial.get("merged_gds")
        summary["native_cap_replacement_extract_status"] = native_cap_full_gds_trial.get(
            "magic_extract_status"
        )
        summary["native_cap_replacement_drc_status"] = native_cap_full_gds_trial.get("drc_status")
        summary["native_cap_replacement_drc_count"] = native_cap_full_gds_trial.get("drc_count")
        summary["native_cap_replacement_native_passive_netgen_status"] = native_cap_full_gds_trial.get(
            "native_passive_netgen_status"
        )
        summary["native_cap_replacement_native_capacitor_device_count"] = native_cap_full_gds_trial.get(
            "native_capacitor_device_count"
        )
        if native_cap_full_gds_trial.get("native_capacitor_device_recognition_status") == "pass":
            summary["native_capacitor_device_recognition_status"] = "pass"
            summary["native_capacitor_devices"] = native_cap_full_gds_trial.get(
                "native_capacitor_devices"
            )
        if native_cap_full_gds_trial.get("full_native_passive_lvs_proven"):
            summary["native_passive_retarget_trial_status"] = native_cap_full_gds_trial.get(
                "native_passive_retarget_status"
            ) or "native_passive_retarget_ready"
            summary["native_passive_device_recognition_status"] = "pass"
            summary["native_passive_device_recognition_claimed"] = True
            summary["native_passive_device_recognition_missing_instances"] = []
            summary["native_passive_device_recognition_blockers"] = {}
            summary["native_cap_replacement_full_native_capacitor_lvs_ready"] = True
            summary["native_cap_replacement_remaining_gates"] = []
            summary["native_passive_retarget_missing_native_source_passive_instances"] = []
            summary["native_passive_retarget_full_native_passive_lvs_ready"] = True
            summary["native_passive_retarget_full_native_passive_lvs_proven"] = True
            summary["full_passive_inclusive_gds_lvs_proven"] = True
            summary["full_passive_inclusive_gds_native_lvs_status"] = "pass"
            summary["full_passive_inclusive_gds_lvs_scope"] = "full_passive_inclusive_gds_lvs"
        summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        artifacts["passive_lvs_evidence_summary_json"] = str(evidence_summary_json)
        artifacts["passive_lvs_evidence_report"] = str(evidence_report)
        artifacts["passive_lvs_evidence_log"] = str(evidence_log)
        artifacts["native_passive_capability_summary_json"] = str(capability_summary_json)
        artifacts["native_passive_capability_report"] = str(capability_report)
        artifacts["native_passive_capability_log"] = str(capability_log)
        artifacts["native_passive_retarget_summary_json"] = str(retarget_summary_json)
        artifacts["native_passive_retarget_report"] = str(retarget_report)
        artifacts["native_passive_retarget_log"] = str(retarget_log)
        if summary.get("native_passive_retarget_source_native_passive_netlist"):
            artifacts["native_passive_retarget_source_native_passive_netlist"] = str(
                summary["native_passive_retarget_source_native_passive_netlist"]
            )
        if summary.get("native_passive_retarget_candidate_native_passive_netlist"):
            artifacts["native_passive_retarget_candidate_native_passive_netlist"] = str(
                summary["native_passive_retarget_candidate_native_passive_netlist"]
            )
        if summary.get("native_resistor_chain_netgen_report"):
            artifacts["native_resistor_chain_netgen_report"] = str(
                summary["native_resistor_chain_netgen_report"]
            )
        if summary.get("native_resistor_chain_netgen_log"):
            artifacts["native_resistor_chain_netgen_log"] = str(summary["native_resistor_chain_netgen_log"])
        artifacts["native_cap_gencell_summary_json"] = str(cap_gencell_summary_json)
        artifacts["native_cap_gencell_report"] = str(cap_gencell_report)
        artifacts["native_cap_gencell_log"] = str(cap_gencell_log)
        if summary.get("native_cap_gencell_magic_log"):
            artifacts["native_cap_gencell_magic_log"] = str(summary["native_cap_gencell_magic_log"])
        if summary.get("native_cap_gencell_spice"):
            artifacts["native_cap_gencell_spice"] = str(summary["native_cap_gencell_spice"])
        if summary.get("native_cap_gencell_mag"):
            artifacts["native_cap_gencell_mag"] = str(summary["native_cap_gencell_mag"])
        if summary.get("native_cap_gencell_gds"):
            artifacts["native_cap_gencell_gds"] = str(summary["native_cap_gencell_gds"])
        if summary.get("native_cap_gencell_ext"):
            artifacts["native_cap_gencell_ext"] = str(summary["native_cap_gencell_ext"])
        if summary.get("native_cap_full_gds_trial_summary_json"):
            artifacts["native_cap_full_gds_trial_summary_json"] = str(
                summary["native_cap_full_gds_trial_summary_json"]
            )
        if summary.get("native_cap_replacement_full_gds"):
            artifacts["native_cap_replacement_full_gds"] = str(
                summary["native_cap_replacement_full_gds"]
            )
        if native_cap_full_gds_trial.get("artifacts"):
            for key, value in native_cap_full_gds_trial.get("artifacts", {}).items():
                if value:
                    artifacts[f"native_cap_full_gds_{key}"] = str(value)
        return {
            "status": summary.get("status"),
            "summary": summary,
            "summary_json": summary_json,
            "artifacts": artifacts,
        }

    def _run_native_cap_full_gds_trial(
        self,
        *,
        compiled: CompiledCandidate,
        variant_dir: Path,
        magic_cell: str,
        identity_json_path: Path,
        resistor_summary: dict[str, Any],
    ) -> dict[str, Any]:
        trial_dir = variant_dir / "native_cap_full_gds_trial"
        trial_dir.mkdir(parents=True, exist_ok=True)
        summary_json = trial_dir / "native_cap_full_gds_trial_summary.json"
        source_instance = str(
            self.config.data.get("verification", {})
            .get("passive_aware", {})
            .get("native_cap_source_instance", "xc0")
        )

        def resolve_path(value: Any) -> Path:
            path = Path(str(value or ""))
            return path if path.is_absolute() else self.config.repo_root / path

        route_bridge_gds = resolve_path(resistor_summary.get("best_route_bridge_gds"))
        packet_json = resolve_path(resistor_summary.get("best_abstraction_packet_json"))
        source_cap_gds = compiled.case_dir / "gds" / f"{self.config.top_cell}_{source_instance}.gds"
        source_structure = run_gds_structure_diagnostic(
            repo_root=self.config.repo_root,
            gds_path=source_cap_gds,
            source_netlist=compiled.netlist_path,
            case_dir=compiled.case_dir,
            out_dir=trial_dir,
            top_cell=self.config.top_cell,
            report_stem=f"{source_instance}_source_gds_structure",
        )
        source_structure_json = Path(str(source_structure.get("summary_json")))

        candidate_dir = variant_dir / "native_cap_replacement_candidate"
        candidate_report = candidate_dir / "native_cap_replacement_report.md"
        candidate_summary_json = candidate_dir / "native_cap_replacement_summary.json"
        candidate_log = candidate_dir / "native_cap_replacement.log"
        candidate = run_native_cap_replacement_candidate(
            repo_root=self.config.repo_root,
            identity_summary=identity_json_path,
            source_gds_structure_json=source_structure_json,
            source_instance=source_instance,
            sky130a=str(self.layout_config.get("sky130a")) if self.layout_config.get("sky130a") else None,
            out_dir=candidate_dir,
            report=candidate_report,
            summary_json=candidate_summary_json,
            log=candidate_log,
            wsl_distro=self._resolved_wsl_distro(),
        )
        candidate_summary = candidate.get("summary", {}) if isinstance(candidate.get("summary"), dict) else {}
        replacement_gds = resolve_path(candidate_summary.get("replacement_gds"))
        bridge_mode = str(
            self.config.data.get("verification", {})
            .get("passive_aware", {})
            .get("native_cap_bridge_mode", "m4_outside_stacks")
        )
        merged_gds = trial_dir / "native_cap_replaced.gds"
        merge_report = trial_dir / "native_cap_replacement_merge.md"
        merge_summary_json = trial_dir / "native_cap_replacement_merge_summary.json"
        merge_log = trial_dir / "native_cap_replacement_merge.log"
        merge = run_native_cap_flat_gds_replacement(
            repo_root=self.config.repo_root,
            input_gds=route_bridge_gds,
            replacement_gds=replacement_gds,
            output_gds=merged_gds,
            identity_summary=identity_json_path,
            source_gds_structure_json=source_structure_json,
            cell=magic_cell,
            source_instance=source_instance,
            bridge_mode=bridge_mode,
            report=merge_report,
            summary_json=merge_summary_json,
            log=merge_log,
        )
        merge_summary = merge.get("summary", {}) if isinstance(merge.get("summary"), dict) else {}
        extract = self._magic_extract_gds(
            gds=merged_gds,
            magic_cell=magic_cell,
            out_dir=trial_dir,
            stem="native_cap_replaced",
            banner="SKY130_NATIVE_CAP_REPLACEMENT: extract full GDS",
        )
        drc = self._run_magic_drc_gds(
            gds=merged_gds,
            magic_cell=magic_cell,
            out_dir=trial_dir,
            stem="native_cap_replaced",
            banner="SKY130_NATIVE_CAP_REPLACEMENT: DRC full GDS",
        )
        retarget_dir = trial_dir / "native_passive_retarget"
        retarget_summary_json = retarget_dir / "native_passive_retarget_summary.json"
        retarget = run_native_passive_retarget_trial(
            repo_root=self.config.repo_root,
            packet_json=packet_json,
            candidate_extracted=Path(str(extract.get("raw_extracted"))),
            out_dir=retarget_dir,
            prefix=f"{self.config.top_cell}_native_cap_full_gds",
            sky130a=str(self.layout_config.get("sky130a")) if self.layout_config.get("sky130a") else None,
            report=retarget_dir / "native_passive_retarget_report.md",
            summary_json=retarget_summary_json,
            log=retarget_dir / "native_passive_retarget.log",
            wsl_distro=self._resolved_wsl_distro(),
        )
        retarget_summary = retarget.get("summary", {}) if isinstance(retarget.get("summary"), dict) else {}
        full_proven = bool(
            merge.get("status") == "native_cap_replacement_merged"
            and extract.get("status") == "pass"
            and drc.get("status") == "pass"
            and drc.get("drc_count") == 0
            and retarget_summary.get("native_capacitor_device_recognition_status") == "pass"
            and retarget_summary.get("native_passive_netgen_status") == "pass"
            and retarget_summary.get("full_native_passive_lvs_proven")
        )
        status = "pass" if full_proven else "incomplete"
        summary = {
            "schema_version": "native_cap_full_gds_trial.v1",
            "status": status,
            "reason": None if full_proven else "native cap full-GDS trial did not prove full passive LVS",
            "source_instance": source_instance,
            "source_cap_gds": str(source_cap_gds),
            "source_gds_structure_status": source_structure.get("status"),
            "source_gds_structure_summary_json": str(source_structure_json),
            "route_bridge_gds": str(route_bridge_gds),
            "passive_abstraction_packet_json": str(packet_json),
            "replacement_candidate_status": candidate.get("status"),
            "replacement_candidate_summary_json": str(candidate_summary_json),
            "replacement_gds": str(replacement_gds),
            "merge_status": merge.get("status"),
            "merge_summary_json": str(merge_summary_json),
            "bridge_mode": bridge_mode,
            "terminal_bridge_status": merge_summary.get("terminal_bridge_status"),
            "top_gds_merge_status": merge_summary.get("top_gds_merge_status"),
            "merged_gds": str(merged_gds),
            "removed_element_count": merge_summary.get("removed_element_count"),
            "preserved_terminal_element_count": merge_summary.get("preserved_terminal_element_count"),
            "inserted_replacement_element_count": merge_summary.get("inserted_replacement_element_count"),
            "magic_extract_status": extract.get("status"),
            "magic_extract_returncode": extract.get("returncode"),
            "magic_extract_netlist": extract.get("raw_extracted"),
            "magic_extract_log": extract.get("magic_log"),
            "drc_status": drc.get("status"),
            "drc_count": drc.get("drc_count"),
            "drc_log": drc.get("magic_log"),
            "native_passive_retarget_status": retarget.get("status"),
            "native_passive_retarget_summary_json": str(retarget_summary_json),
            "native_capacitor_device_recognition_status": retarget_summary.get(
                "native_capacitor_device_recognition_status"
            ),
            "native_capacitor_device_count": retarget_summary.get("native_capacitor_device_count"),
            "native_capacitor_devices": retarget_summary.get("native_capacitor_devices"),
            "native_resistor_chain_status": retarget_summary.get("native_resistor_chain_status"),
            "native_resistor_chain_device_count": retarget_summary.get("native_resistor_chain_device_count"),
            "native_passive_netgen_status": retarget_summary.get("native_passive_netgen_status"),
            "native_passive_netgen": retarget_summary.get("native_passive_netgen"),
            "full_native_passive_lvs_ready": retarget_summary.get("full_native_passive_lvs_ready"),
            "full_native_passive_lvs_proven": retarget_summary.get("full_native_passive_lvs_proven"),
            "full_passive_inclusive_gds_lvs_proven": full_proven,
            "verification_scope": "full_passive_inclusive_gds_lvs" if full_proven else "native_cap_full_gds_trial",
            "artifacts": {
                "source_gds_structure_report": str(source_structure.get("report")),
                "replacement_candidate_report": str(candidate_report),
                "replacement_candidate_summary_json": str(candidate_summary_json),
                "merge_report": str(merge_report),
                "merge_summary_json": str(merge_summary_json),
                "magic_extract_log": str(extract.get("magic_log")),
                "magic_extract_netlist": str(extract.get("raw_extracted")),
                "drc_log": str(drc.get("magic_log")),
                "native_passive_retarget_report": str(retarget.get("report")),
                "native_passive_retarget_summary_json": str(retarget_summary_json),
            },
        }
        _write_text(summary_json, json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return summary

    def _existing_pinned_shapes_gds(self, compiled: CompiledCandidate) -> Path | None:
        candidates = [
            compiled.case_dir / f"{self.config.top_cell}.sky130.pinned_shapes.gds",
            compiled.case_dir / f"{self.config.top_cell}.sky130.pinned.gds",
            compiled.case_dir / f"{self.config.top_cell}.sky130.gds",
        ]
        for path in candidates:
            if path.is_file():
                return path
        return None

    def _mos_only_projection_extracted_netlist(self, compiled: CompiledCandidate) -> Path | None:
        candidates = [
            compiled.candidate_dir / "layout" / "lvs_mos_projection" / f"{self.config.top_cell}_extracted.connectivity.spice",
            compiled.candidate_dir / "layout" / "lvs_mos_projection" / f"{self.config.top_cell}_extracted.spice",
            compiled.candidate_dir / "layout" / "lvs_mos_projection" / f"{self.config.top_cell}_extracted.raw.spice",
        ]
        for path in candidates:
            if path.is_file():
                return path
        return None

    def _resolved_wsl_distro(self) -> str | None:
        return _choose_wsl_distro(
            str(self.layout_config.get("wsl_distro")) if self.layout_config.get("wsl_distro") else None
        )

    def _magic_extract_command(
        self,
        magic_tcl: Path,
        magic_log: Path,
        raw_extracted: Path,
        ext_copy: Path,
        magic_cell: str,
    ) -> list[str]:
        sky130a = self.layout_config.get("sky130a")
        magicrc = _join_posix_or_path(str(sky130a), "libs.tech/magic/sky130A.magicrc") if sky130a else None
        if sys.platform.startswith("win") and shutil.which("wsl"):
            repo = _wsl_path(self.config.repo_root)
            magicrc_text = _wsl_or_posix_path(magicrc) if magicrc is not None else "sky130A.magicrc"
            command = (
                f"cd {shlex.quote(repo)} && "
                f"rm -f {shlex.quote(magic_cell + '.spice')} {shlex.quote(magic_cell + '.sp')} "
                f"{shlex.quote(magic_cell + '.ext')} && "
                f"magic -dnull -noconsole -rcfile {shlex.quote(magicrc_text)} "
                f"< {shlex.quote(_wsl_path(magic_tcl))} > {shlex.quote(_wsl_path(magic_log))} 2>&1; "
                "status=$?; "
                f"if [ -f {shlex.quote(magic_cell + '.spice')} ]; then mv {shlex.quote(magic_cell + '.spice')} {shlex.quote(_wsl_path(raw_extracted))}; fi; "
                f"if [ -f {shlex.quote(magic_cell + '.sp')} ]; then mv {shlex.quote(magic_cell + '.sp')} {shlex.quote(_wsl_path(raw_extracted))}; fi; "
                f"if [ -f {shlex.quote(magic_cell + '.ext')} ]; then mv {shlex.quote(magic_cell + '.ext')} {shlex.quote(_wsl_path(ext_copy))}; fi; "
                "exit $status"
            )
            distro = self._resolved_wsl_distro()
            if distro:
                return ["wsl", "-d", str(distro), "bash", "-lc", command]
            return ["wsl", "bash", "-lc", command]
        magicrc_args = ["-rcfile", str(magicrc)] if magicrc is not None else []
        command = (
            f"rm -f {shlex.quote(magic_cell + '.spice')} {shlex.quote(magic_cell + '.sp')} "
            f"{shlex.quote(magic_cell + '.ext')} && "
            f"magic -dnull -noconsole {' '.join(shlex.quote(arg) for arg in magicrc_args)} "
            f"< {shlex.quote(str(magic_tcl))} > {shlex.quote(str(magic_log))} 2>&1; "
            "status=$?; "
            f"if [ -f {shlex.quote(magic_cell + '.spice')} ]; then mv {shlex.quote(magic_cell + '.spice')} {shlex.quote(str(raw_extracted))}; fi; "
            f"if [ -f {shlex.quote(magic_cell + '.sp')} ]; then mv {shlex.quote(magic_cell + '.sp')} {shlex.quote(str(raw_extracted))}; fi; "
            f"if [ -f {shlex.quote(magic_cell + '.ext')} ]; then mv {shlex.quote(magic_cell + '.ext')} {shlex.quote(str(ext_copy))}; fi; "
            "exit $status"
        )
        return ["bash", "-lc", command]

    def _magic_batch_command(self, magic_tcl: Path, magic_log: Path) -> list[str]:
        sky130a = self.layout_config.get("sky130a")
        magicrc = _join_posix_or_path(str(sky130a), "libs.tech/magic/sky130A.magicrc") if sky130a else None
        if sys.platform.startswith("win") and shutil.which("wsl"):
            repo = _wsl_path(self.config.repo_root)
            magicrc_text = _wsl_or_posix_path(magicrc) if magicrc is not None else "sky130A.magicrc"
            command = (
                f"cd {shlex.quote(repo)} && "
                f"magic -dnull -noconsole -rcfile {shlex.quote(magicrc_text)} "
                f"< {shlex.quote(_wsl_path(magic_tcl))} > {shlex.quote(_wsl_path(magic_log))} 2>&1"
            )
            distro = self._resolved_wsl_distro()
            if distro:
                return ["wsl", "-d", str(distro), "bash", "-lc", command]
            return ["wsl", "bash", "-lc", command]
        magicrc_args = ["-rcfile", str(magicrc)] if magicrc is not None else []
        command = (
            f"magic -dnull -noconsole {' '.join(shlex.quote(arg) for arg in magicrc_args)} "
            f"< {shlex.quote(str(magic_tcl))} > {shlex.quote(str(magic_log))} 2>&1"
        )
        return ["bash", "-lc", command]

    def _magic_extract_gds(
        self,
        *,
        gds: Path,
        magic_cell: str,
        out_dir: Path,
        stem: str,
        banner: str,
    ) -> dict[str, Any]:
        out_dir.mkdir(parents=True, exist_ok=True)
        magic_tcl = out_dir / f"{stem}_extract.tcl"
        magic_log = out_dir / f"{stem}_extract.log"
        raw_extracted = out_dir / f"{stem}.spice"
        ext_copy = out_dir / f"{stem}.ext"
        _write_text(
            magic_tcl,
            "\n".join(
                [
                    f'puts "{banner}"',
                    f"gds read {_repo_relative(self.config.repo_root, gds)}",
                    f"if {{[catch {{load {magic_cell}}} load_error]}} {{",
                    f'    puts stderr "ERROR: failed to load {magic_cell}"',
                    "    puts stderr $load_error",
                    "    quit -noprompt",
                    "}",
                    "select top cell",
                    "extract all",
                    "ext2spice lvs",
                    "ext2spice cthresh 0",
                    "ext2spice rthresh 0",
                    "ext2spice",
                    "quit -noprompt",
                    "",
                ]
            ),
            encoding="ascii",
        )
        result = subprocess.run(
            self._magic_extract_command(magic_tcl, magic_log, raw_extracted, ext_copy, magic_cell),
            cwd=self.config.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        wrapper_log = out_dir / f"{stem}_extract.wrapper.log"
        _write_text(wrapper_log, result.stdout or "")
        status = "pass" if result.returncode == 0 and raw_extracted.is_file() else "fail"
        return {
            "status": status,
            "reason": None if status == "pass" else "Magic extraction failed",
            "returncode": result.returncode,
            "magic_tcl": str(magic_tcl),
            "magic_log": str(magic_log),
            "wrapper_log": str(wrapper_log),
            "raw_extracted": str(raw_extracted),
            "ext": str(ext_copy),
        }

    def _run_magic_drc_gds(
        self,
        *,
        gds: Path,
        magic_cell: str,
        out_dir: Path,
        stem: str,
        banner: str,
    ) -> dict[str, Any]:
        out_dir.mkdir(parents=True, exist_ok=True)
        magic_tcl = out_dir / f"{stem}_drc.tcl"
        magic_log = out_dir / f"{stem}_drc.log"
        _write_text(
            magic_tcl,
            "\n".join(
                [
                    f'puts "{banner}"',
                    f"gds read {_repo_relative(self.config.repo_root, gds)}",
                    f"if {{[catch {{load {magic_cell}}} load_error]}} {{",
                    f'    puts stderr "ERROR: failed to load {magic_cell}"',
                    "    puts stderr $load_error",
                    "    quit -noprompt",
                    "}",
                    "drc check",
                    "drc count",
                    "quit -noprompt",
                    "",
                ]
            ),
            encoding="ascii",
        )
        result = subprocess.run(
            self._magic_batch_command(magic_tcl, magic_log),
            cwd=self.config.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        wrapper_log = out_dir / f"{stem}_drc.wrapper.log"
        _write_text(wrapper_log, result.stdout or "")
        drc_count = parse_magic_drc_count(magic_log)
        status = "pass" if result.returncode == 0 and drc_count == 0 else "fail"
        return {
            "status": status,
            "reason": None if status == "pass" else "Magic DRC failed or reported errors",
            "returncode": result.returncode,
            "drc_count": drc_count,
            "magic_tcl": str(magic_tcl),
            "magic_log": str(magic_log),
            "wrapper_log": str(wrapper_log),
        }

    def _run_passive_abs_netgen_trial(
        self,
        *,
        source_abs_netlist: Path,
        candidate_abs_netlist: Path,
        source_top_cell: str,
        candidate_top_cell: str,
        report: Path,
        log: Path,
        summary: Path,
    ) -> dict[str, Any]:
        if not source_abs_netlist.is_file() or not candidate_abs_netlist.is_file():
            return {
                "status": "skipped",
                "reason": "source or candidate passive abstraction netlist missing",
                "report": str(report),
                "log": str(log),
                "summary": str(summary),
                "returncode": None,
            }
        if not self._ic_netgen_lvs_available():
            return {
                "status": "skipped",
                "reason": "IC netgen-lvs not available",
                "report": str(report),
                "log": str(log),
                "summary": str(summary),
                "returncode": None,
            }
        report.parent.mkdir(parents=True, exist_ok=True)
        for stale in (report, log, summary):
            if stale.is_file():
                stale.unlink()
        tcl = report.with_suffix(report.suffix + ".tcl")
        self._write_netgen_lvs_tcl(
            tcl=tcl,
            source_abs_netlist=source_abs_netlist,
            candidate_abs_netlist=candidate_abs_netlist,
            source_top_cell=source_top_cell,
            candidate_top_cell=candidate_top_cell,
            report=report,
        )
        result = subprocess.run(
            self._netgen_lvs_command(tcl=tcl, log=log),
            cwd=self.config.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        wrapper_log = log.with_suffix(log.suffix + ".wrapper.log")
        wrapper_log.write_text(result.stdout or "", encoding="utf-8")
        analyze_status = subprocess.run(
            [
                sys.executable,
                str(self.config.repo_root / "tools" / "sky130_adapter" / "analyze_lvs_result.py"),
                "--report",
                str(report),
                "--log",
                str(log),
                "--output",
                str(summary),
            ],
            cwd=self.config.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        analyze_log = summary.with_suffix(summary.suffix + ".analyze.log")
        analyze_log.write_text(analyze_status.stdout or "", encoding="utf-8")
        status = "pass" if result.returncode == 0 and analyze_status.returncode == 0 else "fail"
        return {
            "status": status,
            "reason": None if status == "pass" else "passive abstraction Netgen trial failed",
            "report": str(report),
            "log": str(log),
            "tcl": str(tcl),
            "wrapper_log": str(wrapper_log),
            "summary": str(summary),
            "analyze_log": str(analyze_log),
            "returncode": result.returncode,
            "analyze_returncode": analyze_status.returncode,
        }

    def _run_route_bridge_full_gds_trial(
        self,
        *,
        compiled: CompiledCandidate,
        variant: str,
        variant_dir: Path,
        input_gds: Path,
        magic_cell: str,
        abstraction_packet_json: Path,
        mos_reference_netlist: Path | None,
    ) -> dict[str, Any]:
        variant_short = (
            variant.replace("_po_second_stage", "")
            .replace("_bridge", "br")
            .replace("_probe", "pr")
            .replace("_", "")
        )[:16] or "variant"
        trial_dir = variant_dir / f"{variant_short}_rb"
        trial_dir.mkdir(parents=True, exist_ok=True)
        route_labelled_gds = trial_dir / "rl.gds"
        route_label_report = trial_dir / "rl.md"
        route_label_log = trial_dir / "rl.log"
        route_label_result = run_route_net_label_injection(
            repo_root=self.config.repo_root,
            input_gds=input_gds,
            gr_file=compiled.case_dir / f"{self.config.top_cell}.gr",
            output_gds=route_labelled_gds,
            report=route_label_report,
            log=route_label_log,
            cell=magic_cell,
            include_pin_shapes=True,
        )
        route_extract = self._magic_extract_gds(
            gds=route_labelled_gds,
            magic_cell=magic_cell,
            out_dir=trial_dir,
            stem="rl",
            banner=f"SKY130_ROUTE_BRIDGE_TRIAL: extracting route labels for {variant}",
        )
        route_mos_report = trial_dir / "rl_mos.md"
        route_mos_summary_json = trial_dir / "rl_mos.json"
        route_mos_log = trial_dir / "rl_mos.log"
        route_mos = run_mos_connectivity_comparison(
            repo_root=self.config.repo_root,
            reference_netlist=mos_reference_netlist,
            candidate_netlist=Path(str(route_extract.get("raw_extracted", ""))),
            netgen_report=trial_dir / "rl_netgen_placeholder.out",
            report=route_mos_report,
            summary_json=route_mos_summary_json,
            log=route_mos_log,
            vdd=str(self.config.data.get("ports", {}).get("vdd", "vdda")),
            vss=str(self.config.data.get("ports", {}).get("vss", "gnda")),
        )
        bridge_gds = trial_dir / "rb.gds"
        bridge_report = trial_dir / "rb.md"
        bridge_summary_json = trial_dir / "rb.json"
        bridge_log = trial_dir / "rb.log"
        bridge_injection = run_mos_route_bridge_injection(
            repo_root=self.config.repo_root,
            input_gds=route_labelled_gds,
            output_gds=bridge_gds,
            cell=magic_cell,
            source_netlist=compiled.netlist_path,
            pin_file=compiled.case_dir / f"{self.config.top_cell}.pin",
            gr_file=compiled.case_dir / f"{self.config.top_cell}.gr",
            placement_log=compiled.case_dir / f"run_{self.config.top_cell}_trial.log",
            mos_connectivity_summary=route_mos_summary_json,
            top_cell=self.config.top_cell,
            max_gap_dbu=int(
                self.config.data.get("verification", {})
                .get("passive_aware", {})
                .get("mos_route_bridge_max_gap_dbu")
                or 200
            ),
            report=bridge_report,
            summary_json=bridge_summary_json,
            log=bridge_log,
        )
        bridge_summary = (
            bridge_injection.get("summary", {})
            if isinstance(bridge_injection.get("summary"), dict)
            else {}
        )
        bridge_count = int(bridge_summary.get("bridge_count") or 0)
        bridge_drc = self._run_magic_drc_gds(
            gds=bridge_gds,
            magic_cell=magic_cell,
            out_dir=trial_dir,
            stem="rb",
            banner=f"SKY130_ROUTE_BRIDGE_TRIAL: DRC for {variant}",
        )
        bridge_extract = self._magic_extract_gds(
            gds=bridge_gds,
            magic_cell=magic_cell,
            out_dir=trial_dir,
            stem="rb",
            banner=f"SKY130_ROUTE_BRIDGE_TRIAL: extracting bridge GDS for {variant}",
        )
        bridge_mos_report = trial_dir / "rb_mos.md"
        bridge_mos_summary_json = trial_dir / "rb_mos.json"
        bridge_mos_log = trial_dir / "rb_mos.log"
        bridge_mos = run_mos_connectivity_comparison(
            repo_root=self.config.repo_root,
            reference_netlist=mos_reference_netlist,
            candidate_netlist=Path(str(bridge_extract.get("raw_extracted", ""))),
            netgen_report=trial_dir / "rb_netgen_placeholder.out",
            report=bridge_mos_report,
            summary_json=bridge_mos_summary_json,
            log=bridge_mos_log,
            vdd=str(self.config.data.get("ports", {}).get("vdd", "vdda")),
            vss=str(self.config.data.get("ports", {}).get("vss", "gnda")),
        )
        formal_trial_dir = trial_dir / "fp"
        formal_report = trial_dir / "fp_prepare.md"
        formal_summary_json = trial_dir / "fp_prepare.json"
        formal_log = trial_dir / "fp_prepare.log"
        formal_prepare = run_passive_aware_lvs_trial_preparation(
            repo_root=self.config.repo_root,
            source_netlist=compiled.netlist_path,
            extracted_netlist=Path(str(bridge_extract.get("raw_extracted", ""))),
            packet_json=abstraction_packet_json,
            out_dir=formal_trial_dir,
            prefix=self.config.top_cell,
            report=formal_report,
            summary_json=formal_summary_json,
            log=formal_log,
            renames=[],
        )
        formal_prepare_summary = (
            formal_prepare.get("summary", {})
            if isinstance(formal_prepare.get("summary"), dict)
            else {}
        )
        formal_source = Path(str(formal_prepare_summary.get("source_output", "")))
        formal_extracted = Path(str(formal_prepare_summary.get("extracted_output", "")))
        formal_netgen_report = trial_dir / "fp_netgen.out"
        formal_netgen_log = trial_dir / "fp_netgen.log"
        formal_lvs_result_summary = trial_dir / "fp_lvs.md"
        formal_netgen = self._run_passive_abs_netgen_trial(
            source_abs_netlist=formal_source,
            candidate_abs_netlist=formal_extracted,
            source_top_cell=self.config.top_cell,
            candidate_top_cell=magic_cell,
            report=formal_netgen_report,
            log=formal_netgen_log,
            summary=formal_lvs_result_summary,
        )
        status = "pass" if (
            bridge_count > 0
            and bridge_drc.get("drc_count") == 0
            and bridge_mos.get("status") == "pass"
            and formal_netgen.get("status") == "pass"
        ) else "fail"
        summary = {
            "schema_version": "route_bridge_full_gds_trial.v1",
            "status": status,
            "reason": None
            if status == "pass"
            else "route bridge full-GDS formal passive trial did not pass all gates",
            "variant": variant,
            "trial_dir": str(trial_dir),
            "route_label_injection_status": route_label_result.get("status"),
            "route_labelled_gds": str(route_labelled_gds),
            "route_labels_mos_connectivity_status": route_mos.get("status"),
            "route_labels_mos_connectivity_summary_json": str(route_mos_summary_json),
            "route_bridge_injection_status": bridge_injection.get("status"),
            "route_bridge_summary_json": str(bridge_summary_json),
            "route_bridge_count": bridge_count,
            "route_bridge_gds": str(bridge_gds),
            "route_bridge_drc_status": bridge_drc.get("status"),
            "route_bridge_drc_count": bridge_drc.get("drc_count"),
            "route_bridge_mos_connectivity_status": bridge_mos.get("status"),
            "route_bridge_mos_connectivity_summary_json": str(bridge_mos_summary_json),
            "formal_passive_lvs_prepare_status": formal_prepare_summary.get("status"),
            "formal_passive_lvs_prepare_summary_json": str(formal_summary_json),
            "formal_passive_lvs_netgen_status": formal_netgen.get("status"),
            "formal_passive_lvs_result_summary": str(formal_lvs_result_summary),
            "native_passive_device_recognition_claimed": False,
            "full_passive_inclusive_gds_lvs_proven": False,
            "artifacts": {
                "route_label_injection_report": str(route_label_report),
                "route_label_injection_log": str(route_label_log),
                "route_labels_extracted_netlist": str(route_extract.get("raw_extracted")),
                "route_labels_mos_connectivity_report": str(route_mos_report),
                "route_labels_mos_connectivity_summary_json": str(route_mos_summary_json),
                "route_bridge_injection_report": str(bridge_report),
                "route_bridge_injection_summary_json": str(bridge_summary_json),
                "route_bridge_injection_log": str(bridge_log),
                "route_bridge_drc_log": str(bridge_drc.get("magic_log")),
                "route_bridge_extracted_netlist": str(bridge_extract.get("raw_extracted")),
                "route_bridge_mos_connectivity_report": str(bridge_mos_report),
                "route_bridge_mos_connectivity_summary_json": str(bridge_mos_summary_json),
                "formal_passive_lvs_preparation_report": str(formal_report),
                "formal_passive_lvs_preparation_summary_json": str(formal_summary_json),
                "formal_passive_netgen_report": str(formal_netgen_report),
                "formal_passive_netgen_log": str(formal_netgen_log),
                "formal_passive_lvs_result_summary": str(formal_lvs_result_summary),
            },
        }
        summary_path = trial_dir / "rb_trial.json"
        _write_text(summary_path, json.dumps(summary, indent=2, sort_keys=True) + "\n")
        summary["summary_json"] = str(summary_path)
        return summary

    def _write_netgen_lvs_tcl(
        self,
        *,
        tcl: Path,
        source_abs_netlist: Path,
        candidate_abs_netlist: Path,
        source_top_cell: str,
        candidate_top_cell: str,
        report: Path,
    ) -> None:
        sky130a = self.layout_config.get("sky130a")
        setup = _join_posix_or_path(str(sky130a), "libs.tech/netgen/sky130A_setup.tcl") if sky130a else ""
        if sys.platform.startswith("win") and shutil.which("wsl"):
            source_text = _wsl_path(source_abs_netlist)
            candidate_text = _wsl_path(candidate_abs_netlist)
            setup_text = _wsl_or_posix_path(setup) if setup else ""
            report_text = _wsl_path(report)
        else:
            source_text = str(source_abs_netlist)
            candidate_text = str(candidate_abs_netlist)
            setup_text = str(setup)
            report_text = str(report)
        tcl.parent.mkdir(parents=True, exist_ok=True)
        tcl.write_text(
            "\n".join(
                [
                    f"lvs {{{source_text} {source_top_cell}}} {{{candidate_text} {candidate_top_cell}}} {{{setup_text}}} {{{report_text}}}",
                    "quit",
                    "",
                ]
            ),
            encoding="ascii",
        )

    def _netgen_lvs_command(
        self,
        *,
        tcl: Path,
        log: Path,
    ) -> list[str]:
        if sys.platform.startswith("win") and shutil.which("wsl"):
            command = (
                "if [ ! -x /usr/bin/netgen-lvs ]; then echo 'netgen-lvs not found at /usr/bin/netgen-lvs' >&2; exit 127; fi; "
                f"/usr/bin/netgen-lvs -batch source {shlex.quote(_wsl_path(tcl))} "
                f"> {shlex.quote(_wsl_path(log))} 2>&1"
            )
            distro = self._resolved_wsl_distro()
            if distro:
                return ["wsl", "-d", str(distro), "--", "bash", "-lc", command]
            return ["wsl", "--", "bash", "-lc", command]
        command = (
            "netgen_cmd=''; "
            "if [ -x /usr/bin/netgen-lvs ]; then netgen_cmd=/usr/bin/netgen-lvs; fi; "
            "if [ -z \"$netgen_cmd\" ] && command -v netgen-lvs >/dev/null 2>&1; then netgen_cmd=netgen-lvs; fi; "
            "if [ -z \"$netgen_cmd\" ] && command -v netgen >/dev/null 2>&1; then "
            "candidate=$(command -v netgen); "
            "version_out=$(\"$candidate\" -batch quit 2>&1 || true); "
            "if printf '%s\\n' \"$version_out\" | grep -q 'Netgen 1\\.'; then netgen_cmd=\"$candidate\"; fi; "
            "fi; "
            "if [ -z \"$netgen_cmd\" ]; then echo 'IC netgen-lvs not found' >&2; exit 127; fi; "
            f"\"$netgen_cmd\" -batch source {shlex.quote(str(tcl))} "
            f"> {shlex.quote(str(log))} 2>&1"
        )
        return ["bash", "-lc", command]

    def _ic_netgen_lvs_available(self) -> bool:
        distro = self._resolved_wsl_distro()
        if sys.platform.startswith("win") and shutil.which("wsl") and distro:
            check = (
                "if command -v netgen-lvs >/dev/null 2>&1; then exit 0; fi; "
                "if command -v netgen >/dev/null 2>&1; then "
                "candidate=$(command -v netgen); "
                "version_out=$(\"$candidate\" -batch quit 2>&1 || true); "
                "printf '%s\\n' \"$version_out\" | grep -q 'Netgen 1\\.'; "
                "exit $?; "
                "fi; "
                "exit 1"
            )
            result = subprocess.run(
                [
                    "wsl",
                    "-d",
                    str(distro),
                    "--",
                    "bash",
                    "-lc",
                    check,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                return True
        if shutil.which("netgen-lvs") is not None:
            return True
        netgen = shutil.which("netgen")
        if netgen is None:
            return False
        try:
            result = subprocess.run(
                [netgen, "-batch", "quit"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return "Netgen 1." in (result.stdout or "")

    def _command_available(self, command_name: str | tuple[str, ...]) -> bool:
        command_names = (command_name,) if isinstance(command_name, str) else command_name
        distro = self._resolved_wsl_distro()
        if sys.platform.startswith("win") and shutil.which("wsl") and distro:
            check = " || ".join(
                f"command -v {shlex.quote(name)} >/dev/null 2>&1" for name in command_names
            )
            result = subprocess.run(
                [
                    "wsl",
                    "-d",
                    str(distro),
                    "--",
                    "bash",
                    "-lc",
                    check,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                return True
        return any(shutil.which(name) is not None for name in command_names)

    def find_extracted_netlist(self, compiled: CompiledCandidate) -> Path | None:
        candidates = list(compiled.out_dir.glob(f"**/{self.config.top_cell}_extracted.raw.spice"))
        candidates += list(compiled.out_dir.glob(f"**/{self.config.top_cell}_extracted.spice"))
        return candidates[0] if candidates else None

    def _command(self, compiled: CompiledCandidate) -> list[str]:
        ports = self.config.data.get("ports", {})
        if sys.platform.startswith("win") and shutil.which("wsl"):
            return self._wsl_shell_command(compiled, ports)
        cmd = [
            sys.executable,
            str(self.pipeline),
            "--netlist",
            str(compiled.netlist_path),
            "--top-cell",
            self.config.top_cell,
            "--case-name",
            f"{self.config.design_id}_{compiled.candidate_id}",
            "--vdd",
            str(ports.get("vdd", "vdda")),
            "--vss",
            str(ports.get("vss", "gnda")),
            "--out-dir",
            str(compiled.out_dir),
            "--case-dir",
            str(compiled.case_dir),
            "--config",
            str(compiled.config_path),
            "--convert-xschem",
            "no",
            "--keep-going",
        ]
        output_node = ports.get("output")
        if output_node:
            cmd.extend(["--output-node", str(output_node)])
        docker_image = self.layout_config.get("docker_image")
        if docker_image:
            cmd.extend(["--docker-image", str(docker_image)])
        return cmd

    def _runtime_preflight(self, compiled: CompiledCandidate) -> EvidencePacket | None:
        required_magic = self.layout_config.get("required_magic_version")
        if not required_magic:
            return None
        status, output = self._magic_version_output()
        current_magic = _parse_version(output)
        required_tuple = _parse_version(str(required_magic))
        if status == 0 and current_magic is not None and required_tuple is not None and not _version_lt(current_magic, required_tuple):
            return None
        message = (
            f"Magic version preflight failed: required >= {required_magic}, "
            f"current={output.strip() or 'not found'}"
        )
        return EvidencePacket(
            candidate_id=compiled.candidate_id,
            stage="layout_verification",
            fidelity="E2",
            status="fail",
            verification_scope=self.config.verification_scope,
            metrics={
                "pipeline_status": "FAIL",
                "failed_stage": "setup",
                "message": message,
            },
            physical_feedback={
                "verification_scope": self.config.verification_scope,
                "runtime_failure": True,
                "failed_stage": "setup",
                "message": message,
                "required_magic_version": str(required_magic),
                "current_magic_version": output.strip(),
            },
            artifacts={"out_dir": str(compiled.out_dir)},
            messages=[message],
        )

    def _magic_version_output(self) -> tuple[int, str]:
        if sys.platform.startswith("win") and shutil.which("wsl"):
            distro = self._resolved_wsl_distro()
            cmd = ["wsl"]
            if distro:
                cmd.extend(["-d", str(distro)])
            cmd.extend(["bash", "-lc", "magic --version 2>&1 | head -1"])
        else:
            cmd = ["magic", "--version"]
        result = subprocess.run(
            cmd,
            cwd=self.config.repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, (result.stdout or result.stderr or "")

    def _wsl_shell_command(self, compiled: CompiledCandidate, ports: dict[str, Any]) -> list[str]:
        script = self.config.repo_root / "tools" / "sky130_adapter" / "run_sky130_case_pipeline.sh"
        args = [
            _wsl_path(script),
            "--case-name",
            f"{self.config.design_id}_{compiled.candidate_id}",
            "--case-dir",
            _wsl_path(compiled.case_dir),
            "--top-cell",
            self.config.top_cell,
            "--magical-netlist",
            _wsl_path(compiled.netlist_path),
            "--config",
            _wsl_path(compiled.config_path),
            "--vdd",
            str(ports.get("vdd", "vdda")),
            "--vss",
            str(ports.get("vss", "gnda")),
            "--out-dir",
            _wsl_path(compiled.out_dir),
            "--convert-xschem",
            "no",
        ]
        output_node = ports.get("output")
        if output_node:
            args.extend(["--output-node", str(output_node)])
        docker_image = self.layout_config.get("docker_image")
        exports = ""
        sky130a = self.layout_config.get("sky130a")
        if sky130a:
            exports += f"SKY130A={shlex.quote(str(sky130a))} "
        if docker_image:
            exports += f"DOCKER_IMAGE={shlex.quote(str(docker_image))} "
        for key, value in sorted(self._magical_env_overrides(compiled).items()):
            exports += f"{key}={shlex.quote(str(value))} "
        command = (
            f"cd {shlex.quote(_wsl_path(self.config.repo_root))} && "
            f"{exports}{' '.join(shlex.quote(arg) for arg in args)}"
        )
        distro = self._resolved_wsl_distro()
        if distro:
            return ["wsl", "-d", str(distro), "bash", "-lc", command]
        return ["wsl", "bash", "-lc", command]

    def _magical_env_overrides(self, compiled: CompiledCandidate) -> dict[str, str]:
        overrides: dict[str, str] = {}
        configured = self.layout_config.get("magical_env", {})
        if isinstance(configured, dict):
            overrides.update({str(key): str(value) for key, value in configured.items()})
        if self._compiled_config_has_passive_probe(compiled):
            passive_config = self.config.data.get("verification", {}).get("passive_aware", {})
            if isinstance(passive_config, dict):
                passive_env = passive_config.get("magical_env", {})
                if isinstance(passive_env, dict):
                    overrides.update({str(key): str(value) for key, value in passive_env.items()})
        for key in MAGICAL_ENV_KEYS:
            if key in os.environ and key not in overrides:
                overrides[key] = os.environ[key]
        return overrides

    @staticmethod
    def _compiled_config_has_passive_probe(compiled: CompiledCandidate) -> bool:
        if not compiled.config_path.is_file():
            return False
        try:
            data = json.loads(compiled.config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        return bool(data.get("passiveAwareProbe", False))

    def _metrics(self, fields: dict[str, str]) -> dict[str, Any]:
        return {
            "pipeline_status": fields.get("STATUS"),
            "failed_stage": fields.get("FAILED_STAGE"),
            "message": fields.get("MESSAGE"),
            "layout_input_mode": fields.get("LAYOUT_INPUT_MODE"),
            "layout_projection_dropped_passives": _parse_int(fields.get("LAYOUT_PROJECTION_DROPPED_PASSIVES")),
            "magical_sanitize_place_gds_for_router": fields.get("MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER"),
            "magical_skip_router_parse_gds": fields.get("MAGICAL_SKIP_ROUTER_PARSE_GDS"),
            "magical_skip_top_power_route": fields.get("MAGICAL_SKIP_TOP_POWER_ROUTE"),
            "magical_power_stripe_extra_grid": _parse_int(fields.get("MAGICAL_POWER_STRIPE_EXTRA_GRID")),
            "magical_power_stripe_extra_dbu": _parse_int(fields.get("MAGICAL_POWER_STRIPE_EXTRA_DBU")),
            "magical_disable_power_stripe": fields.get("MAGICAL_DISABLE_POWER_STRIPE"),
            "magical_split_power_stripe_around_passives": fields.get(
                "MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES"
            ),
            "magical_power_stripe_passive_keep_out_dbu": _parse_int(
                fields.get("MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU")
            ),
            "magical_router_passive_obstruction_layers": fields.get(
                "MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS"
            ),
            "magical_router_passive_obstruction_margin_dbu": _parse_int(
                fields.get("MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU")
            ),
            "magical_passive_placement_offset_x_dbu": _parse_int(
                fields.get("MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU")
            ),
            "magical_passive_placement_offset_y_dbu": _parse_int(
                fields.get("MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU")
            ),
            "drc_count": _parse_int(fields.get("DRC_COUNT")),
            "lvs_match": fields.get("CONNECTIVITY_LVS_MATCH"),
            "lvs_mode": fields.get("LVS_MODE"),
            "netgen_exit_status": _parse_int(fields.get("NETGEN_EXIT_STATUS")),
            "pex_caps": _parse_int(fields.get("PEX_CAPS")),
            "pex_total_cap_ff": parse_cap_ff(fields.get("PEX_TOTAL_CAP_FF")),
            "pex_output_node": fields.get("PEX_OUTPUT_NODE"),
        }

    def _physical_feedback(self, fields: dict[str, str], returncode: int) -> dict[str, Any]:
        metrics = self._metrics(fields)
        return {
            "verification_scope": self.config.verification_scope,
            "lvs_scope_note": "MOS-only projection; passive-aware LVS/PEX is not claimed.",
            "layout_pipeline_returncode": returncode,
            "runtime_failure": _is_runtime_failure(fields),
            **metrics,
        }

    def _status(self, returncode: int, fields: dict[str, str]) -> str:
        drc = _parse_int(fields.get("DRC_COUNT"))
        lvs_match = str(fields.get("CONNECTIVITY_LVS_MATCH", "")).lower() == "yes"
        if returncode == 0 and drc == 0 and lvs_match:
            return "pass"
        if returncode == 0 and not fields:
            return "unknown"
        return "fail"


def _parse_int(raw: str | None) -> int | None:
    if raw in (None, ""):
        return None
    try:
        return int(str(raw).strip())
    except ValueError:
        return None


def _is_runtime_failure(fields: dict[str, str]) -> bool:
    message = str(fields.get("MESSAGE", "")).lower()
    failed_stage = str(fields.get("FAILED_STAGE", "")).lower()
    return "command failed" in message or failed_stage in {"setup", "magic_drc"}


def _passive_integrity_interpretation(
    *,
    probe_returncode: int,
    probe_pipeline_status: str | None,
    probe_failed_stage: str | None,
    remap_report_present: bool,
    magic_extract_log_present: bool,
    raw_extracted_present: bool,
    source_passives: int,
    generated_passive_gds: int,
    dropped_passives: int | None,
    extracted_physical_passives: int,
    extracted_intentional_passives: int,
    passive_tbd_layer_count: int,
    magic_unknown_layer_count: int,
) -> str:
    if source_passives == 0:
        return "No intentional source passives were present, so passive-aware LVS is not exercised by this candidate."
    if probe_returncode != 0 or str(probe_pipeline_status or "").upper() == "FAIL":
        failed_stage = probe_failed_stage or "unknown"
        artifacts = (
            f"remap_report={'present' if remap_report_present else 'missing'}, "
            f"magic_extract_log={'present' if magic_extract_log_present else 'missing'}, "
            f"raw_extracted_netlist={'present' if raw_extracted_present else 'missing'}"
        )
        return (
            "Passive-aware LVS/PEX is not proven: full extraction probe stopped before "
            f"closure at stage {failed_stage} with return code {probe_returncode}; {artifacts}."
        )
    if (
        generated_passive_gds >= source_passives
        and extracted_physical_passives >= source_passives
        and extracted_intentional_passives >= source_passives
        and dropped_passives == 0
        and passive_tbd_layer_count == 0
        and magic_unknown_layer_count == 0
    ):
        return "Source intentional passives were generated, remapped, extracted, and preserved for full passive-aware LVS."
    reasons: list[str] = []
    if generated_passive_gds < source_passives:
        reasons.append(
            f"MAGICAL generated {generated_passive_gds}/{source_passives} expected passive GDS files"
        )
    if passive_tbd_layer_count:
        reasons.append(f"{passive_tbd_layer_count} passive-related GDS layer/datatype pairs remain TBD in Sky130 remap")
    if magic_unknown_layer_count:
        reasons.append(f"Magic reported {magic_unknown_layer_count} unknown passive-related layer/datatype pairs")
    if extracted_intentional_passives < source_passives:
        if extracted_physical_passives >= source_passives:
            reasons.append(
                f"raw extraction produced {extracted_physical_passives} physical passive devices, "
                f"but preserved only {extracted_intentional_passives}/{source_passives} source passive instances"
            )
        else:
            reasons.append(
                f"raw extraction preserved {extracted_intentional_passives}/{source_passives} intentional passive devices"
            )
    if dropped_passives is None:
        reasons.append("LVS preparation did not report source passive preservation status")
    elif dropped_passives:
        reasons.append(f"LVS preparation dropped {dropped_passives} unsupported source passive devices")
    if not reasons:
        reasons.append("full extraction LVS did not match the source netlist")
    return "Passive-aware LVS/PEX is not proven: " + "; ".join(reasons) + "."


def _parse_version(raw: str) -> tuple[int, ...] | None:
    match = re.search(r"(\d+(?:\.\d+)+)", raw)
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def _version_lt(current: tuple[int, ...], required: tuple[int, ...]) -> bool:
    width = max(len(current), len(required))
    lhs = current + (0,) * (width - len(current))
    rhs = required + (0,) * (width - len(required))
    return lhs < rhs


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _parse_wsl_distro_lines(raw: str) -> list[str]:
    clean = raw.replace("\x00", "")
    distros: list[str] = []
    for item in clean.splitlines():
        line = item.strip().lstrip("* ").strip()
        if not line or line.startswith("wsl:"):
            continue
        lower = line.lower()
        if lower.startswith("name ") or " version" in lower:
            continue
        distros.append(line)
    return distros


def _choose_wsl_distro(explicit: str | None = None) -> str | None:
    if explicit:
        return explicit
    env_distro = os.environ.get("MAGICAL_WSL_DISTRO") or os.environ.get("SKY130_WSL_DISTRO")
    if env_distro:
        return env_distro
    if not (sys.platform.startswith("win") and shutil.which("wsl")):
        return None
    result = subprocess.run(
        ["wsl", "-l", "-q"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return None
    distros = _parse_wsl_distro_lines(result.stdout or "")
    for distro in distros:
        if not distro.lower().startswith("docker-desktop"):
            return distro
    return distros[0] if distros else None


def _join_posix_or_path(base: str, suffix: str) -> Path | str:
    if base.startswith("/"):
        return base.rstrip("/") + "/" + suffix
    return Path(base) / suffix


def _wsl_or_posix_path(path: Path | str) -> str:
    if isinstance(path, str) and path.startswith("/"):
        return path
    return _wsl_path(Path(path))


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if drive:
        rest = str(resolved)[3:].replace("\\", "/")
        return f"/mnt/{drive}/{rest}"
    return str(resolved).replace("\\", "/")
