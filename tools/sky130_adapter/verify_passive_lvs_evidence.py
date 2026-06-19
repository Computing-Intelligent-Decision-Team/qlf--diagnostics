#!/usr/bin/env python3
"""Verify formal passive LVS evidence produced by the Sky130 adapter probes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


RESISTOR_CANDIDATE_TYPE = "segmented_resistor_chain_source_equivalent"
CAPACITOR_CANDIDATE_TYPE = "plate_coupling_capacitor_source_equivalent"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify passive LVS evidence from a variant summary.")
    parser.add_argument("--resistor-summary-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument(
        "--require-resistor",
        action="store_true",
        help="Require a formal resistor abstraction candidate and primitive R device.",
    )
    parser.add_argument(
        "--require-capacitor",
        action="store_true",
        help="Require a formal capacitor abstraction candidate and primitive C device.",
    )
    return parser.parse_args()


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _path_from(value: Any) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    return path if path.is_file() else None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "pass"}
    return bool(value)


def _pass_status(value: Any) -> bool:
    return str(value or "").strip().lower() == "pass"


def _int_value(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _native_full_passive_lvs_pass(summary: dict[str, Any]) -> bool:
    native_status = str(
        summary.get("best_native_passive_device_recognition_status")
        or summary.get("native_passive_device_recognition_status")
        or summary.get("best_full_passive_inclusive_gds_native_lvs_status")
        or summary.get("full_passive_inclusive_gds_native_lvs_status")
        or ""
    ).lower()
    native_claimed = _truthy(
        summary.get("best_native_passive_device_recognition_claimed")
        or summary.get("native_passive_device_recognition_claimed")
        or summary.get("full_passive_inclusive_gds_lvs_proven")
    )
    native_recognition_pass = native_claimed and native_status in {
        "pass",
        "native_passive_device_recognition_pass",
        "full_passive_inclusive_gds_lvs_pass",
    }
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


def _native_passive_recognition_claimed(summary: dict[str, Any]) -> bool:
    native_status = str(
        summary.get("best_native_passive_device_recognition_status")
        or summary.get("native_passive_device_recognition_status")
        or ""
    ).lower()
    return native_status in {"pass", "native_passive_device_recognition_pass"} and _truthy(
        summary.get("best_native_passive_device_recognition_claimed")
        or summary.get("native_passive_device_recognition_claimed")
    )


def passive_primitive_counts(path: Path | None) -> dict[str, int]:
    counts = {"resistor": 0, "capacitor": 0, "total": 0}
    if path is None or not path.is_file():
        return counts
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("*", ".")):
            continue
        if re.match(r"^[Rr]\S+\s+", stripped):
            counts["resistor"] += 1
            counts["total"] += 1
        elif re.match(r"^[Cc]\S+\s+", stripped):
            counts["capacitor"] += 1
            counts["total"] += 1
    return counts


def _candidate_types(packet_verification: dict[str, Any]) -> set[str]:
    types: set[str] = set()
    checks = packet_verification.get("candidate_checks", [])
    if not isinstance(checks, list):
        return types
    for check in checks:
        if isinstance(check, dict) and check.get("candidate_type"):
            types.add(str(check.get("candidate_type")))
    return types


def _lvs_primitive_abstractions(packet_verification: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    checks = packet_verification.get("candidate_checks", [])
    if not isinstance(checks, list):
        return records
    for check in checks:
        if not isinstance(check, dict):
            continue
        primitive_class = check.get("lvs_primitive_device_class")
        primitive_kind = check.get("lvs_primitive_kind")
        candidate_type = str(check.get("candidate_type", ""))
        if not primitive_class:
            if candidate_type == RESISTOR_CANDIDATE_TYPE:
                primitive_class = "r"
                primitive_kind = "resistor"
            elif candidate_type == CAPACITOR_CANDIDATE_TYPE:
                primitive_class = "c"
                primitive_kind = "capacitor"
        if not primitive_class:
            continue
        records.append(
            {
                "source_instance": check.get("source_instance"),
                "candidate_type": check.get("candidate_type"),
                "abstraction_rule": check.get("abstraction_rule"),
                "support_type": check.get("support_type"),
                "lvs_primitive_device_class": str(primitive_class),
                "lvs_primitive_kind": primitive_kind,
                "lvs_primitive_spice": check.get("lvs_primitive_spice"),
                "electrical_terminals": check.get("electrical_terminals"),
            }
        )
    return records


def _formal_requirements(
    *,
    summary: dict[str, Any],
    packet_verification: dict[str, Any],
    source_counts: dict[str, int],
    candidate_counts: dict[str, int],
    require_resistor: bool,
    require_capacitor: bool,
) -> dict[str, bool]:
    candidate_types = _candidate_types(packet_verification)
    packet_formal_ready = _truthy(
        packet_verification.get("formal_lvs_abstraction_ready")
        if packet_verification
        else summary.get("best_formal_lvs_abstraction_ready")
    )
    all_source_passives_have_candidate = _truthy(
        packet_verification.get("all_source_passives_have_candidate")
        if packet_verification
        else summary.get("best_all_source_passives_have_candidate")
    )
    primitive_netlists_present = source_counts["total"] > 0 and candidate_counts["total"] > 0
    primitive_counts_match = (
        source_counts["resistor"] == candidate_counts["resistor"]
        and source_counts["capacitor"] == candidate_counts["capacitor"]
        and source_counts["total"] == candidate_counts["total"]
    )
    resistor_formalized = (
        RESISTOR_CANDIDATE_TYPE in candidate_types
        and source_counts["resistor"] > 0
        and candidate_counts["resistor"] == source_counts["resistor"]
    )
    capacitor_formalized = (
        CAPACITOR_CANDIDATE_TYPE in candidate_types
        and source_counts["capacitor"] > 0
        and candidate_counts["capacitor"] == source_counts["capacitor"]
    )
    return {
        "packet_formal_lvs_abstraction_ready": packet_formal_ready,
        "all_source_passives_have_candidate": all_source_passives_have_candidate,
        "primitive_netlists_present": primitive_netlists_present,
        "primitive_counts_match": primitive_counts_match,
        "passive_only_netgen_lvs_pass": _pass_status(summary.get("best_passive_abs_netgen_status")),
        "hybrid_mos_reference_passive_netgen_lvs_pass": _pass_status(
            summary.get("best_hybrid_mos_passive_lvs_trial_netgen_status")
        ),
        "segmented_resistor_chain_formalized": resistor_formalized if require_resistor else True,
        "cfmom_plate_coupling_formalized": capacitor_formalized if require_capacitor else True,
    }


def _route_bridge_requirements(summary: dict[str, Any]) -> dict[str, bool]:
    return {
        "route_bridge_inserted": str(summary.get("best_route_bridge_injection_status") or "").lower()
        == "bridges_inserted",
        "route_bridge_drc_clean": _int_value(summary.get("best_route_bridge_drc_count")) == 0,
        "route_bridge_mos_connectivity_pass": _pass_status(
            summary.get("best_route_bridge_mos_connectivity_status")
        ),
        "route_bridge_formal_passive_lvs_pass": _pass_status(
            summary.get("best_route_bridge_formal_passive_lvs_netgen_status")
        ),
    }


def _native_recognition_from_abstraction_summary(abstraction_summary: dict[str, Any]) -> dict[str, Any]:
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


def _native_passive_recognition_summary(summary: dict[str, Any]) -> dict[str, Any]:
    existing = summary.get("best_native_passive_device_recognition") or summary.get(
        "native_passive_device_recognition"
    )
    if isinstance(existing, dict) and existing.get("status"):
        return existing
    status = summary.get("best_native_passive_device_recognition_status") or summary.get(
        "native_passive_device_recognition_status"
    )
    if status:
        return {
            "status": status,
            "claimable": _truthy(
                summary.get("best_native_passive_device_recognition_claimed")
                or summary.get("native_passive_device_recognition_claimed")
            ),
            "missing_source_passive_instances": summary.get(
                "best_native_passive_device_recognition_missing_instances"
            )
            or summary.get("native_passive_device_recognition_missing_instances"),
            "blockers_by_instance": summary.get("best_native_passive_device_recognition_blockers")
            or summary.get("native_passive_device_recognition_blockers"),
            "scope": "native_magic_extraction_device_recognition",
        }
    results = summary.get("results", [])
    if isinstance(results, list):
        best_variant = summary.get("best_variant")
        selected = None
        for result in results:
            if not isinstance(result, dict) or not isinstance(result.get("abstraction_summary"), dict):
                continue
            if best_variant is None or result.get("variant") == best_variant:
                selected = result
                break
        if selected is not None:
            return _native_recognition_from_abstraction_summary(selected["abstraction_summary"])
    return {
        "status": "unknown",
        "claimable": False,
        "reason": "native passive recognition evidence is missing",
        "missing_source_passive_instances": None,
        "blockers_by_instance": None,
        "scope": "native_magic_extraction_device_recognition",
    }


def verify_evidence(
    summary: dict[str, Any],
    *,
    require_resistor: bool = False,
    require_capacitor: bool = False,
) -> dict[str, Any]:
    packet_verification_path = _path_from(summary.get("best_abstraction_packet_verification_json"))
    packet_verification = _read_json(packet_verification_path)
    lvs_primitive_abstractions = _lvs_primitive_abstractions(packet_verification)
    source_abs_path = _path_from(summary.get("best_abstraction_source_passive_abs_netlist"))
    candidate_abs_path = _path_from(summary.get("best_abstraction_candidate_passive_abs_netlist"))
    source_counts = passive_primitive_counts(source_abs_path)
    candidate_counts = passive_primitive_counts(candidate_abs_path)
    requirements = _formal_requirements(
        summary=summary,
        packet_verification=packet_verification,
        source_counts=source_counts,
        candidate_counts=candidate_counts,
        require_resistor=require_resistor,
        require_capacitor=require_capacitor,
    )
    formal_pass = all(requirements.values())
    full_gds_formal_abstraction_pass = _pass_status(
        summary.get("best_passive_aware_lvs_trial_netgen_status")
    )
    native_recognition = _native_passive_recognition_summary(summary)
    enriched_summary = {
        **summary,
        "best_native_passive_device_recognition_status": native_recognition.get("status"),
        "best_native_passive_device_recognition_claimed": native_recognition.get("claimable"),
    }
    full_gds_native_pass = _native_full_passive_lvs_pass(enriched_summary)
    native_recognition_claimed = _native_passive_recognition_claimed(enriched_summary)
    route_bridge_requirements = _route_bridge_requirements(summary)
    route_bridge_pass = all(route_bridge_requirements.values())
    if full_gds_native_pass:
        status = "full_passive_inclusive_gds_lvs_pass"
        scope = "full_passive_inclusive_gds_lvs"
    elif formal_pass and full_gds_formal_abstraction_pass:
        status = "formal_passive_lvs_evidence_pass"
        scope = "formal_passive_abstraction_with_full_gds_mos"
    elif formal_pass and route_bridge_pass:
        status = "formal_passive_lvs_evidence_pass"
        scope = "formal_passive_abstraction_with_gds_mos_bridge"
    elif formal_pass:
        status = "formal_passive_lvs_evidence_pass"
        scope = "formal_passive_abstraction_with_mos_only_projection"
    else:
        status = "formal_passive_lvs_evidence_incomplete"
        scope = "mos_only_projection"
    failed = sorted(key for key, passed in requirements.items() if not passed)
    return {
        "schema_version": "passive_lvs_evidence_verification.v1",
        "status": status,
        "verification_scope": scope,
        "formal_passive_lvs_evidence_pass": formal_pass,
        "full_gds_formal_passive_lvs_evidence_pass": formal_pass
        and full_gds_formal_abstraction_pass,
        "route_bridge_formal_passive_lvs_evidence_pass": formal_pass and route_bridge_pass,
        "full_passive_inclusive_gds_lvs_proven": full_gds_native_pass,
        "native_passive_device_recognition_status": native_recognition.get("status"),
        "native_passive_device_recognition_claimed": native_recognition_claimed,
        "native_passive_device_recognition_missing_instances": native_recognition.get(
            "missing_source_passive_instances"
        ),
        "native_passive_device_recognition_blockers": native_recognition.get(
            "blockers_by_instance"
        ),
        "native_passive_device_recognition_summary": native_recognition,
        "failed_requirements": failed,
        "requirements": requirements,
        "route_bridge_requirements": route_bridge_requirements,
        "source_passive_primitive_counts": source_counts,
        "candidate_passive_primitive_counts": candidate_counts,
        "lvs_primitive_abstractions": lvs_primitive_abstractions,
        "packet_verification_json": str(packet_verification_path) if packet_verification_path else None,
        "source_passive_abstraction_netlist": str(source_abs_path) if source_abs_path else None,
        "candidate_passive_abstraction_netlist": str(candidate_abs_path) if candidate_abs_path else None,
        "passive_only_lvs_result_summary": summary.get("best_passive_abs_lvs_result_summary"),
        "hybrid_lvs_result_summary": summary.get("best_hybrid_mos_passive_lvs_trial_result_summary"),
        "route_bridge_trial_summary": summary.get("best_route_bridge_trial_summary_json"),
        "route_bridge_lvs_result_summary": summary.get(
            "best_route_bridge_formal_passive_lvs_result_summary"
        ),
        "full_gds_lvs_result_summary": summary.get("best_passive_aware_lvs_trial_result_summary"),
        "limitations": [
            "Formal passive LVS evidence proves source-equivalent primitive R/C abstraction plus Netgen matching.",
            "Native passive device recognition is reported separately from full passive-inclusive GDS LVS closure.",
            "Full passive-inclusive GDS LVS is proven only when full_passive_inclusive_gds_lvs_proven is true.",
        ],
    }


def render_report(summary: dict[str, Any], input_summary: Path) -> str:
    req = summary.get("requirements", {})
    route_req = summary.get("route_bridge_requirements", {})
    lines = [
        "# Passive LVS Evidence Verification",
        "",
        "## Summary",
        "",
        f"- Input summary: `{input_summary}`",
        f"- Status: `{summary.get('status')}`",
        f"- Verification scope: `{summary.get('verification_scope')}`",
        f"- Formal passive LVS evidence pass: `{summary.get('formal_passive_lvs_evidence_pass')}`",
        f"- Full-GDS formal passive LVS evidence pass: `{summary.get('full_gds_formal_passive_lvs_evidence_pass')}`",
        f"- Route-bridge formal passive LVS evidence pass: `{summary.get('route_bridge_formal_passive_lvs_evidence_pass')}`",
        f"- Full passive-inclusive GDS LVS proven: `{summary.get('full_passive_inclusive_gds_lvs_proven')}`",
        f"- Native passive device recognition status: `{summary.get('native_passive_device_recognition_status')}`",
        f"- Native passive device recognition claimed: `{summary.get('native_passive_device_recognition_claimed')}`",
        f"- Native passive missing instances: `{summary.get('native_passive_device_recognition_missing_instances')}`",
        f"- Failed requirements: `{', '.join(summary.get('failed_requirements', [])) or 'none'}`",
        "",
        "## Requirements",
        "",
        "| Requirement | Pass |",
        "| --- | --- |",
    ]
    for key in sorted(req):
        lines.append(f"| `{key}` | `{req[key]}` |")
    lines.extend(
        [
            "",
            "## Route Bridge Gates",
            "",
            "| Gate | Pass |",
            "| --- | --- |",
        ]
    )
    for key in sorted(route_req):
        lines.append(f"| `{key}` | `{route_req[key]}` |")
    lines.extend(
        [
            "",
            "## Primitive Counts",
            "",
            f"- Source abstraction: `{summary.get('source_passive_primitive_counts')}`",
            f"- Candidate abstraction: `{summary.get('candidate_passive_primitive_counts')}`",
            f"- Primitive abstraction records: `{summary.get('lvs_primitive_abstractions')}`",
            "",
            "## Interpretation",
            "",
            "A formal pass means segmented resistor chains and cfmom plate-coupling evidence have been promoted into primitive LVS R/C devices and have passed Netgen in both passive-only and MOS-reference hybrid trials.",
            "",
            "This is still distinct from native full-GDS passive-aware LVS. Native proof is reported only when `native_passive_device_recognition_claimed=true`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    input_summary = _read_json(args.resistor_summary_json)
    summary = verify_evidence(
        input_summary,
        require_resistor=args.require_resistor,
        require_capacitor=args.require_capacitor,
    )
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(summary, args.resistor_summary_json), encoding="utf-8")
    print(f"status={summary['status']}")
    print(f"formal_passive_lvs_evidence_pass={summary['formal_passive_lvs_evidence_pass']}")
    print(f"full_passive_inclusive_gds_lvs_proven={summary['full_passive_inclusive_gds_lvs_proven']}")
    return 0 if summary["formal_passive_lvs_evidence_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
