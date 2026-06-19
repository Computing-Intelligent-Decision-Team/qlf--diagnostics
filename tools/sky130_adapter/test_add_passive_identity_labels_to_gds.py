#!/usr/bin/env python3
"""Tests for passive identity label injection."""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from add_passive_identity_labels_to_gds import labels_from_identity, write_labelled_gds
from inspect_gds_structure import parse_gds


def record(record_type: int, payload: bytes = b"", data_type: int = 0x00) -> bytes:
    return struct.pack(">HBB", len(payload) + 4, record_type, data_type) + payload


def ascii_payload(value: str) -> bytes:
    payload = value.encode("ascii")
    return payload if len(payload) % 2 == 0 else payload + b"\0"


def minimal_gds() -> bytes:
    return record(0x05) + record(0x06, ascii_payload("TOP"), 0x06) + record(0x07)


class AddPassiveIdentityLabelsToGdsTest(unittest.TestCase):
    def test_labels_from_identity_uses_exact_pin_mapping(self) -> None:
        labels = labels_from_identity(
            {
                "instances": [
                    {
                        "source_instance": "xr0",
                        "terminals": [
                            {
                                "terminal": "net027",
                                "global_box": [19350, 33550, 19450, 34050],
                                "suggested_magic_label_layer": "li1",
                            },
                            {
                                "terminal": "gnda",
                                "global_box": None,
                                "suggested_magic_label_layer": None,
                            },
                        ],
                    }
                ]
            }
        )

        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0].terminal, "net027")
        self.assertEqual(labels[0].label_layer, 67)
        self.assertEqual(labels[0].texttype, 5)
        self.assertEqual(labels[0].pin_layer, 67)
        self.assertEqual(labels[0].pin_datatype, 16)

    def test_write_labelled_gds_inserts_text_and_pin_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_gds = root / "input.gds"
            output_gds = root / "output.gds"
            input_gds.write_bytes(minimal_gds())
            identity = {
                "instances": [
                    {
                        "source_instance": "xc0",
                        "terminals": [
                            {
                                "terminal": "outn",
                                "global_box": [350, 18350, 13450, 18560],
                                "suggested_magic_label_layer": "met1",
                            }
                        ],
                    }
                ]
            }
            labels = labels_from_identity(identity)

            write_labelled_gds(
                input_gds=input_gds,
                output_gds=output_gds,
                labels=labels,
                cell_name="TOP",
                include_pin_shapes=True,
            )
            cells = parse_gds(output_gds)

        cell = cells["TOP"]
        self.assertEqual(cell.element_counts["TEXT"], 1)
        self.assertEqual(cell.element_counts["BOUNDARY"], 1)
        self.assertEqual(cell.texts[0].string, "outn")
        self.assertEqual(cell.texts[0].layer, 68)
        self.assertEqual(cell.texts[0].texttype, 5)
        self.assertEqual(cell.layer_counts["68/16/BOUNDARY"], 1)


if __name__ == "__main__":
    unittest.main()
