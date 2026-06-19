#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import unittest
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

try:
    pipeline = import_module("run_sky130_case_pipeline")
except ModuleNotFoundError:
    pipeline = import_module("tools.sky130_adapter.run_sky130_case_pipeline")

ic_netgen_lvs_path = pipeline.ic_netgen_lvs_path


class RunSky130CasePipelineTest(unittest.TestCase):
    def test_ic_netgen_lvs_path_rejects_meshing_netgen(self) -> None:
        completed = SimpleNamespace(returncode=0, stdout="NETGEN-6.2.2401\nIncluding OpenCascade\n")

        def fake_which(name: str) -> str | None:
            return "/usr/bin/netgen" if name == "netgen" else None

        with patch.object(pipeline.shutil, "which", side_effect=fake_which), patch.object(
            pipeline.subprocess, "run", return_value=completed
        ):
            self.assertIsNone(ic_netgen_lvs_path())

    def test_ic_netgen_lvs_path_accepts_netgen_lvs_wrapper(self) -> None:
        def fake_which(name: str) -> str | None:
            return "/usr/bin/netgen-lvs" if name == "netgen-lvs" else None

        with patch.object(pipeline.shutil, "which", side_effect=fake_which), patch.object(
            pipeline.subprocess,
            "run",
            side_effect=AssertionError("netgen-lvs wrapper should not need probing"),
        ):
            self.assertEqual(ic_netgen_lvs_path(), "/usr/bin/netgen-lvs")

    def test_ic_netgen_lvs_path_accepts_ic_netgen_binary(self) -> None:
        completed = SimpleNamespace(returncode=0, stdout="Netgen 1.5.133 compiled on Thu Dec 1\n")

        def fake_which(name: str) -> str | None:
            return "/usr/local/bin/netgen" if name == "netgen" else None

        with patch.object(pipeline.shutil, "which", side_effect=fake_which), patch.object(
            pipeline.subprocess, "run", return_value=completed
        ):
            self.assertEqual(ic_netgen_lvs_path(), "/usr/local/bin/netgen")

    def test_ic_netgen_lvs_path_handles_probe_timeout(self) -> None:
        def fake_which(name: str) -> str | None:
            return "/usr/local/bin/netgen" if name == "netgen" else None

        with patch.object(pipeline.shutil, "which", side_effect=fake_which), patch.object(
            pipeline.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired("/usr/local/bin/netgen", 10),
        ):
            self.assertIsNone(ic_netgen_lvs_path())


if __name__ == "__main__":
    unittest.main()
