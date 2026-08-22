# GRPO-to-PCS admission runner

生成日期：2026-08-22

## 目的

`tools/analog_harness/grpo_to_pcs_admission_runner.py` 把之前 batch v2/v3/v4 中手动执行的步骤固化成一个可复现终端入口：

```text
L0 sizing manifest / batch replay manifest
→ per-candidate isolated PCS config
→ promote-source-candidate with timeout
→ promotion_results / progress
→ admission_summary / admitted_graphs / failure labels
```

它不替代 PCS 的正式物理闭合逻辑；真正的 layout/DRC/LVS/PEX/post-layout sim 仍由现有：

```bash
python3 -m tools.analog_harness.cli promote-source-candidate
```

执行。runner 只负责长期批量实验的编排、断点续跑和证据汇总。

## 推荐用法

### 1. 先 dry-run 检查命令

```bash
cd /home/qlf/IOT/references/pcs-harness-align-origin-main-20260815

PYTHONPATH=. python3 tools/analog_harness/grpo_to_pcs_admission_runner.py \
  --batch-replay-manifest generated/analog_harness/grpo_batch_v4_l1_l6_admission_20260822/l0_replay_preparation/batch_replay_manifest.json \
  --output-dir generated/analog_harness/grpo_batch_v5_l1_l6_admission_YYYYMMDD \
  --timeout-s 1800 \
  --kill-after-s 60 \
  --dry-run
```

dry-run 只生成：

- `run_plan.json`
- `configs/<candidate_id>.yaml`
- `promotion_progress.json`

不会调用 MAGICAL、Magic、Netgen 或 ngspice。

### 2. 正式运行

```bash
PYTHONPATH=. python3 tools/analog_harness/grpo_to_pcs_admission_runner.py \
  --batch-replay-manifest generated/analog_harness/grpo_batch_v5_l1_l6_admission_YYYYMMDD/l0_replay_preparation/batch_replay_manifest.json \
  --output-dir generated/analog_harness/grpo_batch_v5_l1_l6_admission_YYYYMMDD \
  --timeout-s 1800 \
  --kill-after-s 60 \
  --resume
```

`--resume` 会读取已有 `promotion_results.jsonl`，跳过已经记录过 returncode 的 candidate。

### 3. 从 L0 sizing manifest 开始

如果输入是标准 sizing manifest，可以直接：

```bash
PYTHONPATH=. python3 tools/analog_harness/grpo_to_pcs_admission_runner.py \
  --sizing-manifest path/to/replayable_sizing_manifest.json \
  --output-dir generated/analog_harness/grpo_batch_v5_l1_l6_admission_YYYYMMDD \
  --timeout-s 1800 \
  --kill-after-s 60 \
  --resume
```

runner 会先调用现有 L0 preparation，生成：

- `l0_replay_preparation/source_states/*.source_state.json`
- `l0_replay_preparation/batch_replay_manifest.json`

然后进入 PCS admission。

## 输出

正式运行结束后，标准输出目录包含：

- `run_plan.json`
- `configs/<candidate_id>.yaml`
- `logs/<candidate_id>.stdout.json`
- `logs/<candidate_id>.stderr.log`
- `promotion_results.jsonl`
- `promotion_progress.json`
- `admission_summary.json`
- `admitted_graphs.jsonl`
- `physical_closure_failure_labels.jsonl`
- `timeout_labels.jsonl`
- `raw_pex_available_not_l6.jsonl`
- `admission_table.csv`

默认训练集只接收：

```text
admission_status == admitted_raw_pex_graph
```

也就是同时满足：

- `best_closure_level == L6_post_layout_pvt`
- 存在 verified `*_extracted.raw.spice`

timeout 样本会标记为：

```text
simulation_timeout_or_hang
```

它们保留为 admission/failure 证据，但不进入默认 graph training。

## batch v4 dry-run 验证

已用现有 batch v4 replay manifest 做 dry-run 验证：

```text
total jobs: 24
status: dry_run
per-candidate configs generated: yes
```

验证命令：

```bash
PYTHONPATH=. python3 tools/analog_harness/tests/test_grpo_to_pcs_admission_runner.py
PYTHONPATH=. python3 tools/analog_harness/grpo_to_pcs_admission_runner.py \
  --batch-replay-manifest generated/analog_harness/grpo_batch_v4_l1_l6_admission_20260822/l0_replay_preparation/batch_replay_manifest.json \
  --output-dir generated/analog_harness/grpo_batch_v4_runner_dry_run_20260822 \
  --dry-run \
  --timeout-s 1800 \
  --kill-after-s 60
```

## 边界

- runner 不修改 action-space。
- runner 不根据 classifier 直接判定 pass/fail。
- runner 不把 GRPO sizing 直接变成训练样本。
- runner 不绕过 PCS/MAGICAL/Magic/Netgen/ngspice。
- runner 只是长期生产数据的批处理入口；最终 admission 仍以真实 L0→L6/raw PEX 证据为准。

