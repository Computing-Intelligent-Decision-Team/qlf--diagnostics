#!/usr/bin/env python3
"""Insert small route-to-MOS pin bridges derived from MOS split-net evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from add_local_power_stripe_to_gds import (
    StripeSegment,
    boundary_element,
    find_cell_endstr_offset,
    text_element,
)
from reconstruct_passive_identity import Box, RouteShape, parse_gr_file, parse_pin_file, parse_placement_log


ROUTE_LAYER_TO_GDS = {
    1: {"name": "li1", "drawing": (67, 20), "pin": (67, 16), "label": (67, 5)},
    2: {"name": "met1", "drawing": (68, 20), "pin": (68, 16), "label": (68, 5)},
    3: {"name": "met2", "drawing": (69, 20), "pin": (69, 16), "label": (69, 5)},
    4: {"name": "met3", "drawing": (70, 20), "pin": (70, 16), "label": (70, 5)},
    5: {"name": "met4", "drawing": (71, 20), "pin": (71, 16), "label": (71, 5)},
    6: {"name": "met5", "drawing": (72, 20), "pin": (72, 16), "label": (72, 5)},
}

TERMINAL_NAMES = ("drain", "gate", "source", "bulk")


@dataclass(frozen=True)
class SourceMos:
    instance: str
    model_class: str
    terminals: tuple[str, str, str, str]


@dataclass(frozen=True)
class MosRouteBridge:
    net: str
    source_instance: str
    magical_instance: str
    pin_index: int
    terminal_role: str
    pin_box: Box
    route_id: int
    route_layer: int
    route_box: Box
    bridge_box: Box
    manhattan_gap_dbu: int
    split_candidate_nets: tuple[str, ...]

    def as_summary(self) -> dict[str, Any]:
        layer = ROUTE_LAYER_TO_GDS[self.route_layer]
        return {
            "net": self.net,
            "source_instance": self.source_instance,
            "magical_instance": self.magical_instance,
            "pin_index": self.pin_index,
            "terminal_role": self.terminal_role,
            "pin_box": self.pin_box.as_list(),
            "route_id": self.route_id,
            "route_layer": self.route_layer,
            "route_layer_name": layer["name"],
            "route_box": self.route_box.as_list(),
            "bridge_box": self.bridge_box.as_list(),
            "manhattan_gap_dbu": self.manhattan_gap_dbu,
            "split_candidate_nets": list(self.split_candidate_nets),
            "gds_layers": layer,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add MOS-pin-to-route bridge geometry to a GDS.")
    parser.add_argument("--input-gds", type=Path, required=True)
    parser.add_argument("--output-gds", type=Path, required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--source-netlist", type=Path, required=True)
    parser.add_argument("--pin-file", type=Path, required=True)
    parser.add_argument("--gr-file", type=Path, required=True)
    parser.add_argument("--placement-log", type=Path, required=True)
    parser.add_argument("--mos-connectivity-summary", type=Path, required=True)
    parser.add_argument("--top-cell", required=True)
    parser.add_argument("--max-gap-dbu", type=int, default=200)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    return parser.parse_args()


def model_class(model: str) -> str | None:
    lower = model.lower()
    if "nfet" in lower or "nmos" in lower or "nch" in lower:
        return "nfet"
    if "pfet" in lower or "pmos" in lower or "pch" in lower:
        return "pfet"
    return None


def parse_source_mos(path: Path) -> list[SourceMos]:
    devices: list[SourceMos] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("."):
            continue
        tokens = stripped.replace("(", " ").replace(")", " ").split()
        if len(tokens) < 6 or not tokens[0].lower().startswith(("m", "x")):
            continue
        cls = model_class(tokens[5])
        if cls is None:
            continue
        devices.append(
            SourceMos(
                instance=tokens[0],
                model_class=cls,
                terminals=tuple(token.lower() for token in tokens[1:5]),  # type: ignore[arg-type]
            )
        )
    return devices


def split_reference_nets(connectivity_summary: dict[str, Any]) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for item in connectivity_summary.get("split_net_repair_suggestions", []):
        if not isinstance(item, dict):
            continue
        reference_nets = item.get("reference_nets", [])
        if not isinstance(reference_nets, list) or len(reference_nets) != 1:
            continue
        reference_net = str(reference_nets[0]).lower()
        for group in item.get("candidate_net_groups", []):
            if not isinstance(group, dict):
                continue
            candidate_nets = {
                str(net).lower()
                for net in group.get("candidate_nets", [])
                if str(net).strip()
            }
            if reference_net in candidate_nets and len(candidate_nets) > 1:
                refs.setdefault(reference_net, set()).update(candidate_nets)
    return refs


def bridge_between(pin_box: Box, route_box: Box) -> tuple[Box | None, int]:
    x1 = max(pin_box.x1, route_box.x1)
    x2 = min(pin_box.x2, route_box.x2)
    y1 = max(pin_box.y1, route_box.y1)
    y2 = min(pin_box.y2, route_box.y2)
    if x1 < x2:
        if pin_box.y2 <= route_box.y1:
            return Box(x1, pin_box.y2, x2, route_box.y1), route_box.y1 - pin_box.y2
        if route_box.y2 <= pin_box.y1:
            return Box(x1, route_box.y2, x2, pin_box.y1), pin_box.y1 - route_box.y2
    if y1 < y2:
        if pin_box.x2 <= route_box.x1:
            return Box(pin_box.x2, y1, route_box.x1, y2), route_box.x1 - pin_box.x2
        if route_box.x2 <= pin_box.x1:
            return Box(route_box.x2, y1, pin_box.x1, y2), pin_box.x1 - route_box.x2
    return None, 0


def nearest_bridgeable_route(pin_box: Box, routes: list[RouteShape]) -> tuple[RouteShape, Box, int] | None:
    best: tuple[int, RouteShape, Box] | None = None
    for route in routes:
        if route.layer not in ROUTE_LAYER_TO_GDS:
            continue
        bridge, gap = bridge_between(pin_box, route.box)
        if bridge is None or gap <= 0:
            continue
        if best is None or gap < best[0]:
            best = (gap, route, bridge)
    if best is None:
        return None
    gap, route, bridge = best
    return route, bridge, gap


def magical_instance_name(top_cell: str, instance: str) -> str:
    return f"{top_cell}_{instance}" if top_cell else instance


def build_bridge_plan(
    *,
    source_netlist: Path,
    pin_file: Path,
    gr_file: Path,
    placement_log: Path,
    mos_connectivity_summary: dict[str, Any],
    top_cell: str,
    max_gap_dbu: int,
) -> list[MosRouteBridge]:
    source_mos = parse_source_mos(source_netlist)
    pin_shapes = parse_pin_file(pin_file)
    placements = parse_placement_log(placement_log)
    routes_by_net: dict[str, list[RouteShape]] = {}
    for route in parse_gr_file(gr_file):
        routes_by_net.setdefault(route.net.lower(), []).append(route)
    split_refs = split_reference_nets(mos_connectivity_summary)

    bridges: list[MosRouteBridge] = []
    seen: set[tuple[str, tuple[int, int, int, int]]] = set()
    for reference_net, candidate_nets in sorted(split_refs.items()):
        routes = routes_by_net.get(reference_net, [])
        if not routes:
            continue
        for device in source_mos:
            magical_name = magical_instance_name(top_cell, device.instance)
            placement = placements.get(magical_name)
            shapes = pin_shapes.get(magical_name, [])
            if placement is None:
                continue
            for pin_index, terminal in enumerate(device.terminals):
                if terminal != reference_net or pin_index >= len(shapes):
                    continue
                local_box = shapes[pin_index].local_box
                if local_box is None:
                    continue
                pin_box = local_box.translated(*placement)
                if any(route.box.intersects(pin_box) for route in routes):
                    continue
                nearest = nearest_bridgeable_route(pin_box, routes)
                if nearest is None:
                    continue
                route, bridge_box, gap = nearest
                if gap > max_gap_dbu:
                    continue
                key = (reference_net, tuple(bridge_box.as_list()))
                if key in seen:
                    continue
                seen.add(key)
                bridges.append(
                    MosRouteBridge(
                        net=reference_net,
                        source_instance=device.instance,
                        magical_instance=magical_name,
                        pin_index=pin_index,
                        terminal_role=f"{device.model_class}.{TERMINAL_NAMES[pin_index]}",
                        pin_box=pin_box,
                        route_id=route.route_id,
                        route_layer=route.layer,
                        route_box=route.box,
                        bridge_box=bridge_box,
                        manhattan_gap_dbu=gap,
                        split_candidate_nets=tuple(sorted(candidate_nets)),
                    )
                )
    return bridges


def write_bridged_gds(*, input_gds: Path, output_gds: Path, cell: str, bridges: list[MosRouteBridge]) -> None:
    data = input_gds.read_bytes()
    insert_offset = find_cell_endstr_offset(data, cell)
    inserted: list[bytes] = []
    for bridge in bridges:
        layer = ROUTE_LAYER_TO_GDS[bridge.route_layer]
        segment = StripeSegment(*bridge.bridge_box.as_list())
        drawing_layer, drawing_datatype = layer["drawing"]
        pin_layer, pin_datatype = layer["pin"]
        label_layer, label_texttype = layer["label"]
        inserted.append(boundary_element(drawing_layer, drawing_datatype, segment))
        inserted.append(boundary_element(pin_layer, pin_datatype, segment))
        cx, cy = segment.center
        inserted.append(text_element(label_layer, label_texttype, cx, cy, bridge.net))
    output_gds.parent.mkdir(parents=True, exist_ok=True)
    output_gds.write_bytes(data[:insert_offset] + b"".join(inserted) + data[insert_offset:])


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# MOS Route Bridge Injection",
        "",
        f"- Status: `{summary['status']}`",
        f"- Input GDS: `{summary['input_gds']}`",
        f"- Output GDS: `{summary['output_gds']}`",
        f"- Bridge count: {summary['bridge_count']}",
        f"- Max gap DBU: {summary['max_gap_dbu']}",
        "",
        "## Bridges",
        "",
        "| net | source instance | pin | role | route layer | gap DBU | bridge box |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for bridge in summary["bridges"]:
        lines.append(
            "| `{net}` | `{source_instance}` | {pin_index} | `{terminal_role}` | "
            "`{route_layer_name}` | {manhattan_gap_dbu} | `{bridge_box}` |".format(**bridge)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Bridge geometry is derived from MOS split-net evidence plus MAGICAL route/pin intermediates. "
            "It is a physical GDS repair candidate; downstream DRC and LVS evidence must still pass before "
            "the candidate is treated as layout-verified.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    connectivity = json.loads(args.mos_connectivity_summary.read_text(encoding="utf-8"))
    bridges = build_bridge_plan(
        source_netlist=args.source_netlist.resolve(),
        pin_file=args.pin_file.resolve(),
        gr_file=args.gr_file.resolve(),
        placement_log=args.placement_log.resolve(),
        mos_connectivity_summary=connectivity,
        top_cell=args.top_cell,
        max_gap_dbu=max(0, args.max_gap_dbu),
    )
    if bridges:
        write_bridged_gds(
            input_gds=args.input_gds.resolve(),
            output_gds=args.output_gds.resolve(),
            cell=args.cell,
            bridges=bridges,
        )
        status = "bridges_inserted"
    else:
        args.output_gds.parent.mkdir(parents=True, exist_ok=True)
        args.output_gds.write_bytes(args.input_gds.read_bytes())
        status = "no_bridges_needed_or_found"
    summary = {
        "schema_version": "mos_route_bridge_injection.v1",
        "status": status,
        "input_gds": str(args.input_gds.resolve()),
        "output_gds": str(args.output_gds.resolve()),
        "cell": args.cell,
        "source_netlist": str(args.source_netlist.resolve()),
        "pin_file": str(args.pin_file.resolve()),
        "gr_file": str(args.gr_file.resolve()),
        "placement_log": str(args.placement_log.resolve()),
        "mos_connectivity_summary": str(args.mos_connectivity_summary.resolve()),
        "top_cell": args.top_cell,
        "max_gap_dbu": max(0, args.max_gap_dbu),
        "bridge_count": len(bridges),
        "bridges": [bridge.as_summary() for bridge in bridges],
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(summary), encoding="utf-8")
    print(f"status={status}")
    print(f"bridge_count={len(bridges)}")
    print(f"output_gds={args.output_gds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
