#!/usr/bin/env python3
"""Inspect Sky130 label TEXT and pin-purpose BOUNDARY elements."""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GDS = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds"
DEFAULT_IOPIN = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.ioPin"
DEFAULT_REPORT = REPO_ROOT / "docs/sky130_adapter/gds_pin_shape_analysis.md"

PIN_NAMES = {"A", "Y", "VPWR", "VGND"}
PIN_PURPOSE_MAP = {
    1: ("li1", 67, 20, 67, 5, 67, 16),
    2: ("met1", 68, 20, 68, 5, 68, 16),
    6: ("met5", 72, 20, 72, 5, 72, 16),
}


@dataclass(frozen=True)
class Box:
    x1: int
    y1: int
    x2: int
    y2: int

    def contains_point(self, xy: tuple[int, int] | None) -> bool:
        if xy is None:
            return False
        x, y = xy
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def overlaps(self, other: "Box") -> bool:
        return not (self.x2 < other.x1 or other.x2 < self.x1 or self.y2 < other.y1 or other.y2 < self.y1)

    def text(self) -> str:
        return f"({self.x1}, {self.y1}) - ({self.x2}, {self.y2})"


@dataclass(frozen=True)
class PinInfo:
    name: str
    iopin_layer: int
    box: Box
    sky130_name: str
    drawing_layer: int
    drawing_datatype: int
    label_layer: int
    label_datatype: int
    pin_layer: int
    pin_datatype: int


@dataclass(frozen=True)
class TextElement:
    string: str
    layer: int | None
    texttype: int | None
    xy: tuple[int, int] | None


@dataclass(frozen=True)
class BoundaryElement:
    layer: int | None
    datatype: int | None
    bbox: Box | None


@dataclass
class ElementDraft:
    element_type: str
    layer: int | None = None
    datatype: int | None = None
    texttype: int | None = None
    xy: list[tuple[int, int]] = field(default_factory=list)
    string: str = ""


@dataclass(frozen=True)
class Inspection:
    text_elements: list[TextElement]
    boundaries: list[BoundaryElement]


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


def read_string(payload: bytes) -> str:
    return payload.rstrip(b"\0").decode("ascii", errors="replace")


def bbox_from_points(points: list[tuple[int, int]]) -> Box | None:
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return Box(min(xs), min(ys), max(xs), max(ys))


def inspect_gds(path: Path) -> Inspection:
    data = path.read_bytes()
    offset = 0
    current: ElementDraft | None = None
    texts: list[TextElement] = []
    boundaries: list[BoundaryElement] = []

    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError(f"Truncated GDS record header at byte {offset}")
        record_len, record_type, _data_type = struct.unpack(">HBB", data[offset : offset + 4])
        if record_len < 4:
            raise ValueError(f"Invalid GDS record length {record_len} at byte {offset}")
        payload = data[offset + 4 : offset + record_len]

        if record_type == 0x08:
            current = ElementDraft("BOUNDARY")
        elif record_type == 0x0C:
            current = ElementDraft("TEXT")
        elif current is not None and record_type == 0x0D:
            current.layer = read_int2(payload)
        elif current is not None and record_type == 0x0E:
            current.datatype = read_int2(payload)
        elif current is not None and record_type == 0x16:
            current.texttype = read_int2(payload)
        elif current is not None and record_type == 0x10:
            current.xy = read_int4_pairs(payload)
        elif current is not None and record_type == 0x19:
            current.string = read_string(payload)
        elif record_type == 0x11:
            if current is not None and current.element_type == "TEXT":
                texts.append(
                    TextElement(
                        string=current.string,
                        layer=current.layer,
                        texttype=current.texttype,
                        xy=current.xy[0] if current.xy else None,
                    )
                )
            elif current is not None and current.element_type == "BOUNDARY":
                boundaries.append(
                    BoundaryElement(
                        layer=current.layer,
                        datatype=current.datatype,
                        bbox=bbox_from_points(current.xy),
                    )
                )
            current = None

        offset += record_len

    return Inspection(text_elements=texts, boundaries=boundaries)


def read_iopin(path: Path) -> dict[str, PinInfo]:
    pins: dict[str, PinInfo] = {}
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 6:
            continue
        name, layer_text, x1_text, y1_text, x2_text, y2_text = parts
        if name not in PIN_NAMES:
            continue
        iopin_layer = int(layer_text)
        if iopin_layer not in PIN_PURPOSE_MAP:
            raise ValueError(f"No Sky130 purpose mapping for ioPin layer {iopin_layer} on line {line_no}")
        sky130_name, drawing_layer, drawing_dt, label_layer, label_dt, pin_layer, pin_dt = PIN_PURPOSE_MAP[iopin_layer]
        x1, x2 = sorted((int(x1_text), int(x2_text)))
        y1, y2 = sorted((int(y1_text), int(y2_text)))
        pins[name] = PinInfo(
            name=name,
            iopin_layer=iopin_layer,
            box=Box(x1, y1, x2, y2),
            sky130_name=sky130_name,
            drawing_layer=drawing_layer,
            drawing_datatype=drawing_dt,
            label_layer=label_layer,
            label_datatype=label_dt,
            pin_layer=pin_layer,
            pin_datatype=pin_dt,
        )
    return pins


def has_label(pin: PinInfo, inspection: Inspection) -> bool:
    return any(
        text.string == pin.name
        and text.layer == pin.label_layer
        and text.texttype == pin.label_datatype
        and pin.box.contains_point(text.xy)
        for text in inspection.text_elements
    )


def has_pin_boundary(pin: PinInfo, inspection: Inspection) -> bool:
    return any(
        boundary.layer == pin.pin_layer
        and boundary.datatype == pin.pin_datatype
        and boundary.bbox is not None
        and boundary.bbox.overlaps(pin.box)
        for boundary in inspection.boundaries
    )


def has_drawing_geometry(pin: PinInfo, inspection: Inspection) -> bool:
    return any(
        boundary.layer == pin.drawing_layer
        and boundary.datatype == pin.drawing_datatype
        and boundary.bbox is not None
        and boundary.bbox.overlaps(pin.box)
        for boundary in inspection.boundaries
    )


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def matching_boundaries(pin: PinInfo, inspection: Inspection, layer: int, datatype: int) -> list[BoundaryElement]:
    return [
        boundary
        for boundary in inspection.boundaries
        if boundary.layer == layer
        and boundary.datatype == datatype
        and boundary.bbox is not None
        and boundary.bbox.overlaps(pin.box)
    ]


def matching_labels(pin: PinInfo, inspection: Inspection) -> list[TextElement]:
    return [
        text
        for text in inspection.text_elements
        if text.string == pin.name
        and text.layer == pin.label_layer
        and text.texttype == pin.label_datatype
        and pin.box.contains_point(text.xy)
    ]


def generate_report(gds: Path, iopin: Path, inspection: Inspection, pins: dict[str, PinInfo]) -> str:
    lines = [
        "# GDS Pin Shape Analysis",
        "",
        "## Summary",
        "",
        f"- GDS: `{rel(gds)}`",
        f"- ioPin file: `{rel(iopin)}`",
        f"- TEXT elements: {len(inspection.text_elements)}",
        f"- BOUNDARY elements: {len(inspection.boundaries)}",
        "",
        "## Per-Pin Check",
        "",
        "| pin | ioPin layer | ioPin box | expected Sky130 stack | label TEXT present | pin BOUNDARY present | drawing geometry present |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for name in sorted(pins):
        pin = pins[name]
        lines.append(
            f"| {name} | {pin.iopin_layer} | {pin.box.text()} | "
            f"{pin.sky130_name}: drawing {pin.drawing_layer}/{pin.drawing_datatype}, label {pin.label_layer}/{pin.label_datatype}, pin {pin.pin_layer}/{pin.pin_datatype} | "
            f"{yes_no(has_label(pin, inspection))} | {yes_no(has_pin_boundary(pin, inspection))} | {yes_no(has_drawing_geometry(pin, inspection))} |"
        )

    lines.extend(
        [
            "",
            "## Matching Pin-Purpose Boundaries",
            "",
            "| pin | expected pin layer/datatype | matching boundary boxes |",
            "| --- | --- | --- |",
        ]
    )
    for name in sorted(pins):
        pin = pins[name]
        boxes = [item.bbox.text() for item in matching_boundaries(pin, inspection, pin.pin_layer, pin.pin_datatype) if item.bbox]
        lines.append(f"| {name} | {pin.pin_layer}/{pin.pin_datatype} | {'; '.join(boxes) if boxes else 'none'} |")

    lines.extend(
        [
            "",
            "## Matching Label TEXT",
            "",
            "| pin | expected label layer/texttype | matching labels |",
            "| --- | --- | --- |",
        ]
    )
    for name in sorted(pins):
        pin = pins[name]
        labels = [
            f"{text.string}@({text.xy[0]}, {text.xy[1]})" if text.xy else f"{text.string}@none"
            for text in matching_labels(pin, inspection)
        ]
        lines.append(f"| {name} | {pin.label_layer}/{pin.label_datatype} | {'; '.join(labels) if labels else 'none'} |")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `label TEXT present` requires the Sky130 label layer/texttype and a coordinate inside the ioPin box.",
            "- `pin BOUNDARY present` requires a Sky130 pin-purpose boundary overlapping the ioPin box.",
            "- `drawing geometry present` checks for overlapping Sky130 drawing geometry on the same routing layer.",
            "- This report is diagnostic only and does not modify the GDS.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect Sky130 pin labels and pin-purpose geometry.")
    parser.add_argument("--gds", type=Path, default=DEFAULT_GDS)
    parser.add_argument("--iopin", type=Path, default=DEFAULT_IOPIN)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    gds = args.gds.resolve()
    iopin = args.iopin.resolve()
    report = args.report.resolve()
    try:
        if not gds.is_file():
            raise FileNotFoundError(gds)
        if not iopin.is_file():
            raise FileNotFoundError(iopin)
        inspection = inspect_gds(gds)
        pins = read_iopin(iopin)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(generate_report(gds, iopin, inspection, pins), encoding="utf-8")
        print(f"GDS: {gds}")
        print(f"TEXT elements: {len(inspection.text_elements)}")
        print(f"BOUNDARY elements: {len(inspection.boundaries)}")
        for name in sorted(pins):
            pin = pins[name]
            print(
                f"{name}: label={yes_no(has_label(pin, inspection))}, "
                f"pin_boundary={yes_no(has_pin_boundary(pin, inspection))}, "
                f"drawing={yes_no(has_drawing_geometry(pin, inspection))}"
            )
        print(f"Report written: {report}")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
