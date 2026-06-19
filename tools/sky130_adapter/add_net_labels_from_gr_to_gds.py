#!/usr/bin/env python3
"""Inject Sky130 net labels from MAGICAL .gr route rectangles into a GDS."""

from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

ROUTE_LABEL_MAP = {
    1: ("li1.label", 67, 5, "li1.pin", 67, 16),
    2: ("met1.label", 68, 5, "met1.pin", 68, 16),
    3: ("met2.label", 69, 5, "met2.pin", 69, 16),
    4: ("met3.label", 70, 5, "met3.pin", 70, 16),
    5: ("met4.label", 71, 5, "met4.pin", 71, 16),
    6: ("met5.label", 72, 5, "met5.pin", 72, 16),
}


@dataclass(frozen=True)
class GdsRecord:
    record_type: int
    data_type: int
    offset: int
    length: int
    payload: bytes


@dataclass(frozen=True)
class RouteNetLabel:
    net: str
    route_id: int
    route_layer: int
    label_layer_name: str
    label_layer: int
    texttype: int
    pin_layer_name: str
    pin_layer: int
    pin_datatype: int
    x1: int
    y1: int
    x2: int
    y2: int
    center_x: int
    center_y: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add Sky130 TEXT labels from MAGICAL .gr routes to GDS.")
    parser.add_argument("--input-gds", type=Path, required=True)
    parser.add_argument("--gr", type=Path, required=True)
    parser.add_argument("--output-gds", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--net", action="append", default=[], help="Net to label. May be repeated.")
    parser.add_argument(
        "--exclude-net",
        action="append",
        default=[],
        help="Net to skip when --net is omitted. May be repeated.",
    )
    parser.add_argument(
        "--include-pin-shapes",
        action="store_true",
        help="Also insert pin-purpose BOUNDARY shapes. Default is TEXT labels only.",
    )
    parser.add_argument(
        "--max-labels-per-net",
        type=int,
        default=3,
        help="Limit injected labels per net to avoid excessive duplicate labels.",
    )
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


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


def string_record(value: str) -> bytes:
    payload = value.encode("ascii")
    if len(payload) % 2:
        payload += b"\0"
    return gds_record(0x19, 0x06, payload)


def text_element(label: RouteNetLabel) -> bytes:
    return b"".join(
        [
            gds_record(0x0C, 0x00),
            int2_record(0x0D, label.label_layer),
            int2_record(0x16, label.texttype),
            xy_record([(label.center_x, label.center_y)]),
            string_record(label.net),
            gds_record(0x11, 0x00),
        ]
    )


def pin_boundary_element(label: RouteNetLabel) -> bytes:
    points = [
        (label.x1, label.y1),
        (label.x1, label.y2),
        (label.x2, label.y2),
        (label.x2, label.y1),
        (label.x1, label.y1),
    ]
    return b"".join(
        [
            gds_record(0x08, 0x00),
            int2_record(0x0D, label.pin_layer),
            int2_record(0x0E, label.pin_datatype),
            xy_record(points),
            gds_record(0x11, 0x00),
        ]
    )


def read_string(payload: bytes) -> str:
    return payload.rstrip(b"\0").decode("ascii", errors="replace")


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
        if record.record_type == 0x06:
            current_cell = read_string(record.payload)
            in_target = current_cell == cell_name
        elif record.record_type == 0x07:
            last_endstr = record.offset
            if in_target:
                return record.offset
            current_cell = ""
            in_target = False
    if last_endstr is not None:
        return last_endstr
    raise ValueError("No ENDSTR record found in input GDS")


def parse_gr_labels(
    gr_path: Path,
    *,
    nets: set[str] | None,
    exclude_nets: set[str],
    max_labels_per_net: int,
) -> list[RouteNetLabel]:
    labels: list[RouteNetLabel] = []
    per_net_count: dict[str, int] = {}
    for line_no, raw_line in enumerate(gr_path.read_text(encoding="utf-8").splitlines(), start=1):
        parts = raw_line.split()
        if len(parts) < 7 or parts[0] in {"gridStep", "Offset", "symAxis"}:
            continue
        net = parts[0]
        if nets is not None and net not in nets:
            continue
        if net in exclude_nets:
            continue
        if per_net_count.get(net, 0) >= max_labels_per_net:
            continue
        try:
            route_id = int(parts[1])
            route_layer = int(parts[2])
            x1, y1, x2, y2 = (int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6]))
        except ValueError as exc:
            raise ValueError(f"Invalid .gr numeric field on line {line_no}: {raw_line}") from exc
        if route_layer not in ROUTE_LABEL_MAP:
            continue
        label_name, label_layer, texttype, pin_name, pin_layer, pin_datatype = ROUTE_LABEL_MAP[route_layer]
        xlo, xhi = sorted((x1, x2))
        ylo, yhi = sorted((y1, y2))
        labels.append(
            RouteNetLabel(
                net=net,
                route_id=route_id,
                route_layer=route_layer,
                label_layer_name=label_name,
                label_layer=label_layer,
                texttype=texttype,
                pin_layer_name=pin_name,
                pin_layer=pin_layer,
                pin_datatype=pin_datatype,
                x1=xlo,
                y1=ylo,
                x2=xhi,
                y2=yhi,
                center_x=int(round((xlo + xhi) / 2.0)),
                center_y=int(round((ylo + yhi) / 2.0)),
            )
        )
        per_net_count[net] = per_net_count.get(net, 0) + 1
    return labels


def write_labelled_gds(
    *,
    input_gds: Path,
    output_gds: Path,
    labels: list[RouteNetLabel],
    cell_name: str,
    include_pin_shapes: bool,
) -> None:
    data = input_gds.read_bytes()
    insert_offset = find_cell_endstr_offset(data, cell_name)
    inserted_parts: list[bytes] = []
    for label in labels:
        inserted_parts.append(text_element(label))
        if include_pin_shapes:
            inserted_parts.append(pin_boundary_element(label))
    output_gds.parent.mkdir(parents=True, exist_ok=True)
    output_gds.write_bytes(data[:insert_offset] + b"".join(inserted_parts) + data[insert_offset:])


def generate_report(
    *,
    input_gds: Path,
    gr: Path,
    output_gds: Path,
    labels: list[RouteNetLabel],
    cell_name: str,
    include_pin_shapes: bool,
) -> str:
    lines = [
        "# Route Net Label Injection Report",
        "",
        "## Summary",
        "",
        f"- Input GDS: `{rel(input_gds)}`",
        f"- Route GR: `{rel(gr)}`",
        f"- Output GDS: `{rel(output_gds)}`",
        f"- Target cell: `{cell_name}`",
        f"- Added TEXT labels: {len(labels)}",
        f"- Added pin-purpose BOUNDARY shapes: {len(labels) if include_pin_shapes else 0}",
        "- This is an extraction-name recovery probe, not a physical LVS signoff claim.",
        "",
        "## Injected Labels",
        "",
    ]
    if labels:
        lines.extend(
            [
                "| net | route id | route layer | box | label purpose | label center |",
                "| --- | ---: | ---: | --- | --- | --- |",
            ]
        )
        for label in labels:
            lines.append(
                f"| `{label.net}` | {label.route_id} | {label.route_layer} | "
                f"`[{label.x1}, {label.y1}, {label.x2}, {label.y2}]` | "
                f"`{label.label_layer_name} {label.label_layer}/{label.texttype}` | "
                f"`({label.center_x}, {label.center_y})` |"
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    input_gds = args.input_gds.resolve()
    gr = args.gr.resolve()
    output_gds = args.output_gds.resolve()
    report = args.report.resolve()
    if not input_gds.is_file():
        raise FileNotFoundError(input_gds)
    if not gr.is_file():
        raise FileNotFoundError(gr)
    selected_nets = set(args.net) if args.net else None
    labels = parse_gr_labels(
        gr,
        nets=selected_nets,
        exclude_nets=set(args.exclude_net),
        max_labels_per_net=args.max_labels_per_net,
    )
    if not labels:
        raise RuntimeError(f"No injectable route labels found in {gr}")
    write_labelled_gds(
        input_gds=input_gds,
        output_gds=output_gds,
        labels=labels,
        cell_name=args.cell,
        include_pin_shapes=bool(args.include_pin_shapes),
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        generate_report(
            input_gds=input_gds,
            gr=gr,
            output_gds=output_gds,
            labels=labels,
            cell_name=args.cell,
            include_pin_shapes=bool(args.include_pin_shapes),
        ),
        encoding="utf-8",
    )
    print(f"output_gds={output_gds}")
    print(f"report={report}")
    print(f"labels={len(labels)}")
    print(f"pin_shapes={len(labels) if args.include_pin_shapes else 0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
