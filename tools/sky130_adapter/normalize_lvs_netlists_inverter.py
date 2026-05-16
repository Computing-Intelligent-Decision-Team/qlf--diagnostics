#!/usr/bin/env python3
"""Normalize the extracted inverter netlist for the current LVS trial.

This is intentionally inverter-specific. It removes extracted parasitic
capacitors and rewrites known Magic-generated node names back to the inverter
ports used by the source netlist.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "generated/sky130_lvs/inverter_core_extracted.spice"
DEFAULT_OUTPUT = REPO_ROOT / "generated/sky130_lvs/inverter_core_extracted_normalized.spice"
DEFAULT_REPORT = REPO_ROOT / "generated/sky130_lvs/normalize_lvs_report.md"

NET_RENAMES = {
    "a_55_90#": "Y",
    "a_25_70#": "A",
    "w_245_n115#": "VPWR",
    "a_n15_90#": "VGND",
    "a_n135_n215#": "VGND",
}

REMOVED_PROPERTIES = {"ad", "as", "pd", "ps"}


def normalize_line(line: str) -> tuple[str | None, bool]:
    stripped = line.strip()
    if re.match(r"^[Cc]\S*\s+", stripped):
        return None, True

    if stripped.lower().startswith(".subckt inverter_core_flat"):
        return ".subckt inverter_core_flat A Y VPWR VGND\n", False

    normalized = line
    for old, new in NET_RENAMES.items():
        normalized = normalized.replace(old, new)

    if re.match(r"^[Xx]\S*\s+", normalized.strip()):
        tokens = normalized.split()
        kept = []
        for token in tokens:
            key = token.split("=", 1)[0].lower()
            if key in REMOVED_PROPERTIES:
                continue
            kept.append(token)
        normalized = " ".join(kept) + "\n"

    return normalized, False


def normalize(input_path: Path, output_path: Path, report_path: Path) -> None:
    lines = input_path.read_text(encoding="utf-8").splitlines(keepends=True)
    output_lines: list[str] = []
    deleted_caps = 0
    removed_properties = {name: 0 for name in sorted(REMOVED_PROPERTIES)}

    for line in lines:
        for prop in REMOVED_PROPERTIES:
            removed_properties[prop] += len(re.findall(rf"(?<!\S){prop}=", line, flags=re.IGNORECASE))
        normalized, deleted = normalize_line(line)
        if deleted:
            deleted_caps += 1
            continue
        if normalized is not None:
            output_lines.append(normalized)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(output_lines), encoding="utf-8")

    report_lines = [
        "# Inverter LVS Netlist Normalization Report",
        "",
        "## Summary",
        "",
        f"- Input extracted netlist: `{input_path}`",
        f"- Output normalized netlist: `{output_path}`",
        f"- Deleted parasitic capacitor lines: {deleted_caps}",
        f"- Removed MOS properties: {', '.join(f'{k}={v}' for k, v in removed_properties.items())}",
        "",
        "## Net Renames",
        "",
        "| Extracted net | Normalized net |",
        "| --- | --- |",
    ]
    for old, new in NET_RENAMES.items():
        report_lines.append(f"| `{old}` | `{new}` |")

    report_lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This normalization is inverter-specific and temporary.",
            "- It removes parasitic capacitors so this LVS trial compares only MOS topology.",
            "- It removes extracted ad/as/pd/ps layout-derived MOS properties to avoid property-only mismatches.",
            "- It keeps w/l properties.",
            "- It does not solve the underlying GDS label/pin preservation issue.",
            "- PEX-oriented flows should keep layout-derived parasitic and geometry properties.",
            "- A general solution should make Magic extraction preserve layout ports from labels or pins.",
            "",
        ]
    )
    report_path.write_text("\n".join(report_lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize inverter extracted netlist for LVS.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input extracted SPICE.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output normalized SPICE.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Normalization report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    report_path = args.report.resolve()

    if not input_path.is_file():
        raise FileNotFoundError(input_path)

    normalize(input_path, output_path, report_path)
    print(f"Normalized extracted netlist: {output_path}")
    print(f"Normalization report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
