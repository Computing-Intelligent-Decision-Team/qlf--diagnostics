from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare_mos_connectivity import compare, render_report


REFERENCE_NETLIST = """\
.subckt SMC vdda gnda vin vip ibias vout
X0 vdda ibias ibias vdda sky130_fd_pr__pfet_01v8 w=0.22 l=10
X1 net53 ibias vdda vdda sky130_fd_pr__pfet_01v8 w=0.22 l=10
X2 vout outn gnda gnda sky130_fd_pr__nfet_01v8 w=1.48 l=10
X3 gnda outp outn gnda sky130_fd_pr__nfet_01v8 w=1.5 l=10
X4 outp vin net53 vdda sky130_fd_pr__pfet_01v8 w=7.52 l=8.24
X5 gnda outp outp gnda sky130_fd_pr__nfet_01v8 w=1.5 l=10
X6 vout ibias vdda vdda sky130_fd_pr__pfet_01v8 w=0.22 l=10
X7 net53 vip outn vdda sky130_fd_pr__pfet_01v8 w=7.52 l=8.24
.ends
"""


CANDIDATE_SUPPLY_MISMATCH = """\
.subckt SMC_flat vdda gnda vin vip ibias vout
X0 vout ibias vdda vdda sky130_fd_pr__pfet_01v8 w=0.22 l=10
X1 vdda ibias a_n15_2446# vdda sky130_fd_pr__pfet_01v8 w=0.22 l=10
X2 vdda a_1340_n30# a_3585_n10# vdda sky130_fd_pr__nfet_01v8 w=1.5 l=10
X9 a_1340_n30# vin a_3264_586# vdda sky130_fd_pr__pfet_01v8 w=7.52 l=8.24
X22 a_3264_586# ibias vdda vdda sky130_fd_pr__pfet_01v8 w=0.22 l=10
X30 vout vdda vdda vdda sky130_fd_pr__nfet_01v8 w=1.48 l=10
X33 a_3264_586# vip vdda vdda sky130_fd_pr__pfet_01v8 w=7.52 l=8.24
X35 vdda a_1340_n30# vdda vdda sky130_fd_pr__nfet_01v8 w=1.5 l=10
.ends
"""


Candidate_INTERNAL_SPLIT = """\
.subckt SMC_flat vdda gnda vin vip ibias vout
X0 vout ibias vdda vdda sky130_fd_pr__pfet_01v8 w=0.22 l=10
X1 vdda ibias a_n15_2446# vdda sky130_fd_pr__pfet_01v8 w=0.22 l=10
X2 gnda outp_gate_pair outp_source_only gnda sky130_fd_pr__nfet_01v8 w=1.5 l=10
X3 outp_gate_pair vin net53 vdda sky130_fd_pr__pfet_01v8 w=7.52 l=8.24
X4 net53 ibias vdda vdda sky130_fd_pr__pfet_01v8 w=0.22 l=10
X5 vout outn_alias gnda gnda sky130_fd_pr__nfet_01v8 w=1.48 l=10
X6 net53 vip outn_alias vdda sky130_fd_pr__pfet_01v8 w=7.52 l=8.24
X7 gnda outp_gate_pair outn_alias gnda sky130_fd_pr__nfet_01v8 w=1.5 l=10
.ends
"""


NETGEN_REPORT = """\
Cell SMC_flat disconnected node: gnda
Number of devices: 10                      |Number of devices: 10
Number of nets: 10 **Mismatch**            |Number of nets: 11 **Mismatch**
Netlists do not match.
"""


class MosConnectivityComparisonTest(unittest.TestCase):
    def write_file(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_identical_mos_connectivity_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = self.write_file(root, "reference.spice", REFERENCE_NETLIST)
            candidate = self.write_file(root, "candidate.spice", REFERENCE_NETLIST)

            summary = compare(reference_path=reference, candidate_path=candidate)

        self.assertEqual(summary["status"], "pass")
        self.assertEqual(summary["issues"], [])
        self.assertEqual(summary["candidate"]["mos_device_class_count"], {"pfet": 5, "nfet": 3})

    def test_supply_corruption_and_disconnected_vss_are_classified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = self.write_file(root, "reference.spice", REFERENCE_NETLIST)
            candidate = self.write_file(root, "candidate.spice", CANDIDATE_SUPPLY_MISMATCH)
            netgen = self.write_file(root, "netgen.out", NETGEN_REPORT)

            summary = compare(
                reference_path=reference,
                candidate_path=candidate,
                netgen_report=netgen,
            )

        self.assertEqual(summary["status"], "supply_or_internal_net_mismatch")
        self.assertIn("candidate_vss_has_no_mos_terminal_roles", summary["issues"])
        self.assertIn("candidate_nfet_source_or_bulk_tied_to_vdd", summary["issues"])
        self.assertIn("netgen_reports_vss_disconnected", summary["issues"])
        self.assertEqual(summary["netgen_report"]["disconnected_nodes"], ["gnda"])
        self.assertEqual(summary["candidate"]["supply_role_summary"]["nfet_source_or_bulk_to_vdd"], 5)
        suggestions = summary["role_signature_match_suggestions"]
        self.assertTrue(any(item["reference_net"] == "vdda" for item in suggestions))
        report = render_report(summary)
        self.assertIn("## Closest Candidate Role Matches", report)
        self.assertIn("| reference net | reference roles | candidate net |", report)

    def test_internal_split_suggestions_identify_candidate_net_groups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = self.write_file(root, "reference.spice", REFERENCE_NETLIST)
            candidate = self.write_file(root, "candidate.spice", Candidate_INTERNAL_SPLIT)

            summary = compare(reference_path=reference, candidate_path=candidate)

        self.assertEqual(summary["status"], "mos_internal_net_mismatch")
        split_suggestions = summary["split_net_repair_suggestions"]
        outp = next(item for item in split_suggestions if item["reference_nets"] == ["outp"])
        self.assertEqual(
            outp["candidate_net_groups"][0]["candidate_nets"],
            ["outp_gate_pair", "outp_source_only"],
        )
        exact_renames = summary["exact_role_rename_suggestions"]
        self.assertIn(
            {
                "candidate_net": "outn_alias",
                "reference_net": "outn",
                "candidate_roles": {"nfet.gate": 1, "nfet.source": 1, "pfet.source": 1},
                "reason": "candidate internal net has the same MOS terminal-role signature as the reference net",
            },
            exact_renames,
        )
        report = render_report(summary)
        self.assertIn("## Split-Net Repair Hints", report)
        self.assertIn("## Exact-Role Rename Hints", report)
        self.assertIn("outp_gate_pair", report)
        self.assertIn("outn_alias", report)


if __name__ == "__main__":
    unittest.main()
