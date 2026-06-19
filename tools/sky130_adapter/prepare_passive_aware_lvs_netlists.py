#!/usr/bin/env python3
"""Prepare MOS + packet-passive abstraction netlists for diagnostic LVS trials."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from prepare_lvs_netlists import (
    EXTRACTED_PASSIVE_MODELS,
    NMOS_ALIASES,
    PASSIVE_ALIASES,
    PMOS_ALIASES,
    REMOVED_PROPERTIES,
    apply_renames,
    mos_model_alias,
    normalize_length,
    normalize_width,
    parse_first_subckt_ports,
    parse_renames,
)
from verify_passive_abstraction_packet import candidate_source_terms_and_model, primitive_line, verify_packet


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


def write_text(path: Path, text: str) -> None:
    fs_path(path).write_text(text, encoding="utf-8")


def copy_file(source: Path, destination: Path) -> None:
    shutil.copyfile(fs_path(source), fs_path(destination))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare passive-aware abstraction LVS netlists.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--extracted", type=Path, required=True)
    parser.add_argument("--packet-json", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--rename", action="append", default=[])
    parser.add_argument(
        "--mos-reference",
        type=Path,
        help=(
            "Optional already-verified MOS-only extraction. When provided, the "
            "extracted LVS trial netlist uses this MOS connectivity and then "
            "injects the packet passive abstractions. This is a diagnostic "
            "restoration, not full passive-inclusive GDS signoff."
        ),
    )
    return parser.parse_args()


def is_passive_model(model: str) -> bool:
    return model.split("=", 1)[0].lower() in PASSIVE_ALIASES


def is_extracted_passive_line(tokens: list[str]) -> bool:
    if len(tokens) < 4:
        return False
    instance = tokens[0].lower()
    if instance.startswith("r"):
        return tokens[3].lower() in EXTRACTED_PASSIVE_MODELS
    if instance.startswith("x"):
        return any(
            token.lower() in EXTRACTED_PASSIVE_MODELS or token.split("=", 1)[0].lower() in PASSIVE_ALIASES
            for token in tokens[1:]
        )
    return False


def normalize_mos_xline(tokens: list[str]) -> tuple[str | None, str | None]:
    model_token_index = None
    for idx in range(1, len(tokens)):
        key = tokens[idx].split("=", 1)[0].lower()
        if key in NMOS_ALIASES or key in PMOS_ALIASES:
            model_token_index = idx
            break
    if model_token_index is None:
        return None, None
    model = tokens[model_token_index]
    alias = mos_model_alias(model)
    if alias is None or model_token_index < 5:
        return None, None
    width = ""
    length = ""
    for token in tokens[model_token_index + 1 :]:
        key = token.split("=", 1)[0].lower()
        if key == "w":
            width = normalize_width(token)
        elif key == "l":
            length = normalize_length(token)
    suffix = []
    if width:
        suffix.append(f"w={width}")
    if length:
        suffix.append(f"l={length}")
    line = " ".join([tokens[0], tokens[1], tokens[2], tokens[3], tokens[4], alias] + suffix)
    model_alias = f"{model}->{alias}" if alias != model else None
    return line + "\n", model_alias


def passive_source_primitive(tokens: list[str], model_index: int) -> tuple[str | None, list[str]]:
    instance = tokens[0]
    model = tokens[model_index]
    terminals = tokens[1:model_index]
    return primitive_line(instance, terminals, model)


def lvs_primitive_record(
    *,
    source_instance: str,
    source_model: str,
    source_terminals: list[str],
    electrical_terminals: list[str],
    primitive: str,
    source: str,
    candidate_type: str | None = None,
    abstraction_rule: str | None = None,
) -> dict[str, Any]:
    primitive_class = primitive[0].lower() if primitive else "unknown"
    primitive_kind = {"r": "resistor", "c": "capacitor"}.get(primitive_class, "unknown")
    record = {
        "source_instance": source_instance,
        "source_model": source_model,
        "source_terminals": source_terminals,
        "electrical_terminals": electrical_terminals,
        "ignored_reference_terminals": source_terminals[len(electrical_terminals) :],
        "lvs_primitive_device_class": primitive_class,
        "lvs_primitive_kind": primitive_kind,
        "lvs_primitive_spice": primitive,
        "abstraction_source": source,
    }
    if candidate_type:
        record["candidate_type"] = candidate_type
    if abstraction_rule:
        record["abstraction_rule"] = abstraction_rule
    return record


def source_to_passive_aware_connectivity(lines: list[str]) -> tuple[list[str], dict[str, Any]]:
    output: list[str] = []
    model_aliases: Counter[str] = Counter()
    abstracted_passives: Counter[str] = Counter()
    ignored_reference_terminals: dict[str, list[str]] = {}
    lvs_primitive_abstractions: list[dict[str, Any]] = []
    saw_subckt = False
    saw_ends = False
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if not stripped:
            output.append(line)
            continue
        if lower.startswith("subckt "):
            output.append(re.sub(r"^\s*subckt\b", ".subckt", line, flags=re.IGNORECASE))
            saw_subckt = True
            continue
        if lower.startswith(".subckt "):
            output.append(line)
            saw_subckt = True
            continue
        if re.match(r"^ends(\s+|$)", lower):
            output.append(re.sub(r"^\s*ends\b", ".ends", line, flags=re.IGNORECASE))
            saw_ends = True
            continue
        if lower.startswith(".ends"):
            output.append(line)
            saw_ends = True
            continue
        tokens = stripped.replace("(", " ").replace(")", " ").split()
        if tokens and tokens[0].lower().startswith("x"):
            passive_model_index = next(
                (
                    idx
                    for idx in range(1, len(tokens))
                    if is_passive_model(tokens[idx])
                ),
                None,
            )
            if passive_model_index is not None:
                primitive, electrical = passive_source_primitive(tokens, passive_model_index)
                if primitive:
                    output.append(primitive + "\n")
                    model = tokens[passive_model_index].split("=", 1)[0].lower()
                    abstracted_passives[model] += 1
                    lvs_primitive_abstractions.append(
                        lvs_primitive_record(
                            source_instance=tokens[0],
                            source_model=model,
                            source_terminals=tokens[1:passive_model_index],
                            electrical_terminals=electrical,
                            primitive=primitive,
                            source="source_netlist",
                        )
                    )
                    ignored = tokens[1:passive_model_index][len(electrical) :]
                    if ignored:
                        ignored_reference_terminals[tokens[0]] = ignored
                continue
            mos_line, model_alias = normalize_mos_xline(tokens)
            if mos_line is not None:
                output.append(mos_line)
                if model_alias:
                    model_aliases[model_alias] += 1
                continue
        if re.match(r"^[Mm]\S+\s+", stripped):
            if len(tokens) < 6:
                output.append(line)
                continue
            inst = "X" + tokens[0][1:]
            model = mos_model_alias(tokens[5]) or tokens[5]
            if model != tokens[5]:
                model_aliases[f"{tokens[5]}->{model}"] += 1
            width = ""
            length = ""
            for token in tokens[6:]:
                key = token.split("=", 1)[0].lower()
                if key == "w":
                    width = normalize_width(token)
                elif key == "l":
                    length = normalize_length(token)
            suffix = []
            if width:
                suffix.append(f"w={width}")
            if length:
                suffix.append(f"l={length}")
            output.append(" ".join([inst, tokens[1], tokens[2], tokens[3], tokens[4], model] + suffix) + "\n")
            continue
        output.append(line)
    return output, {
        "saw_subckt": saw_subckt,
        "saw_ends": saw_ends,
        "model_aliases": dict(model_aliases),
        "abstracted_source_passives": dict(abstracted_passives),
        "ignored_reference_terminals": ignored_reference_terminals,
        "lvs_primitive_abstractions": lvs_primitive_abstractions,
    }


def packet_candidate_primitives(packet: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for candidate in packet.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        instance = str(candidate.get("source_instance", ""))
        terms, model = candidate_source_terms_and_model(candidate)
        primitive, _electrical = primitive_line(instance, terms, model)
        if primitive:
            lines.append(primitive)
    return lines


def packet_candidate_primitive_records(packet: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for candidate in packet.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        instance = str(candidate.get("source_instance", ""))
        terms, model = candidate_source_terms_and_model(candidate)
        primitive, electrical = primitive_line(instance, terms, model)
        if primitive:
            candidate_type = candidate.get("candidate_type")
            abstraction_rule = candidate.get("abstraction_rule")
            records.append(
                lvs_primitive_record(
                    source_instance=instance,
                    source_model=model,
                    source_terminals=terms,
                    electrical_terminals=electrical,
                    primitive=primitive,
                    source="passive_abstraction_packet",
                    candidate_type=str(candidate_type) if candidate_type else None,
                    abstraction_rule=str(abstraction_rule) if abstraction_rule else None,
                )
            )
    return records


def filter_subckt_ports(line: str, source_ports: list[str]) -> str:
    tokens = line.strip().split()
    if len(tokens) <= 2 or not tokens[0].lower().endswith("subckt"):
        return line
    return f".subckt {tokens[1]} {' '.join(source_ports)}\n"


def extracted_to_passive_aware_connectivity(
    lines: list[str],
    *,
    packet: dict[str, Any],
    renames: dict[str, str],
    source_ports: list[str],
) -> tuple[list[str], dict[str, Any]]:
    output: list[str] = []
    candidate_primitives = packet_candidate_primitives(packet)
    candidate_primitive_records = packet_candidate_primitive_records(packet)
    inserted_candidates = False
    skipped_caps = 0
    skipped_physical_passives = 0
    skipped_subckt_port_continuations = 0
    removed_props: Counter[str] = Counter()
    renamed_lines = 0
    filtering_subckt_ports = False
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith(".subckt ") or lower.startswith("subckt "):
            output.append(filter_subckt_ports(line, source_ports))
            filtering_subckt_ports = True
            continue
        if filtering_subckt_ports and lower.startswith("+"):
            skipped_subckt_port_continuations += 1
            continue
        if stripped and not lower.startswith("*"):
            filtering_subckt_ports = False
        if lower.startswith(".ends") or re.match(r"^ends(\s+|$)", lower):
            if not inserted_candidates:
                output.extend(candidate + "\n" for candidate in candidate_primitives)
                inserted_candidates = True
            output.append(re.sub(r"^\s*ends\b", ".ends", line, flags=re.IGNORECASE))
            continue
        if re.match(r"^[Cc]\S*\s+", stripped):
            skipped_caps += 1
            continue
        tokens = stripped.replace("(", " ").replace(")", " ").split()
        if is_extracted_passive_line(tokens):
            skipped_physical_passives += 1
            continue
        renamed = apply_renames(line, renames)
        if renamed != line:
            renamed_lines += 1
        if re.match(r"^[Xx]\S+\s+", renamed.strip()):
            kept = []
            for token in renamed.split():
                key = token.split("=", 1)[0].lower()
                if key in REMOVED_PROPERTIES:
                    removed_props[key] += 1
                    continue
                kept.append(token)
            renamed = " ".join(kept) + "\n"
        output.append(renamed)
    if not inserted_candidates:
        output.extend(candidate + "\n" for candidate in candidate_primitives)
    return output, {
        "inserted_candidate_count": len(candidate_primitives),
        "skipped_parasitic_capacitors": skipped_caps,
        "skipped_physical_passives": skipped_physical_passives,
        "skipped_subckt_port_continuations": skipped_subckt_port_continuations,
        "removed_properties": dict(removed_props),
        "renamed_lines": renamed_lines,
        "lvs_primitive_abstractions": candidate_primitive_records,
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Passive-Aware LVS Trial Netlist Preparation",
        "",
        "## Summary",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Full passive-aware LVS proven: `{summary.get('full_passive_aware_lvs_proven')}`",
        f"- Source output: `{summary.get('source_output')}`",
        f"- Extracted output: `{summary.get('extracted_output')}`",
        f"- Packet verification status: `{summary.get('packet_verification', {}).get('status')}`",
        f"- Formal LVS abstraction ready: `{summary.get('packet_verification', {}).get('formal_lvs_abstraction_ready')}`",
        f"- Abstraction scope: `{summary.get('packet_verification', {}).get('abstraction_scope')}`",
        f"- Remaining unresolved blockers: `{summary.get('packet_verification', {}).get('remaining_unresolved_blockers')}`",
        f"- Source passives abstracted: `{summary.get('source_stats', {}).get('abstracted_source_passives')}`",
        f"- Extracted MOS connectivity source: `{summary.get('mos_connectivity_source')}`",
        f"- MOS reference: `{summary.get('mos_reference')}`",
        f"- Extracted physical passives removed: {summary.get('extracted_stats', {}).get('skipped_physical_passives')}",
        f"- Extracted candidate passives inserted: {summary.get('extracted_stats', {}).get('inserted_candidate_count')}",
        f"- Extracted parasitic capacitors removed: {summary.get('extracted_stats', {}).get('skipped_parasitic_capacitors')}",
        "",
        "## Interpretation",
        "",
        "These netlists are a MOS + formal packet-passive abstraction trial. Segmented resistor chains and cfmom plate-coupling evidence are rewritten to primitive R/C devices for LVS. This is a formal source-equivalent abstraction layer, not native Magic/Netgen recognition of every source passive device.",
        "",
        "If `mos_connectivity_source=mos_reference`, the extracted-side MOS network was restored from a separately verified MOS-only extraction. That mode proves the passive abstraction can compose with a correct MOS network, but it does not prove the passive-inclusive full GDS extracted MOS network is correct.",
        "",
    ]
    return "\n".join(lines)


def prepare(
    *,
    source_path: Path,
    extracted_path: Path,
    packet_path: Path,
    out_dir: Path,
    prefix: str,
    renames: dict[str, str],
    mos_reference_path: Path | None = None,
) -> dict[str, Any]:
    fs_path(out_dir).mkdir(parents=True, exist_ok=True)
    source_lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    extracted_lines = extracted_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    mos_reference_lines = (
        mos_reference_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        if mos_reference_path is not None
        else None
    )
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet_verification = verify_packet(source_lines=[line.rstrip("\n") for line in source_lines], packet=packet)
    source_output, source_stats = source_to_passive_aware_connectivity(source_lines)
    if not source_stats["saw_subckt"] or not source_stats["saw_ends"]:
        raise ValueError(f"source netlist lacks subckt/ends: {source_path}")
    source_ports = list(parse_first_subckt_ports(source_lines))
    extracted_mos_lines = mos_reference_lines if mos_reference_lines is not None else extracted_lines
    extracted_output, extracted_stats = extracted_to_passive_aware_connectivity(
        extracted_mos_lines,
        packet=packet,
        renames=renames,
        source_ports=source_ports,
    )
    source_out = out_dir / f"{prefix}_source.passive_aware.spice"
    extracted_out = out_dir / f"{prefix}_extracted.passive_aware.spice"
    raw_copy = out_dir / f"{prefix}_extracted.raw.spice"
    write_text(source_out, "".join(source_output))
    write_text(extracted_out, "".join(extracted_output))
    copy_file(extracted_path, raw_copy)
    status = "ready_for_netgen_trial" if packet_verification["status"] != "fail" else "packet_verification_failed"
    return {
        "schema_version": "passive_aware_lvs_trial_netlists.v1",
        "status": status,
        "full_passive_aware_lvs_proven": False,
        "formal_lvs_abstraction_ready": packet_verification.get("formal_lvs_abstraction_ready", False),
        "abstraction_scope": packet_verification.get("abstraction_scope"),
        "source_output": str(source_out),
        "extracted_output": str(extracted_out),
        "raw_extracted_copy": str(raw_copy),
        "mos_reference": str(mos_reference_path) if mos_reference_path is not None else None,
        "mos_connectivity_source": "mos_reference" if mos_reference_path is not None else "full_gds_extraction",
        "source_top_cell": parse_first_subckt_ports(source_lines),
        "renames": renames,
        "source_stats": source_stats,
        "extracted_stats": extracted_stats,
        "packet_verification": packet_verification,
    }


def main() -> int:
    args = parse_args()
    summary = prepare(
        source_path=args.source.resolve(),
        extracted_path=args.extracted.resolve(),
        packet_path=args.packet_json.resolve(),
        out_dir=args.out_dir.resolve(),
        prefix=args.prefix,
        renames=parse_renames(args.rename),
        mos_reference_path=args.mos_reference.resolve() if args.mos_reference else None,
    )
    fs_path(args.summary_json.parent).mkdir(parents=True, exist_ok=True)
    write_text(args.summary_json, json.dumps(summary, indent=2, sort_keys=True) + "\n")
    fs_path(args.report.parent).mkdir(parents=True, exist_ok=True)
    write_text(args.report, render_report(summary))
    print(f"status={summary['status']}")
    print(f"source_output={summary['source_output']}")
    print(f"extracted_output={summary['extracted_output']}")
    return 0 if summary["status"] == "ready_for_netgen_trial" else 2


if __name__ == "__main__":
    raise SystemExit(main())
