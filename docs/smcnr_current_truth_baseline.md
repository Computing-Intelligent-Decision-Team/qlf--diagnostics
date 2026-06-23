# SMCNR Current Truth Baseline

**Date**: 2026-06-23
**Status**: Fresh MAGICAL producer NOT available; cand_0031 replay is only stable positive baseline

## 1. Confirmed Facts

### 1.1 Working path

| Item | Status | Evidence |
|------|--------|----------|
| SMCNR local replay (pre-generated GDS) | ✅ Stable | R1/R2 LVS PASS, equiv=0, 6 ports, PMOS on vdda |
| cand_0031 positive baseline | ✅ Only verified positive | DRC=0, LVS=PASS, PEX=37 caps, post-sim PASS, PVT 3/3 |
| Multi sweep 7/7 batch results | ✅ Valid artifacts | DRC=0, LVS=yes, PEX=37 for all 7 candidates |
| Harness-native pipeline code | ✅ Functional | SpiceCandidateCompiler + LayoutVerificationAdapter |
| MAGICAL Docker image | ✅ Available | jayl940712/magical:latest |
| AnalogGym importer | ✅ Working | Mock smoke test PASS; real import pending |
| Parasitic dataset v0 | ✅ 6 records | 1 positive + 5 failure-case |
| 24 tests | ✅ All passing | test_parasitic_dataset + test_analoggym_importer |

### 1.2 Non-working path

| Item | Status | Evidence |
|------|--------|----------|
| Fresh MAGICAL with passives | ❌ Unavailable | 0/15+ extraction pass rate; passives trigger collapse |
| W/L perturbation sweep | ⚠️ Blocked (but fix identified) | Use MOS-only projection |
| nf perturbation | ⚠️ Blocked (but fix identified) | Use MOS-only projection |
| Same-sizing layout seed sweep | ⚠️ Blocked (but fix identified) | Use MOS-only projection |

### 1.3 Fixed path (newly confirmed)

| Item | Status | Evidence |
|------|--------|----------|
| MOS-only MAGICAL extraction | ✅ Working | 2/2 equiv=0, clean extraction |
| MOS-only = multi sweep path | ✅ Confirmed | Multi sweep used MOS-only projection |
| Fresh MAGICAL producer (MOS-only) | ✅ Available | Requires stripping passives from netlist |

## 2. Withdrawn Hypotheses

Each was proposed, tested, and eliminated as the sole root cause.

| # | Hypothesis | Why withdrawn | Evidence |
|---|-----------|---------------|----------|
| 1 | Post-route local_power stripe missing | Multi sweep had it OFF (0) and passed | `MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE=0` in summary |
| 2 | Pre-route VDD stripe env missing | Multi sweep had `MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES=0` | Summary shows all stripe vars at default/OFF |
| 3 | Manual shell vs harness controller | Harness controller runs also fail | 4/4 harness CIEL runs FAIL |
| 4 | CIEL PDK vs bundled PDK | CIEL PDK runs also fail | wl_ref_ciel_000 FAIL with CIEL PDK |
| 5 | PDK trial regenerated | Multi sweep used same 12:09 PDK trial | Timeline: 12:09 gen → 15:38 sweep PASS |
| 6 | lvsNetRenames missing | Present in both PASS and FAIL cases | Configs byte-identical |
| 7 | Netlist format difference | Diff shows trivial formatting only | `l=10u` vs `l=10.0u` |
| 8 | MAGICAL nondeterminism | 0/5 assay too consistent for chance | All 5 fail identically |
| 9 | Magic version | Same 8.3.483 in both | Verified in pipeline logs |
| 10 | Docker image | Same jayl940712/magical:latest | Unchanged |

## 3. Root Cause Found: Passives Trigger Well/Substrate Collapse

### 3.1 The enabling condition

**MOS-only projection (R+C passives stripped from MAGICAL netlist) produces
clean extraction. Full netlist with rppolywo_m + cfmom_2t passives triggers
`equiv "gnda" "vdda"` well/substrate collapse.**

Evidence:
- Multi sweep 7/7 PASS: all runs used MOS-only projection (passives dropped)
- Manual full-netlist runs 0/15+ FAIL: all included passives
- Assay MOS-only run 1: equiv=0 ✅
- Assay MOS-only run 2: equiv=0 ✅
- Assay full-netlist runs 1-5: equiv=1 ❌

### 3.2 Why passives cause collapse

When MAGICAL places the resistor (rppolywo_m) and capacitor (cfmom_2t)
devices, their geometry interacts with the n-well structure. The passive
device cells occupy die area that may displace or disrupt the n-well
connectivity. Without passives, the n-well is cleanly separated from
p-substrate in extraction.

The upstream SMCNR replay GDS (which includes passives and extracts clean)
was generated on a different system (Windows+WSL) with a different PDK trial
and MAGICAL environment. That environment apparently handled passive placement
without triggering the collapse — a capability not reproduced locally.

### 3.3 Extraction collapse mechanism

When the collapse occurs, Magic extraction consistently produces:
- `equiv "gnda" "vdda"` (1 record)
- PMOS source/bulk on `gnda` instead of `vdda`
- `vdda` port dropped from extracted subckt
- "Ports gnda and vdda are electrically shorted" (2 warnings)

The physical port shapes are spatially separated (~8µm on met5). The collapse
is an extraction model artifact, not a physical metal short.

## 4. Current Status

| Capability | Status |
|-----------|--------|
| MOS-only fresh MAGICAL producer | ✅ Working (strip passives) |
| Full-netlist fresh MAGICAL producer | ❌ Blocked (passives trigger collapse) |
| W/L perturbation | ⚠️ Must use MOS-only projection |
| AnalogGym data production | ⚠️ Must generate MOS-only candidates |
| Passive-inclusive PEX | ❌ Requires fixing passive placement/extraction |

## 5. Available Assets

| Asset | Location | Use |
|-------|----------|-----|
| Multi sweep batch | `harness_native_sweep_multi_0001/` | Reference artifacts (7/7 PASS) |
| SMCNR replay GDS | `generated/smcnr_local_replay*/` | Verified working GDS |
| Upstream artifacts | `origin/main:reproducibility/.../upstream_artifacts/` | Full upstream GDS chain |
| Batch_0002 candidates | `harness_native_sweep_wl_0002/` | Pre-generated W/L variants (unvalidated) |
| NMCNR MOS-only probe | `generated/diagnostics/nmcnr_mos_only_projection/` | Failure-case evidence |
| AnalogGym source audit | `docs/analoggym_source_audit.md` | Circuit source mapping |
| Parasitic dataset v0 | `generated/parasitic_modeling/dataset_v0.jsonl` | 6 records, 1 positive |

## 6. Next Actions (Priority Order)

### P0 — Resume W/L sweep with MOS-only projection
- Root cause identified: passives trigger collapse
- Fix: use MOS-only netlist (strip R+C) for all MAGICAL runs
- Resume batch_0002 W/L candidates with MOS-only projection
- Verify extraction pass rate > 0 with correct netlist type

### P1 — Add passive stripping to harness pipeline
- Ensure `LayoutVerificationAdapter` always passes MOS-only netlist to MAGICAL
- The multi sweep already does this via `write-mos-projection` helper
- Document the requirement

### P2 — Investigate passive-inclusive path (longer term)
- Why does passives+R+C trigger collapse locally but not on upstream?
- Compare upstream passive placement vs local
- May require PDK cell fix or MAGICAL placement constraint
