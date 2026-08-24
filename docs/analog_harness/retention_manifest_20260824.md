# AnalogHarness 存储保留策略与 B11 瘦身 dry-run（2026-08-24）

状态：本文件只生成保留策略和 dry-run 清单，未移动、未删除任何实验文件。

## 总览

- `generated/analog_harness`: 36.9 GiB
- `/home/qlf/IOT/references/.codex-archives`: 6.6 GiB — review_archive_then_optional_purge
- `/home/qlf/IOT/references/pcs-harness-align-origin-main-20260815/.codex-trash`: 2.8 GiB — recoverable_trash_candidate_after_confirmation
- `/home/qlf/IOT/references/qlf--diagnostics/.codex-trash`: 1.2 MiB — recoverable_trash_candidate_after_confirmation

## 最大目录与分类

| size | directory | class | note |
|---:|---|---|---|
| 14.2 GiB | `grpo_batch_v11_pool100_l1_l6_admission_20260824_terminal_v1` | `slim_failed_keep_admitted` | 保留 summary/failure/admitted_graphs、6 条 L6 完整 run；失败/timeout 的大型 GDS 中间产物移入 .codex-trash 后再观察 |
| 4.4 GiB | `grpo_batch_v8_classifier_stratified9_l1_l6_admission_20260823_terminal_v1` | `slim_failed_keep_admitted` | 保留 B8 admitted raw-PEX run 和 full-pool admission 证据；失败 GDS 可瘦身 |
| 3.3 GiB | `grpo_m12_bound_experiment_20260819_v1` | `archive_diagnostic_slim` | M12 边界诊断实验，保留 audit、代表性 L6/失败证据；其余大 GDS 可瘦身 |
| 3.2 GiB | `grpo_batch_v10_pool24_l1_l6_admission_20260823_terminal_v1` | `archive_failure_evidence_slim` | B10 无 L6/raw-PEX admitted，保留 summary/failure/source-state，失败 GDS 可瘦身 |
| 2.7 GiB | `grpo_batch_v4_l1_l6_admission_20260822` | `archive_or_slim_legacy_batch` | 旧 GRPO admission 批次；若已合入后续 dataset，只保留 admitted run + summary/failure evidence |
| 1.3 GiB | `grpo_batch_v2_l1_l6_admission_20260822` | `archive_or_slim_legacy_batch` | 旧 GRPO admission 批次；若已合入后续 dataset，只保留 admitted run + summary/failure evidence |
| 1.2 GiB | `grpo_batch_v6_fresh_recommended5_l1_l6_admission_20260823` | `archive_or_slim_legacy_batch` | 旧 GRPO admission 批次；若已合入后续 dataset，只保留 admitted run + summary/failure evidence |
| 1.1 GiB | `grpo_batch_v3_l1_l6_admission_20260822` | `archive_or_slim_legacy_batch` | 旧 GRPO admission 批次；若已合入后续 dataset，只保留 admitted run + summary/failure evidence |
| 1.0 GiB | `grpo_batch_v6_remaining_top3_l1_l6_admission_20260823_terminal_v2` | `archive_or_slim_legacy_batch` | 旧 GRPO admission 批次；若已合入后续 dataset，只保留 admitted run + summary/failure evidence |
| 809.7 MiB | `stage3_amplifier_coverage_v1` | `keep_or_light_archive_baseline` | 基线/复现实验，体量较小或有复现价值；暂不优先清理 |
| 808.6 MiB | `grpo_batch_v5_step1_recommended_l1_l6_admission_20260823_envfix_v3` | `archive_or_slim_legacy_batch` | 旧 GRPO admission 批次；若已合入后续 dataset，只保留 admitted run + summary/failure evidence |
| 708.2 MiB | `grpo_batch_v7_fresh_recommended5_l1_l6_admission_20260823_terminal_v1` | `archive_or_slim_legacy_batch` | 旧 GRPO admission 批次；若已合入后续 dataset，只保留 admitted run + summary/failure evidence |
| 654.2 MiB | `grpo_b8_0004_biascm_geometry_controlled_replay_20260823_v1` | `review_later` | 未归类，小体量或非当前主线，暂缓处理 |
| 313.4 MiB | `stage3_full_regression_20260816_regenerated_raw_v1` | `keep_or_light_archive_baseline` | 基线/复现实验，体量较小或有复现价值；暂不优先清理 |
| 244.8 MiB | `smcnr_sizing_sweep_combo_20260817_v1` | `keep_or_light_archive_baseline` | 基线/复现实验，体量较小或有复现价值；暂不优先清理 |
| 244.5 MiB | `smcnr_sizing_sweep_20260817_v1` | `keep_or_light_archive_baseline` | 基线/复现实验，体量较小或有复现价值；暂不优先清理 |
| 155.9 MiB | `patent_min_cause_replay_20260823` | `review_later` | 未归类，小体量或非当前主线，暂缓处理 |
| 155.5 MiB | `patent_min_cause_place_replay_20260823` | `review_later` | 未归类，小体量或非当前主线，暂缓处理 |
| 75.7 MiB | `parasitic_modeling` | `keep_research_outputs` | 寄生建模 dataset/eval 研究主资产 |
| 64.2 MiB | `fan_smc_reproduction_sweep_20260817_v1` | `keep_or_light_archive_baseline` | 基线/复现实验，体量较小或有复现价值；暂不优先清理 |
| 61.6 MiB | `sau_cfcc_reproduction_sweep_20260818_v1` | `keep_or_light_archive_baseline` | 基线/复现实验，体量较小或有复现价值；暂不优先清理 |
| 61.1 MiB | `sizing_candidate_replay_20260817_v1` | `review_later` | 未归类，小体量或非当前主线，暂缓处理 |
| 59.8 MiB | `stage2_route_connectivity_repair_v1` | `review_later` | 未归类，小体量或非当前主线，暂缓处理 |
| 54.8 MiB | `leung_nmcf_reproduction_sweep_20260818_v1` | `keep_or_light_archive_baseline` | 基线/复现实验，体量较小或有复现价值；暂不优先清理 |
| 26.9 MiB | `alfio_raffc_effective_sweep_v2_20260819_v1` | `review_later` | 未归类，小体量或非当前主线，暂缓处理 |
| 20.9 MiB | `fan_smc_reproduction_probe_20260817_v1` | `review_later` | 未归类，小体量或非当前主线，暂缓处理 |
| 20.3 MiB | `leung_nmcf_reproduction_probe_20260818_v1` | `review_later` | 未归类，小体量或非当前主线，暂缓处理 |
| 20.1 MiB | `sau_cfcc_reproduction_probe_20260818_v1` | `review_later` | 未归类，小体量或非当前主线，暂缓处理 |
| 15.7 MiB | `alfio_raffc_reproduction_sweep_20260818_v1` | `keep_or_light_archive_baseline` | 基线/复现实验，体量较小或有复现价值；暂不优先清理 |
| 5.8 MiB | `fan_smc_sizing_sweep_20260817_v1` | `keep_or_light_archive_baseline` | 基线/复现实验，体量较小或有复现价值；暂不优先清理 |

## B11 dry-run 策略

- B11 路径：`/home/qlf/IOT/references/pcs-harness-align-origin-main-20260815/generated/analog_harness/grpo_batch_v11_pool100_l1_l6_admission_20260824_terminal_v1`
- B11 大小：14.2 GiB
- 保留完整 run 的 admitted candidates：grpo_leung_dfcfc2_0011, grpo_leung_dfcfc2_0032, grpo_leung_dfcfc2_0038, grpo_leung_dfcfc2_0045, grpo_leung_dfcfc2_0057, grpo_leung_dfcfc2_0083
- dry-run 候选移动文件数：2715
- dry-run 可释放/迁移大小：13.5 GiB
- 确认后目标回收目录：`/home/qlf/IOT/references/pcs-harness-align-origin-main-20260815/.codex-trash/slimmed_grpo_batch_v11_pool100_20260824`

### 将保留

- `admission_summary.json`
- `admitted_graphs.jsonl`
- `physical_closure_failure_labels.jsonl`
- `promotion_results.jsonl`
- `promotion_progress.json`
- `environment_preflight.json`
- `run_plan.json`
- `l0_replay_preparation/`
- `configs/`
- `logs/`
- `runs/<6 admitted candidates>/`

### dry-run 移动规则

仅建议把 B11 中 **非 admitted candidate** 的 `*.gds` 大型中间版图移入 `.codex-trash`，不碰 summary、labels、source_state、raw SPICE、logs、configs，也不碰 6 条 admitted run。

### 最大 dry-run 文件 Top 30

| size | candidate | relative path |
|---:|---|---|
| 638.5 MiB | `grpo_leung_dfcfc2_0060` | `runs/grpo_leung_dfcfc2_0060/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 513.1 MiB | `grpo_leung_dfcfc2_0093` | `runs/grpo_leung_dfcfc2_0093/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 494.9 MiB | `grpo_leung_dfcfc2_0024` | `runs/grpo_leung_dfcfc2_0024/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 428.7 MiB | `grpo_leung_dfcfc2_0021` | `runs/grpo_leung_dfcfc2_0021/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 416.3 MiB | `grpo_leung_dfcfc2_0061` | `runs/grpo_leung_dfcfc2_0061/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 405.5 MiB | `grpo_leung_dfcfc2_0069` | `runs/grpo_leung_dfcfc2_0069/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 398.1 MiB | `grpo_leung_dfcfc2_0095` | `runs/grpo_leung_dfcfc2_0095/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 345.9 MiB | `grpo_leung_dfcfc2_0082` | `runs/grpo_leung_dfcfc2_0082/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 336.2 MiB | `grpo_leung_dfcfc2_0008` | `runs/grpo_leung_dfcfc2_0008/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 335.5 MiB | `grpo_leung_dfcfc2_0099` | `runs/grpo_leung_dfcfc2_0099/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 333.3 MiB | `grpo_leung_dfcfc2_0006` | `runs/grpo_leung_dfcfc2_0006/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 306.9 MiB | `grpo_leung_dfcfc2_0041` | `runs/grpo_leung_dfcfc2_0041/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 274.2 MiB | `grpo_leung_dfcfc2_0089` | `runs/grpo_leung_dfcfc2_0089/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 235.3 MiB | `grpo_leung_dfcfc2_0096` | `runs/grpo_leung_dfcfc2_0096/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 231.6 MiB | `grpo_leung_dfcfc2_0054` | `runs/grpo_leung_dfcfc2_0054/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 218.1 MiB | `grpo_leung_dfcfc2_0084` | `runs/grpo_leung_dfcfc2_0084/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 213.9 MiB | `grpo_leung_dfcfc2_0088` | `runs/grpo_leung_dfcfc2_0088/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 208.8 MiB | `grpo_leung_dfcfc2_0009` | `runs/grpo_leung_dfcfc2_0009/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 204.8 MiB | `grpo_leung_dfcfc2_0036` | `runs/grpo_leung_dfcfc2_0036/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 204.5 MiB | `grpo_leung_dfcfc2_0027` | `runs/grpo_leung_dfcfc2_0027/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 198.3 MiB | `grpo_leung_dfcfc2_0047` | `runs/grpo_leung_dfcfc2_0047/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 191.7 MiB | `grpo_leung_dfcfc2_0067` | `runs/grpo_leung_dfcfc2_0067/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 189.6 MiB | `grpo_leung_dfcfc2_0074` | `runs/grpo_leung_dfcfc2_0074/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 172.3 MiB | `grpo_leung_dfcfc2_0072` | `runs/grpo_leung_dfcfc2_0072/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 163.4 MiB | `grpo_leung_dfcfc2_0048` | `runs/grpo_leung_dfcfc2_0048/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 154.3 MiB | `grpo_leung_dfcfc2_0076` | `runs/grpo_leung_dfcfc2_0076/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 150.8 MiB | `grpo_leung_dfcfc2_0010` | `runs/grpo_leung_dfcfc2_0010/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 150.6 MiB | `grpo_leung_dfcfc2_0090` | `runs/grpo_leung_dfcfc2_0090/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 146.9 MiB | `grpo_leung_dfcfc2_0034` | `runs/grpo_leung_dfcfc2_0034/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |
| 146.9 MiB | `grpo_leung_dfcfc2_0081` | `runs/grpo_leung_dfcfc2_0081/cand_0001/case/leung_dfcfc2_pin_3_init.gds` |

完整 dry-run 清单见：

- `/home/qlf/IOT/references/qlf--diagnostics/generated/storage_retention/retention_manifest_20260824/b11_slim_dry_run_moves_20260824.jsonl`
- `/home/qlf/IOT/references/qlf--diagnostics/generated/storage_retention/retention_manifest_20260824/retention_manifest_20260824.json`

## 后续确认门

执行实际移动前，需要用户明确确认。建议命令由脚本逐条 `mkdir -p target.parent && mv source target` 完成，保持可恢复。

## 实际清理记录

执行时间：2026-08-24 14:27:57 CST

本次目标是在尽可能保留实验进度、数据和结论的前提下，释放 `IOT` 仓库相关产物占用的空间。实际执行时，优先处理“非 admitted 的大型中间 GDS”和 `.codex-trash`，不动当前默认训练集、B11 的 summary/label、6 条 admitted raw PEX 证据和 profile/family-aware evaluation 结果。

### 已释放/瘦身

- B11 非 admitted candidate 的大型 `*.gds`：dry-run 清单 2715 个，实际确认 2715/2715 已不存在；按 dry-run 估算约 13.50 GiB。
- B11 admission 目录：从约 14.2 GiB 降到 788 MiB。
- `generated/analog_harness` 总目录：从约 36.9 GiB 降到约 24 GiB。
- PCS worktree `.codex-trash`：约 2.8 GiB，已清空；root-owned 剩余项通过 Docker root 视角清理，最终目录不存在。
- `qlf--diagnostics/.codex-trash`：约 1.2 MiB，已清空，最终目录不存在。

### 明确保留

- dataset v9：
  - `/home/qlf/IOT/references/qlf--diagnostics/generated/parasitic_modeling/graph_learning_samples_20260824_75graphs_grpo_batch_v11_pool100_dataset_v9/`
- profile comparison v9：
  - `/home/qlf/IOT/references/qlf--diagnostics/generated/parasitic_modeling/profile_comparison_20260824_dataset_v9/profile_comparison.json`
- family-aware eval v9：
  - `/home/qlf/IOT/references/qlf--diagnostics/generated/parasitic_modeling/family_aware_eval_20260824_dataset_v9/`
- B11 admission 证据：
  - `admission_summary.json`
  - `admitted_graphs.jsonl`
  - `physical_closure_failure_labels.jsonl`
  - `promotion_results.jsonl`
  - `promotion_progress.json`
  - `environment_preflight.json`
  - `run_plan.json`
  - `l0_replay_preparation/`
  - `configs/`
  - `logs/`
  - 6 条 admitted run 的 raw PEX 和 GDS：
    - `grpo_leung_dfcfc2_0011`
    - `grpo_leung_dfcfc2_0032`
    - `grpo_leung_dfcfc2_0038`
    - `grpo_leung_dfcfc2_0045`
    - `grpo_leung_dfcfc2_0057`
    - `grpo_leung_dfcfc2_0083`

### 验证结果

- B11 summary 仍可读：
  - 100 candidates
  - 100 L0 replayable
  - 6 `l6_admitted_raw_pex_graph`
  - 77 `physical_closure_failed_no_raw_pex`
  - 11 `raw_pex_available_not_l6`
  - 6 `simulation_timeout_or_hang`
- 6 条 admitted run 均确认至少存在 1 个 `*_extracted.raw.spice`，且各自保留 34 个 GDS。
- dry-run 清单中的 2715 个非 admitted GDS：剩余存在数为 0。
- dataset v9 可解析：75 graphs，75 unique graph ids，1215 nodes，7455 cap edges，edge cardinality mismatch 为 0。
- 项目相关 graph/dataset/profile/family-aware 测试：16 tests OK。

### 暂未处理

- `/home/qlf/IOT/references/.codex-archives`：约 6.6 GiB，未动。
- B8/B10/M12 bound experiment 等旧批次大目录：未在本轮继续瘦身，避免把仍可能用于失败归因/对照审计的材料误删。
- Windows D 盘上的 WSL 虚拟磁盘文件可能不会因 Linux 内部删除而立即物理缩小；若需要让 Windows 资源管理器看到 D 盘回收空间，还需要在确认 Linux 内部状态稳定后执行 WSL shutdown + VHDX compact。

### 实际清理产物

- `/home/qlf/IOT/references/qlf--diagnostics/generated/storage_retention/retention_manifest_20260824/b11_slim_actual_summary_20260824.json`
- `/home/qlf/IOT/references/qlf--diagnostics/generated/storage_retention/retention_manifest_20260824/b11_slim_actual_deleted_gds_20260824.jsonl`
- `/home/qlf/IOT/references/qlf--diagnostics/generated/storage_retention/retention_manifest_20260824/pcs_codex_trash_inventory_before_purge_20260824.jsonl`
- `/home/qlf/IOT/references/qlf--diagnostics/generated/storage_retention/retention_manifest_20260824/pcs_codex_trash_purge_summary_20260824.json`
- `/home/qlf/IOT/references/qlf--diagnostics/generated/storage_retention/retention_manifest_20260824/qlf_codex_trash_purge_summary_20260824.json`
