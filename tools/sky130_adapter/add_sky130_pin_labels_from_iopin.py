#!/usr/bin/env python3
"""Add experimental Sky130 pin labels from MAGICAL ioPin boxes.

The original GDS is left untouched. The script inserts additional TEXT elements
before the top cell ENDSTR and writes a new pinned GDS for Magic extraction
experiments. Existing TEXT records, including MAGICAL's 131/0 and 136/0 labels,
are preserved.
"""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

from pin_top_port_filter import PinFilterResult, filter_pin_objects, parse_top_ports


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_GDS = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.sky130.gds"
DEFAULT_IOPIN = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.ioPin"
DEFAULT_OUTPUT_GDS = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.sky130.pinned.gds"
DEFAULT_REPORT = REPO_ROOT / "docs/sky130_adapter/sky130_pin_label_postprocess.md"
DEFAULT_CELL = "inverter_core_flat"

PIN_LABEL_MAP = {
    1: ("li1.label", 67, 5),
    2: ("met1.label", 68, 5),
    6: ("met5.label", 72, 5),
}


@dataclass(frozen=True)
class GdsRecord:
    record_type: int
    data_type: int
    offset: int
    length: int
    payload: bytes


@dataclass(frozen=True)
class PinLabel:
    name: str
    iopin_layer: int
    x1: int
    y1: int
    x2: int
    y2: int
    center_x: int
    center_y: int
    sky130_name: str
    gds_layer: int
    texttype: int


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


def xy_record(x: int, y: int) -> bytes:
    return gds_record(0x10, 0x03, struct.pack(">ll", x, y))


def string_record(value: str) -> bytes:
    payload = value.encode("ascii")
    if len(payload) % 2:
        payload += b"\0"
    return gds_record(0x19, 0x06, payload)


def text_element(label: PinLabel) -> bytes:
    return b"".join(
        [
            gds_record(0x0C, 0x00),  # TEXT
            int2_record(0x0D, label.gds_layer),  # LAYER
            int2_record(0x16, label.texttype),  # TEXTTYPE
            xy_record(label.center_x, label.center_y),
            string_record(label.name),
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
        records.append(
            GdsRecord(
                record_type=record_type,
                data_type=data_type,
                offset=offset,
                length=length,
                payload=data[offset + 4 : end],
            )
        )
        offset = end
    return records


def find_cell_endstr_offset(data: bytes, cell_name: str) -> int:
    records = parse_records(data)
    current_cell = ""
    in_target = False
    last_endstr: int | None = None

    for record in records:
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


def read_iopin(path: Path) -> list[PinLabel]:
    labels: list[PinLabel] = []
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

        if iopin_layer not in PIN_LABEL_MAP:
            raise ValueError(f"No Sky130 label mapping for ioPin layer {iopin_layer} on line {line_no}")

        sky130_name, gds_layer, texttype = PIN_LABEL_MAP[iopin_layer]
        xlo, xhi = sorted((x1, x2))
        ylo, yhi = sorted((y1, y2))
        labels.append(
            PinLabel(
                name=name,
                iopin_layer=iopin_layer,
                x1=xlo,
                y1=ylo,
                x2=xhi,
                y2=yhi,
                center_x=int(round((xlo + xhi) / 2.0)),
                center_y=int(round((ylo + yhi) / 2.0)),
                sky130_name=sky130_name,
                gds_layer=gds_layer,
                texttype=texttype,
            )
        )
    return labels


def write_pinned_gds(input_gds: Path, output_gds: Path, labels: list[PinLabel], cell_name: str) -> None:
    data = input_gds.read_bytes()
    insert_offset = find_cell_endstr_offset(data, cell_name)
    inserted = b"".join(text_element(label) for label in labels)
    output_gds.parent.mkdir(parents=True, exist_ok=True)
    output_gds.write_bytes(data[:insert_offset] + inserted + data[insert_offset:])


def generate_report(
    input_gds: Path,
    output_gds: Path,
    iopin: Path,
    labels: list[PinLabel],
    cell_name: str,
    netlist: Path | None = None,
    top_cell: str | None = None,
    top_ports: list[str] | None = None,
    filter_result: PinFilterResult | None = None,
    only_top_ports: bool = False,
) -> str:
    lines = [
        "# Sky130 Pin Label Postprocess",
        "",
        "## Summary",
        "",
        f"- Input GDS: `{rel(input_gds)}`",
        f"- Output GDS: `{rel(output_gds)}`",
        f"- ioPin file: `{rel(iopin)}`",
        f"- Target cell: `{cell_name}`",
        f"- Top-port filtering: {'enabled' if only_top_ports else 'disabled'}",
        f"- Added TEXT labels: {len(labels)}",
        "- Existing geometry and existing TEXT records are preserved.",
        "- This is a non-destructive experimental postprocess, not final native Sky130 export.",
        "",
        "## Top-Port Filter",
        "",
    ]
    if only_top_ports:
        assert netlist is not None
        assert top_cell is not None
        assert top_ports is not None
        assert filter_result is not None
        lines.extend(
            [
                f"- Netlist: `{rel(netlist)}`",
                f"- Top cell: `{top_cell}`",
                f"- Top ports: {', '.join(top_ports) if top_ports else '(none)'}",
                f"- Processed pins: {', '.join(filter_result.processed) if filter_result.processed else '(none)'}",
                f"- Skipped internal nets: {', '.join(filter_result.skipped) if filter_result.skipped else '(none)'}",
                "",
                "| skipped net | skipped reason |",
                "| --- | --- |",
            ]
        )
        if filter_result.skipped:
            for name in filter_result.skipped:
                lines.append(f"| {name} | {filter_result.skipped_reasons[name]} |")
        else:
            lines.append("| (none) | (none) |")
    else:
        lines.extend(
            [
                "- Top-port filtering was not requested.",
                "- Warning: all ioPin entries are treated as pins, including any internal routed nets present in ioPin.",
            ]
        )

    lines.extend(
        [
            "",
        "## Added Labels",
        "",
        "| pin | ioPin layer | ioPin box | label center | Sky130 label purpose | GDS layer | texttype |",
        "| --- | ---: | --- | --- | --- | ---: | ---: |",
        ]
    )
    for label in labels:
        lines.append(
            f"| {label.name} | {label.iopin_layer} | "
            f"({label.x1}, {label.y1}) - ({label.x2}, {label.y2}) | "
            f"({label.center_x}, {label.center_y}) | {label.sky130_name} | "
            f"{label.gds_layer} | {label.texttype} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- ioPin layer 1 is mapped to `li1.label` `67/5`.",
            "- ioPin layer 2 is mapped to `met1.label` `68/5`.",
            "- ioPin layer 6 is mapped to `met5.label` `72/5`.",
            "- The older MAGICAL TEXT records on `131/0` and `136/0` are intentionally retained for comparison.",
            "- If Magic still extracts anonymous internal node names, the next check is whether Magic expects pin shapes in addition to labels.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add Sky130 pin TEXT labels from MAGICAL ioPin boxes.")
    parser.add_argument("--input-gds", type=Path, default=DEFAULT_INPUT_GDS)
    parser.add_argument("--iopin", type=Path, default=DEFAULT_IOPIN)
    parser.add_argument("--output-gds", type=Path, default=DEFAULT_OUTPUT_GDS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--cell", default=DEFAULT_CELL)
    parser.add_argument("--netlist", type=Path, help="Source netlist containing the top subckt declaration.")
    parser.add_argument("--top-cell", help="Top subckt name to read from --netlist.")
    parser.add_argument("--only-top-ports", action="store_true", help="Only add labels for ioPin names that are top subckt ports.")
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
        labels = read_iopin(iopin)
        if not labels:
            raise RuntimeError(f"No pin labels found in {iopin}")

        netlist: Path | None = None
        top_ports: list[str] | None = None
        filter_result: PinFilterResult | None = None
        if args.only_top_ports:
            if args.netlist is None:
                raise ValueError("--netlist is required with --only-top-ports")
            if args.top_cell is None:
                raise ValueError("--top-cell is required with --only-top-ports")
            netlist = args.netlist.resolve()
            if not netlist.is_file():
                raise FileNotFoundError(netlist)
            top_ports = parse_top_ports(netlist, args.top_cell)
            labels, filter_result = filter_pin_objects(labels, top_ports)
            if not labels:
                raise RuntimeError(f"No top-port pin labels found in {iopin}")
        else:
            print("warning: --only-top-ports not set; all ioPin entries will be labeled", file=sys.stderr)

        write_pinned_gds(input_gds, output_gds, labels, args.cell)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            generate_report(
                input_gds,
                output_gds,
                iopin,
                labels,
                args.cell,
                netlist=netlist,
                top_cell=args.top_cell,
                top_ports=top_ports,
                filter_result=filter_result,
                only_top_ports=args.only_top_ports,
            ),
            encoding="utf-8",
        )

        print(f"Input GDS: {input_gds}")
        print(f"Output GDS: {output_gds}")
        if args.only_top_ports:
            assert top_ports is not None
            assert filter_result is not None
            print(f"Top ports: {', '.join(top_ports)}")
            print(f"Processed pins: {', '.join(filter_result.processed) if filter_result.processed else '(none)'}")
            print(f"Skipped internal nets: {', '.join(filter_result.skipped) if filter_result.skipped else '(none)'}")
            for name in filter_result.skipped:
                print(f"Skipped {name}: {filter_result.skipped_reasons[name]}")
        for label in labels:
            print(
                f"Added {label.name}: ioPin layer {label.iopin_layer}, "
                f"center ({label.center_x}, {label.center_y}), "
                f"{label.sky130_name} {label.gds_layer}/{label.texttype}"
            )
        print(f"Report written: {report}")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
