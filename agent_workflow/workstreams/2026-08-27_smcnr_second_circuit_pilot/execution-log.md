# Execution Log

### 2026-08-27 CST | Workstream start

- goal: 完成前三步：DFCFC2 封口、SMCNR 旧数据审计、SMCNR 3-5 样本 pilot。
- boundary: 不进入第四步多电路建模；不盲跑 100 个；不破坏现有 DFCFC2 正式数据集。

### 2026-08-27 CST | T001

- action: 审计 `datasets/dfcfc2_parasitic/current` 软链接指向的正式 DFCFC2 数据集，读取 `dataset.json`、`AUDIT_REPORT.json`、CSV/JSONL/统计文件并记录关键 SHA256。
- result: DFCFC2 当前封口版本为 95 个可信样本、27 维 sizing、12052 条电容边、1805 条节点记录；硬门为 sizing lineage、DRC pass、connectivity LVS pass、parseable raw PEX；PM/reward/PVT/performance 为 observation-only。
- artifact: `dfcfc2_dataset_closure_audit.md`。
- verify: `dataset.json` schema 为 `dfcfc2_trusted_parasitic_corpus.v1`；`counts.samples=95`；`counts.sizing_dimension=27`；关键文件 SHA256 已记录。

### 2026-08-27 CST | T002

- action: 审计历史 SMCNR fixed-GDS L6 candidate 和当前 main 中的 32-graph SMCNR combo dataset。
- result: 历史 SMCNR candidate 为 `L6_post_layout_pvt`，23 维 values/action，DRC=0，connectivity LVS=yes，raw PEX 有 34 条电容线，PEX total cap 432.739 fF，PVT 3/3；关键 state/raw PEX/GDS/LVS/PVT 文件均存在。当前 32-graph dataset 为 `parasitic_graph_learning_samples.v1.32_smcnr_combo_20260817`，缺失 required checks 为 0。
- decision: 历史 fixed-GDS SMCNR 可作为环境/版图血缘锚点；当前 regenerated-layout controlled SMCNR rows 才适合作为 sizing-response pilot。
- artifact: `smcnr_legacy_data_audit.md`。
- verify: `state.json`、raw PEX、connectivity PEX、source connectivity、GDS、corner evidence、case JSON、net identity audit 均存在并记录 SHA256。

### 2026-08-27 CST | T003

- action: 从当前 32-graph SMCNR combo dataset 中抽取 5 个 pilot graphs：baseline、`diff_pair_w` 正负扰动、`second_stage_pmos_w` 扰动、一个双变量 combo。
- result: 生成 `smcnr_pilot_5_current_graphs/pilot_graphs.json` 与 `pilot_graphs.jsonl`。5 个样本均为 `L6_post_layout_pvt` 且 `raw_spice_source_verified=True`，覆盖 cap_count 32--33、total_cap 763.42667--765.46556 fF、output-node cap 645.06645--645.69675 fF。
- artifact: `smcnr_pilot_5_current_graphs/README.md`；`smcnr_pilot_5_current_graphs/pilot_graphs.json`；`smcnr_pilot_5_current_graphs/pilot_graphs.jsonl`。
- verify: source dataset missing required checks = 0；pilot selected graphs = 5；所有 selected rows 具备 L6 closure 和 raw-SPICE source verification。
