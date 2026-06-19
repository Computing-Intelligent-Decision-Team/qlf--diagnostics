#!/usr/bin/env python3
"""Replace a flattened MAGICAL MOM cap region with a Sky130 native cap cell.

The tool is intentionally conservative: it removes only geometry inside the
source capacitor bbox, preserves the original route pin boxes/labels, inserts
the Magic-generated native capacitor geometry, and retargets C1/C2 labels to
the source net names.  Downstream Magic extraction and LVS remain the authority
for whether the replacement is signoff-ready.
"""

from __future__ import annotations

import argparse
import json
import struct
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from strip_passive_geometry_from_gds import BBox, Element, iter_gds_units
except ModuleNotFoundError:
    from .strip_passive_geometry_from_gds import BBox, Element, iter_gds_units


ROUTE_LAYER_TO_GDS = {
    1: {"name": "li1", "drawing": (67, 20), "pin": (67, 16), "label": (67, 5)},
    2: {"name": "met1", "drawing": (68, 20), "pin": (68, 16), "label": (68, 5)},
    3: {"name": "met2", "drawing": (69, 20), "pin": (69, 16), "label": (69, 5)},
    4: {"name": "met3", "drawing": (70, 20), "pin": (70, 16), "label": (70, 5)},
    5: {"name": "met4", "drawing": (71, 20), "pin": (71, 16), "label": (71, 5)},
    6: {"name": "met5", "drawing": (72, 20), "pin": (72, 16), "label": (72, 5)},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replace a flat cfmom_2t GDS region with a native Sky130 cap.")
    parser.add_argument("--input-gds", type=Path, required=True)
    parser.add_argument("--replacement-gds", type=Path, required=True)
    parser.add_argument("--output-gds", type=Path, required=True)
    parser.add_argument("--identity-summary", type=Path, required=True)
    parser.add_argument("--source-gds-structure-json", type=Path, required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--source-instance", default="xc0")
    parser.add_argument(
        "--label-map",
        action="append",
        default=[],
        help="Replacement label rewrite, e.g. C1=outn. Defaults from source terminal order.",
    )
    parser.add_argument(
        "--bridge-mode",
        choices=("label_only", "m1_m4_stacks", "mim_m3_split_access", "m4_outside_stacks"),
        default="label_only",
        help="Optional physical bridge mode between preserved M1 route pins and replacement MIM cap terminals.",
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    return parser.parse_args()


def gds_record(record_type: int, data_type: int, payload: bytes = b"") -> bytes:
    length = 4 + len(payload)
    if length % 2:
        raise ValueError(f"GDS record length must be even, got {length}")
    return struct.pack(">HBB", length, record_type, data_type) + payload


def _decode_ascii(payload: bytes) -> str:
    return payload.rstrip(b"\0").decode("ascii", errors="replace")


def _string_payload(value: str) -> bytes:
    payload = value.encode("ascii")
    if len(payload) % 2:
        payload += b"\0"
    return payload


def _int2_record(record_type: int, value: int) -> bytes:
    return gds_record(record_type, 0x02, struct.pack(">h", value))


def _xy_record(points: list[tuple[int, int]]) -> bytes:
    flat: list[int] = []
    for x, y in points:
        flat.extend([x, y])
    return gds_record(0x10, 0x03, struct.pack(f">{len(flat)}i", *flat))


def _boundary(layer: int, datatype: int, box: BBox) -> bytes:
    points = [
        (box.x1, box.y1),
        (box.x1, box.y2),
        (box.x2, box.y2),
        (box.x2, box.y1),
        (box.x1, box.y1),
    ]
    return b"".join(
        [
            gds_record(0x08, 0x00),
            _int2_record(0x0D, layer),
            _int2_record(0x0E, datatype),
            _xy_record(points),
            gds_record(0x11, 0x00),
        ]
    )


def _text(layer: int, texttype: int, point: tuple[int, int], label: str) -> bytes:
    return b"".join(
        [
            gds_record(0x0C, 0x00),
            _int2_record(0x0D, layer),
            _int2_record(0x16, texttype),
            _xy_record([point]),
            gds_record(0x19, 0x06, _string_payload(label)),
            gds_record(0x11, 0x00),
        ]
    )


def _record_type(unit: bytes) -> int | None:
    if len(unit) < 4:
        return None
    record_len, record_type, _data_type = struct.unpack(">HBB", unit[:4])
    if record_len != len(unit):
        return None
    return record_type


def _record_string(unit: bytes) -> str:
    if len(unit) < 4:
        return ""
    record_len, _record_type_value, _data_type = struct.unpack(">HBB", unit[:4])
    return _decode_ascii(unit[4:record_len])


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bbox_from_list(values: list[Any]) -> BBox:
    if len(values) != 4:
        raise ValueError(f"bbox must contain four values, got {values}")
    x1, y1, x2, y2 = (int(value) for value in values)
    return BBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def find_identity_instance(identity: dict[str, Any], source_instance: str) -> dict[str, Any]:
    for item in identity.get("instances", []):
        if isinstance(item, dict) and item.get("source_instance") == source_instance:
            return item
    raise ValueError(f"source instance not found in identity summary: {source_instance}")


def source_cell_bbox(structure: dict[str, Any]) -> BBox:
    cells = structure.get("top_gds", {}).get("cells", [])
    if not cells or not isinstance(cells[0], dict) or not cells[0].get("bbox"):
        raise ValueError("source GDS structure summary does not contain a top cell bbox")
    return bbox_from_list(cells[0]["bbox"])


def instance_strip_bbox(instance: dict[str, Any], structure: dict[str, Any]) -> BBox:
    origin = instance.get("placement_origin")
    if not isinstance(origin, list) or len(origin) != 2:
        raise ValueError("identity instance lacks placement_origin")
    return source_cell_bbox(structure).translate(int(origin[0]), int(origin[1]))


def _terminal_route_layer(terminal: dict[str, Any]) -> int | None:
    matches = terminal.get("matched_routes", [])
    if isinstance(matches, list) and matches:
        first = matches[0]
        if isinstance(first, dict) and first.get("layer") is not None:
            return int(first["layer"])
    label_layer = str(terminal.get("suggested_magic_label_layer") or "").lower()
    for route_layer, spec in ROUTE_LAYER_TO_GDS.items():
        if spec["name"] == label_layer:
            return route_layer
    return None


def terminal_specs(instance: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for terminal in instance.get("terminals", []):
        if not isinstance(terminal, dict) or not terminal.get("global_box"):
            continue
        route_layer = _terminal_route_layer(terminal)
        if route_layer not in ROUTE_LAYER_TO_GDS:
            continue
        layer = ROUTE_LAYER_TO_GDS[route_layer]
        specs.append(
            {
                "terminal": str(terminal.get("terminal")),
                "global_box": bbox_from_list(terminal["global_box"]),
                "route_layer": route_layer,
                "drawing": tuple(layer["drawing"]),
                "pin": tuple(layer["pin"]),
                "label": tuple(layer["label"]),
            }
        )
    return specs


def default_label_map(specs: list[dict[str, Any]]) -> dict[str, str]:
    labels = ["C1", "C2"]
    return {
        label: spec["terminal"]
        for label, spec in zip(labels, specs)
        if spec.get("terminal")
    }


def parse_label_map(items: list[str], fallback: dict[str, str]) -> dict[str, str]:
    mapping = dict(fallback)
    for item in items:
        if "=" not in item:
            raise ValueError(f"invalid --label-map value: {item}")
        old, new = item.split("=", 1)
        mapping[old.strip()] = new.strip()
    return {old: new for old, new in mapping.items() if old and new}


def _point_in_box(point: tuple[int, int], box: BBox) -> bool:
    x, y = point
    return box.x1 <= x <= box.x2 and box.y1 <= y <= box.y2


def _matches_layer_pair(element: Element, layer_pair: tuple[int, int]) -> bool:
    return element.layer == layer_pair[0] and element.purpose_datatype == layer_pair[1]


def should_preserve_terminal_element(element: Element, specs: list[dict[str, Any]]) -> bool:
    bbox = element.bbox
    if bbox is None:
        return False
    for spec in specs:
        terminal_box: BBox = spec["global_box"]
        if element.element_type == "TEXT":
            if (
                element.xy
                and _point_in_box(element.xy[0], terminal_box)
                and _matches_layer_pair(element, spec["label"])
            ):
                return True
            continue
        if not terminal_box.contains(bbox):
            continue
        if _matches_layer_pair(element, spec["drawing"]) or _matches_layer_pair(element, spec["pin"]):
            return True
    return False


def should_remove_source_cap_element(element: Element, strip_box: BBox, specs: list[dict[str, Any]]) -> bool:
    bbox = element.bbox
    if bbox is None or element.element_type not in {"BOUNDARY", "PATH", "TEXT"}:
        return False
    if should_preserve_terminal_element(element, specs):
        return False
    return strip_box.contains(bbox)


def _rewrite_xy_payload(payload: bytes, dx: int, dy: int) -> bytes:
    output = bytearray()
    for offset in range(0, len(payload), 8):
        if offset + 8 > len(payload):
            output.extend(payload[offset:])
            break
        x, y = struct.unpack(">ii", payload[offset : offset + 8])
        output.extend(struct.pack(">ii", x + dx, y + dy))
    return bytes(output)


def transform_element_raw(raw: bytes, *, dx: int, dy: int, label_map: dict[str, str]) -> bytes:
    output = bytearray()
    offset = 0
    while offset + 4 <= len(raw):
        record_len, record_type, data_type = struct.unpack(">HBB", raw[offset : offset + 4])
        if record_len < 4 or offset + record_len > len(raw):
            raise ValueError("invalid GDS element record while transforming replacement")
        payload = raw[offset + 4 : offset + record_len]
        if record_type == 0x10:
            output.extend(gds_record(record_type, data_type, _rewrite_xy_payload(payload, dx, dy)))
        elif record_type == 0x19:
            text = _decode_ascii(payload)
            output.extend(gds_record(record_type, data_type, _string_payload(label_map.get(text, text))))
        else:
            output.extend(raw[offset : offset + record_len])
        offset += record_len
    return bytes(output)


def replacement_label_points(
    elements: list[Element],
    *,
    dx: int,
    dy: int,
    label_map: dict[str, str],
) -> dict[str, tuple[int, int]]:
    points: dict[str, tuple[int, int]] = {}
    for element in elements:
        if element.element_type != "TEXT" or not element.string or not element.xy:
            continue
        terminal = label_map.get(element.string)
        if not terminal:
            continue
        x, y = element.xy[0]
        points[terminal] = (x + dx, y + dy)
    return points


def _box_center(box: BBox) -> tuple[int, int]:
    return int(round((box.x1 + box.x2) / 2.0)), int(round((box.y1 + box.y2) / 2.0))


def _centered_box(x: int, y: int, half_width: int, half_height: int | None = None) -> BBox:
    hy = half_width if half_height is None else half_height
    return BBox(x - half_width, y - hy, x + half_width, y + hy)


def _vertical_route_box(x: int, terminal_box: BBox, target_y: int, half_width: int) -> BBox:
    if target_y >= terminal_box.y2:
        y1, y2 = terminal_box.y2, target_y
    elif target_y <= terminal_box.y1:
        y1, y2 = target_y, terminal_box.y1
    else:
        y1, y2 = target_y - half_width, target_y + half_width
    if y1 == y2:
        y1 -= half_width
        y2 += half_width
    return BBox(x - half_width, min(y1, y2), x + half_width, max(y1, y2))


def bridge_stack_elements(
    *,
    specs: list[dict[str, Any]],
    label_points: dict[str, tuple[int, int]],
    route_half_width: int = 110,
    via_half_width: int = 100,
    landing_half_width: int = 220,
) -> tuple[list[bytes], list[dict[str, Any]], Counter[str]]:
    elements: list[bytes] = []
    summaries: list[dict[str, Any]] = []
    by_layer: Counter[str] = Counter()
    metal_layers = [(68, 20), (69, 20), (70, 20), (71, 20)]
    via_layers = [(68, 44), (69, 44), (70, 44)]
    for spec in specs:
        terminal = str(spec["terminal"])
        point = label_points.get(terminal)
        if point is None:
            continue
        if int(spec["route_layer"]) != 2:
            continue
        x, y = point
        terminal_box: BBox = spec["global_box"]
        route_box = _vertical_route_box(x, terminal_box, y, route_half_width)
        items: list[tuple[str, int, int, BBox]] = [("route", 68, 20, route_box)]
        for layer, datatype in metal_layers:
            items.append(("landing", layer, datatype, _centered_box(x, y, landing_half_width)))
        for layer, datatype in via_layers:
            items.append(("via", layer, datatype, _centered_box(x, y, via_half_width)))
        for _kind, layer, datatype, box in items:
            elements.append(_boundary(layer, datatype, box))
            by_layer[f"{layer}/{datatype}/BOUNDARY"] += 1
        elements.append(_text(68, 5, _box_center(route_box), terminal))
        by_layer["68/5/TEXT"] += 1
        summaries.append(
            {
                "terminal": terminal,
                "cap_terminal_point": [x, y],
                "source_terminal_box": terminal_box.as_list(),
                "route_box": route_box.as_list(),
                "route_layer": "met1",
                "stack_layers": {
                    "metal": [list(pair) for pair in metal_layers],
                    "via": [list(pair) for pair in via_layers],
                },
            }
        )
    return elements, summaries, by_layer


def _m1_connection_to_point(terminal_box: BBox, x: int, y: int, half_width: int) -> list[BBox]:
    boxes: list[BBox] = []
    _cx, terminal_y = _box_center(terminal_box)
    if terminal_box.x1 <= x <= terminal_box.x2:
        boxes.append(_vertical_route_box(x, terminal_box, y, half_width))
    else:
        edge_x = terminal_box.x2 if x > terminal_box.x2 else terminal_box.x1
        boxes.append(BBox(min(edge_x, x), terminal_y - half_width, max(edge_x, x), terminal_y + half_width))
        boxes.append(BBox(x - half_width, min(terminal_y, y), x + half_width, max(terminal_y, y)))
    return [box for box in boxes if box.x1 < box.x2 and box.y1 < box.y2]


def bridge_mim_m3_split_access_elements(
    *,
    specs: list[dict[str, Any]],
    label_points: dict[str, tuple[int, int]],
    replacement_global_bbox: BBox,
    route_half_width: int = 110,
    via_half_width: int = 100,
    landing_half_width: int = 220,
    side_clearance: int = 300,
) -> tuple[list[bytes], list[dict[str, Any]], Counter[str]]:
    """Bridge a sky130_fd_pr__cap_mim_m3_* replacement without shorting plates.

    The Magic gencell exposes one terminal through the M3 bottom plate and the
    other through a separate M4 plate.  The first source terminal is connected
    to the M3 plate with an M1-M3 stack.  The second source terminal is routed
    to a stack outside the M3 plate and then connected to the M4 plate.
    """
    elements: list[bytes] = []
    summaries: list[dict[str, Any]] = []
    by_layer: Counter[str] = Counter()
    ordered_specs = [spec for spec in specs if str(spec.get("terminal")) in label_points]
    if len(ordered_specs) < 2:
        return elements, summaries, by_layer

    def add_boundary(kind: str, layer: int, datatype: int, box: BBox) -> None:
        elements.append(_boundary(layer, datatype, box))
        by_layer[f"{layer}/{datatype}/BOUNDARY"] += 1
        current["elements"].append({"kind": kind, "layer": layer, "datatype": datatype, "box": box.as_list()})

    # First terminal: access the native MIM bottom plate through M3.
    spec0 = ordered_specs[0]
    term0 = str(spec0["terminal"])
    x0, y0 = label_points[term0]
    current: dict[str, Any] = {"terminal": term0, "access": "m1_m3_bottom_plate", "elements": []}
    for box in _m1_connection_to_point(spec0["global_box"], x0, y0, route_half_width):
        add_boundary("m1_route", 68, 20, box)
    for layer, datatype in [(68, 20), (69, 20), (70, 20)]:
        add_boundary("landing", layer, datatype, _centered_box(x0, y0, landing_half_width))
    for layer, datatype in [(68, 44), (69, 44)]:
        add_boundary("via", layer, datatype, _centered_box(x0, y0, via_half_width))
    elements.append(_text(68, 5, _box_center(_vertical_route_box(x0, spec0["global_box"], y0, route_half_width)), term0))
    by_layer["68/5/TEXT"] += 1
    current["cap_terminal_point"] = [x0, y0]
    current["source_terminal_box"] = spec0["global_box"].as_list()
    summaries.append(current)

    # Second terminal: access the M4 plate from outside the M3 plate.
    spec1 = ordered_specs[1]
    term1 = str(spec1["terminal"])
    plate_x, plate_y = label_points[term1]
    stack_x = replacement_global_bbox.x2 + side_clearance
    stack_y = plate_y
    current = {
        "terminal": term1,
        "access": "outside_m1_m4_stack_to_m4_plate",
        "elements": [],
        "cap_terminal_point": [plate_x, plate_y],
        "outside_stack_point": [stack_x, stack_y],
        "source_terminal_box": spec1["global_box"].as_list(),
    }
    for box in _m1_connection_to_point(spec1["global_box"], stack_x, stack_y, route_half_width):
        add_boundary("m1_route", 68, 20, box)
    for layer, datatype in [(68, 20), (69, 20), (70, 20), (71, 20)]:
        add_boundary("landing", layer, datatype, _centered_box(stack_x, stack_y, landing_half_width))
    for layer, datatype in [(68, 44), (69, 44), (70, 44)]:
        add_boundary("via", layer, datatype, _centered_box(stack_x, stack_y, via_half_width))
    add_boundary(
        "m4_plate_bridge",
        71,
        20,
        BBox(min(plate_x, stack_x), plate_y - route_half_width, max(plate_x, stack_x), plate_y + route_half_width),
    )
    elements.append(_text(68, 5, (stack_x, stack_y), term1))
    by_layer["68/5/TEXT"] += 1
    summaries.append(current)
    return elements, summaries, by_layer


def bridge_m4_outside_stack_elements(
    *,
    specs: list[dict[str, Any]],
    label_points: dict[str, tuple[int, int]],
    replacement_global_bbox: BBox,
    route_half_width: int = 110,
    via_half_width: int = 100,
    landing_half_width: int = 220,
    side_clearance: int = 300,
) -> tuple[list[bytes], list[dict[str, Any]], Counter[str]]:
    """Bridge both MIM terminals from outside the replacement bbox to M4 plates."""
    elements: list[bytes] = []
    summaries: list[dict[str, Any]] = []
    by_layer: Counter[str] = Counter()
    ordered_specs = [spec for spec in specs if str(spec.get("terminal")) in label_points]
    if len(ordered_specs) < 2:
        return elements, summaries, by_layer
    side_x = [
        replacement_global_bbox.x1 - side_clearance,
        replacement_global_bbox.x2 + side_clearance,
    ]

    def add(item_summary: dict[str, Any], kind: str, layer: int, datatype: int, box: BBox) -> None:
        elements.append(_boundary(layer, datatype, box))
        by_layer[f"{layer}/{datatype}/BOUNDARY"] += 1
        item_summary["elements"].append(
            {"kind": kind, "layer": layer, "datatype": datatype, "box": box.as_list()}
        )

    for index, spec in enumerate(ordered_specs[:2]):
        terminal = str(spec["terminal"])
        plate_x, plate_y = label_points[terminal]
        stack_x = side_x[index]
        stack_y = plate_y
        item = {
            "terminal": terminal,
            "access": "outside_m1_m4_stack_to_m4_plate",
            "cap_terminal_point": [plate_x, plate_y],
            "outside_stack_point": [stack_x, stack_y],
            "source_terminal_box": spec["global_box"].as_list(),
            "elements": [],
        }
        for box in _m1_connection_to_point(spec["global_box"], stack_x, stack_y, route_half_width):
            add(item, "m1_route", 68, 20, box)
        for layer, datatype in [(68, 20), (69, 20), (70, 20), (71, 20)]:
            add(item, "landing", layer, datatype, _centered_box(stack_x, stack_y, landing_half_width))
        for layer, datatype in [(68, 44), (69, 44), (70, 44)]:
            add(item, "via", layer, datatype, _centered_box(stack_x, stack_y, via_half_width))
        add(
            item,
            "m4_plate_bridge",
            71,
            20,
            BBox(min(plate_x, stack_x), plate_y - route_half_width, max(plate_x, stack_x), plate_y + route_half_width),
        )
        elements.append(_text(68, 5, (stack_x, stack_y), terminal))
        by_layer["68/5/TEXT"] += 1
        summaries.append(item)
    return elements, summaries, by_layer


def replacement_cell_elements(path: Path) -> list[Element]:
    elements: list[Element] = []
    current_cell = ""
    first_cell = ""
    for unit in iter_gds_units(path.read_bytes()):
        if isinstance(unit, bytes):
            record_type = _record_type(unit)
            if record_type == 0x06:
                current_cell = _record_string(unit)
                if not first_cell:
                    first_cell = current_cell
            elif record_type == 0x07:
                current_cell = ""
            continue
        if current_cell == first_cell:
            elements.append(unit)
    return elements


def bbox_for_elements(elements: list[Element]) -> BBox:
    boxes = [element.bbox for element in elements if element.bbox is not None]
    if not boxes:
        raise ValueError("replacement GDS contains no elements with XY bboxes")
    return BBox(
        min(box.x1 for box in boxes),
        min(box.y1 for box in boxes),
        max(box.x2 for box in boxes),
        max(box.y2 for box in boxes),
    )


def center_delta(source: BBox, replacement: BBox) -> tuple[int, int]:
    source_cx = int(round((source.x1 + source.x2) / 2.0))
    source_cy = int(round((source.y1 + source.y2) / 2.0))
    repl_cx = int(round((replacement.x1 + replacement.x2) / 2.0))
    repl_cy = int(round((replacement.y1 + replacement.y2) / 2.0))
    return source_cx - repl_cx, source_cy - repl_cy


def sample_element(element: Element) -> dict[str, Any]:
    bbox = element.bbox
    return {
        "element_type": element.element_type,
        "layer": element.layer,
        "purpose_datatype": element.purpose_datatype,
        "layer_key": element.layer_key,
        "bbox": bbox.as_list() if bbox else None,
        "text": element.string,
    }


def replace_native_cap(
    *,
    input_gds: Path,
    replacement_gds: Path,
    output_gds: Path,
    identity_summary: Path,
    source_gds_structure_json: Path,
    cell: str,
    source_instance: str,
    label_map_overrides: list[str],
    bridge_mode: str = "label_only",
    max_samples: int = 80,
) -> dict[str, Any]:
    identity = load_json(identity_summary)
    structure = load_json(source_gds_structure_json)
    instance = find_identity_instance(identity, source_instance)
    specs = terminal_specs(instance)
    if len(specs) < 2:
        raise ValueError(f"source instance {source_instance} lacks two routed terminal specs")
    strip_box = instance_strip_bbox(instance, structure)
    label_map = parse_label_map(label_map_overrides, default_label_map(specs))

    replacement_elements = replacement_cell_elements(replacement_gds)
    replacement_bbox = bbox_for_elements(replacement_elements)
    dx, dy = center_delta(strip_box, replacement_bbox)
    label_points = replacement_label_points(replacement_elements, dx=dx, dy=dy, label_map=label_map)
    inserted = [
        transform_element_raw(element.raw, dx=dx, dy=dy, label_map=label_map)
        for element in replacement_elements
        if element.element_type in {"BOUNDARY", "PATH", "TEXT"}
    ]
    bridge_elements: list[bytes] = []
    bridge_summaries: list[dict[str, Any]] = []
    bridge_by_layer: Counter[str] = Counter()
    replacement_global_bbox = replacement_bbox.translate(dx, dy)
    if bridge_mode == "m1_m4_stacks":
        bridge_elements, bridge_summaries, bridge_by_layer = bridge_stack_elements(
            specs=specs,
            label_points=label_points,
        )
        inserted.extend(bridge_elements)
    elif bridge_mode == "mim_m3_split_access":
        bridge_elements, bridge_summaries, bridge_by_layer = bridge_mim_m3_split_access_elements(
            specs=specs,
            label_points=label_points,
            replacement_global_bbox=replacement_global_bbox,
        )
        inserted.extend(bridge_elements)
    elif bridge_mode == "m4_outside_stacks":
        bridge_elements, bridge_summaries, bridge_by_layer = bridge_m4_outside_stack_elements(
            specs=specs,
            label_points=label_points,
            replacement_global_bbox=replacement_global_bbox,
        )
        inserted.extend(bridge_elements)

    output = bytearray()
    current_cell = ""
    target_seen = False
    inserted_done = False
    removed_count = 0
    preserved_count = 0
    kept_count = 0
    removed_by_layer: Counter[str] = Counter()
    inserted_by_layer: Counter[str] = Counter(
        element.layer_key for element in replacement_elements if element.element_type in {"BOUNDARY", "PATH", "TEXT"}
    )
    inserted_by_layer.update(bridge_by_layer)
    removed_samples: list[dict[str, Any]] = []
    preserved_samples: list[dict[str, Any]] = []

    for unit in iter_gds_units(input_gds.read_bytes()):
        if isinstance(unit, bytes):
            record_type = _record_type(unit)
            if record_type == 0x06:
                current_cell = _record_string(unit)
                target_seen = target_seen or current_cell == cell
            elif record_type == 0x07:
                if current_cell == cell and not inserted_done:
                    output.extend(b"".join(inserted))
                    inserted_done = True
                current_cell = ""
            output.extend(unit)
            continue

        if current_cell == cell and should_remove_source_cap_element(unit, strip_box, specs):
            removed_count += 1
            removed_by_layer[unit.layer_key] += 1
            if len(removed_samples) < max_samples:
                removed_samples.append(sample_element(unit))
            continue
        if current_cell == cell and should_preserve_terminal_element(unit, specs):
            preserved_count += 1
            if len(preserved_samples) < max_samples:
                preserved_samples.append(sample_element(unit))
        kept_count += 1
        output.extend(unit.raw)

    if not target_seen:
        raise ValueError(f"target cell not found in input GDS: {cell}")
    if not inserted_done:
        raise ValueError(f"target cell ENDSTR not found in input GDS: {cell}")

    output_gds.parent.mkdir(parents=True, exist_ok=True)
    output_gds.write_bytes(output)

    return {
        "schema_version": "sky130_native_cap_flat_gds_replacement.v1",
        "status": "native_cap_replacement_merged",
        "input_gds": str(input_gds),
        "replacement_gds": str(replacement_gds),
        "output_gds": str(output_gds),
        "cell": cell,
        "source_instance": source_instance,
        "source_model": instance.get("model"),
        "replacement_translation_dbu": [dx, dy],
        "source_strip_bbox": strip_box.as_list(),
        "replacement_local_bbox": replacement_bbox.as_list(),
        "replacement_global_bbox": replacement_global_bbox.as_list(),
        "label_retarget_map": label_map,
        "replacement_label_points": {terminal: list(point) for terminal, point in sorted(label_points.items())},
        "terminal_specs": [
            {
                "terminal": spec["terminal"],
                "global_box": spec["global_box"].as_list(),
                "route_layer": spec["route_layer"],
                "drawing": list(spec["drawing"]),
                "pin": list(spec["pin"]),
                "label": list(spec["label"]),
            }
            for spec in specs
        ],
        "terminal_bridge_status": (
            "m4_outside_stacks_inserted"
            if bridge_mode == "m4_outside_stacks"
            else "mim_m3_split_access_inserted"
            if bridge_mode == "mim_m3_split_access"
            else ("m1_m4_stacks_inserted" if bridge_mode == "m1_m4_stacks" else "label_retarget_only")
        ),
        "bridge_mode": bridge_mode,
        "bridge_element_count": len(bridge_elements),
        "bridge_by_layer": dict(sorted(bridge_by_layer.items())),
        "bridge_terminals": bridge_summaries,
        "top_gds_merge_status": "merged_replacement_candidate",
        "removed_element_count": removed_count,
        "preserved_terminal_element_count": preserved_count,
        "kept_element_count": kept_count,
        "inserted_replacement_element_count": len(inserted),
        "removed_by_layer": dict(sorted(removed_by_layer.items())),
        "inserted_by_layer": dict(sorted(inserted_by_layer.items())),
        "removed_samples": removed_samples,
        "preserved_terminal_samples": preserved_samples,
        "full_native_capacitor_lvs_ready": False,
        "remaining_gates": [
            "run Magic extraction on output_gds and prove a sky130_fd_pr__cap_* device has source terminals",
            "run DRC on output_gds after replacement",
            "run native passive retarget netgen after full candidate extraction includes both native resistor and native capacitor",
        ],
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Native Capacitor Flat-GDS Replacement",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Input GDS: `{summary.get('input_gds')}`",
        f"- Replacement GDS: `{summary.get('replacement_gds')}`",
        f"- Output GDS: `{summary.get('output_gds')}`",
        f"- Source instance: `{summary.get('source_instance')}`",
        f"- Translation DBU: `{summary.get('replacement_translation_dbu')}`",
        f"- Label retarget map: `{summary.get('label_retarget_map')}`",
        f"- Removed elements: {summary.get('removed_element_count')}",
        f"- Preserved terminal elements: {summary.get('preserved_terminal_element_count')}",
        f"- Inserted replacement elements: {summary.get('inserted_replacement_element_count')}",
        f"- Terminal bridge status: `{summary.get('terminal_bridge_status')}`",
        f"- Bridge elements: {summary.get('bridge_element_count')}",
        "",
        "## Remaining Gates",
        "",
    ]
    for gate in summary.get("remaining_gates", []):
        lines.append(f"- {gate}")
    lines.extend(["", "## Removed By Layer", ""])
    removed = summary.get("removed_by_layer", {})
    if removed:
        lines.extend(["| layer/type | count |", "| --- | ---: |"])
        for key, count in removed.items():
            lines.append(f"| `{key}` | {count} |")
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    summary = replace_native_cap(
        input_gds=args.input_gds.resolve(),
        replacement_gds=args.replacement_gds.resolve(),
        output_gds=args.output_gds.resolve(),
        identity_summary=args.identity_summary.resolve(),
        source_gds_structure_json=args.source_gds_structure_json.resolve(),
        cell=args.cell,
        source_instance=args.source_instance,
        label_map_overrides=args.label_map,
        bridge_mode=args.bridge_mode,
    )
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(args.report, summary)
    print(f"native_cap_replacement_merge_status={summary['status']}")
    print(f"output_gds={summary['output_gds']}")
    print(f"removed_element_count={summary['removed_element_count']}")
    print(f"inserted_replacement_element_count={summary['inserted_replacement_element_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
