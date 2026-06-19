from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from probe_gds_element_short_subsets import (
    build_probe_sets,
    has_short,
    parse_magic_port_shorts,
    parse_wsl_distro_lines,
    render_report,
    resolve_wsl_distro,
)


class ProbeGdsElementShortSubsetsTest(unittest.TestCase):
    def test_build_probe_sets_enumerates_bounded_combinations(self) -> None:
        elements = [
            {"probe_id": "e0", "layer_key": "67/20/BOUNDARY", "bbox": [0, 0, 1, 1]},
            {"probe_id": "e1", "layer_key": "68/20/BOUNDARY", "bbox": [1, 1, 2, 2]},
            {"probe_id": "e2", "layer_key": "72/20/BOUNDARY", "bbox": [2, 2, 3, 3]},
        ]

        probes = build_probe_sets(
            elements,
            max_combination_size=2,
            run_baseline=True,
            run_all_elements=True,
        )

        self.assertEqual(probes[0]["name"], "baseline_no_strip")
        self.assertEqual([probe["kind"] for probe in probes].count("size_1"), 3)
        self.assertEqual([probe["kind"] for probe in probes].count("size_2"), 3)
        self.assertEqual(probes[-1]["kind"], "all_elements")

    def test_parse_magic_port_shorts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "magic.log"
            log.write_text(
                'Warning:  Ports "gnda" and "vdda" are electrically shorted.\n',
                encoding="utf-8",
            )

            shorts = parse_magic_port_shorts(log)

            self.assertEqual(shorts, [{"port_a": "gnda", "port_b": "vdda"}])
            self.assertTrue(has_short(shorts, "vdda", "gnda"))
            self.assertFalse(has_short(shorts, "vdda", "vin"))

    def test_render_report_includes_strip_mode_and_geometry_counts(self) -> None:
        report = render_report(
            {
                "input_gds": "input.gds",
                "vdd": "vdda",
                "vss": "gnda",
                "strip_mode": "clip-crossing",
                "candidate_element_count": 1,
                "probe_count": 1,
                "minimal_short_free_size": 1,
                "minimal_short_free_sets": [],
                "results": [
                    {
                        "name": "combo_1_00",
                        "stripped_element_count": 0,
                        "clipped_element_count": 1,
                        "cropped_element_count": 0,
                        "magic_supply_short_present": False,
                        "mos_connectivity_status": "pass",
                    }
                ],
            }
        )

        self.assertIn("Strip mode: `clip-crossing`", report)
        self.assertIn("| `combo_1_00` | 0 | 1 | 0 | `False` | `pass` |", report)

    def test_parse_wsl_distro_lines_filters_table_noise(self) -> None:
        text = "\x00*\x00 \x00d\x00o\x00c\x00k\x00e\x00r\x00-\x00d\x00e\x00s\x00k\x00t\x00o\x00p\x00\n\x00U\x00b\x00u\x00n\x00t\x00u\x00-\x002\x004\x00.\x000\x004\x00\n"

        self.assertEqual(parse_wsl_distro_lines(text), ["docker-desktop", "Ubuntu-24.04"])

    def test_resolve_wsl_distro_prefers_non_docker_distribution(self) -> None:
        completed = type("Completed", (), {"returncode": 0, "stdout": "docker-desktop\nUbuntu-24.04\n"})()

        with patch("probe_gds_element_short_subsets.sys.platform", "win32"), patch(
            "probe_gds_element_short_subsets.shutil.which", return_value="wsl"
        ), patch("probe_gds_element_short_subsets.subprocess.run", return_value=completed):
            self.assertEqual(resolve_wsl_distro(None), "Ubuntu-24.04")


if __name__ == "__main__":
    unittest.main()
