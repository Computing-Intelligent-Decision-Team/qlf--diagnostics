# SMCNR 只改 L 的寄生候选审查

**日期**：2026-06-24  
**范围**：MOS-only projection（只保留 MOS 器件、去掉电阻电容）路径；从
`SMCNR_SE_2st_AMP/cand_0031` 做只改沟道长度 L 的微扰。

## 1. 当前判断

前两步已经完成：

1. `l_008_second_stage_pmos_l_p5` 已重新做 LVS（版图和原理图一致性检查）。
   把抽取网表里的匿名节点 `a_1385_3366#` 映射回 `ibias` 后，Netgen 报告
   8 对 8 器件、9 对 9 网络，并且唯一匹配。
2. 8 个只改 L 的候选都已经和 `var_ref_001` 基线做了 PEX（寄生参数提取）
   签名对比。

目前最有价值的是 PMOS 的 L 微扰。它们不只是让电容数值变化，还会改变寄生
电容图的结构，比如电容数量从 37 变成 36 或 35。

没有任何新候选被升级为 training-positive（训练正样本）。

## 2. 证据依据

基线：

| 基线 | LVS | 电容数量 | 总电容 |
|------|-----|----------|--------|
| `var_ref_001` | PASS | 37 | 80.945475 fF |

审计制品：

- `generated/smcnr_variants/l_only_sweep/cap_signature_audit_0001.json`

`l_008` 的 LVS 修复制品：

- `generated/smcnr_variants/l_only_sweep/l_008_second_stage_pmos_l_p5/lvs_ext_mos_renamed.spice`
- `generated/smcnr_variants/l_only_sweep/l_008_second_stage_pmos_l_p5/lvs_renamed.log`

`l_008` 原来的问题不是器件数量错，而是抽取网表把一个本该属于 `ibias`
的 PMOS 源/漏节点拆成了匿名节点 `a_1385_3366#`。映射回 `ibias` 后结果为：

```text
Number of devices: 8 | Number of devices: 8
Number of nets:    9 | Number of nets:    9
Circuits match uniquely.
Netlists match uniquely.
```

## 3. 候选汇总

| 候选 | 改动 | equiv | LVS 状态 | 电容数量 | 总电容变化 | vout 电容变化 | 当前分类 |
|------|------|-------|----------|----------|------------|----------------|----------|
| `l_001_bias_pmos_l_m5` | `bias_pmos_l -5%` | 0 | PASS（同 `wl_005`） | 36 | -0.697142 fF | +0.030455 fF | structural-diverse ✅ |
| `l_002_bias_pmos_l_p5` | `bias_pmos_l +5%` | 0 | PASS | 36 | +1.101577 fF | -0.033155 fF | structural-diverse ✅ |
| `l_003_load_nmos_l_m5` | `load_nmos_l -5%` | 0 | PASS | 37 | -0.328164 fF | 0.000000 fF | marginal_numeric |
| `l_004_load_nmos_l_p5` | `load_nmos_l +5%` | 0 | PASS | 37 | +0.361488 fF | 0.000000 fF | marginal_numeric |
| `l_005_second_stage_nmos_l_m5` | `second_stage_nmos_l -5%` | 0 | PASS | 37 | -0.225421 fF | +0.000466 fF | marginal_numeric |
| `l_006_second_stage_nmos_l_p5` | `second_stage_nmos_l +5%` | 0 | PASS | 37 | +0.327391 fF | -0.014964 fF | marginal_numeric |
| `l_007_second_stage_pmos_l_m5` | `second_stage_pmos_l -5%` | 0 | PASS | 36 | -0.277779 fF | -0.001552 fF | structural-diverse ✅ |
| `l_008_second_stage_pmos_l_p5` | `second_stage_pmos_l +5%` | 0 | PASS（`a_1385_3366#→ibias`） | 35 | -2.015368 fF | -0.946147 fF | structural-diverse ✅ |

## 4. 解释

PMOS 的 L 微扰更适合优先进入寄生建模候选池：

- `bias_pmos_l +5%` 让总电容增加约 1.10 fF，并且 LVS 干净通过。
- `second_stage_pmos_l -5%` 让电容数量从 37 变成 36，并且 LVS 干净通过。
- `second_stage_pmos_l +5%` 让电容数量从 37 变成 35；补上一条抽取节点
  重命名后，LVS 也通过。

NMOS 的 L 微扰也不是完全没用。它们的电容数量仍是 37，但总电容变化约
0.23 到 0.36 fF。四个 NMOS-L 候选已全部通过 LVS，标记为 `marginal_numeric_diversity`。

## 5. 数据集状态

经过 8/8 LVS PASS，当前 verified parasitic samples 计数：

```text
verified parasitic samples = 5
  = 1 baseline (cand_0031, reviewed positive)
  + 4 PMOS-L structural-diverse variants (candidate_for_parasitic_modeling_review)
  + 4 NMOS-L marginal_numeric_diversity (补充数据点)
```

所有新样本均标注：
- `trust_assigned=false`
- `usable_for_supervised_positive_training=false`
- `evidence_scope=mos_only_projection`

## 6. 验收标准

一个候选进入寄生建模审查池，需要同时满足：

- `equiv=0`
- 6 个端口都保留：`vdda gnda vin vip ibias vout`
- MOS 数量仍是 8
- LVS 报告 `Netlists match uniquely`
- PEX 能解析出非零电容数量
- 候选来源清楚：只从 `cand_0031` 改了一个 L 参数

## 7. 不允许声称的边界

- 不能把任何只改 L 的候选称为 reviewed positive training sample（已审查训练正样本）。
- 不能声称这里证明了 passive-inclusive LVS（包含电阻电容的完整 LVS）。
- 不能把“有 PEX”直接等同于“可以用于训练”或“可以用于后仿”。
- 不能在 NMOS L 候选的重命名 LVS 通过前，声称它们 LVS-clean（LVS 干净通过）。
