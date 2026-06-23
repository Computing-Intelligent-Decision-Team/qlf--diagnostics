# SMCNR Local Replay Readiness Audit

**Date**: 2026-06-22
**Scope**: Readiness assessment — no replay executed yet

## Current Judgment

当前环境**不能直接声称能稳定从零跑出 SMCNR 正样本**。更准确的分层：

| 能力 | 状态 | 证据 |
| --- | --- | --- |
| 审计 packaged cand_0031 | ✓ | `state.json`, `evidence.jsonl`, LVS/DRC/PEX 摘要 |
| 本地 Magic extraction（AH-SMC-023） | ✓ | `.ext`, `.spice`, extract log 已生成 |
| 本地 DRC 重跑 | **未验证** | `magic_drc.tcl` 存在但未在当前环境执行 |
| 本地 LVS 重跑 | **未验证** | Netgen 可用但未本地跑 SMCNR LVS |
| 本地 PEX summary 重生成 | **未验证** | 未和 packaged 37 caps / 71.5 fF 对齐 |
| 完整闭环（DRC→extract→LVS→PEX） | **未验证** | 未执行完整序列 |
| 重复性验证（2 次一致） | **未验证** | — |

---

## 1. 当前环境工具

| 工具 | 版本 | 路径 | Notes |
| --- | --- | --- | --- |
| Magic (system) | 8.3.105 | `/usr/bin/magic` | 不支持 sky130A |
| Magic (env) | **8.3.483** | `/home/qlf/IOT/scripts/env/bin/magic` | 支持 sky130A |
| Netgen | 1.5.133 | `/usr/lib/netgen/bin/netgen` | — |
| PDK | 7b70722e | `/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A` | tech + netgen setup 存在 |
| Magic RC | sky130A | `third_party/analoggym_grpo/.../sky130A.magicrc` | 需 PDK_ROOT 环境变量 |
| Docker | jayl940712/magical:latest | 可用 | MAGICAL P&R 已验证 |
| Python | 3.12.3 | 系统 | — |

---

## 2. SMCNR Packaged Artifacts 清单

### 存在

| 类型 | 路径 |
| --- | --- |
| GDS (pinned shapes) | `reproducibility/.../gds/SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds` |
| Case files | `.pin`, `.bound`, `.sp`, `.json`, `.gr`, `.iopin`, `.sym`, `.symnet` |
| Netgen LVS result | `best_candidate/cand_0031/layout/lvs_mos_projection/lvs_result_summary.md` (PASS) |
| PEX summary | `lvs_mos_projection/pex_summary.md` (37 caps, 71.5 fF) |
| Extracted SPICE (raw) | `lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.raw.spice` |
| Extracted SPICE (connectivity) | `lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.connectivity.spice` |
| Source connectivity | `lvs_mos_projection/SMCNR_SE_2st_AMP_source.connectivity.spice` |
| Magic DRC Tcl | `layout/magic_drc.tcl` |
| Magic Extract Tcl | `lvs_mos_projection/magic_extract.tcl` |
| LVS renames | `layout/lvs_renames.txt` (5 entries) |

### 缺失

| 类型 | Note |
| --- | --- |
| `.ext` 文件 | 不在 reproducibility package（package size reduction） |
| Magic extraction log | 不在 package |
| Netgen stdout log | 不在 package |
| MAGICAL route GDS | 不在 package（only post-remap GDS） |
| Magic DRC log | 不在 package |

---

## 3. AH-SMC-023 本地 Extraction vs Packaged

| 指标 | Packaged (cand_0031) | AH-SMC-023 Local | 一致？ |
| --- | --- | --- | --- |
| Magic 版本 | unknown (Windows) | 8.3.483 | unknown |
| `substrate` | unknown | `"gnda"` | — |
| `equiv` records | unknown | 0 | — |
| Extracted ports | 6 (vdda gnda vin vip ibias vout) | 6 | ✓ |
| MOS count | 8 | 8 | ✓ |
| NMOS body | gnda (3/3) | gnda (3/3) | ✓ |
| Parasitic caps | 37 | 未统计 | 需验证 |
| Total cap | 71.5 fF | 未计算 | 需验证 |

**AH-SMC-023 extraction 关键证据**：本地 Magic 8.3.483 从 packaged GDS 成功生成了 `.ext` 和 `.spice`，输出端口和 MOS 数量与 packaged 一致。但没有跑 DRC、LVS、PEX 对齐。

---

## 4. 最小 Replay 命令序列（建议，未执行）

```bash
# 环境变量
export PDK_ROOT=/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9
export MAGIC_RC=third_party/analoggym_grpo/simulation_files/sky130_pdk/libs.tech/magic/sky130A.magicrc
export MAGIC=/home/qlf/IOT/scripts/env/bin/magic
export NETGEN=/usr/lib/netgen/bin/netgen

# Step 1: DRC
cd smcnr_replay
cp ../reproducibility/.../gds/SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds .
$MAGIC -dnull -noconsole -rcfile $MAGIC_RC magic_drc.tcl 2>&1 | tee drc.log
# 验证: drc_count = 0

# Step 2: Extract
$MAGIC -dnull -noconsole -rcfile $MAGIC_RC magic_extract.tcl 2>&1 | tee extract.log
# 验证: .ext 存在，无 port short warning

# Step 3: LVS (使用 packaged connectivity netlists 或重新 prepare)
$NETGEN -batch source run_lvs.tcl 2>&1 | tee lvs.log
# 验证: lvs_match = yes, devices 8 vs 8, nets 9 vs 9

# Step 4: PEX verify
grep "^C" extracted.spice | wc -l
# 验证: ≈37 caps, total ≈71.5 fF

# Step 5: Repeat (Step 1-4) to verify reproducibility
```

---

## 5. 尚未解决的风险

1. **Magic 版本差异**：packaged run 使用 Windows Magic 8.3.483，当前本地使用 Linux Magic 8.3.105 + Magic 8.3.483 (env)。AH-SMC-023 验证了 8.3.483 (env) 可以生成正确的 `.ext`，但 DRC 未验证。

2. **Netgen setup 版本**：packaged run 使用 unknown PDK version 的 `sky130A_setup.tcl`。本地 PDK version = 7b70722e。可能产生不同的 LVS 结果。

3. **Magic DRC 配置**：`magic_drc.tcl` 存在于 package 中但 Tcl 脚本可能引用 Windows 路径。

4. **One-shot vs reproducible**：AH-SMC-023 只跑了一次 extraction。需要重复跑确认输出一致。

5. **PEX 数值精度**：Magic extraction 的寄生电容值可能有微小变化（网格精度、浮点误差），71.5 fF 可能需要 ±0.5 fF 的容差。

---

## 6. Recommendation

先跑一次最小 replay（仅 extraction），确认：

- 本地 `.ext` 和 AH-SMC-023 结果一致
- PEX cap count 和 total 在容差范围内

然后跑完整 DRC→extract→LVS 序列。

如果通过，再做第二次重复跑确认稳定。

**不要在没有 replay report 前启动 AnalogGym-Opt 数据生产。**
