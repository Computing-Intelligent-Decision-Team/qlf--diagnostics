#!/usr/bin/env python3
"""Tests for post-route local power stripe GDS injection."""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from add_local_power_stripe_to_gds import StripeSegment, parse_box, split_segments, write_gds
from inspect_gds_structure import parse_gds


def record(record_type: int, payload: bytes = b"", data_type: int = 0x00) -> bytes:
    return struct.pack(">HBB", len(payload) + 4, record_type, data_type) + payload


def ascii_payload(value: str) -> bytes:
    payload = value.encode("ascii")
    return payload if len(payload) % 2 == 0 else payload + b"\0"


def minimal_gds() -> bytes:
    return record(0x05) + record(0x06, ascii_payload("TOP"), 0x06) + record(0x07)


class AddLocalPowerStripeToGdsTest(unittest.TestCase):
    def test_parse_box_sorts_coordinates(self) -> None:
        self.assertEqual(parse_box("10,40,0,20"), (0, 20, 10, 40))

    def test_split_segments_removes_excluded_intervals(self) -> None:
        segments = split_segments(
            x1=0,
            y1=10,
            x2=100,
            y2=20,
            intervals=[(30, 40), (35, 70)],
            min_width=10,
        )

        self.assertEqual([segment.as_list() for segment in segments], [[0, 10, 30, 20], [70, 10, 100, 20]])

    def test_write_gds_inserts_drawing_pin_and_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_gds = root / "input.gds"
            output_gds = root / "output.gds"
            input_gds.write_bytes(minimal_gds())
            args = SimpleNamespace(
                drawing_layer=72,
                drawing_datatype=20,
                pin_layer=72,
                pin_datatype=16,
                label_layer=72,
                label_texttype=5,
            )

            write_gds(
                input_gds=input_gds,
                output_gds=output_gds,
                cell="TOP",
                net="vdda",
                segments=[StripeSegment(0, 10, 100, 20)],
                args=args,
            )

            cells = parse_gds(output_gds)
            cell = cells["TOP"]
            self.assertEqual(cell.layer_counts["72/20/BOUNDARY"], 1)
            self.assertEqual(cell.layer_counts["72/16/BOUNDARY"], 1)
            self.assertEqual(cell.layer_counts["72/5/TEXT"], 1)
            self.assertEqual(cell.texts[0].string, "vdda")


if __name__ == "__main__":
    unittest.main()
