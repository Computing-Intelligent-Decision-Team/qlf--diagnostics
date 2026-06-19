#!/usr/bin/env python3
"""Tests for passive abstraction readiness diagnostics."""

from __future__ import annotations

import unittest

from analyze_passive_abstraction import (
    analyze,
    parse_ext_devres,
    parse_ext_passive_rsubckts,
    parse_capacitance_ff,
    parse_extracted_capacitors,
    parse_magic_port_shorts,
    render_abstraction_packet,
    render_candidate_netlist,
)


class AnalyzePassiveAbstractionTest(unittest.TestCase):
    def test_parse_extracted_capacitors_skips_non_cap_devices(self) -> None:
        capacitors = parse_extracted_capacitors(
            [
                "R1 a b sky130_fd_pr__res_generic_m1 w=1 l=2\n",
                "C7 outn net027 0.1f\n",
                ".ends\n",
            ]
        )

        self.assertEqual(capacitors, [{"instance": "C7", "terminals": ["outn", "net027"], "value": "0.1f"}])

    def test_parse_capacitance_ff_converts_common_suffixes(self) -> None:
        self.assertAlmostEqual(parse_capacitance_ff("0.12862p") or 0.0, 128.62)
        self.assertAlmostEqual(parse_capacitance_ff("0.31275f") or 0.0, 0.31275)
        self.assertAlmostEqual(parse_capacitance_ff("-0"), 0.0)

    def test_abstraction_readiness_reports_real_partial_labelled_case(self) -> None:
        source = [
            ".subckt amp vdda gnda vin vip ibias vout\n",
            "xr0 net027 vout gnda rppolywo_m lr=4e-6\n",
            "xc0 outn net027 cfmom_2t nr=94\n",
            ".ends amp\n",
        ]
        extracted = [
            ".subckt amp_flat vdda vin vip ibias vout net027 outn net027_uq0\n",
            "R1 net027_uq0 net027 sky130_fd_pr__res_generic_m1 w=0.12 l=0.06\n",
            "R5 outn vdda sky130_fd_pr__res_generic_m1 w=0.12 l=0.06\n",
            "C10 outn vout 0.2f\n",
            ".ends\n",
        ]
        identity = {
            "instances": [
                {
                    "source_instance": "xr0",
                    "terminals": [
                        {"terminal": "net027", "match_status": "exact"},
                        {"terminal": "vout", "match_status": "exact"},
                        {"terminal": "gnda", "match_status": "no_pin_geometry"},
                    ],
                },
                {
                    "source_instance": "xc0",
                    "terminals": [
                        {"terminal": "outn", "match_status": "exact", "global_box": [350, 18350, 13450, 18560]},
                        {"terminal": "net027", "match_status": "exact", "global_box": [350, 28840, 13450, 29050]},
                    ],
                },
            ]
        }

        summary = analyze(
            source_lines=source,
            extracted_lines=extracted,
            magic_shorts=[{"port_a": "gnda", "port_b": "vdda"}],
            identity=identity,
            ext_devres=[
                {"model": "sky130_fd_pr__res_generic_m1", "ext_x": 70, "ext_y": 3670, "gds_x": 350, "gds_y": 18350},
                {"model": "sky130_fd_pr__res_generic_m1", "ext_x": 70, "ext_y": 5768, "gds_x": 350, "gds_y": 28840},
            ],
        )

        self.assertEqual(summary["status"], "partial_passive_abstraction_readiness")
        self.assertEqual(summary["source_passives_candidate_for_abstraction"], 0)
        xr0 = summary["source_passives"][0]
        xc0 = summary["source_passives"][1]
        self.assertEqual(xr0["source_instance"], "xr0")
        self.assertEqual(xr0["status"], "partial_terminal_recovery")
        self.assertIn("vout", xr0["covered_terminals"])
        self.assertIn("vout", xr0["missing_from_expected_kind_devices"])
        self.assertIn("body_or_substrate_pin_has_no_magical_geometry:gnda", xr0["blockers"])
        self.assertIn("missing_expected_kind_terminals:vout", xr0["blockers"])
        self.assertIn("no_extracted_resistor_between_expected_electrical_terminals", xr0["blockers"])
        self.assertIn("no_coordinate_matched_extracted_resistor_for_source_instance", xr0["blockers"])
        self.assertEqual(xr0["coordinate_matched_devres_count"], 0)
        self.assertEqual(xc0["source_instance"], "xc0")
        self.assertEqual(xc0["status"], "partial_terminal_recovery")
        self.assertEqual(xc0["coordinate_matched_devres_count"], 2)
        self.assertIn("coordinate_matched_devices_are_resistor_markers_not_capacitor", xc0["blockers"])
        self.assertIn("no_extracted_capacitor_between_expected_electrical_terminals", xc0["blockers"])
        self.assertIn(
            "source_capacitor_touches_extracted_resistor_markers_not_a_capacitor_device",
            xc0["blockers"],
        )

    def test_parse_ext_devres_reads_magic_coordinates(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            ext = Path(tmpdir) / "amp.ext"
            ext.write_text(
                'device devres sky130_fd_pr__res_generic_m1 70 3670 71 3671 12 24 "m1" 0 0 "outn" 1 1 "gnda" 1 1\n',
                encoding="utf-8",
            )

            devres = parse_ext_devres(ext)

        self.assertEqual(devres[0]["model"], "sky130_fd_pr__res_generic_m1")
        self.assertEqual(devres[0]["ext_x"], 70)
        self.assertEqual(devres[0]["gds_y"], 18350)

    def test_parse_ext_passive_rsubckts_reads_poly_resistor_coordinates(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            ext = Path(tmpdir) / "amp.ext"
            ext.write_text(
                'device rsubckt sky130_fd_pr__res_xhigh_po 3021 2830 3022 2831 l=768 w=80 "gnda" "a" 0 0 "vout" 80 1,1 "b" 80 1,1\n',
                encoding="utf-8",
            )

            devices = parse_ext_passive_rsubckts(ext)

        self.assertEqual(devices[0]["model"], "sky130_fd_pr__res_xhigh_po")
        self.assertEqual(devices[0]["ext_x"], 3021)
        self.assertEqual(devices[0]["gds_y"], 14150)

    def test_abstraction_readiness_uses_ext_rsubckt_resistor_ownership(self) -> None:
        source = [
            ".subckt amp gnda net027 vout\n",
            "xr0 net027 vout gnda rppolywo_m lr=4e-6\n",
            ".ends amp\n",
        ]
        extracted = [
            ".subckt amp_flat gnda net027 vout\n",
            "X20 vout a_3789_2830# vdda sky130_fd_pr__res_xhigh_po w=0.4 l=4\n",
            "X28 a_2945_6600# net027 vdda sky130_fd_pr__res_xhigh_po w=0.4 l=4\n",
            ".ends\n",
        ]
        identity = {
            "instances": [
                {
                    "source_instance": "xr0",
                    "terminals": [
                        {
                            "terminal": "vout",
                            "match_status": "exact",
                            "global_box": [14750, 14150, 14850, 14650],
                        },
                        {
                            "terminal": "net027",
                            "match_status": "exact",
                            "global_box": [19350, 33550, 19450, 34050],
                        },
                        {"terminal": "gnda", "match_status": "no_pin_geometry"},
                    ],
                }
            ]
        }

        summary = analyze(
            source_lines=source,
            extracted_lines=extracted,
            magic_shorts=[{"port_a": "gnda", "port_b": "vdda"}],
            identity=identity,
            ext_passive_rsubckts=[
                {
                    "model": "sky130_fd_pr__res_xhigh_po",
                    "ext_x": 3021,
                    "ext_y": 2830,
                    "gds_x": 15105,
                    "gds_y": 14150,
                }
            ],
        )

        xr0 = summary["source_passives"][0]
        self.assertEqual(xr0["coordinate_matched_ext_resistor_count"], 1)
        self.assertNotIn("no_coordinate_matched_extracted_resistor_for_source_instance", xr0["blockers"])
        self.assertIn("no_extracted_resistor_between_expected_electrical_terminals", xr0["blockers"])

    def test_abstraction_readiness_detects_segmented_resistor_chain(self) -> None:
        source = [
            ".subckt amp gnda net027 vout\n",
            "xr0 net027 vout gnda rppolywo_m lr=4e-6\n",
            ".ends amp\n",
        ]
        extracted = [
            ".subckt amp_flat gnda net027 vout\n",
            "X1 vout n1 vdda sky130_fd_pr__res_xhigh_po w=0.4 l=4\n",
            "X2 n1 net027 vdda sky130_fd_pr__res_xhigh_po w=0.4 l=4\n",
            ".ends\n",
        ]
        identity = {
            "instances": [
                {
                    "source_instance": "xr0",
                    "terminals": [
                        {"terminal": "vout", "match_status": "exact", "global_box": [0, 0, 10, 10]},
                        {"terminal": "net027", "match_status": "exact", "global_box": [100, 0, 110, 10]},
                        {"terminal": "gnda", "match_status": "no_pin_geometry"},
                    ],
                }
            ]
        }

        summary = analyze(
            source_lines=source,
            extracted_lines=extracted,
            magic_shorts=[{"port_a": "gnda", "port_b": "vdda"}],
            identity=identity,
        )

        xr0 = summary["source_passives"][0]
        self.assertEqual(summary["source_resistors_with_segmented_chain"], 1)
        self.assertEqual(summary["source_level_abstraction_candidate_count"], 1)
        self.assertTrue(xr0["segmented_expected_resistor_chain_present"])
        self.assertEqual(xr0["segmented_expected_resistor_chain"]["device_instances"], ["X2", "X1"])
        self.assertIn("source_resistor_requires_segmented_chain_abstraction", xr0["blockers"])
        self.assertNotIn("no_extracted_resistor_between_expected_electrical_terminals", xr0["blockers"])
        self.assertIn("body_or_substrate_pin_has_no_magical_geometry:gnda", xr0["blockers"])
        candidate = xr0["source_level_abstraction_candidate"]
        self.assertEqual(candidate["candidate_status"], "candidate_requires_review")
        self.assertEqual(candidate["source_equivalent_spice"], "xr0 net027 vout gnda rppolywo_m")
        self.assertIn("body_or_substrate_pin_has_no_magical_geometry:gnda", candidate["unresolved"])

        fragment = render_candidate_netlist(summary)
        self.assertIn("Diagnostic artifact only", fragment)
        self.assertIn("candidate_status=candidate_requires_review", fragment)
        self.assertIn("xr0 net027 vout gnda rppolywo_m", fragment)

    def test_abstraction_readiness_detects_capacitor_plate_coupling_candidate(self) -> None:
        source = [
            ".subckt amp outn net027\n",
            "xc0 outn net027 cfmom_2t nr=94\n",
            ".ends amp\n",
        ]
        extracted = [
            ".subckt amp_flat outn net027\n",
            "C1 m1_70_3670# m1_70_5768# 0.12862p\n",
            "C2 outn m1_70_3670# 0.01f\n",
            "C3 net027 m1_70_5768# 0.02f\n",
            ".ends\n",
        ]
        identity = {
            "instances": [
                {
                    "source_instance": "xc0",
                    "terminals": [
                        {"terminal": "outn", "match_status": "exact", "global_box": [350, 18350, 13450, 18560]},
                        {"terminal": "net027", "match_status": "exact", "global_box": [350, 28840, 13450, 29050]},
                    ],
                }
            ]
        }

        summary = analyze(
            source_lines=source,
            extracted_lines=extracted,
            magic_shorts=[],
            identity=identity,
            ext_devres=[
                {
                    "model": "sky130_fd_pr__res_generic_m1",
                    "ext_x": 70,
                    "ext_y": 3670,
                    "gds_x": 350,
                    "gds_y": 18350,
                    "line": 'device devres sky130_fd_pr__res_generic_m1 70 3670 71 3671 12 24 "m1_70_3670#" 0 0 "outn" 1 1',
                },
                {
                    "model": "sky130_fd_pr__res_generic_m1",
                    "ext_x": 70,
                    "ext_y": 5768,
                    "gds_x": 350,
                    "gds_y": 28840,
                    "line": 'device devres sky130_fd_pr__res_generic_m1 70 5768 71 5769 12 24 "m1_70_5768#" 0 0 "net027" 1 1',
                },
            ],
        )

        xc0 = summary["source_passives"][0]
        self.assertEqual(summary["source_capacitors_with_plate_coupling_evidence"], 1)
        self.assertEqual(summary["source_level_abstraction_candidate_count"], 1)
        self.assertTrue(xc0["capacitor_plate_coupling_present"])
        self.assertAlmostEqual(xc0["capacitor_plate_coupling"]["coupling_capacitance_ff"], 128.62)
        self.assertIn("source_capacitor_requires_plate_coupling_abstraction", xc0["blockers"])
        self.assertNotIn("no_extracted_capacitor_between_expected_electrical_terminals", xc0["blockers"])
        candidate = xc0["source_level_abstraction_candidate"]
        self.assertEqual(candidate["candidate_type"], "plate_coupling_capacitor_source_equivalent")
        self.assertEqual(candidate["source_equivalent_spice"], "xc0 outn net027 cfmom_2t")
        fragment = render_candidate_netlist(summary)
        self.assertIn("coupling_capacitance_ff=128.62", fragment)
        self.assertIn("xc0 outn net027 cfmom_2t", fragment)
        packet = render_abstraction_packet(summary)
        self.assertEqual(packet["schema_version"], "passive_abstraction_packet.v1")
        self.assertEqual(packet["proof_status"], "candidate_requires_review")
        self.assertFalse(packet["full_passive_aware_lvs_proven"])
        self.assertEqual(
            packet["candidate_summary"]["source_equivalent_netlist"],
            ["xc0 outn net027 cfmom_2t"],
        )
        self.assertEqual(packet["source_instance_coverage"]["source_instances"], ["xc0"])
        self.assertEqual(packet["source_instance_coverage"]["candidate_instances"], ["xc0"])
        self.assertTrue(packet["source_instance_coverage"]["all_source_passives_have_candidate"])
        self.assertIn(
            "source_capacitor_requires_plate_coupling_abstraction",
            packet["candidate_summary"]["unresolved_blockers"],
        )

    def test_abstraction_readiness_accepts_direct_matching_capacitor(self) -> None:
        source = [
            ".subckt amp outn net027\n",
            "xc0 outn net027 cfmom_2t nr=94\n",
            ".ends amp\n",
        ]
        extracted = [
            ".subckt amp_flat outn net027\n",
            "C1 outn net027 2f\n",
            ".ends\n",
        ]

        summary = analyze(source_lines=source, extracted_lines=extracted, magic_shorts=[], identity={})

        self.assertEqual(summary["status"], "all_source_passives_candidate_for_abstraction")
        self.assertEqual(summary["source_passives_candidate_for_abstraction"], 1)
        self.assertTrue(summary["source_passives"][0]["direct_expected_device_present"])


if __name__ == "__main__":
    unittest.main()
