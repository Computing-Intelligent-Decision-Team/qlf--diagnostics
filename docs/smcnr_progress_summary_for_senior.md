# SMCNR 寄生参数建模阶段进展说明

**日期**：2026-06-24
**目的**：说明从师兄上传 SMCNR 相关 GitHub 数据后，我们在 AnalogHarness 中完成的验证、数据整理、问题定位、样本扩展，以及下一步计划。

## 1. 背景

最开始我们的核心问题是：

> 师兄上传的 SMCNR 成功样本，能不能在我们本地环境中复现？
> 如果能复现，能不能基于它继续产生更多可用于寄生参数建模的数据？

这里的“寄生参数建模”主要指：从电路参数、版图结果、抽取网表中学习寄生电容的变化规律。我们目前关注的是 PEX（寄生参数提取）里的电容数量、电容连接关系、总电容，以及关键节点电容变化。

需要强调的是，师兄的 `SMCNR_SE_2st_AMP/cand_0031` 仍然是目前唯一经过完整审查的成功基线样本。后续新生成的样本，目前都只是“通过了寄生参数相关检查的候选样本”，还不能直接称为训练正样本。

## 2. 已完成的主要工作

### 2.1 拉取并审查师兄上传的 SMCNR 数据

我们首先对师兄上传到 GitHub 的 SMCNR 相关数据进行了审查，包括：

- GDS 版图文件
- extracted SPICE 抽取网表
- LVS 结果
- PEX 结果
- state/evidence 记录
- 上游完整运行制品压缩包

产出包括：

- `docs/smcnr_upstream_artifact_request.md`
- `docs/smcnr_upstream_vs_local_diff.md`
- `docs/smcnr_current_truth_baseline.md`
- `reproducibility/smcnr_se_2st_amp/upstream_artifacts/`

结论：

- 师兄的 `cand_0031` 是真实可用的成功样本。
- 它不是 AnalogGym-Opt 仓库直接跑出来的普通样本，而是在 AnalogHarness 中经过封装、审查和证据整理后的正基线。
- 它目前仍是唯一可以稳妥称为“已审查成功基线”的样本。

### 2.2 本地复现 SMCNR 的抽取和 LVS

我们在当前 Linux 环境中复跑了 SMCNR 的关键验证链路：

- Magic DRC：0 errors
- Magic extraction：`equiv=0`
- Netgen LVS：通过，8 个 MOS 对 8 个 MOS，9 个网络对 9 个网络
- PEX：可解析出寄生电容

产出包括：

- `docs/smcnr_local_replay_readiness.md`
- `docs/smcnr_local_replay_report.md`

结论：

- 当前本地环境可以复现师兄上传的 SMCNR 成功样本。
- 这使得后续基于 SMCNR 做数据扩展有了基础。

### 2.3 排查为什么其他电路大多失败

我们尝试了 Fan_SMC、DFCFC2、NMCNR 等电路。结果发现：

- DRC 往往可以通过。
- 但 LVS 或 extraction 经常失败。
- 主要问题不是简单的几何违规，而是抽取过程中出现 substrate/well 相关的网络塌陷或节点错误合并。

典型情况：

- Fan_SMC：出现 `vout-vdda-gnda` 之类的网络等价问题。
- DFCFC2：存在 MIM 电容映射和 substrate collapse 问题。
- NMCNR：MOS-only 后仍出现 well merging 或网络数量不匹配。

相关文档：

- `docs/nmcnr_mos_only_layout_probe.md`
- `docs/nmcnr_harness_readiness_audit.md`
- `docs/smcnr_nf2_failure_taxonomy.md`

结论：

- 目前不能简单认为“AnalogGym 里的任意电路都能直接进入数据生产”。
- 当前最稳的方向仍然是围绕已经成功的 SMCNR 做受控扩展。

### 2.4 明确 SMCNR 的可靠路径：MOS-only projection

早期我们尝试直接把完整网表送入 MAGICAL，其中包括电阻、电容等被动器件。后来发现这会触发抽取错误。

经过多轮对比，最终明确：

> SMCNR 当前可靠的版图验证路径是 MOS-only projection，也就是在进入 MAGICAL 前只保留 MOS 器件，暂时去掉电阻和电容等被动器件。

这个路径下：

- MAGICAL 更稳定
- Magic extraction 更容易保持网络正确
- Netgen LVS 更容易通过
- PEX 可以稳定产生寄生电容数据

相关文档：

- `docs/smcnr_variant_pipeline_equivalence_report.md`
- `docs/smcnr_variant_pipeline_native_equivalence_pass.md`
- `docs/smcnr_local_power_stripe_replay.md`
- `docs/smcnr_wl_mos_projection_sweep_0003.md`

结论：

- 后续 SMCNR 数据生产应优先采用 MOS-only projection 路径。
- 目前还不能声称完整包含电阻电容的 full passive LVS 已完全解决。

## 3. 样本扩展工作

### 3.1 手动 L 参数微扰

我们先从 `cand_0031` 出发，尝试只改一个 MOS 的沟道长度 L。

比较安全的扰动轴包括：

- `bias_pmos_l`
- `second_stage_pmos_l`
- `load_nmos_l`
- `second_stage_nmos_l`

结果：

- 8 个 L-only 变体全部 extraction clean，即 `equiv=0`
- 8 个 L-only 变体全部 LVS 通过
- 其中 PMOS L 变体能带来明显寄生结构变化
- NMOS L 变体主要带来寄生数值变化

这里的“寄生结构变化”指的是：

- 寄生电容数量变化，比如 37 个变成 36 个或 35 个
- 或者寄生电容连接关系变化

“寄生数值变化”指的是：

- 电容数量仍然相同
- 但总电容或某些节点电容数值发生变化

相关文档：

- `docs/smcnr_l_only_parasitic_candidates.md`
- `docs/smcnr_wl_0003_trust_review.md`

结论：

- PMOS L 是目前最有效、最可靠的寄生样本扩展方向。
- NMOS L 也有价值，但信息量相对弱一些。

### 3.2 受约束 Monte Carlo 微扰

在手动验证安全轴之后，我们进一步做了一个小规模 Monte Carlo 实验。

这里的 Monte Carlo 不是随便乱改参数，而是：

- 只在已经验证安全的 PMOS L 参数轴上做小扰动
- 扰动范围控制在约 ±1% 到 ±5%
- 每个候选都走完整检查链路：
  - MAGICAL
  - Magic extraction
  - 自动网名重命名
  - Netgen LVS
  - PEX

初始阶段曾出现 0/16 LVS 通过的问题。后来定位到不是版图错误，而是自动网名重命名脚本的正则表达式漏匹配。

旧正则只能匹配：

```text
a_1234_5678#
```

但匹配不了：

```text
a_2100_n30#
a_4345_n10#
```

修复后：

```python
a_\d+_[a-z]*\d+#
```

结果变为：

- 16/16 extraction clean
- 15/16 LVS PASS
- 1/16 因器件数量不匹配被拒收
- MAGICAL 在这批任务中没有崩溃

相关代码：

- `tools/analog_harness/ml/auto_lvs_rename_smcnr.py`

结论：

- SMCNR 的 PMOS L 轴已经形成了初步可用的数据生产线。
- 当前失败主要可以由信任门控筛掉，而不是阻断整个生产流程。

## 4. Dataset v0.1 当前成果

我们已经把数据整理为 Dataset v0.1。

目前数据集包含 15 条记录，分为四类：

### 4.1 已审查成功基线

1 条：

- `smcnr_se_2st_amp_cand_0031`

这是目前唯一可以称为完整成功基线的样本。

### 4.2 通过寄生检查的候选样本

8 条：

- 4 条手动 L-only PMOS 变体
- 4 条 Monte Carlo PMOS-L 变体

这些样本都满足：

- extraction clean
- LVS 通过
- PEX 可解析
- 能提供寄生参数变化

但它们还不能称为训练正样本，因为没有经过完整后仿、PVT 和最终人工审查。

### 4.3 失败样本

包括 Fan_SMC、DFCFC2、NMCNR 等。

这些样本虽然不能作为正样本训练，但可以作为失败案例库，用于研究：

- 哪些版图/抽取路径会失败
- substrate/well collapse 如何出现
- LVS mismatch 的常见类型

### 4.4 拒收样本

1 条：

- `mc_second_stage_pmos_1p05`

它在 Monte Carlo 中出现器件数量不匹配，不能进入寄生建模候选池。

相关文件：

- `tools/analog_harness/ml/parasitic_dataset.py`
- `generated/parasitic_modeling/dataset_v0.jsonl`
- `docs/parasitic_dataset_v0_1_card.md`

测试结果：

- `tools.analog_harness.tests.test_analoggym_importer`
- `tools.analog_harness.tests.test_parasitic_dataset`
- 共 24 个测试，全部通过。

## 5. 当前获得的核心成果

### 5.1 从单个成功样本变成了小型可信数据集

最开始我们只有一个成功样本 `cand_0031`。

现在我们有：

- 1 个已审查成功基线
- 8 个通过 LVS/PEX 的寄生建模候选
- 多个失败样本用于诊断和边界分析

这已经从“单点成功”进入“可扩展数据生产”的阶段。

### 5.2 找到了稳定的数据生产轴

目前最可靠的是：

```text
SMCNR PMOS L 参数微扰
```

也就是微调 PMOS 的沟道长度 L。

这条轴可以稳定产生寄生参数变化，尤其是：

- 电容数量变化
- 总电容变化
- 关键节点电容变化

### 5.3 建立了自动网名重命名工具

Magic 抽取出的内部节点经常是匿名名，例如：

```text
a_2100_n30#
```

这些节点需要映射回源网表里的逻辑网络名。我们已经修复并验证了自动重命名逻辑，使得批量 LVS 成为可能。

### 5.4 明确了当前边界

我们没有把结论说过头。目前不能声称：

- 所有 AnalogGym 电路都能跑通
- full passive LVS 已完全解决
- 新变体都是训练正样本
- 可以直接训练复杂 diffusion/Mamba 模型

目前能稳妥声称的是：

> 在 SMCNR 电路上，基于 MOS-only projection 和 PMOS L 微扰，我们已经建立了一条可以批量产生 LVS/PEX 通过的寄生建模候选样本生产线。

## 6. 下一步计划

### 6.1 继续稳固 Dataset v0.1

下一步建议先不要盲目扩到很大规模，而是先把 Dataset v0.1 的说明、字段、样本分类整理清楚。

需要继续完善：

- 每条样本的参数扰动来源
- LVS/PEX 证据路径
- 是否结构性寄生变化
- 是否仅数值变化
- 是否应作为候选样本、失败样本或拒收样本

### 6.2 形成 Monte Carlo 批量生产脚本

目前 Monte Carlo 已经证明可行。下一步可以把它整理成正式脚本：

输入：

- 基线 `cand_0031`
- 参数白名单，例如 `bias_pmos_l`、`second_stage_pmos_l`
- 扰动范围，例如 ±1% 到 ±5%
- seed 数量

输出：

- 每个候选的 layout / extraction / LVS / PEX 结果
- 自动重命名日志
- 通过/失败/拒收原因
- 可加入数据集的样本记录

### 6.3 做小规模 baseline 模型

在上复杂模型前，建议先做最小 baseline：

输入：

- 改了哪个参数
- 改动百分比
- 器件类型

输出：

- 总电容
- 电容数量
- 是否发生结构性寄生变化

可先尝试：

- 线性回归
- 随机森林
- 小 MLP

目的不是追求高精度，而是检查：

- 数据字段是否够用
- 数据格式是否稳定
- 寄生变化是否有可学习规律

### 6.4 再评估 diffusion / Mamba

我们检索了相关论文，发现寄生参数建模领域目前主流还是：

- GNN
- CNN
- MLP
- 随机森林

diffusion 或 Mamba 直接用于寄生电容网络建模的工作目前不多。因此建议：

1. 先用简单模型作为 baseline。
2. 确认数据链路和任务定义没问题。
3. 再考虑 diffusion 用于“寄生网络生成”，或者 Mamba 用于“PEX 网表序列建模”。

这样更稳，也更容易写成论文叙事。

## 7. 希望师兄重点帮忙分析的问题

希望师兄可以重点看以下几个问题：

1. `cand_0031` 的完整原始运行路径中，是否还有我们本地没记录到的关键环境变量或中间制品？
2. MOS-only projection 作为当前生产路径是否合理？是否有更好的方式逐步恢复电阻/电容的完整证据？
3. PMOS L 微扰作为数据扩展轴是否符合电路设计直觉？
4. 当前自动网名重命名逻辑是否足够稳健？是否需要更严格的连通性校验？
5. Dataset v0.1 的样本分层是否合理：
   - 已审查成功基线
   - 通过寄生检查的候选样本
   - 失败样本
   - 拒收样本
6. 下一阶段是否应该优先扩 SMCNR 样本，还是回头修复 DFCFC2 / Fan_SMC / NMCNR 的失败链路？

## 8. 一句话总结

从师兄上传 SMCNR 数据到现在，我们已经完成了从“验证一个成功样本”到“建立一条 SMCNR 寄生参数候选样本生产线”的转变。当前最可靠的数据扩展方向是 SMCNR 的 PMOS L 微扰；Dataset v0.1 已经具备 1 个完整成功基线、8 个通过 LVS/PEX 的寄生建模候选，以及一批失败/拒收样本用于诊断。下一步应先稳固数据集和生产脚本，再做小模型验证，最后再考虑 diffusion 或 Mamba 等更复杂模型。
