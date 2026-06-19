#!/usr/bin/env python3
from __future__ import annotations

import json
import struct
import tempfile
import unittest
from importlib import import_module
from pathlib import Path


try:
    repl = import_module("replace_native_cap_in_flat_gds")
    strip = import_module("strip_passive_geometry_from_gds")
except ModuleNotFoundError:
    repl = import_module("tools.sky130_adapter.replace_native_cap_in_flat_gds")
    strip = import_module("tools.sky130_adapter.strip_passive_geometry_from_gds")


def int2_record(record_type: int, value: int) -> bytes:
    return repl.gds_record(record_type, 0x02, struct.pack(">h", value))


def xy_record(points: list[tuple[int, int]]) -> bytes:
    flat: list[int] = []
    for x, y in points:
        flat.extend([x, y])
    return repl.gds_record(0x10, 0x03, struct.pack(f">{len(flat)}i", *flat))


def string_record(value: str) -> bytes:
    return repl.gds_record(0x19, 0x06, repl._string_payload(value))


def strname(name: str) -> bytes:
    return repl.gds_record(0x06, 0x06, repl._string_payload(name))


def endstr() -> bytes:
    return repl.gds_record(0x07, 0x00)


def boundary(layer: int, datatype: int, box: list[int]) -> bytes:
    x1, y1, x2, y2 = box
    points = [(x1, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1)]
    return b"".join(
        [
            repl.gds_record(0x08, 0x00),
            int2_record(0x0D, layer),
            int2_record(0x0E, datatype),
            xy_record(points),
            repl.gds_record(0x11, 0x00),
        ]
    )


def text(layer: int, texttype: int, point: tuple[int, int], label: str) -> bytes:
    return b"".join(
        [
            repl.gds_record(0x0C, 0x00),
            int2_record(0x0D, layer),
            int2_record(0x16, texttype),
            xy_record([point]),
            string_record(label),
            repl.gds_record(0x11, 0x00),
        ]
    )


def fake_gds(cell: str, elements: list[bytes]) -> bytes:
    return b"".join([strname(cell), *elements, endstr()])


class ReplaceNativeCapInFlatGdsTest(unittest.TestCase):
    def test_transform_element_raw_rewrites_xy_and_labels(self) -> None:
        raw = text(71, 5, (1, 2), "C1")
        transformed = repl.transform_element_raw(raw, dx=10, dy=20, label_map={"C1": "outn"})

        element = strip.parse_element(transformed, "TEXT")

        self.assertEqual(element.xy, [(11, 22)])
        self.assertEqual(element.string, "outn")

    def test_replace_preserves_terminals_removes_old_cap_and_inserts_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_gds = tmp_path / "input.gds"
            replacement_gds = tmp_path / "replacement.gds"
            output_gds = tmp_path / "output.gds"
            identity = tmp_path / "identity.json"
            structure = tmp_path / "structure.json"
            report = tmp_path / "report.md"
            summary_json = tmp_path / "summary.json"

            input_gds.write_bytes(
                fake_gds(
                    "top",
                    [
                        boundary(68, 20, [0, 0, 100, 10]),
                        boundary(68, 16, [0, 0, 100, 10]),
                        text(68, 5, (50, 5), "outn"),
                        boundary(71, 20, [0, 10, 100, 90]),
                    ],
                )
            )
            replacement_gds.write_bytes(
                fake_gds(
                    "cap",
                    [
                        boundary(71, 20, [-10, -10, 10, 10]),
                        text(71, 5, (-5, 0), "C1"),
                        text(71, 5, (5, 0), "C2"),
                    ],
                )
            )
            identity.write_text(
                json.dumps(
                    {
                        "instances": [
                            {
                                "source_instance": "xc0",
                                "model": "cfmom_2t",
                                "placement_origin": [0, 0],
                                "terminals": [
                                    {
                                        "terminal": "outn",
                                        "global_box": [0, 0, 100, 10],
                                        "matched_routes": [{"layer": 2}],
                                    },
                                    {
                                        "terminal": "net027",
                                        "global_box": [0, 90, 100, 100],
                                        "matched_routes": [{"layer": 2}],
                                    },
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            structure.write_text(
                json.dumps({"top_gds": {"cells": [{"bbox": [0, 0, 100, 100]}]}}),
                encoding="utf-8",
            )

            summary = repl.replace_native_cap(
                input_gds=input_gds,
                replacement_gds=replacement_gds,
                output_gds=output_gds,
                identity_summary=identity,
                source_gds_structure_json=structure,
                cell="top",
                source_instance="xc0",
                label_map_overrides=[],
            )
            summary_json.write_text(json.dumps(summary), encoding="utf-8")
            repl.write_report(report, summary)

            elements = [unit for unit in strip.iter_gds_units(output_gds.read_bytes()) if not isinstance(unit, bytes)]
            layer_boxes = [(element.layer_key, element.bbox.as_list() if element.bbox else None) for element in elements]
            labels = sorted(element.string for element in elements if element.element_type == "TEXT")

            self.assertEqual(summary["status"], "native_cap_replacement_merged")
            self.assertEqual(summary["removed_element_count"], 1)
            self.assertEqual(summary["preserved_terminal_element_count"], 3)
            self.assertIn(("68/20/BOUNDARY", [0, 0, 100, 10]), layer_boxes)
            self.assertNotIn(("71/20/BOUNDARY", [0, 10, 100, 90]), layer_boxes)
            self.assertIn(("71/20/BOUNDARY", [40, 40, 60, 60]), layer_boxes)
            self.assertEqual(labels, ["net027", "outn", "outn"])


if __name__ == "__main__":
    unittest.main()
