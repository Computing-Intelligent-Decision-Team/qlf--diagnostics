#!/usr/bin/env python3
"""Reconstruct passive instance identity from MAGICAL placement/routing intermediates."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prepare_lvs_netlists import (
    SourcePassive,
    parse_extracted_physical_passives,
    parse_source_passives,
)


PLACEMENT_NODE_RE = re.compile(r"^node\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s*$")
ROUTE_LAYER_TO_MAGIC_LABEL_LAYER = {
    1: "li1",
    2: "met1",
    3: "met2",
    4: "met3",
    5: "met4",
    6: "met5",
}


@dataclass(frozen=True)
class Box:
    x1: int
    y1: int
    x2: int
    y2: int

    @classmethod
    def from_tokens(cls, tokens: list[str]) -> "Box":
        if len(tokens) != 4:
            raise ValueError(f"expected 4 box coordinates, got {tokens}")
        x1, y1, x2, y2 = (int(token) for token in tokens)
        return cls(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

    def translated(self, dx: int, dy: int) -> "Box":
        return Box(self.x1 + dx, self.y1 + dy, self.x2 + dx, self.y2 + dy)

    def intersects(self, other: "Box") -> bool:
        return self.x1 < other.x2 and other.x1 < self.x2 and self.y1 < other.y2 and other.y1 < self.y2

    def as_list(self) -> list[int]:
        return [self.x1, self.y1, self.x2, self.y2]


@dataclass(frozen=True)
class PinShape:
    local_box: Box | None


@dataclass(frozen=True)
class RouteShape:
    net: str
    route_id: int
    layer: int
    box: Box


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconstruct passive identity from MAGICAL .pin/.gr/log files.")
    parser.add_argument("--source-netlist", type=Path, required=True, help="Source SPICE netlist.")
    parser.add_argument("--pin-file", type=Path, required=True, help="MAGICAL .pin file.")
    parser.add_argument("--gr-file", type=Path, required=True, help="MAGICAL .gr global-routing file.")
    parser.add_argument("--placement-log", type=Path, required=True, help="MAGICAL placement/run log.")
    parser.add_argument("--report", type=Path, required=True, help="Markdown report path.")
    parser.add_argument("--summary-json", type=Path, help="Machine-readable JSON summary path.")
    parser.add_argument("--top-cell", default="", help="Top-cell prefix used in MAGICAL instance names.")
    parser.add_argument("--extracted-netlist", type=Path, help="Optional Magic extracted netlist for cross-check.")
    return parser.parse_args()


def parse_pin_file(path: Path) -> dict[str, list[PinShape]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    if not lines:
        return {}
    index = 1
    cells: dict[str, list[PinShape]] = {}
    while index < len(lines):
        header = lines[index].split()
        index += 1
        if len(header) != 2:
            raise ValueError(f"invalid pin block header in {path}: {' '.join(header)}")
        cell_name, pin_count_raw = header
        pin_count = int(pin_count_raw)
        pins: list[PinShape] = []
        for _ in range(pin_count):
            if index >= len(lines):
                raise ValueError(f"pin block ended early for {cell_name}")
            tokens = lines[index].split()
            index += 1
            if tokens == ["-1"]:
                pins.append(PinShape(local_box=None))
            else:
                pins.append(PinShape(local_box=Box.from_tokens(tokens)))
        cells[cell_name] = pins
    return cells


def parse_gr_file(path: Path) -> list[RouteShape]:
    shapes: list[RouteShape] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("gridStep", "Offset", "symAxis", "NET_SPEC:")):
            continue
        tokens = stripped.split()
        if len(tokens) < 7:
            continue
        if not re.match(r"^-?\d+$", tokens[1]):
            continue
        try:
            shapes.append(
                RouteShape(
                    net=tokens[0],
                    route_id=int(tokens[1]),
                    layer=int(tokens[2]),
                    box=Box.from_tokens(tokens[3:7]),
                )
            )
        except ValueError:
            continue
    return shapes


def parse_placement_log(path: Path) -> dict[str, tuple[int, int]]:
    placements: dict[str, tuple[int, int]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = PLACEMENT_NODE_RE.match(line.strip())
        if match:
            placements[match.group(1)] = (int(match.group(2)), int(match.group(3)))
    return placements


def source_passives(path: Path) -> list[SourcePassive]:
    return parse_source_passives(path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True))


def magical_instance_name(top_cell: str, source_instance: str) -> str:
    return f"{top_cell}_{source_instance}" if top_cell else source_instance


def match_route_shapes(expected_net: str, global_box: Box | None, routes: list[RouteShape]) -> tuple[str, list[RouteShape]]:
    if global_box is None:
        return "no_pin_geometry", []
    same_net = [shape for shape in routes if shape.net == expected_net]
    exact = [shape for shape in same_net if shape.box == global_box]
    if exact:
        return "exact", exact
    overlapping = [shape for shape in same_net if shape.box.intersects(global_box)]
    if overlapping:
        return "overlap", overlapping
    return "missing", []


def suggested_magic_label_layer(matches: list[RouteShape]) -> str | None:
    if not matches:
        return None
    return ROUTE_LAYER_TO_MAGIC_LABEL_LAYER.get(matches[0].layer)


def extracted_passive_terminal_hits(path: Path | None, expected_terminals: set[str]) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {
            "extracted_netlist": str(path) if path else None,
            "extracted_physical_passive_count": None,
            "expected_terminals_in_extracted_physical_passives": [],
        }
    devices = parse_extracted_physical_passives(path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True))
    terminals = {
        terminal
        for device in devices
        for terminal in device.terminals
        if terminal in expected_terminals
    }
    return {
        "extracted_netlist": str(path),
        "extracted_physical_passive_count": len(devices),
        "expected_terminals_in_extracted_physical_passives": sorted(terminals),
    }


def build_summary(
    *,
    source_netlist: Path,
    pin_file: Path,
    gr_file: Path,
    placement_log: Path,
    top_cell: str,
    extracted_netlist: Path | None,
) -> dict[str, Any]:
    passives = source_passives(source_netlist)
    pin_shapes = parse_pin_file(pin_file)
    routes = parse_gr_file(gr_file)
    placements = parse_placement_log(placement_log)
    route_nets = sorted({shape.net for shape in routes})
    instances: list[dict[str, Any]] = []
    pin_total = 0
    pins_with_geometry = 0
    exact_matches = 0
    overlap_matches = 0
    missing_matches = 0
    no_geometry = 0
    label_candidates = 0

    for passive in passives:
        magical_name = magical_instance_name(top_cell, passive.instance)
        placement = placements.get(magical_name)
        shapes = pin_shapes.get(magical_name, [])
        terminal_rows: list[dict[str, Any]] = []
        for pin_index, terminal in enumerate(passive.terminals):
            pin_total += 1
            local_box = shapes[pin_index].local_box if pin_index < len(shapes) else None
            global_box = local_box.translated(*placement) if local_box is not None and placement is not None else None
            status, matches = match_route_shapes(terminal, global_box, routes)
            if status == "exact":
                exact_matches += 1
            elif status == "overlap":
                overlap_matches += 1
            elif status == "missing":
                missing_matches += 1
            elif status == "no_pin_geometry":
                no_geometry += 1
            if global_box is not None:
                pins_with_geometry += 1
            label_layer = suggested_magic_label_layer(matches)
            if label_layer is not None:
                label_candidates += 1
            terminal_rows.append(
                {
                    "pin_index": pin_index,
                    "terminal": terminal,
                    "local_box": None if local_box is None else local_box.as_list(),
                    "global_box": None if global_box is None else global_box.as_list(),
                    "match_status": status,
                    "suggested_magic_label_layer": label_layer,
                    "suggested_magic_label_command": (
                        None
                        if global_box is None or label_layer is None
                        else f"box {global_box.x1} {global_box.y1} {global_box.x2} {global_box.y2}; label {terminal} center {label_layer}"
                    ),
                    "matched_routes": [
                        {
                            "net": route.net,
                            "route_id": route.route_id,
                            "layer": route.layer,
                            "box": route.box.as_list(),
                        }
                        for route in matches
                    ],
                }
            )
        instances.append(
            {
                "source_instance": passive.instance,
                "magical_instance": magical_name,
                "model": passive.model,
                "placement_origin": None if placement is None else [placement[0], placement[1]],
                "pin_shape_count": len(shapes),
                "terminal_count": len(passive.terminals),
                "terminals": terminal_rows,
            }
        )

    geometry_pins = pin_total - no_geometry
    if pin_total == 0:
        status = "not_applicable"
    elif missing_matches == 0 and geometry_pins > 0:
        status = "source_passive_pin_identity_reconstructed_from_magical_intermediates"
    elif exact_matches + overlap_matches > 0:
        status = "partial_source_passive_pin_identity_reconstruction"
    else:
        status = "source_passive_pin_identity_not_reconstructed"

    expected_terminals = {terminal for passive in passives for terminal in passive.terminals}
    return {
        "status": status,
        "source_netlist": str(source_netlist),
        "pin_file": str(pin_file),
        "gr_file": str(gr_file),
        "placement_log": str(placement_log),
        "top_cell": top_cell,
        "source_passive_count": len(passives),
        "source_passive_pin_count": pin_total,
        "source_passive_pins_with_geometry": pins_with_geometry,
        "source_passive_pins_without_geometry": no_geometry,
        "source_passive_pin_exact_route_matches": exact_matches,
        "source_passive_pin_overlap_route_matches": overlap_matches,
        "source_passive_pin_missing_route_matches": missing_matches,
        "source_passive_label_injection_candidates": label_candidates,
        "route_net_count": len(route_nets),
        "route_nets": route_nets,
        "instances": instances,
        "extracted_crosscheck": extracted_passive_terminal_hits(extracted_netlist, expected_terminals),
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Passive Identity Reconstruction Report",
        "",
        "## Summary",
        "",
        f"- Status: `{summary['status']}`",
        f"- Source passive devices: {summary['source_passive_count']}",
        f"- Source passive pins: {summary['source_passive_pin_count']}",
        f"- Pins with MAGICAL geometry: {summary['source_passive_pins_with_geometry']}",
        f"- Pins without MAGICAL geometry: {summary['source_passive_pins_without_geometry']}",
        f"- Exact route matches: {summary['source_passive_pin_exact_route_matches']}",
        f"- Overlap route matches: {summary['source_passive_pin_overlap_route_matches']}",
        f"- Missing route matches: {summary['source_passive_pin_missing_route_matches']}",
        f"- Label injection candidates: {summary['source_passive_label_injection_candidates']}",
        "",
        "## Passive Pin Mapping",
        "",
    ]
    for instance in summary["instances"]:
        lines.extend(
            [
                f"### `{instance['source_instance']}`",
                "",
                f"- MAGICAL instance: `{instance['magical_instance']}`",
                f"- Model: `{instance['model']}`",
                f"- Placement origin: `{instance['placement_origin']}`",
                f"- Pin shapes in `.pin`: {instance['pin_shape_count']}",
                "",
                "| pin | source terminal | local box | global box | route match | suggested Magic label | matched routes |",
                "| ---: | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for terminal in instance["terminals"]:
            matched_routes = ", ".join(
                f"{route['net']}@L{route['layer']}:{route['box']}" for route in terminal["matched_routes"]
            )
            label_command = terminal["suggested_magic_label_command"] or "none"
            lines.append(
                f"| {terminal['pin_index']} | `{terminal['terminal']}` | "
                f"`{terminal['local_box']}` | `{terminal['global_box']}` | "
                f"`{terminal['match_status']}` | `{label_command}` | `{matched_routes or 'none'}` |"
            )
        lines.append("")

    crosscheck = summary["extracted_crosscheck"]
    lines.extend(
        [
            "## Extracted Netlist Crosscheck",
            "",
            f"- Extracted netlist: `{crosscheck['extracted_netlist']}`",
            f"- Extracted physical passive devices: {crosscheck['extracted_physical_passive_count']}",
            "- Source terminals present on extracted physical passive terminals: "
            + (
                ", ".join(f"`{terminal}`" for terminal in crosscheck["expected_terminals_in_extracted_physical_passives"])
                if crosscheck["expected_terminals_in_extracted_physical_passives"]
                else "none"
            ),
            "",
            "## Interpretation",
            "",
            "MAGICAL placement/routing intermediates can recover source passive pin identity when pin boxes match source-net route rectangles.",
            "This is not a full passive-aware LVS proof by itself; it is a placement-aware mapping artifact that can drive label injection or a future passive abstraction rule.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    summary = build_summary(
        source_netlist=args.source_netlist.resolve(),
        pin_file=args.pin_file.resolve(),
        gr_file=args.gr_file.resolve(),
        placement_log=args.placement_log.resolve(),
        top_cell=args.top_cell,
        extracted_netlist=args.extracted_netlist.resolve() if args.extracted_netlist else None,
    )
    write_report(report, summary)
    if args.summary_json:
        summary_json = args.summary_json.resolve()
        summary_json.parent.mkdir(parents=True, exist_ok=True)
        summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"report={report}")
    if args.summary_json:
        print(f"summary_json={args.summary_json.resolve()}")
    print(f"status={summary['status']}")
    print(f"exact_route_matches={summary['source_passive_pin_exact_route_matches']}")
    print(f"missing_route_matches={summary['source_passive_pin_missing_route_matches']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
