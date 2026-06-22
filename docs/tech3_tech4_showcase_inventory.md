# Tech3/Tech4 Showcase Inventory

> Generated: 2026-06-21 | Scope: AnalogHarness local GDS + screenshots
> Follows: AGENTS.md, smcnr_positive_baseline_contract.md, codex_ah_smc_009_review.md

## 1. Fan_SMC GDS Stage Inventory

All paths under `generated/diagnostics/fan_smc_c0_proxy_94x10/`.

| Stage | File | Size (KB) | SHA256 (first 16) | Top Cell | Bbox (µm) | Layers | What it shows |
|-------|------|-----------|-------------------|----------|-----------|--------|---------------|
| init | `case/fan_smc_pin_3_init.gds` | 1,553 | 4f4c3c96… | INTERCONNECTION | 36410×68010 | 29 | Full MAGICAL internal representation; all device geometry, internal layers, interconnections visible |
| floorplan | `case/fan_smc_pin_3.floorplan.gds` | 123 | 4a809a56… | FLOORPLAN | 15600×27800 | 2 | Bare frame — only boundary and device-region outlines; no devices placed yet |
| place | `case/fan_smc_pin_3.place.gds` | 327 | 76884f3a… | fan_smc_pin_3 | 18025×33875 | 29 | Devices placed into the floorplan region; transistor blocks visible with orientation |
| route | `case/fan_smc_pin_3.route.gds` | 352 | ea8935c7… | fan_smc_pin_3_flat | 18025×33875 | 31 | Routing added on top of placement; metal traces connecting device terminals |
| sky130 | `fan_smc_pin_3.sky130.gds` | 352 | 0522c31d… | fan_smc_pin_3_flat | 18025×33875 | 31 | MAGICAL internal layers remapped to Sky130 layer/datatype pairs |
| pinned_shapes | `fan_smc_pin_3.pinned_shapes.gds` | 352 | fe4a159b… | fan_smc_pin_3_flat | 18025×33875 | 37 | Pin labels + pin shapes added; ready for Magic DRC ingestion |

### Additional Fan_SMC diagnostic variant

| File | Path | Size (KB) | What it shows |
|------|------|-----------|---------------|
| psub_tap diagnostic | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds` | — | AH-SMC-009: single p+ substrate tap added to gnda rail; DRC=0 but extraction still collapses vout/vdda/gnda |

### Fan_SMC Claim Boundaries

| May claim | May NOT claim |
|-----------|---------------|
| 6-stage layout generation pipeline from SPICE to pinned_shapes GDS | LVS match (fails: devices/nets mismatch) |
| DRC 0 errors on pinned_shapes and psub_tap | Post-layout simulation pass |
| PEX available (112 caps, 29.4 fF) | PVT corner pass |
| AH-SMC-009: diagnostic tap repair attempted | Fan_SMC closed-loop success |
| Trust gate correctly blocks unsafe samples | Fan_SMC usable for training/reward |
| | Fan_SMC positive baseline |

---

## 2. SMCNR/cand_0031 GDS Inventory

All paths under `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/gds/`.

| File | Size (KB) | SHA256 (first 16) | Top Cell | Bbox (µm) | Layers | What it shows |
|------|-----------|-------------------|----------|-----------|--------|---------------|
| `SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds` | 523 | e40d1d65… | SMCNR_SE_2st_AMP_flat | 73825×41050 | 34 | Final verified layout; DRC=0, LVS=yes, post-sim=pass, PVT=3/3 |
| `SMCNR_SE_2st_AMP.sky130.pinned_shapes.local_power.gds` | 431 | e7f828a5… | SMCNR_SE_2st_AMP_flat | 36775×41050 | 32 | Power-aware derivative; narrower bbox from local power grid extraction |
| `native_cap_replaced.gds` | 490 | b4a6b449… | SMCNR_SE_2st_AMP_flat | 73825×41050 | 32 | Native passive replacement: 31-device resistor chain + MIM cap, Netgen pass |

### SMCNR Positive Baseline Status

Per `smcnr_positive_baseline_contract.md`:

| Gate | Status |
|------|--------|
| Pre-layout simulation | pass |
| DRC | 0 errors |
| LVS | match |
| PEX | available |
| Post-layout simulation | pass |
| PVT | 3/3 corners pass |
| Passive scope | `full_passive_inclusive_gds_lvs` |
| Trust: usable_for_training | true |
| Trust: usable_for_reward | true |

### SMCNR Claim Boundaries

| May claim | May NOT claim |
|-----------|---------------|
| cand_0031 is the reviewed positive baseline | SMCNR positive status applies to Fan_SMC or DFCFC2 |
| Full EvidencePacket chain from pre-sim through PVT | The reproducibility package is a full original run tree (30 paths are non-portable, 28 are generated-only) |
| Backfilled passive evidence with provenance noted | Original passive probe passed without backfill |
| DRC/LVS/PEX/post-sim/PVT independently verified | MAGICAL repairs generalize to other circuits |

---

## 3. Screenshot Asset Checklist

All screenshots exist and are non-empty.

### Fan_SMC (`docs/assets/tech3_tech4/fan_smc/`)

| File | Size (KB) | Status |
|------|-----------|--------|
| `01_floorplan.png` | 37 | ✅ ready for PPT |
| `02_place.png` | 69 | ✅ ready for PPT |
| `03_route.png` | 108 | ✅ ready for PPT |
| `04_sky130.png` | 107 | ✅ ready for PPT |
| `05_pinned_shapes.png` | 108 | ✅ ready for PPT |
| `06_psub_tap_diagnostic.png` | 107 | ✅ ready for PPT |

### SMCNR (`docs/assets/tech3_tech4/smcnr/`)

| File | Size (KB) | Status |
|------|-----------|--------|
| `01_pinned_shapes.png` | 75 | ✅ ready for PPT |
| `02_local_power.png` | 96 | ✅ ready for PPT |
| `03_native_cap_replaced.png` | 81 | ✅ ready for PPT |

---

## 4. Recommended PPT Slide Placements

### Tech3: 约束驱动的版图自动生成

| Slide position | Asset | 1-sentence explanation (for non-experts) |
|----------------|-------|------------------------------------------|
| Left (video) | Terminal: `tech3_layout_generation/run_demo.py` | Pipeline replay showing each stage completing |
| Right top-left | `01_floorplan.png` | "先画一个框——自动规划器件放在哪" |
| Right top-right | `02_place.png` | "把晶体管一个一个摆进去" |
| Right mid-left | `03_route.png` | "自动把线连上——金属走线全部生成" |
| Right mid-right | `04_sky130.png` | "换成真实工艺的颜色——Sky130 层映射" |
| Right bottom | `05_pinned_shapes.png` | "加上端口标签——可以拿去检查了" |
| Caption | — | "从 SPICE 网表到可验证 GDS，五步全自动" |

### Tech4: 验证诊断与反馈闭环

| Slide position | Asset | 1-sentence explanation (for non-experts) |
|----------------|-------|------------------------------------------|
| Left (video) | DRC log / trust_decision replay | Shows verification finding issues and blocking unsafe samples |
| Right top | `05_pinned_shapes.png` (Fan_SMC) | "版图生成后进入物理验证——发现衬底短路问题" |
| Right mid-left | `06_psub_tap_diagnostic.png` | "尝试修复：加一个衬底接触——DRC 还是零，但问题没解决" |
| Right mid-right | trust_decision.json | "系统判定：不可信，拦截——不让错误数据进入训练" |
| Right bottom | `01_pinned_shapes.png` (SMCNR) | "对比正向基线：同一个流程，正确电路全部通过" |
| Caption | — | "生成→验证→诊断→拦截，四步闭环。好的放行，坏的拦住" |

---

## 5. Trust Decision Summary

| Circuit | DRC | LVS | PEX | usable_for_training | usable_only_as_failure_case |
|---------|-----|-----|-----|---------------------|----------------------------|
| Fan_SMC (c0_proxy_94x10) | 0 errors | FAIL | available | false | true |
| Fan_SMC (psub_tap) | 0 errors | FAIL | — | false | true |
| SMCNR (cand_0031) | 0 errors | PASS | available | true | false |

**Key distinction**: DRC=0 does not mean the layout is correct. SMCNR passed LVS, post-sim, and PVT. Fan_SMC passed none of those. Both are useful for the PPT — Fan_SMC demonstrates the diagnostic/repair loop (Tech4), SMCNR demonstrates what success looks like.

---

## 6. Files Modified / Created

| Action | File |
|--------|------|
| **Created** | `docs/tech3_tech4_showcase_inventory.md` |
| **Read only** | All other files (no modifications to controller, reward, GRPO, closure, MAGICAL- artifacts) |
| **Not modified** | `reproducibility/`, `generated/`, `tools/`, `flow/`, `examples/` |

Git status: no commits, no pushes.
