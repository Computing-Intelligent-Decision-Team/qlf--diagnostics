#!/usr/bin/env python3
"""Parasitic modeling dataset v0: extract PEX data from AnalogHarness artifacts.

Produces a JSONL dataset where each line is one circuit candidate with
parasitic capacitance edges, per-node capacitance, and trust metadata.

Samples are NOT all training-safe. Trust scope is recorded per-sample:
  - SMCNR/cand_0031: verified positive, LVS PASS
  - Fan_SMC: LVS FAIL, failure-case only
  - DFCFC2: LVS FAIL, failure-case only
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
CURATED_FIXTURE_ROOT = REPO_ROOT / "tools" / "analog_harness" / "fixtures"


@dataclass
class ParasiticEdge:
    src: str
    dst: str
    cap_ff: float
    cap_id: str = ""


@dataclass
class ParasiticSample:
    sample_id: str
    circuit: str
    candidate_id: str
    lvs_status: str
    trust_scope: str
    usable_for_supervised_positive_training: bool
    pex_caps: int
    pex_total_cap_ff: float
    usable_for_parasitic_modeling: bool = True
    usable_only_as_failure_case: bool = False
    candidate_for_parasitic_modeling_review: bool = False
    evidence_scope: str = ""
    diversity_class: str = ""
    parasitic_edges: list[ParasiticEdge] = field(default_factory=list)
    per_node_cap_ff: dict[str, float] = field(default_factory=dict)
    graph_features: dict[str, Any] = field(default_factory=dict)
    source_artifacts: dict[str, str] = field(default_factory=dict)
    provenance_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["parasitic_edges"] = [asdict(e) for e in self.parasitic_edges]
        return d


# ── Registry of known samples ──

SAMPLE_REGISTRY = [
    {
        "sample_id": "smcnr_se_2st_amp_cand_0031",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "cand_0031",
        "lvs_status": "PASS",
        "trust_scope": "full_passive_inclusive_gds_lvs",
        "usable_for_supervised_positive_training": True,
        "usable_for_parasitic_modeling": True,
        "usable_only_as_failure_case": False,
        "provenance_note": "Reviewed SMCNR positive baseline; passive scope is accepted as backfilled evidence from curated artifacts.",
        "raw_spice_path": str(CURATED_FIXTURE_ROOT / "smcnr_se_2st_amp_cand_0031.raw.spice"),
        "pex_summary_path": "/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/pex_summary.md",
        "state_path": "/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json",
        "regenerated_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_023/SMCNR_SE_2st_AMP_flat.spice",
        "regenerated_ext_path": "/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_023/SMCNR_SE_2st_AMP_flat.ext",
    },
    {
        "sample_id": "fan_smc_c0_proxy_psub_tap",
        "circuit": "Fan_SMC_Pin_3",
        "candidate_id": "psub_tap_baseline",
        "lvs_status": "FAIL",
        "trust_scope": "failure_case_only",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": True,
        "usable_only_as_failure_case": True,
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/fan_smc_pin_3_extracted.raw.spice",
        "ext_path": "/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext",
        "device_mapping_path": "/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/device_mapping.json",
        "trust_decision_path": "/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/trust_decision.json",
        "failure_note": "substrate/equiv collapse restructures extracted connectivity; LVS FAIL",
    },
    {
        "sample_id": "fan_smc_c0_proxy_guardring_true",
        "circuit": "Fan_SMC_Pin_3",
        "candidate_id": "guardring_true",
        "lvs_status": "FAIL",
        "trust_scope": "failure_case_only",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": True,
        "usable_only_as_failure_case": True,
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_021/guardring_true/case/fan_smc_pin_3_flat.spice",
        "failure_note": "useDeviceSubGuardRing=true changed extraction but did not resolve collapse",
    },
    {
        "sample_id": "dfcfc2_mim_proxy",
        "circuit": "AMP_DFCFC2",
        "candidate_id": "mim_proxy_full_pipeline",
        "lvs_status": "FAIL",
        "trust_scope": "failure_case_only",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": True,
        "usable_only_as_failure_case": True,
        "raw_spice_path": "/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/Leung_DFCFC2_Pin_3_extracted.raw.spice",
        "pex_summary_path": "/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/pex_summary.md",
        "harness_decision_path": "/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/harness_decision.json",
        "failure_note": "substrate collapse + MIM cap mapping failure; 26→52 device count mismatch",
    },
    {
        "sample_id": "dfcfc2_mos_only_rerun",
        "circuit": "AMP_DFCFC2",
        "candidate_id": "default_vars_mos_only_rerun",
        "lvs_status": "FAIL",
        "trust_scope": "failure_case_only",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": True,
        "usable_only_as_failure_case": True,
        "raw_spice_path": "/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_current_code_rerun_full_pipeline/Leung_DFCFC2_Pin_3_extracted.raw.spice",
        "pex_summary_path": "/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_current_code_rerun_full_pipeline/pex_summary.md",
        "harness_decision_path": "/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_current_code_rerun_full_pipeline/harness_decision.json",
        "failure_note": "substrate collapse; device count mismatch; missing gnda port",
    },
    {
        "sample_id": "leung_nmcnr_mos_only",
        "circuit": "Leung_NMCNR_Pin_3",
        "candidate_id": "leung_nmcnr_mos_only_default",
        "lvs_status": "FAIL",
        "trust_scope": "failure_case_only",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "usable_only_as_failure_case": True,
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/nmcnr_mos_only_projection/leung_nmcnr_mos_only_flat.spice",
        "ext_path": "/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/nmcnr_mos_only_projection/leung_nmcnr_mos_only_flat.ext",
        "lvs_log_path": "/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/nmcnr_mos_only_projection/lvs.log",
        "probe_report_path": "/home/qlf/IOT/references/AnalogHarness/docs/nmcnr_mos_only_layout_probe.md",
        "failure_note": "MOS-only projection LVS FAIL: well-merging collapse absorbs 9 source nets into w_n35_1245# (n-well); 24 MOS pass DRC 0 but extracted connectivity is restructured; equiv=0 but net merging confirmed via LVS log (33 vs 21 nets)",
    },
    {
        "sample_id": "l_002_bias_pmos_l_p5",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "l_002_bias_pmos_l_p5",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "usable_only_as_failure_case": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_002_bias_pmos_l_p5/SMCNR_SE_2st_AMP_flat.spice",
        "ext_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_002_bias_pmos_l_p5/SMCNR_SE_2st_AMP_flat.ext",
        "lvs_log_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_002_bias_pmos_l_p5/lvs.log",
        "provenance_note": "PMOS-L structural-diverse variant: bias_pmos_l +5% (10.0→10.5). MOS-only projection. LVS PASS (8 dev, 9 nets). PEX 36 caps, +1.10 fF vs baseline.",
    },
    {
        "sample_id": "l_007_second_stage_pmos_l_m5",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "l_007_second_stage_pmos_l_m5",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "usable_only_as_failure_case": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_007_second_stage_pmos_l_m5/SMCNR_SE_2st_AMP_flat.spice",
        "ext_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_007_second_stage_pmos_l_m5/SMCNR_SE_2st_AMP_flat.ext",
        "lvs_log_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_007_second_stage_pmos_l_m5/lvs.log",
        "provenance_note": "PMOS-L structural-diverse variant: second_stage_pmos_l -5% (10.0→9.5). MOS-only projection. LVS PASS (8 dev, 9 nets). PEX 36 caps, -0.28 fF vs baseline.",
    },
    {
        "sample_id": "l_008_second_stage_pmos_l_p5",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "l_008_second_stage_pmos_l_p5",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "usable_only_as_failure_case": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_008_second_stage_pmos_l_p5/SMCNR_SE_2st_AMP_flat.spice",
        "ext_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_008_second_stage_pmos_l_p5/SMCNR_SE_2st_AMP_flat.ext",
        "lvs_log_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_008_second_stage_pmos_l_p5/lvs_renamed.log",
        "provenance_note": "PMOS-L structural-diverse variant: second_stage_pmos_l +5% (10.0→10.5). MOS-only projection. LVS PASS after rename fix (8 dev, 9 nets). PEX 35 caps, -2.02 fF vs baseline — strongest diversity signal.",
    },
    {
        "sample_id": "l_001_bias_pmos_l_m5",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "l_001_bias_pmos_l_m5",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "usable_only_as_failure_case": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_001_bias_pmos_l_m5/SMCNR_SE_2st_AMP_flat.spice",
        "ext_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_001_bias_pmos_l_m5/SMCNR_SE_2st_AMP_flat.ext",
        "provenance_note": "PMOS-L structural-diverse variant: bias_pmos_l -5% (10.0→9.5). Same parameters as wl_005. MOS-only projection. LVS PASS. PEX 36 caps, -0.70 fF vs baseline.",
    },
    {
        "sample_id": "mc0002_bias_pmos_l_0p95_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_0p95_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_0p95_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l -5%. LVS PASS. 36 caps, 80.2488 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_0p96_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_0p96_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_0p96_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l -4%. LVS PASS. 36 caps, 80.3002 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_0p97_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_0p97_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_0p97_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l -3%. LVS PASS. 36 caps, 80.5801 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_0p98_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_0p98_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_0p98_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l -2%. LVS PASS. 36 caps, 80.6316 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_0p99_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_0p99_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_0p99_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l -1%. LVS PASS. 37 caps, 80.8933 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_1p005_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_1p005_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_1p005_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l +0%. LVS PASS. 36 caps, 81.2503 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_1p01_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_1p01_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_1p01_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l +1%. LVS PASS. 36 caps, 81.2766 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_1p015_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_1p015_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_1p015_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l +1%. LVS PASS. 36 caps, 81.3028 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_1p02_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_1p02_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_1p02_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l +2%. LVS PASS. 36 caps, 81.329 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_1p025_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_1p025_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_1p025_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l +2%. LVS PASS. 36 caps, 81.5792 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_1p03_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_1p03_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_1p03_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l +3%. LVS PASS. 36 caps, 81.6054 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_1p04_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_1p04_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_1p04_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l +4%. LVS PASS. 36 caps, 81.6579 fF."
    },
    {
        "sample_id": "mc0002_bias_pmos_l_1p05_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_bias_pmos_l_1p05_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_bias_pmos_l_1p05_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: bias_pmos_l +5%. LVS PASS. 36 caps, 82.0475 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_0p95_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_0p95_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_0p95_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l -5%. LVS PASS. 36 caps, 80.6681 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_0p96_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_0p96_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_0p96_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l -4%. LVS PASS. 36 caps, 80.693 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_0p97_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_0p97_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_0p97_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l -3%. LVS PASS. 37 caps, 80.7073 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_0p98_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_0p98_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_0p98_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l -2%. LVS PASS. 37 caps, 80.7323 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_0p99_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_0p99_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_0p99_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l -1%. LVS PASS. 37 caps, 80.9197 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_1p005_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_1p005_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_1p005_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l +0%. LVS PASS. 37 caps, 81.0299 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_1p01_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_1p01_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_1p01_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l +1%. LVS PASS. 37 caps, 81.043 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_1p02_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_1p02_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_1p02_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l +2%. LVS PASS. 37 caps, 81.069 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_1p025_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_1p025_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_1p025_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l +2%. LVS PASS. 36 caps, 81.2492 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_1p03_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_1p03_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_1p03_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l +3%. LVS PASS. 36 caps, 81.2622 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_1p04_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_1p04_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_1p04_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l +4%. LVS PASS. 36 caps, 81.2884 fF."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_1p05_seed01_rejected",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_1p05_seed01",
        "lvs_status": "FAIL",
        "trust_scope": "failure_case_only",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "usable_only_as_failure_case": True,
        "diversity_class": "rejected",
        "evidence_scope": "mos_only_projection_lvs_failed",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_1p05_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "failure_note": "MC0002 second_stage_pmos_l +5%: LVS FAIL device_mismatch 8 vs 7."
    },
    {
        "sample_id": "mc0002_second_stage_pmos_l_1p015_seed01",
        "circuit": "SMCNR_SE_2st_AMP",
        "candidate_id": "mc0002_second_stage_pmos_l_1p015_seed01",
        "lvs_status": "PASS",
        "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": True,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "structural_diverse",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/mc_pmos_l_0002/mc0002_second_stage_pmos_l_1p015_seed01/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "MC0002 PMOS-L: second_stage_pmos_l +1.5%. LVS PASS. 36 caps, 81.0556 fF."
    },
    {
        "sample_id": "l_003_load_nmos_l_m5",
        "circuit": "SMCNR_SE_2st_AMP", "candidate_id": "l_003_load_nmos_l_m5",
        "lvs_status": "PASS", "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": False,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "marginal_numeric",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_003_load_nmos_l_m5/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "NMOS-L marginal_numeric: load_nmos_l -5%. LVS PASS. 37 caps, 80.6173 fF.",
    },
    {
        "sample_id": "l_004_load_nmos_l_p5",
        "circuit": "SMCNR_SE_2st_AMP", "candidate_id": "l_004_load_nmos_l_p5",
        "lvs_status": "PASS", "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": False,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "marginal_numeric",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_004_load_nmos_l_p5/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "NMOS-L marginal_numeric: load_nmos_l +5%. LVS PASS. 37 caps, 81.3069 fF.",
    },
    {
        "sample_id": "l_005_second_stage_nmos_l_m5",
        "circuit": "SMCNR_SE_2st_AMP", "candidate_id": "l_005_second_stage_nmos_l_m5",
        "lvs_status": "PASS", "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": False,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "marginal_numeric",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_005_second_stage_nmos_l_m5/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "NMOS-L marginal_numeric: 2nd_stage_nmos_l -5%. LVS PASS. 37 caps, 80.72 fF.",
    },
    {
        "sample_id": "l_006_second_stage_nmos_l_p5",
        "circuit": "SMCNR_SE_2st_AMP", "candidate_id": "l_006_second_stage_nmos_l_p5",
        "lvs_status": "PASS", "trust_scope": "mos_only_projection",
        "usable_for_supervised_positive_training": False,
        "usable_for_parasitic_modeling": False,
        "candidate_for_parasitic_modeling_review": False,
        "evidence_scope": "mos_only_projection",
        "diversity_class": "marginal_numeric",
        "raw_spice_path": "/home/qlf/IOT/references/AnalogHarness/generated/smcnr_variants/l_only_sweep/l_006_second_stage_nmos_l_p5/SMCNR_SE_2st_AMP_flat.spice",
        "provenance_note": "NMOS-L marginal_numeric: 2nd_stage_nmos_l +5%. LVS PASS. 37 caps, 81.2729 fF.",
    }
]


# ── Extraction functions ──


def _cap_to_ff(value: str, suffix: str | None) -> float:
    raw_value = float(value)
    if suffix == "p":
        return raw_value * 1000.0
    if suffix == "n":
        return raw_value * 1_000_000.0
    if suffix == "f":
        return raw_value
    return raw_value * 1e15


def parse_extracted_spice(path: str) -> tuple[list[ParasiticEdge], dict[str, float], float]:
    """Parse an ngspice extracted SPICE file for parasitic capacitors.

    Returns (edges, per_node_cap, total_cap).
    """
    edges: list[ParasiticEdge] = []
    per_node: dict[str, float] = {}
    total = 0.0

    try:
        with open(path) as f:
            for line in f:
                # Skip lines with only noise tokens
                stripped = line.strip()
                # Strip trailing comments ($ ...)
                if "$" in stripped:
                    stripped = stripped.split("$")[0].strip()

                # Match: C<n> net_a net_b value[f|p|n]
                m = re.match(
                    r"^(C\d+)\s+(\S+)\s+(\S+)\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([fpn])?\s*$",
                    stripped,
                    flags=re.IGNORECASE,
                )
                if m:
                    cap_id, a, b = m.group(1), m.group(2), m.group(3)
                    value_ff = _cap_to_ff(m.group(4), (m.group(5) or "").lower() or None)
                    edges.append(ParasiticEdge(src=a, dst=b, cap_ff=value_ff, cap_id=cap_id))
                    per_node[a] = per_node.get(a, 0.0) + value_ff
                    per_node[b] = per_node.get(b, 0.0) + value_ff
                    total += value_ff
    except FileNotFoundError:
        pass

    return edges, per_node, total


def extract_basic_graph_features(spice_path: str) -> dict[str, Any]:
    """Extract basic graph features from the extracted SPICE.

    Returns MOS count, net count, model counts, etc.
    """
    features: dict[str, Any] = {
        "mos_count": 0,
        "net_count": 0,
        "pmos_count": 0,
        "nmos_count": 0,
        "passive_count": 0,
    }
    try:
        nets = set()
        with open(spice_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("X") or line.startswith("M"):
                    if "nfet_01v8" in line or "nfet" in line:
                        features["nmos_count"] += 1
                        features["mos_count"] += 1
                    elif "pfet_01v8" in line or "pfet" in line:
                        features["pmos_count"] += 1
                        features["mos_count"] += 1
                    elif "sky130_fd_pr__" in line and "nfet" not in line and "pfet" not in line:
                        features["passive_count"] += 1
                    # Collect nets from device terminals
                    parts = line.split()
                    for token in parts[1:5]:
                        if not token.startswith("sky130") and not token.startswith("w=") and not token.startswith("l="):
                            if token and not token[0].isdigit():
                                nets.add(token)
    except FileNotFoundError:
        pass

    features["net_count"] = len(nets)
    return features


def build_sample(entry: dict[str, Any]) -> ParasiticSample:
    """Build a ParasiticSample from a registry entry."""
    sample = ParasiticSample(
        sample_id=entry["sample_id"],
        circuit=entry["circuit"],
        candidate_id=entry["candidate_id"],
        lvs_status=entry["lvs_status"],
        trust_scope=entry["trust_scope"],
        usable_for_supervised_positive_training=entry["usable_for_supervised_positive_training"],
        pex_caps=0,
        pex_total_cap_ff=0.0,
        usable_for_parasitic_modeling=entry.get("usable_for_parasitic_modeling", True),
        usable_only_as_failure_case=entry.get("usable_only_as_failure_case", False),
        candidate_for_parasitic_modeling_review=entry.get("candidate_for_parasitic_modeling_review", False),
        evidence_scope=entry.get("evidence_scope", ""),
        diversity_class=entry.get("diversity_class", ""),
        provenance_note=entry.get("provenance_note") or entry.get("failure_note", ""),
    )

    # Parse extracted SPICE
    spice_path = entry.get("raw_spice_path", "")
    if spice_path:
        edges, per_node, total = parse_extracted_spice(spice_path)
        sample.parasitic_edges = edges
        sample.per_node_cap_ff = per_node
        sample.pex_caps = len(edges)
        sample.pex_total_cap_ff = round(total, 4)
        sample.graph_features = extract_basic_graph_features(spice_path)

    # Record source artifacts
    for key in ["raw_spice_path", "pex_summary_path", "state_path", "ext_path",
                "device_mapping_path", "trust_decision_path", "harness_decision_path",
                "regenerated_spice_path", "regenerated_ext_path"]:
        if key in entry and entry[key]:
            artifact_name = key.replace("_path", "")
            sample.source_artifacts[artifact_name] = entry[key]

    return sample


def build_dataset(output_path: str | None = None) -> list[ParasiticSample]:
    """Build the full dataset from the registry.

    If output_path is provided, writes JSONL.
    Returns the list of samples.
    """
    samples = [build_sample(entry) for entry in SAMPLE_REGISTRY]

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            for s in samples:
                f.write(json.dumps(s.to_dict()) + "\n")

    return samples


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build parasitic modeling dataset v0")
    parser.add_argument("--output", type=str, default=None, help="Output JSONL path")
    parser.add_argument("--summary", action="store_true", help="Print summary to stdout")
    args = parser.parse_args()

    samples = build_dataset(args.output)

    if args.summary:
        print("Parasitic Modeling Dataset v0")
        print(f"Total samples: {len(samples)}")
        for s in samples:
            if s.usable_for_supervised_positive_training:
                pos = "POSITIVE"
            elif getattr(s, 'candidate_for_parasitic_modeling_review', False):
                pos = "review-pool"
            elif getattr(s, 'diversity_class', '') == 'marginal_numeric':
                pos = "marginal"
            elif s.usable_only_as_failure_case:
                pos = "failure-only"
            else:
                pos = "unclassified"
            print(f"  {s.sample_id}: {s.lvs_status} | {s.pex_caps} caps | {s.pex_total_cap_ff:.1f} fF | {pos}")

    if args.output:
        print(f"Dataset written to {args.output}")


if __name__ == "__main__":
    main()
