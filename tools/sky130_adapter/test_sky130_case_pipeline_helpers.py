#!/usr/bin/env python3
"""Tests for generic Sky130 case pipeline helpers."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from sky130_case_pipeline_helpers import (
    check_power_nets,
    connectivity_lvs_projection,
    experimental_passive_remap,
    lvs_renames,
    pdk_line_ending_issues,
    subckt_ports,
    write_mos_projection_case,
)


class Sky130CasePipelineHelpersTest(unittest.TestCase):
    def test_check_power_nets_accepts_explicit_vdd_vss_arrays(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Path(tmpdir) / "case.json"
            config.write_text(
                '{"vddNetNames": ["VDD"], "vssNetNames": ["GND"]}\n',
                encoding="utf-8",
            )

            result = check_power_nets(config, "VDD", "GND")

        self.assertEqual(result.vdd_present, True)
        self.assertEqual(result.vss_present, True)
        self.assertEqual(result.missing, [])

    def test_check_power_nets_reports_missing_net(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Path(tmpdir) / "case.json"
            config.write_text(
                '{"vddNetNames": ["VDD"], "vssNetNames": []}\n',
                encoding="utf-8",
            )

            result = check_power_nets(config, "VDD", "GND")

        self.assertEqual(result.vdd_present, True)
        self.assertEqual(result.vss_present, False)
        self.assertEqual(result.missing, ["GND"])

    def test_subckt_ports_extracts_raw_magic_ports(self) -> None:
        ports = subckt_ports(".subckt ota_core_flat VINP VINM IB VDD VOUT GND")

        self.assertEqual(ports, "VINP VINM IB VDD VOUT GND")

    def test_lvs_projection_and_renames_parse_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Path(tmpdir) / "case.json"
            config.write_text(
                json.dumps(
                    {
                        "connectivityLvsProjection": "mos_only",
                        "lvsNetRenames": [
                            "a_1#=net1",
                            {"old": "a_2#", "new": "net2"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(connectivity_lvs_projection(config), "mos_only")
            self.assertEqual(lvs_renames(config), ["a_1#=net1", "a_2#=net2"])

    def test_experimental_passive_remap_defaults_off_and_parses_bool(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            default_config = Path(tmpdir) / "default.json"
            default_config.write_text("{}", encoding="utf-8")
            enabled_config = Path(tmpdir) / "enabled.json"
            enabled_config.write_text('{"experimentalPassiveRemap": true}', encoding="utf-8")

            self.assertFalse(experimental_passive_remap(default_config))
            self.assertTrue(experimental_passive_remap(enabled_config))

    def test_pdk_line_ending_issues_reports_crlf_and_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            techfile = root / "sky130.techfile"
            simple = root / "sky130.techfile.simple"
            config = root / "case.json"
            techfile.write_bytes(b"techLayers(\r\n)\r\n")
            simple.write_bytes(b"OD 1\n")
            config.write_text(
                json.dumps(
                    {
                        "techfile": "sky130.techfile",
                        "simple_tech_file": "sky130.techfile.simple",
                        "lef": "missing.lef",
                    }
                ),
                encoding="utf-8",
            )

            issues = pdk_line_ending_issues(config)

        self.assertEqual(len(issues), 2)
        self.assertTrue(any(issue.startswith("crlf\ttechfile\t") for issue in issues))
        self.assertTrue(any(issue.startswith("missing\tlef\t") for issue in issues))

    def test_write_mos_projection_case_drops_passives_and_rewrites_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_case = root / "examples" / "amp"
            tech_dir = root / "generated" / "sky130PDK_trial"
            projection_case = root / "generated" / "sky130_cases" / "amp_projection_case"
            source_case.mkdir(parents=True)
            tech_dir.mkdir(parents=True)
            for name in ("sky130.techfile", "sky130.techfile.simple", "sky130.lef"):
                (tech_dir / name).write_text("", encoding="utf-8")

            source = source_case / "amp.sp"
            source.write_text(
                ".subckt amp vdd vss out\n"
                "xm0 out out vss vss nch_mac l=1u w=1u\n"
                "xr0 n1 out vss rppolywo_m lr=4u wr=0.4u\n"
                "xc0 out n1 cfmom_2t nr=10\n"
                ".ends amp\n",
                encoding="utf-8",
            )
            config = source_case / "amp.json"
            config.write_text(
                json.dumps(
                    {
                        "hspice_netlist": "amp.sp",
                        "techfile": os.path.relpath(tech_dir / "sky130.techfile", source_case),
                        "simple_tech_file": os.path.relpath(
                            tech_dir / "sky130.techfile.simple", source_case
                        ),
                        "lef": os.path.relpath(tech_dir / "sky130.lef", source_case),
                        "connectivityLvsProjection": "mos_only",
                        "lvsNetRenames": ["a_1#=net1"],
                    }
                ),
                encoding="utf-8",
            )

            projection_netlist, projection_config, dropped = write_mos_projection_case(
                source,
                config,
                projection_case,
                "amp_mos_only.sp",
                "amp_mos_only.json",
            )

            self.assertEqual(dropped, 2)
            self.assertNotIn("rppolywo_m", projection_netlist.read_text(encoding="utf-8"))
            projected = json.loads(projection_config.read_text(encoding="utf-8"))
            self.assertEqual(projected["hspice_netlist"], "amp_mos_only.sp")
            self.assertNotIn("connectivityLvsProjection", projected)
            self.assertEqual(projected["lvsNetRenames"], ["a_1#=net1"])
            self.assertEqual(
                projected["techfile"],
                os.path.relpath(tech_dir / "sky130.techfile", projection_case).replace(os.sep, "/"),
            )


if __name__ == "__main__":
    unittest.main()
