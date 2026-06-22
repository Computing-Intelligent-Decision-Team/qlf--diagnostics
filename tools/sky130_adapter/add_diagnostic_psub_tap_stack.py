#!/usr/bin/env python3
"""Inject one diagnostic p+ substrate tap stack into a Sky130 flat GDS cell.

This tool adds exactly one physical p+ substrate contact stack tied to an
existing gnda met5 rail.  It does NOT rewrite any original bytes, change
cell names, add TEXT, or modify the netlist.  The output is a new GDS file
whose only difference is 14 BOUNDARY elements inserted before the target
cell's ENDSTR record.
"""

from __future__ import annotations

import argparse
import json
import struct
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Fixed contract constants
# ---------------------------------------------------------------------------

STACK_SPECS: tuple[tuple[str, int, int, tuple[int, int, int, int]], ...] = (
    ("tap.drawing", 65, 44, (-150, -150, 150, 150)),
    ("psdm.drawing", 94, 20, (-250, -250, 250, 250)),
    ("licon1.drawing", 66, 44, (-25, -25, 25, 25)),
    ("li1.drawing", 67, 20, (-150, -150, 150, 150)),
    ("mcon.drawing", 67, 44, (-50, -50, 50, 50)),
    ("met1.drawing", 68, 20, (-150, -150, 150, 150)),
    ("via.drawing", 68, 44, (-25, -25, 25, 25)),
    ("met2.drawing", 69, 20, (-150, -150, 150, 150)),
    ("via2.drawing", 69, 44, (-25, -25, 25, 25)),
    ("met3.drawing", 70, 20, (-150, -150, 150, 150)),
    ("via3.drawing", 70, 44, (-25, -25, 25, 25)),
    ("met4.drawing", 71, 20, (-150, -150, 150, 150)),
    ("via4.drawing", 71, 44, (-50, -50, 50, 50)),
    ("met5.drawing", 72, 20, (-150, -150, 150, 150)),
)

FORBIDDEN_LAYERS: dict[tuple[int, int], str] = {
    (65, 20): "diff.drawing",
    (65, 44): "tap.existing",
    (64, 20): "nwell.drawing",
    (66, 20): "poly.drawing",
}


# ---------------------------------------------------------------------------
# Primitive geometry helpers
# ---------------------------------------------------------------------------


def parse_box(value: str) -> tuple[int, int, int, int]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("box must contain four comma-separated integers")
    x1, y1, x2, y2 = (int(part) for part in parts)
    if x1 >= x2 or y1 >= y2:
        raise ValueError("box must satisfy x1 < x2 and y1 < y2")
    return x1, y1, x2, y2


def absolute_box(
    anchor: tuple[int, int], relative: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    ax, ay = anchor
    x1, y1, x2, y2 = relative
    return (ax + x1, ay + y1, ax + x2, ay + y2)


def overlaps(
    a: tuple[int, int, int, int], b: tuple[int, int, int, int]
) -> bool:
    """True when axis-aligned boxes a and b have interior intersection.

    Edge touch (a[2] == b[0] etc.) is NOT overlap.
    """
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def contains_point(
    box: tuple[int, int, int, int], point: tuple[int, int]
) -> bool:
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


# ---------------------------------------------------------------------------
# GDS record model
# ---------------------------------------------------------------------------

GDS_RECORD_HEADER = struct.Struct(">HBB")

# Element starts
_BOUNDARY = 0x08
_PATH = 0x09
_SREF = 0x0A
_AREF = 0x0B
_TEXT = 0x0C

# Record types we care about
_BGNSTR = 0x05
_ENDSTR = 0x07
_STRNAME = 0x06
_LAYER = 0x0D
_DATATYPE = 0x0E
_XY = 0x10
_ENDEL = 0x11
_HEADER = 0x00
_ENDLIB = 0x04


@dataclass(frozen=True)
class GdsRecord:
    raw: bytes
    record_type: int
    data_type: int
    payload: bytes
    offset: int  # byte offset in source

    @property
    def length(self) -> int:
        return len(self.raw)


@dataclass
class GdsElement:
    layer: int | None = None
    datatype: int | None = None
    bbox: tuple[int, int, int, int] | None = None


def parse_records(data: bytes) -> list[GdsRecord]:
    """Parse *data* into a list of :class:`GdsRecord` objects.

    Raises :class:`ValueError` for truncated, malformed, or invalid GDS.
    """
    if len(data) < 4:
        raise ValueError("truncated GDS: fewer than 4 header bytes")
    records: list[GdsRecord] = []
    offset = 0
    while offset + 4 <= len(data):
        length, rtype, dtype = GDS_RECORD_HEADER.unpack(data[offset : offset + 4])
        if length < 4:
            raise ValueError(f"invalid GDS: record length {length} < 4 at offset {offset}")
        if offset + length > len(data):
            raise ValueError(f"truncated GDS: record at offset {offset} extends past EOF")
        payload = data[offset + 4 : offset + length]
        records.append(GdsRecord(raw=data[offset : offset + length],
                                 record_type=rtype, data_type=dtype,
                                 payload=payload, offset=offset))
        offset += length
    return records


# ---------------------------------------------------------------------------
# Scan a parsed record list for the target cell
# ---------------------------------------------------------------------------

@dataclass
class TargetCellInfo:
    name: str
    bgnstr_offset: int
    endstr_offset: int  # offset of the ENDSTR record (0x07)
    elements: list[GdsElement] = field(default_factory=list)


def scan_target(records: list[GdsRecord], cell: str) -> TargetCellInfo:
    """Locate *cell* in *records* and return its ENDSTR offset + elements.

    Raises :class:`ValueError` when the cell is absent.
    """
    depth = 0
    in_target = False
    bgnstr_offset = -1
    endstr_offset = -1
    elements: list[GdsElement] = []
    current_element: GdsElement | None = None

    for rec in records:
        if rec.record_type == _BGNSTR:
            depth += 1
            bgnstr_offset = rec.offset
            continue
        if rec.record_type == _ENDSTR:
            if in_target:
                endstr_offset = rec.offset
                break
            depth -= 1
            continue
        if rec.record_type == _STRNAME and depth == 1:
            name = rec.payload.rstrip(b"\0").decode("ascii", errors="replace")
            if name == cell:
                in_target = True
            continue
        if not in_target:
            continue

        # Inside target cell — track elements
        if rec.record_type == _BOUNDARY:
            current_element = GdsElement()
            continue
        if current_element is None:
            continue
        if rec.record_type == _LAYER:
            current_element.layer = _decode_int2(rec.payload)
        elif rec.record_type == _DATATYPE:
            current_element.datatype = _decode_int2(rec.payload)
        elif rec.record_type == _XY:
            current_element.bbox = _decode_bbox(rec.payload)
        elif rec.record_type == _ENDEL:
            if current_element.bbox is not None:
                elements.append(current_element)
            current_element = None

    if not in_target or endstr_offset < 0:
        raise ValueError(f"target cell is missing: {cell}")

    return TargetCellInfo(name=cell, bgnstr_offset=bgnstr_offset,
                          endstr_offset=endstr_offset, elements=elements)


def _decode_int2(payload: bytes) -> int | None:
    if len(payload) < 2:
        return None
    return struct.unpack(">h", payload[:2])[0]


def _decode_bbox(payload: bytes) -> tuple[int, int, int, int] | None:
    """Decode a five-point XY payload into a closed axis-aligned bbox.

    Returns ``(min_x, min_y, max_x, max_y)`` or raises :class:`ValueError`.
    """
    points = _decode_xy(payload)
    if len(points) < 5:
        raise ValueError("unsupported non-rectangular BOUNDARY in target cell")
    xs = {p[0] for p in points}
    ys = {p[1] for p in points}
    if len(xs) != 2 or len(ys) != 2:
        raise ValueError("unsupported non-rectangular BOUNDARY in target cell")
    if points[0] != points[-1]:
        raise ValueError("unsupported non-rectangular BOUNDARY in target cell")
    return (min(xs), min(ys), max(xs), max(ys))


def _decode_xy(payload: bytes) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for off in range(0, len(payload), 8):
        if off + 8 <= len(payload):
            x, y = struct.unpack(">ii", payload[off : off + 8])
            points.append((x, y))
    return points


# ---------------------------------------------------------------------------
# Encode BOUNDARY element bytes
# ---------------------------------------------------------------------------


def _encode_boundary(layer: int, datatype: int, box: tuple[int, int, int, int]) -> bytes:
    """Encode a GDS BOUNDARY element: BOUNDARY/LAYER/DATATYPE/XY/ENDEL."""
    x1, y1, x2, y2 = box
    xy = (x1, y1, x1, y2, x2, y2, x2, y1, x1, y1)
    xy_bytes = struct.pack(">10l", *xy)
    return (
        _gds_record(_BOUNDARY) +
        _gds_record(_LAYER, 2, struct.pack(">h", layer)) +
        _gds_record(_DATATYPE, 2, struct.pack(">h", datatype)) +
        _gds_record(_XY, 3, xy_bytes) +
        _gds_record(_ENDEL)
    )


def _gds_record(record_type: int, data_type: int = 0, payload: bytes = b"") -> bytes:
    return struct.pack(">HBB", len(payload) + 4, record_type, data_type) + payload


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inject_stack(
    *,
    input_gds: Path,
    output_gds: Path,
    report: Path,
    summary_json: Path,
    cell: str,
    anchor: tuple[int, int],
    expected_met5_box: tuple[int, int, int, int],
) -> dict[str, Any]:
    """Inject one diagnostic p+ substrate tap stack and write outputs.

    Returns the summary dictionary (also written to *summary_json*).
    """
    # --- Gate 1: input and output paths must differ ---
    if input_gds.resolve() == output_gds.resolve():
        raise ValueError("input and output GDS paths must be different")

    # --- Gate 2: parse input completely ---
    source = input_gds.read_bytes()
    records = parse_records(source)

    # --- Gate 3: target cell exists ---
    target = scan_target(records, cell)

    # --- Gate 4: anchor inside expected met5 box ---
    if not contains_point(expected_met5_box, anchor):
        raise ValueError(
            f"anchor {anchor} is outside expected met5 box "
            f"({expected_met5_box[0]},{expected_met5_box[1]} "
            f"{expected_met5_box[2]},{expected_met5_box[3]})"
        )

    # --- Gate 5: a target-cell 72/20 BOUNDARY contains the anchor ---
    #              AND overlaps the proposed met5 patch
    proposed_met5_patch = absolute_box(anchor, (-150, -150, 150, 150))
    matched_met5_boxes: list[list[int]] = []
    for elem in target.elements:
        if elem.layer == 72 and elem.datatype == 20 and elem.bbox is not None:
            if contains_point(elem.bbox, anchor) and overlaps(elem.bbox, proposed_met5_patch):
                matched_met5_boxes.append(list(elem.bbox))
    if not matched_met5_boxes:
        raise ValueError(
            "no met5 (72/20) BOUNDARY in target cell contains the anchor "
            f"{anchor} and overlaps the proposed met5 patch "
            f"{proposed_met5_patch}"
        )

    # --- Gate 6: no forbidden overlap ---
    psdm_bbox = absolute_box(anchor, (-250, -250, 250, 250))
    forbidden_hits: list[dict[str, Any]] = []
    for elem in target.elements:
        if elem.layer is None or elem.datatype is None or elem.bbox is None:
            continue
        key = (elem.layer, elem.datatype)
        if key in FORBIDDEN_LAYERS and overlaps(psdm_bbox, elem.bbox):
            forbidden_hits.append({
                "layer": elem.layer,
                "datatype": elem.datatype,
                "label": FORBIDDEN_LAYERS[key],
                "bbox": list(elem.bbox),
            })
    if forbidden_hits:
        labels = [h["label"] for h in forbidden_hits]
        raise ValueError(
            f"forbidden overlap detected with: {', '.join(labels)}"
        )

    # --- Build insertion bytes ---
    absolute_rectangles: list[dict[str, Any]] = []
    inserted_parts: list[bytes] = []
    for name, layer, datatype, relative_box in STACK_SPECS:
        abs_box = absolute_box(anchor, relative_box)
        absolute_rectangles.append({
            "name": name,
            "layer": layer,
            "datatype": datatype,
            "relative_bbox": list(relative_box),
            "absolute_bbox": list(abs_box),
        })
        inserted_parts.append(_encode_boundary(layer, datatype, abs_box))

    inserted = b"".join(inserted_parts)
    endstr_offset = target.endstr_offset

    # --- Write output ---
    output_gds.parent.mkdir(parents=True, exist_ok=True)
    result = source[:endstr_offset] + inserted + source[endstr_offset:]

    # Preservation assertions
    original_records_byte_identical = (result[:endstr_offset] == source[:endstr_offset])
    original_tail = source[endstr_offset:]
    result_tail = result[endstr_offset + len(inserted):]
    original_record_order_preserved = (result_tail == original_tail)

    output_gds.write_bytes(result)

    # --- Build summary ---
    stack_spec_entries: list[dict[str, Any]] = []
    for name, layer, datatype, relative_box in STACK_SPECS:
        stack_spec_entries.append({
            "name": name,
            "layer": layer,
            "datatype": datatype,
            "relative_bbox": list(relative_box),
        })

    summary: dict[str, Any] = {
        "input_gds": str(input_gds.resolve()),
        "output_gds": str(output_gds.resolve()),
        "cell": cell,
        "anchor": list(anchor),
        "expected_gnda_met5_box": list(expected_met5_box),
        "matched_gnda_met5_boxes": matched_met5_boxes,
        "stack_spec": stack_spec_entries,
        "absolute_rectangles": absolute_rectangles,
        "added_boundary_count": len(STACK_SPECS),
        "added_text_count": 0,
        "stack_count": 1,
        "forbidden_overlap_count": len(forbidden_hits),
        "source_byte_count": len(source),
        "output_byte_count": len(result),
        "inserted_byte_count": len(inserted),
        "original_records_byte_identical": original_records_byte_identical,
        "original_record_order_preserved": original_record_order_preserved,
    }

    # --- Write report ---
    report.parent.mkdir(parents=True, exist_ok=True)
    _write_report(report, summary)

    # --- Write summary JSON ---
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # --- CLI summary ---
    print(f"output_gds={output_gds.resolve()}")
    print(f"added_boundary_count={len(STACK_SPECS)}")
    print(f"preservation_verified={original_records_byte_identical}")

    return summary


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# P+ Substrate Tap Stack Injection Report",
        "",
        "## Summary",
        "",
        f"- Input GDS: `{summary['input_gds']}`",
        f"- Output GDS: `{summary['output_gds']}`",
        f"- Target cell: `{summary['cell']}`",
        f"- Anchor: `{summary['anchor']}`",
        f"- Expected gnda met5 box: `{summary['expected_gnda_met5_box']}`",
        f"- Matched gnda met5 boxes: {len(summary['matched_gnda_met5_boxes'])}",
        f"- Boundaries added: {summary['added_boundary_count']}",
        f"- TEXT labels added: {summary['added_text_count']}",
        f"- Stack count: {summary['stack_count']}",
        f"- Forbidden overlap count: {summary['forbidden_overlap_count']}",
        f"- Source byte count: {summary['source_byte_count']}",
        f"- Output byte count: {summary['output_byte_count']}",
        f"- Original records byte-identical: {summary['original_records_byte_identical']}",
        f"- Original record order preserved: {summary['original_record_order_preserved']}",
        "",
        "## Absolute Rectangle Table",
        "",
        "| Name | Layer | Datatype | Absolute BBox (x1,y1,x2,y2) |",
        "| --- | ---: | ---: | --- |",
    ]
    for rect in summary["absolute_rectangles"]:
        bbox = rect["absolute_bbox"]
        lines.append(
            f"| `{rect['name']}` | {rect['layer']} | {rect['datatype']} | "
            f"`{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}` |"
        )

    lines.extend([
        "",
        "## Preservation",
        "",
        "- No TEXT or pin-purpose geometry was added.",
        "- All original GDS records remain byte-identical and in the same order.",
        "- Only new BOUNDARY elements were inserted before the target cell's ENDSTR.",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inject one diagnostic p+ substrate tap stack into a Sky130 flat GDS."
    )
    parser.add_argument("--input-gds", type=Path, required=True)
    parser.add_argument("--output-gds", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--cell", type=str, required=True)
    parser.add_argument("--anchor-x", type=int, required=True)
    parser.add_argument("--anchor-y", type=int, required=True)
    parser.add_argument("--expected-gnda-met5-box", type=str, required=True,
                        help="x1,y1,x2,y2 of the expected gnda met5 rail")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    expected_met5_box = parse_box(args.expected_gnda_met5_box)
    inject_stack(
        input_gds=args.input_gds.resolve(),
        output_gds=args.output_gds.resolve(),
        report=args.report.resolve(),
        summary_json=args.summary_json.resolve(),
        cell=args.cell,
        anchor=(args.anchor_x, args.anchor_y),
        expected_met5_box=expected_met5_box,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
