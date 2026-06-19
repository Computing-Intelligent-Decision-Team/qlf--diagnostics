#!/usr/bin/env python3
from __future__ import annotations

import json
from types import SimpleNamespace
import tempfile
import unittest
import struct
from pathlib import Path
from unittest.mock import patch

from tools.analog_harness.layout import (
    _choose_wsl_distro,
    _passive_integrity_interpretation,
    _parse_wsl_distro_lines,
    _parse_version,
    _version_lt,
    _wsl_path,
    classify_passive_aware_evidence,
    derive_mos_connectivity_repair_plan,
    LayoutVerificationAdapter,
    count_extracted_intentional_passives,
    extracted_physical_passive_devices,
    count_source_passives,
    find_generated_passive_gds,
    native_passive_device_recognition_summary,
    parse_magic_unknown_layers,
    parse_magic_port_shorts,
    parse_passive_abstraction_status,
    parse_cap_ff,
    parse_dropped_passives,
    parse_markdown_table,
    passive_tbd_layers,
    passive_terminal_recovery_summary,
    run_gds_structure_diagnostic,
    run_lvs_preparation_diagnostic,
    run_passive_abstraction_readiness_diagnostic,
    run_passive_identity_reconstruction,
    source_passive_instances,
    summarize_resistor_remap_variants,
    write_passive_integrity_report,
    write_passive_terminal_recovery_report,
)
from tools.analog_harness.models import EvidencePacket
from tools.analog_harness.models import CompiledCandidate
from tools.analog_harness.controller import HarnessController
from tools.analog_harness.optimizer import aggregate_reward, closure_level_from_evidence, flatten_evidence
from tools.analog_harness.sim import (
    Sky130ModelBin,
    _parse_ac_sweep_rows,
    _settling_time_from_rows,
    _unity_gain_crossing,
    normalize_magic_extracted_units,
    project_magical_macros_to_sky130,
    project_sky130_primitives_to_direct_models,
    read_subckt_name,
    snap_magic_extracted_model_bins,
)
from tools.analog_harness.state import CandidateStore


def _gds_record(record_type: int, payload: bytes = b"", data_type: int = 0x00) -> bytes:
    return struct.pack(">HBB", len(payload) + 4, record_type, data_type) + payload


def _gds_ascii(value: str) -> bytes:
    payload = value.encode("ascii")
    return payload if len(payload) % 2 == 0 else payload + b"\0"


def _gds_int2(value: int) -> bytes:
    return struct.pack(">h", value)


def _gds_xy(x: int, y: int) -> bytes:
    return struct.pack(">ii", x, y)


def _minimal_text_gds(label: str = "vout") -> bytes:
    return (
        _gds_record(0x05)
        + _gds_record(0x06, _gds_ascii("TOP"), 0x06)
        + _gds_record(0x0C)
        + _gds_record(0x0D, _gds_int2(67), 0x02)
        + _gds_record(0x16, _gds_int2(5), 0x02)
        + _gds_record(0x10, _gds_xy(300, 400), 0x03)
        + _gds_record(0x19, _gds_ascii(label), 0x06)
        + _gds_record(0x11)
        + _gds_record(0x07)
    )


class LayoutOptimizerStateTest(unittest.TestCase):
    def test_parse_layout_summary_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.md"
            summary.write_text(
                "| Field | Value |\n"
                "| --- | --- |\n"
                "| DRC_COUNT | 0 |\n"
                "| LAYOUT_INPUT_MODE | mos_only_projection |\n"
                "| LAYOUT_PROJECTION_DROPPED_PASSIVES | 2 |\n"
                "| MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER | 0 |\n"
                "| MAGICAL_SKIP_ROUTER_PARSE_GDS | 1 |\n"
                "| MAGICAL_SKIP_TOP_POWER_ROUTE | 1 |\n"
                "| LVS_MODE | mos_only_projection |\n"
                "| CONNECTIVITY_LVS_MATCH | yes |\n"
                "| PEX_TOTAL_CAP_FF | 71.4964 fF |\n",
                encoding="utf-8",
            )
            fields = parse_markdown_table(summary)

        self.assertEqual(fields["DRC_COUNT"], "0")
        self.assertEqual(fields["LAYOUT_INPUT_MODE"], "mos_only_projection")
        self.assertEqual(fields["LAYOUT_PROJECTION_DROPPED_PASSIVES"], "2")
        self.assertEqual(fields["MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER"], "0")
        self.assertEqual(fields["MAGICAL_SKIP_ROUTER_PARSE_GDS"], "1")
        self.assertEqual(fields["MAGICAL_SKIP_TOP_POWER_ROUTE"], "1")
        self.assertEqual(fields["LVS_MODE"], "mos_only_projection")
        self.assertEqual(parse_cap_ff(fields["PEX_TOTAL_CAP_FF"]), 71.4964)

    def test_wsl_path_translates_windows_drive_paths(self) -> None:
        translated = _wsl_path(Path("E:/codex-magical-sky130-harness/example.sp"))

        self.assertEqual(translated, "/mnt/e/codex-magical-sky130-harness/example.sp")

    def test_wsl_distro_parser_prefers_non_docker_distribution(self) -> None:
        text = "\x00*\x00 \x00d\x00o\x00c\x00k\x00e\x00r\x00-\x00d\x00e\x00s\x00k\x00t\x00o\x00p\x00\n\x00U\x00b\x00u\x00n\x00t\x00u\x00-\x002\x004\x00.\x000\x004\x00\n"

        self.assertEqual(_parse_wsl_distro_lines(text), ["docker-desktop", "Ubuntu-24.04"])

        completed = type("Completed", (), {"returncode": 0, "stdout": "docker-desktop\nUbuntu-24.04\n"})()
        with patch("tools.analog_harness.layout.sys.platform", "win32"), patch(
            "tools.analog_harness.layout.shutil.which", return_value="wsl"
        ), patch("tools.analog_harness.layout.subprocess.run", return_value=completed):
            self.assertEqual(_choose_wsl_distro(), "Ubuntu-24.04")

    def test_magic_version_comparison(self) -> None:
        self.assertEqual(_parse_version("Magic 8.3.105"), (8, 3, 105))
        self.assertTrue(_version_lt((8, 3, 105), (8, 3, 411)))
        self.assertFalse(_version_lt((8, 3, 411), (8, 3, 411)))

    def test_command_available_uses_local_lookup_without_wsl_distro(self) -> None:
        adapter = object.__new__(LayoutVerificationAdapter)
        adapter.layout_config = {}

        self.assertTrue(adapter._command_available("python") or adapter._command_available("py"))
        self.assertTrue(adapter._command_available(("python", "py")))
        self.assertFalse(adapter._command_available("__codex_missing_command_for_test__"))
        self.assertFalse(
            adapter._command_available(
                ("__codex_missing_command_for_test__", "__codex_missing_command_for_test_2__")
            )
        )

    def test_ic_netgen_lvs_available_rejects_meshing_netgen(self) -> None:
        adapter = object.__new__(LayoutVerificationAdapter)
        adapter.layout_config = {}
        completed = SimpleNamespace(returncode=0, stdout="NETGEN-6.2.2401\nIncluding OpenCascade\n")

        def fake_which(name: str) -> str | None:
            return "/usr/bin/netgen" if name == "netgen" else None

        with patch("tools.analog_harness.layout.sys.platform", "linux"), patch(
            "tools.analog_harness.layout.shutil.which", side_effect=fake_which
        ), patch("tools.analog_harness.layout.subprocess.run", return_value=completed):
            self.assertFalse(adapter._ic_netgen_lvs_available())

    def test_ic_netgen_lvs_available_accepts_ic_netgen_fallback(self) -> None:
        adapter = object.__new__(LayoutVerificationAdapter)
        adapter.layout_config = {}
        completed = SimpleNamespace(returncode=0, stdout="Netgen 1.5.133 compiled on Thu Dec 1\n")

        def fake_which(name: str) -> str | None:
            return "/usr/local/bin/netgen" if name == "netgen" else None

        with patch("tools.analog_harness.layout.sys.platform", "linux"), patch(
            "tools.analog_harness.layout.shutil.which", side_effect=fake_which
        ), patch("tools.analog_harness.layout.subprocess.run", return_value=completed):
            self.assertTrue(adapter._ic_netgen_lvs_available())

    def test_mos_only_projection_extracted_netlist_prefers_spice(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            extracted = root / "layout" / "lvs_mos_projection" / "AMP_extracted.spice"
            extracted.parent.mkdir(parents=True)
            extracted.write_text("* extracted\n", encoding="utf-8")
            adapter = object.__new__(LayoutVerificationAdapter)
            adapter.config = type("Cfg", (), {"top_cell": "AMP"})()
            compiled = CompiledCandidate(
                candidate_id="cand",
                candidate_dir=root,
                case_dir=root / "case",
                out_dir=root / "layout",
                netlist_path=root / "source.sp",
                config_path=root / "config.json",
                action_normalized=[],
                values={},
                assignments={},
            )

            self.assertEqual(adapter._mos_only_projection_extracted_netlist(compiled), extracted)

    def test_passive_full_probe_cleans_mos_projection_config_and_falls_back_on_lvs_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            case_dir = root / "case"
            candidate_dir = root / "cand"
            out_dir = candidate_dir / "layout"
            case_dir.mkdir(parents=True)
            out_dir.mkdir(parents=True)
            netlist = case_dir / "AMP.sp"
            netlist.write_text(
                ".subckt AMP vdda gnda out\n"
                "xr0 n1 out gnda rppolywo_m\n"
                ".ends AMP\n",
                encoding="utf-8",
            )
            config_path = case_dir / "AMP.json"
            config_path.write_text(
                json.dumps(
                    {
                        "hspice_netlist": "AMP.sp",
                        "connectivityLvsProjection": "mos_only",
                        "lvsNetRenames": ["a_1#=out"],
                    }
                ),
                encoding="utf-8",
            )
            compiled = CompiledCandidate(
                candidate_id="cand_0001",
                candidate_dir=candidate_dir,
                case_dir=case_dir,
                out_dir=out_dir,
                netlist_path=netlist,
                config_path=config_path,
                action_normalized=[],
                values={},
                assignments={},
            )
            adapter = object.__new__(LayoutVerificationAdapter)
            adapter.config = SimpleNamespace(
                data={
                    "verification": {
                        "passive_aware": {
                            "reuse_existing_pinned_gds_probe": True,
                            "experimental_passive_remap": True,
                        }
                    }
                },
                design_id="amp",
                top_cell="AMP",
                repo_root=root,
                verification_scope="mos_only_projection",
            )
            adapter.layout_config = {}

            def fake_run(*args, **kwargs):
                summary = candidate_dir / "layout_passive_aware" / "summary.md"
                summary.write_text(
                    "| Field | Value |\n"
                    "| --- | --- |\n"
                    "| STATUS | FAIL |\n"
                    "| FAILED_STAGE | connectivity_lvs |\n",
                    encoding="utf-8",
                )
                return SimpleNamespace(returncode=1)

            fallback_packet = EvidencePacket(
                candidate_id="cand_0001",
                stage="passive_aware_lvs",
                fidelity="E2P",
                status="unsupported",
                verification_scope="mos_only_projection",
            )

            with patch.object(adapter, "_runtime_preflight", return_value=None), patch.object(
                adapter, "_command", return_value=["fake"]
            ), patch("tools.analog_harness.layout.subprocess.run", side_effect=fake_run), patch.object(
                adapter, "_run_existing_pinned_gds_probe", return_value=fallback_packet
            ) as fallback:
                packet = adapter._run_full_extraction_probe(compiled, source_passives=1)

            probe_config = json.loads((case_dir / "amp_cand_0001_passive_probe.json").read_text(encoding="utf-8"))
            self.assertNotIn("connectivityLvsProjection", probe_config)
            self.assertNotIn("lvsNetRenames", probe_config)
            self.assertTrue(probe_config["passiveAwareProbe"])
            self.assertTrue(probe_config["experimentalPassiveRemap"])
            fallback.assert_called_once()
            self.assertEqual(packet, fallback_packet)

    def test_magical_env_overrides_include_passive_specific_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.json"
            config_path.write_text('{"passiveAwareProbe": true}\n', encoding="utf-8")
            compiled = CompiledCandidate(
                candidate_id="cand",
                candidate_dir=root,
                case_dir=root,
                out_dir=root,
                netlist_path=root / "source.sp",
                config_path=config_path,
                action_normalized=[],
                values={},
                assignments={},
            )
            adapter = object.__new__(LayoutVerificationAdapter)
            adapter.layout_config = {"magical_env": {"MAGICAL_POWER_STRIPE_EXTRA_GRID": "1"}}
            adapter.config = SimpleNamespace(
                data={
                    "verification": {
                        "passive_aware": {
                            "magical_env": {"MAGICAL_POWER_STRIPE_EXTRA_GRID": "2"}
                        }
                    }
                }
            )

            overrides = adapter._magical_env_overrides(compiled)

            self.assertEqual(overrides["MAGICAL_POWER_STRIPE_EXTRA_GRID"], "2")

    def test_summarize_resistor_remap_variants_prefers_abstraction_candidate(self) -> None:
        summary = summarize_resistor_remap_variants(
            [
                {
                    "variant": "high_po_second_stage",
                    "abstraction_summary": {
                        "source_level_abstraction_candidate_count": 0,
                        "source_resistors_with_segmented_chain": 0,
                        "ext_passive_rsubckt_count": 0,
                        "blocker_count": 7,
                    },
                },
                {
                    "variant": "xhigh_po_second_stage",
                    "abstraction_summary": {
                        "status": "partial_passive_abstraction_readiness",
                        "source_level_abstraction_candidate_count": 1,
                        "source_resistors_with_segmented_chain": 1,
                        "source_capacitors_with_plate_coupling_evidence": 1,
                        "ext_passive_rsubckt_count": 31,
                        "ext_passive_rsubckt_by_source_instance": {"xr0": 28, "xc0": 3},
                        "blocker_count": 5,
                    },
                    "magic_port_short_count": 1,
                    "magic_supply_short_present": True,
                    "magic_port_shorts": [{"port_a": "gnda", "port_b": "vdda"}],
                    "abstraction_packet_json": "xhigh_po_second_stage_abstraction_packet.json",
                    "extracted_netlist": "xhigh_po_second_stage_extracted.spice",
                    "abstraction_candidates": "xhigh_po_second_stage_abstraction_candidates.spice",
                    "abstraction_packet_verification_status": "candidate_requires_review",
                    "abstraction_packet_verification_json": (
                        "xhigh_po_second_stage_abstraction_packet_verification_summary.json"
                    ),
                    "abstraction_source_passive_abs_netlist": "xhigh_po_second_stage_source_passive_abs.spice",
                    "abstraction_candidate_passive_abs_netlist": (
                        "xhigh_po_second_stage_candidate_passive_abs.spice"
                    ),
                    "passive_abs_netgen_status": "pass",
                    "passive_abs_lvs_result_summary": "xhigh_po_second_stage_passive_abs_lvs_result_summary.md",
                    "passive_abs_netgen_report": "xhigh_po_second_stage_passive_abs_netgen_report.out",
                    "passive_aware_lvs_trial_prepare_status": "ready_for_netgen_trial",
                    "passive_aware_lvs_trial_netgen_status": "fail",
                    "passive_aware_lvs_trial_result_summary": (
                        "xhigh_po_second_stage_passive_aware_lvs_result_summary.md"
                    ),
                    "passive_aware_mos_connectivity_status": "supply_or_internal_net_mismatch",
                    "passive_aware_mos_connectivity_reason": (
                        "Candidate MOS connectivity has supply-role corruption or a disconnected VSS node."
                    ),
                    "passive_aware_mos_connectivity_summary_json": (
                        "xhigh_po_second_stage_passive_aware_mos_connectivity_summary.json"
                    ),
                    "passive_aware_mos_connectivity_report": (
                        "xhigh_po_second_stage_passive_aware_mos_connectivity_report.md"
                    ),
                    "hybrid_mos_passive_lvs_trial_prepare_status": "ready_for_netgen_trial",
                    "hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                    "hybrid_mos_passive_lvs_trial_result_summary": (
                        "xhigh_po_second_stage_hybrid_mos_passive_lvs_result_summary.md"
                    ),
                    "abstraction_packet": {
                        "source_instance_coverage": {
                            "all_source_passives_have_candidate": True,
                            "missing_source_passive_instances": [],
                        }
                    },
                },
            ]
        )

        self.assertEqual(summary["status"], "pass")
        self.assertEqual(summary["best_variant"], "xhigh_po_second_stage")
        self.assertEqual(summary["best_source_level_abstraction_candidate_count"], 1)
        self.assertEqual(summary["best_magic_port_short_count"], 1)
        self.assertTrue(summary["best_magic_supply_short_present"])
        self.assertEqual(summary["best_magic_port_shorts"], [{"port_a": "gnda", "port_b": "vdda"}])
        self.assertEqual(summary["best_source_resistors_with_segmented_chain"], 1)
        self.assertEqual(summary["best_source_capacitors_with_plate_coupling_evidence"], 1)
        self.assertEqual(summary["best_ext_passive_rsubckt_by_source_instance"], {"xr0": 28, "xc0": 3})
        self.assertEqual(
            summary["best_abstraction_packet_json"],
            "xhigh_po_second_stage_abstraction_packet.json",
        )
        self.assertEqual(summary["best_extracted_netlist"], "xhigh_po_second_stage_extracted.spice")
        self.assertEqual(
            summary["best_abstraction_candidates"],
            "xhigh_po_second_stage_abstraction_candidates.spice",
        )
        self.assertEqual(summary["best_abstraction_packet_verification_status"], "candidate_requires_review")
        self.assertEqual(
            summary["best_abstraction_packet_verification_json"],
            "xhigh_po_second_stage_abstraction_packet_verification_summary.json",
        )
        self.assertEqual(
            summary["best_abstraction_source_passive_abs_netlist"],
            "xhigh_po_second_stage_source_passive_abs.spice",
        )
        self.assertEqual(
            summary["best_abstraction_candidate_passive_abs_netlist"],
            "xhigh_po_second_stage_candidate_passive_abs.spice",
        )
        self.assertEqual(summary["best_passive_abs_netgen_status"], "pass")
        self.assertEqual(
            summary["best_passive_abs_lvs_result_summary"],
            "xhigh_po_second_stage_passive_abs_lvs_result_summary.md",
        )
        self.assertEqual(
            summary["best_passive_abs_netgen_report"],
            "xhigh_po_second_stage_passive_abs_netgen_report.out",
        )
        self.assertEqual(summary["best_passive_aware_lvs_trial_prepare_status"], "ready_for_netgen_trial")
        self.assertEqual(summary["best_passive_aware_lvs_trial_netgen_status"], "fail")
        self.assertEqual(
            summary["best_passive_aware_lvs_trial_result_summary"],
            "xhigh_po_second_stage_passive_aware_lvs_result_summary.md",
        )
        self.assertEqual(
            summary["best_passive_aware_mos_connectivity_status"],
            "supply_or_internal_net_mismatch",
        )
        self.assertEqual(
            summary["best_passive_aware_mos_connectivity_reason"],
            "Candidate MOS connectivity has supply-role corruption or a disconnected VSS node.",
        )
        self.assertEqual(
            summary["best_passive_aware_mos_connectivity_summary_json"],
            "xhigh_po_second_stage_passive_aware_mos_connectivity_summary.json",
        )
        self.assertEqual(
            summary["best_passive_aware_mos_connectivity_report"],
            "xhigh_po_second_stage_passive_aware_mos_connectivity_report.md",
        )
        self.assertEqual(summary["best_hybrid_mos_passive_lvs_trial_prepare_status"], "ready_for_netgen_trial")
        self.assertEqual(summary["best_hybrid_mos_passive_lvs_trial_netgen_status"], "pass")
        self.assertEqual(
            summary["best_hybrid_mos_passive_lvs_trial_result_summary"],
            "xhigh_po_second_stage_hybrid_mos_passive_lvs_result_summary.md",
        )
        self.assertTrue(summary["best_all_source_passives_have_candidate"])
        self.assertEqual(summary["best_missing_source_passive_instances"], [])

    def test_native_passive_recognition_fails_for_segmented_and_plate_coupling_only(self) -> None:
        native = native_passive_device_recognition_summary(
            {
                "source_passive_count": 2,
                "source_passives": [
                    {
                        "source_instance": "xr0",
                        "source_model": "rppolywo_m",
                        "expected_kind": "resistor",
                        "direct_expected_device_present": False,
                        "blockers": ["source_resistor_requires_segmented_chain_abstraction"],
                    },
                    {
                        "source_instance": "xc0",
                        "source_model": "cfmom_2t",
                        "expected_kind": "capacitor",
                        "direct_expected_device_present": False,
                        "blockers": ["source_capacitor_requires_plate_coupling_abstraction"],
                    },
                ],
            }
        )

        self.assertEqual(native["status"], "fail")
        self.assertFalse(native["claimable"])
        self.assertEqual(native["recognized_source_passive_count"], 0)
        self.assertEqual(native["missing_source_passive_instances"], ["xr0", "xc0"])
        self.assertIn("source_resistor_requires_segmented_chain_abstraction", native["blockers_by_instance"]["xr0"])
        self.assertIn("source_capacitor_requires_plate_coupling_abstraction", native["blockers_by_instance"]["xc0"])

    def test_summarize_resistor_remap_variants_reports_native_recognition_gate(self) -> None:
        summary = summarize_resistor_remap_variants(
            [
                {
                    "variant": "xhigh_po_second_stage",
                    "abstraction_summary": {
                        "source_passive_count": 2,
                        "source_level_abstraction_candidate_count": 2,
                        "source_resistors_with_segmented_chain": 1,
                        "ext_passive_rsubckt_count": 31,
                        "blocker_count": 2,
                        "source_passives": [
                            {
                                "source_instance": "xr0",
                                "source_model": "rppolywo_m",
                                "expected_kind": "resistor",
                                "direct_expected_device_present": False,
                                "blockers": ["source_resistor_requires_segmented_chain_abstraction"],
                            },
                            {
                                "source_instance": "xc0",
                                "source_model": "cfmom_2t",
                                "expected_kind": "capacitor",
                                "direct_expected_device_present": False,
                                "blockers": ["source_capacitor_requires_plate_coupling_abstraction"],
                            },
                        ],
                    },
                }
            ]
        )

        self.assertEqual(summary["best_native_passive_device_recognition_status"], "fail")
        self.assertFalse(summary["best_native_passive_device_recognition_claimed"])
        self.assertEqual(summary["best_native_passive_device_recognition_missing_instances"], ["xr0", "xc0"])

    def test_classify_passive_aware_evidence_promotes_formal_abstraction(self) -> None:
        classification = classify_passive_aware_evidence(
            {
                "best_formal_lvs_abstraction_ready": True,
                "best_all_source_passives_have_candidate": True,
                "best_passive_abs_netgen_status": "pass",
                "best_hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                "best_passive_aware_lvs_trial_netgen_status": "fail",
            },
            fallback_reason="native full-GDS passive-aware LVS is unavailable",
            fallback_scope="mos_only_projection",
        )

        self.assertEqual(classification["packet_status"], "formal_abstraction_pass")
        self.assertEqual(classification["passive_aware_status"], "formal_abstraction_pass")
        self.assertEqual(
            classification["verification_scope"],
            "formal_passive_abstraction_with_mos_only_projection",
        )
        self.assertTrue(classification["formal_passive_abstraction_ready"])
        self.assertTrue(classification["formal_passive_only_lvs_match"])
        self.assertTrue(classification["hybrid_mos_reference_passive_lvs_match"])
        self.assertFalse(classification["full_passive_inclusive_gds_lvs_proven"])

    def test_classify_passive_aware_evidence_full_gds_formal_pass_is_scoped(self) -> None:
        classification = classify_passive_aware_evidence(
            {
                "best_formal_lvs_abstraction_ready": True,
                "best_all_source_passives_have_candidate": True,
                "best_passive_abs_netgen_status": "pass",
                "best_hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                "best_passive_aware_lvs_trial_netgen_status": "pass",
            },
            fallback_reason="native full-GDS passive-aware LVS is unavailable",
            fallback_scope="mos_only_projection",
        )

        self.assertEqual(classification["packet_status"], "formal_abstraction_with_full_gds_mos_pass")
        self.assertEqual(
            classification["passive_aware_status"],
            "formal_abstraction_with_full_gds_mos_pass",
        )
        self.assertEqual(
            classification["verification_scope"],
            "formal_passive_abstraction_with_full_gds_mos",
        )
        self.assertFalse(classification["full_passive_inclusive_gds_lvs_proven"])

    def test_classify_native_recognition_without_full_gds_lvs_does_not_upgrade_scope(self) -> None:
        classification = classify_passive_aware_evidence(
            {
                "best_formal_lvs_abstraction_ready": True,
                "best_all_source_passives_have_candidate": True,
                "best_passive_abs_netgen_status": "pass",
                "best_hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                "best_passive_aware_lvs_trial_netgen_status": "fail",
                "best_native_passive_device_recognition_status": "pass",
                "best_native_passive_device_recognition_claimed": True,
            },
            fallback_reason="native full-GDS passive-aware LVS is unavailable",
            fallback_scope="mos_only_projection",
        )

        self.assertEqual(classification["packet_status"], "formal_abstraction_pass")
        self.assertEqual(
            classification["verification_scope"],
            "formal_passive_abstraction_with_mos_only_projection",
        )
        self.assertFalse(classification["full_passive_inclusive_gds_lvs_proven"])

    def test_classify_passive_aware_evidence_only_native_pass_is_packet_pass(self) -> None:
        classification = classify_passive_aware_evidence(
            {
                "best_formal_lvs_abstraction_ready": True,
                "best_all_source_passives_have_candidate": True,
                "best_passive_abs_netgen_status": "pass",
                "best_hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                "best_passive_aware_lvs_trial_netgen_status": "pass",
                "best_native_passive_device_recognition_status": "pass",
                "best_native_passive_device_recognition_claimed": True,
            },
            fallback_reason="native full-GDS passive-aware LVS is unavailable",
            fallback_scope="mos_only_projection",
        )

        self.assertEqual(classification["packet_status"], "pass")
        self.assertEqual(classification["passive_aware_status"], "full_passive_aware_lvs_pass")
        self.assertEqual(classification["verification_scope"], "full_passive_inclusive_gds_lvs")
        self.assertTrue(classification["full_passive_inclusive_gds_lvs_proven"])

    def test_classify_passive_aware_evidence_bridge_pass_does_not_claim_native_passive_lvs(self) -> None:
        classification = classify_passive_aware_evidence(
            {
                "best_formal_lvs_abstraction_ready": True,
                "best_all_source_passives_have_candidate": True,
                "best_passive_abs_netgen_status": "pass",
                "best_hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                "best_passive_aware_lvs_trial_netgen_status": "fail",
                "best_route_bridge_formal_passive_lvs_netgen_status": "pass",
                "best_route_bridge_mos_connectivity_status": "pass",
                "best_route_bridge_drc_count": 0,
            },
            fallback_reason="native full-GDS passive-aware LVS is unavailable",
            fallback_scope="mos_only_projection",
        )

        self.assertEqual(
            classification["packet_status"],
            "formal_abstraction_with_gds_mos_bridge_pass",
        )
        self.assertEqual(
            classification["verification_scope"],
            "formal_passive_abstraction_with_gds_mos_bridge",
        )
        self.assertFalse(classification["full_passive_inclusive_gds_lvs_proven"])

    def test_mos_connectivity_repair_plan_uses_split_and_exact_role_hints(self) -> None:
        plan = derive_mos_connectivity_repair_plan(
            {
                "split_net_repair_suggestions": [
                    {
                        "reference_nets": ["ibias"],
                        "candidate_net_groups": [
                            {"candidate_nets": ["a_n15_2446#", "ibias"]}
                        ],
                    },
                    {
                        "reference_nets": ["outp"],
                        "candidate_net_groups": [
                            {"candidate_nets": ["a_1340_n30#", "a_3585_n10#"]}
                        ],
                    },
                ],
                "exact_role_rename_suggestions": [
                    {"candidate_net": "a_660_2774#", "reference_net": "outn"},
                    {"candidate_net": "a_3264_586#", "reference_net": "net53"},
                ],
            }
        )

        self.assertEqual(plan["status"], "ready")
        self.assertFalse(plan["signoff_eligible"])
        self.assertTrue(plan["requires_reference_role_signatures"])
        self.assertEqual(
            plan["renames"],
            [
                "a_n15_2446#=ibias",
                "a_1340_n30#=outp",
                "a_3585_n10#=outp",
                "a_660_2774#=outn",
                "a_3264_586#=net53",
            ],
        )

    def test_mos_connectivity_repair_plan_reports_conflicts(self) -> None:
        plan = derive_mos_connectivity_repair_plan(
            {
                "split_net_repair_suggestions": [
                    {
                        "reference_nets": ["outp"],
                        "candidate_net_groups": [{"candidate_nets": ["a_1#"]}],
                    }
                ],
                "exact_role_rename_suggestions": [
                    {"candidate_net": "a_1#", "reference_net": "outn"},
                ],
            }
        )

        self.assertEqual(plan["status"], "conflict")
        self.assertEqual(plan["renames"], ["a_1#=outp"])
        self.assertEqual(len(plan["conflicts"]), 1)

    def test_evidence_reward_and_closure_level(self) -> None:
        evidence = [
            EvidencePacket(
                candidate_id="cand_0001",
                stage="pre_sim",
                fidelity="E0",
                status="proxy_fallback",
                verification_scope="mos_only_projection",
                metrics={"dcgain": 80.0, "Power": 0.1},
            ),
            EvidencePacket(
                candidate_id="cand_0001",
                stage="layout_verification",
                fidelity="E2",
                status="pass",
                verification_scope="mos_only_projection",
            ),
        ]
        reward = aggregate_reward(
            {
                "dcgain": {"target": 70.0, "objective": "max"},
                "Power": {"target": 0.25, "objective": "min"},
            },
            evidence,
        )

        self.assertGreater(reward, 0.2)
        self.assertEqual(closure_level_from_evidence(evidence), "L4_layout_verified_mos_only")

    def test_post_sim_proxy_does_not_claim_l5(self) -> None:
        evidence = [
            EvidencePacket(
                candidate_id="cand_0001",
                stage="layout_verification",
                fidelity="E2",
                status="pass",
                verification_scope="mos_only_projection",
            ),
            EvidencePacket(
                candidate_id="cand_0001",
                stage="post_sim",
                fidelity="E3",
                status="proxy_fallback",
                verification_scope="mos_only_projection",
            ),
        ]
        flat = flatten_evidence(evidence)

        self.assertEqual(closure_level_from_evidence(evidence), "L4_layout_verified_mos_only")
        self.assertTrue(flat["verification_mask"]["E2"])
        self.assertFalse(flat["verification_mask"]["E3"])
        self.assertTrue(flat["verification_native_pass_mask"]["E2"])
        self.assertFalse(flat["verification_native_pass_mask"]["E3"])

    def test_flatten_scoped_passive_evidence_keeps_native_pass_separate(self) -> None:
        evidence = [
            EvidencePacket(
                candidate_id="cand_0001",
                stage="layout_verification",
                fidelity="E2",
                status="pass",
                verification_scope="mos_only_projection",
            ),
            EvidencePacket(
                candidate_id="cand_0001",
                stage="passive_aware_lvs",
                fidelity="E2P",
                status="formal_abstraction_with_gds_mos_bridge_pass",
                verification_scope="formal_passive_abstraction_with_gds_mos_bridge",
                metrics={
                    "passive_resistor_variant_best_route_bridge_drc_count": 0,
                },
            ),
        ]

        flat = flatten_evidence(evidence)

        self.assertEqual(closure_level_from_evidence(evidence), "L4_layout_verified_mos_only")
        self.assertTrue(flat["verification_mask"]["E2P"])
        self.assertFalse(flat["verification_native_pass_mask"]["E2P"])
        self.assertEqual(
            flat["verification_status_mask"]["E2P"],
            "formal_abstraction_with_gds_mos_bridge_pass",
        )
        self.assertEqual(
            flat["verification_scope_mask"]["E2P"],
            "formal_passive_abstraction_with_gds_mos_bridge",
        )
        self.assertEqual(flat["passive_aware_lvs_passive_resistor_variant_best_route_bridge_drc_count"], 0)

    def test_post_sim_pass_claims_l5(self) -> None:
        evidence = [
            EvidencePacket(
                candidate_id="cand_0001",
                stage="layout_verification",
                fidelity="E2",
                status="pass",
                verification_scope="mos_only_projection",
            ),
            EvidencePacket(
                candidate_id="cand_0001",
                stage="post_sim",
                fidelity="E3",
                status="pass",
                verification_scope="mos_only_projection",
            ),
        ]

        self.assertEqual(closure_level_from_evidence(evidence), "L5_post_layout_nominal")

    def test_pvt_sim_pass_claims_l6(self) -> None:
        evidence = [
            EvidencePacket(
                candidate_id="cand_0001",
                stage="layout_verification",
                fidelity="E2",
                status="pass",
                verification_scope="mos_only_projection",
            ),
            EvidencePacket(
                candidate_id="cand_0001",
                stage="post_sim",
                fidelity="E3",
                status="pass",
                verification_scope="mos_only_projection",
            ),
            EvidencePacket(
                candidate_id="cand_0001",
                stage="pvt_sim",
                fidelity="E4",
                status="pass",
                verification_scope="mos_only_projection",
            ),
        ]

        self.assertEqual(closure_level_from_evidence(evidence), "L6_post_layout_pvt")

    def test_reads_extracted_flat_subckt_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            netlist = Path(tmpdir) / "extracted.raw.spice"
            netlist.write_text(
                "* raw extracted\n"
                ".subckt SMCNR_SE_2st_AMP_flat vdda gnda vin vip ibias vout\n"
                ".ends\n",
                encoding="utf-8",
            )

            self.assertEqual(read_subckt_name(netlist), "SMCNR_SE_2st_AMP_flat")

    def test_normalizes_magic_extracted_sky130_mos_units(self) -> None:
        normalized = normalize_magic_extracted_units(
            "X0 d g s b sky130_fd_pr__pfet_01v8 ad=0.0385 pd=0.79 as=0 ps=0 w=0.22 l=10\n"
            "C0 d s 0.2f\n"
        )

        self.assertIn("ad=0.0385p", normalized)
        self.assertIn("pd=0.79u", normalized)
        self.assertIn("w=0.22u", normalized)
        self.assertIn("l=10u", normalized)
        self.assertIn("as=0", normalized)
        self.assertIn("C0 d s 0.2f", normalized)

    def test_normalize_magic_units_does_not_modify_existing_units(self) -> None:
        normalized = normalize_magic_extracted_units(
            "X0 d g s b sky130_fd_pr__pfet_01v8 w=10.0u l=8.24u ad=0.1p\n"
        )

        self.assertIn("w=10.0u", normalized)
        self.assertIn("l=8.24u", normalized)
        self.assertIn("ad=0.1p", normalized)
        self.assertNotIn("u0u", normalized)

    def test_snaps_magic_extracted_mos_to_nearest_model_bin(self) -> None:
        snapped, count = snap_magic_extracted_model_bins(
            "X0 d g s b sky130_fd_pr__pfet_01v8 ad=0.0385p pd=0.79u as=0 ps=0 w=0.22u l=10u\n",
            {"sky130_fd_pr__pfet_01v8": [Sky130ModelBin(lmin_um=8.0, lmax_um=20.0, wmin_um=0.42, wmax_um=0.55)]},
        )

        self.assertEqual(count, 1)
        self.assertIn("w=0.485u", snapped)
        self.assertIn("l=14u", snapped)

    def test_projects_sky130_primitive_to_direct_model(self) -> None:
        projected, snapped, model_count = project_sky130_primitives_to_direct_models(
            "X0 d g s b sky130_fd_pr__pfet_01v8 ad=0.0385p pd=0.79u as=0 ps=0 w=0.22u l=10u\n",
            {
                "sky130_fd_pr__pfet_01v8": [
                    Sky130ModelBin(
                        lmin_um=8.0,
                        lmax_um=20.0,
                        wmin_um=0.42,
                        wmax_um=0.55,
                        model_name="sky130_fd_pr__pfet_01v8__model.9",
                        model_lines=(
                            ".model sky130_fd_pr__pfet_01v8__model.9 pmos",
                            "+ level = 54.0 tox={4.23e-09+mc_mm_switch*sky130_fd_pr__pfet_01v8__toxe_slope}",
                        ),
                    )
                ]
            },
        )

        self.assertEqual(snapped, 1)
        self.assertEqual(model_count, 1)
        self.assertIn(".param l=1u", projected)
        self.assertIn(".param w=1u", projected)
        self.assertIn(".param mult=1", projected)
        self.assertIn(".param mc_mm_switch=0", projected)
        self.assertIn(".param sky130_fd_pr__pfet_01v8__toxe_slope=0", projected)
        self.assertIn(".model sky130_harness_pfet_9 pmos", projected)
        self.assertIn("M0 d g s b sky130_harness_pfet_9", projected)
        self.assertIn("m=", project_sky130_primitives_to_direct_models(
            "X0 d g s b sky130_fd_pr__pfet_01v8 w=0.22u l=10u multi=4\n",
            {
                "sky130_fd_pr__pfet_01v8": [
                    Sky130ModelBin(
                        lmin_um=8.0,
                        lmax_um=20.0,
                        wmin_um=0.42,
                        wmax_um=0.55,
                        model_name="sky130_fd_pr__pfet_01v8__model.9",
                        model_lines=(".model sky130_fd_pr__pfet_01v8__model.9 pmos", "+ level = 54.0"),
                    )
                ]
            },
        )[0])

    def test_projects_magical_macros_to_sky130_and_passive_primitives(self) -> None:
        projected, feedback = project_magical_macros_to_sky130(
            "xm0 out in tail vdda pch_mac l=8u w=7u multi=2\n"
            "xr0 n1 out gnda rppolywo_m lr=4e-6 wr=400e-9 series=31\n"
            "xc0 out n1 cfmom_2t nr=94\n"
        )

        self.assertIn("sky130_fd_pr__pfet_01v8", projected)
        self.assertIn("m=2", projected)
        self.assertIn("Rr0 n1 out", projected)
        self.assertIn("Cc0 out n1", projected)
        self.assertEqual(feedback["prelayout_projected_mos"], 1)
        self.assertEqual(feedback["prelayout_projected_resistors"], 1)
        self.assertEqual(feedback["prelayout_projected_capacitors"], 1)

    def test_ac_crossing_and_settling_helpers(self) -> None:
        sweep = _parse_ac_sweep_rows(
            [
                [1.0, 40.0, 1.0, -90.0],
                [10.0, 20.0, 10.0, -110.0],
                [100.0, -10.0, 100.0, -140.0],
            ]
        )
        crossing = _unity_gain_crossing(sweep)

        self.assertIsNotNone(crossing)
        assert crossing is not None
        self.assertGreater(crossing[0], 10.0)
        self.assertGreater(crossing[1], 0.0)
        self.assertEqual(
            _settling_time_from_rows([[0.0, 0.0], [1e-8, 0.8], [2e-8, 1.002], [3e-8, 1.0]], 1e-8, 0.02),
            1e-8,
        )

    def test_passive_probe_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            netlist = root / "amp.sp"
            netlist.write_text("xr0 a b g rppolywo_m\nxc0 b c cfmom_2t\n", encoding="utf-8")
            report = root / "lvs_preparation_report.md"
            report.write_text("- Dropped unsupported source passive devices: 2\n", encoding="utf-8")

            self.assertEqual(count_source_passives(netlist), 2)
            self.assertEqual(parse_dropped_passives(report), 2)

    def test_passive_integrity_parsers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            netlist = root / "amp.sp"
            netlist.write_text(
                ".subckt amp vdda gnda out\n"
                "xr0 net027 out gnda rppolywo_m lr=4e-6\n"
                "xc0 out net027 cfmom_2t nr=94\n"
                ".ends\n",
                encoding="utf-8",
            )
            remap = root / "gds_remap_report.md"
            remap.write_text(
                "| input layer | input datatype | element type | output layer | output datatype | action | mapping |\n"
                "| ---: | ---: | --- | ---: | ---: | --- | --- |\n"
                "| 115 | 1 | BOUNDARY | 115 | 1 | preserved_tbd | RPDMY -> TBD |\n"
                "| 31 | 0 | BOUNDARY | 67 | 20 | remapped | M1 -> li1 67/20 |\n",
                encoding="utf-8",
            )
            magic_log = root / "magic_extract.log"
            magic_log.write_text(
                "Error while reading cell: Unknown layer/datatype in boundary, layer=115 type=1\n",
                encoding="utf-8",
            )
            extracted = root / "extracted.raw.spice"
            extracted.write_text(
                ".subckt amp out gnda\n"
                "X0 out gnda gnda gnda sky130_fd_pr__nfet_01v8 w=1 l=1\n"
                "R0 a b sky130_fd_pr__res_generic_m3 w=1 l=2\n"
                "C0 out gnda 1f\n"
                ".ends\n",
                encoding="utf-8",
            )
            gds_dir = root / "case" / "gds"
            gds_dir.mkdir(parents=True)
            (gds_dir / "AMP_xr0.gds").write_text("", encoding="utf-8")
            (gds_dir / "AMP_xc0.gds").write_text("", encoding="utf-8")
            instances = source_passive_instances(netlist)
            found_gds = find_generated_passive_gds(root / "case", "AMP", instances)
            report = root / "passive_integrity_report.md"

            write_passive_integrity_report(
                report,
                {
                    "source_passive_devices": len(instances),
                    "source_passive_instances": instances,
                    "generated_passive_gds": len(found_gds),
                    "generated_passive_gds_paths": found_gds,
                    "dropped_source_passives": 2,
                    "extracted_physical_passive_devices": len(extracted_physical_passive_devices(extracted)),
                    "extracted_physical_passive_models": {"sky130_fd_pr__res_generic_m3": 1},
                    "extracted_intentional_passive_devices": count_extracted_intentional_passives(
                        extracted, instances
                    ),
                    "passive_tbd_layer_count": len(passive_tbd_layers(remap)),
                    "passive_tbd_layers": passive_tbd_layers(remap),
                    "magic_unknown_layer_count": len(parse_magic_unknown_layers(magic_log)),
                    "magic_unknown_layers": parse_magic_unknown_layers(magic_log),
                    "interpretation": "passive evidence test",
                },
            )

            self.assertEqual([item["instance"] for item in instances], ["xr0", "xc0"])
            self.assertEqual(len(found_gds), 2)
            self.assertEqual(passive_tbd_layers(remap), ["RPDMY:115/1"])
            self.assertEqual(parse_magic_unknown_layers(magic_log), ["115/1"])
            extracted_passives = extracted_physical_passive_devices(extracted)
            self.assertEqual(len(extracted_passives), 1)
            self.assertEqual(extracted_passives[0]["terminals"], ["a", "b"])
            self.assertEqual(count_extracted_intentional_passives(extracted, instances), 0)
            self.assertIn("Passive-Aware Extraction Integrity Report", report.read_text(encoding="utf-8"))
            self.assertIn("GDS remap report present", report.read_text(encoding="utf-8"))

    def test_lvs_preparation_diagnostic_helper_writes_passive_abstraction_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "amp.sp"
            source.write_text(
                ".subckt amp vdda gnda vin vip ibias vout\n"
                "xr0 net027 vout gnda rppolywo_m lr=4e-6\n"
                "xc0 outn net027 cfmom_2t nr=94\n"
                ".ends amp\n",
                encoding="utf-8",
            )
            extracted = root / "amp_extracted.spice"
            extracted.write_text(
                ".subckt amp_flat vdda vin vip ibias vout\n"
                "R0 m2_82_5771# m2_82_5771# sky130_fd_pr__res_generic_m3 w=1 l=2\n"
                ".ends\n",
                encoding="utf-8",
            )
            repo_root = Path(__file__).resolve().parents[3]

            diagnostic = run_lvs_preparation_diagnostic(
                repo_root=repo_root,
                source_netlist=source,
                extracted_netlist=extracted,
                out_dir=root / "probe",
                top_cell="AMP",
            )

            report = diagnostic["report"]
            self.assertEqual(diagnostic["status"], "pass")
            self.assertEqual(diagnostic["returncode"], 0)
            self.assertEqual(
                diagnostic["passive_abstraction_status"],
                "physical_passives_extracted_but_source_terminals_not_recovered",
            )
            self.assertEqual(
                parse_passive_abstraction_status(report),
                "physical_passives_extracted_but_source_terminals_not_recovered",
            )
            self.assertIn("Passive Abstraction Diagnostic", report.read_text(encoding="utf-8"))

    def test_gds_structure_diagnostic_helper_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            gds = root / "top.gds"
            gds.write_bytes(_minimal_text_gds("vout") + b"xr0")
            source = root / "amp.sp"
            source.write_text(
                ".subckt amp vdda gnda vout\n"
                "xr0 net027 vout gnda rppolywo_m lr=4e-6\n"
                ".ends amp\n",
                encoding="utf-8",
            )
            case_dir = root / "case"
            passive_gds_dir = case_dir / "gds"
            passive_gds_dir.mkdir(parents=True)
            (passive_gds_dir / "AMP_xr0.gds").write_bytes(_minimal_text_gds("pin0"))
            repo_root = Path(__file__).resolve().parents[3]

            diagnostic = run_gds_structure_diagnostic(
                repo_root=repo_root,
                gds_path=gds,
                source_netlist=source,
                case_dir=case_dir,
                out_dir=root / "probe",
                top_cell="AMP",
            )

            summary = diagnostic["summary"]
            self.assertEqual(diagnostic["status"], "pass")
            self.assertEqual(diagnostic["returncode"], 0)
            self.assertEqual(summary["top_gds"]["text_count"], 1)
            self.assertEqual(summary["source_passive_instance_names_present_count"], 1)
            self.assertEqual(summary["source_passive_terminal_names_present_count"], 1)
            self.assertEqual(summary["generated_passive_gds_present_count"], 1)
            self.assertTrue(diagnostic["report"].is_file())
            self.assertTrue(diagnostic["summary_json"].is_file())

    def test_passive_identity_reconstruction_helper_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "AMP.sp"
            source.write_text(
                ".subckt AMP vdda gnda outn vout\n"
                "xr0 net027 vout gnda rppolywo_m lr=4e-6\n"
                ".ends AMP\n",
                encoding="utf-8",
            )
            case_dir = root / "case"
            case_dir.mkdir()
            (case_dir / "AMP.pin").write_text(
                "1\n"
                "AMP_xr0 3\n"
                "4550 19350 4650 19850\n"
                "-50 -50 50 450\n"
                "-1\n",
                encoding="utf-8",
            )
            (case_dir / "AMP.gr").write_text(
                "gridStep 200\n"
                "net027 29 1 19350 33550 19450 34050 0 0\n"
                "vout 18 1 14750 14150 14850 14650 0 0\n",
                encoding="utf-8",
            )
            (case_dir / "run_AMP_trial.log").write_text(
                "node  AMP_xr0 14800 14200\n",
                encoding="utf-8",
            )
            repo_root = Path(__file__).resolve().parents[3]

            diagnostic = run_passive_identity_reconstruction(
                repo_root=repo_root,
                source_netlist=source,
                case_dir=case_dir,
                out_dir=root / "probe",
                top_cell="AMP",
                extracted_netlist=None,
            )

            summary = diagnostic["summary"]
            self.assertEqual(diagnostic["status"], "pass")
            self.assertEqual(diagnostic["returncode"], 0)
            self.assertEqual(
                summary["status"],
                "source_passive_pin_identity_reconstructed_from_magical_intermediates",
            )
            self.assertEqual(summary["source_passive_pin_exact_route_matches"], 2)
            self.assertEqual(summary["source_passive_pins_without_geometry"], 1)
            self.assertEqual(summary["source_passive_label_injection_candidates"], 2)
            self.assertTrue(diagnostic["report"].is_file())
            self.assertTrue(diagnostic["summary_json"].is_file())

    def test_passive_integrity_interpretation_reports_probe_stage_failure(self) -> None:
        interpretation = _passive_integrity_interpretation(
            probe_returncode=1,
            probe_pipeline_status="FAIL",
            probe_failed_stage="magical_place_route",
            remap_report_present=False,
            magic_extract_log_present=False,
            raw_extracted_present=False,
            source_passives=2,
            generated_passive_gds=2,
            dropped_passives=None,
            extracted_physical_passives=0,
            extracted_intentional_passives=0,
            passive_tbd_layer_count=0,
            magic_unknown_layer_count=0,
        )

        self.assertIn("magical_place_route", interpretation)
        self.assertIn("remap_report=missing", interpretation)

    def test_passive_terminal_recovery_reports_split_nets_and_port_shorts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            magic_log = root / "magic.log"
            magic_log.write_text(
                'Warning: Ports "gnda" and "vdda" are electrically shorted.\n',
                encoding="utf-8",
            )
            source_instances = [
                {"instance": "xr0", "model": "rppolywo_m", "terminals": ["net027", "vout", "gnda"]},
                {"instance": "xc0", "model": "cfmom_2t", "terminals": ["outn", "net027"]},
            ]
            extracted_devices = [
                {
                    "instance": "R1",
                    "model": "sky130_fd_pr__res_generic_m1",
                    "terminals": ["net027_uq0", "net027"],
                },
                {
                    "instance": "R5",
                    "model": "sky130_fd_pr__res_generic_m1",
                    "terminals": ["outn", "vdda"],
                },
            ]
            summary = passive_terminal_recovery_summary(
                source_instances=source_instances,
                extracted_devices=extracted_devices,
                magic_log=magic_log,
            )
            report = root / "terminal_recovery.md"
            write_passive_terminal_recovery_report(report, summary, extracted_devices)

            self.assertEqual(summary["status"], "partial_source_passive_terminal_recovery")
            self.assertEqual(summary["covered_source_passive_terminals"], ["net027", "outn"])
            self.assertEqual(summary["missing_source_passive_terminals"], ["gnda", "vout"])
            self.assertEqual(
                summary["split_source_passive_terminals"],
                [{"source_terminal": "net027", "extracted_terminal": "net027_uq0"}],
            )
            self.assertEqual(parse_magic_port_shorts(magic_log), [{"port_a": "gnda", "port_b": "vdda"}])
            self.assertIn("Passive Terminal Recovery Report", report.read_text(encoding="utf-8"))

    def test_passive_abstraction_readiness_helper_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "amp.sp"
            source.write_text(
                ".subckt amp vdda gnda vin vip ibias vout\n"
                "xr0 net027 vout gnda rppolywo_m lr=4e-6\n"
                "xc0 outn net027 cfmom_2t nr=94\n"
                ".ends amp\n",
                encoding="utf-8",
            )
            extracted = root / "amp_extracted.spice"
            extracted.write_text(
                ".subckt amp_flat vdda vin vip ibias vout net027 outn net027_uq0\n"
                "R1 net027_uq0 net027 sky130_fd_pr__res_generic_m1 w=0.12 l=0.06\n"
                "R5 outn vdda sky130_fd_pr__res_generic_m1 w=0.12 l=0.06\n"
                ".ends\n",
                encoding="utf-8",
            )
            magic_log = root / "magic.log"
            magic_log.write_text('Warning: Ports "gnda" and "vdda" are electrically shorted.\n', encoding="utf-8")
            identity = root / "identity.json"
            identity.write_text(
                '{"instances":[{"source_instance":"xr0","terminals":[{"terminal":"gnda","match_status":"no_pin_geometry"}]}]}',
                encoding="utf-8",
            )
            repo_root = Path(__file__).resolve().parents[3]

            diagnostic = run_passive_abstraction_readiness_diagnostic(
                repo_root=repo_root,
                source_netlist=source,
                extracted_netlist=extracted,
                out_dir=root / "probe",
                magic_log=magic_log,
                identity_json=identity,
            )

            summary = diagnostic["summary"]
            self.assertEqual(diagnostic["status"], "pass")
            self.assertEqual(summary["status"], "partial_passive_abstraction_readiness")
            self.assertEqual(summary["source_passives_candidate_for_abstraction"], 0)
            self.assertGreater(summary["blocker_count"], 0)
            self.assertTrue(diagnostic["report"].is_file())
            self.assertTrue(diagnostic["summary_json"].is_file())

    def test_candidate_store_records_jsonl_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CandidateStore(Path(tmpdir))
            packet = EvidencePacket(
                candidate_id="cand_0001",
                stage="layout_verification",
                fidelity="E2",
                status="pass",
                verification_scope="mos_only_projection",
            )
            store.append_evidence(packet)
            store.write_candidate_state("cand_0001", {"candidate_id": "cand_0001", "reward": 1.0})
            states = store.read_candidate_states()

            self.assertEqual(states[0]["candidate_id"], "cand_0001")
            self.assertTrue((Path(tmpdir) / "evidence" / "events.jsonl").is_file())

    def test_controller_backfills_formal_passive_artifact_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            candidate_dir = root / "cand_0001"
            variant_dir = candidate_dir / "layout_passive_existing_gds" / "resistor_remap_variants"
            variant_dir.mkdir(parents=True)
            (variant_dir / "resistor_remap_variant_probe_summary.json").write_text(
                json.dumps(
                    {
                        "best_formal_lvs_abstraction_ready": True,
                        "best_all_source_passives_have_candidate": True,
                        "best_passive_abs_netgen_status": "pass",
                        "best_hybrid_mos_passive_lvs_trial_netgen_status": "pass",
                        "best_passive_aware_lvs_trial_netgen_status": "fail",
                        "best_route_bridge_trial_status": "pass",
                        "best_route_bridge_drc_count": 0,
                        "best_route_bridge_mos_connectivity_status": "pass",
                        "best_route_bridge_formal_passive_lvs_netgen_status": "pass",
                    }
                ),
                encoding="utf-8",
            )
            (variant_dir / "passive_lvs_evidence_summary.json").write_text(
                json.dumps(
                    {
                        "status": "formal_passive_lvs_evidence_pass",
                        "formal_passive_lvs_evidence_pass": True,
                        "full_passive_inclusive_gds_lvs_proven": False,
                        "verification_scope": "formal_passive_abstraction_with_gds_mos_bridge",
                        "requirements": {
                            "segmented_resistor_chain_formalized": True,
                            "cfmom_plate_coupling_formalized": True,
                        },
                        "route_bridge_requirements": {
                            "route_bridge_drc_clean": True,
                            "route_bridge_mos_connectivity_pass": True,
                            "route_bridge_formal_passive_lvs_pass": True,
                        },
                        "lvs_primitive_abstractions": [
                            {
                                "source_instance": "xr0",
                                "lvs_primitive_device_class": "r",
                            },
                            {
                                "source_instance": "xc0",
                                "lvs_primitive_device_class": "c",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            native_dir = variant_dir / "native_passive_retarget_trial"
            native_dir.mkdir()
            (native_dir / "native_passive_retarget_summary.json").write_text(
                json.dumps(
                    {
                        "status": "native_passive_retarget_incomplete",
                        "native_resistor_chain_status": "pass",
                        "native_resistor_chain_source_instance": "xr0",
                        "native_resistor_chain_device_count": 31,
                        "native_resistor_chain_model": ["sky130_fd_pr__res_xhigh_po"],
                        "native_resistor_chain_netgen_status": "pass",
                        "native_resistor_chain_netgen": {
                            "report": str(native_dir / "res_netgen.out"),
                            "log": str(native_dir / "res_netgen.log"),
                        },
                        "native_capacitor_device_recognition_status": "fail",
                        "missing_native_source_passive_instances": ["xc0"],
                        "full_native_passive_lvs_ready": False,
                        "full_native_passive_lvs_proven": False,
                        "source_native_passive_netlist": str(native_dir / "source_native.spice"),
                        "candidate_native_passive_netlist": str(native_dir / "candidate_native.spice"),
                    }
                ),
                encoding="utf-8",
            )
            cap_gencell_dir = variant_dir / "native_cap_gencell_probe"
            cap_gencell_dir.mkdir()
            (cap_gencell_dir / "native_cap_gencell_summary.json").write_text(
                json.dumps(
                    {
                        "native_cap_gencell_extraction_status": "pass",
                        "model": "sky130_fd_pr__cap_mim_m3_1",
                        "cell_name": "sky130_native_cap_gencell_probe",
                        "recognized_native_capacitor_device_count": 1,
                        "native_capacitor_devices": [
                            {
                                "instance": "X0",
                                "terminals": ["C1", "C2"],
                                "model": "sky130_fd_pr__cap_mim_m3_1",
                            }
                        ],
                        "log": str(cap_gencell_dir / "magic.log"),
                        "spice": str(cap_gencell_dir / "cap.spice"),
                        "mag": str(cap_gencell_dir / "cap.mag"),
                        "gds": str(cap_gencell_dir / "cap.gds"),
                        "ext": str(cap_gencell_dir / "cap.ext"),
                    }
                ),
                encoding="utf-8",
            )
            cap_replacement_dir = variant_dir / "native_cap_replacement_candidate"
            cap_replacement_dir.mkdir()
            (cap_replacement_dir / "native_cap_replacement_summary.json").write_text(
                json.dumps(
                    {
                        "status": "replacement_candidate_prepared",
                        "replacement_cell_name": "AMP_xc0",
                        "replacement_gds": str(cap_replacement_dir / "AMP_xc0.gds"),
                        "replacement_spice": str(cap_replacement_dir / "AMP_xc0.spice"),
                        "replacement_magic_log": str(cap_replacement_dir / "magic.log"),
                        "terminal_bridge_status": "not_implemented",
                        "top_gds_merge_status": "not_implemented",
                        "full_native_capacitor_lvs_ready": False,
                        "remaining_gates": ["bridge C1/C2", "merge top GDS"],
                    }
                ),
                encoding="utf-8",
            )
            controller = object.__new__(HarnessController)
            controller.config = SimpleNamespace(
                run_dir=root,
                verification_scope="mos_only_projection",
                performance={},
            )
            state = {
                "candidate_id": "cand_0001",
                "reward": 0.0,
                "artifacts": {"candidate_dir": str(candidate_dir)},
                "evidence": [
                    EvidencePacket(
                        candidate_id="cand_0001",
                        stage="layout_verification",
                        fidelity="E2",
                        status="pass",
                        verification_scope="mos_only_projection",
                    ).to_dict(),
                    EvidencePacket(
                        candidate_id="cand_0001",
                        stage="passive_aware_lvs",
                        fidelity="E2P",
                        status="formal_abstraction_with_gds_mos_bridge_pass",
                        verification_scope="formal_passive_abstraction_with_gds_mos_bridge",
                    ).to_dict(),
                ],
            }

            normalized = controller._state_with_current_scores(state)
            passive_packet = next(
                packet for packet in normalized["evidence"] if packet["stage"] == "passive_aware_lvs"
            )

            self.assertTrue(normalized["passive_evidence_backfilled_from_artifacts"])
            self.assertEqual(
                passive_packet["status"],
                "formal_abstraction_with_gds_mos_bridge_pass",
            )
            self.assertEqual(
                passive_packet["verification_scope"],
                "formal_passive_abstraction_with_gds_mos_bridge",
            )
            self.assertTrue(
                passive_packet["metrics"]["passive_requirement_segmented_resistor_chain_formalized"]
            )
            self.assertTrue(
                passive_packet["metrics"]["passive_requirement_cfmom_plate_coupling_formalized"]
            )
            primitive_records = {
                item["source_instance"]: item
                for item in passive_packet["metrics"]["passive_lvs_primitive_abstractions"]
            }
            self.assertEqual(primitive_records["xr0"]["lvs_primitive_device_class"], "r")
            self.assertEqual(primitive_records["xc0"]["lvs_primitive_device_class"], "c")
            self.assertFalse(passive_packet["metrics"]["full_passive_inclusive_gds_lvs_proven"])
            self.assertEqual(passive_packet["metrics"]["native_resistor_chain_status"], "pass")
            self.assertEqual(passive_packet["metrics"]["native_resistor_chain_netgen_status"], "pass")
            self.assertEqual(passive_packet["metrics"]["native_resistor_chain_device_count"], 31)
            self.assertEqual(
                passive_packet["metrics"]["native_capacitor_device_recognition_status"],
                "fail",
            )
            self.assertEqual(
                passive_packet["metrics"]["native_passive_retarget_missing_native_source_passive_instances"],
                ["xc0"],
            )
            self.assertFalse(
                passive_packet["metrics"]["native_passive_retarget_full_native_passive_lvs_proven"]
            )
            self.assertEqual(passive_packet["metrics"]["native_cap_gencell_extraction_status"], "pass")
            self.assertEqual(
                passive_packet["metrics"]["native_cap_gencell_model"],
                "sky130_fd_pr__cap_mim_m3_1",
            )
            self.assertEqual(passive_packet["metrics"]["native_cap_gencell_recognized_device_count"], 1)
            self.assertEqual(
                passive_packet["metrics"]["native_cap_replacement_status"],
                "replacement_candidate_prepared",
            )
            self.assertEqual(
                passive_packet["metrics"]["native_cap_replacement_terminal_bridge_status"],
                "not_implemented",
            )
            self.assertFalse(
                passive_packet["metrics"]["native_cap_replacement_full_native_capacitor_lvs_ready"]
            )
            self.assertIn("native_passive_retarget_report", passive_packet["artifacts"])
            self.assertIn("native_resistor_chain_netgen_report", passive_packet["artifacts"])
            self.assertIn("native_cap_gencell_spice", passive_packet["artifacts"])
            self.assertIn("native_cap_gencell_gds", passive_packet["artifacts"])
            self.assertIn("native_cap_replacement_gds", passive_packet["artifacts"])


if __name__ == "__main__":
    unittest.main()
