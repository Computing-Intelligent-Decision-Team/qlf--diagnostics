#!/usr/bin/env python3
"""Compare MOS connectivity between a reference and a candidate SPICE netlist."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any


NMOS_MARKERS = ("nfet", "nmos")
PMOS_MARKERS = ("pfet", "pmos")
TERMINAL_NAMES = ("drain", "gate", "source", "bulk")


def fs_path(path: Path) -> Path:
    """Return a filesystem path that can handle long Windows paths."""
    if os.name != "nt":
        return path
    text = str(path)
    if text.startswith("\\\\?\\"):
        return path
    if text.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + text.lstrip("\\"))
    if path.is_absolute():
        return Path("\\\\?\\" + text)
    return path


def read_text(path: Path) -> str:
    return fs_path(path).read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    fs_path(path).write_text(text, encoding="utf-8")


@dataclass(frozen=True)
class MosDevice:
    instance: str
    model_class: str
    model: str
    terminals: tuple[str, str, str, str]
    width: str | None
    length: str | None
    line: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare MOS terminal connectivity between two netlists.")
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--netgen-report", type=Path)
    parser.add_argument("--vdd", default="vdda")
    parser.add_argument("--vss", default="gnda")
    return parser.parse_args()


def normalize_net(net: str) -> str:
    return net.strip().lower()


def model_class(token: str) -> str | None:
    lower = token.lower()
    if any(marker in lower for marker in NMOS_MARKERS):
        return "nfet"
    if any(marker in lower for marker in PMOS_MARKERS):
        return "pfet"
    return None


def parse_first_subckt_ports(lines: list[str]) -> tuple[str | None, list[str]]:
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if lower.startswith(".subckt ") or lower.startswith("subckt "):
            tokens = stripped.split()
            if len(tokens) >= 2:
                return tokens[1], tokens[2:]
    return None, []


def mos_from_tokens(tokens: list[str], original_line: str) -> MosDevice | None:
    if not tokens:
        return None
    first = tokens[0]
    model_idx: int | None = None
    cls: str | None = None
    if first[0].lower() == "x":
        for idx in range(1, len(tokens)):
            cls = model_class(tokens[idx].split("=", 1)[0])
            if cls is not None:
                model_idx = idx
                break
    elif first[0].lower() == "m" and len(tokens) >= 6:
        cls = model_class(tokens[5].split("=", 1)[0])
        model_idx = 5 if cls is not None else None
    if model_idx is None or cls is None or model_idx < 5:
        return None
    terminals = tuple(normalize_net(token) for token in tokens[1:5])
    width = None
    length = None
    for token in tokens[model_idx + 1 :]:
        key, _, value = token.partition("=")
        lower_key = key.lower()
        if lower_key == "w":
            width = value
        elif lower_key == "l":
            length = value
    return MosDevice(
        instance=first,
        model_class=cls,
        model=tokens[model_idx],
        terminals=terminals,  # type: ignore[arg-type]
        width=width,
        length=length,
        line=original_line.strip(),
    )


def parse_netlist(path: Path) -> dict[str, Any]:
    lines = read_text(path).splitlines()
    top_cell, ports = parse_first_subckt_ports(lines)
    devices: list[MosDevice] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("."):
            continue
        tokens = stripped.replace("(", " ").replace(")", " ").split()
        device = mos_from_tokens(tokens, stripped)
        if device is not None:
            devices.append(device)
    return {
        "path": str(path),
        "top_cell": top_cell,
        "ports": ports,
        "devices": devices,
    }


def device_class_count(devices: list[MosDevice]) -> dict[str, int]:
    return dict(Counter(device.model_class for device in devices))


def terminal_role_count(devices: list[MosDevice]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for device in devices:
        for terminal_name, net in zip(TERMINAL_NAMES, device.terminals):
            counts[net][f"{device.model_class}.{terminal_name}"] += 1
    return {net: dict(counter) for net, counter in sorted(counts.items())}


def net_signature_map(devices: list[MosDevice]) -> dict[tuple[tuple[str, int], ...], list[str]]:
    roles = terminal_role_count(devices)
    signatures: dict[tuple[tuple[str, int], ...], list[str]] = defaultdict(list)
    for net, role_counts in roles.items():
        signature = tuple(sorted(role_counts.items()))
        signatures[signature].append(net)
    return {signature: sorted(nets) for signature, nets in signatures.items()}


def role_similarity(reference_roles: dict[str, int], candidate_roles: dict[str, int]) -> dict[str, Any]:
    shared = 0
    missing: dict[str, int] = {}
    extra: dict[str, int] = {}
    for role, count in reference_roles.items():
        candidate_count = candidate_roles.get(role, 0)
        shared += min(count, candidate_count)
        if candidate_count < count:
            missing[role] = count - candidate_count
    for role, count in candidate_roles.items():
        reference_count = reference_roles.get(role, 0)
        if reference_count < count:
            extra[role] = count - reference_count
    return {"shared_role_count": shared, "missing_roles": missing, "extra_roles": extra}


def suggest_role_signature_matches(
    reference_roles: dict[str, dict[str, int]],
    candidate_roles: dict[str, dict[str, int]],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for reference_net, ref_counts in sorted(reference_roles.items()):
        scored: list[dict[str, Any]] = []
        for candidate_net, cand_counts in sorted(candidate_roles.items()):
            similarity = role_similarity(ref_counts, cand_counts)
            if not similarity["shared_role_count"]:
                continue
            scored.append(
                {
                    "candidate_net": candidate_net,
                    "candidate_roles": cand_counts,
                    **similarity,
                }
            )
        scored.sort(
            key=lambda item: (
                -int(item["shared_role_count"]),
                len(item["missing_roles"]),
                len(item["extra_roles"]),
                item["candidate_net"],
            )
        )
        suggestions.append(
            {
                "reference_net": reference_net,
                "reference_roles": ref_counts,
                "candidates": scored[:limit],
            }
        )
    return suggestions


def _combined_roles(nets: tuple[str, ...], candidate_roles: dict[str, dict[str, int]]) -> dict[str, int]:
    combined: Counter[str] = Counter()
    for net in nets:
        combined.update(candidate_roles.get(net, {}))
    return dict(combined)


def suggest_split_net_repairs(
    missing_reference_signature_nets: list[dict[str, Any]],
    candidate_roles: dict[str, dict[str, int]],
    *,
    max_group_size: int = 3,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find candidate net groups whose combined terminal roles match missing reference nets."""
    candidate_nets = sorted(candidate_roles)
    suggestions: list[dict[str, Any]] = []
    for missing in missing_reference_signature_nets:
        ref_roles = {
            str(role): int(count)
            for role, count in dict(missing.get("role_signature", {})).items()
        }
        matches: list[dict[str, Any]] = []
        for group_size in range(2, max_group_size + 1):
            for nets in combinations(candidate_nets, group_size):
                combined = _combined_roles(nets, candidate_roles)
                if combined == ref_roles:
                    matches.append(
                        {
                            "candidate_nets": list(nets),
                            "combined_roles": combined,
                            "candidate_net_count": group_size,
                        }
                    )
            if matches:
                break
        suggestions.append(
            {
                "reference_nets": missing.get("reference_nets", []),
                "reference_roles": ref_roles,
                "candidate_net_groups": matches[:limit],
            }
        )
    return suggestions


def suggest_exact_role_renames(
    reference_roles: dict[str, dict[str, int]],
    candidate_roles: dict[str, dict[str, int]],
    *,
    reference_ports: list[str],
    candidate_ports: list[str],
) -> list[dict[str, Any]]:
    reference_port_set = {normalize_net(port) for port in reference_ports}
    candidate_port_set = {normalize_net(port) for port in candidate_ports}
    suggestions: list[dict[str, Any]] = []
    for reference_net, ref_counts in sorted(reference_roles.items()):
        if reference_net in reference_port_set:
            continue
        exact_candidates = [
            candidate_net
            for candidate_net, cand_counts in sorted(candidate_roles.items())
            if candidate_net != reference_net
            and candidate_net not in candidate_port_set
            and cand_counts == ref_counts
        ]
        for candidate_net in exact_candidates:
            suggestions.append(
                {
                    "candidate_net": candidate_net,
                    "reference_net": reference_net,
                    "candidate_roles": candidate_roles[candidate_net],
                    "reason": "candidate internal net has the same MOS terminal-role signature as the reference net",
                }
            )
    return suggestions


def supply_role_summary(devices: list[MosDevice], *, vdd: str, vss: str) -> dict[str, Any]:
    vdd_norm = normalize_net(vdd)
    vss_norm = normalize_net(vss)
    summary: dict[str, Any] = {
        "vdd": vdd_norm,
        "vss": vss_norm,
        "nfet_source_to_vss": 0,
        "nfet_source_to_vdd": 0,
        "nfet_source_other": 0,
        "nfet_bulk_to_vss": 0,
        "nfet_bulk_to_vdd": 0,
        "nfet_bulk_other": 0,
        "nfet_source_or_bulk_to_vss": 0,
        "nfet_source_or_bulk_to_vdd": 0,
        "nfet_source_or_bulk_other": 0,
        "pfet_source_to_vdd": 0,
        "pfet_source_to_vss": 0,
        "pfet_source_other": 0,
        "pfet_bulk_to_vdd": 0,
        "pfet_bulk_to_vss": 0,
        "pfet_bulk_other": 0,
        "pfet_source_or_bulk_to_vdd": 0,
        "pfet_source_or_bulk_to_vss": 0,
        "pfet_source_or_bulk_other": 0,
        "nfet_with_source_or_bulk_not_vss": [],
        "pfet_with_source_or_bulk_not_vdd": [],
    }
    for device in devices:
        source, bulk = device.terminals[2], device.terminals[3]
        if device.model_class == "nfet":
            bad = False
            if source == vss_norm:
                summary["nfet_source_to_vss"] += 1
            elif source == vdd_norm:
                summary["nfet_source_to_vdd"] += 1
                bad = True
            else:
                summary["nfet_source_other"] += 1
            if bulk == vss_norm:
                summary["nfet_bulk_to_vss"] += 1
            elif bulk == vdd_norm:
                summary["nfet_bulk_to_vdd"] += 1
                bad = True
            else:
                summary["nfet_bulk_other"] += 1
                bad = True
            for net in (source, bulk):
                if net == vss_norm:
                    summary["nfet_source_or_bulk_to_vss"] += 1
                elif net == vdd_norm:
                    summary["nfet_source_or_bulk_to_vdd"] += 1
                else:
                    summary["nfet_source_or_bulk_other"] += 1
            if bad:
                summary["nfet_with_source_or_bulk_not_vss"].append(
                    {"instance": device.instance, "source": source, "bulk": bulk, "line": device.line}
                )
        elif device.model_class == "pfet":
            bad = False
            if source == vdd_norm:
                summary["pfet_source_to_vdd"] += 1
            elif source == vss_norm:
                summary["pfet_source_to_vss"] += 1
                bad = True
            else:
                summary["pfet_source_other"] += 1
            if bulk == vdd_norm:
                summary["pfet_bulk_to_vdd"] += 1
            elif bulk == vss_norm:
                summary["pfet_bulk_to_vss"] += 1
                bad = True
            else:
                summary["pfet_bulk_other"] += 1
                bad = True
            for net in (source, bulk):
                if net == vdd_norm:
                    summary["pfet_source_or_bulk_to_vdd"] += 1
                elif net == vss_norm:
                    summary["pfet_source_or_bulk_to_vss"] += 1
                else:
                    summary["pfet_source_or_bulk_other"] += 1
            if bad:
                summary["pfet_with_source_or_bulk_not_vdd"].append(
                    {"instance": device.instance, "source": source, "bulk": bulk, "line": device.line}
                )
    return summary


def parse_netgen_report(path: Path | None) -> dict[str, Any]:
    if path is None or not fs_path(path).is_file():
        return {}
    text = read_text(path)
    disconnected = sorted(set(re.findall(r"disconnected node:\s*(\S+)", text, flags=re.IGNORECASE)))
    net_mismatch = bool(re.search(r"Number of nets:.*\*\*Mismatch\*\*", text))
    device_mismatch = bool(re.search(r"Number of devices:.*\*\*Mismatch\*\*", text))
    match = re.search(
        r"Number of nets:\s*(\d+)\s*(?:\*\*Mismatch\*\*)?\s*\|\s*Number of nets:\s*(\d+)",
        text,
    )
    return {
        "path": str(path),
        "disconnected_nodes": disconnected,
        "device_mismatch": device_mismatch,
        "net_mismatch": net_mismatch,
        "source_net_count": int(match.group(1)) if match else None,
        "candidate_net_count": int(match.group(2)) if match else None,
    }


def compare(
    *,
    reference_path: Path,
    candidate_path: Path,
    netgen_report: Path | None = None,
    vdd: str = "vdda",
    vss: str = "gnda",
) -> dict[str, Any]:
    reference = parse_netlist(reference_path)
    candidate = parse_netlist(candidate_path)
    reference_devices: list[MosDevice] = reference["devices"]
    candidate_devices: list[MosDevice] = candidate["devices"]
    reference_roles = terminal_role_count(reference_devices)
    candidate_roles = terminal_role_count(candidate_devices)
    role_match_suggestions = suggest_role_signature_matches(reference_roles, candidate_roles)
    reference_signatures = net_signature_map(reference_devices)
    candidate_signatures = net_signature_map(candidate_devices)
    missing_reference_signature_nets: list[dict[str, Any]] = []
    for signature, nets in sorted(reference_signatures.items(), key=lambda item: item[1]):
        matched = candidate_signatures.get(signature, [])
        if not matched:
            missing_reference_signature_nets.append(
                {"reference_nets": nets, "role_signature": dict(signature)}
            )
    split_net_repair_suggestions = suggest_split_net_repairs(
        missing_reference_signature_nets,
        candidate_roles,
    )
    exact_role_rename_suggestions = suggest_exact_role_renames(
        reference_roles,
        candidate_roles,
        reference_ports=reference["ports"],
        candidate_ports=candidate["ports"],
    )
    reference_class_count = device_class_count(reference_devices)
    candidate_class_count = device_class_count(candidate_devices)
    reference_supply = supply_role_summary(reference_devices, vdd=vdd, vss=vss)
    candidate_supply = supply_role_summary(candidate_devices, vdd=vdd, vss=vss)
    netgen = parse_netgen_report(netgen_report)
    vss_norm = normalize_net(vss)
    vdd_norm = normalize_net(vdd)
    issues: list[str] = []
    if reference_class_count != candidate_class_count:
        issues.append("mos_device_class_count_mismatch")
    if len(reference_devices) != len(candidate_devices):
        issues.append("mos_device_count_mismatch")
    if not candidate_roles.get(vss_norm):
        issues.append("candidate_vss_has_no_mos_terminal_roles")
    if candidate_supply["nfet_bulk_to_vdd"] or candidate_supply["nfet_source_to_vdd"]:
        issues.append("candidate_nfet_source_or_bulk_tied_to_vdd")
    if candidate_supply["nfet_bulk_other"]:
        issues.append("candidate_nfet_bulk_on_non_vss_internal_net")
    if candidate_supply["pfet_bulk_to_vss"] or candidate_supply["pfet_source_to_vss"]:
        issues.append("candidate_pfet_source_or_bulk_tied_to_vss")
    if candidate_supply["pfet_bulk_other"]:
        issues.append("candidate_pfet_bulk_on_non_vdd_internal_net")
    if missing_reference_signature_nets:
        issues.append("missing_reference_mos_net_role_signatures")
    if vss_norm in netgen.get("disconnected_nodes", []):
        issues.append("netgen_reports_vss_disconnected")
    if netgen.get("net_mismatch"):
        issues.append("netgen_reports_net_count_mismatch")
    if not issues:
        status = "pass"
        reason = None
    elif any(issue.startswith("mos_device") for issue in issues):
        status = "device_mismatch"
        reason = "MOS device classes/counts differ between reference and candidate."
    elif (
        "candidate_vss_has_no_mos_terminal_roles" in issues
        or "candidate_nfet_source_or_bulk_tied_to_vdd" in issues
        or "netgen_reports_vss_disconnected" in issues
    ):
        status = "supply_or_internal_net_mismatch"
        reason = "Candidate MOS connectivity has supply-role corruption or a disconnected VSS node."
    else:
        status = "mos_internal_net_mismatch"
        reason = "Candidate MOS connectivity differs from the reference MOS role signatures."
    return {
        "schema_version": "mos_connectivity_comparison.v1",
        "status": status,
        "reason": reason,
        "issues": issues,
        "reference": {
            "path": str(reference_path),
            "top_cell": reference["top_cell"],
            "ports": reference["ports"],
            "mos_device_count": len(reference_devices),
            "mos_device_class_count": reference_class_count,
            "terminal_role_count": reference_roles,
            "supply_role_summary": reference_supply,
        },
        "candidate": {
            "path": str(candidate_path),
            "top_cell": candidate["top_cell"],
            "ports": candidate["ports"],
            "mos_device_count": len(candidate_devices),
            "mos_device_class_count": candidate_class_count,
            "terminal_role_count": candidate_roles,
            "supply_role_summary": candidate_supply,
        },
        "missing_reference_signature_nets": missing_reference_signature_nets,
        "role_signature_match_suggestions": role_match_suggestions,
        "split_net_repair_suggestions": split_net_repair_suggestions,
        "exact_role_rename_suggestions": exact_role_rename_suggestions,
        "netgen_report": netgen,
        "full_passive_aware_lvs_proven": False,
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# MOS Connectivity Comparison",
        "",
        "## Summary",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Reason: {summary.get('reason') or 'none'}",
        f"- Full passive-aware LVS proven: `{summary.get('full_passive_aware_lvs_proven')}`",
        f"- Issues: `{', '.join(summary.get('issues', [])) or 'none'}`",
        "",
        "## Device Counts",
        "",
        f"- Reference MOS devices: {summary.get('reference', {}).get('mos_device_count')}",
        f"- Candidate MOS devices: {summary.get('candidate', {}).get('mos_device_count')}",
        f"- Reference classes: `{summary.get('reference', {}).get('mos_device_class_count')}`",
        f"- Candidate classes: `{summary.get('candidate', {}).get('mos_device_class_count')}`",
        "",
        "## Supply Role Check",
        "",
        f"- Reference supply roles: `{summary.get('reference', {}).get('supply_role_summary')}`",
        f"- Candidate supply roles: `{summary.get('candidate', {}).get('supply_role_summary')}`",
        "",
        "## Netgen Cross-Check",
        "",
        f"- Disconnected nodes: `{summary.get('netgen_report', {}).get('disconnected_nodes', [])}`",
        f"- Net mismatch: `{summary.get('netgen_report', {}).get('net_mismatch')}`",
        f"- Source net count: `{summary.get('netgen_report', {}).get('source_net_count')}`",
        f"- Candidate net count: `{summary.get('netgen_report', {}).get('candidate_net_count')}`",
        "",
        "## Missing Reference Net Role Signatures",
        "",
    ]
    missing = summary.get("missing_reference_signature_nets", [])
    if not missing:
        lines.append("- none")
    else:
        for item in missing:
            lines.append(
                f"- reference nets `{item.get('reference_nets')}` with roles `{item.get('role_signature')}`"
            )
    lines.extend(["", "## Split-Net Repair Hints", ""])
    split_suggestions = summary.get("split_net_repair_suggestions", [])
    rows = [
        (item, group)
        for item in split_suggestions
        for group in item.get("candidate_net_groups", [])
    ]
    if rows:
        lines.extend(
            [
                "| reference net | reference roles | candidate net group | combined roles |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item, group in rows:
            lines.append(
                f"| `{item.get('reference_nets')}` | `{item.get('reference_roles')}` | "
                f"`{group.get('candidate_nets')}` | `{group.get('combined_roles')}` |"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Exact-Role Rename Hints", ""])
    exact_renames = summary.get("exact_role_rename_suggestions", [])
    if exact_renames:
        lines.extend(
            [
                "| candidate net | reference net | roles |",
                "| --- | --- | --- |",
            ]
        )
        for item in exact_renames:
            lines.append(
                f"| `{item.get('candidate_net')}` | `{item.get('reference_net')}` | "
                f"`{item.get('candidate_roles')}` |"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Closest Candidate Role Matches", ""])
    suggestions = summary.get("role_signature_match_suggestions", [])
    if suggestions:
        lines.extend(
            [
                "| reference net | reference roles | candidate net | shared roles | missing roles | extra roles |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for item in suggestions:
            for candidate in item.get("candidates", [])[:3]:
                lines.append(
                    f"| `{item.get('reference_net')}` | `{item.get('reference_roles')}` | "
                    f"`{candidate.get('candidate_net')}` | {candidate.get('shared_role_count')} | "
                    f"`{candidate.get('missing_roles')}` | `{candidate.get('extra_roles')}` |"
                )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This diagnostic compares MOS terminal-role connectivity only. A pass here would still not prove full passive-aware LVS; it would only show that the full passive-remapped extraction has not corrupted the MOS network relative to the MOS-only reference.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    summary = compare(
        reference_path=args.reference.resolve(),
        candidate_path=args.candidate.resolve(),
        netgen_report=args.netgen_report.resolve() if args.netgen_report else None,
        vdd=args.vdd,
        vss=args.vss,
    )
    fs_path(args.summary_json.parent).mkdir(parents=True, exist_ok=True)
    write_text(args.summary_json, json.dumps(summary, indent=2, sort_keys=True) + "\n")
    fs_path(args.report.parent).mkdir(parents=True, exist_ok=True)
    write_text(args.report, render_report(summary))
    print(f"status={summary['status']}")
    print(f"reason={summary.get('reason')}")
    return 0 if summary["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
