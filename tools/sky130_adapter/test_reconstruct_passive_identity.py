#!/usr/bin/env python3
"""Tests for passive identity reconstruction from MAGICAL intermediates."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reconstruct_passive_identity import build_summary, parse_gr_file, parse_pin_file, parse_placement_log


class ReconstructPassiveIdentityTest(unittest.TestCase):
    def test_reconstructs_passive_pins_from_pin_gr_and_placement(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "amp.sp"
            source.write_text(
                ".subckt AMP vdda gnda outn vout\n"
                "xr0 net027 vout gnda rppolywo_m lr=4e-6\n"
                "xc0 outn net027 cfmom_2t nr=94\n"
                ".ends AMP\n",
                encoding="utf-8",
            )
            pin_file = root / "AMP.pin"
            pin_file.write_text(
                "2\n"
                "AMP_xr0 3\n"
                "4550 19350 4650 19850\n"
                "-50 -50 50 450\n"
                "-1\n"
                "AMP_xc0 2\n"
                "-50 -50 13050 160\n"
                "-50 10440 13050 10650\n",
                encoding="utf-8",
            )
            gr_file = root / "AMP.gr"
            gr_file.write_text(
                "gridStep 200\n"
                "net027 29 1 19350 33550 19450 34050 0 0\n"
                "vout 18 1 14750 14150 14850 14650 0 0\n"
                "outn 25 2 350 18350 13450 18560 0 0\n"
                "net027 30 2 350 28840 13450 29050 0 0\n",
                encoding="utf-8",
            )
            log = root / "run.log"
            log.write_text(
                "node  AMP_xr0 14800 14200\n"
                "node  AMP_xc0 400 18400\n",
                encoding="utf-8",
            )

            summary = build_summary(
                source_netlist=source,
                pin_file=pin_file,
                gr_file=gr_file,
                placement_log=log,
                top_cell="AMP",
                extracted_netlist=None,
            )

        self.assertEqual(summary["status"], "source_passive_pin_identity_reconstructed_from_magical_intermediates")
        self.assertEqual(summary["source_passive_count"], 2)
        self.assertEqual(summary["source_passive_pin_count"], 5)
        self.assertEqual(summary["source_passive_pins_with_geometry"], 4)
        self.assertEqual(summary["source_passive_pins_without_geometry"], 1)
        self.assertEqual(summary["source_passive_pin_exact_route_matches"], 4)
        self.assertEqual(summary["source_passive_pin_missing_route_matches"], 0)
        self.assertEqual(summary["source_passive_label_injection_candidates"], 4)
        xr0 = summary["instances"][0]
        self.assertEqual(xr0["placement_origin"], [14800, 14200])
        self.assertEqual(xr0["terminals"][0]["global_box"], [19350, 33550, 19450, 34050])
        self.assertEqual(xr0["terminals"][0]["match_status"], "exact")
        self.assertEqual(xr0["terminals"][0]["suggested_magic_label_layer"], "li1")
        self.assertEqual(
            xr0["terminals"][0]["suggested_magic_label_command"],
            "box 19350 33550 19450 34050; label net027 center li1",
        )
        self.assertEqual(xr0["terminals"][2]["match_status"], "no_pin_geometry")

    def test_individual_parsers_accept_magical_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pin_file = root / "AMP.pin"
            pin_file.write_text("1\nAMP_xr0 1\n-50 -50 50 450\n", encoding="utf-8")
            gr_file = root / "AMP.gr"
            gr_file.write_text("gridStep 200\nvout 1 1 0 0 100 100 0 0\n", encoding="utf-8")
            log = root / "run.log"
            log.write_text("node  AMP_xr0 14800 14200\n", encoding="utf-8")

            pins = parse_pin_file(pin_file)
            routes = parse_gr_file(gr_file)
            placements = parse_placement_log(log)

        self.assertEqual(pins["AMP_xr0"][0].local_box.as_list(), [-50, -50, 50, 450])
        self.assertEqual(routes[0].net, "vout")
        self.assertEqual(placements["AMP_xr0"], (14800, 14200))


if __name__ == "__main__":
    unittest.main()
