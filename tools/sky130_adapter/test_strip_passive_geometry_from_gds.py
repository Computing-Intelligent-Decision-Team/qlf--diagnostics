from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from strip_passive_geometry_from_gds import load_strip_box_items, strip_gds


def record(record_type: int, payload: bytes = b"", data_type: int = 0x02) -> bytes:
    return struct.pack(">HBB", len(payload) + 4, record_type, data_type) + payload


def int2(value: int) -> bytes:
    return struct.pack(">h", value)


def xy(points: list[tuple[int, int]]) -> bytes:
    values: list[int] = []
    for x, y in points:
        values.extend([x, y])
    return struct.pack(f">{len(values)}l", *values)


def boundary(layer: int, datatype: int, x1: int, y1: int, x2: int, y2: int) -> bytes:
    points = [(x1, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1)]
    return b"".join(
        [
            record(0x08, b"", 0x00),
            record(0x0D, int2(layer)),
            record(0x0E, int2(datatype)),
            record(0x10, xy(points), 0x03),
            record(0x11, b"", 0x00),
        ]
    )


class StripPassiveGeometryFromGdsTest(unittest.TestCase):
    def test_load_strip_box_items_accepts_bbox_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "boxes.json"
            path.write_text(
                '{"boxes": [{"name": "vdd_overlap", "bbox": [1, 2, 3, 4]}]}\n',
                encoding="utf-8",
            )

            boxes = load_strip_box_items(path)

            self.assertEqual(
                boxes,
                [
                    {
                        "instance": "vdd_overlap",
                        "placement": None,
                        "local_bbox": None,
                        "strip_bbox": [1, 2, 3, 4],
                    }
                ],
            )

    def test_strip_gds_removes_elements_inside_box(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_gds = root / "input.gds"
            output_gds = root / "output.gds"
            input_gds.write_bytes(
                boundary(67, 20, 0, 0, 10, 10)
                + boundary(68, 20, 100, 100, 110, 110)
            )

            summary = strip_gds(
                input_gds=input_gds,
                output_gds=output_gds,
                strip_box_items=[
                    {
                        "instance": "xp0",
                        "strip_bbox": [-5, -5, 15, 15],
                    }
                ],
                mode="contains",
            )

            self.assertEqual(summary["stripped_element_count"], 1)
            self.assertEqual(summary["kept_element_count"], 1)
            self.assertEqual(summary["stripped_by_layer"], {"67/20/BOUNDARY": 1})
            self.assertIn(boundary(68, 20, 100, 100, 110, 110), output_gds.read_bytes())
            self.assertNotIn(boundary(67, 20, 0, 0, 10, 10), output_gds.read_bytes())

    def test_strip_gds_respects_selected_element_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_gds = root / "input.gds"
            output_gds = root / "output.gds"
            keep = boundary(67, 20, 0, 0, 10, 10)
            selected = boundary(68, 20, 20, 20, 30, 30)
            input_gds.write_bytes(keep + selected)

            summary = strip_gds(
                input_gds=input_gds,
                output_gds=output_gds,
                strip_box_items=[
                    {
                        "instance": "xp0",
                        "strip_bbox": [-5, -5, 35, 35],
                    }
                ],
                mode="contains",
                selected_elements={("68/20/BOUNDARY", (20, 20, 30, 30))},
            )

            self.assertEqual(summary["stripped_element_count"], 1)
            self.assertEqual(summary["selected_element_missing_count"], 0)
            self.assertIn(keep, output_gds.read_bytes())
            self.assertNotIn(selected, output_gds.read_bytes())

    def test_strip_gds_removes_layer_key_without_strip_boxes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_gds = root / "input.gds"
            output_gds = root / "output.gds"
            removed = boundary(83, 44, 0, 0, 10, 10)
            kept = boundary(67, 20, 20, 20, 30, 30)
            input_gds.write_bytes(removed + kept)

            summary = strip_gds(
                input_gds=input_gds,
                output_gds=output_gds,
                strip_box_items=[],
                mode="contains",
                strip_layer_keys={"83/44/BOUNDARY"},
            )

            output = output_gds.read_bytes()
            self.assertEqual(summary["stripped_element_count"], 1)
            self.assertEqual(summary["strip_layer_keys"], ["83/44/BOUNDARY"])
            self.assertNotIn(removed, output)
            self.assertIn(kept, output)

    def test_clip_crossing_splits_rectangular_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_gds = root / "input.gds"
            output_gds = root / "output.gds"
            original = boundary(72, 20, 0, 0, 100, 10)
            input_gds.write_bytes(original)

            summary = strip_gds(
                input_gds=input_gds,
                output_gds=output_gds,
                strip_box_items=[
                    {
                        "instance": "xr0",
                        "strip_bbox": [40, -5, 60, 15],
                    }
                ],
                mode="clip-crossing",
            )

            output = output_gds.read_bytes()
            self.assertEqual(summary["stripped_element_count"], 0)
            self.assertEqual(summary["clipped_element_count"], 1)
            self.assertEqual(summary["clipped_fragment_count"], 2)
            self.assertEqual(summary["clipped_by_layer"], {"72/20/BOUNDARY": 1})
            self.assertNotIn(original, output)
            self.assertIn(boundary(72, 20, 0, 0, 40, 10), output)
            self.assertIn(boundary(72, 20, 60, 0, 100, 10), output)

    def test_crop_crossing_keeps_only_overlap_with_strip_box(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_gds = root / "input.gds"
            output_gds = root / "output.gds"
            original = boundary(72, 20, 0, 0, 100, 10)
            input_gds.write_bytes(original)

            summary = strip_gds(
                input_gds=input_gds,
                output_gds=output_gds,
                strip_box_items=[
                    {
                        "instance": "xr0",
                        "strip_bbox": [40, -5, 60, 15],
                    }
                ],
                mode="crop-crossing",
            )

            output = output_gds.read_bytes()
            self.assertEqual(summary["stripped_element_count"], 0)
            self.assertEqual(summary["cropped_element_count"], 1)
            self.assertEqual(summary["cropped_fragment_count"], 1)
            self.assertEqual(summary["cropped_by_layer"], {"72/20/BOUNDARY": 1})
            self.assertNotIn(original, output)
            self.assertNotIn(boundary(72, 20, 0, 0, 40, 10), output)
            self.assertNotIn(boundary(72, 20, 60, 0, 100, 10), output)
            self.assertIn(boundary(72, 20, 40, 0, 60, 10), output)


if __name__ == "__main__":
    unittest.main()
