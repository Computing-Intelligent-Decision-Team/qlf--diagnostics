# Tasks

| task_id | title | status | depends_on | target | artifact | verify |
|---|---|---|---|---|---|---|
| T001 | DFCFC2 正式数据集封口审计 | done | - | `datasets/dfcfc2_parasitic/current` | `dfcfc2_dataset_closure_audit.md` | dataset/manifest/sample schema/count/hash 可复查 |
| T002 | SMCNR 历史数据可信性审计 | done | T001 | retired SMCNR worktree outputs | `smcnr_legacy_data_audit.md` | DRC/LVS/PEX/sizing/provenance 文件存在性可复查 |
| T003 | SMCNR 当前流程 3-5 样本 pilot 准备/执行 | done | T002 | current PCS SMCNR graph dataset | `smcnr_pilot_5_current_graphs/` | 5 个 pilot graph 均 L6 且 raw_spice_source_verified |
