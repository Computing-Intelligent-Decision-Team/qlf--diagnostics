# 寄生参数建模下一步计划与师兄协作请求

**日期**：2026-06-25
**项目**：AnalogHarness / SMCNR 寄生参数建模数据线
**目的**：说明当前已经完成的工作、为什么下一步不能只继续微扰 SMCNR、以及需要师兄协助提供哪些数据和判断。

## 1. 当前结论

我们已经把 SMCNR 的寄生参数数据生产线从“只有一个成功样本”推进到了一个可审计的小数据集。

目前最可靠的基线仍然是：

- `SMCNR_SE_2st_AMP/cand_0031`
- 它是唯一已经完整审查过的成功基线样本。
- 后续所有新样本都不能自动等同于这个基线样本。

在这个基线之上，我们验证了一条可用的样本扩展路径：

```text
cand_0031 参数
  -> 只微扰 PMOS 的沟道长度 L
  -> MOS-only 版图路径
  -> Magic DRC
  -> Magic extraction
  -> 自动 LVS 网名重命名
  -> Netgen LVS
  -> PEX 寄生电容解析
  -> 写入数据集
```

这里的 “MOS-only” 指的是：版图验证时只保留 MOS 器件，暂时不把电阻、电容等被动器件纳入完整 LVS。
所以这些新样本可以用于寄生建模候选池，但不能声称已经通过完整被动器件 LVS。

## 2. 已经获得的成果

### 2.1 Dataset v0.3

当前数据集版本是 `v0.3`，共 40 条记录：

| 类型 | 数量 | 含义 |
|------|------|------|
| 已审查成功基线 | 1 | `cand_0031`，唯一可以作为完整成功基线的样本 |
| PMOS-L 寄生候选样本 | 29 | 只改 PMOS 沟道长度 L，LVS/PEX 证据完整，可用于寄生建模候选池 |
| 失败样本 | 6 | Fan_SMC、DFCFC2、NMCNR、失败边界样本等，可用于失败分类 |
| NMOS-L 辅助样本 | 4 | 只改 NMOS 沟道长度 L，LVS 通过，但寄生变化较弱 |

相关文件：

- `docs/parasitic_dataset_v0_3_card.md`
- `generated/parasitic_modeling/dataset_v0_3.jsonl`
- `tools/analog_harness/ml/parasitic_dataset.py`

### 2.2 PMOS-L 微扰生产线

我们确认两个安全微扰轴：

- `bias_pmos_l`
- `second_stage_pmos_l`

可用倍率为：

```text
0.95, 0.96, 0.97, 0.98, 0.99,
1.005, 1.01, 1.015, 1.02, 1.025,
1.03, 1.04, 1.05
```

这意味着在当前 MAGICAL + Sky130 PDK 版本下，PMOS-L 空间的安全样本上限大约是：

```text
2 个参数轴 x 13 个倍率 = 26 个候选
```

这 26 个候选已经在 `mc_pmos_l_0002` 中跑完。
再细分到 0.0025 步长时，MAGICAL 会因为 PDK 网格约束崩溃，所以不能继续用更密的 L 微扰硬扩。

### 2.3 稳定性验证

我们选了三个参数点，每个点重复跑 3 个 seed：

- baseline
- `bias_pmos_l = 0.95`
- `second_stage_pmos_l = 1.03`

结果：

- 9/9 LVS PASS
- 同一参数点的 PEX 总电容方差为 0.0 fF
- 说明这条 PMOS-L 生产线在当前设置下是稳定的，不是偶然通过

相关文件：

- `docs/smcnr_pmos_l_seed_stability_0001.md`
- `generated/smcnr_variants/mc_pmos_l_seed_stability_0001/stability_results.json`

### 2.4 Runner 和自动重命名工具

我们修复了两个关键工程问题：

1. 自动 LVS 重命名脚本漏匹配匿名节点名
   例如 `a_2100_n30#` 这种带字母的节点。现在已修复。

2. Monte Carlo runner 的 DRC 计数字段以前会出现 `None`
   现在已经能从 Magic 输出里解析 DRC count，并且规定：
   - `DRC=0` 才能继续进入 LVS/PEX
   - DRC 未知或非零都必须拒收

相关文件：

- `tools/analog_harness/ml/auto_lvs_rename_smcnr.py`
- `tools/analog_harness/ml/smcnr_pmos_l_mc_runner.py`
- `docs/smcnr_mc_runner_drc_count_fix.md`

## 3. 为什么现在不能直接做 diffusion / Mamba

现在的数据还不适合直接训练 diffusion 或 Mamba 这类模型。

原因很简单：

1. 样本量太小
   目前真正干净、可用于寄生建模的 SMCNR 周边样本只有几十条。
   diffusion 这类生成模型通常需要大量样本，否则很容易只记住样本，而不是学到规律。

2. 样本集中在一个拓扑附近
   当前数据主要来自同一个 SMCNR 电路，只是微调部分 MOS 的 L。
   这对验证数据链路很有价值，但不能代表多种模拟电路。

3. 寄生参数和拓扑强耦合
   寄生电容不只由 W/L 决定，还和这些因素有关：
   - 器件之间怎么连接
   - 哪些节点是高阻节点、输出节点、电源节点
   - 版图中器件的相对位置
   - 金属走线长度、层次、邻近关系
   - well/substrate/tap 结构

所以，只靠一个 SMCNR 最优点周围的几十个扰动样本，不能训练出可以泛化到其他电路的寄生预测模型。

当前数据更适合做三件事：

- 验证数据生产线是否可靠
- 验证样本证据格式和信任门控是否正确
- 做非常小规模的基线模型或特征分析

## 4. 下一步主线目标

下一步不应该继续强行在 SMCNR 上无限微扰。
更合理的主线是：

```text
从单个 SMCNR 点扩展到多候选、多拓扑的数据来源。
```

也就是说，我们需要从 AnalogGym / AnalogGym-Opt 或师兄历史运行结果中拿到更多候选解，而不是只围绕一个最优点手工改参数。

## 5. 我们下一步会做什么

### Step 1：冻结 Dataset v0.3

目标：

- 把当前 40 条记录作为一个明确版本保存下来。
- 明确哪些样本可以用于寄生建模候选池，哪些只能作为失败样本。
- 保持 `cand_0031` 是唯一完整成功基线。

验收标准：

- `docs/parasitic_dataset_v0_3_card.md` 存在且字段完整。
- `generated/parasitic_modeling/dataset_v0_3.jsonl` 可重新生成。
- 单元测试通过。

### Step 2：向师兄索要候选历史数据

目标：

从师兄已有的 AnalogGym / AnalogGym-Opt 运行中拿到“候选解历史”，而不是只拿最终最优解。

理想情况下，每个候选需要包含：

- 电路名 / 拓扑名
- sizing 参数
- 前仿指标
- reward 或 score
- 随机 seed
- generation / step 编号
- 原始 netlist 或可重建 netlist 的参数文件
- 是否曾经通过 layout / LVS / PEX / post-sim
- 对应日志或 artifact 路径

我们拿到这些以后，会逐个候选重新走 AnalogHarness 的信任门控，不会直接相信旧结果。

### Step 3：优先挑第二个简单拓扑

目标：

找一个比 Fan_SMC / DFCFC2 / NMCNR 更容易闭环的第二个电路。

优先条件：

- MOS 数量不要太大，最好先在 8 到 12 MOS 左右
- 被动器件少，或者可以先做 MOS-only projection
- 有 testbench
- 有多个 sizing 候选
- 能在 Magic extraction 下保持 `equiv=0`

这一步的目标不是马上做很大的模型，而是验证：

```text
同一套数据管线能不能从 SMCNR 迁移到第二个电路。
```

### Step 4：建立小模型基线

在数据量达到几十到几百条之后，先不要直接上 diffusion。
建议先做更小的基线模型：

- 线性模型 / 随机森林：预测总电容或关键节点电容
- 图特征统计：节点度数、器件类型、W/L、网络角色
- 小型图神经网络：只做回归，不做生成

这样可以先确认数据里是否真的存在可学习信号。

### Step 5：再考虑 diffusion / Mamba

只有当我们具备以下条件时，才建议进入 diffusion / Mamba：

- 至少数百条干净样本
- 最好跨多个拓扑
- 每条样本都有明确的版图、LVS、PEX 证据
- 有统一的图表示和训练/验证划分
- 能证明简单模型已经遇到瓶颈

否则 diffusion 很容易变成“模型很复杂，但数据不够”的空转。

## 6. 需要师兄协助什么

### 6.1 提供候选解历史，而不是只提供 best candidate

最需要的是：

```text
AnalogGym / AnalogGym-Opt 每轮搜索产生过哪些候选？
```

如果有 JSON、CSV、pickle、日志目录、checkpoint 或数据库都可以。
我们可以适配格式，但需要能还原每个候选的参数和来源。

### 6.2 提供 SMCNR 成功路径的原始运行信息

如果师兄本地还有原始运行目录，希望能提供：

- MAGICAL 输入 netlist
- MAGICAL config
- GDS
- extraction log
- LVS log
- PEX netlist
- 运行脚本
- 环境版本

这有助于我们继续确认为什么 `cand_0031` 是成功样本，以及哪些路径可以稳定复现。

### 6.3 推荐一个第二拓扑

希望师兄帮忙判断：AnalogGym 里哪个电路最适合作为第二个闭环目标。

我们目前不建议直接硬啃：

- Fan_SMC：已有 substrate/well 相关失败
- DFCFC2：MIM 电容映射和 substrate 问题都比较重
- NMCNR：24 MOS 后出现复杂 LVS 问题

更希望先找一个更简单、更接近 SMCNR 复杂度的拓扑。

### 6.4 确认是否有更多 SMCNR 附近的真实候选

如果师兄以前跑过 SMCNR 的多组 sizing，而不是只有 `cand_0031`，这些数据非常有价值。
我们可以把它们逐个送入当前生产线，验证是否能产生更多寄生样本。

## 7. 不应声称的内容

为了避免误解，当前阶段不能声称：

- 已经可以训练 diffusion 模型。
- 当前样本已经足够支持跨电路泛化。
- 新生成样本是完整训练正样本。
- MOS-only LVS 等价于 full passive-inclusive LVS。
- SMCNR 的结论可以直接推广到 Fan_SMC、DFCFC2、NMCNR。

当前可以稳妥声称的是：

- `cand_0031` 是唯一完整审查过的成功基线。
- SMCNR 的 PMOS-L 微扰路径可以稳定产生寄生建模候选样本。
- Dataset v0.3 已经形成一个可审计的小规模寄生数据集。
- 下一步需要从候选历史和第二拓扑扩展数据来源。

## 8. 建议给师兄的请求摘要

可以直接向师兄请求：

```text
我们已经把 SMCNR/cand_0031 周边的 PMOS-L 微扰数据线跑通，
Dataset v0.3 有 40 条记录，其中 cand_0031 仍是唯一完整成功基线。

现在最大瓶颈不是 runner，而是数据来源太少、拓扑太单一。
为了继续做寄生参数建模，希望师兄提供 AnalogGym / AnalogGym-Opt
的候选解历史，而不仅是 best candidate。

每个候选最好包含：拓扑名、sizing 参数、前仿指标、reward/score、
seed、step 编号、netlist 或可重建配置、以及对应的 layout/LVS/PEX
日志或 artifact。

我们会用 AnalogHarness 重新跑 DRC/extraction/LVS/PEX 和信任门控，
不会直接把旧结果当成通过样本。

同时希望师兄推荐一个复杂度接近 SMCNR、被动器件较少、有 testbench
的第二拓扑，用来验证这条数据生产线能否从 SMCNR 迁移到其他电路。
```
