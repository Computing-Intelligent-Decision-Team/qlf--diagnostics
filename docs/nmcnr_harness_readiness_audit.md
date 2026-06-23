# NMCNR Harness-Readiness Audit

**Date**: 2026-06-23
**Status**: **NOT ready for layout gate** — 3 blockers, 1 warning

## Executive Summary

`Leung_NMCNR_Pin_3` 的 NMCNR candidate 目前不能直接进入 AnalogHarness/MAGICAL layout gate。
MOS 器件被 MAGICAL DesignDB 识别（✅），但电流源、电阻、电容都是 SPICE primitive 形式，
不被 MAGICAL 识别为物理器件。此外 5-port 缺少显式 `ibias` 端口，bias 结构需要重新设计。

---

## 1. Evidence Basis

检查了以下源码：

| 文件 | 角色 |
|------|------|
| `flow/python/DesignDB.py` | MAGICAL 器件识别表（nmos_set, pmos_set, capacitor_set, resistor_set, pas_set） |
| `tools/sky130_adapter/run_sky130_case_pipeline.py` | Sky130 pipeline 入口 |
| `tools/sky130_adapter/convert_xschem_sky130_netlist.py` | Xschem→MAGICAL netlist 转换器 |
| `tools/analog_harness/configs/smcnr_se_2st_amp.yaml` | SMCNR working baseline 配置 |
| `tools/analog_harness/spice.py` | SPICE candidate compiler |
| `examples/smcnr_se_2st_amp_sky130_try/SMCNR_SE_2st_AMP_layout_physical_hspice.sp` | SMCNR working netlist |
| `examples/smcnr_se_2st_amp_sky130_try/smcnr_se_2st_amp.json` | SMCNR MAGICAL config JSON |
| `generated/analog_gym_import/circuit_leung_nmcnr/cand_baseline/source.spice` | NMCNR candidate netlist |

---

## 2. Device Support Matrix

### 2.1 MAGICAL DesignDB Recognized Device Sets

From `flow/python/DesignDB.py:12-18`:

```python
nmos_set = {"nmos", "nch", ..., "nch_mac", ..., "sky130_fd_pr__nfet_01v8"}
pmos_set = {"pmos", "pch", "pch_mac", ..., "sky130_fd_pr__pfet_01v8"}
capacitor_set = {"cfmom", "cfmom_2t"}
resistor_set = {"rppoly", "rppoly_m", "rppolywo_m", "rppolywo"}
pas_set = capacitor_set.union(resistor_set)
```

### 2.2 NMCNR Device-by-Device Assessment

| NMCNR Device | Count | MAGICAL Model | Status | Action Required |
|---|---|---|---|---|
| `xm0-xm11` (PMOS) | 12 | `sky130_fd_pr__pfet_01v8` | ✅ **Recognized** | None |
| `xm12-xm23` (NMOS) | 12 | `sky130_fd_pr__nfet_01v8` | ✅ **Recognized** | None |
| `I0 net013 GNDA 'CURRENT_0_BIAS'` | 1 | (none) | ❌ **No MAGICAL support** | Must redesign bias |
| `R0 net044 VOUT 'RESISTOR_0'` | 1 | (SPICE primitive) | ❌ **Not recognized** | Remap to `rppolywo_m` |
| `C0 net050 net044 'CAPACITOR_0'` | 1 | (SPICE primitive) | ❌ **Not recognized** | Remap to `cfmom_2t` |
| `C1 net044 net049 'CAPACITOR_1'` | 1 | (SPICE primitive) | ❌ **Not recognized** | Remap to `cfmom_2t` |

---

## 3. Blocker Details

### Blocker 1 (CRITICAL): Current Source I0 Has No Physical Layout

**Problem**: `I0 net013 GNDA 'CURRENT_0_BIAS'` is a SPICE simulation primitive. MAGICAL
generates physical layouts from recognized device types (MOSFET, resistor, capacitor).
There is no "current source" device in the Sky130 PDK that MAGICAL can instantiate.

**SMCNR reference**: The SMCNR working netlist has NO internal current source. Bias
current is supplied through the external `ibias` port, which MAGICAL routes as a pin.
The actual bias current comes from an off-chip or testbench current source.

```spice
* SMCNR (working): ibias is a PORT
.subckt SMCNR_SE_2st_AMP vdda gnda vin vip ibias vout
xm7 ibias ibias vdda vdda pch_mac ...  ← ibias connects directly to bias mirror

* NMCNR (our candidate): I0 is internal
.subckt leung_nmcnr_pin_3 gnda vdda vinn vinp vout
I0 net013 GNDA 'CURRENT_0_BIAS'          ← no physical layout
```

**Resolution options** (none implemented):
1. **Add explicit `ibias` port**: Remove I0, add `ibias` to port list, connect `ibias` to `net013`. Requires netlist topology change and testbench update.
2. **Replace I0 with resistor-based bias**: Use a poly resistor from vdda to net013. Simpler but less accurate (bias varies with vdda).
3. **Add MOS-based bias generator**: Add a diode-connected NMOS+resistor bias string. Adds ~3-4 devices. Most accurate but changes topology significantly.

### Blocker 2 (HIGH): Passives Are SPICE Primitives, Not MAGICAL Macros

**Problem**: R0, C0, C1 use SPICE primitive syntax (`R0`, `C0`), not MAGICAL macro
instantiations (`xr0 ... rppolywo_m`, `xc0 ... cfmom_2t`).

**Required mapping**:

```spice
# NMCNR current form (NOT recognized):
R0 net044 VOUT 'RESISTOR_0'
C0 net050 net044 'CAPACITOR_0'
C1 net044 net049 'CAPACITOR_1'

# Required MAGICAL form (for reference — SMCNR baseline):
xr0 net027 vout gnda rppolywo_m lr=4.0e-6 wr=400e-9 multi=1 m=1 series=31 segspace=250e-9
xc0 outn net027 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
```

**Parameter translation needed**:
- `RESISTOR_0=10k` → `rppolywo_m` with `lr`, `wr`, `series` (sheet rho ≈ 48 Ω/sq for rppolywo)
- `CAPACITOR_0=5pF`, `CAPACITOR_1=3pF` → `cfmom_2t` with `nr`, `lr`, `w`, `s` (unit cap ≈ 1 fF for cfmom)

The `probe_sky130_native_cap_gencell.py` utility exists but has not been run for NMCNR
passive sizing.

### Blocker 3 (HIGH): No Explicit `ibias` Port

**Problem**: NMCNR has 5 ports: `gnda vdda vinn vinp vout`. AnalogHarness SMCNR flow
expects 6 ports: `vdda gnda vin vip ibias vout`. The missing `ibias` port means:

1. MAGICAL config JSON has no `ibias` in its net name recognition
2. Post-layout testbench can't inject bias current externally
3. LVS netlist comparison will fail if source netlist adds ibias later

**Port mapping gap**:

| NMCNR (5-port) | SMCNR convention (6-port) |
|---|---|
| `gnda` | `gnda` |
| `vdda` | `vdda` |
| `vinn` | `vin` |
| `vinp` | `vip` |
| `vout` | `vout` |
| *(internal I0)* | `ibias` ← **missing** |

### Warning 1 (MEDIUM): Port Name and Order Convention

- NMCNR uses `vinn`/`vinp` (differential naming); SMCNR uses `vin`/`vip`
- NMCNR port order: `gnda vdda vinn vinp vout` (ground-first); SMCNR: `vdda gnda vin vip ibias vout` (power-first)
- These are surmountable with a rename wrapper but add complexity to the pipeline

---

## 4. Required Actions Before Layout Gate

### Minimal viable path (MOS-only projection)

If the goal is a **MOS-only LVS projection** (like SMCNR's initial `mos_only_projection` scope):

1. **Strip I0**: Remove the current source from the netlist
2. **Add ibias port**: Append `ibias` to port list, connect it to `net013`
3. **Strip R0, C0, C1**: Remove passives (they won't be in the layout)
4. **Rename ports**: `vinn→vin`, `vinp→vip`, reorder to `vdda gnda vin vip ibias vout`
5. **Create MAGICAL JSON**: `connectivityLvsProjection: "mos_only"`, supply net names, `lvsNetRenames`

This produces a 24-MOS netlist that MAGICAL can (potentially) place-and-route — pending
the Fan_SMC/DFCFC2 lessons about large-MOS-count substrate collapse.

### Full passive-inclusive path

Requires solving all three blockers:

1. Bias redesign (I0 → ibias port or bias generator)
2. Passive remap (R0→rppolywo_m, C0/C1→cfmom_2t with correct geometry params)
3. Port convention adapter

---

## 5. Current Trust Status (unchanged)

| Flag | Value |
|---|---|
| `trust_assigned` | `false` |
| `usable_for_supervised_positive_training` | `false` |
| `usable_for_parasitic_modeling` | `false` |
| `usable_only_as_failure_case` | `false` |
| `layout_gate_ready` | **`false`** |

---

## 6. Decisions Needed

Before proceeding to layout gate, Codex must decide:

1. **Scope**: MOS-only projection first, or full passive-inclusive?
2. **Bias strategy**: Add ibias port (changes netlist topology), keep I0 (blocked from MAGICAL), or redesign bias network?
3. **Risk tolerance**: 24 MOS is 3× SMCNR's 8 MOS. Fan_SMC (24 MOS) failed with substrate collapse. Is NMCNR likely to hit the same wall?

---

## 7. Forbidden Claims

- ❌ NMCNR is NOT ready for DRC/LVS/PEX
- ❌ DC convergence does NOT equal pre-sim pass
- ❌ MOS device recognition does NOT equal layout-ready
- ❌ The 5-port to 6-port gap is NOT resolved
