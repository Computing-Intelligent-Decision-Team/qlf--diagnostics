# AnalogGym Source Audit

**Date**: 2026-06-23
**Status**: Complete — source mapping, no training run

## Executive Summary

本地 AnalogGym 副本包含 18 个放大器 SPICE netlist（14 个 sky130 + 4 个 TSMC180/其他）、1 个 sky130 PDK（含 ngspice corner 模型）、14 个 RGNN RL 环境、和 1 个预训练 agent checkpoint（仅 NMCF）。SMCNR 在 AnalogGym 中有三个不同的形态，**没有一个直接等于 AnalogHarness 的 SMCNR/cand_0031**。它们需要通过 artifact mapping 建立关系后才能作为 candidate source。

**来源**：https://github.com/Computing-Intelligent-Decision-Team/AnalogGym
**本地副本**：`/home/qlf/IOT/Others'Projects/Analog/AnalogGym-main—LJT/AnalogGym-main`

---

## 1. Repository Structure

```
AnalogGym-main/
├── AnalogGym/
│   ├── Amplifier/
│   │   ├── spice_netlist/         18 files (one per topology)
│   │   ├── spectre_netlist/       17 files
│   │   ├── design_variables/      21 files (incl. SMCNR, cascode variants)
│   │   ├── schematic/             16 PNG images
│   │   ├── amp_spice_testbench/   TB_Amplifier_ACDC.cir, TB_Amplifier_Tran.cir
│   │   └── perf_extraction_amp.py
│   ├── Sensing Front End/
│   │   ├── SMCNR_SE_2st_AMP       ★ Netlist (TSMC180)
│   │   ├── TB_AC_SMCNR_SE_2st_AMP.sp
│   │   ├── TB_TRAN_SMCNR_SE_2st_AMP .sp
│   │   └── ...
│   ├── Low Dropout Regulator/
│   ├── Charge Pump/
│   ├── Phase-Locked Loop/
│   └── Voltage Reference/
├── RGNN_RL/
│   ├── main_AMP.py                Training entry point (DDPG)
│   ├── AMP_NMCNR.py               ★ NMCNR RL env
│   ├── AMP_SMC.py                 ★ Fan_SMC RL env
│   ├── AMP_DFCFC2.py              ★ DFCFC2 RL env
│   ├── AMP_*.py                   11 more RL envs
│   ├── ckt_graphs.py              3462 lines, 16 graph classes
│   ├── dev_params.py              Device parameter utils
│   ├── models.py                  GNN models (GCN/GAT/RGCN/MLP)
│   ├── ddpg.py                    DDPG agent
│   ├── utils.py                   Action normalizer, output parser
│   ├── simulations/               NMCF pre-built sim files only
│   ├── saved_agents/              1 checkpoint (NMCF only)
│   ├── mosfet_model/              sky130_pdk.zip (needs extraction)
│   ├── environment.yml            Conda env spec
│   └── *.whl                      torch_scatter/cluster/sparse/spline_conv
├── PDK/
│   └── sky130_pdk/                Full sky130 PDK (3123 files)
│       └── libs.tech/ngspice/     tt/ff/ss corner models ★
└── docs/
```

---

## 2. Key Circuits: AnalogGym vs AnalogHarness Relationship

### 2.1 SMCNR_SE_2st_AMP (Sensing Front End)

| Attribute | Value |
|-----------|-------|
| File | `AnalogGym/Sensing Front End/SMCNR_SE_2st_AMP` |
| PDK | **TSMC180** (`nch_mac` / `pch_mac`) |
| Ports | `vdda gnda vin vip vout` (5 ports) |
| Devices | 7 PMOS + 1 NMOS + 1 bias current + 1 R (100kΩ) + 1 C (2pF) = **10 total** |
| NMOS | 2 (`xm1`, `xm3` — current mirror load) — wait, these are `nch_mac`... let me recount. `xm1 nch_mac`, `xm3 nch_mac`, `xm4 nch_mac` = **3 NMOS**. `xm7 pch_mac`, `xm6 pch_mac`, `xm5 pch_mac`, `xm2 pch_mac`, `xm0 pch_mac` = **5 PMOS**. Total: 3 NMOS + 5 PMOS = 8 MOS |
| Testbench | `TB_AC_SMCNR_SE_2st_AMP.sp` (TSMC180HV, 6 parallel instances) |

**Relationship to AnalogHarness SMCNR/cand_0031**:
- Both have exactly **8 MOS** (3 NMOS + 5 PMOS)
- Both are 2-stage single-ended amplifiers with Miller compensation
- Port difference: AnalogGym has **5 ports** (`vdda gnda vin vip vout`), AnalogHarness has **6 ports** (`vdda gnda vin vip ibias vout`) — bias is explicit in AnalogHarness
- **Different PDK**: TSMC180 vs Sky130
- **Different device models**: `nch_mac`/`pch_mac` vs `sky130_fd_pr__nfet_01v8`/`sky130_fd_pr__pfet_01v8`
- Verdict: **Same topology family, different PDK. Cannot be used directly as AnalogHarness candidate source without Sky130 remap.**

### 2.2 TwoSt_SMCNR_Pin_2 (design_variables only)

| Attribute | Value |
|-----------|-------|
| File | `Amplifier/design_variables/TwoSt_SMCNR_Pin_2` |
| Netlist | **None** — no SPICE netlist exists |
| Design vars | 8 MOSFETs (M0-M7): BIASCM0-2, INPUT1_PMOS, LOAD1_NMOS, INPUT2_NMOS + R + C + Ibias + CLOAD + VCM |
| Device suffix | `NOFAST` (not standard sky130) |

**Verdict**: Missing netlist. Cannot be used as candidate source. This is an incomplete entry in the benchmark.

### 2.3 Leung_NMCNR_Pin_3 ★ Primary Candidate Source

| Attribute | Value |
|-----------|-------|
| File | `Amplifier/spice_netlist/Leung_NMCNR_Pin_3` |
| PDK | **Sky130** (`sky130_fd_pr__pfet_01v8`, `sky130_fd_pr__nfet_01v8`) |
| Ports | `gnda vdda vinn vinp vout` (5 ports) |
| Devices | 12 PMOS + 12 NMOS + 1 Ibias + 2 Caps + 1 Resistor = **28 total** |
| Design vars | 19 tunable: W/L/M for M0,M8,M10,M17,M21,M23 + Ib + M_C0,M_C1,M_R0 |
| RL env | `RGNN_RL/AMP_NMCNR.py` (GraphAMPNMCNR, 30 nodes, 22 action dim) |
| Testbench | Compatible with `TB_Amplifier_ACDC.cir` / `TB_Amplifier_Tran.cir` |
| NGspice deps | `AMP_NMCNR_vars.spice`, `AMP_NMCNR_ACDC.cir`, `AMP_NMCNR_Tran.cir` in `RGNN_RL/simulations/` (need generation) |

**Relationship to SMCNR/cand_0031**:
- Both use Sky130 devices
- Different topology: NMCNR is NMOS-input cascode with resistor load; SMCNR is PMOS-input 2-stage with Miller compensation
- Different scale: NMCNR has 24 MOS vs SMCNR's 8 MOS
- Different port convention: NMCNR uses `gnda vdda vinn vinp vout`; SMCNR uses `vdda gnda vin vip ibias vout`
- Verdict: **Different topology, same PDK. Can be a candidate source, but is NOT a drop-in replacement for SMCNR/cand_0031.**

### 2.4 Leung_DFCFC2_Pin_3 ★ Candidate Source (failure-case aware)

| Attribute | Value |
|-----------|-------|
| File | `Amplifier/spice_netlist/Leung_DFCFC2_Pin_3` |
| PDK | **Sky130** |
| Ports | `gnda vdda vinn vinp vout` (5 ports) |
| Devices | 13 PMOS + 13 NMOS + 1 Ibias + 2 Caps = **29 total** |
| Design vars | 25 tunable (includes M11-gm2_PMOS, M12-gmf2_PMOS, M10-gm4_PMOS) |
| RL env | `RGNN_RL/AMP_DFCFC2.py` (GraphAMPDFCFC2, 31 nodes, 27 action dim) |
| Known issue | MIM cap (`cap_mim_m3_1`) — same mapping gap as AnalogHarness DFCFC2 diagnostics |

**Verdict**: Valid sky130 source. Same MIM cap mapping issue as AnalogHarness DFCFC2. Any candidate from this topology will face the same substrate/equiv collapse risk when run through MAGICAL → Magic extraction. Should be tagged as **high-risk** in candidate import.

### 2.5 Fan_SMC_Pin_3 ★ Candidate Source (failure-case aware)

| Attribute | Value |
|-----------|-------|
| File | `Amplifier/spice_netlist/Fan_SMC_Pin_3` |
| PDK | **Sky130** |
| Ports | `gnda vdda vinn vinp vout` (5 ports) |
| Devices | 12 PMOS + 12 NMOS + 1 Ibias + 1 Cap = **26 total** |
| Design vars | 19 tunable |
| RL env | `RGNN_RL/AMP_SMC.py` (GraphAMPSMC) |
| Known issue | Substrate/equiv collapse (confirmed in AnalogHarness AH-SMC-001~025) |

**Verdict**: Valid sky130 source. Same substrate collapse risk as AnalogHarness Fan_SMC diagnostics. Any candidate from this topology goes through the same extraction gate. Tag as **failure-prone** in candidate import.

---

## 3. PDK Asset Assessment

| Asset | Location | Status |
|-------|----------|--------|
| Sky130 ngspice models | `PDK/sky130_pdk/libs.tech/ngspice/` | ✅ Complete (tt/ff/ss corners) |
| `tt.spice` | `.../ngspice/corners/tt.spice` | ✅ Exists |
| `ff.spice`, `ss.spice` | `.../ngspice/corners/` | ✅ Exist |
| R+C parasitic models | `.../ngspice/r+c/` | ✅ Available |
| GDS/LEF/MAG | `PDK/sky130_pdk/libs.ref/` | ✅ Available |
| RGNN_RL mosfet_model | `RGNN_RL/mosfet_model/sky130_pdk.zip` | Zipped — needs extraction |

**Path fix needed**: `TB_Amplifier_ACDC.cir` references `../mosfet_model/sky130_pdk/libs.tech/ngspice/corners/tt.spice`. This relative path assumes `mosfet_model/` is under `AnalogGym/Amplifier/` — it's actually at `RGNN_RL/mosfet_model/` and is **zipped**. Must be extracted and symlinked or copied before simulation.

---

## 4. RGNN_RL Training Infrastructure

### 4.1 Pre-trained Assets

| Asset | Topology | Reward | Date |
|-------|----------|--------|------|
| `DDPGAgent_GraphAMPNMCF_*.zip` | NMCF | -0.29 | 2024-09-10 |
| `memory_GraphAMPNMCF_*.pkl` | NMCF | -0.29 | 2024-09-10 |
| `memory_GraphLDOtestbench_*.pkl` | LDO | -12.87 | 2024-09-10 |

**No pre-trained checkpoints for NMCNR, SMC, or DFCFC2.** Training from scratch required.

### 4.2 Training Config (main_AMP.py)

| Parameter | Value |
|-----------|-------|
| Algorithm | DDPG |
| GNN | ActorCriticRGCN (also GCN/GAT/MLP available) |
| Steps | 10000 |
| Memory size | 100000 |
| Batch size | 128 |
| Noise | uniform, sigma 2→0.1, decay 0.9995 |
| Initial random steps | 1000 |

### 4.3 Dependencies

```
numpy, torch, matplotlib, tabulate, IPython
torch_scatter, torch_cluster, torch_sparse, torch_spline_conv (pre-built .whl for cp310)
ngspice (>=42)
```

Pre-built `.whl` files for torch geometric extensions exist in `RGNN_RL/` for Python 3.10 + PyTorch 1.13 CPU.

---

## 5. Testbench Coverage

### 5.1 Amplifier Generic Testbench (`TB_Amplifier_ACDC.cir`)

**Metrics**: `cmrrdc`, `dcgain`, `gain_bandwidth_product`, `phase_margin`, `DCPSRp`, `DCPSRn`, `maxval`, `minval`, `TC`, `Power`, `vos`

**PDK path**: `../mosfet_model/sky130_pdk/libs.tech/ngspice/corners/tt.spice` (needs fixing — see Section 3)

**Adaptable to any 5-port topology** by changing `.include` lines.

### 5.2 Sensing Front End Testbench (`TB_AC_SMCNR_SE_2st_AMP.sp`)

TSMC180-specific. Uses 6 parallel ngspice instances. Not sky130-compatible.

### 5.3 Missing: SMCNR/NMCNR/SMC/DFCFC2-specific testbenches

The `RGNN_RL/simulations/` directory only has NMCF pre-built files. For other topologies, the `*_vars.spice`, `*_ACDC.cir`, `*_Tran.cir` files need to be generated from `dev_params.py` and the generic testbench templates.

---

## 6. Port Convention Mapping

This is critical for AnalogHarness integration:

| Source | Ports | Convention |
|--------|-------|------------|
| AnalogGym Amplifier (18 topologies) | `gnda vdda vinn vinp vout` | 5 ports, ground first |
| AnalogGym SMCNR_SE_2st_AMP | `vdda gnda vin vip vout` | 5 ports, power first |
| AnalogHarness SMCNR/cand_0031 | `vdda gnda vin vip ibias vout` | **6 ports**, explicit bias |
| AnalogHarness Fan_SMC | `vdda gnda vin vip ibias vout` | **6 ports**, explicit bias |

**All AnalogGym Amplifier netlists share `gnda vdda vinn vinp vout` (5 ports, no explicit bias).** Any candidate imported from AnalogGym into AnalogHarness must bridge this port convention gap before MAGICAL layout generation.

---

## 7. Candidate Source Recommendations

### Ready for AnalogHarness import (after environment setup)

| Topology | Priority | Risk | Rationale |
|----------|----------|------|-----------|
| **Leung_NMCNR_Pin_3** | **P0** | Medium | Sky130, closest to SMCNR in topology family, no known substrate collapse |
| Leung_DFCFC2_Pin_3 | P1 | **High** | Sky130, but MIM cap mapping gap; will face same collapse as AnalogHarness DFCFC2 |
| Fan_SMC_Pin_3 | P1 | **High** | Sky130, confirmed substrate collapse; useful as failure-case stress test |

### NOT ready (blocked)

| Source | Blocker |
|--------|---------|
| SMCNR_SE_2st_AMP (Sensing Front End) | TSMC180 — needs PDK remap to Sky130 before AnalogHarness can use |
| TwoSt_SMCNR_Pin_2 | Missing SPICE netlist |
| Any topology | Need RGNN RL training or alternative candidate generation before candidates exist |

### Candidate Generation Options

1. **RGNN RL training** (`main_AMP.py`): Requires setting up Python env (torch+numpy+etc), extracting `sky130_pdk.zip` to `mosfet_model/`, generating sim files for NMCNR, then training DDPG. Produces ranked candidates from the RL agent's rollout.

2. **Direct grid/random sampling**: Use `AMP_NMCNR.py`'s design variable ranges + `dev_params.py` to generate diverse sizing candidates without RL training. Simulate with ngspice for pre-sim metrics. Faster bootstrap than full RL training.

3. **GRPO (vendored in AnalogHarness `third_party/analoggym_grpo/`)**: The vendored GRPO code already has `amp_nmcnr` config and sim files. Requires same Python deps as RGNN RL. Can train GRPO agent for NMCNR topology.

---

## 8. ckt_graphs.py Anomaly

Lines 791 and 982 both define `class GraphAMPNMCNR` with identical structure (24 MOS + Ib + C0 + C1 + R0, 30 nodes). This appears to be a **code duplication**, not two distinct topologies. The second definition (line 982) has docstring annotations; the first (line 791) does not. The second is likely the canonical one.

---

## 9. Action Items

### Immediate (this workstream)

- [ ] Extract `PDK/sky130_pdk/` to `RGNN_RL/mosfet_model/sky130_pdk/` (or symlink)
- [ ] Set up working Python venv with torch+numpy+matplotlib+tabulate+IPython
- [ ] Generate NMCNR simulation files (`AMP_NMCNR_vars.spice`, `AMP_NMCNR_ACDC.cir`, `AMP_NMCNR_Tran.cir`)
- [ ] Run small-batch candidate generation for Leung_NMCNR_Pin_3 (RL or sampling — decide approach)
- [ ] Import candidates via `analoggym_importer.py` with `trust_assigned=False`
- [ ] Run each candidate through AnalogHarness DRC/LVS/PEX gate

### Future

- [ ] SMCNR_SE_2st_AMP Sky130 remap: port the TSMC180 netlist to sky130 devices
- [ ] TwoSt_SMCNR_Pin_2: locate or reconstruct missing netlist
- [ ] Fan_SMC/DFCFC2: import as failure-case pressure tests only

---

## 10. Forbidden Claims

- Do not claim AnalogGym's SMCNR_SE_2st_AMP equals AnalogHarness SMCNR/cand_0031
- Do not claim Leung_NMCNR_Pin_3 is a drop-in SMCNR replacement
- Do not claim any AnalogGym netlist has passed AnalogHarness LVS without running the pipeline
- Do not treat `RGNN_RL/saved_agents/NMCF` as transferable to NMCNR/SMC/DFCFC2
