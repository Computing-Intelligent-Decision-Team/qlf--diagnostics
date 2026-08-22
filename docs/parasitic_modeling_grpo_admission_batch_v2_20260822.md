# GRPO-to-PCS admission batch v2 记录（2026-08-22）

## 结论

本轮从 AnalogGym-Opt 导出 `leung_dfcfc2_pin_3` 的 12 条 fresh GRPO sizing candidate，经 PCS L0→L6 admission 后，严格进入默认寄生图训练集的是 3 条。

- 3 条达到 `L6_post_layout_pvt`，且有 raw `*_extracted.raw.spice`，已追加进 dataset v3。
- 2 条生成了 raw PEX，但 connectivity LVS 未通过，只保留为诊断 raw-PEX 样本，不进入默认训练集。
- 7 条停在 MAGICAL place-route，未生成 raw PEX，作为 physical closure failure label。
- `grpo_leung_dfcfc2_0003` 属于 MAGICAL place-route failure：L0/L2 可重放，但没有可用于图学习的 raw PEX。

## 机器可读产物

- `generated/analog_harness/grpo_batch_v2_l1_l6_admission_20260822/admission_summary_v2.json`
- `generated/analog_harness/grpo_batch_v2_l1_l6_admission_20260822/admitted_graphs_v2.jsonl`
- `generated/analog_harness/grpo_batch_v2_l1_l6_admission_20260822/physical_closure_failure_labels_v2.jsonl`
- `generated/analog_harness/grpo_batch_v2_l1_l6_admission_20260822/raw_pex_available_not_l6_v2.jsonl`
- `generated/analog_harness/parasitic_modeling/graph_learning_samples_20260822_55graphs_grpo_batch_v2_dataset_v3/graphs.jsonl`
- `generated/analog_harness/parasitic_modeling/profile_comparison_grpo_batch_v2_dataset_v3/profile_comparison.md`
- `generated/analog_harness/parasitic_modeling/family_aware_eval_grpo_batch_v2_dataset_v3/no_total_cap_leakage/report.md`

## Admission 结果表

| candidate | M12.M | closure | status | fail stage | raw caps | total cap fF |
|---|---:|---|---|---|---:|---:|
| `grpo_leung_dfcfc2_0000` | 389 | `L6_post_layout_pvt` | `admitted_raw_pex_graph` | `` | 131 | 1762.34211 |
| `grpo_leung_dfcfc2_0001` | 442 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  |
| `grpo_leung_dfcfc2_0002` | 393 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  |
| `grpo_leung_dfcfc2_0003` | 444 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  |
| `grpo_leung_dfcfc2_0004` | 437 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  |
| `grpo_leung_dfcfc2_0005` | 339 | `L2_pre_layout_pvt` | `raw_pex_available_not_l6` | `connectivity_lvs` | 119 | 2631.76498 |
| `grpo_leung_dfcfc2_0006` | 350 | `L2_pre_layout_pvt` | `raw_pex_available_not_l6` | `connectivity_lvs` | 105 | 4025.11998 |
| `grpo_leung_dfcfc2_0007` | 449 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  |
| `grpo_leung_dfcfc2_0008` | 367 | `L6_post_layout_pvt` | `admitted_raw_pex_graph` | `` | 112 | 5781.05423 |
| `grpo_leung_dfcfc2_0009` | 352 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  |
| `grpo_leung_dfcfc2_0010` | 397 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  |
| `grpo_leung_dfcfc2_0011` | 337 | `L6_post_layout_pvt` | `admitted_raw_pex_graph` | `` | 129 | 3656.83521 |

## Dataset v3 摘要

- base graphs: 52
- added GRPO L6 graphs: 3
- total graphs: 55
- total nodes: 835
- total edges: 4963

## 新增 L6 图样本

| graph | M12.M | edges | total cap fF | raw spice sha256 |
|---|---:|---:|---:|---|
| `leung_dfcfc2_pin_3__grpo_admission_batch_v2_20260822/grpo_leung_dfcfc2_0000` | 389 | 131 | 1762.342110 | `319f68880e9a25da093e4a712a6150b14bb2c04e238ec7274b3dbba4005946ad` |
| `leung_dfcfc2_pin_3__grpo_admission_batch_v2_20260822/grpo_leung_dfcfc2_0008` | 367 | 112 | 5781.054230 | `6329ba1858983976632ec874d9eccbbb69076dcf4672073e65af6e62d693f5a6` |
| `leung_dfcfc2_pin_3__grpo_admission_batch_v2_20260822/grpo_leung_dfcfc2_0011` | 337 | 129 | 3656.835210 | `7dc7fc86f884ce02f43ddc464e72f42e91be124f6b44e7d9a4825974db9b2086` |

## 解释边界

默认 graph-training dataset 只接收 `L6_post_layout_pvt + raw PEX`。这不是说 0005/0006 的 raw PEX 没有价值，而是它们没有通过 connectivity LVS，不能与“物理闭环样本”混为同一类标签。

MAGICAL place-route failure 的样本也不是“没用”：它们可以用于 admission/gate 研究，说明 GRPO action-space 内合法 sizing 并不等于 PCS 后端物理可闭合。

## 验证命令

```bash
python3 - <<'PY'
import json
from pathlib import Path
s=json.loads(Path('generated/analog_harness/grpo_batch_v2_l1_l6_admission_20260822/admission_summary_v2.json').read_text())
d=json.loads(Path('generated/analog_harness/parasitic_modeling/graph_learning_samples_20260822_55graphs_grpo_batch_v2_dataset_v3/summary.json').read_text())
print(s['counts'])
print(d['counts'])
PY
```
