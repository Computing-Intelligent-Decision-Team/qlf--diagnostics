# physical_closure_classifier_v1：GRPO→PCS 物理闭合小样本诊断

生成时间：2026-08-22

## 结论

基于 batch v2 + batch v3 的 24 条 GRPO→PCS admission 结果，已经生成 `physical_closure_classifier_v1`。它不是正式可泛化模型，而是一个小样本诊断器，用来指导 batch v4 的受控采样。

核心结论：

- 24 条里有 7 条进入 `admitted_raw_pex_graph`，也就是 L6 + raw PEX graph 可训练样本。
- 13 条停在 `physical_closure_failed`，没有 raw PEX graph。
- 4 条有 raw PEX，但没有达到 L6，不进入默认图训练集。
- 模型输入只使用 GRPO/source_state 中物理运行前可知的 sizing/export 特征，不使用 `pex_cap_count`、`pex_total_cap_ff` 等结果字段，避免 label leakage。
- LOO 结果显示：线性 logistic 表现很差，浅层 tree 明显更好，说明当前 failure boundary 更像组合型物理闭合边界，不适合继续只看 `M12`。

## 产物路径

主输出目录：

```text
generated/physical_closure_classifier_20260822_v1/
```

关键文件：

```text
admission_table.csv
admission_table.jsonl
feature_matrix.csv
label_matrix.csv
label_matrix.jsonl
leave_one_out_predictions.csv
model_metrics.json
feature_importance.csv
univariate_feature_summary.csv
feature_summary.json
batch_v4_sampling_recommendation.md
batch_v4_sampling_recommendation.json
manifest.json
```

生成脚本：

```text
tools/analog_harness/ml/physical_closure_classifier.py
```

测试：

```text
tools/analog_harness/tests/test_physical_closure_classifier.py
```

## 输入数据

使用两批 admission summary：

```text
generated/grpo_to_pcs_admission_batch_v2_20260822/admission_summary_v2.json
generated/grpo_to_pcs_admission_batch_v3_20260822/admission_summary_v3.json
```

对应 source_state 从 PCS 对齐 worktree 读取：

```text
/home/qlf/IOT/references/pcs-harness-align-origin-main-20260815
```

每条样本通过 `batch_id/candidate_id` 形成唯一 ID，避免 v2/v3 中 `grpo_leung_dfcfc2_000x` 名字重复。

## 标签定义

默认二分类标签：

```text
graph_training_admitted = 1
```

仅当：

```text
admission_status == admitted_raw_pex_graph
```

也就是说，只有真实通过 L6 且有 raw PEX graph 的候选才算正样本。

同时保留多类状态：

```text
admitted_raw_pex_graph
raw_pex_available_not_l6
physical_closure_failed
```

本次统计：

```text
total records: 24
admitted_raw_pex_graph: 7
physical_closure_failed: 13
raw_pex_available_not_l6: 4
raw_pex_available total: 11
feature count: 111
```

## 特征定义

使用 admission 前可知特征：

- 27 维 sizing 值：MOS W/L/M、电流、电容；
- 27 维 normalized GRPO action；
- 派生 MOS 统计：PMOS/NMOS 的 W/L/M sum/mean/min/max；
- 派生版图复杂度 proxy：
  - `mos_width_times_m_sum`
  - `mos_gate_area_proxy_sum`
  - `mos_aspect_times_m_sum`
  - `pmos_to_nmos_m_ratio`
  - `requested_cap_sum`
  - `bias_current_sum`
- batch v3 的 selection bucket one-hot，仅作为诊断上下文。

明确不进入 feature matrix 的结果变量：

```text
pex_cap_count
pex_total_cap_ff
raw_spice_sha256
best_closure_level
failure_stage
admission_status
```

这些只出现在 admission/label 表里，不作为模型输入。

## Baseline 结果

Leave-one-out evaluation：

| model | accuracy | balanced accuracy | precision | recall | F1 | confusion matrix |
|---|---:|---:|---:|---:|---:|---|
| dummy_most_frequent | 0.708 | 0.500 | 0.000 | 0.000 | 0.000 | tp=0, tn=17, fp=0, fn=7 |
| logistic_l2_balanced | 0.333 | 0.277 | 0.091 | 0.143 | 0.111 | tp=1, tn=7, fp=10, fn=6 |
| decision_tree_depth3_balanced | 0.792 | 0.727 | 0.667 | 0.571 | 0.615 | tp=4, tn=15, fp=2, fn=3 |

解释：

- dummy 的 accuracy 高是因为负样本多，但它完全找不到 admitted 样本，所以 F1=0。
- logistic 很差，说明当前 24 条里不存在简单线性边界。
- depth-3 tree 在 LOO 上相对最好，但样本太少，不能把它当成稳定规律。

## 当前最强的单变量诊断信号

按 admitted 与 not-admitted 的标准化均值差排序，前几项是：

| feature | admitted mean | not-admitted mean | direction |
|---|---:|---:|---|
| `mos_width_times_m_sum` | 1953.44 | 2811.70 | admitted 更小 |
| `sizing__mosfet_12_1_w_gmf2_pmos` | 3.30 | 5.07 | admitted 更小 |
| `sizing__mosfet_23_2_m_load2_nmos` | 30.00 | 40.88 | admitted 更小 |
| `sizing__mosfet_25_1_m_gm3_nmos` | 30.43 | 19.65 | admitted 更大 |
| `sizing__mosfet_23_2_w_load2_nmos` | 4.66 | 6.69 | admitted 更小 |

这些不是 hard rule，只是 batch v2+v3 的候选分布里出现的经验信号。

## 对 batch v4 的建议

不要把 action-space 改死，也不要写成 “M12 大于某个值就丢”。batch v3 已经证明 `M12=392/394` 仍然可以 L6。

建议 batch v4：

1. 仍然使用 AnalogGym-aligned action-space contract。
2. 先导出更大的 fresh GRPO candidate pool。
3. 用 `physical_closure_classifier_v1` 或其统计特征做 sampling guide，而不是 admission oracle。
4. 分层采样：
   - 高预测闭合概率：增加 raw PEX graph 正样本；
   - 中等不确定区：刻画边界；
   - 高风险区：保留少量 failure 样本，防止模型只学习幸存者偏差。
5. 下一批建议 24–36 条，并继续记录：
   - L6 admitted；
   - raw PEX available but not L6；
   - physical closure failed no raw；
   - 具体失败阶段。

最终是否进入寄生图训练集，仍然只能由真实 L0→L6 + raw PEX admission 决定。

## 复现命令

```bash
cd /home/qlf/IOT/references/qlf--diagnostics
python3 tools/analog_harness/tests/test_physical_closure_classifier.py
python3 tools/analog_harness/ml/physical_closure_classifier.py
```

验证摘要：

```text
Ran 4 tests in 0.011s
OK

record_count: 24
feature_count: 111
admitted_count: 7
label_counts:
  admitted_raw_pex_graph: 7
  physical_closure_failed: 13
  raw_pex_available_not_l6: 4
```
