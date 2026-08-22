# GRPO-to-PCS admission batch v4 状态记录

生成日期：2026-08-22

## 结论

batch v4 已完成 24 条 GRPO fresh candidate 的 PCS admission 审计，并把可进入默认寄生图训练集的样本合入 dataset v5。

核心结果：

- 24 条 candidate 全部通过 L0 replayability 检查。
- 5 条达到 `L6_post_layout_pvt` 且存在 verified raw PEX，可进入默认 graph training。
- 4 条存在 raw PEX，但未达到 L6，只保留为诊断样本。
- 12 条停在物理闭合前段，标记为 `physical_closure_failed`。
- 3 条触发单条 30min timeout，单独标记为 `simulation_timeout_or_hang`，不进入默认训练集。

这批结果继续支持当前原则：

> GRPO 输出合法 sizing 只是候选源；是否能成为寄生图训练样本，必须以实际 L0→L6 + raw PEX admission 证据为准。

## 采样方式

batch v4 没有硬改或收缩 action-space。候选来自 AnalogGym-Opt/GRPO export pool，再用 v1 physical-closure classifier 做 stratified sampling：

- high predicted closure：8 条
- medium predicted closure：8 条
- low predicted closure：8 条

这个 classifier 只用于“选哪些候选先跑”，不是判定样本能不能入库。最终入库仍由实际 PCS 跑出来的 L6/raw PEX 结果决定。

证据文件：

- `generated/grpo_to_pcs_admission_batch_v4_20260822/candidate_selection/batch_v4_candidate_selection_manifest.json`
- `generated/grpo_to_pcs_admission_batch_v4_20260822/admission_summary_v4.json`

## v4 admitted raw-PEX graph 样本

| candidate | M12.M | selection stratum | PEX cap count | total cap fF | default training |
|---|---:|---|---:|---:|---|
| `grpo_leung_dfcfc2_0000` | 100 | high_predicted_closure | 122 | 1843.24312 | yes |
| `grpo_leung_dfcfc2_0002` | 161 | high_predicted_closure | 129 | 1287.54450 | yes |
| `grpo_leung_dfcfc2_0007` | 222 | high_predicted_closure | 135 | 3228.24591 | yes |
| `grpo_leung_dfcfc2_0010` | 100 | medium_predicted_closure | 111 | 1444.80572 | yes |
| `grpo_leung_dfcfc2_0013` | 500 | medium_predicted_closure | 117 | 1887.57411 | yes |

对应输出：

- `generated/grpo_to_pcs_admission_batch_v4_20260822/admitted_graphs_v4.jsonl`
- `generated/parasitic_modeling/graph_learning_samples_20260822_64graphs_grpo_batch_v4_dataset_v5/graphs.jsonl`

## timeout 样本边界

timeout 样本：

| candidate | M12.M | selection stratum | label |
|---|---:|---|---|
| `grpo_leung_dfcfc2_0009` | 478 | medium_predicted_closure | simulation_timeout_or_hang |
| `grpo_leung_dfcfc2_0012` | 191 | medium_predicted_closure | simulation_timeout_or_hang |
| `grpo_leung_dfcfc2_0019` | 500 | low_predicted_closure | simulation_timeout_or_hang |

timeout 策略：

- 单条 timeout：1800s
- kill-after：60s
- 处理方式：保留为 failure/admission 证据；不进默认 graph training。

注意：timeout 表示“当前预算下未完成”，不是证明该 sizing 物理上必然不能闭合。如果后续要研究极慢样本，应单独开 extended-time rerun，而不是混入默认训练集。

对应输出：

- `generated/grpo_to_pcs_admission_batch_v4_20260822/timeout_labels_v4.jsonl`
- `generated/grpo_to_pcs_admission_batch_v4_20260822/physical_closure_failure_labels_v4.jsonl`

## dataset v5

dataset v5 从 dataset v4 的 59 graphs 起步，只追加 batch v4 的 5 条 L6/raw-PEX 样本：

- base graphs：59
- added GRPO graphs：5
- total graphs：64
- total nodes：1006
- total edges：6071
- skipped non-admitted GRPO records：19

输出目录：

- `generated/parasitic_modeling/graph_learning_samples_20260822_64graphs_grpo_batch_v4_dataset_v5/`

## physical_closure_classifier_v2

classifier v2 使用 batch v2+v3+v4 的完整 admission 结果：

- record count：48
- feature count：114
- admitted count：12
- label counts：
  - `admitted_raw_pex_graph`：12
  - `physical_closure_failed`：25
  - `raw_pex_available_not_l6`：8
  - `simulation_timeout_or_hang`：3

新增边界：

- label matrix 中单独加入 `label_simulation_timeout_or_hang`。
- timeout 不再混进普通物理失败类别。
- 模型目标仍是预测 `graph_training_admitted`，也就是是否能成为 L6/raw-PEX graph 样本。

输出目录：

- `generated/physical_closure_classifier_20260822_v2/`

## profile / family-aware eval v5

已基于 64-graph dataset v5 重跑：

- profile comparison v5：
  - `generated/parasitic_modeling/profile_comparison_20260822_dataset_v5/`
- family-aware eval v5：
  - `generated/parasitic_modeling/family_aware_eval_20260822_dataset_v5/`

profile comparison 中的默认研究 profile 仍是 `no_total_cap_leakage`；`structure_only` 用于检查只靠拓扑/数量信号能学到多少；`leaky_smoke_test` 只作管线烟测，不作为正式结论。

`no_total_cap_leakage` 的 leave-one-out 样本数为 64。当前 ridge baseline 对 `total_cap_ff` 的 MAE 为 93.1313 fF。这个数值只说明训练接口和特征 profile 可稳定消费 dataset v5，不应被解释为最终模型性能。

family-aware eval v5 包含：

- within `leung_dfcfc2_pin_3` split：1 个
- leave-family-out split：14 个

## 后续建议

1. batch v5 不要直接扩大 timeout 时长作为默认策略；先复盘 3 条 timeout 的日志，看是仿真慢、流程 hang，还是可恢复的局部工具卡点。
2. 继续扩大 admitted raw-PEX graph 数量时，优先保持 classifier-guided stratified sampling，而不是只追求高通过率。
3. action-space contract 继续保持版本化；任何收缩都必须来自明确合同修订或统计证据，而不是从单批 failure 直接硬编码。
4. 如果目标是进入“有建模意义”的寄生学习阶段，下一阶段应把同一族 admitted raw-PEX graph 推到 50–100 条量级。

