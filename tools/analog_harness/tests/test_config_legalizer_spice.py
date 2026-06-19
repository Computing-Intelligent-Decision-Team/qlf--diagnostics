#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.analog_harness.config import load_harness_config
from tools.analog_harness.legalizer import SizingLegalizer
from tools.analog_harness.spice import SpiceCandidateCompiler, rewrite_instance_params


class ConfigLegalizerSpiceTest(unittest.TestCase):
    def test_default_config_loads_and_legalizes_initial_action(self) -> None:
        config = load_harness_config("tools/analog_harness/configs/smcnr_se_2st_amp.yaml")
        legalizer = SizingLegalizer(config.variables)

        values = legalizer.legalize_normalized(legalizer.initial_normalized())

        self.assertEqual(legalizer.action_dim, len(config.variables))
        self.assertEqual(values["diff_pair_w"], 7.52)
        self.assertEqual(values["second_stage_pmos_multi"], 10)
        self.assertIn("xm0", legalizer.device_assignments(values))

    def test_rewrite_instance_params_updates_grouped_devices(self) -> None:
        source = (
            ".subckt amp vdd vss in out\n"
            "xm0 out in vss vss nch_mac l=1u w=2u multi=1 nf=1\n"
            "xm1 out in vdd vdd pch_mac l=1u w=2u multi=1 nf=1\n"
            ".ends amp\n"
        )
        rewritten = rewrite_instance_params(
            source,
            {"xm0": {"w": 3.25, "multi": 4}},
            {("xm0", "w"): "u"},
        )

        self.assertIn("xm0 out in vss vss nch_mac l=1u w=3.25u multi=4 nf=1", rewritten)
        self.assertIn("xm1 out in vdd vdd", rewritten)

    def test_compile_writes_candidate_netlist_and_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source.sp"
            source.write_text(
                ".subckt amp vdd vss in out\n"
                "xm0 out in vss vss nch_mac l=1u w=2u multi=1 nf=1\n"
                ".ends amp\n",
                encoding="utf-8",
            )
            tech = root / "tech"
            tech.mkdir()
            for name in ("sky130.techfile", "sky130.techfile.simple", "sky130.lef"):
                (tech / name).write_text("", encoding="utf-8")
            source_config = root / "source.json"
            source_config.write_text(
                json.dumps(
                    {
                        "hspice_netlist": "source.sp",
                        "techfile": "tech/sky130.techfile",
                        "simple_tech_file": "tech/sky130.techfile.simple",
                        "lef": "tech/sky130.lef",
                    }
                ),
                encoding="utf-8",
            )
            harness_config = root / "harness.yaml"
            harness_config.write_text(
                f"""
design_id: test_amp
top_cell: amp
paths:
  source_netlist: {source}
  source_config: {source_config}
  runs_dir: {root / "runs"}
ports: {{vdd: vdd, vss: vss, output: out}}
sizing_variables:
  - {{name: m0_w, kind: device, instances: [xm0], param: w, min: 1, max: 4, init: 2, step: 0.5, unit: u}}
""",
                encoding="utf-8",
            )
            config = load_harness_config(harness_config)
            legalizer = SizingLegalizer(config.variables)
            compiled = SpiceCandidateCompiler(config, legalizer).compile(
                "cand_0001",
                {"m0_w": 3.0},
                [0.0],
            )

            self.assertIn("w=3u", compiled.netlist_path.read_text(encoding="utf-8"))
            generated_config = json.loads(compiled.config_path.read_text(encoding="utf-8"))
            self.assertEqual(generated_config["hspice_netlist"], "amp_cand_0001.sp")
            self.assertEqual(generated_config["resultDir"], "./")


if __name__ == "__main__":
    unittest.main()
