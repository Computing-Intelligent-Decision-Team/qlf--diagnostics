#!/usr/bin/env python3
"""Tests for route-net label injection from MAGICAL .gr files."""

from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from add_net_labels_from_gr_to_gds import parse_gr_labels, write_labelled_gds
from inspect_gds_structure import parse_gds


def record(record_type: int, payload: bytes = b"", data_type: int = 0x00) -> bytes:
    return struct.pack(">HBB", len(payload) + 4, record_type, data_type) + payload


def ascii_payload(value: str) -> bytes:
    payload = value.encode("ascii")
    return payload if len(payload) % 2 == 0 else payload + b"\0"


def minimal_gds() -> bytes:
    return record(0x05) + record(0x06, ascii_payload("TOP"), 0x06) + record(0x07)


class AddNetLabelsFromGrToGdsTest(unittest.TestCase):
    def test_parse_gr_labels_maps_route_layers_to_sky130_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gr = Path(tmp) / "cell.gr"
            gr.write_text(
                "gridStep 200\n"
                "outn 31 1 6550 -50 6650 1450 0 0\n"
                "net027 39 2 40350 28840 53450 29050 0 0\n"
                "met2net 40 3 1 2 3 4 0 0\n",
                encoding="utf-8",
            )

            labels = parse_gr_labels(
                gr,
                nets={"outn", "net027", "met2net"},
                exclude_nets=set(),
                max_labels_per_net=2,
            )

        self.assertEqual([label.net for label in labels], ["outn", "net027", "met2net"])
        self.assertEqual(labels[0].label_layer_name, "li1.label")
        self.assertEqual(labels[0].label_layer, 67)
        self.assertEqual(labels[1].label_layer_name, "met1.label")
        self.assertEqual(labels[1].label_layer, 68)
        self.assertEqual(labels[2].label_layer_name, "met2.label")
        self.assertEqual(labels[2].label_layer, 69)

    def test_write_labelled_gds_inserts_route_net_text_only_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gr = root / "cell.gr"
            input_gds = root / "input.gds"
            output_gds = root / "output.gds"
            gr.write_text("outp 28 1 17950 1550 28250 1650 0 0\n", encoding="utf-8")
            input_gds.write_bytes(minimal_gds())
            labels = parse_gr_labels(
                gr,
                nets={"outp"},
                exclude_nets=set(),
                max_labels_per_net=1,
            )

            write_labelled_gds(
                input_gds=input_gds,
                output_gds=output_gds,
                labels=labels,
                cell_name="TOP",
                include_pin_shapes=False,
            )
            cells = parse_gds(output_gds)

        cell = cells["TOP"]
        self.assertEqual(cell.element_counts["TEXT"], 1)
        self.assertEqual(cell.element_counts.get("BOUNDARY", 0), 0)
        self.assertEqual(cell.texts[0].string, "outp")
        self.assertEqual(cell.texts[0].layer, 67)
        self.assertEqual(cell.texts[0].texttype, 5)


if __name__ == "__main__":
    unittest.main()
