#!/usr/bin/env python3
"""Diagnose NMOS source/drain terminal mapping in the pinned-shapes GDS."""

from __future__ import annotations

import argparse
import math
import re
import struct
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.sky130_adapter import diagnose_gds_connectivity as conn  # noqa: E402


DEFAULT_GDS = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds"
DEFAULT_EXTRACTED = REPO_ROOT / "generated/sky130_lvs_pinned_shapes/inverter_core_extracted_pinned_shapes.spice"
ALT_EXTRACTED = REPO_ROOT / "generated/sky130_lvs_pinned_shapes/inverter_core_extracted.spice"
DEFAULT_CONNECTIVITY_REPORT = REPO_ROOT / "docs/sky130_adapter/gds_connectivity_diagnosis.md"
DEFAULT_IOPIN = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.ioPin"
DEFAULT_REPORT = REPO_ROOT / "docs/sky130_adapter/nmos_terminal_mapping_diagnosis.md"
DEFAULT_DEBUG_GDS = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.nmos_terminal_debug.gds"
DEFAULT_CELL = "inverter_core_flat"

SOURCE_NODE = "a_n15_90#"
SOURCE_NODE_RAW_COORD = (-15, 90)
SOURCE_NODE_GDS_COORD = (SOURCE_NODE_RAW_COORD[0] * 5, SOURCE_NODE_RAW_COORD[1] * 5)

DEBUG_TEXT_LAYER = 200
DEBUG_TEXTTYPE = 0


@dataclass(frozen=True)
class DeviceCandidate:
    diff: conn.Element
    poly: conn.Element
    score: float

    @property
    def left_box(self) -> conn.Box:
        return conn.Box(self.diff.bbox.x1, self.diff.bbox.y1, self.poly.bbox.x1, self.diff.bbox.y2)

    @property
    def right_box(self) -> conn.Box:
        return conn.Box(self.poly.bbox.x2, self.diff.bbox.y1, self.diff.bbox.x2, self.diff.bbox.y2)

    @property
    def gate_box(self) -> conn.Box:
        return self.poly.bbox


@dataclass(frozen=True)
class TerminalInfo:
    side: str
    box: conn.Box
    seed_contacts: list[conn.Element]
    roots: list[int]
    members: list[conn.Element]
    layer_counts: dict[str, int]
    pin_overlaps: dict[str, list[conn.Element]]
    connected_names: set[str]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def resolve_extracted(path: Path) -> Path:
    if path.is_file():
        return path
    if DEFAULT_EXTRACTED.is_file():
        return DEFAULT_EXTRACTED
    if ALT_EXTRACTED.is_file():
        return ALT_EXTRACTED
    raise FileNotFoundError(path)


def parse_raw_nmos(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    result = {
        "subckt_line": "",
        "nmos_line": "",
        "d": "",
        "g": "",
        "s": "",
        "b": "",
    }
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(".subckt inverter_core_flat"):
            result["subckt_line"] = stripped
        if re.match(r"^[Xx]0\s+", stripped):
            parts = stripped.split()
            result["nmos_line"] = stripped
            if len(parts) >= 5:
                result["d"] = parts[1]
                result["g"] = parts[2]
                result["s"] = parts[3]
                result["b"] = parts[4]
    return result


def center_distance(box: conn.Box, point: tuple[int, int]) -> float:
    cx, cy = box.center()
    return math.hypot(cx - point[0], cy - point[1])


def locate_nmos(elements: list[conn.Element]) -> DeviceCandidate:
    candidates: list[DeviceCandidate] = []
    diffs = [item for item in elements if item.name == "diff.drawing"]
    polys = [item for item in elements if item.name == "poly.drawing"]
    for diff in diffs:
        for poly in polys:
            if not diff.bbox.overlaps(poly.bbox):
                continue
            if poly.bbox.x1 <= diff.bbox.x1 or poly.bbox.x2 >= diff.bbox.x2:
                continue
            overlap_y = min(diff.bbox.y2, poly.bbox.y2) - max(diff.bbox.y1, poly.bbox.y1)
            diff_height = diff.bbox.y2 - diff.bbox.y1
            if overlap_y < diff_height * 0.5:
                continue
            score = center_distance(diff.bbox, SOURCE_NODE_GDS_COORD)
            candidates.append(DeviceCandidate(diff=diff, poly=poly, score=score))
    if not candidates:
        raise RuntimeError("Could not locate an NMOS-like diff/poly crossing")
    return sorted(candidates, key=lambda item: item.score)[0]


def build_routing_uf(elements: list[conn.Element]) -> conn.UnionFind:
    """Build routing connectivity without shorting source/drain through diff.

    Diffusion is intentionally excluded from same-layer union and licon1-to-diff
    union. NMOS terminal seeds start from licon1 contacts on each side of the
    gate, then trace upward into li1/metals/vias. This approximates how source
    and drain are separated by the poly gate.
    """

    uf = conn.UnionFind(len(elements))
    by_pair: dict[tuple[int, int], list[conn.Element]] = defaultdict(list)
    by_name: dict[str, list[conn.Element]] = defaultdict(list)

    for element in elements:
        by_name[element.name].append(element)
        if element.name != "diff.drawing":
            by_pair[(element.layer, element.datatype)].append(element)

    for group in by_pair.values():
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                if left.bbox.overlaps(right.bbox):
                    uf.union(left.idx, right.idx)

    for pin_name, drawing_name in conn.PIN_TO_DRAWING.items():
        for pin in by_name.get(pin_name, []):
            for drawing in by_name.get(drawing_name, []):
                if pin.bbox.overlaps(drawing.bbox):
                    uf.union(pin.idx, drawing.idx)

    for contact_name, (_lower_name, upper_name) in conn.CONTACT_CONNECTIONS.items():
        for contact in by_name.get(contact_name, []):
            neighbor_names = [upper_name] if contact_name == "licon1.drawing" else list(conn.CONTACT_CONNECTIONS[contact_name])
            for neighbor_name in neighbor_names:
                if neighbor_name == "diff.drawing":
                    continue
                for neighbor in by_name.get(neighbor_name, []):
                    if contact.bbox.overlaps(neighbor.bbox):
                        uf.union(contact.idx, neighbor.idx)

    return uf


def terminal_info(
    side: str,
    box: conn.Box,
    elements: list[conn.Element],
    uf: conn.UnionFind,
    pins: dict[str, tuple[int, conn.Box]],
) -> TerminalInfo:
    seeds = [item for item in elements if item.name == "licon1.drawing" and item.bbox.overlaps(box)]
    roots = sorted({uf.find(seed.idx) for seed in seeds})
    members = [item for item in elements if any(uf.find(item.idx) == root for root in roots)]
    pin_overlaps = conn.component_pin_overlaps(members, pins)
    connected_names = set(pin_overlaps)
    if side == "left":
        connected_names.add(SOURCE_NODE)
    return TerminalInfo(
        side=side,
        box=box,
        seed_contacts=seeds,
        roots=roots,
        members=members,
        layer_counts=conn.layer_counts(members),
        pin_overlaps=pin_overlaps,
        connected_names=connected_names,
    )


def terminal_connected_to(terminal: TerminalInfo, name: str) -> bool:
    return name in terminal.connected_names


def classify(left: TerminalInfo, right: TerminalInfo, nmos: dict[str, str]) -> tuple[str, str]:
    y_side = "left" if terminal_connected_to(left, "Y") else "right" if terminal_connected_to(right, "Y") else "unknown"
    internal_side = "left" if terminal_connected_to(left, SOURCE_NODE) else "right" if terminal_connected_to(right, SOURCE_NODE) else "unknown"
    vgnd_side = "left" if terminal_connected_to(left, "VGND") else "right" if terminal_connected_to(right, "VGND") else "none"

    if vgnd_side == "none" and internal_side != "unknown":
        issue = "actual routing connectivity or terminal association issue"
        reason = (
            f"Magic's S-like terminal is `{nmos.get('s')}`, associated here with the {internal_side} terminal, "
            "but neither NMOS terminal component overlaps the VGND pin-purpose geometry."
        )
    elif vgnd_side == internal_side:
        issue = "Magic extraction terminal ordering or naming issue"
        reason = "The terminal associated with the internal source node also overlaps VGND, so geometry appears connected but Magic did not merge the names."
    elif vgnd_side != "none":
        issue = "source/drain association mismatch"
        reason = f"VGND overlaps the {vgnd_side} terminal while Magic reports `{nmos.get('s')}` on the {internal_side} terminal."
    else:
        issue = "undetermined"
        reason = "The simplified terminal analysis did not identify enough pin overlaps."

    return issue, f"Y terminal side: {y_side}; `{SOURCE_NODE}` terminal side: {internal_side}; VGND terminal side: {vgnd_side}. {reason}"


def box_text_list(elements: list[conn.Element]) -> str:
    if not elements:
        return "none"
    return "; ".join(item.bbox.text() for item in elements)


def pin_overlap_text(pin_overlaps: dict[str, list[conn.Element]]) -> str:
    return conn.pin_overlap_text(pin_overlaps)


def gds_record(record_type: int, data_type: int, payload: bytes = b"") -> bytes:
    length = 4 + len(payload)
    if length % 2:
        raise ValueError("GDS record length must be even")
    return struct.pack(">HBB", length, record_type, data_type) + payload


def int2_record(record_type: int, value: int) -> bytes:
    return gds_record(record_type, 0x02, struct.pack(">h", value))


def xy_record(x: int, y: int) -> bytes:
    return gds_record(0x10, 0x03, struct.pack(">ll", x, y))


def string_record(text: str) -> bytes:
    payload = text.encode("ascii", errors="replace")
    if len(payload) % 2:
        payload += b"\0"
    return gds_record(0x19, 0x06, payload)


def text_element(text: str, x: int, y: int) -> bytes:
    return b"".join(
        [
            gds_record(0x0C, 0x00),
            int2_record(0x0D, DEBUG_TEXT_LAYER),
            int2_record(0x16, DEBUG_TEXTTYPE),
            xy_record(x, y),
            string_record(text),
            gds_record(0x11, 0x00),
        ]
    )


def read_gds_records(data: bytes) -> list[tuple[int, int, int, bytes]]:
    records = []
    offset = 0
    while offset < len(data):
        length, record_type, data_type = struct.unpack(">HBB", data[offset : offset + 4])
        records.append((offset, record_type, data_type, data[offset + 4 : offset + length]))
        offset += length
    return records


def read_gds_string(payload: bytes) -> str:
    return payload.rstrip(b"\0").decode("ascii", errors="replace")


def find_cell_endstr_offset(data: bytes, cell_name: str) -> int:
    in_target = False
    last_endstr = None
    for offset, record_type, _data_type, payload in read_gds_records(data):
        if record_type == 0x06:
            in_target = read_gds_string(payload) == cell_name
        elif record_type == 0x07:
            last_endstr = offset
            if in_target:
                return offset
            in_target = False
    if last_endstr is None:
        raise ValueError("No ENDSTR found in GDS")
    return last_endstr


def write_debug_gds(input_gds: Path, output_gds: Path, device: DeviceCandidate, left: TerminalInfo, right: TerminalInfo) -> None:
    data = input_gds.read_bytes()
    insert_at = find_cell_endstr_offset(data, DEFAULT_CELL)
    left_center = left.box.center()
    right_center = right.box.center()
    gate_center = device.gate_box.center()
    markers = b"".join(
        [
            text_element("NMOS_LEFT_TERMINAL", int(left_center[0]), int(left_center[1])),
            text_element("NMOS_RIGHT_TERMINAL", int(right_center[0]), int(right_center[1])),
            text_element("MAGIC_X0_S_a_n15_90", int(left_center[0]), int(left_center[1]) + 120),
            text_element("MAGIC_X0_D_Y", int(right_center[0]), int(right_center[1]) + 120),
            text_element("NMOS_GATE_A", int(gate_center[0]), int(gate_center[1])),
        ]
    )
    output_gds.parent.mkdir(parents=True, exist_ok=True)
    output_gds.write_bytes(data[:insert_at] + markers + data[insert_at:])


def terminal_rows(left: TerminalInfo, right: TerminalInfo) -> list[str]:
    rows = [
        "| terminal | bbox | seed licon1 count | component roots | layer contents | pin-purpose overlaps | met5 present |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for terminal in (left, right):
        rows.append(
            f"| {terminal.side} | {terminal.box.text()} | {len(terminal.seed_contacts)} | "
            f"{', '.join(str(root) for root in terminal.roots) or 'none'} | "
            f"{conn.format_counts(terminal.layer_counts)} | "
            f"{pin_overlap_text(terminal.pin_overlaps)} | "
            f"{'yes' if 'met5.drawing' in terminal.layer_counts else 'no'} |"
        )
    return rows


def generate_report(
    gds_path: Path,
    extracted_path: Path,
    connectivity_report: Path,
    iopin_path: Path,
    debug_gds: Path,
    device: DeviceCandidate,
    left: TerminalInfo,
    right: TerminalInfo,
    nmos: dict[str, str],
    issue: str,
    reason: str,
) -> str:
    vgnd_connected = terminal_connected_to(left, "VGND") or terminal_connected_to(right, "VGND")
    y_side = "left" if terminal_connected_to(left, "Y") else "right" if terminal_connected_to(right, "Y") else "unknown"
    internal_side = "left" if terminal_connected_to(left, SOURCE_NODE) else "right" if terminal_connected_to(right, SOURCE_NODE) else "unknown"
    lines = [
        "# NMOS Terminal Mapping Diagnosis",
        "",
        "## Inputs",
        "",
        f"- GDS: `{rel(gds_path)}`",
        f"- Raw extracted netlist: `{rel(extracted_path)}`",
        f"- Previous connectivity report: `{rel(connectivity_report)}`",
        f"- ioPin file: `{rel(iopin_path)}`",
        f"- Debug GDS: `{rel(debug_gds)}`",
        "",
        "## Raw Magic NMOS Interpretation",
        "",
        f"- `.subckt`: `{nmos.get('subckt_line') or 'not found'}`",
        f"- NMOS line: `{nmos.get('nmos_line') or 'not found'}`",
        f"- D-like terminal: `{nmos.get('d')}`",
        f"- G terminal: `{nmos.get('g')}`",
        f"- S-like terminal: `{nmos.get('s')}`",
        f"- B terminal: `{nmos.get('b')}`",
        "",
        "## Located NMOS Device",
        "",
        f"- Device diff bbox: `{device.diff.bbox.text()}`",
        f"- Gate poly bbox: `{device.poly.bbox.text()}`",
        f"- Left terminal bbox: `{left.box.text()}`",
        f"- Right terminal bbox: `{right.box.text()}`",
        f"- Source node coordinate hint: raw `{SOURCE_NODE_RAW_COORD}`, GDS `{SOURCE_NODE_GDS_COORD}`",
        "",
        "## Terminal Component Summary",
        "",
    ]
    lines.extend(terminal_rows(left, right))
    lines.extend(
        [
            "",
            "## Terminal Seed Contacts",
            "",
            "| terminal | licon1 contact boxes |",
            "| --- | --- |",
            f"| left | {box_text_list(left.seed_contacts)} |",
            f"| right | {box_text_list(right.seed_contacts)} |",
            "",
            "## Diagnosis",
            "",
            f"- Terminal connected to Y: `{y_side}`",
            f"- Terminal associated with `{SOURCE_NODE}`: `{internal_side}`",
            f"- VGND pin-purpose geometry overlaps an NMOS terminal component: {'yes' if vgnd_connected else 'no'}",
            f"- Current classification: **{issue}**.",
            f"- Reason: {reason}",
            "",
        ]
    )

    if not vgnd_connected:
        lines.extend(
            [
                "The NMOS source/drain terminals identified around the gate do not overlap the VGND pin-purpose component. This points away from Magic terminal ordering as the main issue and toward MAGICAL routing or terminal association: the device terminal that should be tied to VGND is currently left as an independent routed component.",
                "",
                "## Next Minimum Step",
                "",
                "Trace how MAGICAL assigns the NMOS source/drain pins from the device generator into the router. The smallest likely fix is to align the NMOS terminal pin association so the terminal Magic extracts as `a_n15_90#` is routed to `VGND`, or to swap/normalize source-drain pin mapping before routing if MAGICAL and Magic disagree on terminal orientation.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "VGND overlaps one terminal component, so the next step is to compare Magic's extracted terminal ordering against MAGICAL's source/drain pin ordering.",
                "",
            ]
        )

    lines.extend(
        [
            "Keep `normalize_lvs_netlists_inverter.py` for now. It is still required because raw extraction keeps `a_n15_90#`.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose NMOS terminal mapping in pinned-shapes GDS.")
    parser.add_argument("--gds", type=Path, default=DEFAULT_GDS)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--connectivity-report", type=Path, default=DEFAULT_CONNECTIVITY_REPORT)
    parser.add_argument("--iopin", type=Path, default=DEFAULT_IOPIN)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--debug-gds", type=Path, default=DEFAULT_DEBUG_GDS)
    parser.add_argument("--no-debug-gds", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    gds_path = args.gds.resolve()
    extracted_path = args.extracted.resolve()
    if not extracted_path.is_file() and extracted_path.name == "inverter_core_extracted.spice":
        extracted_path = DEFAULT_EXTRACTED
    connectivity_report = args.connectivity_report.resolve()
    iopin_path = args.iopin.resolve()
    report_path = args.report.resolve()
    debug_gds = args.debug_gds.resolve()

    try:
        for path in (gds_path, extracted_path, iopin_path):
            if not path.is_file():
                raise FileNotFoundError(path)
        elements = conn.parse_gds_boundaries(gds_path)
        pins = conn.read_iopin(iopin_path)
        nmos = parse_raw_nmos(extracted_path)
        device = locate_nmos(elements)
        uf = build_routing_uf(elements)
        left = terminal_info("left", device.left_box, elements, uf, pins)
        right = terminal_info("right", device.right_box, elements, uf, pins)
        issue, reason = classify(left, right, nmos)

        if not args.no_debug_gds:
            write_debug_gds(gds_path, debug_gds, device, left, right)

        report = generate_report(
            gds_path,
            extracted_path,
            connectivity_report,
            iopin_path,
            debug_gds,
            device,
            left,
            right,
            nmos,
            issue,
            reason,
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")

        print(f"NMOS diff bbox: {device.diff.bbox.text()}")
        print(f"NMOS gate poly bbox: {device.poly.bbox.text()}")
        print(f"Left terminal bbox: {left.box.text()} -> {pin_overlap_text(left.pin_overlaps)}")
        print(f"Right terminal bbox: {right.box.text()} -> {pin_overlap_text(right.pin_overlaps)}")
        print(f"Raw NMOS D/G/S/B: {nmos.get('d')}/{nmos.get('g')}/{nmos.get('s')}/{nmos.get('b')}")
        print(f"Classification: {issue}")
        print(f"Report written: {report_path}")
        if not args.no_debug_gds:
            print(f"Debug GDS written: {debug_gds}")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
