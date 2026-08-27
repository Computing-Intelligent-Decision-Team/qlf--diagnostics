# DFCFC2 Dataset Closure Audit

- audited_link: `datasets/dfcfc2_parasitic/current`
- resolved_path: `/home/qlf/IOT/references/pcs-harness-align-origin-main-20260815/generated/analog_harness/parasitic_modeling/dfcfc2_trusted_parasitic_95_20260826_v3`
- schema_version: `dfcfc2_trusted_parasitic_corpus.v1`
- dataset_scope: `DFCFC2 pcs-harness L6 sizing to trusted MOS-only raw PEX capacitor graph`

## Closure Verdict

DFCFC2 当前正式寄生建模数据集可以作为第一电路封口版本使用。它已经具备样本表、JSONL、节点特征、电容边、审计报告、统计报告和 SHA256 校验文件；当前任务不再继续扩大 DFCFC2 样本，而把它作为 SMCNR 第二电路 pilot 的对照基准。

## Core Counts

| metric | value |
|---|---:|
| `samples` | 95 |
| `sizing_dimension` | 27 |
| `source_l6_records` | 98 |
| `unique_sizing_raw_pairs` | 95 |
| `rejected_l6_records` | 3 |
| `capacitor_edges_all` | 12052 |
| `capacitor_edges_positive` | 10794 |
| `capacitor_edges_zero` | 1258 |
| `explicit_resistor_edges` | 0 |
| `node_records` | 1805 |

## Sizing Dimension Check

| dimension | sample_count |
|---:|---:|
| 27 | 95 |

## Batch Coverage

| batch | samples |
|---|---:|
| `grpo_batch_v12_trained_step300_pool100_l1_l6_admission_20260825_v1` | 64 |
| `grpo_batch_v11_pool100_l1_l6_admission_20260824_terminal_v1` | 6 |
| `grpo_batch_v4_l1_l6_admission_20260822` | 5 |
| `grpo_batch_v3_l1_l6_admission_20260822` | 4 |
| `grpo_b8_0004_biascm_geometry_controlled_replay_20260823_v1` | 3 |
| `grpo_batch_v2_l1_l6_admission_20260822` | 3 |
| `grpo_batch_v8_classifier_stratified9_l1_l6_admission_20260823_terminal_v1` | 3 |
| `grpo_batch_v5_step1_recommended_l1_l6_admission_20260823_envfix_v3` | 2 |
| `grpo_m12_bound_experiment_20260819_v1` | 2 |
| `stage3_amplifier_coverage_v1` | 2 |
| `grpo_batch_v6_remaining_top3_l1_l6_admission_20260823_terminal_v2` | 1 |

## Label Contract

- `limitations`: ["Connectivity evidence only; no property-level or native-passive signoff.", "Raw PEX files contain capacitor elements but no explicit resistor elements."]
- `observation_only`: ["pm", "reward", "pre_layout_sim", "pvt", "post_layout_performance"]
- `required`: ["sizing_lineage", "drc_pass", "connectivity_lvs_pass", "parseable_raw_pex"]
- `verification_scope`: "mos_only_projection"

## Key Files SHA256

| file | bytes | sha256 |
|---|---:|---|
| `dataset.json` | 14447092 | `57efcd9ac6b6130f48d58502988f4727e99f7224149411b998edbbadf2ad9c49` |
| `samples.csv` | 74204 | `4fc7459db405388b0d959feb4e09744e68866fcf58acf84e30fd1f66e515f928` |
| `samples.jsonl` | 12529847 | `8b1997bcc62b5054b050231523b32259f806792d18fdf4af237af7ce0b67dc71` |
| `capacitor_edges.csv` | 6840272 | `fd5a82e9ffcc2cd8cf798ee6d8287b6290b42949cedb02d5fd4f3b17f6cfcfe0` |
| `node_features.csv` | 211814 | `82e060e2c1b207386ae1b5a1dbf84cd2a030bf81f04598e46d3fe2b16f8bf85a` |
| `AUDIT_REPORT.json` | 1573 | `4b317df4fa9af52840a520237fc24588bea916a8803401af4b69be482064be22` |
| `SHA256SUMS` | 1085 | `3f51fd54ca1fa4d02168440a6d011261adf7c5ae1481618d66c7278210c11b40` |
| `STATISTICS.md` | 1002 | `1a6ca895533c4186f6f385188fcce7b2aca4854be5b55f545d1cf7941913ad53` |
| `README.md` | 645 | `462ddb5418ef97a76e8e1bc3e0dd391e22483c939ebf3c3d6a972b01a7d0c4fa` |

## Notes For Next Circuit

- DFCFC2 的封口标准是：样本必须能追溯 sizing，且对应 PCS 结果通过 DRC/LVS，并有可信 raw PEX 电容图标签。
- SMCNR 不能直接因为有 PEX 文件就进入数据池；必须先按同样标准审计。
- 后仿/PVT/reward/PM 可以记录，但不作为寄生标签是否可信的必要筛选条件。
