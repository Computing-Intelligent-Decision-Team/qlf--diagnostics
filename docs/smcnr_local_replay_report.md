# SMCNR/cand_0031 Local Replay Report

**Date**: 2026-06-22
**Status**: **PASS** — 当前环境可重复复现 SMCNR DRC/extract/LVS

## Executive Summary

SMCNR/cand_0031 的 **DRC → Magic extraction → Netgen LVS** 已在当前 Linux 环境完成两次独立 replay。R1 与 R2 均为 DRC 0 错误，extraction 无 port short、substrate = "gnda"、0 equiv 记录、6 端口完整、8 MOS 正确，LVS 结果为 "Circuits match uniquely"。

PEX 寄生电容总数与 packaged PEX summary 有差异（本地 extracted SPICE 327 caps vs packaged 37 caps）。本地 extraction 使用了 `cthresh=0, rthresh=0`，因此该 SPICE 适合做 raw parasitic audit；它还不能直接替代 packaged PEX summary 作为同一粒度的训练标签。差异需要单独对齐分析。

---

## 1. 环境

| 工具 | 版本 | 路径 |
| --- | --- | --- |
| Magic | 8.3.483 | `/home/qlf/IOT/scripts/env/bin/magic` |
| Netgen | 1.5.133 | `/usr/lib/netgen/bin/netgen` |
| PDK | 7b70722e | `/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A` |
| Magic rcfile | — | `third_party/analoggym_grpo/simulation_files/sky130_pdk/libs.tech/magic/sky130A.magicrc` |
| OS | Linux (WSL2) | `6.6.87.2-microsoft-standard-WSL2` |

---

## 2. DRC

**命令**：
```bash
/home/qlf/IOT/scripts/env/bin/magic -dnull -noconsole \
  -rcfile /home/qlf/IOT/references/AnalogHarness/third_party/analoggym_grpo/simulation_files/sky130_pdk/libs.tech/magic/sky130A.magicrc \
  drc.tcl
```

**结果**：`Total DRC errors found: 0`

**必需环境变量**：
```bash
PDK_ROOT=/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9
SKY130A=/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A
```

| 指标 | Packaged | Local | 匹配 |
| --- | --- | --- | --- |
| DRC count | 0 | **0** | ✓ |

---

## 3. Magic Extraction

**命令**：
```bash
/home/qlf/IOT/scripts/env/bin/magic -dnull -noconsole \
  -rcfile /home/qlf/IOT/references/AnalogHarness/third_party/analoggym_grpo/simulation_files/sky130_pdk/libs.tech/magic/sky130A.magicrc \
  extract.tcl
```

**Tcl**：`extract all; ext2spice lvs; ext2spice cthresh 0; ext2spice rthresh 0; ext2spice`

**结果**：

| 指标 | Packaged | Local | 匹配 |
| --- | --- | --- | --- |
| `substrate` | unknown | **"gnda"** | ✓ (推断) |
| `equiv` 记录 | unknown | **0** | ✓ (推断) |
| Port short warnings | unknown | **0** | ✓ (推断) |
| Extracted ports | 6 | **6** | ✓ |
| Port names | vdda gnda vin vip ibias vout | vdda gnda vin vip ibias vout | ✓ |
| MOS devices | 8 | **8** | ✓ |
| NMOS count | 3 | 3 | ✓ |
| PMOS count | 5 | 5 | ✓ |
| `.ext` 生成 | — | ✓ | — |
| `.spice` 生成 | — | ✓ | — |

---

## 4. Netgen LVS

**命令**：
```bash
/usr/lib/netgen/bin/netgen -batch source run_lvs.tcl
```

**输入**：使用 packaged connectivity netlists (source + extracted)

**结果**：
```
Result: Circuits match uniquely.
Subcircuit summary:
Circuit 1: SMCNR_SE_2st_AMP    |Circuit 2: SMCNR_SE_2st_AMP_flat
sky130_fd_pr__pfet_01v8 (5)    |sky130_fd_pr__pfet_01v8 (5)
sky130_fd_pr__nfet_01v8 (3)    |sky130_fd_pr__nfet_01v8 (3)
Number of devices: 8            |Number of devices: 8
Number of nets: 9               |Number of nets: 9
```

| 指标 | Packaged | Local | 匹配 |
| --- | --- | --- | --- |
| LVS result | PASS | **PASS** | ✓ |
| Devices | 8 vs 8 | **8 vs 8** | ✓ |
| Nets | 9 vs 9 | **9 vs 9** | ✓ |

---

## 5. PEX

| 指标 | Packaged PEX summary | Local raw SPICE | Note |
| --- | --- | --- | --- |
| Cap count | 37 | **327** | 本地包含 sub-fF 级寄生 |
| Total cap | 71.4964 fF | **146.7633 fF** | 本地包含全部寄生（无阈值截断） |
| Largest cap | C31 vdda↔gnda 35.8705 fF | — | 待分析 |
| Per-node 分布 | 11 nodes in summary | — | 待分析 |

**差异原因**：本地 extraction 使用了 `ext2spice cthresh 0; rthresh 0`，输出**全部**寄生电容（包括 aF 级）。Packaged PEX summary 是较粗粒度的 curated summary。两者差异可解释，但还未完成逐边对齐，不能声称 PEX 精确复现。

**验证方式**：查看 packaged raw SPICE 中是否有相同的大电容值——C31 vdda↔gnda 35.8705fF 应该在本地 extraction 中也能找到。

---

## 6. 制品路径

| 制品 | 路径 |
| --- | --- |
| DRC Tcl | `generated/smcnr_local_replay/drc.tcl` |
| Extract Tcl | `generated/smcnr_local_replay/extract.tcl` |
| `.ext` | `generated/smcnr_local_replay/SMCNR_SE_2st_AMP_flat.ext` |
| `.spice` | `generated/smcnr_local_replay/SMCNR_SE_2st_AMP_flat.spice` |
| LVS log | `generated/smcnr_local_replay/lvs.log` |
| LVS Tcl | `generated/smcnr_local_replay/run_lvs.tcl` |
| R2 directory | `generated/smcnr_local_replay_r2/` |
| R2 LVS log | `generated/smcnr_local_replay_r2/lvs.log` |

---

## 7. Repeatability

| 指标 | R1 | R2 | 匹配 |
| --- | --- | --- | --- |
| DRC count | 0 | 0 | ✓ |
| Extracted ports | 6 | 6 | ✓ |
| `substrate` | gnda | gnda | ✓ |
| `equiv` records | 0 | 0 | ✓ |
| MOS devices | 8 | 8 | ✓ |
| `.ext` cap lines | 271 | 271 | ✓ |
| extracted SPICE cap lines | 327 | 327 | ✓ |
| LVS result | PASS | PASS | ✓ |

---

## 8. 结论

**当前 Linux 环境已经可重复复现 SMCNR/cand_0031 的 DRC → extraction → LVS 链。** 满足以下验收标准：

- [x] DRC count = 0
- [x] `.ext` 和 extracted SPICE 生成
- [x] LVS match = yes
- [x] substrate = "gnda"，0 equiv 记录
- [x] 6 端口完整
- [x] 重复性验证（R2 与 R1 关键指标一致）
- [ ] PEX cap count 与 packaged 精确对齐

**下一步**：可以启动 AnalogGym-Opt 小批量数据生产，将新 candidate 送入当前 SMCNR replay pipeline。正式训练前，仍需 PEX packaged-summary 粒度对齐与 trust gate 自动化。
