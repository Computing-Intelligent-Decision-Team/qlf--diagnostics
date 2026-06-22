# DFCFC2/Fan_SMC Artifact Inventory

Generated from a read-only scan of `/home/qlf/IOT/references/MAGICAL-`.

Do not treat an artifact as proof of AnalogHarness closure by itself. The goal
is to make old MAGICAL- evidence auditable and mappable into AnalogHarness
diagnostics/trust-gate decisions.

## Scan Metadata

| Field | Value |
| --- | --- |
| Scanner | Claude Code |
| Scan date | 2026-06-20 |
| Source repo | `/home/qlf/IOT/references/MAGICAL-` |
| Target repo | `/home/qlf/IOT/references/AnalogHarness` |
| Commands run | `find ... -iname "*dfcfc*"`, `find ... -iname "*fan_smc*"`, `find ... -iname "*leung*"`, `find ... -name "summary.md"`, `find ... -name "*.json"`, `find ... -name "*.log"`, `find ... -name "*.out"`, `ls -laR` on key directories, `cat`/`head`/`read` on evidence files; `grep -r "post_layout\|pvt"` on canonical run directories |
| Files modified | `docs/dfcfc2_smc_artifact_inventory.md` only |

## Executive Summary

- DFCFC2 artifact count: **~85 experiment directories** with 3 canonical full-pipeline runs containing structured evidence; all audited runs LVS=FAIL
- Fan_SMC/Fan_SMC_Pin_3 artifact count: **~20 extract variants** across 2 major branches (main + smc09_no_c0); all audited runs LVS=FAIL
- Strongest negative sample candidate: **DFCFC2 `mim_proxy_full_pipeline_with_lvs_diagnosis`** — observed Magic DRC count 0 (in partially remapped run), PEX=103 caps/865 fF, LVS=FAIL
- Most common failure category: **`device_mismatch`** + **`net_mismatch`** (DFCFC2); **`power_domain_short`** + **`net_mismatch`** (Fan_SMC)
- Missing evidence that blocks trust-gate conversion:
  - No post-layout ngspice simulation found in audited canonical DFCFC2 and Fan_SMC runs
  - No PVT sweep found in audited canonical DFCFC2 and Fan_SMC runs
  - No LVS=pass for any audited run (both circuits fail LVS in all observed canonical variants)
  - No passive-aware full-GDS evidence for either circuit (MIM capacitor mapping remains unresolved)
  - DFCFC2 source net port `gnda` consistently missing from extracted ports (recorded in LVS diagnosis)

---

## Artifact Inventory

### Section A: DFCFC2 Canonical Full-Pipeline Runs

| ID | Circuit | Absolute path | Artifact class | Local status | Failure category | Feeds diagnostic | Evidence strength | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A001 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/summary.md` | `other` | **local** | `device_mismatch`, `net_mismatch` | `sample_trust_gate` | `summary only` | Pipeline summary. Observed DRC count 0 in partially remapped run; PEX=103/865fF; LVS=FAIL. Most complete structured evidence bundle. |
| A002 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/magic_drc.log` | `magic_drc_log` | **local** | — (DRC count 0 observed) | `artifact_verifier` | `direct log` | Magic 8.3.483. Total DRC errors found: 0. 12 TBD layer/datatype read errors present; DRC count 0 is from this partially remapped run. |
| A003 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/magic_extract.log` | `magic_extract_log` | **local** | — (extraction completed) | `pex_structuring` | `direct log` | Magic extraction completed. TBD layer warnings present but extraction produced .ext and .spice. |
| A004 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/Leung_DFCFC2_Pin_3_extracted.spice` | `extracted_raw_spice` | **local** | — (extracted netlist present) | `pex_structuring` | `direct log` | Raw extracted SPICE. Contains 103 parasitic capacitors. |
| A005 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/Leung_DFCFC2_Pin_3_extracted.raw.spice` | `extracted_raw_spice` | **local** | — | `pex_structuring` | `direct log` | Copy of raw extracted SPICE. |
| A006 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/Leung_DFCFC2_Pin_3_source.connectivity.spice` | `other` | **local** | — | `lvs_failure_taxonomy` | `direct log` | Connectivity-normalized source netlist for LVS. |
| A007 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/Leung_DFCFC2_Pin_3_extracted.connectivity.spice` | `other` | **local** | — | `lvs_failure_taxonomy` | `direct log` | Connectivity-normalized extracted netlist for LVS. |
| A008 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/netgen_lvs_report.out` | `netgen_lvs_report` | **local** | `device_mismatch`, `net_mismatch` | `lvs_failure_taxonomy` | `direct log` | Full Netgen report. Source MOS=26 vs extracted MOS=52. Device and net mismatch confirmed. |
| A009 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/netgen_lvs.log` | `netgen_lvs_report` | **local** | `device_mismatch`, `net_mismatch` | `lvs_failure_taxonomy` | `direct log` | Netgen log. Netgen 1.5.133. cfmom_2t placeholder cells, property warnings. |
| A010 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/lvs_result_summary.md` | `netgen_lvs_report` | **local** | `device_mismatch`, `net_mismatch` | `lvs_failure_taxonomy` | `summary only` | Summarized LVS result: FAIL, device mismatch=yes, net mismatch=yes. |
| A011 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/lvs_decomposition_diagnosis.json` | `other` | **local** | `device_mismatch`, `net_mismatch` | `lvs_failure_taxonomy` | `structured json` | LVS decomposition diagnosis. Records device count mismatch (26 vs 52). Also documents power-ground short, missing extracted port gnda, missing capacitor proxy, and route warning net31 in diagnostic detail fields. |
| A012 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/pex_summary.md` | `pex_summary` | **local** | `pex_without_lvs` | `pex_structuring` | `summary only` | PEX: 103 caps, 865.01 fF total. vout=363 fF. Largest cap: C100 a_830_5820#↔vdda 371.25 fF. |
| A013 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/parasitic_summary.json` | `parasitic_summary` | **local** | `pex_without_lvs` | `pex_structuring` | `structured json` | Structured PEX summary. |
| A014 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/risk_report.json` | `risk_report` | **local** | `pex_without_lvs` | `sample_trust_gate` | `structured json` | V1 parasitic risk report. 3 findings: bias_node_cap (observation), output_node_cap (warning, 363fF), large_unmapped_extracted_net (warning, 707fF). |
| A015 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/harness_decision.json` | `harness_decision` | **local** | `device_mismatch`, `net_mismatch` | `sample_trust_gate` | `structured json` | Decision: reject_pipeline_artifact, usable_for_training=false. Blocking reasons include lvs_not_matched. |
| A016 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/sample_record.json` | `other` | **local** | `pex_without_lvs` | `pex_structuring` | `structured json` | Graph-learning sample record. training_sample.usable_for_graph_learning=false. |
| A017 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/gds_remap_report.md` | `other` | **local** | — (remap completed) | `artifact_verifier` | `summary only` | GDS remap report. 31 input layers: 17 remapped, 12 TBD, 2 unmapped. Layers 150/155 preserved as TBD. |
| A018 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/magical_route_log_report.json` | `other` | **local** | `unknown` | `artifact_verifier` | `structured json` | MAGICAL route log report. Route status: completed_with_route_warnings. Failed net: net31 (noted in LVS diagnosis). |
| A019 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/circuit_graph.json` | `other` | **local** | — | `pex_structuring` | `structured json` | Circuit graph for graph-learning integration. |
| A020 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/lvs_preparation_report.md` | `other` | **local** | — | `lvs_failure_taxonomy` | `summary only` | LVS preparation report. Connectivity normalization performed, parasitic caps removed. |

### Section B: DFCFC2 Latest Rerun (MOS-only, current code)

| ID | Circuit | Absolute path | Artifact class | Local status | Failure category | Feeds diagnostic | Evidence strength | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B001 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_current_code_rerun_full_pipeline/summary.md` | `other` | **local** | `device_mismatch`, `net_mismatch` | `sample_trust_gate` | `summary only` | Pipeline summary. Latest MOS-only rerun: DRC count 0, PEX=51/34.9fF, LVS=FAIL. |
| B002 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_current_code_rerun_full_pipeline/magic_drc.log` | `magic_drc_log` | **local** | — (DRC count 0 observed) | `artifact_verifier` | `direct log` | Observed DRC count 0 in this partially remapped run. |
| B003 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_current_code_rerun_full_pipeline/harness_decision.json` | `harness_decision` | **local** | `device_mismatch`, `body_well_substrate_mismatch` | `sample_trust_gate` | `structured json` | Decision: reject_pipeline_artifact. Blocking reasons include lvs_not_matched and body domain mismatch diagnoses. |
| B004 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_current_code_rerun_full_pipeline/extracted_device_mapping_diagnosis.json` | `other` | **local** | `body_well_substrate_mismatch` | `lvs_failure_taxonomy` | `structured json` | Extracted device mapping diagnosis. 20 mapped source vs 33 extracted. 19 unmatched. 33 body mismatches. 132 terminal mismatches. |
| B005 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_current_code_rerun_full_pipeline/nwell_body_domains.json` | `other` | **local** | `body_well_substrate_mismatch` | `lvs_failure_taxonomy` | `structured json` | Nwell body domain analysis. |
| B006 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_current_code_rerun_full_pipeline/vdd_vss_connection_trace.json` | `other` | **local** | `power_domain_short` | `lvs_failure_taxonomy` | `structured json` | VDD/VSS connection path trace for short diagnosis. |
| B007 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_current_code_rerun_full_pipeline/psub_substrate_geometry_diagnosis.json` | `other` | **local** | `body_well_substrate_mismatch` | `lvs_failure_taxonomy` | `structured json` | Psub/substrate geometry analysis. |

### Section C: DFCFC2 Audit and Configuration Documents

| ID | Circuit | Absolute path | Artifact class | Local status | Failure category | Feeds diagnostic | Evidence strength | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C001 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/docs/sky130_adapter/amp_dfcfc2_adapter_audit.md` | `other` | **local** | `native_cap_mapping_failure` | `manual_review` | `summary only` | Adapter audit. Readiness: blocked. Unsupported model: sky130_fd_pr__cap_mim_m3_1 ×2. MIM proxy cfmom_2t mapped_requires_validation. |
| C002 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/audit.json` | `other` | **local** | `native_cap_mapping_failure` | `manual_review` | `structured json` | Structured audit. 28 instances, pfet=13, nfet=13, capacitor=2. |
| C003 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/pin_equivalence_audit.json` | `other` | **local** | `pin_label_overlap` | `lvs_failure_taxonomy` | `structured json` | Pin equivalence audit. vinn/vinp share identical 10×90 μm ioPin box with 4 other nets on met1. Root cause of vinn/vinp merge in extraction. |
| C004 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/m8_m9_nwell_body_domains_summary.json` | `other` | **local** | `body_well_substrate_mismatch` | `lvs_failure_taxonomy` | `structured json` | Deep nwell/body domain analysis. |
| C005 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/no_pin_extracted_device_mapping.json` | `other` | **local** | `body_well_substrate_mismatch` | `lvs_failure_taxonomy` | `structured json` | Extracted device mapping. 20 mapped source vs 33 extracted. 19 unmatched devices. 33 body mismatches. |

### Section D: DFCFC2 A/B Experiment Directories (Key Representatives)

| ID | Circuit | Absolute path | Artifact class | Local status | Failure category | Feeds diagnostic | Evidence strength | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D001 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_full_pipeline/` | `ab_experiment_dir` | **local** | `unknown` | `manual_review` | `path reference only` | Baseline MOS-only full pipeline. |
| D002 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_full_pipeline_noguardring_probe/` | `ab_experiment_dir` | **local** | `body_well_substrate_mismatch` | `manual_review` | `path reference only` | No guard ring probe — isolates guard ring impact. |
| D003 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_full_pipeline_nopowerstripe_probe/` | `ab_experiment_dir` | **local** | `power_domain_short` | `manual_review` | `path reference only` | No power stripe probe — isolates power mesh impact. |
| D004 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_full_pipeline_tap_split_probe/` | `ab_experiment_dir` | **local** | `body_well_substrate_mismatch` | `manual_review` | `path reference only` | Tap split probe — isolates tap/substrate body effects. |
| D005 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_no_sym_full_pipeline/` | `ab_experiment_dir` | **local** | `power_domain_short` | `manual_review` | `path reference only` | No symmetry constraint — tests whether sym causes net collapse. |
| D006 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_preserve_no_selfsym_net31_full_pipeline/` | `ab_experiment_dir` | **local** | `unknown` | `manual_review` | `path reference only` | Preserve net31 routing without self-symmetry constraint. Route failure noted in LVS diagnosis. |
| D007 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/default_vars_mos_only_gnda_only_probe/` | `ab_experiment_dir` | **local** | `missing_top_port_label` | `manual_review` | `path reference only` | gnda-only extraction probe — isolates gnda port suppression issue noted in LVS diagnosis. |
| D008 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/global_ab_layers/` | `ab_experiment_dir` | **local** | `body_well_substrate_mismatch` | `manual_review` | `path reference only` | Global layer A/B extraction — nwell/psdm/nsdm body domain hypothesis. |
| D009 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/minimal_power_semantics/` | `ab_experiment_dir` | **local** | `power_domain_short` | `manual_review` | `path reference only` | Minimal power semantics probe. |
| D010 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/label_only_extract_probe/` | `ab_experiment_dir` | **local** | `pin_label_overlap` | `manual_review` | `path reference only` | Label-only extraction (no pin shapes) to isolate label vs shape effects. |
| D011 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/no_pin_extract_probe/` | `ab_experiment_dir` | **local** | `pin_label_overlap` | `manual_review` | `path reference only` | No-pin extraction probe. |

### Section E: DFCFC2 Top-Level and Source Files

| ID | Circuit | Absolute path | Artifact class | Local status | Failure category | Feeds diagnostic | Evidence strength | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E001 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/Leung_DFCFC2_Pin_3_M11.spice` | `extracted_raw_spice` | **local** | — | `artifact_verifier` | `direct log` | Top-level extracted SPICE for DFCFC2 (M11 metal stack). |
| E002 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/Leung_DFCFC2_Pin_3_M11.ext` | `other` | **local** | — | `artifact_verifier` | `direct log` | Top-level Magic .ext file. |
| E003 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/amp_dfcfc2_mos_only_magical.sp` | `other` | **local** | — (MOS-only) | `artifact_verifier` | `direct log` | MOS-only MAGICAL netlist, 26 devices. |
| E004 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/bounded_topk_rank1/AMP_DFCFC2_rank1_vars.spice` | `other` | **local** | — | `artifact_verifier` | `direct log` | Rank1 sizing: reward=-0.75, PM=76.8°, dcgain=128.6, GBW=948 kHz. |
| E005 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/ext_naming_probe_summary.json` | `other` | **local** | `net_name_normalization_mismatch` | `lvs_failure_taxonomy` | `structured json` | Extraction naming/normalization probe. |
| E006 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/generated/sky130_body_domain_probes/pmos_internal_body_full_pipeline/` | `ab_experiment_dir` | **local** | `body_well_substrate_mismatch` | `manual_review` | `path reference only` | PMOS internal body domain probe at sky130_body_domain_probes level. |

### Section F: Fan_SMC/Fan_SMC_Pin_3 Canonical Runs

| ID | Circuit | Absolute path | Artifact class | Local status | Failure category | Feeds diagnostic | Evidence strength | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F001 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract_v2/magic_extract.log` | `magic_extract_log` | **local** | `power_domain_short` | `lvs_failure_taxonomy` | `direct log` | Magic extraction: "Ports vout and vdda are electrically shorted", "Ports vout and gnda are electrically shorted". 11 warnings total. |
| F002 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/smc_extracted_device_mapping.json` | `other` | **local** | `body_well_substrate_mismatch`, `power_domain_short` | `lvs_failure_taxonomy` | `structured json` | Extracted device mapping diagnosis. 23 mapped source, 23 extracted, 1 unmatched. 23 body mismatches, 88 terminal mismatches. vout among mismatch body nets (power domain collapse). |
| F003 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/summary/harness_decision.json` | `harness_decision` | **local** | `net_mismatch` | `sample_trust_gate` | `structured json` | Decision: reject_pipeline_artifact. No-C0 diagnostic candidate. DRC=0, devices match (24 vs 24), nets mismatch (18 vs 39). PEX=351 caps/51.6 fF. |
| F004 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/summary/pex_summary.md` | `pex_summary` | **local** | `pex_without_lvs` | `pex_structuring` | `summary only` | PEX: 351 caps, 51.5874 fF. Largest cap: C349 (2.99 fF). |
| F005 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/summary/parasitic_summary.json` | `parasitic_summary` | **local** | `pex_without_lvs` | `pex_structuring` | `structured json` | Structured PEX summary. |
| F006 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/summary/sample_record.json` | `other` | **local** | `pex_without_lvs` | `pex_structuring` | `structured json` | Graph-learning sample record. training_sample.usable_for_graph_learning=false. |
| F007 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/lvs/netgen_lvs.json` | `netgen_lvs_report` | **local** | `net_mismatch` | `lvs_failure_taxonomy` | `structured json` | Full Netgen LVS JSON. Devices 24=24 match, nets 18 vs 39 mismatch. RC net fragmentation. |
| F008 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/lvs/netgen_lvs.out` | `netgen_lvs_report` | **local** | `net_mismatch` | `lvs_failure_taxonomy` | `direct log` | Netgen output. Device count match but net fragmentation. Net vout mapped to w_485_525#. |
| F009 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/lvs/lvs_preparation_report.md` | `other` | **local** | — | `lvs_failure_taxonomy` | `summary only` | LVS preparation report. 351 parasitic caps removed, MOS properties (ad/as/pd/ps) removed. |
| F010 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/magic_extract.log` | `magic_extract_log` | **local** | — (extraction completed) | `pex_structuring` | `direct log` | Extraction completed without port-short warnings (B1 M5 containment applied). |

### Section G: Fan_SMC/Fan_SMC_Pin_3 A/B Extract Variants

| ID | Circuit | Absolute path | Artifact class | Local status | Failure category | Feeds diagnostic | Evidence strength | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G001 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract/` | `ab_experiment_dir` | **local** | `power_domain_short` | `manual_review` | `path reference only` | Base extraction (all layers). |
| G002 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract_ab_active/` | `ab_experiment_dir` | **local** | `body_well_substrate_mismatch` | `manual_review` | `path reference only` | Active layer removed — isolates diffusion body effects. |
| G003 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract_ab_nwell/` | `ab_experiment_dir` | **local** | `body_well_substrate_mismatch` | `manual_review` | `path reference only` | Nwell layer removed — isolates well body domain. |
| G004 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract_ab_psdm/` | `ab_experiment_dir` | **local** | `body_well_substrate_mismatch` | `manual_review` | `path reference only` | PSDM layer removed — isolates PMOS source/drain body effects. |
| G005 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract_ab_nsdm/` | `ab_experiment_dir` | **local** | `body_well_substrate_mismatch` | `manual_review` | `path reference only` | NSDM layer removed — isolates NMOS source/drain body effects. |
| G006 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract_ab_tap/` | `ab_experiment_dir` | **local** | `body_well_substrate_mismatch` | `manual_review` | `path reference only` | Tap layer removed — isolates substrate tap effects. |
| G007 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract_delete_m5/` | `ab_experiment_dir` | **local** | `power_domain_short` | `manual_review` | `path reference only` | M5 layer deleted — isolates top-metal power mesh short. |
| G008 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract_del_metals/` | `ab_experiment_dir` | **local** | `power_domain_short` | `manual_review` | `path reference only` | All metals deleted — isolates metal-related shorts. |
| G009 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/smc09_no_c0/` | `ab_experiment_dir` | **local** | `net_mismatch` | `sample_trust_gate` | `path reference only` | No-C0 diagnostic branch. C0 cfmom_2t capacitor removed for diagnosis. B1 M5 containment applied. |
| G010 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/lvs_native/` | `ab_experiment_dir` | **local** | `net_mismatch` | `lvs_failure_taxonomy` | `path reference only` | Native LVS attempt under B1 branch (no-merge variant). |

### Section H: Fan_SMC/Fan_SMC_Pin_3 Audit and Configuration Documents

| ID | Circuit | Absolute path | Artifact class | Local status | Failure category | Feeds diagnostic | Evidence strength | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H001 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/docs/sky130_adapter/fan_smc_pin_3_adapter_audit.md` | `other` | **local** | `passive_mapping_failure` | `manual_review` | `summary only` | Adapter audit. Readiness: candidate. 24 MOS-only devices. Note: document title says "amp_dfcfc2" but content is for fan_smc. |
| H002 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/adapter_harness_decision.json` | `harness_decision` | **local** | `passive_mapping_failure` | `sample_trust_gate` | `structured json` | Decision: smoke_only_not_final. I0 current_source unsupported, C0 cfmom_2t mapped_requires_validation. |
| H003 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/audit.json` | `other` | **local** | `passive_mapping_failure` | `manual_review` | `structured json` | Structured audit. 24 instances. pfet=12, nfet=12. No unsupported models (MOS-only view). |
| H004 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/fan_smc_pin_3_raw.spice` | `other` | **local** | — | `artifact_verifier` | `direct log` | Original AnalogGym raw SPICE. Contains behavioral current source and capacitor. |
| H005 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/fan_smc_pin_3_magical.sp` | `other` | **local** | `passive_mapping_failure` | `artifact_verifier` | `direct log` | Converted MAGICAL netlist. C0 mapped to cfmom_2t proxy. |
| H006 | Fan_SMC | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/run_fan_smc_pin_3_trial.log` | `other` | **local** | — | `artifact_verifier` | `direct log` | MAGICAL placement/routing trial log. Path corrected from initial inventory (was missing `magical_case/`). |

### Section I: Shared/Cross-Circuit Artifacts

| ID | Circuit | Absolute path | Artifact class | Local status | Failure category | Feeds diagnostic | Evidence strength | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I001 | Other | `/home/qlf/IOT/references/MAGICAL-/generated/sky130_environment_diagnosis.json` | `other` | **local** | — | `artifact_verifier` | `structured json` | Environment diagnosis. Status=pass. Magic 8.3.483, Docker 28.4.0, netgen-lvs at /usr/bin/netgen-lvs. PDK hash verified. |

---

## Candidate Negative Samples

### Candidate N1: DFCFC2 `mim_proxy_full_pipeline_with_lvs_diagnosis` (Rank1 MIM Proxy)

| Field | Value |
| --- | --- |
| Circuit | DFCFC2 |
| Candidate/run directory | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/amp_dfcfc2/mim_proxy_full_pipeline_with_lvs_diagnosis/` |
| Main failure | LVS mismatch: device count (source 26 vs extracted 52) and net mismatch. LVS diagnosis also records power-ground short and missing extracted port gnda. |
| DRC status | **pass** (observed DRC count 0 in this partially remapped run; 12 TBD layer/datatype mappings remain) |
| LVS status | **fail** (CONNECTIVITY_LVS_MATCH=no, device mismatch=yes, net mismatch=yes) |
| PEX available | **yes** (103 caps, 865.01 fF total, per-node breakdown available) |
| Post-sim valid | **unknown** — no post-layout ngspice simulation found in audited canonical runs |
| PVT valid | **unknown** — no PVT sweep found in audited canonical runs |
| Suggested trust outcome | `usable_only_as_failure_case` |

Required supporting artifacts:
- DRC evidence: A002 (`magic_drc.log` — observed DRC count 0 in partially remapped run)
- LVS evidence: A008 (`netgen_lvs_report.out`), A009 (`netgen_lvs.log`), A010 (`lvs_result_summary.md`), A011 (`lvs_decomposition_diagnosis.json`)
- PEX evidence: A012 (`pex_summary.md`), A013 (`parasitic_summary.json`)
- Harness decision: A015 (`harness_decision.json` — reject_pipeline_artifact)
- Risk report: A014 (`risk_report.json` — 3 findings, max severity=warning)
- Notes on missing evidence: Post-layout ngspice not found in audited canonical runs. PVT sweep not found. Passive-aware full-GDS LVS not found.

**Why this is the recommended first negative sample:**

1. **Most complete evidence bundle**: This run has the richest set of structured diagnostic artifacts — DRC log, extraction log, LVS report (both raw and JSON structured), PEX summary (both markdown and JSON), parasitic risk report, harness decision, and LVS decomposition diagnosis.
2. **Direct LVS failure evidence is unequivocal**: The `lvs_decomposition_diagnosis.json` documents specific failure details. The raw Netgen report shows device count mismatch (26 vs 52). The harness decision is `reject_pipeline_artifact`.
3. **Observed DRC count is 0**: Reduces DRC as a confounding variable for LVS diagnosis, with the caveat that 12 TBD layer/datatype mappings remain unresolved.
4. **PEX exists but is not usable for training**: With 103 parasitic caps and node-level detail, the PEX data is structurally rich — but the underlying LVS has not passed.
5. **Demonstrates the mandatory constraint**: PEX availability ≠ training-safe. The harness decision already has `usable_for_training=false`.
6. **Can be replayed**: The source netlist, MAGICAL config, ioPin, and route GDS are referenced and located. A fresh extraction/LVS run is possible.

**DRC and PEX status detail:**
- DRC: Observed count 0 on pinned-shapes GDS in this partially remapped run. Magic 8.3.483 with sky130A tech. 12 TBD layer read warnings (layers 150/155) — these are preserved unmapped layers, not counted as DRC violations by Magic in this run.
- PEX: 103 parasitic capacitors, 865.01 fF total. Output node vout has 363.4 fF (42% of total). The largest capacitor (C100: 371.2 fF) bridges anonymous node a_830_5820# to vdda.

**Trust gate mapping (contract reason codes only):**
```json
{
  "candidate_id": "dfcfc2_mim_proxy_rank1",
  "drc_clean": true,
  "lvs_match": false,
  "pex_available": true,
  "post_sim_valid": false,
  "pvt_valid": false,
  "evidence_scope": "mos_only_projection",
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": true,
  "usable_only_as_failure_case": true,
  "reasons": [
    "lvs_not_matched",
    "post_sim_invalid",
    "pvt_invalid",
    "scope_not_full_passive_inclusive_gds_lvs"
  ]
}
```

`drc_clean=true` reflects the observed Magic DRC count of 0 in this partially remapped run; it does not erase the unresolved layer-mapping caveat recorded in A017.

**Why `usable_only_as_failure_case`:**
- DRC count 0 observed and PEX available → `usable_for_parasitic_modeling=true`
- LVS has not passed → `usable_for_post_sim=false`, `usable_for_reward=false`
- No post-layout simulation or PVT sweep found in audited canonical runs → `post_sim_invalid`, `pvt_invalid`
- Evidence scope is `mos_only_projection`, not `full_passive_inclusive_gds_lvs` → `scope_not_full_passive_inclusive_gds_lvs`
- MIM capacitor mapping is unresolved (`cfmom_2t` proxy not validated)
- Route has an unresolved net (noted in LVS diagnosis)

### Candidate N2: Fan_SMC `smc09_no_c0` B1 Diagnostic Candidate

| Field | Value |
| --- | --- |
| Circuit | Fan_SMC |
| Candidate/run directory | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/` |
| Main failure | LVS net mismatch: source 18 nets vs extracted 39 nets (RC net fragmentation). Devices match (24 vs 24). |
| DRC status | **pass** (DRC_COUNT=0, per harness_decision.json) |
| LVS status | **fail** (device match=yes, net match=no: 18 vs 39 nets) |
| PEX available | **yes** (351 caps, 51.5874 fF total) |
| Post-sim valid | **unknown** — no post-layout simulation found in audited canonical runs |
| PVT valid | **unknown** — no PVT sweep found in audited canonical runs |
| Suggested trust outcome | `usable_only_as_failure_case` |

Required supporting artifacts:
- DRC evidence: F003 (`harness_decision.json` reports DRC=0)
- LVS evidence: F007 (`netgen_lvs.json`), F008 (`netgen_lvs.out`)
- PEX evidence: F004 (`pex_summary.md`), F005 (`parasitic_summary.json`)
- Harness decision: F003 (`harness_decision.json`)
- Notes on missing evidence: Diagnostic-only candidate (C0 removed, B1 M5 containment applied). NOT original AnalogGym SMC. Post-layout simulation not found. PVT not found.

**Note on N2 limitations**: This candidate is explicitly labeled "diagnostic_candidate_not_original_analoggym_smc" and "c0_cfmom_2t_removed_diagnostic_only". It is useful as a secondary negative sample to demonstrate that matching device counts do not imply matching netlists, but it is not a faithful circuit representation.

---

## Open Questions For Codex Review

- Question 1: Should we prioritize the DFCFC2 `mim_proxy_full_pipeline_with_lvs_diagnosis` as the first negative fixture, or would a simpler MOS-only run (e.g., `default_vars_mos_only_current_code_rerun_full_pipeline`) be more appropriate for initial trust-gate test scaffolding?
- Question 2: The Fan_SMC adapter audit document (`docs/sky130_adapter/fan_smc_pin_3_adapter_audit.md`) has its title and first line incorrectly stating "amp_dfcfc2" — should this be noted as a documentation bug or treated as a derived copy?
- Question 3: Fan_SMC `extract_v2` confirms "Ports vout and vdda are electrically shorted" and "Ports vout and gnda are electrically shorted" — this power-domain collapse appears more fundamental than DFCFC2's net fragmentation. Should Fan_SMC's power short be the first `power_domain_short` taxonomy test case?
- Question 4: The DFCFC2 `lvs_decomposition_diagnosis.json` shows extracted MOS count = 52 while source MOS count = 26. This 2× factor may indicate finger decomposition (nf>1 instances being split during extraction). Should the `lvs_failure_taxonomy` parser handle this as a distinct sub-category?
- Question 5: Neither circuit has post-layout ngspice or PVT evidence in the audited canonical runs. Should the inventory explicitly recommend that these not be pursued until LVS passes, or should a "parasitic-only" post-layout simulation be attempted even with LVS=FAIL?

## Do-Not-Claim List

- Do not claim DFCFC2 or Fan_SMC is permanently impossible to close. All observed failures are within known taxonomy categories and are being actively diagnosed.
- Do not claim PEX availability means LVS passed. DFCFC2 has PEX with 103 caps while LVS=FAIL. Fan_SMC has PEX with 351 caps while LVS=FAIL.
- Do not claim a sample is training-safe without DRC/LVS/PEX/post-sim/PVT and scope review. Neither circuit passes the full trust-gate criteria.
- Do not claim the Fan_SMC `smc09_no_c0` diagnostic candidate represents the original AnalogGym SMC circuit — it is a C0-removed diagnostic control.
- Do not claim "device counts match" as equivalent to LVS match for Fan_SMC. Devices do match (24 vs 24), but nets do not (18 vs 39), and the harness correctly marks LVS as failed.
- Do not claim the DFCFC2 MIM proxy `cfmom_2t` mapping is validated. The adapter harness marks it `mapped_requires_validation` with `final_flow_allowed=false`.
- Do not claim DFCFC2's observed DRC count 0 means the layout is fully Sky130-compliant — 12 layer/datatype pairs remain TBD and generate Magic read warnings.
- Do not claim this inventory is exhaustive for all A/B experiment directories. The ~85 DFCFC2 and ~20 Fan_SMC experiment directories were sampled at the directory-listing level; deep content of each probe directory was not examined unless it contained structured JSON/Markdown evidence.
