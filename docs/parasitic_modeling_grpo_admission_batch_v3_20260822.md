# GRPO-to-PCS admission batch v3 controlled sampling（2026-08-22）

## 结论

本轮 batch v3 没有改死 AnalogGym action-space，而是从真实 AnalogGym-Opt GRPO export pool 中筛选 `330 <= M12.M <= 397` 的 12 条 candidate，送入同一 PCS L0→L6 admission gate。

- candidates: 12
- L6 + raw PEX admitted graph: 4
- raw PEX available but not L6: 2
- physical closure failed with no raw PEX: 6
- dataset v4 graphs: 59 = 55 + 4

关键发现：`M12.M` 不是单参数硬边界。batch v2 提示 `M12.M >= 393` 高风险，但 batch v3 中 `M12.M=392` 和 `M12.M=394` 均达到 `L6_post_layout_pvt + raw PEX`。

## 产物路径

- `generated/analog_harness/grpo_candidate_export_20260822_batch_v3_controlled/controlled_selection_manifest.json`
- `generated/analog_harness/grpo_batch_v3_l1_l6_admission_20260822/admission_summary_v3.json`
- `generated/analog_harness/grpo_batch_v3_l1_l6_admission_20260822/admitted_graphs_v3.jsonl`
- `generated/analog_harness/grpo_batch_v3_l1_l6_admission_20260822/physical_closure_failure_labels_v3.jsonl`
- `generated/analog_harness/parasitic_modeling/graph_learning_samples_20260822_59graphs_grpo_batch_v3_dataset_v4/graphs.jsonl`
- `generated/analog_harness/parasitic_modeling/profile_comparison_grpo_batch_v3_dataset_v4/profile_comparison.md`
- `generated/analog_harness/parasitic_modeling/family_aware_eval_grpo_batch_v3_dataset_v4/no_total_cap_leakage/report.md`

## Admission 明细

| candidate | bucket | M12.M | closure | status | fail stage | caps | total cap fF | elapsed s |
|---|---|---:|---|---|---|---:|---:|---:|
| `grpo_leung_dfcfc2_0000` | `l6_neighborhood_m12_330_390` | 331 | `L2_pre_layout_pvt` | `raw_pex_available_not_l6` | `post_layout_or_lvs_not_l6` | 124 | 1565.48117 | 222.355 |
| `grpo_leung_dfcfc2_0001` | `diagnostic_neighborhood_m12_335_365` | 336 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  | 221.229 |
| `grpo_leung_dfcfc2_0002` | `diagnostic_neighborhood_m12_335_365` | 339 | `L6_post_layout_pvt` | `admitted_raw_pex_graph` | `` | 118 | 2001.61333 | 755.583 |
| `grpo_leung_dfcfc2_0003` | `diagnostic_neighborhood_m12_335_365` | 356 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  | 177.77 |
| `grpo_leung_dfcfc2_0004` | `diagnostic_neighborhood_m12_335_365` | 363 | `L2_pre_layout_pvt` | `raw_pex_available_not_l6` | `post_layout_or_lvs_not_l6` | 109 | 4461.6688 | 229.798 |
| `grpo_leung_dfcfc2_0005` | `l6_neighborhood_m12_330_390` | 375 | `L6_post_layout_pvt` | `admitted_raw_pex_graph` | `` | 135 | 3351.97493 | 2194.813 |
| `grpo_leung_dfcfc2_0006` | `l6_neighborhood_m12_330_390` | 380 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  | 237.461 |
| `grpo_leung_dfcfc2_0007` | `boundary_m12_388_397` | 390 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  | 280.746 |
| `grpo_leung_dfcfc2_0008` | `boundary_m12_388_397` | 390 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  | 183.626 |
| `grpo_leung_dfcfc2_0009` | `boundary_m12_388_397` | 390 | `L2_pre_layout_pvt` | `physical_closure_failed` | `magical_place_route` |  |  | 188.535 |
| `grpo_leung_dfcfc2_0010` | `boundary_m12_388_397` | 392 | `L6_post_layout_pvt` | `admitted_raw_pex_graph` | `` | 129 | 2365.25273 | 929.789 |
| `grpo_leung_dfcfc2_0011` | `boundary_m12_388_397` | 394 | `L6_post_layout_pvt` | `admitted_raw_pex_graph` | `` | 112 | 1991.44623 | 1557.18 |

## Bucket 结果

| bucket | candidates | L6 | no-raw failure |
|---|---:|---:|---:|
| `boundary_m12_388_397` | 5 | 2 | 3 |
| `diagnostic_neighborhood_m12_335_365` | 4 | 1 | 2 |
| `l6_neighborhood_m12_330_390` | 3 | 1 | 1 |

## 新增 graph 样本

| graph | M12.M | edges | total cap fF | raw spice sha256 |
|---|---:|---:|---:|---|
| `leung_dfcfc2_pin_3__grpo_admission_batch_v3_20260822/grpo_leung_dfcfc2_0002` | 339 | 118 | 2001.613330 | `99bf8ec9e4c41dd9eed51eeaa4055bbe9f9782c2d497e0f1894de55319ddca01` |
| `leung_dfcfc2_pin_3__grpo_admission_batch_v3_20260822/grpo_leung_dfcfc2_0005` | 375 | 135 | 3351.974930 | `db2688cc59e17d4e6639024d144539b90b8f292f7fd0b0e431e2905b70a96b4f` |
| `leung_dfcfc2_pin_3__grpo_admission_batch_v3_20260822/grpo_leung_dfcfc2_0010` | 392 | 129 | 2365.252730 | `b5d20d446e4deda88667ef1142a1663630706e6eae317cadbb460598d8ac00e0` |
| `leung_dfcfc2_pin_3__grpo_admission_batch_v3_20260822/grpo_leung_dfcfc2_0011` | 394 | 112 | 1991.446230 | `75338bc53fa99c9824c2960692379d99482861c704e12d83a0359705558d5f17` |

## 下一步建议

1. 不要收缩为 `M12.M < 393` 这种单参数硬规则。
2. 下一轮应该建一个 lightweight physical-closure classifier，输入完整 sizing，而不是只看 M12。
3. 寄生建模默认训练集继续只使用 `L6_post_layout_pvt + raw PEX`，raw-only/non-L6 行保留为 admission diagnostic。
