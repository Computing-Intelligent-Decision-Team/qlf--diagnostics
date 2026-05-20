#!/usr/bin/env python3
"""Add experimental Sky130 pin-purpose shapes from MAGICAL ioPin boxes.

Input is the label-pinned GDS. Output is a separate GDS with additional
Sky130 pin-purpose BOUNDARY elements. Existing drawing geometry and TEXT are
preserved exactly; this is only an experimental postprocess for Magic
extraction.
"""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_GDS = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.sky130.pinned.gds"
DEFAULT_IOPIN = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.ioPin"
DEFAULT_OUTPUT_GDS = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds"
DEFAULT_REPORT = REPO_ROOT / "docs/sky130_adapter/sky130_pin_shape_postprocess.md"
DEFAULT_CELL = "inverter_core_flat"

PDK_QUERY_SOURCES = [
    "libs.tech/klayout/tech/sky130A.lyp",
    "libs.tech/klayout/tech/sky130A.map",
    "libs.tech/magic/sky130A.tech",
    "libs.tech/magic/sky130A-GDS.tech",
]

PIN_SHAPE_MAP = {
    1: ("li1.pin", 67, 16, "li1.label", 67, 5, "li1.drawing", 67, 20),
    2: ("met1.pin", 68, 16, "met1.label", 68, 5, "met1.drawing", 68, 20),
    6: ("met5.pin", 72, 16, "met5.label", 72, 5, "met5.drawing", 72, 20),
}


@dataclass(frozen=True)
class GdsRecord:
    record_type: int
    data_type: int
    offset: int
    length: int
    payload: bytes


@dataclass(frozen=True)
class PinShape:
    name: str
    iopin_layer: int
    x1: int
    y1: int
    x2: int
    y2: int
    pin_name: str
    pin_layer: int
    pin_datatype: int
    label_name: str
    label_layer: int
    label_datatype: int
    drawing_name: str
    drawing_layer: int
    drawing_datatype: int


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_string(payload: bytes) -> str:
    return payload.rstrip(b"\0").decode("ascii", errors="replace")


def gds_record(record_type: int, data_type: int, payload: bytes = b"") -> bytes:
    length = 4 + len(payload)
    if length % 2:
        raise ValueError(f"GDS record length must be even, got {length}")
    return struct.pack(">HBB", length, record_type, data_type) + payload


def int2_record(record_type: int, value: int) -> bytes:
    return gds_record(record_type, 0x02, struct.pack(">h", value))


def xy_record(points: list[tuple[int, int]]) -> bytes:
    flat: list[int] = []
    for x, y in points:
        flat.extend([x, y])
    return gds_record(0x10, 0x03, struct.pack(f">{len(flat)}l", *flat))


def boundary_element(shape: PinShape) -> bytes:
    points = [
        (shape.x1, shape.y1),
        (shape.x1, shape.y2),
        (shape.x2, shape.y2),
        (shape.x2, shape.y1),
        (shape.x1, shape.y1),
    ]
    return b"".join(
        [
            gds_record(0x08, 0x00),  # BOUNDARY
            int2_record(0x0D, shape.pin_layer),  # LAYER
            int2_record(0x0E, shape.pin_datatype),  # DATATYPE
            xy_record(points),
            gds_record(0x11, 0x00),  # ENDEL
        ]
    )


def parse_records(data: bytes) -> list[GdsRecord]:
    records: list[GdsRecord] = []
    offset = 0
    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError(f"Truncated GDS record header at byte {offset}")
        length, record_type, data_type = struct.unpack(">HBB", data[offset : offset + 4])
        if length < 4:
            raise ValueError(f"Invalid GDS record length {length} at byte {offset}")
        end = offset + length
        if end > len(data):
            raise ValueError(f"Truncated GDS record payload at byte {offset}")
        records.append(GdsRecord(record_type, data_type, offset, length, data[offset + 4 : end]))
        offset = end
    return records


def find_cell_endstr_offset(data: bytes, cell_name: str) -> int:
    current_cell = ""
    in_target = False
    last_endstr: int | None = None
    for record in parse_records(data):
        if record.record_type == 0x06:  # STRNAME
            current_cell = read_string(record.payload)
            in_target = current_cell == cell_name
        elif record.record_type == 0x07:  # ENDSTR
            last_endstr = record.offset
            if in_target:
                return record.offset
            current_cell = ""
            in_target = False
    if last_endstr is not None:
        return last_endstr
    raise ValueError("No ENDSTR record found in input GDS")


def read_iopin(path: Path) -> list[PinShape]:
    shapes: list[PinShape] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 6:
            continue
        name, layer_text, x1_text, y1_text, x2_text, y2_text = parts
        try:
            iopin_layer = int(layer_text)
            x1 = int(x1_text)
            y1 = int(y1_text)
            x2 = int(x2_text)
            y2 = int(y2_text)
        except ValueError as exc:
            raise ValueError(f"Invalid ioPin numeric field on line {line_no}: {raw_line}") from exc
        if iopin_layer not in PIN_SHAPE_MAP:
            raise ValueError(f"No Sky130 pin-shape mapping for ioPin layer {iopin_layer} on line {line_no}")

        pin_name, pin_layer, pin_datatype, label_name, label_layer, label_datatype, drawing_name, drawing_layer, drawing_datatype = PIN_SHAPE_MAP[iopin_layer]
        xlo, xhi = sorted((x1, x2))
        ylo, yhi = sorted((y1, y2))
        shapes.append(
            PinShape(
                name=name,
                iopin_layer=iopin_layer,
                x1=xlo,
                y1=ylo,
                x2=xhi,
                y2=yhi,
                pin_name=pin_name,
                pin_layer=pin_layer,
                pin_datatype=pin_datatype,
                label_name=label_name,
                label_layer=label_layer,
                label_datatype=label_datatype,
                drawing_name=drawing_name,
                drawing_layer=drawing_layer,
                drawing_datatype=drawing_datatype,
            )
        )
    return shapes


def write_pinned_shapes_gds(input_gds: Path, output_gds: Path, shapes: list[PinShape], cell_name: str) -> None:
    data = input_gds.read_bytes()
    insert_offset = find_cell_endstr_offset(data, cell_name)
    inserted = b"".join(boundary_element(shape) for shape in shapes)
    output_gds.parent.mkdir(parents=True, exist_ok=True)
    output_gds.write_bytes(data[:insert_offset] + inserted + data[insert_offset:])


def generate_report(input_gds: Path, output_gds: Path, iopin: Path, shapes: list[PinShape], cell_name: str) -> str:
    lines = [
        "# Sky130 Pin Shape Postprocess",
        "",
        "## Summary",
        "",
        f"- Input GDS: `{rel(input_gds)}`",
        f"- Output GDS: `{rel(output_gds)}`",
        f"- ioPin file: `{rel(iopin)}`",
        f"- Target cell: `{cell_name}`",
        f"- Added pin-purpose BOUNDARY elements: {len(shapes)}",
        "- Existing drawing geometry, old TEXT, and new label TEXT are preserved.",
        "- This is an experimental postprocess, not final native Sky130 export.",
        "",
        "## Local PDK Datatype Confirmation",
        "",
        "| purpose | GDS layer/datatype | source |",
        "| --- | --- | --- |",
        "| li1.label | 67/5 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |",
        "| li1.pin | 67/16 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |",
        "| met1.label | 68/5 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |",
        "| met1.pin | 68/16 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |",
        "| met5.label | 72/5 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |",
        "| met5.pin | 72/16 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |",
        "",
        "Checked PDK files:",
    ]
    for source in PDK_QUERY_SOURCES:
        lines.append(f"- `{source}`")

    lines.extend(
        [
            "",
            "## Added Pin Shapes",
            "",
            "| pin | ioPin layer | box | Sky130 pin purpose | GDS layer | datatype | expected drawing layer | expected label layer |",
            "| --- | ---: | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for shape in shapes:
        lines.append(
            f"| {shape.name} | {shape.iopin_layer} | ({shape.x1}, {shape.y1}) - ({shape.x2}, {shape.y2}) | "
            f"{shape.pin_name} | {shape.pin_layer} | {shape.pin_datatype} | "
            f"{shape.drawing_name} {shape.drawing_layer}/{shape.drawing_datatype} | "
            f"{shape.label_name} {shape.label_layer}/{shape.label_datatype} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Pin shape boxes are copied directly from `inverter_core.ioPin`.",
            "- The output GDS keeps the existing `131/0` and `136/0` TEXT labels and the Sky130 label-purpose TEXT labels from the previous postprocess.",
            "- This experiment tests whether Magic extraction needs both label TEXT and pin-purpose geometry to preserve top-level port names.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add Sky130 pin-purpose BOUNDARY shapes from ioPin boxes.")
    parser.add_argument("--input-gds", type=Path, default=DEFAULT_INPUT_GDS)
    parser.add_argument("--iopin", type=Path, default=DEFAULT_IOPIN)
    parser.add_argument("--output-gds", type=Path, default=DEFAULT_OUTPUT_GDS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--cell", default=DEFAULT_CELL)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    input_gds = args.input_gds.resolve()
    iopin = args.iopin.resolve()
    output_gds = args.output_gds.resolve()
    report = args.report.resolve()

    try:
        if not input_gds.is_file():
            raise FileNotFoundError(input_gds)
        if not iopin.is_file():
            raise FileNotFoundError(iopin)
        shapes = read_iopin(iopin)
        if not shapes:
            raise RuntimeError(f"No pin shapes found in {iopin}")
        write_pinned_shapes_gds(input_gds, output_gds, shapes, args.cell)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(generate_report(input_gds, output_gds, iopin, shapes, args.cell), encoding="utf-8")

        print(f"Input GDS: {input_gds}")
        print(f"Output GDS: {output_gds}")
        for shape in shapes:
            print(
                f"Added {shape.name}: ioPin layer {shape.iopin_layer}, "
                f"box ({shape.x1}, {shape.y1}) - ({shape.x2}, {shape.y2}), "
                f"{shape.pin_name} {shape.pin_layer}/{shape.pin_datatype}"
            )
        print(f"Report written: {report}")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
