#!/usr/bin/env python3
"""Prepare raw and connectivity netlists for Sky130 LVS trials."""

from __future__ import annotations

import argparse
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


REMOVED_PROPERTIES = {"ad", "as", "pd", "ps"}
NMOS_ALIASES = {
    "nmos",
    "nch",
    "nch_na",
    "nch_mac",
    "nch_lvt",
    "nch_lvt_mac",
    "nch_25_mac",
    "nch_na25_mac",
    "nch_hvt_mac",
    "nch_25ud18_mac",
    "sky130_fd_pr__nfet_01v8",
}
PMOS_ALIASES = {
    "pmos",
    "pch",
    "pch_mac",
    "pch_lvt",
    "pch_lvt_mac",
    "pch_25_mac",
    "pch_na25_mac",
    "pch_hvt_mac",
    "pch_25ud18_mac",
    "pch_hvt",
    "sky130_fd_pr__pfet_01v8",
}
PASSIVE_ALIASES = {"rppoly", "rppoly_m", "rppolywo_m", "rppolywo", "cfmom", "cfmom_2t"}
EXTRACTED_PASSIVE_MODELS = {
    "sky130_fd_pr__res_generic_m1",
    "sky130_fd_pr__res_generic_m2",
    "sky130_fd_pr__res_generic_m3",
    "sky130_fd_pr__res_generic_m4",
    "sky130_fd_pr__res_xhigh_po",
    "sky130_fd_pr__res_high_po",
    "sky130_fd_pr__res_generic_po",
}


@dataclass(frozen=True)
class SourcePassive:
    instance: str
    model: str
    terminals: tuple[str, ...]


@dataclass(frozen=True)
class ExtractedPassive:
    instance: str
    model: str
    terminals: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Sky130 LVS netlist variants.")
    parser.add_argument("--source", type=Path, required=True, help="Input source netlist.")
    parser.add_argument("--extracted", type=Path, required=True, help="Magic raw extracted netlist.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory.")
    parser.add_argument("--report", type=Path, help="Preparation report path.")
    parser.add_argument("--prefix", default="inverter_core", help="Output filename prefix.")
    parser.add_argument(
        "--rename",
        action="append",
        default=[],
        metavar="OLD=NEW",
        help="Explicit net rename for connectivity LVS. May be repeated.",
    )
    return parser.parse_args()


def parse_renames(rename_args: list[str]) -> dict[str, str]:
    renames: dict[str, str] = {}
    for item in rename_args:
        if "=" not in item:
            raise ValueError(f"invalid rename '{item}', expected OLD=NEW")
        old, new = item.split("=", 1)
        if not old or not new:
            raise ValueError(f"invalid rename '{item}', expected OLD=NEW")
        renames[old] = new
    return renames


def normalize_spice_dimension(value: str) -> str:
    value = value.lower()
    if "=" in value:
        value = value.split("=", 1)[1]
    if value.endswith("n"):
        return f"{float(value[:-1]) / 1000.0:g}"
    if value.endswith("u"):
        return f"{float(value[:-1]):g}"
    parsed = float(value)
    if abs(parsed) < 1e-3:
        parsed *= 1e6
    return f"{parsed:g}"


def normalize_length(value: str) -> str:
    return normalize_spice_dimension(value)


def normalize_width(value: str) -> str:
    return normalize_spice_dimension(value)


def mos_model_alias(model: str) -> str | None:
    model_lower = model.lower()
    if model_lower in NMOS_ALIASES:
        return "sky130_fd_pr__nfet_01v8"
    if model_lower in PMOS_ALIASES:
        return "sky130_fd_pr__pfet_01v8"
    return None


def parse_source_passives(lines: list[str]) -> list[SourcePassive]:
    devices: list[SourcePassive] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("."):
            continue
        tokens = stripped.replace("(", " ").replace(")", " ").split()
        if not tokens:
            continue
        model_index = None
        for idx, token in enumerate(tokens[1:], start=1):
            if token.split("=", 1)[0].lower() in PASSIVE_ALIASES:
                model_index = idx
                break
        if model_index is None:
            continue
        devices.append(
            SourcePassive(
                instance=tokens[0],
                model=tokens[model_index],
                terminals=tuple(tokens[1:model_index]),
            )
        )
    return devices


def parse_extracted_physical_passives(lines: list[str]) -> list[ExtractedPassive]:
    devices: list[ExtractedPassive] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("."):
            continue
        tokens = stripped.replace("(", " ").replace(")", " ").split()
        if len(tokens) < 4:
            continue
        instance = tokens[0]
        if instance.lower().startswith("r"):
            model = tokens[3]
            if model.lower() in EXTRACTED_PASSIVE_MODELS:
                devices.append(ExtractedPassive(instance=instance, model=model, terminals=tuple(tokens[1:3])))
            continue
        if instance.lower().startswith("x"):
            for idx, token in enumerate(tokens[1:], start=1):
                if token.lower() in PASSIVE_ALIASES or token.lower() in EXTRACTED_PASSIVE_MODELS:
                    devices.append(
                        ExtractedPassive(instance=instance, model=token, terminals=tuple(tokens[1:idx]))
                    )
                    break
    return devices


def parse_first_subckt_ports(lines: list[str]) -> tuple[str, ...]:
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith(".subckt ") or stripped.lower().startswith("subckt "):
            return tuple(stripped.split()[2:])
    return ()


def is_magic_internal_net(net: str) -> bool:
    return bool(re.match(r"^[amw]\d*_", net)) or net.endswith("#")


def passive_abstraction_diagnostic(source_lines: list[str], extracted_lines: list[str]) -> dict[str, object]:
    source_passives = parse_source_passives(source_lines)
    extracted_passives = parse_extracted_physical_passives(extracted_lines)
    source_ports = set(parse_first_subckt_ports(source_lines))
    source_passive_terminals = {
        terminal
        for device in source_passives
        for terminal in device.terminals
    }
    extracted_terminal_set = {
        terminal
        for device in extracted_passives
        for terminal in device.terminals
    }
    covered_source_terminals = sorted(source_passive_terminals.intersection(extracted_terminal_set))
    extracted_touching_source = [
        device for device in extracted_passives if set(device.terminals).intersection(source_passive_terminals)
    ]
    extracted_touching_ports = [
        device for device in extracted_passives if set(device.terminals).intersection(source_ports)
    ]
    self_loop_devices = [
        device for device in extracted_passives if len(device.terminals) >= 2 and device.terminals[0] == device.terminals[1]
    ]
    internal_only_devices = [
        device
        for device in extracted_passives
        if not set(device.terminals).intersection(source_passive_terminals)
        and all(is_magic_internal_net(terminal) or terminal not in source_ports for terminal in device.terminals)
    ]
    model_counts: Counter[str] = Counter(device.model for device in extracted_passives)
    if not source_passives:
        status = "not_applicable"
    elif not extracted_passives:
        status = "no_extracted_physical_passives"
    elif 0 < len(covered_source_terminals) < len(source_passive_terminals):
        status = "physical_passives_partially_recover_source_terminals"
    elif len(covered_source_terminals) < len(source_passive_terminals):
        status = "physical_passives_extracted_but_source_terminals_not_recovered"
    else:
        status = "candidate_for_passive_abstraction"
    return {
        "status": status,
        "source_passive_count": len(source_passives),
        "source_passives": source_passives,
        "source_passive_terminals": sorted(source_passive_terminals),
        "source_ports": sorted(source_ports),
        "extracted_physical_passive_count": len(extracted_passives),
        "extracted_passives": extracted_passives,
        "extracted_model_counts": model_counts,
        "covered_source_passive_terminals": covered_source_terminals,
        "missing_source_passive_terminals": sorted(source_passive_terminals - extracted_terminal_set),
        "extracted_passives_touching_source_terminals": len(extracted_touching_source),
        "extracted_passives_touching_source_ports": len(extracted_touching_ports),
        "self_loop_extracted_passives": len(self_loop_devices),
        "internal_only_extracted_passives": len(internal_only_devices),
    }


def format_inline_list(values: object) -> str:
    if not values:
        return "none"
    if isinstance(values, (list, tuple, set)):
        return ", ".join(f"`{value}`" for value in values) if values else "none"
    return f"`{values}`"


def append_passive_abstraction_section(lines: list[str], diagnostic: dict[str, object]) -> None:
    model_counts = diagnostic.get("extracted_model_counts", Counter())
    source_passives = diagnostic.get("source_passives", [])
    extracted_passives = diagnostic.get("extracted_passives", [])

    lines.extend(
        [
            "",
            "## Passive Abstraction Diagnostic",
            "",
            f"- Status: `{diagnostic.get('status', 'unknown')}`",
            f"- Source passive devices: {diagnostic.get('source_passive_count', 0)}",
            f"- Extracted physical passive devices: {diagnostic.get('extracted_physical_passive_count', 0)}",
            f"- Source passive terminals: {format_inline_list(diagnostic.get('source_passive_terminals', []))}",
            f"- Covered source passive terminals: {format_inline_list(diagnostic.get('covered_source_passive_terminals', []))}",
            f"- Missing source passive terminals: {format_inline_list(diagnostic.get('missing_source_passive_terminals', []))}",
            f"- Extracted passives touching source passive terminals: {diagnostic.get('extracted_passives_touching_source_terminals', 0)}",
            f"- Extracted passives touching source top ports: {diagnostic.get('extracted_passives_touching_source_ports', 0)}",
            f"- Self-loop extracted passives: {diagnostic.get('self_loop_extracted_passives', 0)}",
            f"- Internal-only extracted passives: {diagnostic.get('internal_only_extracted_passives', 0)}",
            "- Source passive instances:",
        ]
    )
    if source_passives:
        for device in source_passives:
            if isinstance(device, SourcePassive):
                lines.append(
                    f"  - `{device.instance}` `{device.model}` terminals: {format_inline_list(device.terminals)}"
                )
    else:
        lines.append("  - none")

    lines.append("- Extracted passive model counts:")
    if isinstance(model_counts, Counter) and model_counts:
        for model, count in sorted(model_counts.items()):
            lines.append(f"  - `{model}`: {count}")
    else:
        lines.append("  - none")

    lines.append("- Extracted passive examples:")
    if extracted_passives:
        for device in list(extracted_passives)[:8]:
            if isinstance(device, ExtractedPassive):
                lines.append(
                    f"  - `{device.instance}` `{device.model}` terminals: {format_inline_list(device.terminals)}"
                )
        if len(extracted_passives) > 8:
            lines.append(f"  - ... {len(extracted_passives) - 8} more")
    else:
        lines.append("  - none")

    status = str(diagnostic.get("status", "unknown"))
    if status == "physical_passives_extracted_but_source_terminals_not_recovered":
        interpretation = (
            "Physical passive shapes are extractable, but the extracted generic devices do not recover "
            "the source passive terminals. Full passive-aware LVS still needs an explicit abstraction "
            "or mapping rule from extracted physical devices back to source passive instances."
        )
    elif status == "candidate_for_passive_abstraction":
        interpretation = (
            "Extracted passive terminals overlap all source passive terminals. This is a candidate for "
            "a future passive abstraction rule, but it is not yet a full LVS proof by itself."
        )
    elif status == "physical_passives_partially_recover_source_terminals":
        interpretation = (
            "Some source passive terminals now appear on extracted physical passive devices, but the "
            "mapping is incomplete. Full passive-aware LVS still needs the remaining source terminals "
            "and source-instance abstraction to be recovered."
        )
    elif status == "no_extracted_physical_passives":
        interpretation = "Source passives exist, but Magic did not extract matching physical passive devices."
    elif status == "not_applicable":
        interpretation = "No source passive devices were found in this source netlist."
    else:
        interpretation = "Passive abstraction status is unknown."
    lines.extend(["", f"Interpretation: {interpretation}"])


def source_to_connectivity(lines: list[str]) -> tuple[list[str], bool, bool, Counter[str], Counter[str]]:
    output: list[str] = []
    model_aliases: Counter[str] = Counter()
    dropped_passives: Counter[str] = Counter()
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
        flattened = stripped.replace("(", " ").replace(")", " ")
        tokens = flattened.split()
        if (
            len(tokens) >= 4
            and tokens[0].lower().startswith("x")
        ):
            model_token_index = None
            for idx in range(1, len(tokens)):
                key = tokens[idx].split("=", 1)[0].lower()
                if key in NMOS_ALIASES or key in PMOS_ALIASES or key in PASSIVE_ALIASES:
                    model_token_index = idx
                    break
            if model_token_index is not None:
                model = tokens[model_token_index]
                model_lower = model.lower()
                if model_lower in PASSIVE_ALIASES:
                    dropped_passives[model_lower] += 1
                    continue
                alias = mos_model_alias(model)
                if alias is not None and model_token_index >= 5:
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
                    if alias != model:
                        model_aliases[f"{model}->{alias}"] += 1
                    output.append(
                        " ".join(
                            [tokens[0], tokens[1], tokens[2], tokens[3], tokens[4], alias] + suffix
                        )
                        + "\n"
                    )
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
            output.append(
                " ".join([inst, tokens[1], tokens[2], tokens[3], tokens[4], model] + suffix)
                + "\n"
            )
            continue
        output.append(line)
    return output, saw_subckt, saw_ends, model_aliases, dropped_passives


def apply_renames(line: str, renames: dict[str, str]) -> str:
    for old, new in renames.items():
        line = line.replace(old, new)
    return line


def extracted_to_connectivity(
    lines: list[str], renames: dict[str, str]
) -> tuple[list[str], int, Counter[str], int]:
    output: list[str] = []
    deleted_caps = 0
    removed_props: Counter[str] = Counter()
    renamed_lines = 0
    for line in lines:
        stripped = line.strip()
        if re.match(r"^[Cc]\S*\s+", stripped):
            deleted_caps += 1
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
    return output, deleted_caps, removed_props, renamed_lines


def write_report(
    report_path: Path,
    source_path: Path,
    extracted_path: Path,
    raw_copy: Path,
    source_conn: Path,
    extracted_conn: Path,
    deleted_caps: int,
    removed_props: Counter[str],
    model_aliases: Counter[str],
    dropped_passives: Counter[str],
    renames: dict[str, str],
    renamed_lines: int,
    passive_diagnostic: dict[str, object],
) -> None:
    lines = [
        "# LVS Preparation Report",
        "",
        "## Outputs",
        "",
        f"- Input source netlist: `{source_path}`",
        f"- Input Magic raw extracted netlist: `{extracted_path}`",
        f"- Raw extracted netlist copy: `{raw_copy}`",
        f"- Connectivity source netlist: `{source_conn}`",
        f"- Connectivity extracted netlist: `{extracted_conn}`",
        "",
        "## Connectivity Normalization",
        "",
        f"- Dropped unsupported source passive devices: {sum(dropped_passives.values())}",
        f"- Deleted parasitic capacitor lines: {deleted_caps}",
        "- Source MOS model aliases:",
    ]
    if model_aliases:
        for alias, count in sorted(model_aliases.items()):
            lines.append(f"  - `{alias}`: {count}")
    else:
        lines.append("  - none")
    lines.extend([
        "- Dropped source passive models:",
    ])
    if dropped_passives:
        for model, count in sorted(dropped_passives.items()):
            lines.append(f"  - `{model}`: {count}")
    else:
        lines.append("  - none")
    lines.extend([
        "- Removed MOS properties:",
    ])
    for prop in sorted(REMOVED_PROPERTIES):
        lines.append(f"  - `{prop}`: {removed_props.get(prop, 0)}")
    lines.extend(["", "## Net Renames", ""])
    if renames:
        lines.extend(["| Extracted net | Connectivity net |", "| --- | --- |"])
        for old, new in sorted(renames.items()):
            lines.append(f"| `{old}` | `{new}` |")
        lines.append(f"\nRenamed lines: {renamed_lines}")
    else:
        lines.append("- Net rename enabled: no")
        lines.append("- Power-net fixed baseline no longer requires `a_n15_90#` rename.")
    append_passive_abstraction_section(lines, passive_diagnostic)
    lines.extend(
        [
            "",
            "## LVS Type",
            "",
            "This output is for connectivity LVS, not parasitic-aware LVS.",
            "The raw Magic extraction is preserved separately so parasitic information is not lost.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    source_path = args.source.resolve()
    extracted_path = args.extracted.resolve()
    out_dir = args.out_dir.resolve()
    report_path = (args.report or out_dir / "lvs_preparation_report.md").resolve()
    renames = parse_renames(args.rename)

    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if not extracted_path.is_file():
        raise FileNotFoundError(extracted_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    raw_copy = out_dir / f"{args.prefix}_extracted.raw.spice"
    extracted_conn = out_dir / f"{args.prefix}_extracted.connectivity.spice"
    source_conn = out_dir / f"{args.prefix}_source.connectivity.spice"

    shutil.copyfile(extracted_path, raw_copy)

    source_lines = source_path.read_text(encoding="utf-8").splitlines(keepends=True)
    source_output, saw_subckt, saw_ends, model_aliases, dropped_passives = source_to_connectivity(source_lines)
    if not saw_subckt or not saw_ends:
        raise ValueError(f"source netlist lacks subckt/ends: {source_path}")
    source_conn.write_text("".join(source_output), encoding="utf-8")

    extracted_lines = extracted_path.read_text(encoding="utf-8").splitlines(keepends=True)
    passive_diagnostic = passive_abstraction_diagnostic(source_lines, extracted_lines)
    extracted_output, deleted_caps, removed_props, renamed_lines = extracted_to_connectivity(
        extracted_lines, renames
    )
    extracted_conn.write_text("".join(extracted_output), encoding="utf-8")

    write_report(
        report_path,
        source_path,
        extracted_path,
        raw_copy,
        source_conn,
        extracted_conn,
        deleted_caps,
        removed_props,
        model_aliases,
        dropped_passives,
        renames,
        renamed_lines,
        passive_diagnostic,
    )

    print(f"raw_extracted={raw_copy}")
    print(f"connectivity_source={source_conn}")
    print(f"connectivity_extracted={extracted_conn}")
    print(f"report={report_path}")
    print(f"deleted_caps={deleted_caps}")
    print("net_renames=yes" if renames else "net_renames=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
