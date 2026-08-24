# Leung DFCFC2：B8 成功与 B10 失败的同阶段几何审计

## 范围与边界

本审计只读取既有 B8/B10 的 L0 source-state、生成网表、MAGICAL 输入和
运行日志。它不修改 GRPO、action-space、PCS 配置、MAGICAL 或 LVS。

比较对象均为 `leung_dfcfc2_pin_3`、同一 action-space contract
`leung_dfcfc2_pin_3.analoggym_action_space_v1`、同一 MOS-only projection
流程。

| cohort | 样本 | 已观测阶段结果 | 用途 |
|---|---|---|---|
| B8 L6 | `0004`, `0005`, `0012` | `L6_post_layout_pvt` + raw PEX | 成功基准 |
| B10 placement | `0004`, `0007` | `magical_place_route` | legalization/网格对齐失败 |
| B10 router | `0003`, `0009` | `magical_place_route` | 路由不可达失败 |
| B10 LVS | `0000`, `0011` | raw PEX 已生成、connectivity LVS fail | 后端连通性失败 |

所有九条均为 L0 replayable，并实际通过 L2 pre-layout PVT；因此它们不是
action 格式、单位、source netlist 或前仿 PVT 的失败。

## 可复查的逐样本证据

每条的完整 27 维 sizing 已经以 `values` 字段保存在列出的 L0 source-state
中；其完整器件几何（每个 `xm*` 的 `l`、`w`、`multi`、`nf`）位于生成的
`layout_mos_only.sp`。不复制这些大文件，避免产生第二份会失真的“真源”；
下面的 source-state 和 SP 文件是本审计所导出的权威引用。

| cohort / sample | 完整 sizing source-state | 生成器件几何 SP | MAGICAL 输入 JSON | 对称约束/失败证据 |
|---|---|---|---|---|
| B8 L6 `0004` | `pcs-harness-align-origin-main-20260815/generated/analog_harness/grpo_batch_v8_classifier_pool_24_20260823/l0_replay_preparation/source_states/grpo_leung_dfcfc2_0004.source_state.json` | `.../grpo_batch_v8_classifier_stratified9_l1_l6_admission_20260823_terminal_v1/runs/grpo_leung_dfcfc2_0004/cand_0001/case/leung_dfcfc2_pin_3_cand_0001.layout_mos_only.sp` | 同目录 `.layout_mos_only.json` | L6，raw PEX 142 edges |
| B8 L6 `0005` | `pcs-harness-align-origin-main-20260815/generated/analog_harness/grpo_batch_v8_classifier_pool_24_20260823/l0_replay_preparation/source_states/grpo_leung_dfcfc2_0005.source_state.json` | `.../grpo_batch_v8_classifier_stratified9_l1_l6_admission_20260823_terminal_v1/runs/grpo_leung_dfcfc2_0005/cand_0001/case/leung_dfcfc2_pin_3_cand_0001.layout_mos_only.sp` | 同目录 `.layout_mos_only.json` | L6，raw PEX 145 edges |
| B8 L6 `0012` | `pcs-harness-align-origin-main-20260815/generated/analog_harness/grpo_batch_v8_classifier_pool_24_20260823/l0_replay_preparation/source_states/grpo_leung_dfcfc2_0012.source_state.json` | `.../grpo_batch_v8_classifier_stratified9_l1_l6_admission_20260823_terminal_v1/runs/grpo_leung_dfcfc2_0012/cand_0001/case/leung_dfcfc2_pin_3_cand_0001.layout_mos_only.sp` | 同目录 `.layout_mos_only.json` | L6，raw PEX 123 edges |
| B10 placement `0004` | `pcs-harness-align-origin-main-20260815/generated/analog_harness/grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/l0_replay_preparation/source_states/grpo_leung_dfcfc2_0004.source_state.json` | `.../grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/runs/grpo_leung_dfcfc2_0004/cand_0001/case/leung_dfcfc2_pin_3_cand_0001.layout_mos_only.sp` | 同目录 `.layout_mos_only.json` | LP infeasible；`alignGrid.cpp:55` |
| B10 placement `0007` | `pcs-harness-align-origin-main-20260815/generated/analog_harness/grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/l0_replay_preparation/source_states/grpo_leung_dfcfc2_0007.source_state.json` | `.../grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/runs/grpo_leung_dfcfc2_0007/cand_0001/case/leung_dfcfc2_pin_3_cand_0001.layout_mos_only.sp` | 同目录 `.layout_mos_only.json` | LP infeasible；`alignGrid.cpp:55` |
| B10 router `0003` | `pcs-harness-align-origin-main-20260815/generated/analog_harness/grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/l0_replay_preparation/source_states/grpo_leung_dfcfc2_0003.source_state.json` | `.../grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/runs/grpo_leung_dfcfc2_0003/cand_0001/case/leung_dfcfc2_pin_3_cand_0001.layout_mos_only.sp` | 同目录 `.layout_mos_only.json` | `gnda` power routing fail |
| B10 router `0009` | `pcs-harness-align-origin-main-20260815/generated/analog_harness/grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/l0_replay_preparation/source_states/grpo_leung_dfcfc2_0009.source_state.json` | `.../grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/runs/grpo_leung_dfcfc2_0009/cand_0001/case/leung_dfcfc2_pin_3_cand_0001.layout_mos_only.sp` | 同目录 `.layout_mos_only.json` | `vout` signal routing fail |
| B10 LVS `0000` | `pcs-harness-align-origin-main-20260815/generated/analog_harness/grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/l0_replay_preparation/source_states/grpo_leung_dfcfc2_0000.source_state.json` | `.../grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/runs/grpo_leung_dfcfc2_0000/cand_0001/case/leung_dfcfc2_pin_3_cand_0001.layout_mos_only.sp` | 同目录 `.layout_mos_only.json` | raw PEX；device/net mismatch |
| B10 LVS `0011` | `pcs-harness-align-origin-main-20260815/generated/analog_harness/grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/l0_replay_preparation/source_states/grpo_leung_dfcfc2_0011.source_state.json` | `.../grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1/runs/grpo_leung_dfcfc2_0011/cand_0001/case/leung_dfcfc2_pin_3_cand_0001.layout_mos_only.sp` | 同目录 `.layout_mos_only.json` | raw PEX；device/net mismatch |

`...` 在表中统一表示该行前一个明确给出的 batch/run 根目录；实际完整路径可由
相同行的 source-state 路径和 candidate ID 唯一定位。

## 同阶段控制变量核对

九个 `layout_mos_only.json` 去除必然随 run 改变的 `hspice_netlist` 与
`resultDir` 路径字段后，语义 SHA256 前缀均为 `6c84ee7190ad11ea`。所有样本
共享：

- `symmetryConstraintWaivers: [["xm15", "xm14"]]`；
- `signalAnalogWireWidthTable: [[0, 0.1]]`；
- 相同电源网名、MOS-only projection 和 top cell。

因此，这批样本中没有发现 MAGICAL 输入设置、waiver 或环境合同的组间漂移。
变化进入 MAGICAL 的载体是各自生成的 transistor netlist，即由 27 维 sizing
渲染出的 `l/w/multi` 几何。

一个可直接复查的对比：B8 L6 `0004` 的 `xm12` 为 `l=5u, w=10u, multi=395`，
而 B10 placement `0004` 为 `l=5u, w=0.5u, multi=100`；相应 `xm4` 的
`multi` 为 12 与 100。这个差异说明候选确实生成了不同的阵列几何，但**不构成
单变量因果结论**：每个候选同时改变了多个 sizing。

## 已证实失败模式

| 已证实模式 | B10 数量 | 直接日志证据 | 能否归因给单一 sizing |
|---|---:|---|---|
| placement/legalization | 11/24 | LP legalization infeasible，随后 `xm20/xm21` 对称网格对齐断言 | 不能；需单变量受控回放 |
| router 无法完成 | 10/24 | `router.solve returned false`；涉及 `gnda`、`DM_2`、`net063`、`vout` 等 | 不能；需与 L6 的阶段产物比较 |
| raw PEX 后 connectivity LVS fail | 3/24 | `Circuits match uniquely: no`、device mismatch、net mismatch | 不能；需比较 source/extracted connectivity |

## 结论与下一步边界

本审计排除了“B10 使用了不同 MAGICAL 输入设置或不同 waiver”这个解释；B8 与
B10 的分界出现在 sizing 渲染之后的几何实现阶段。它尚未证明任何特定 W/L/M 是
失败根因，也不授权缩窄 action-space 或修改 MAGICAL。

下一步应仅针对上述样本做 **同一个 baseline source-state 的单变量、逐次变化
回放**，记录何时由 L6 变为 placement/router/LVS 失败。该实验必须保持其余 26
维 sizing、环境合同和 MAGICAL 输入不变。
