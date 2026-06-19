#!/usr/bin/env python3
"""Tests for GDS structure inspection diagnostics."""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from inspect_gds_structure import build_summary, parse_gds


def record(record_type: int, payload: bytes = b"", data_type: int = 0x00) -> bytes:
    return struct.pack(">HBB", len(payload) + 4, record_type, data_type) + payload


def ascii_payload(value: str) -> bytes:
    payload = value.encode("ascii")
    return payload if len(payload) % 2 == 0 else payload + b"\0"


def int2(value: int) -> bytes:
    return struct.pack(">h", value)


def xy(*points: tuple[int, int]) -> bytes:
    return b"".join(struct.pack(">ii", x, y) for x, y in points)


def minimal_gds() -> bytes:
    return (
        record(0x05)
        + record(0x06, ascii_payload("TOP"), 0x06)
        + record(0x0A)
        + record(0x12, ascii_payload("CHILD"), 0x06)
        + record(0x10, xy((100, 200)), 0x03)
        + record(0x11)
        + record(0x0C)
        + record(0x0D, int2(67), 0x02)
        + record(0x16, int2(5), 0x02)
        + record(0x10, xy((300, 400)), 0x03)
        + record(0x19, ascii_payload("vout"), 0x06)
        + record(0x11)
        + record(0x08)
        + record(0x0D, int2(150), 0x02)
        + record(0x0E, int2(2), 0x02)
        + record(0x10, xy((0, 0), (1, 0), (1, 1), (0, 0)), 0x03)
        + record(0x11)
        + record(0x07)
    )


class InspectGdsStructureTest(unittest.TestCase):
    def test_parse_gds_extracts_refs_texts_and_layers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "top.gds"
            path.write_bytes(minimal_gds())

            cells = parse_gds(path)

        self.assertEqual(list(cells), ["TOP"])
        cell = cells["TOP"]
        self.assertEqual(cell.element_counts["SREF"], 1)
        self.assertEqual(cell.element_counts["TEXT"], 1)
        self.assertEqual(cell.refs[0].sname, "CHILD")
        self.assertEqual(cell.texts[0].string, "vout")
        self.assertEqual(cell.layer_counts["150/2/BOUNDARY"], 1)

    def test_build_summary_reports_passive_name_and_terminal_presence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            gds = root / "top.gds"
            gds.write_bytes(minimal_gds() + b"xr0")
            netlist = root / "amp.sp"
            netlist.write_text(
                ".subckt amp vdda gnda vout\n"
                "xr0 net027 vout gnda rppolywo_m lr=4e-6\n"
                ".ends\n",
                encoding="utf-8",
            )
            case_dir = root / "case"
            passive_gds_dir = case_dir / "gds"
            passive_gds_dir.mkdir(parents=True)
            (passive_gds_dir / "AMP_xr0.gds").write_bytes(minimal_gds())

            summary = build_summary(
                top_gds=gds,
                source_netlist=netlist,
                case_dir=case_dir,
                top_cell="AMP",
            )

        self.assertEqual(summary["top_gds"]["cell_count"], 1)
        self.assertEqual(summary["top_gds"]["text_count"], 1)
        self.assertEqual(summary["top_gds"]["ref_count"], 1)
        self.assertEqual(summary["source_passive_instance_names_present"]["xr0"], True)
        self.assertEqual(summary["source_passive_terminal_names_present"]["vout"], True)
        self.assertEqual(summary["source_passive_terminal_names_present"]["net027"], False)
        self.assertEqual(summary["generated_passive_gds_present_count"], 1)
        self.assertEqual(summary["generated_passive_gds"]["xr0"]["text_count"], 1)


if __name__ == "__main__":
    unittest.main()
