# Fan_SMC & DFCFC2 Diagnostic Closure

## Status

**Fan_SMC_Pin_3**: 诊断已收束。当前 MAGICAL -> Sky130 remap -> Magic extraction 链上的可复现失败案例。
**DFCFC2 (AMP_DFCFC2)**: 暂停主动修复。它呈现出与 Fan_SMC 相似的 substrate/equiv collapse 症状，并叠加 MIM cap 映射问题。

两条电路均暂停主动修复，转为 failure-case 参考样本。主线回到
SMCNR/cand_0031 这个已审核正样本基线。

---

## 1. 电路对比

| 属性 | SMCNR/cand_0031 (PASS) | Fan_SMC (FAIL) | DFCFC2 (FAIL) |
| --- | --- | --- | --- |
| NMOS | 3 | 12 | 13 |
| PMOS | 5 | 12 | 13 |
| 电容 | 1 (cfmom_2t) | 1 (cfmom_2t, C0) | 2 (cap_mim_m3_1) |
| diff.drawing shapes | 56 | 128 | 26 |
| NMOS .pin 第4端 | -1 | -1 | -1 |
| `.ext` substrate | **"gnda"** | "vout" | "vout" |
| `.ext` equiv | **0 条** | 2 条 | 2 条 |
| 提取端口 | 6/6 | 3/5 | 4/6 |
| LVS | **PASS** | FAIL | FAIL |

**关键结论**：`.pin=-1` 不是单一根因。SMCNR 也有 -1 但通过；Fan_SMC 的失败更接近 layout/extraction 组合问题：较大规模、多指展开、diffusion domain 分布和当前 Magic extraction 规则共同导致 extracted connectivity 被重构。

---

## 2. Fan_SMC 诊断历程（AH-SMC-001 ~ 025）

### 已排除的假设

| 假设 | 验证实验 | 结论 |
| --- | --- | --- |
| 加顶层 p+ tap 能修 | AH-SMC-009 | 无效 |
| NMOS .pin=-1 是单一根因 | AH-SMC-016A | **被 SMCNR 对比证伪** |
| 手画 GDS body contact | AH-SMC-011 | 被 met5 污染（AH-SMC-012） |
| 外部改 .pin 让 MAGICAL 重路由 | AH-SMC-013/013R | **被阻断**（MAGICAL 覆盖 .pin） |
| Netgen rename/setup 差异 | AH-SMC-016C | **降级**（collapse 下 rename 不可能） |
| 底部 psub stripe 是根因 | AH-SMC-018-B | 无效 |
| M22/M23/M20 path diff mask | AH-SMC-018-C | 破坏 5 MOS，equiv 不变 |
| 17 个 non-device diff mask | AH-SMC-020 | 删除/remap 均无效 |
| `useDeviceSubGuardRing` | AH-SMC-021 | 改变 extraction 但不消除 collapse |
| 3 端 LVS（忽略 body） | AH-SMC-025 | 无效——拓扑已被重构 |

### 已确认的根因

| 发现 | 实验 | 置信度 |
| --- | --- | --- |
| MAGICAL OD 层统一 remap 到 diff.drawing | AH-SMC-019 | 高 |
| diffusion 相关几何是 merge 的强相关因素 | AH-SMC-017 | 高 |
| collapse 是 port-level、device-global | AH-SMC-024 | 高 |
| 拓扑重构超出 body 端子 | AH-SMC-025 | 高 |
| 电路规模是 SMCNR/Fan_SMC 的分水岭 | AH-SMC-022/023 | 中 |

### 结构性限制

```text
在当前 MAGICAL -> Sky130 remap -> Magic extraction 设置下，
Fan_SMC 的 extracted `.ext` 会产生 substrate/equiv 记录，
并把 vout/vdda/gnda 相关连通关系折叠到同一组等价关系中。

这不是一个简单的 Netgen rename 或 body-pin stripping 问题。
现有证据显示，问题发生在 Magic extraction 形成 extracted
connectivity 的阶段；到 Netgen LVS 时，源网表和提取网表拓扑
已经不是同一个可一一对应的结构。
```

---

## 3. DFCFC2 诊断摘要

DFCFC2 和 Fan_SMC 呈现出相似的 substrate/equiv collapse 症状：

```text
substrate "vout"
equiv "vout" "vdda"
equiv "vout" "gnda"
```

**额外问题**：
1. device count 翻倍（26→52，multi-finger 被 Magic 拆成独立 fingers）
2. MIM cap 映射不支持（`cap_mim_m3_1` ×2）
3. `ib`（bias 端口）也被拖入 psub collapse

虽然 diff.drawing 数量少于 Fan_SMC，但当前 artifacts 仍显示 substrate/equiv collapse。DFCFC2 暂时不再作为正向 closure 目标，而是保留为复杂压力测试样本。

---

## 4. 最终 Trust Decision

### Fan_SMC_Pin_3

```json
{
  "drc_clean": true,
  "lvs_match": false,
  "pex_available": true,
  "post_sim_valid": false,
  "pvt_valid": false,
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": true,
  "usable_only_as_failure_case": true,
  "failure_category": "substrate_collapse",
  "failure_detail": "Magic extraction produces equiv vout-vdda and equiv vout-gnda records; extracted netlist topology is restructured",
  "structural_limitation": "Current MAGICAL-to-Sky130 remap and Magic extraction setup does not preserve a training-safe Fan_SMC extracted topology"
}
```

### DFCFC2

```json
{
  "drc_clean": true,
  "lvs_match": false,
  "pex_available": true,
  "post_sim_valid": false,
  "pvt_valid": false,
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": true,
  "usable_only_as_failure_case": true,
  "failure_category": "substrate_collapse_with_mim_cap_mapping_gap",
  "failure_detail": "Similar substrate/equiv collapse symptoms to Fan_SMC; additional device count mismatch from multi-finger split; 2 cap_mim_m3_1 instances are not supported by current remap"
}
```

---

## 5. 经验总结

### 什么有效

1. **跨电路对比（SMCNR vs Fan_SMC）是最有效的诊断手段**——直接证伪了 `.pin=-1` 单独根因
2. **`psub_substrate_geometry.json`** 一次性定位了 diffusion 的主导作用（with-diff / without-diff 对比）
3. **Docker MAGICAL rerun** 可以复现，`.pin` 修改会被覆盖但 .json 参数修改（`useDeviceSubGuardRing`）可以生效
4. **GDS layer provenance audit**（AH-SMC-019）揭示了 remap aliasing 问题
5. **`.ext` substrate graph trace**（AH-SMC-024）精确定位了 collapse 的拓扑结构

### 什么无效

1. **局部 diffusion mask**——60 个 shape 改了，collapse 纹丝不动
2. **外部 .pin 编辑**——MAGICAL 会覆盖
3. **3 端 LVS**——拓扑已经被重构，body stripping 不够

### 什么时候应该回到 Fan_SMC

1. 前端生成新的 layout-friendly candidate（nf 更小、multi 更小）
2. MAGICAL primitive 层加入了 NMOS body contact 生成
3. Magic extraction model 被配置为区分 substrate domain

### 下一步

- **主线**：SMCNR/cand_0031 作为已审核正样本基线维护
- **负样本**：Fan_SMC / DFCFC2 作为 trust-gate 压力测试
- **前端**：如果重新跑 AnalogGym GRPO，新 candidate 可以直接跑现有 diagnostic pipeline
