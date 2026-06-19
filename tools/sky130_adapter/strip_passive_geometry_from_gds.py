#!/usr/bin/env python3
"""Strip placed passive-instance geometry from a flat GDS for short diagnostics."""

from __future__ import annotations

import argparse
import json
import re
import struct
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ELEMENT_STARTS = {
    0x08: "BOUNDARY",
    0x09: "PATH",
    0x0A: "SREF",
    0x0B: "AREF",
    0x0C: "TEXT",
}
LAYER_RECORD = 0x0D
DATATYPE_RECORDS = {0x0E: "DATATYPE", 0x16: "TEXTTYPE", 0x2A: "NODETYPE", 0x2E: "BOXTYPE"}
XY_RECORD = 0x10
SNAME_RECORD = 0x12
STRING_RECORD = 0x19
ENDEL_RECORD = 0x11


@dataclass(frozen=True)
class BBox:
    x1: int
    y1: int
    x2: int
    y2: int

    def expand(self, margin: int) -> "BBox":
        return BBox(self.x1 - margin, self.y1 - margin, self.x2 + margin, self.y2 + margin)

    def translate(self, dx: int, dy: int) -> "BBox":
        return BBox(self.x1 + dx, self.y1 + dy, self.x2 + dx, self.y2 + dy)

    def contains(self, other: "BBox") -> bool:
        return self.x1 <= other.x1 and self.y1 <= other.y1 and self.x2 >= other.x2 and self.y2 >= other.y2

    def intersects(self, other: "BBox") -> bool:
        return not (self.x2 < other.x1 or other.x2 < self.x1 or self.y2 < other.y1 or other.y2 < self.y1)

    def as_list(self) -> list[int]:
        return [self.x1, self.y1, self.x2, self.y2]


@dataclass
class Element:
    raw: bytes = b""
    element_type: str = ""
    layer: int | None = None
    datatype: int | None = None
    texttype: int | None = None
    sname: str | None = None
    string: str | None = None
    xy: list[tuple[int, int]] = field(default_factory=list)

    @property
    def purpose_datatype(self) -> int | None:
        return self.texttype if self.element_type == "TEXT" else self.datatype

    @property
    def bbox(self) -> BBox | None:
        if not self.xy:
            return None
        xs = [point[0] for point in self.xy]
        ys = [point[1] for point in self.xy]
        return BBox(min(xs), min(ys), max(xs), max(ys))

    @property
    def layer_key(self) -> str:
        return f"{self.layer}/{self.purpose_datatype}/{self.element_type}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strip passive placement regions from a flat GDS.")
    parser.add_argument("--input-gds", type=Path, required=True)
    parser.add_argument("--output-gds", type=Path, required=True)
    parser.add_argument("--placement-log", type=Path)
    parser.add_argument("--case-dir", type=Path)
    parser.add_argument("--top-cell", required=True)
    parser.add_argument("--passive-instance", action="append", default=[])
    parser.add_argument(
        "--strip-box-json",
        type=Path,
        help=(
            "Optional JSON strip boxes. Accepts a top-level list, `strip_boxes`, "
            "or `boxes`; each item must contain `strip_bbox` or `bbox`."
        ),
    )
    parser.add_argument("--margin", type=int, default=0)
    parser.add_argument("--max-samples", type=int, default=80)
    parser.add_argument(
        "--selected-element-json",
        type=Path,
        help=(
            "Optional JSON selector. When provided, only strip matching elements from "
            "`elements`, `stripped_samples`, or a top-level list. Each item must include "
            "`layer_key` and `bbox`."
        ),
    )
    parser.add_argument(
        "--strip-layer-key",
        action="append",
        default=[],
        help=(
            "Strip every element with this exact layer/type key, for example "
            "`83/44/BOUNDARY`. May be passed multiple times."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("contains", "intersects", "crossing", "clip-crossing", "crop-crossing"),
        default="contains",
        help=(
            "Delete or clip an element when its bbox is contained by or intersects "
            "a passive strip box."
        ),
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    return parser.parse_args()


def decode_ascii(payload: bytes) -> str:
    return payload.rstrip(b"\0").decode("ascii", errors="replace")


def read_int2(payload: bytes) -> int | None:
    if len(payload) < 2:
        return None
    return struct.unpack(">h", payload[:2])[0]


def decode_xy(payload: bytes) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for offset in range(0, len(payload), 8):
        if offset + 8 <= len(payload):
            points.append(struct.unpack(">ii", payload[offset : offset + 8]))
    return points


def parse_element(raw: bytes, element_type: str) -> Element:
    element = Element(raw=raw, element_type=element_type)
    offset = 0
    while offset + 4 <= len(raw):
        record_len, record_type, _data_type = struct.unpack(">HBB", raw[offset : offset + 4])
        payload = raw[offset + 4 : offset + record_len]
        offset += record_len
        if record_type == LAYER_RECORD:
            element.layer = read_int2(payload)
        elif record_type == 0x0E:
            element.datatype = read_int2(payload)
        elif record_type == 0x16:
            element.texttype = read_int2(payload)
        elif record_type == SNAME_RECORD:
            element.sname = decode_ascii(payload)
        elif record_type == STRING_RECORD:
            element.string = decode_ascii(payload)
        elif record_type == XY_RECORD:
            element.xy = decode_xy(payload)
    return element


def iter_gds_units(data: bytes) -> list[bytes | Element]:
    units: list[bytes | Element] = []
    offset = 0
    while offset + 4 <= len(data):
        start = offset
        record_len, record_type, _data_type = struct.unpack(">HBB", data[offset : offset + 4])
        if record_len < 4 or offset + record_len > len(data):
            raise ValueError(f"invalid GDS record at byte {offset}")
        if record_type not in ELEMENT_STARTS:
            units.append(data[offset : offset + record_len])
            offset += record_len
            continue
        element_type = ELEMENT_STARTS[record_type]
        offset += record_len
        while offset + 4 <= len(data):
            next_len, next_type, _next_data_type = struct.unpack(">HBB", data[offset : offset + 4])
            if next_len < 4 or offset + next_len > len(data):
                raise ValueError(f"invalid GDS element record at byte {offset}")
            offset += next_len
            if next_type == ENDEL_RECORD:
                break
        raw = data[start:offset]
        units.append(parse_element(raw, element_type))
    if offset != len(data):
        raise ValueError("trailing partial GDS record")
    return units


def parse_gds_elements(path: Path) -> list[Element]:
    return [unit for unit in iter_gds_units(path.read_bytes()) if isinstance(unit, Element)]


def bbox_for_gds(path: Path) -> BBox | None:
    boxes = [element.bbox for element in parse_gds_elements(path) if element.bbox is not None]
    if not boxes:
        return None
    return BBox(
        min(box.x1 for box in boxes),
        min(box.y1 for box in boxes),
        max(box.x2 for box in boxes),
        max(box.y2 for box in boxes),
    )


def parse_placements(path: Path, top_cell: str) -> dict[str, tuple[int, int]]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    placements: dict[str, tuple[int, int]] = {}
    pattern = re.compile(rf"\bnode\s+{re.escape(top_cell)}_(\S+)\s+(-?\d+)\s+(-?\d+)")
    for match in pattern.finditer(text):
        placements[match.group(1)] = (int(match.group(2)), int(match.group(3)))
    return placements


def passive_strip_boxes(
    *,
    case_dir: Path,
    top_cell: str,
    placement_log: Path,
    passive_instances: list[str],
    margin: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    placements = parse_placements(placement_log, top_cell)
    boxes: list[dict[str, Any]] = []
    missing: list[str] = []
    for instance in passive_instances:
        passive_gds = case_dir / "gds" / f"{top_cell}_{instance}.gds"
        local_box = bbox_for_gds(passive_gds) if passive_gds.is_file() else None
        placement = placements.get(instance)
        if local_box is None or placement is None:
            missing.append(instance)
            continue
        placed = local_box.translate(*placement)
        strip_box = placed.expand(margin)
        boxes.append(
            {
                "instance": instance,
                "passive_gds": str(passive_gds),
                "placement": list(placement),
                "local_bbox": local_box.as_list(),
                "placed_bbox": placed.as_list(),
                "strip_bbox": strip_box.as_list(),
            }
        )
    return boxes, missing


def box_from_item(item: dict[str, Any]) -> BBox:
    x1, y1, x2, y2 = item["strip_bbox"]
    return BBox(int(x1), int(y1), int(x2), int(y2))


def matching_strip_boxes(element: Element, strip_box_items: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    bbox = element.bbox
    if bbox is None or element.element_type not in {"BOUNDARY", "PATH", "TEXT"}:
        return []
    matches: list[dict[str, Any]] = []
    for item in strip_box_items:
        strip_box = box_from_item(item)
        if mode == "contains":
            matched = strip_box.contains(bbox)
        elif mode in {"crossing", "clip-crossing", "crop-crossing"}:
            matched = strip_box.intersects(bbox) and not strip_box.contains(bbox)
        else:
            matched = strip_box.intersects(bbox)
        if matched:
            matches.append(item)
    return matches


def should_strip(element: Element, strip_box_items: list[dict[str, Any]], mode: str) -> bool:
    return bool(matching_strip_boxes(element, strip_box_items, mode))


def rectangle_for_boundary(element: Element) -> BBox | None:
    if element.element_type != "BOUNDARY" or len(element.xy) < 4:
        return None
    bbox = element.bbox
    if bbox is None or bbox.x1 == bbox.x2 or bbox.y1 == bbox.y2:
        return None
    allowed = {
        (bbox.x1, bbox.y1),
        (bbox.x1, bbox.y2),
        (bbox.x2, bbox.y1),
        (bbox.x2, bbox.y2),
    }
    if all(point in allowed for point in element.xy):
        return bbox
    return None


def subtract_box(rects: list[BBox], cutter: BBox) -> list[BBox]:
    output: list[BBox] = []
    for rect in rects:
        if not rect.intersects(cutter):
            output.append(rect)
            continue
        ix1 = max(rect.x1, cutter.x1)
        iy1 = max(rect.y1, cutter.y1)
        ix2 = min(rect.x2, cutter.x2)
        iy2 = min(rect.y2, cutter.y2)
        if ix1 >= ix2 or iy1 >= iy2:
            output.append(rect)
            continue
        pieces = [
            BBox(rect.x1, rect.y1, ix1, rect.y2),
            BBox(ix2, rect.y1, rect.x2, rect.y2),
            BBox(ix1, rect.y1, ix2, iy1),
            BBox(ix1, iy2, ix2, rect.y2),
        ]
        output.extend(piece for piece in pieces if piece.x1 < piece.x2 and piece.y1 < piece.y2)
    return output


def clip_rectangle(rect: BBox, cutters: list[BBox]) -> list[BBox]:
    rects = [rect]
    for cutter in cutters:
        rects = subtract_box(rects, cutter)
        if not rects:
            break
    return rects


def intersect_box(first: BBox, second: BBox) -> BBox | None:
    x1 = max(first.x1, second.x1)
    y1 = max(first.y1, second.y1)
    x2 = min(first.x2, second.x2)
    y2 = min(first.y2, second.y2)
    if x1 >= x2 or y1 >= y2:
        return None
    return BBox(x1, y1, x2, y2)


def crop_rectangle(rect: BBox, cutters: list[BBox]) -> list[BBox]:
    fragments: list[BBox] = []
    seen: set[tuple[int, int, int, int]] = set()
    for cutter in cutters:
        fragment = intersect_box(rect, cutter)
        if fragment is None:
            continue
        key = (fragment.x1, fragment.y1, fragment.x2, fragment.y2)
        if key in seen:
            continue
        fragments.append(fragment)
        seen.add(key)
    return fragments


def encode_xy(points: list[tuple[int, int]]) -> bytes:
    values: list[int] = []
    for x, y in points:
        values.extend([x, y])
    return struct.pack(f">{len(values)}i", *values)


def rectangle_points(rect: BBox) -> list[tuple[int, int]]:
    return [
        (rect.x1, rect.y1),
        (rect.x1, rect.y2),
        (rect.x2, rect.y2),
        (rect.x2, rect.y1),
        (rect.x1, rect.y1),
    ]


def raw_with_xy(raw: bytes, points: list[tuple[int, int]]) -> bytes:
    payload = encode_xy(points)
    record = struct.pack(">HBB", len(payload) + 4, XY_RECORD, 0x03) + payload
    output = bytearray()
    offset = 0
    replaced = False
    while offset + 4 <= len(raw):
        record_len, record_type, data_type = struct.unpack(">HBB", raw[offset : offset + 4])
        if record_len < 4 or offset + record_len > len(raw):
            raise ValueError("invalid GDS element record while replacing XY")
        if record_type == XY_RECORD and not replaced:
            output.extend(record)
            replaced = True
        else:
            output.extend(raw[offset : offset + record_len])
        offset += record_len
    if not replaced:
        raise ValueError("boundary lacks XY record")
    return bytes(output)


def sample_for_element(element: Element, matches: list[dict[str, Any]]) -> dict[str, Any]:
    bbox = element.bbox
    return {
        "element_type": element.element_type,
        "layer_key": element.layer_key,
        "bbox": bbox.as_list() if bbox else None,
        "text": element.string,
        "matching_instances": [item.get("instance") for item in matches],
        "matching_strip_bboxes": [item.get("strip_bbox") for item in matches],
    }


def element_selector_key(item: dict[str, Any]) -> tuple[str, tuple[int, int, int, int]] | None:
    layer_key = item.get("layer_key")
    bbox = item.get("bbox")
    if not isinstance(layer_key, str) or not isinstance(bbox, list) or len(bbox) != 4:
        return None
    return layer_key, tuple(int(value) for value in bbox)  # type: ignore[return-value]


def load_selected_elements(path: Path | None) -> set[tuple[str, tuple[int, int, int, int]]] | None:
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("elements") or data.get("stripped_samples") or []
    else:
        items = []
    selectors: set[tuple[str, tuple[int, int, int, int]]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        key = element_selector_key(item)
        if key is not None:
            selectors.add(key)
    return selectors


def load_strip_box_items(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("strip_boxes") or data.get("boxes") or []
    else:
        items = []
    boxes: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        bbox = item.get("strip_bbox") or item.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        boxes.append(
            {
                "instance": str(item.get("instance") or item.get("name") or f"json_box_{idx}"),
                "placement": item.get("placement"),
                "local_bbox": item.get("local_bbox"),
                "strip_bbox": [int(value) for value in bbox],
            }
        )
    return boxes


def strip_gds(
    *,
    input_gds: Path,
    output_gds: Path,
    strip_box_items: list[dict[str, Any]],
    mode: str,
    selected_elements: set[tuple[str, tuple[int, int, int, int]]] | None = None,
    strip_layer_keys: set[str] | None = None,
    max_samples: int = 80,
) -> dict[str, Any]:
    units = iter_gds_units(input_gds.read_bytes())
    output = bytearray()
    stripped_count = 0
    kept_count = 0
    stripped_by_layer: Counter[str] = Counter()
    kept_by_layer: Counter[str] = Counter()
    stripped_samples: list[dict[str, Any]] = []
    crossing_samples: list[dict[str, Any]] = []
    selected_seen: set[tuple[str, tuple[int, int, int, int]]] = set()
    clipped_count = 0
    clipped_fragment_count = 0
    clipped_by_layer: Counter[str] = Counter()
    clipped_samples: list[dict[str, Any]] = []
    cropped_count = 0
    cropped_fragment_count = 0
    cropped_by_layer: Counter[str] = Counter()
    cropped_samples: list[dict[str, Any]] = []
    for unit in units:
        if not isinstance(unit, Element):
            output.extend(unit)
            continue
        matches = matching_strip_boxes(unit, strip_box_items, mode)
        bbox = unit.bbox
        selector = (
            (unit.layer_key, tuple(bbox.as_list()))  # type: ignore[arg-type]
            if bbox is not None
            else None
        )
        if matches and selected_elements is not None:
            if selector not in selected_elements:
                matches = []
            elif selector is not None:
                selected_seen.add(selector)
        layer_key_match = bool(strip_layer_keys and unit.layer_key in strip_layer_keys)
        if layer_key_match:
            stripped_count += 1
            stripped_by_layer[unit.layer_key] += 1
            if len(stripped_samples) < max_samples:
                sample = sample_for_element(unit, [])
                sample["matching_instances"] = ["layer_key_filter"]
                sample["matching_strip_bboxes"] = []
                stripped_samples.append(sample)
            continue
        if matches:
            if mode in {"clip-crossing", "crop-crossing"}:
                rect = rectangle_for_boundary(unit)
                if rect is not None:
                    cutters = [box_from_item(item) for item in matches]
                    fragments = (
                        clip_rectangle(rect, cutters)
                        if mode == "clip-crossing"
                        else crop_rectangle(rect, cutters)
                    )
                    if fragments:
                        if mode == "clip-crossing":
                            clipped_count += 1
                            clipped_fragment_count += len(fragments)
                            clipped_by_layer[unit.layer_key] += 1
                            target_samples = clipped_samples
                        else:
                            cropped_count += 1
                            cropped_fragment_count += len(fragments)
                            cropped_by_layer[unit.layer_key] += 1
                            target_samples = cropped_samples
                        if len(target_samples) < max_samples:
                            sample = sample_for_element(unit, matches)
                            sample["fragments"] = [fragment.as_list() for fragment in fragments]
                            target_samples.append(sample)
                        for fragment in fragments:
                            output.extend(raw_with_xy(unit.raw, rectangle_points(fragment)))
                        continue
            stripped_count += 1
            stripped_by_layer[unit.layer_key] += 1
            if len(stripped_samples) < max_samples:
                stripped_samples.append(sample_for_element(unit, matches))
            if mode == "intersects" and not matching_strip_boxes(unit, strip_box_items, "contains"):
                if len(crossing_samples) < max_samples:
                    crossing_samples.append(sample_for_element(unit, matches))
            continue
        kept_count += 1
        kept_by_layer[unit.layer_key] += 1
        output.extend(unit.raw)
    output_gds.parent.mkdir(parents=True, exist_ok=True)
    output_gds.write_bytes(output)
    return {
        "input_gds": str(input_gds),
        "output_gds": str(output_gds),
        "mode": mode,
        "strip_box_count": len(strip_box_items),
        "strip_layer_keys": sorted(strip_layer_keys or []),
        "stripped_element_count": stripped_count,
        "kept_element_count": kept_count,
        "stripped_by_layer": dict(sorted(stripped_by_layer.items())),
        "kept_by_layer": dict(sorted(kept_by_layer.items())),
        "stripped_samples": stripped_samples,
        "clipped_element_count": clipped_count,
        "clipped_fragment_count": clipped_fragment_count,
        "clipped_by_layer": dict(sorted(clipped_by_layer.items())),
        "clipped_samples": clipped_samples,
        "cropped_element_count": cropped_count,
        "cropped_fragment_count": cropped_fragment_count,
        "cropped_by_layer": dict(sorted(cropped_by_layer.items())),
        "cropped_samples": cropped_samples,
        "crossing_sample_count": len(crossing_samples),
        "crossing_samples": crossing_samples,
        "selected_element_count": len(selected_elements) if selected_elements is not None else None,
        "selected_element_missing_count": (
            len(selected_elements - selected_seen) if selected_elements is not None else None
        ),
        "selected_element_missing": (
            [
                {"layer_key": layer_key, "bbox": list(bbox)}
                for layer_key, bbox in sorted(selected_elements - selected_seen)
            ]
            if selected_elements is not None
            else []
        ),
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Passive Geometry Strip Diagnostic",
        "",
        "## Summary",
        "",
        f"- Input GDS: `{summary.get('input_gds')}`",
        f"- Output GDS: `{summary.get('output_gds')}`",
        f"- Mode: `{summary.get('mode')}`",
        f"- Margin: `{summary.get('margin')}`",
        f"- Strip boxes: {summary.get('strip_box_count')}",
        f"- Stripped elements: {summary.get('stripped_element_count')}",
        f"- Clipped crossing elements: {summary.get('clipped_element_count', 0)}",
        f"- Clipped fragments: {summary.get('clipped_fragment_count', 0)}",
        f"- Cropped crossing elements: {summary.get('cropped_element_count', 0)}",
        f"- Cropped fragments: {summary.get('cropped_fragment_count', 0)}",
        f"- Kept elements: {summary.get('kept_element_count')}",
        f"- Missing passive instances: `{summary.get('missing_passive_instances', [])}`",
        "",
        "## Strip Boxes",
        "",
    ]
    boxes = summary.get("strip_boxes", [])
    if boxes:
        lines.extend(["| instance | placement | local bbox | strip bbox |", "| --- | --- | --- | --- |"])
        for item in boxes:
            lines.append(
                f"| `{item['instance']}` | `{item['placement']}` | `{item['local_bbox']}` | `{item['strip_bbox']}` |"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Stripped By Layer", ""])
    stripped = summary.get("stripped_by_layer", {})
    if stripped:
        lines.extend(["| layer/type | count |", "| --- | ---: |"])
        for key, count in stripped.items():
            lines.append(f"| `{key}` | {count} |")
    else:
        lines.append("- none")
    lines.extend(["", "## Clipped By Layer", ""])
    clipped = summary.get("clipped_by_layer", {})
    if clipped:
        lines.extend(["| layer/type | count |", "| --- | ---: |"])
        for key, count in clipped.items():
            lines.append(f"| `{key}` | {count} |")
    else:
        lines.append("- none")
    lines.extend(["", "## Clipped Samples", ""])
    clipped_samples = summary.get("clipped_samples", [])
    if clipped_samples:
        lines.extend(["| layer/type | original bbox | fragments | matching instances |", "| --- | --- | --- | --- |"])
        for item in clipped_samples:
            lines.append(
                f"| `{item.get('layer_key')}` | `{item.get('bbox')}` | `{item.get('fragments')}` | `{item.get('matching_instances')}` |"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Cropped By Layer", ""])
    cropped = summary.get("cropped_by_layer", {})
    if cropped:
        lines.extend(["| layer/type | count |", "| --- | ---: |"])
        for key, count in cropped.items():
            lines.append(f"| `{key}` | {count} |")
    else:
        lines.append("- none")
    lines.extend(["", "## Cropped Samples", ""])
    cropped_samples = summary.get("cropped_samples", [])
    if cropped_samples:
        lines.extend(["| layer/type | original bbox | fragments | matching instances |", "| --- | --- | --- | --- |"])
        for item in cropped_samples:
            lines.append(
                f"| `{item.get('layer_key')}` | `{item.get('bbox')}` | `{item.get('fragments')}` | `{item.get('matching_instances')}` |"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Crossing Samples", ""])
    crossings = summary.get("crossing_samples", [])
    if crossings:
        lines.extend(["| layer/type | bbox | matching instances |", "| --- | --- | --- |"])
        for item in crossings:
            lines.append(
                f"| `{item.get('layer_key')}` | `{item.get('bbox')}` | `{item.get('matching_instances')}` |"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Stripped Samples", ""])
    samples = summary.get("stripped_samples", [])
    if samples:
        lines.extend(["| layer/type | bbox | matching instances |", "| --- | --- | --- |"])
        for item in samples:
            lines.append(
                f"| `{item.get('layer_key')}` | `{item.get('bbox')}` | `{item.get('matching_instances')}` |"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This diagnostic removes flat GDS elements by passive placement region. If Magic no longer reports a supply short on the stripped GDS, the short is localized to geometry inside those passive placement regions. This is not passive-aware LVS signoff; it is a localization experiment.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    instances = list(args.passive_instance)
    json_strip_boxes = load_strip_box_items(args.strip_box_json)
    missing: list[str] = []
    strip_boxes = list(json_strip_boxes)
    if instances:
        if args.case_dir is None or args.placement_log is None:
            raise SystemExit("--case-dir and --placement-log are required with --passive-instance")
        passive_boxes, missing = passive_strip_boxes(
            case_dir=args.case_dir.resolve(),
            top_cell=args.top_cell,
            placement_log=args.placement_log.resolve(),
            passive_instances=instances,
            margin=args.margin,
        )
        strip_boxes.extend(passive_boxes)
    strip_layer_keys = set(args.strip_layer_key or [])
    if not strip_boxes and not strip_layer_keys:
        raise SystemExit("--passive-instance, --strip-box-json, or --strip-layer-key is required")
    summary = strip_gds(
        input_gds=args.input_gds.resolve(),
        output_gds=args.output_gds.resolve(),
        strip_box_items=strip_boxes,
        mode=args.mode,
        selected_elements=load_selected_elements(args.selected_element_json),
        strip_layer_keys=strip_layer_keys,
        max_samples=args.max_samples,
    )
    summary.update(
        {
            "schema_version": "passive_geometry_strip.v1",
            "top_cell": args.top_cell,
            "passive_instances": instances,
            "strip_box_json": str(args.strip_box_json.resolve()) if args.strip_box_json else None,
            "missing_passive_instances": missing,
            "margin": args.margin,
            "strip_boxes": strip_boxes,
        }
    )
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(summary), encoding="utf-8")
    print(f"output_gds={summary['output_gds']}")
    print(f"stripped_element_count={summary['stripped_element_count']}")
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
