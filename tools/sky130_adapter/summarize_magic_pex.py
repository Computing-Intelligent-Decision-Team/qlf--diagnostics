#!/usr/bin/env python3
"""Summarize parasitic capacitors in a Magic raw extracted SPICE netlist."""

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path


UNIT_TO_FARADS = {
    "f": 1e-15,
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Magic extracted parasitic caps.")
    parser.add_argument("--input", type=Path, required=True, help="Raw extracted SPICE netlist.")
    parser.add_argument("--output", type=Path, required=True, help="Markdown summary path.")
    parser.add_argument("--top", type=int, default=10, help="Number of largest caps to list.")
    parser.add_argument("--output-node", help="Optional top output node for a focused capacitance estimate.")
    return parser.parse_args()


def parse_cap_value(value: str) -> float | None:
    match = re.fullmatch(r"([0-9.+\-eE]+)([fpnum]?)", value.strip())
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2)
    return number * UNIT_TO_FARADS.get(unit, 1.0)


def fmt_ff(farads: float) -> str:
    return f"{farads / 1e-15:.6g} fF"


def parse_caps(lines: list[str]) -> list[tuple[str, str, str, float]]:
    caps: list[tuple[str, str, str, float]] = []
    for line in lines:
        stripped = line.strip()
        if not re.match(r"^[Cc]\S+\s+", stripped):
            continue
        tokens = stripped.split()
        if len(tokens) < 4:
            continue
        value = parse_cap_value(tokens[3])
        if value is None:
            continue
        name, node1, node2 = tokens[:3]
        caps.append((name, node1, node2, value))
    return caps


def node_stats(caps: list[tuple[str, str, str, float]]) -> tuple[Counter[str], dict[str, float]]:
    per_node_count: Counter[str] = Counter()
    per_node_cap: dict[str, float] = defaultdict(float)
    for _, node1, node2, value in caps:
        for node in (node1, node2):
            per_node_count[node] += 1
            per_node_cap[node] += value
    return per_node_count, per_node_cap


def render_summary(
    caps: list[tuple[str, str, str, float]],
    input_name: str,
    top: int = 10,
    output_node: str | None = None,
) -> str:
    per_node_count, per_node_cap = node_stats(caps)
    total = sum(cap[-1] for cap in caps)
    largest = sorted(caps, key=lambda item: item[-1], reverse=True)[:top]

    lines = [
        "# Magic PEX Summary",
        "",
        f"- Raw extracted netlist: `{input_name}`",
        f"- Parasitic capacitor count: {len(caps)}",
        f"- Total listed capacitance: {fmt_ff(total)}",
        "",
        "## Per-Node Capacitance",
        "",
        "| Node | Capacitor count | Sum connected capacitance |",
        "| --- | --- | --- |",
    ]
    for node, value in sorted(per_node_cap.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"| `{node}` | {per_node_count[node]} | {fmt_ff(value)} |")

    if output_node:
        lines.extend(
            [
                "",
                "## Output Node Estimate",
                "",
                "| Node | Connected capacitor count | Sum connected capacitance |",
                "| --- | ---: | ---: |",
                f"| `{output_node}` | {per_node_count.get(output_node, 0)} | {fmt_ff(per_node_cap.get(output_node, 0.0))} |",
            ]
        )

    lines.extend(["", f"## Largest {len(largest)} Capacitors", "", "| Cap | Node 1 | Node 2 | Value |", "| --- | --- | --- | --- |"])
    for name, node1, node2, value in largest:
        lines.append(f"| `{name}` | `{node1}` | `{node2}` | {fmt_ff(value)} |")

    lines.extend(
        [
            "",
            "## Note",
            "",
            "This is a PEX summary only. The connectivity LVS netlists intentionally remove",
            "these capacitors, while the raw extracted netlist keeps them for later analysis.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    caps = parse_caps(args.input.read_text(encoding="utf-8", errors="replace").splitlines())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render_summary(caps, str(args.input), top=args.top, output_node=args.output_node),
        encoding="utf-8",
    )
    total = sum(cap[-1] for cap in caps)
    print(f"cap_count={len(caps)}")
    print(f"total_cap_ff={total / 1e-15:.6g}")
    print(f"summary={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
