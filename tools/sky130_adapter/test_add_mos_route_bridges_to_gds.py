#!/usr/bin/env python3
"""Tests for MOS route bridge GDS injection."""

from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from add_mos_route_bridges_to_gds import build_bridge_plan, write_bridged_gds
from inspect_gds_structure import parse_gds


def record(record_type: int, payload: bytes = b"", data_type: int = 0x00) -> bytes:
    return struct.pack(">HBB", len(payload) + 4, record_type, data_type) + payload


def ascii_payload(value: str) -> bytes:
    payload = value.encode("ascii")
    return payload if len(payload) % 2 == 0 else payload + b"\0"


def minimal_gds(cell: str) -> bytes:
    return record(0x05) + record(0x06, ascii_payload(cell), 0x06) + record(0x07)


class AddMosRouteBridgesToGdsTest(unittest.TestCase):
    def test_builds_and_writes_bridge_from_split_net_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "amp.spice"
            pin_file = root / "AMP.pin"
            gr_file = root / "AMP.gr"
            placement = root / "run_AMP_trial.log"
            input_gds = root / "input.gds"
            output_gds = root / "output.gds"
            source.write_text(
                ".subckt AMP vdda gnda sig out\n"
                "xm0 sig gate vdda vdda pch_mac l=1u w=1u\n"
                ".ends AMP\n",
                encoding="utf-8",
            )
            pin_file.write_text(
                "1\n"
                "AMP_xm0 4\n"
                "0 0 100 100\n"
                "0 200 400 300\n"
                "400 0 500 100\n"
                "-1\n",
                encoding="utf-8",
            )
            gr_file.write_text("sig 1 1 1000 1200 1400 1300\n", encoding="utf-8")
            placement.write_text("node AMP_xm0 1000 1000\n", encoding="utf-8")
            input_gds.write_bytes(minimal_gds("AMP_flat"))
            summary = {
                "split_net_repair_suggestions": [
                    {
                        "reference_nets": ["sig"],
                        "candidate_net_groups": [
                            {"candidate_nets": ["sig", "a_1_2#"], "combined_roles": {"pfet.drain": 1}}
                        ],
                    }
                ]
            }

            bridges = build_bridge_plan(
                source_netlist=source,
                pin_file=pin_file,
                gr_file=gr_file,
                placement_log=placement,
                mos_connectivity_summary=summary,
                top_cell="AMP",
                max_gap_dbu=200,
            )

            self.assertEqual(len(bridges), 1)
            self.assertEqual(bridges[0].bridge_box.as_list(), [1000, 1100, 1100, 1200])
            self.assertEqual(bridges[0].net, "sig")

            write_bridged_gds(input_gds=input_gds, output_gds=output_gds, cell="AMP_flat", bridges=bridges)

            cells = parse_gds(output_gds)
            cell = cells["AMP_flat"]
            self.assertEqual(cell.layer_counts["67/20/BOUNDARY"], 1)
            self.assertEqual(cell.layer_counts["67/16/BOUNDARY"], 1)
            self.assertEqual(cell.layer_counts["67/5/TEXT"], 1)
            self.assertEqual(cell.texts[0].string, "sig")


if __name__ == "__main__":
    unittest.main()
