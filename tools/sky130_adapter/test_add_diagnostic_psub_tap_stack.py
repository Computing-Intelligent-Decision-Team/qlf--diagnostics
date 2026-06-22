#!/usr/bin/env python3
"""Tests for diagnostic p+ substrate tap stack injection into a Sky130 flat GDS."""

from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from add_diagnostic_psub_tap_stack import STACK_SPECS, inject_stack
from inspect_gds_structure import parse_gds


def record(kind: int, dtype: int = 0, payload: bytes = b"") -> bytes:
    return struct.pack(">HBB", len(payload) + 4, kind, dtype) + payload


def int2(kind: int, value: int) -> bytes:
    return record(kind, 2, struct.pack(">h", value))


def ascii_record(kind: int, value: str) -> bytes:
    payload = value.encode("ascii")
    if len(payload) % 2:
        payload += b"\0"
    return record(kind, 6, payload)


def boundary(layer: int, datatype: int, box: tuple[int, int, int, int]) -> bytes:
    x1, y1, x2, y2 = box
    xy = (x1, y1, x1, y2, x2, y2, x2, y1, x1, y1)
    return b"".join((
        record(0x08), int2(0x0D, layer), int2(0x0E, datatype),
        record(0x10, 3, struct.pack(">10l", *xy)), record(0x11),
    ))


def structure(name: str, elements: bytes) -> bytes:
    return record(0x05) + ascii_record(0x06, name) + elements + record(0x07)


def fixture(*extra: bytes, include_rail: bool = True) -> bytes:
    rail = boundary(72, 20, (150, -2050, 650, 11650)) if include_rail else b""
    harmless = boundary(108, 0, (2000, 2000, 2200, 2200))
    return b"".join((
        record(0x00),
        structure("OTHER", boundary(70, 20, (0, 0, 10, 10))),
        structure("fan_smc_pin_3_flat", rail + harmless + b"".join(extra)),
        record(0x04),
    ))


class AddDiagnosticPsubstrateTapStackTest(unittest.TestCase):
    """Tests for diagnostic p+ substrate tap stack injection."""

    def test_adds_exact_stack_and_preserves_original_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source, output = root / "input.gds", root / "output.gds"
            report, summary_path = root / "report.md", root / "summary.json"
            original = fixture()
            source.write_bytes(original)
            summary = inject_stack(
                input_gds=source, output_gds=output, report=report,
                summary_json=summary_path, cell="fan_smc_pin_3_flat",
                anchor=(400, -1000),
                expected_met5_box=(150, -2050, 650, 11650),
            )
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(summary["added_boundary_count"], 14)
            self.assertEqual(summary["added_text_count"], 0)
            self.assertTrue(summary["original_records_byte_identical"])
            self.assertTrue(summary["original_record_order_preserved"])
            self.assertEqual(summary["stack_count"], 1)
            self.assertEqual(json.loads(summary_path.read_text()), summary)
            cell = parse_gds(output)["fan_smc_pin_3_flat"]
            for name, layer, datatype, relative_box in STACK_SPECS:
                with self.subTest(name=name):
                    expected_count = 2 if (layer, datatype) == (72, 20) else 1
                    self.assertEqual(
                        cell.layer_counts[f"{layer}/{datatype}/BOUNDARY"],
                        expected_count,
                    )
                    self.assertIn({
                        "name": name, "layer": layer, "datatype": datatype,
                        "relative_bbox": list(relative_box),
                    }, summary["stack_spec"])
            self.assertEqual(cell.element_counts.get("TEXT", 0), 0)

    def assert_rejected(
        self, data: bytes, pattern: str, *, cell: str = "fan_smc_pin_3_flat",
        same_path: bool = False,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "input.gds"
            output = source if same_path else root / "output.gds"
            report, summary = root / "report.md", root / "summary.json"
            source.write_bytes(data)
            with self.assertRaisesRegex(ValueError, pattern):
                inject_stack(
                    input_gds=source, output_gds=output, report=report,
                    summary_json=summary, cell=cell, anchor=(400, -1000),
                    expected_met5_box=(150, -2050, 650, 11650),
                )
            if not same_path:
                self.assertFalse(output.exists())
            self.assertFalse(report.exists())
            self.assertFalse(summary.exists())

    def test_rejects_absent_target_cell(self) -> None:
        self.assert_rejected(fixture(), "target cell.*missing", cell="ABSENT")

    def test_rejects_missing_met5_anchor(self) -> None:
        self.assert_rejected(fixture(include_rail=False), "met5.*anchor")

    def test_rejects_forbidden_overlaps(self) -> None:
        for layer, datatype, label in (
            (66, 20, "poly.drawing"), (64, 20, "nwell.drawing"),
            (65, 20, "diff.drawing"), (65, 44, "tap.existing"),
        ):
            with self.subTest(label=label):
                self.assert_rejected(
                    fixture(boundary(layer, datatype, (300, -1100, 500, -900))),
                    f"forbidden overlap.*{label}",
                )

    def test_allows_edge_touch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source, output = root / "input.gds", root / "output.gds"
            source.write_bytes(fixture(boundary(66, 20, (650, -1250, 800, -750))))
            summary = inject_stack(
                input_gds=source, output_gds=output, report=root / "report.md",
                summary_json=root / "summary.json", cell="fan_smc_pin_3_flat",
                anchor=(400, -1000),
                expected_met5_box=(150, -2050, 650, 11650),
            )
            self.assertEqual(summary["forbidden_overlap_count"], 0)

    def test_rejects_same_input_output(self) -> None:
        self.assert_rejected(fixture(), "input and output.*different", same_path=True)

    def test_rejects_truncated_gds(self) -> None:
        self.assert_rejected(b"\x00\x10\x00\x00bad", "truncated|invalid GDS")
