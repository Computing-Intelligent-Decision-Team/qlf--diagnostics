# SMCNR Legacy Data Audit

- legacy_root: `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821`
- audited_candidate: `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001`
- current_graph_dataset: `references/pcs-harness-align-origin-main-20260815/generated/analog_harness/parasitic_modeling/graph_learning_samples_20260817_32graphs_smcnr_combo_v1`

## Verdict

SMCNR 可以作为第二电路验证对象，但应区分两类数据：

1. 历史 fixed-GDS L6 样本：可作为环境/版图血缘锚点，不能直接放入当前 regenerated-layout 局部响应曲线。
2. 当前 regenerated-layout controlled SMCNR sweep/combo：已有 18 个 SMCNR controlled rows；当前 32-graph 数据集整体为 L6 且 raw-SPICE-source verified，适合作为 3-5 样本 pilot 的低风险入口。

## Historical L6 Candidate Evidence

| item | value |
|---|---:|
| closure_level | `L6_post_layout_pvt` |
| design_id | `smcnr_se_2st_amp` |
| candidate_id | `cand_0001` |
| values_dimension | 23 |
| action_dimension | 23 |
| `drc_count` | `0` |
| `lvs_match` | `yes` |
| `pex_caps` | `34` |
| `pex_total_cap_ff` | `432.739` |
| `pex_output_node` | `vout` |
| `pvt_passed_corners` | `3` |
| `pvt_total_corners` | `3` |
| performance_feasible | `True` |
| raw_pex_cap_line_count | 34 |

## Historical Candidate File Completeness

| label | exists | bytes | sha256 | path |
|---|---:|---:|---|---|
| `state.json` | true | 34334 | `1990ca56eb8ceec764fd9c56aca7af0b8894e047e5cc9e7665035d15635f96d5` | `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001/state.json` |
| `raw_pex` | true | 4050 | `e38cf4816260c3a15217ea72a95066a07bb2e938abfa471c87522006da1a6d50` | `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001/layout/SMCNR_SE_2st_AMP_extracted.raw.spice` |
| `connectivity_pex` | true | 2187 | `c836190e735e9c888264850383395686bdf6c3221076d4bb6f03732420dd9f64` | `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001/layout/SMCNR_SE_2st_AMP_extracted.connectivity.spice` |
| `source_connectivity` | true | 535 | `8c529cf7509ea320337571c23ccca20652bcc8a980a87ae291f86a5a974bbce6` | `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001/layout/SMCNR_SE_2st_AMP_source.connectivity.spice` |
| `extracted_spice` | true | 4050 | `e38cf4816260c3a15217ea72a95066a07bb2e938abfa471c87522006da1a6d50` | `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001/layout/SMCNR_SE_2st_AMP_extracted.spice` |
| `flat_ext` | true | 7380 | `52798bd982411436a9c577074136f3f9f68cfbf126d02d81e68053a772c9ece9` | `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001/layout/SMCNR_SE_2st_AMP_flat.ext` |
| `magic_extract_input_gds` | true | 855054 | `af5c7a557131284664d59f94d425786624aaba899c3259b0d1122a25d1738b7a` | `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001/layout/SMCNR_SE_2st_AMP.magic_extract_input.gds` |
| `lvs_iopin` | true | 604 | `0e7ae8c3e65c772f683137fc9ee7c1a9abcef5212fbbf0f3ca2d7bf14a8f0ae0` | `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001/layout/SMCNR_SE_2st_AMP.lvs.ioPin` |
| `post_layout_pvt_corner_evidence` | true | 18024 | `456ef14d3c9bf54d215406d8ed3c885217e4c64d90ff346b902a013afaefaeb0` | `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001/sim/post_layout_pvt/corner_evidence.json` |
| `case_json` | true | 989 | `fbaec0eb5f2cf52f343c04f500442fb54e20f4d255d3501053d706a5000a081c` | `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001/case/smcnr_se_2st_amp_cand_0001.json` |
| `net_identity_audit` | true | 1303 | `3eec6c5d21df386169f1dce9fa15fb320f7e2fd1fc87a4c7cd0de34bbf1ac4a6` | `references/.codex-archives/retired_worktrees/pcs-harness-smcnr-trusted-data-factory-20260821/generated/analog_harness/stage2_route_connectivity_repair_v1/regression/final_v3/smcnr_se_2st_amp/cand_0001/case/SMCNR_SE_2st_AMP_cand_0001.net_identity_audit.json` |

## Current 32-Graph Dataset Quality Snapshot

| item | value |
|---|---:|
| schema_version | `parasitic_graph_learning_samples.v1.32_smcnr_combo_20260817` |
| graphs | 32 |
| missing_required_checks | 0 |
| family `smcnr_sizing_probe_20260817` | 2 |
| family `smcnr_sizing_sweep_20260817_v1` | 8 |
| family `smcnr_sizing_sweep_combo_20260817_v1` | 8 |
| family `stage2_fixed_gds` | 3 |
| family `stage3_fresh` | 11 |

## Boundary

- 历史 fixed-GDS SMCNR：`34 caps / 432.739 fF`，输出节点电容约 `172.429 fF`，适合作为复现和环境锚点。
- 当前 regenerated-layout baseline：文档记录为 `33 caps / 764.45058 fF`，输出节点电容 `645.62162 fF`；它和 fixed-GDS 样本不是同一条 sizing-response 曲线。
- 本阶段继续遵守 DFCFC2 的可信标签标准：DRC/LVS/raw PEX 是硬门，PM/reward/PVT/performance 记录但不作为寄生标签硬门。
