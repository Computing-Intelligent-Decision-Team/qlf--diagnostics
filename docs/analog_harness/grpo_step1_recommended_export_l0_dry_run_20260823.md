# GRPO step-1 recommended candidates → PCS L0 dry-run 记录（2026-08-23）

## 结论

本次完成的是主线 A：把本地 AnalogGym-Opt 的短步 GRPO 推荐候选转换成 PCS 可接收的 sizing manifest，并执行 runner dry-run。

这一步只证明：

- GRPO 产物能被标准 export contract 读取；
- action vector 能映射成 Leung DFCFC2 的 PCS sizing；
- 这些 sizing 通过 PCS L0 ingest/config 合法性检查；
- runner 可以生成后续 L1-L6 admission 所需的 replay jobs。

这一步不证明：

- 已完成 layout / DRC / LVS / PEX；
- 已生成 raw PEX graph；
- 已进入默认寄生图训练集。

## 数据来源

- AnalogGym-Opt repo: `/home/qlf/IOT/references/AnalogGym-Opt-9f2cbba1463efeb5d6160311630e5d56b297f9bf`
- source commit: `9f2cbba1463efeb5d6160311630e5d56b297f9bf`
- run dir: `training_saves/grpo_amp_dfcfc2_20260821-204623`
- source file: `recommended_candidates_tt/recommended_candidates.json`
- circuit id: `amp_dfcfc2`
- target PCS design id: `leung_dfcfc2_pin_3`
- action-space contract id: `leung_dfcfc2_pin_3.analoggym_action_space_v1`

## 本次产物

复制到 qlf--diagnostics 的证据包：

```text
generated/grpo_to_pcs_admission_batch_v5_step1_recommended_20260823/
├── export/
│   ├── grpo_export_contract.json
│   ├── grpo_export_candidates_for_pcs.jsonl
│   ├── grpo_sizing_manifest.yaml
│   ├── source_summary.json
│   └── manifest_bundle/
│       ├── grpo_sizing_manifest.yaml
│       ├── replayable_sizing_manifest.yaml
│       ├── physical_closure_failure_labels.jsonl
│       └── README.md
└── l0_dry_run/
    ├── dry_run_summary.json
    ├── promotion_progress.json
    ├── run_plan.json
    └── l0_replay_preparation/
        ├── batch_replay_manifest.json
        ├── candidate_replay_jobs.csv
        ├── validated_sizing_manifest.json
        └── README.md
```

## 数量

- 原始推荐展示记录：`5`
- 标准 export 去重后候选：`4`
- 跳过的无 action 向量记录：`13`
- L0 replayable：`4/4`
- L0 invalid：`0/4`
- dry-run jobs：`4`

去重原因：export 以完整 `action_real` 向量作为候选身份；重复 sizing 不重复进入 PCS admission。

## 边界

当前 runner 的 `--dry-run` 分支会写：

- `run_plan.json`
- `promotion_progress.json`
- L0 replay preparation 目录

但不会写真实 admission 运行后的 `admission_summary.json`。因此本次额外记录 `dry_run_summary.json`，并明确其状态是：

```text
dry_run_prepared
```

后续若要进入寄生图训练样本，必须继续对这些 replay jobs 执行正式 L1-L6 admission，并且只有满足 L6 + raw PEX 的候选才能进入默认 graph dataset。

## 验证命令

在 PCS worktree 中执行：

```bash
PYTHONPATH=. python3 tools/analog_harness/tests/test_analoggym_grpo_manifest.py
PYTHONPATH=. python3 tools/analog_harness/tests/test_sizing_candidate_manifest.py
PYTHONPATH=. python3 tools/analog_harness/tests/test_grpo_to_pcs_admission_runner.py
PYTHONPATH=/home/qlf/IOT/references/qlf--diagnostics \
  python3 /home/qlf/IOT/references/qlf--diagnostics/tools/analog_harness/ml/grpo_export_contract.py \
  validate generated/analog_harness/grpo_batch_v5_step1_recommended_20260823/grpo_export_contract.json
```

结果：

```text
test_analoggym_grpo_manifest.py: 3 tests OK
test_sizing_candidate_manifest.py: 3 tests OK
test_grpo_to_pcs_admission_runner.py: 3 tests OK
grpo_export_contract validate: status ok, candidate_count 4
```

## 下一步

主线 A 的下一步可以二选一：

1. 对这 4 条 step-1 recommended candidates 做正式 L1-L6 admission；
2. 先完善外置 YAML 版 action mapping contract，把当前 PCS 代码内的 Leung/DFCFC2 显式映射转成可版本化文件。

主线 B（长时间重新训练 GRPO policy）暂时不做。
