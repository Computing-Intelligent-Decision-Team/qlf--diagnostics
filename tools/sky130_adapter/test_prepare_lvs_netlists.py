#!/usr/bin/env python3
"""Tests for Sky130 LVS netlist preparation diagnostics."""

from __future__ import annotations

import unittest
from collections import Counter

from prepare_lvs_netlists import (
    ExtractedPassive,
    SourcePassive,
    passive_abstraction_diagnostic,
    parse_extracted_physical_passives,
    parse_source_passives,
)


class PrepareLvsNetlistsTest(unittest.TestCase):
    def test_source_passive_parser_detects_resistor_and_capacitor_instances(self) -> None:
        devices = parse_source_passives(
            [
                ".subckt amp vdda gnda outn vout\n",
                "xr0 net027 vout gnda rppolywo_m lr=4e-6 wr=4e-7\n",
                "xc0 outn net027 cfmom_2t nr=94 lr=4e-6\n",
                "xm0 outn vip gnda gnda nch_mac l=1u w=2u\n",
                ".ends amp\n",
            ]
        )

        self.assertEqual(
            devices,
            [
                SourcePassive("xr0", "rppolywo_m", ("net027", "vout", "gnda")),
                SourcePassive("xc0", "cfmom_2t", ("outn", "net027")),
            ],
        )

    def test_extracted_passive_parser_detects_magic_generic_resistors(self) -> None:
        devices = parse_extracted_physical_passives(
            [
                "R0 m2_82_5771# m2_82_5771# sky130_fd_pr__res_generic_m3 w=1 l=2\n",
                "R1 m1_82_3673# vdda sky130_fd_pr__res_generic_m1 w=0.12 l=0.06\n",
                "C0 net1 net2 1f\n",
            ]
        )

        self.assertEqual(
            devices,
            [
                ExtractedPassive(
                    "R0",
                    "sky130_fd_pr__res_generic_m3",
                    ("m2_82_5771#", "m2_82_5771#"),
                ),
                ExtractedPassive(
                    "R1",
                    "sky130_fd_pr__res_generic_m1",
                    ("m1_82_3673#", "vdda"),
                ),
            ],
        )

    def test_passive_abstraction_reports_uncovered_source_terminals(self) -> None:
        source = [
            ".subckt amp vdda gnda vin vip ibias vout\n",
            "xr0 net027 vout gnda rppolywo_m lr=4e-6\n",
            "xc0 outn net027 cfmom_2t nr=94\n",
            ".ends amp\n",
        ]
        extracted = [
            ".subckt amp_flat vdda vin vip ibias vout\n",
            "R0 m2_82_5771# m2_82_5771# sky130_fd_pr__res_generic_m3 w=1 l=2\n",
            "R1 m1_82_3673# vdda sky130_fd_pr__res_generic_m1 w=0.12 l=0.06\n",
            ".ends\n",
        ]

        diagnostic = passive_abstraction_diagnostic(source, extracted)

        self.assertEqual(
            diagnostic["status"],
            "physical_passives_extracted_but_source_terminals_not_recovered",
        )
        self.assertEqual(diagnostic["source_passive_count"], 2)
        self.assertEqual(diagnostic["extracted_physical_passive_count"], 2)
        self.assertEqual(diagnostic["covered_source_passive_terminals"], [])
        self.assertEqual(
            diagnostic["missing_source_passive_terminals"],
            ["gnda", "net027", "outn", "vout"],
        )
        self.assertEqual(diagnostic["extracted_passives_touching_source_terminals"], 0)
        self.assertEqual(diagnostic["extracted_passives_touching_source_ports"], 1)
        self.assertEqual(diagnostic["self_loop_extracted_passives"], 1)
        self.assertEqual(diagnostic["internal_only_extracted_passives"], 1)
        self.assertEqual(
            diagnostic["extracted_model_counts"],
            Counter(
                {
                    "sky130_fd_pr__res_generic_m1": 1,
                    "sky130_fd_pr__res_generic_m3": 1,
                }
            ),
        )

    def test_passive_abstraction_reports_partial_source_terminal_recovery(self) -> None:
        source = [
            ".subckt amp vdda gnda vin vip ibias vout\n",
            "xr0 net027 vout gnda rppolywo_m lr=4e-6\n",
            "xc0 outn net027 cfmom_2t nr=94\n",
            ".ends amp\n",
        ]
        extracted = [
            ".subckt amp_flat vdda vin vip ibias vout net027 outn\n",
            "R1 net027_uq0 net027 sky130_fd_pr__res_generic_m1 w=0.12 l=0.06\n",
            "R5 outn vdda sky130_fd_pr__res_generic_m1 w=0.12 l=0.06\n",
            ".ends\n",
        ]

        diagnostic = passive_abstraction_diagnostic(source, extracted)

        self.assertEqual(
            diagnostic["status"],
            "physical_passives_partially_recover_source_terminals",
        )
        self.assertEqual(diagnostic["covered_source_passive_terminals"], ["net027", "outn"])
        self.assertEqual(diagnostic["missing_source_passive_terminals"], ["gnda", "vout"])


if __name__ == "__main__":
    unittest.main()
