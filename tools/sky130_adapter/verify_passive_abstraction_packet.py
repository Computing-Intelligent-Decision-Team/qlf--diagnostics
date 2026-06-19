#!/usr/bin/env python3
"""Verify a passive abstraction packet against the source netlist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from prepare_lvs_netlists import SourcePassive, parse_source_passives


FORMAL_RESISTOR_ABSTRACTION_BLOCKERS = {
    "source_resistor_requires_segmented_chain_abstraction",
}
FORMAL_CAPACITOR_ABSTRACTION_BLOCKERS = {
    "source_capacitor_requires_plate_coupling_abstraction",
    "coordinate_matched_devices_are_resistor_markers_not_capacitor",
    "source_capacitor_touches_extracted_resistor_markers_not_a_capacitor_device",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify passive abstraction packet structure.")
    parser.add_argument("--source-netlist", type=Path, required=True)
    parser.add_argument("--packet-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--top-cell", default="passive_abstraction")
    parser.add_argument("--source-abstraction-netlist", type=Path)
    parser.add_argument("--candidate-abstraction-netlist", type=Path)
    return parser.parse_args()


def candidate_line_matches_source(line: str, source: SourcePassive) -> bool:
    tokens = line.replace("(", " ").replace(")", " ").split()
    expected = [source.instance] + list(source.terminals) + [source.model]
    return tokens[: len(expected)] == expected


def _candidate_support_status(candidate: dict[str, Any]) -> dict[str, Any]:
    candidate_type = str(candidate.get("candidate_type", ""))
    if candidate_type == "segmented_resistor_chain_source_equivalent":
        chain = candidate.get("chain", {})
        present = bool(isinstance(chain, dict) and chain.get("present"))
        device_count = int(chain.get("device_count") or 0) if isinstance(chain, dict) else 0
        return {
            "support_type": "segmented_resistor_chain",
            "support_verified": present and device_count > 0,
            "abstraction_rule": "collapse_segmented_resistor_chain_to_lvs_resistor",
            "support_detail": {
                "device_count": device_count,
                "start_net": chain.get("start_net") if isinstance(chain, dict) else None,
                "end_net": chain.get("end_net") if isinstance(chain, dict) else None,
            },
        }
    if candidate_type == "plate_coupling_capacitor_source_equivalent":
        cap_count = int(candidate.get("coupling_capacitor_count") or 0)
        cap_ff = float(candidate.get("coupling_capacitance_ff") or 0.0)
        return {
            "support_type": "plate_coupling_capacitance",
            "support_verified": cap_count > 0 and cap_ff > 0.0,
            "abstraction_rule": "collapse_plate_coupling_evidence_to_lvs_capacitor",
            "support_detail": {
                "coupling_capacitor_count": cap_count,
                "coupling_capacitance_ff": cap_ff,
                "plate_node_counts": candidate.get("plate_node_counts"),
            },
        }
    return {
        "support_type": "unknown",
        "support_verified": False,
        "abstraction_rule": None,
        "support_detail": {"candidate_type": candidate_type},
    }


def _formalized_blockers_for_candidate(candidate: dict[str, Any]) -> set[str]:
    candidate_type = str(candidate.get("candidate_type", ""))
    if candidate_type == "segmented_resistor_chain_source_equivalent":
        return FORMAL_RESISTOR_ABSTRACTION_BLOCKERS
    if candidate_type == "plate_coupling_capacitor_source_equivalent":
        return FORMAL_CAPACITOR_ABSTRACTION_BLOCKERS
    return set()


def _is_formalized_blocker(candidate: dict[str, Any], blocker: str) -> bool:
    if blocker.startswith("body_or_substrate_pin_has_no_magical_geometry:"):
        return str(candidate.get("candidate_type", "")) == "segmented_resistor_chain_source_equivalent"
    return blocker in _formalized_blockers_for_candidate(candidate)


def passive_kind(model: str) -> str:
    lowered = model.lower()
    if lowered.startswith("r") or "res" in lowered:
        return "resistor"
    if lowered.startswith("c") or "cap" in lowered:
        return "capacitor"
    return "unknown"


def primitive_line(instance: str, terminals: list[str], model: str) -> tuple[str | None, list[str]]:
    kind = passive_kind(model)
    electrical = terminals[:2]
    if len(electrical) < 2:
        return None, []
    safe_instance = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in instance)
    if kind == "resistor":
        return f"R_{safe_instance} {electrical[0]} {electrical[1]} 1", electrical
    if kind == "capacitor":
        return f"C_{safe_instance} {electrical[0]} {electrical[1]} 1f", electrical
    return None, []


def candidate_source_terms_and_model(candidate: dict[str, Any]) -> tuple[list[str], str]:
    terms = list(candidate.get("source_terminals", []))
    model = str(candidate.get("source_model", ""))
    if terms and model:
        return terms, model
    tokens = str(candidate.get("source_equivalent_spice", "")).split()
    if len(tokens) < 4:
        return terms, model
    return tokens[1:-1], tokens[-1]


def render_passive_abstraction_netlist(
    *,
    top_cell: str,
    primitive_lines: list[str],
    ports: list[str],
    comments: list[str],
) -> str:
    lines = [
        "* Passive-only abstraction netlist generated for diagnostic LVS trial.",
        "* This is not a full layout-extracted LVS netlist.",
    ]
    lines.extend(f"* {comment}" for comment in comments)
    lines.append(f".subckt {top_cell} {' '.join(ports)}")
    if primitive_lines:
        lines.extend(primitive_lines)
    else:
        lines.append("* no passive primitives")
    lines.append(f".ends {top_cell}")
    return "\n".join(lines) + "\n"


def abstraction_netlists(
    *,
    source_lines: list[str],
    packet: dict[str, Any],
    top_cell: str,
) -> tuple[str, str]:
    source_devices = {device.instance: device for device in parse_source_passives(source_lines)}
    candidates = {
        str(candidate.get("source_instance")): candidate
        for candidate in packet.get("candidates", [])
        if isinstance(candidate, dict) and candidate.get("source_instance")
    }
    ports: set[str] = set()
    source_primitives: list[str] = []
    candidate_primitives: list[str] = []
    source_comments: list[str] = []
    candidate_comments: list[str] = []
    for source_instance, source_device in sorted(source_devices.items()):
        primitive, electrical = primitive_line(
            source_device.instance,
            list(source_device.terminals),
            source_device.model,
        )
        ports.update(electrical)
        if primitive:
            source_primitives.append(primitive)
            if len(source_device.terminals) > len(electrical):
                source_comments.append(
                    f"{source_instance}: ignored non-electrical terminals {' '.join(source_device.terminals[len(electrical):])}"
                )
        candidate = candidates.get(source_instance)
        if not candidate:
            continue
        candidate_terms, candidate_model = candidate_source_terms_and_model(candidate)
        primitive, electrical = primitive_line(
            source_instance,
            candidate_terms,
            candidate_model,
        )
        ports.update(electrical)
        if primitive:
            candidate_primitives.append(primitive)
            candidate_comments.append(
                f"{source_instance}: {candidate.get('candidate_type')} status={candidate.get('candidate_status')}"
            )
    ordered_ports = sorted(ports)
    return (
        render_passive_abstraction_netlist(
            top_cell=f"{top_cell}_source_passive_abs",
            primitive_lines=source_primitives,
            ports=ordered_ports,
            comments=source_comments,
        ),
        render_passive_abstraction_netlist(
            top_cell=f"{top_cell}_candidate_passive_abs",
            primitive_lines=candidate_primitives,
            ports=ordered_ports,
            comments=candidate_comments,
        ),
    )


def verify_packet(*, source_lines: list[str], packet: dict[str, Any]) -> dict[str, Any]:
    source_devices = {device.instance: device for device in parse_source_passives(source_lines)}
    candidates = [
        candidate
        for candidate in packet.get("candidates", [])
        if isinstance(candidate, dict)
    ]
    candidate_by_source = {
        str(candidate.get("source_instance")): candidate
        for candidate in candidates
        if candidate.get("source_instance")
    }
    source_instances = sorted(source_devices)
    candidate_instances = sorted(candidate_by_source)
    missing_source_passive_instances = sorted(set(source_instances) - set(candidate_instances))
    extra_candidate_instances = sorted(set(candidate_instances) - set(source_instances))
    candidate_checks: list[dict[str, Any]] = []
    structural_failures: list[str] = []

    for source_instance, source_device in sorted(source_devices.items()):
        candidate = candidate_by_source.get(source_instance)
        if candidate is None:
            structural_failures.append(f"missing_candidate:{source_instance}")
            continue
        source_equivalent = str(candidate.get("source_equivalent_spice", ""))
        line_matches = candidate_line_matches_source(source_equivalent, source_device)
        if not line_matches:
            structural_failures.append(f"source_equivalent_mismatch:{source_instance}")
        support = _candidate_support_status(candidate)
        if not support["support_verified"]:
            structural_failures.append(f"support_not_verified:{source_instance}")
        unresolved_for_candidate = [str(item) for item in candidate.get("unresolved", [])]
        formalized_unresolved = [
            item for item in unresolved_for_candidate if _is_formalized_blocker(candidate, item)
        ]
        remaining_unresolved = [
            item for item in unresolved_for_candidate if item not in set(formalized_unresolved)
        ]
        candidate_terms, candidate_model = candidate_source_terms_and_model(candidate)
        primitive, electrical = primitive_line(source_instance, candidate_terms, candidate_model)
        primitive_class = primitive[0].lower() if primitive else None
        primitive_kind = {"r": "resistor", "c": "capacitor"}.get(str(primitive_class), None)
        formal_lvs_abstraction_ready = (
            line_matches
            and bool(support["support_verified"])
            and not remaining_unresolved
            and support.get("abstraction_rule") is not None
        )
        candidate_checks.append(
            {
                "source_instance": source_instance,
                "candidate_type": candidate.get("candidate_type"),
                "candidate_status": candidate.get("candidate_status"),
                "source_equivalent_spice": source_equivalent,
                "source_equivalent_matches_source": line_matches,
                "unresolved": candidate.get("unresolved", []),
                "formalized_unresolved": formalized_unresolved,
                "remaining_unresolved": remaining_unresolved,
                "formal_lvs_abstraction_ready": formal_lvs_abstraction_ready,
                "lvs_primitive_device_class": primitive_class,
                "lvs_primitive_kind": primitive_kind,
                "lvs_primitive_spice": primitive,
                "electrical_terminals": electrical,
                **support,
            }
        )

    unresolved = sorted(
        {
            str(item)
            for candidate in candidates
            for item in candidate.get("unresolved", [])
        }
    )
    all_source_passives_have_candidate = bool(source_instances) and not missing_source_passive_instances
    all_source_equivalents_match = all(
        bool(item.get("source_equivalent_matches_source")) for item in candidate_checks
    ) and len(candidate_checks) == len(source_instances)
    all_candidate_support_verified = all(
        bool(item.get("support_verified")) for item in candidate_checks
    ) and len(candidate_checks) == len(source_instances)
    all_candidates_formal_lvs_abstraction_ready = all(
        bool(item.get("formal_lvs_abstraction_ready")) for item in candidate_checks
    ) and len(candidate_checks) == len(source_instances)
    remaining_unresolved = sorted(
        {
            str(item)
            for check in candidate_checks
            for item in check.get("remaining_unresolved", [])
        }
    )

    if structural_failures:
        status = "fail"
    elif not source_instances:
        status = "not_applicable"
    elif all_candidates_formal_lvs_abstraction_ready:
        status = "formal_lvs_abstraction_verified"
    elif unresolved:
        status = "candidate_requires_review"
    else:
        status = "passive_abstraction_candidate_verified"

    return {
        "schema_version": "passive_abstraction_packet_verification.v1",
        "status": status,
        "full_passive_aware_lvs_proven": False,
        "packet_proof_status": packet.get("proof_status"),
        "source_passive_count": len(source_instances),
        "candidate_count": len(candidates),
        "source_instances": source_instances,
        "candidate_instances": candidate_instances,
        "missing_source_passive_instances": missing_source_passive_instances,
        "extra_candidate_instances": extra_candidate_instances,
        "all_source_passives_have_candidate": all_source_passives_have_candidate,
        "all_source_equivalents_match": all_source_equivalents_match,
        "all_candidate_support_verified": all_candidate_support_verified,
        "all_candidates_formal_lvs_abstraction_ready": all_candidates_formal_lvs_abstraction_ready,
        "formal_lvs_abstraction_ready": status == "formal_lvs_abstraction_verified",
        "abstraction_scope": "source_equivalent_passive_lvs_abstraction",
        "unresolved_blockers": unresolved,
        "remaining_unresolved_blockers": remaining_unresolved,
        "structural_failures": structural_failures,
        "candidate_checks": candidate_checks,
        "limitations": [
            "This verifies packet consistency and source-equivalent passive abstraction support.",
            "Formal passive abstraction means source passive devices are rewritten to LVS primitive R/C devices using verified structural evidence.",
            "It does not prove native Magic/Netgen recognition of every source passive device.",
            "It is not a full passive-aware LVS/PEX proof unless the rewritten MOS+passive netlists also pass Netgen.",
        ],
    }


def render_report(summary: dict[str, Any], source_netlist: Path, packet_json: Path) -> str:
    lines = [
        "# Passive Abstraction Packet Verification",
        "",
        "## Summary",
        "",
        f"- Source netlist: `{source_netlist}`",
        f"- Packet JSON: `{packet_json}`",
        f"- Status: `{summary.get('status')}`",
        f"- Full passive-aware LVS proven: `{summary.get('full_passive_aware_lvs_proven')}`",
        f"- Source passives: {summary.get('source_passive_count', 0)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- All source passives have candidate: {summary.get('all_source_passives_have_candidate')}",
        f"- All source-equivalent lines match source: {summary.get('all_source_equivalents_match')}",
        f"- All candidate support verified: {summary.get('all_candidate_support_verified')}",
        f"- Formal LVS abstraction ready: {summary.get('formal_lvs_abstraction_ready')}",
        f"- Abstraction scope: `{summary.get('abstraction_scope')}`",
        f"- Missing source passive instances: `{', '.join(summary.get('missing_source_passive_instances', [])) or 'none'}`",
        f"- Unresolved blockers: `{', '.join(summary.get('unresolved_blockers', [])) or 'none'}`",
        f"- Remaining unresolved blockers after formal abstraction: `{', '.join(summary.get('remaining_unresolved_blockers', [])) or 'none'}`",
        f"- Structural failures: `{', '.join(summary.get('structural_failures', [])) or 'none'}`",
        "",
        "## Candidate Checks",
        "",
    ]
    checks = summary.get("candidate_checks", [])
    if checks:
        lines.extend(
            [
                "| source instance | type | source line match | support verified | unresolved |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for check in checks:
            lines.append(
                f"| `{check.get('source_instance')}` | `{check.get('candidate_type')}` | "
                f"{check.get('source_equivalent_matches_source')} | {check.get('support_verified')} | "
                f"`{', '.join(check.get('unresolved', [])) or 'none'}` |"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "A `formal_lvs_abstraction_verified` status means segmented resistor chains and plate-coupling capacitor evidence are strong enough to rewrite source passives as LVS primitive R/C devices. This is a formal abstraction layer, not native passive device recognition, and it still requires the rewritten MOS+passive netlists to pass Netgen before full passive-aware LVS can be claimed.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    source_lines = args.source_netlist.read_text(encoding="utf-8", errors="replace").splitlines()
    packet = json.loads(args.packet_json.read_text(encoding="utf-8"))
    summary = verify_packet(source_lines=source_lines, packet=packet)
    if args.source_abstraction_netlist is not None or args.candidate_abstraction_netlist is not None:
        source_abs, candidate_abs = abstraction_netlists(
            source_lines=source_lines,
            packet=packet,
            top_cell=args.top_cell,
        )
        if args.source_abstraction_netlist is not None:
            args.source_abstraction_netlist.parent.mkdir(parents=True, exist_ok=True)
            args.source_abstraction_netlist.write_text(source_abs, encoding="utf-8")
            summary["source_abstraction_netlist"] = str(args.source_abstraction_netlist)
        if args.candidate_abstraction_netlist is not None:
            args.candidate_abstraction_netlist.parent.mkdir(parents=True, exist_ok=True)
            args.candidate_abstraction_netlist.write_text(candidate_abs, encoding="utf-8")
            summary["candidate_abstraction_netlist"] = str(args.candidate_abstraction_netlist)
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(summary, args.source_netlist, args.packet_json), encoding="utf-8")
    print(f"status={summary['status']}")
    print(f"full_passive_aware_lvs_proven={summary['full_passive_aware_lvs_proven']}")
    print(f"all_source_passives_have_candidate={summary['all_source_passives_have_candidate']}")
    return 0 if summary["status"] in {
        "candidate_requires_review",
        "passive_abstraction_candidate_verified",
        "formal_lvs_abstraction_verified",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
