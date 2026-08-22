# GRPO-to-PCS admission batch v4 failure triage

生成日期：2026-08-22

## 结论

batch v4 的 19 条未进入默认寄生图训练集样本，可以分成三类：

| triage group | count | 默认训练集处理 | 解释 |
|---|---:|---|---|
| `magical_place_route_no_raw_pex` | 12 | 不进入 | MAGICAL place/route 阶段失败，没有 raw PEX；这是最早的物理闭合失败。 |
| `raw_pex_but_connectivity_lvs_failed` | 4 | 不进入 | 已经有 raw PEX，但 connectivity LVS 未过，所以不是 L6 样本。 |
| `timeout_after_layout_pex_with_lvs_property_mismatch` | 3 | 不进入 | 30min wrapper timeout；已有 layout/DRC/LVS/PEX 产物，但最终 state 未完成，且 LVS 证据显示 property mismatch。 |

这说明 batch v4 的失败不是一个单一阈值问题，尤其不能只根据 `M12.M` 直接硬编码 action-space。正确用法仍然是：GRPO candidate 进入 PCS admission gate，真实跑完后再入库或标 failure label。

## 1. magical_place_route_no_raw_pex：12 条

这些样本停在 `magical_place_route`，没有 raw PEX，因此不能产生寄生图训练样本。

| candidate | M12.M | stratum | layout failed stage | raw PEX |
|---|---:|---|---|---|
| `grpo_leung_dfcfc2_0001` | 154 | high_predicted_closure | magical_place_route | no |
| `grpo_leung_dfcfc2_0003` | 100 | high_predicted_closure | magical_place_route | no |
| `grpo_leung_dfcfc2_0004` | 100 | high_predicted_closure | magical_place_route | no |
| `grpo_leung_dfcfc2_0005` | 149 | high_predicted_closure | magical_place_route | no |
| `grpo_leung_dfcfc2_0006` | 161 | high_predicted_closure | magical_place_route | no |
| `grpo_leung_dfcfc2_0008` | 500 | medium_predicted_closure | magical_place_route | no |
| `grpo_leung_dfcfc2_0011` | 100 | medium_predicted_closure | magical_place_route | no |
| `grpo_leung_dfcfc2_0014` | 100 | medium_predicted_closure | magical_place_route | no |
| `grpo_leung_dfcfc2_0016` | 500 | low_predicted_closure | magical_place_route | no |
| `grpo_leung_dfcfc2_0017` | 500 | low_predicted_closure | magical_place_route | no |
| `grpo_leung_dfcfc2_0020` | 500 | low_predicted_closure | magical_place_route | no |
| `grpo_leung_dfcfc2_0023` | 500 | low_predicted_closure | magical_place_route | no |

观察：high/medium/low 三个 stratum 都有这类失败；M12.M=100、154、161、500 都出现过失败。因此 batch v4 不能支持“只按 M12.M 判定能否闭合”的规则。

## 2. raw_pex_but_connectivity_lvs_failed：4 条

这些样本已经有 raw PEX 和 PEX summary，但 layout summary 标记 `FAILED_STAGE=connectivity_lvs`，LVS summary 中同时出现 device/net mismatch。因此它们适合做失败诊断，不适合进默认 graph training。

| candidate | M12.M | stratum | PEX caps | total cap | LVS likely cause |
|---|---:|---|---:|---:|---|
| `grpo_leung_dfcfc2_0015` | 446 | medium_predicted_closure | 88 | 1848.40686 | unmatched or mismatched devices, net mismatch |
| `grpo_leung_dfcfc2_0018` | 500 | low_predicted_closure | 105 | 5785.90632 | net mismatch |
| `grpo_leung_dfcfc2_0021` | 480 | low_predicted_closure | 91 | 1970.80381 | net mismatch |
| `grpo_leung_dfcfc2_0022` | 475 | low_predicted_closure | 95 | 4190.74792 | unmatched or mismatched devices, net mismatch |

观察：这组集中在 M12.M≈446–500 的较大尺寸区域，但仍不能反推为硬边界，因为 batch v4 同时有 M12.M=500 的 `0013` 成功进入 L6。

## 3. timeout_after_layout_pex_with_lvs_property_mismatch：3 条

这些样本被 30min per-candidate timeout 杀掉。它们不是默认训练样本，因为没有完整 final state/L6 admission；但它们也不是简单的“没有物理产物”：三条都有 layout/DRC/LVS/PEX 相关产物，且 summary 中能看到 DRC 0、raw PEX cap 数和 total cap。

| candidate | M12.M | stratum | PEX caps | total cap | LVS note |
|---|---:|---|---:|---:|---|
| `grpo_leung_dfcfc2_0009` | 478 | medium_predicted_closure | 126 | 4723.97 | property mismatch |
| `grpo_leung_dfcfc2_0012` | 191 | medium_predicted_closure | 115 | 3128.18 | property mismatch |
| `grpo_leung_dfcfc2_0019` | 500 | low_predicted_closure | 115 | 6944.79 | property mismatch |

处理边界：timeout 表示“当前预算下未完成”，不是物理不可闭合证明。后续如要使用，应单独做 extended-time rerun，不能直接混入默认训练集。

## 对 batch v5 的影响

建议：

1. 继续使用 classifier-guided stratified sampling，但不要把 classifier 当 gate。
2. batch v5 仍保留 high/medium/low 三层；high 用于增加 admitted graph，medium/low 用于继续刻画失败边界。
3. 对 timeout 邻域单独设 `extended_rerun` 标签：默认 batch 仍用 30min，另开长时小实验验证 timeout 是否可恢复。
4. 对 raw-PEX-but-LVS-fail 样本，不进默认训练集，但保留在 failure classifier 训练集中，因为它们能告诉模型“有 raw PEX 也不等于 L6”。
5. 不从 batch v4 直接收缩 action-space；若要改 action-space，需要合同版本更新和更多批次统计支持。

## 产物路径

- `generated/grpo_to_pcs_admission_batch_v4_20260822/failure_triage_v4.json`
- `generated/grpo_to_pcs_admission_batch_v4_20260822/failure_triage_v4.csv`
- `generated/grpo_to_pcs_admission_batch_v4_20260822/admission_summary_v4.json`
