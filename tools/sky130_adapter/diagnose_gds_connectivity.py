#!/usr/bin/env python3
"""Diagnose simplified Sky130 GDS connectivity for the inverter trial.

This is a geometry-level diagnostic for the current MAGICAL Sky130 adapter
experiment. It parses the pinned-shapes GDS, builds a simplified connectivity
graph across Sky130 drawing/contact/via layers, and compares the VGND rail
component with the component near Magic's extracted `a_n15_90#` node.

The script is intentionally read-only. It does not modify GDS, PDK, source,
or normalized LVS files.
"""

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
DEFAULT_GDS = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds"
DEFAULT_EXTRACTED = REPO_ROOT / "generated/sky130_lvs_pinned_shapes/inverter_core_extracted_pinned_shapes.spice"
ALT_EXTRACTED = REPO_ROOT / "generated/sky130_lvs_pinned_shapes/inverter_core_extracted.spice"
DEFAULT_IOPIN = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.ioPin"
DEFAULT_REPORT = REPO_ROOT / "docs/sky130_adapter/gds_connectivity_diagnosis.md"

SOURCE_NODE = "a_n15_90#"
RAW_SOURCE_NODE_COORD = (-15, 90)
SOURCE_COORD_SCALE = 5
SOURCE_NODE_COORD = (RAW_SOURCE_NODE_COORD[0] * SOURCE_COORD_SCALE, RAW_SOURCE_NODE_COORD[1] * SOURCE_COORD_SCALE)
SEARCH_RADIUS = 600

DRAWING_LAYERS = {
    (65, 20): "diff.drawing",
    (66, 20): "poly.drawing",
    (67, 20): "li1.drawing",
    (68, 20): "met1.drawing",
    (69, 20): "met2.drawing",
    (70, 20): "met3.drawing",
    (71, 20): "met4.drawing",
    (72, 20): "met5.drawing",
}

CONTACT_LAYERS = {
    (66, 44): ("licon1.drawing", ("diff.drawing", "li1.drawing")),
    (67, 44): ("mcon.drawing", ("li1.drawing", "met1.drawing")),
    (68, 44): ("via.drawing", ("met1.drawing", "met2.drawing")),
    (69, 44): ("via2.drawing", ("met2.drawing", "met3.drawing")),
    (70, 44): ("via3.drawing", ("met3.drawing", "met4.drawing")),
    (71, 44): ("via4.drawing", ("met4.drawing", "met5.drawing")),
}

PIN_LAYERS = {
    (67, 16): "li1.pin",
    (68, 16): "met1.pin",
    (72, 16): "met5.pin",
}

ALL_LAYERS = set(DRAWING_LAYERS) | set(CONTACT_LAYERS) | set(PIN_LAYERS)

STACK_EDGES = [
    ("diff.drawing", "licon1.drawing"),
    ("licon1.drawing", "li1.drawing"),
    ("li1.drawing", "mcon.drawing"),
    ("mcon.drawing", "met1.drawing"),
    ("met1.drawing", "via.drawing"),
    ("via.drawing", "met2.drawing"),
    ("met2.drawing", "via2.drawing"),
    ("via2.drawing", "met3.drawing"),
    ("met3.drawing", "via3.drawing"),
    ("via3.drawing", "met4.drawing"),
    ("met4.drawing", "via4.drawing"),
    ("via4.drawing", "met5.drawing"),
]

CONTACT_CONNECTIONS = {
    "licon1.drawing": ("diff.drawing", "li1.drawing"),
    "mcon.drawing": ("li1.drawing", "met1.drawing"),
    "via.drawing": ("met1.drawing", "met2.drawing"),
    "via2.drawing": ("met2.drawing", "met3.drawing"),
    "via3.drawing": ("met3.drawing", "met4.drawing"),
    "via4.drawing": ("met4.drawing", "met5.drawing"),
}

PIN_TO_DRAWING = {
    "li1.pin": "li1.drawing",
    "met1.pin": "met1.drawing",
    "met5.pin": "met5.drawing",
}


@dataclass(frozen=True)
class Box:
    x1: int
    y1: int
    x2: int
    y2: int

    def overlaps(self, other: "Box") -> bool:
        return not (self.x2 < other.x1 or other.x2 < self.x1 or self.y2 < other.y1 or other.y2 < self.y1)

    def expanded(self, margin: int) -> "Box":
        return Box(self.x1 - margin, self.y1 - margin, self.x2 + margin, self.y2 + margin)

    def contains_point(self, point: tuple[int, int]) -> bool:
        x, y = point
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def distance_to_point(self, point: tuple[int, int]) -> float:
        x, y = point
        dx = 0 if self.x1 <= x <= self.x2 else min(abs(x - self.x1), abs(x - self.x2))
        dy = 0 if self.y1 <= y <= self.y2 else min(abs(y - self.y1), abs(y - self.y2))
        return math.hypot(dx, dy)

    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def text(self) -> str:
        return f"({self.x1}, {self.y1}) - ({self.x2}, {self.y2})"


@dataclass(frozen=True)
class Element:
    idx: int
    layer: int
    datatype: int
    name: str
    bbox: Box
    kind: str


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        if self.rank[root_left] == self.rank[root_right]:
            self.rank[root_left] += 1


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_int2(payload: bytes) -> int:
    return struct.unpack(">h", payload[:2])[0]


def read_int4_pairs(payload: bytes) -> list[tuple[int, int]]:
    if len(payload) % 8 != 0:
        raise ValueError("GDS XY payload length is not a multiple of 8")
    values = struct.unpack(f">{len(payload) // 4}l", payload)
    return [(values[i], values[i + 1]) for i in range(0, len(values), 2)]


def bbox_from_points(points: list[tuple[int, int]]) -> Box | None:
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return Box(min(xs), min(ys), max(xs), max(ys))


def layer_name(layer: int, datatype: int) -> tuple[str, str] | None:
    key = (layer, datatype)
    if key in DRAWING_LAYERS:
        return DRAWING_LAYERS[key], "drawing"
    if key in CONTACT_LAYERS:
        return CONTACT_LAYERS[key][0], "contact"
    if key in PIN_LAYERS:
        return PIN_LAYERS[key], "pin"
    return None


def parse_gds_boundaries(path: Path) -> list[Element]:
    data = path.read_bytes()
    offset = 0
    in_boundary = False
    current_layer: int | None = None
    current_datatype: int | None = None
    current_points: list[tuple[int, int]] = []
    elements: list[Element] = []

    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError(f"Truncated GDS record header at byte {offset}")
        record_len, record_type, _data_type = struct.unpack(">HBB", data[offset : offset + 4])
        if record_len < 4:
            raise ValueError(f"Invalid GDS record length {record_len} at byte {offset}")
        payload = data[offset + 4 : offset + record_len]

        if record_type == 0x08:  # BOUNDARY
            in_boundary = True
            current_layer = None
            current_datatype = None
            current_points = []
        elif in_boundary and record_type == 0x0D:  # LAYER
            current_layer = read_int2(payload)
        elif in_boundary and record_type == 0x0E:  # DATATYPE
            current_datatype = read_int2(payload)
        elif in_boundary and record_type == 0x10:  # XY
            current_points = read_int4_pairs(payload)
        elif record_type == 0x11:  # ENDEL
            if in_boundary and current_layer is not None and current_datatype is not None:
                name_kind = layer_name(current_layer, current_datatype)
                bbox = bbox_from_points(current_points)
                if name_kind is not None and bbox is not None:
                    name, kind = name_kind
                    elements.append(
                        Element(
                            idx=len(elements),
                            layer=current_layer,
                            datatype=current_datatype,
                            name=name,
                            bbox=bbox,
                            kind=kind,
                        )
                    )
            in_boundary = False

        offset += record_len

    return elements


def read_iopin(path: Path) -> dict[str, tuple[int, Box]]:
    pins: dict[str, tuple[int, Box]] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 6:
            continue
        name, layer, x1, y1, x2, y2 = parts
        xa, xb = sorted((int(x1), int(x2)))
        ya, yb = sorted((int(y1), int(y2)))
        pins[name] = (int(layer), Box(xa, ya, xb, yb))
    return pins


def resolve_extracted_path(path: Path) -> Path:
    if path.is_file():
        return path
    if path == ALT_EXTRACTED and DEFAULT_EXTRACTED.is_file():
        return DEFAULT_EXTRACTED
    if path == DEFAULT_EXTRACTED and ALT_EXTRACTED.is_file():
        return ALT_EXTRACTED
    raise FileNotFoundError(path)


def parse_extracted_source_node(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    result = {
        "subckt_line": "",
        "nmos_line": "",
        "nmos_source": "",
        "source_node_found": "no",
    }
    for line in text.splitlines():
        if line.strip().lower().startswith(".subckt inverter_core_flat"):
            result["subckt_line"] = line.strip()
        if re.match(r"^\s*X0\s+", line):
            result["nmos_line"] = line.strip()
            parts = line.split()
            if len(parts) >= 4:
                result["nmos_source"] = parts[3]
    result["source_node_found"] = "yes" if SOURCE_NODE in text else "no"
    return result


def build_connectivity(elements: list[Element]) -> UnionFind:
    uf = UnionFind(len(elements))
    by_name: dict[str, list[Element]] = defaultdict(list)
    for element in elements:
        by_name[element.name].append(element)

    # Same-layer overlap/touch connects drawing, contact, and pin-purpose shapes
    # on the same layer-purpose pair.
    by_pair: dict[tuple[int, int], list[Element]] = defaultdict(list)
    for element in elements:
        by_pair[(element.layer, element.datatype)].append(element)
    for group in by_pair.values():
        for i, left in enumerate(group):
            for right in group[i + 1 :]:
                if left.bbox.overlaps(right.bbox):
                    uf.union(left.idx, right.idx)

    # Pin-purpose shapes are annotations, but for this diagnostic we connect
    # them to overlapping drawing geometry on the same metal layer.
    for pin_name, drawing_name in PIN_TO_DRAWING.items():
        for pin in by_name.get(pin_name, []):
            for drawing in by_name.get(drawing_name, []):
                if pin.bbox.overlaps(drawing.bbox):
                    uf.union(pin.idx, drawing.idx)

    # Contacts/vias connect to their lower and upper drawing layers.
    for contact_name, (lower_name, upper_name) in CONTACT_CONNECTIONS.items():
        for contact in by_name.get(contact_name, []):
            for neighbor_name in (lower_name, upper_name):
                for neighbor in by_name.get(neighbor_name, []):
                    if contact.bbox.overlaps(neighbor.bbox):
                        uf.union(contact.idx, neighbor.idx)

    return uf


def component_members(elements: list[Element], uf: UnionFind, root: int | None) -> list[Element]:
    if root is None:
        return []
    return [element for element in elements if uf.find(element.idx) == root]


def layer_counts(members: list[Element]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for element in members:
        counts[element.name] += 1
    return dict(sorted(counts.items()))


def find_vgnd_roots(elements: list[Element], uf: UnionFind, vgnd_box: Box) -> tuple[list[int], list[Element]]:
    hits = [
        element
        for element in elements
        if element.name in {"met5.drawing", "met5.pin"} and element.bbox.overlaps(vgnd_box)
    ]
    roots = sorted({uf.find(element.idx) for element in hits})
    return roots, hits


def component_pin_overlaps(members: list[Element], pins: dict[str, tuple[int, Box]]) -> dict[str, list[Element]]:
    overlaps: dict[str, list[Element]] = {}
    for pin_name, (_layer, box) in pins.items():
        hits = [element for element in members if element.kind == "pin" and element.bbox.overlaps(box)]
        if hits:
            overlaps[pin_name] = hits
    return overlaps


def nearest_elements(elements: list[Element], point: tuple[int, int], names: set[str], limit: int = 12) -> list[tuple[float, Element]]:
    candidates = [(element.bbox.distance_to_point(point), element) for element in elements if element.name in names]
    return sorted(candidates, key=lambda item: item[0])[:limit]


def source_candidates(elements: list[Element], point: tuple[int, int]) -> list[Element]:
    search_box = Box(point[0], point[1], point[0], point[1]).expanded(SEARCH_RADIUS)
    candidates = [
        element
        for element in elements
        if element.name == "diff.drawing" and (element.bbox.contains_point(point) or element.bbox.overlaps(search_box))
    ]
    if candidates:
        return sorted(candidates, key=lambda element: element.bbox.distance_to_point(point))
    nearest = nearest_elements(elements, point, {"diff.drawing"}, limit=1)
    return [nearest[0][1]] if nearest else []


def edge_status(members: list[Element]) -> list[tuple[str, str, str]]:
    names = {element.name for element in members}
    rows: list[tuple[str, str, str]] = []
    for left, right in STACK_EDGES:
        if left in names and right in names:
            status = "present in source component"
        elif left in names and right not in names:
            status = "break after this layer"
        elif left not in names and right in names:
            status = "upper/contact present without lower side in source component"
        else:
            status = "absent from source component"
        rows.append((left, right, status))
    return rows


def first_break(rows: list[tuple[str, str, str]]) -> str:
    for left, right, status in rows:
        if status == "break after this layer":
            return f"{left} -> {right}"
    return "not identified from simplified chain"


def pin_overlap_text(overlaps: dict[str, list[Element]]) -> str:
    if not overlaps:
        return "none"
    parts: list[str] = []
    for pin_name in sorted(overlaps):
        desc = ", ".join(f"{item.name} {item.bbox.text()}" for item in overlaps[pin_name])
        parts.append(f"{pin_name}: {desc}")
    return "; ".join(parts)


def format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{name}={count}" for name, count in counts.items())


def element_table(elements: list[Element], title: str) -> list[str]:
    lines = [title, "", "| layer | datatype | purpose | kind | bbox |", "| ---: | ---: | --- | --- | --- |"]
    if not elements:
        lines.append("| none | none | none | none | none |")
    for element in elements:
        lines.append(f"| {element.layer} | {element.datatype} | {element.name} | {element.kind} | {element.bbox.text()} |")
    lines.append("")
    return lines


def generate_report(
    gds_path: Path,
    extracted_path: Path,
    iopin_path: Path,
    elements: list[Element],
    uf: UnionFind,
    extracted: dict[str, str],
    vgnd_box: Box,
    pins: dict[str, tuple[int, Box]],
    vgnd_roots: list[int],
    vgnd_hits: list[Element],
    source_elems: list[Element],
) -> str:
    source_root = uf.find(source_elems[0].idx) if source_elems else None
    source_members = component_members(elements, uf, source_root)
    source_layers = layer_counts(source_members)
    vgnd_members_by_root = {root: component_members(elements, uf, root) for root in vgnd_roots}
    same_component = source_root in vgnd_roots if source_root is not None else False
    rows = edge_status(source_members)
    source_pin_overlaps = component_pin_overlaps(source_members, pins)
    source_has_full_vertical_stack = all(status == "present in source component" for _left, _right, status in rows)
    likely_break = "none; source and VGND are in same simplified component" if same_component else first_break(rows)
    if not same_component and source_has_full_vertical_stack:
        likely_break = "not a vertical layer-stack break; source candidate is a separate routed component from VGND"

    source_near = [item for _distance, item in nearest_elements(
        elements,
        SOURCE_NODE_COORD,
        {
            "diff.drawing",
            "licon1.drawing",
            "li1.drawing",
            "mcon.drawing",
            "met1.drawing",
            "via.drawing",
            "met2.drawing",
            "via2.drawing",
            "met3.drawing",
            "via3.drawing",
            "met4.drawing",
            "via4.drawing",
            "met5.drawing",
        },
        limit=16,
    )]

    if same_component:
        issue_type = "Magic extraction rule or node naming nuance"
        next_step = "Compare Magic's extracted `.ext` node areas with the simplified GDS component, because geometry appears connected in this diagnostic."
    elif source_has_full_vertical_stack:
        issue_type = "actual routing connectivity or device-terminal association issue"
        next_step = "Use Magic/KLayout visual probing around the NMOS source diffusion to confirm which physical diffusion terminal is connected to the `a_n15_90#` component. The simplified graph shows that this component has a complete vertical stack but is routed as a separate component from the VGND rail."
    elif "diff.drawing" in source_layers and len(source_layers) == 1:
        issue_type = "layer remap or actual geometry connectivity issue near source contact"
        next_step = "Inspect the source diffusion area for overlapping `licon1.drawing 66/44` and `li1.drawing 67/20`; the minimum likely fix is correcting CO/licon1 placement or remap around the NMOS source."
    else:
        issue_type = "actual routing connectivity or layer stack issue"
        next_step = f"Focus on the first missing transition in the source component: `{likely_break}`."

    lines = [
        "# GDS Connectivity Diagnosis",
        "",
        "## 1. Current Problem",
        "",
        "The pinned-shapes GDS now has Sky130 label TEXT and pin-purpose BOUNDARY geometry for `A/Y/VPWR/VGND`. Magic extraction preserves the top-level port list, but the NMOS source terminal still appears as `a_n15_90#` instead of being merged into `VGND`.",
        "",
        "This report checks geometry connectivity rather than adding more labels.",
        "",
        "## 2. Inputs",
        "",
        f"- GDS: `{rel(gds_path)}`",
        f"- Extracted netlist: `{rel(extracted_path)}`",
        f"- ioPin file: `{rel(iopin_path)}`",
        f"- Raw coordinate implied by `{SOURCE_NODE}`: `{RAW_SOURCE_NODE_COORD}`",
        f"- GDS coordinate used for search: `{SOURCE_NODE_COORD}` (`raw * {SOURCE_COORD_SCALE}`)",
        f"- Source search radius: `{SEARCH_RADIUS}` GDS units",
        "",
        "## 3. Extracted Netlist Evidence",
        "",
        f"- `.subckt` line: `{extracted.get('subckt_line') or 'not found'}`",
        f"- NMOS line: `{extracted.get('nmos_line') or 'not found'}`",
        f"- NMOS source terminal: `{extracted.get('nmos_source') or 'not found'}`",
        f"- `{SOURCE_NODE}` appears in extracted netlist: {extracted.get('source_node_found')}",
        "",
        "## 4. Layer Counts Parsed From GDS",
        "",
        "| purpose | count |",
        "| --- | ---: |",
    ]
    all_counts = layer_counts(elements)
    for name, count in all_counts.items():
        lines.append(f"| {name} | {count} |")

    lines.extend(
        [
            "",
            "## 5. VGND Rail Check",
            "",
            f"- VGND ioPin box: `{vgnd_box.text()}`",
            f"- VGND box overlaps `met5.drawing` or `met5.pin`: {'yes' if vgnd_hits else 'no'}",
            f"- VGND rail component roots: `{', '.join(str(root) for root in vgnd_roots) if vgnd_roots else 'none'}`",
            "",
        ]
    )
    lines.extend(element_table(vgnd_hits, "### VGND Overlapping Elements"))

    for root, members in vgnd_members_by_root.items():
        lines.extend(
            [
                f"### VGND Component `{root}`",
                "",
                f"- Element count: {len(members)}",
                f"- Layer contents: {format_counts(layer_counts(members))}",
                "",
            ]
        )

    lines.extend(
        [
            "## 6. Source Node Neighborhood",
            "",
            f"- Source candidate elements selected near `{SOURCE_NODE_COORD}`: {len(source_elems)}",
            f"- Source component root: `{source_root if source_root is not None else 'none'}`",
            f"- Source component element count: {len(source_members)}",
            f"- Source component layer contents: {format_counts(source_layers)}",
            f"- Source component overlaps pin-purpose shapes for: {pin_overlap_text(source_pin_overlaps)}",
            f"- Source and VGND are in the same simplified component: {'yes' if same_component else 'no'}",
            "",
        ]
    )
    lines.extend(element_table(source_elems, "### Source Candidate Diffusion Elements"))

    lines.extend(
        [
            "### Source Candidate Component Summary",
            "",
            "| candidate bbox | component root | same as VGND | component layers | pin-purpose overlaps |",
            "| --- | ---: | --- | --- | --- |",
        ]
    )
    for candidate in source_elems:
        root = uf.find(candidate.idx)
        members = component_members(elements, uf, root)
        overlaps = component_pin_overlaps(members, pins)
        lines.append(
            f"| {candidate.bbox.text()} | {root} | {'yes' if root in vgnd_roots else 'no'} | "
            f"{format_counts(layer_counts(members))} | {pin_overlap_text(overlaps)} |"
        )
    lines.append("")

    lines.extend(element_table(source_near, "### Nearest Stack Elements Around a_n15_90#"))

    lines.extend(
        [
            "## 7. Source-to-VGND Stack Check",
            "",
            "| transition | status |",
            "| --- | --- |",
        ]
    )
    for left, right, status in rows:
        lines.append(f"| `{left} -> {right}` | {status} |")

    lines.extend(
        [
            "",
            "## 8. Diagnosis",
            "",
            f"- Most likely break: `{likely_break}`",
            f"- Current classification: **{issue_type}**.",
            "",
            "This is not primarily a pin annotation problem: the pinned-shapes GDS has labels and pin-purpose geometry, and Magic now writes the top-level port list. The remaining issue is that the source-side geometry component selected near `a_n15_90#` is not merged with the `VGND` rail component in the simplified GDS connectivity graph.",
            "",
            "## 9. Next Minimum Step",
            "",
            next_step,
            "",
            "Keep `normalize_lvs_netlists_inverter.py` for now. It is still required because raw Magic extraction keeps `a_n15_90#`.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose simplified Sky130 GDS connectivity.")
    parser.add_argument("--gds", type=Path, default=DEFAULT_GDS)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--iopin", type=Path, default=DEFAULT_IOPIN)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    gds_path = args.gds.resolve()
    extracted_path = resolve_extracted_path(args.extracted.resolve())
    iopin_path = args.iopin.resolve()
    report_path = args.report.resolve()

    try:
        if not gds_path.is_file():
            raise FileNotFoundError(gds_path)
        if not iopin_path.is_file():
            raise FileNotFoundError(iopin_path)
        elements = parse_gds_boundaries(gds_path)
        pins = read_iopin(iopin_path)
        if "VGND" not in pins:
            raise RuntimeError("VGND was not found in ioPin file")
        _vgnd_layer, vgnd_box = pins["VGND"]
        extracted = parse_extracted_source_node(extracted_path)
        uf = build_connectivity(elements)
        vgnd_roots, vgnd_hits = find_vgnd_roots(elements, uf, vgnd_box)
        source_elems = source_candidates(elements, SOURCE_NODE_COORD)
        report = generate_report(
            gds_path,
            extracted_path,
            iopin_path,
            elements,
            uf,
            extracted,
            vgnd_box,
            pins,
            vgnd_roots,
            vgnd_hits,
            source_elems,
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")

        source_root = uf.find(source_elems[0].idx) if source_elems else None
        same_component = source_root in vgnd_roots if source_root is not None else False
        source_layers = layer_counts(component_members(elements, uf, source_root))
        rows = edge_status(component_members(elements, uf, source_root))
        source_has_full_vertical_stack = all(status == "present in source component" for _left, _right, status in rows)
        likely_break = "none" if same_component else first_break(rows)
        if not same_component and source_has_full_vertical_stack:
            likely_break = "not a vertical layer-stack break; source candidate is a separate routed component from VGND"

        print(f"GDS: {gds_path}")
        print(f"Extracted netlist: {extracted_path}")
        print(f"Parsed elements: {len(elements)}")
        print(f"VGND rail overlaps met5/pin elements: {'yes' if vgnd_hits else 'no'}")
        print(f"Source component layers: {format_counts(source_layers)}")
        print(f"Source and VGND same component: {'yes' if same_component else 'no'}")
        print(f"Likely break: {likely_break}")
        print(f"Report written: {report_path}")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
