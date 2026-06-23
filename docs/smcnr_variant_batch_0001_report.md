# SMCNR Variant Batch 0001 — Report

**Date**: 2026-06-23
**Status**: **STOPPED** — trust gate stop condition triggered on first variant

## 1. Executive Summary

Batch 0001 attempted to generate 5 SMCNR sizing variants from cand_0031 baseline
using MULTI-only perturbation (bias_tail_multi, second_stage_multi, etc.). The
first variant (`var_m01`: bias_tail_multi 2→3) triggered the stop condition:

**DRC=0, but Magic extraction produces `equiv "gnda" "vdda"` — well/substrate extraction collapse triggered by multi+1.**

Conclusion: SMCNR/cand_0031 is a **toolchain-feasible island**, not a stable
neighborhood. Even the smallest integer perturbation (multi +1) can produce
a power-ground short in MAGICAL routing.

## 2. Background: Reproducibility Package Audit

The `reproducibility/smcnr_se_2st_amp/` package contains 38 candidates
(cand_0001 through cand_0038) from the original AnalogGym GRPO run. An audit
of their `state.json` files revealed:

| Finding | Detail |
|---------|--------|
| Total candidates | 38 |
| With non-zero sizing deviation from cand_0031 | 3 (cand_0001, cand_0002, cand_0004: ~1.4% in 3 params) |
| With 0.0% deviation | 35 (sizing-identical to cand_0031) |
| With large deviation (>10%) | 0 remaining — the rest converge to cand_0031 |

**The 35 "identical" candidates cannot serve as variants.** They produce the
exact same sizing values as cand_0031 and would generate identical layouts.
The 3 that differ do so by only ~1.4% in W values — and even those are within
MAGICAL PDK grid rounding.

Artifact paths in the reproducibility `state.json` files reference Windows
paths (`E:\...`) that don't exist locally. Only the sizing values are portable.

## 3. Variant Design

Five variants were designed using MULTI-only perturbation (keeping W/L/nf
exactly as cand_0031, since W perturbation was found to crash MAGICAL's
Anaroute router with `abs(pBox->yl()) % 10` assertion failure):

| Variant | Perturbation | cand_0031 value | New value |
|---------|-------------|-----------------|-----------|
| var_m01 | bias_tail_multi +1 | 2 | 3 |
| var_m02 | second_stage_pmos_multi +2 | 10 | 12 |
| var_m03 | second_stage_nmos_multi +2 | 10 | 12 |
| var_m04 | bias_tail_multi+1 + pmos_multi+2 | 2, 10 | 3, 12 |
| var_m05 | all multi ±1 | 2,10,10,1 | 3,9,11,2 |

**Only var_m01 was executed** before the stop condition was triggered.

## 4. var_m01 Pipeline Results

### 4.1 MAGICAL Placement & Routing

- **Result**: ✅ PASS
- `SMCNR_SE_2st_AMP.route.gds`: 429 KB written
- `SMCNR_SE_2st_AMP.ioPin`: generated
- Runtime: ~5 seconds

### 4.2 Sky130 GDS Remap

- **Result**: ✅ PASS
- 18 layers remapped, 2 preserved unmapped

### 4.3 Pin Shapes & Labels

- **Result**: ✅ Added
- 6 top-level ports identified from ioPin

### 4.4 Magic DRC

- **Result**: ✅ PASS
- `Total DRC errors found: 0`

### 4.5 Magic Extraction

- **Result**: ⚠️ Completed with critical warnings
- **`Ports "gnda" and "vdda" are electrically shorted`**
- Substrate: `"gnda"` ✅
- **Equiv: 1 record — `equiv "gnda" "vdda"`** ❌
- 13 total warnings
- 16 devices in extracted SPICE (expected 10: 8 MOS + 1 R + 1 C = 8 MOS counted as 8 + R count issue)

### 4.6 LVS Gate

- **Result**: ❌ **FAIL — Stop condition triggered**
- `equiv > 0` → immediate stop
- vdda-gnda short makes LVS impossible regardless of device match

## 5. Failure Evidence

### 5.1 Extraction Warnings (from `extract2.log`)

```
Warning: Ports "gnda" and "vdda" are electrically shorted.
SMCNR_SE_2st_AMP_flat: 13 warnings
Total of 13 warnings.
Warning: Ports "gnda" and "vdda" are electrically shorted.
```

### 5.2 Equiv Record (from `.ext` file)

```
equiv "gnda" "vdda"
```

### 5.3 Artifacts

```
generated/smcnr_variants/batch_0001/var_m01/
├── case/
│   ├── SMCNR_SE_2st_AMP_var_m01.sp        ← MAGICAL netlist
│   ├── smcnr_se_2st_amp_var_m01.json       ← MAGICAL config
│   ├── SMCNR_SE_2st_AMP.route.gds          ← MAGICAL output
│   ├── SMCNR_SE_2st_AMP.sky130.gds         ← remapped
│   ├── SMCNR_SE_2st_AMP.sky130.pinned.gds  ← with pin shapes+labels
│   ├── SMCNR_SE_2st_AMP.ioPin              ← MAGICAL pin data
│   └── run.log                             ← MAGICAL run log
├── SMCNR_SE_2st_AMP.gds                    ← copied for extraction
├── SMCNR_SE_2st_AMP_flat.ext               ← Magic extraction
├── SMCNR_SE_2st_AMP_flat.spice             ← extracted SPICE
├── drc.tcl, drc.log, extract.tcl, extract2.log
└── state.json                              ← variant parameters
```

## 6. Trust Status

| Flag | Value |
|------|-------|
| `trust_assigned` | `false` |
| `usable_for_supervised_positive_training` | `false` |
| `usable_for_parasitic_modeling` | `false` |
| `usable_only_as_failure_case` | `true` |
| `failure_category` | `well_substrate_extraction_collapse` |
| `positive_dataset_count` | **unchanged (1)** |

## 7. Stop Condition Analysis

The stop condition was `equiv > 0`, triggered on the FIRST variant.

| Condition | Detected | Value |
|-----------|----------|-------|
| DRC = 0 | ✅ | 0 errors |
| substrate = gnda | ✅ | "gnda" |
| equiv = 0 | ❌ FAIL | 1 record |
| LVS match | ❌ FAIL | vdda-gnda short |
| 3 consecutive FAILs | Not reached | stopped after 1st |

## 8. Root Cause Assessment

### 8.1 What the evidence actually shows

The physical VDD and GND port shapes are spatially separated (`port "vdda"` at
y=7110–7470, `port "gnda"` at y=-740–-380, ~8µm apart on m5). The failure is
**not** a routed metal short between VDD and GND wires.

Instead, the failure is a **well/substrate extraction collapse**: Magic extraction
produces `equiv "gnda" "vdda"` and extracts PMOS source/bulk terminals onto
`gnda` instead of `vdda`. The n-well-to-p-substrate connectivity domain is being
merged during extraction, not during routing.

### 8.2 Mechanism

The `multi` parameter controls the number of parallel device fingers in MAGICAL.
When `multi` changes from 2 to 3:

1. MAGICAL selects/assembles a different device GDS geometry (different
   finger count, different well/tap/body contact arrangement, different
   diffusion拼接 pattern)
2. Magic extraction reads this geometry and interprets the well/substrate
   connectivity
3. At `multi=2`, the well/tap/substrate relationship is correctly resolved:
   `substrate=gnda`, `equiv=0`, PMOS bulk correctly on `vdda`
4. At `multi=3`, extraction merges the n-well and p-substrate domains:
   `equiv "gnda" "vdda"`, PMOS source/bulk extracted onto `gnda`

### 8.3 What we know vs what we don't

**Known (evidence-backed):**
- `multi=2` → cand_0031 passes extraction/LVS
- `multi=3` → var_m01 shows `equiv "gnda" "vdda"` with PMOS S/B on `gnda`
- DRC=0 in both cases — DRC does not detect this class of failure
- The failure is in Magic extraction, not in metal routing geometry

**Unknown (requires further diagnosis):**
- Whether the root cause is in MAGICAL device assembly (well/tap placement),
  MAGICAL routing of well ties, or Magic's substrate extraction model
- Whether it is specific to `xm6` (bias tail) or general to any `multi`
  perturbation
- Whether other multi groups trigger the same collapse

### 8.4 Why cand_0031 succeeded

The GRPO optimizer converged to (bias_tail=2, pmos_multi=10, nmos_multi=10,
bias_ref=1) — 34/38 candidates share this combination. This parameter point
happens to produce device geometries that Magic extraction correctly resolves.
It is a **toolchain-feasible island**: a discrete point in the parameter space
where MAGICAL device assembly, routing, and Magic extraction all align to
produce a correct result.

## 9. Key Findings

1. **SMCNR/cand_0031 is a toolchain-feasible island**, not a stable neighborhood.
2. **MULTI perturbation changes device geometry**, which changes how Magic
   extraction resolves well/substrate connectivity.
3. **The var_m01 failure is NOT a metal short.** It is `equiv "gnda" "vdda"`
   introduced during extraction, with PMOS terminals extracted onto `gnda`.
4. **DRC=0 does not detect well/substrate extraction collapse.**
5. **The existing 38 reproducibility candidates are 2 unique multi combinations**
   — (2,10,10,1) with 34 candidates, (1,25,9,2) with 4. Only the first was
   carried to L6 closure.
6. **W perturbations (±5%) crash MAGICAL's Anaroute router** with grid alignment
   assertion failures — a separate issue from the extraction collapse.

## 10. Next Step: Single-Variable Multi Sweep

Do NOT expand sizing perturbation blindly. Instead, run a controlled sweep to
identify which MOS group triggers the extraction collapse:

| Sweep ID | Change | Group |
|----------|--------|-------|
| sweep_01 | bias_tail_multi 2→3 | xm6 (tail current source) — **already done, FAIL** |
| sweep_02 | bias_ref_multi 1→2 | xm7 (bias reference diode) |
| sweep_03 | second_stage_pmos_multi 10→11 | xm5 (output PMOS) |
| sweep_04 | second_stage_nmos_multi 10→11 | xm4 (output NMOS) |
| sweep_05 | diff_pair_multi 1→2 | xm0, xm2 (input diff pair) |
| sweep_06 | load_nmos_multi 1→2 | xm1, xm3 (load NMOS) |

Each sweep point:
- Changes exactly ONE multi parameter by +1
- Keeps all other parameters at cand_0031 values
- Runs only to extraction (no PEX, no post-sim)
- Checks: substrate name, equiv count, PMOS bulk net, port count

Stop condition per sweep point:
- `equiv > 0` → record as FAIL, continue to next group
- `substrate != gnda` → record as FAIL, continue

Goal: identify which MOS group(s) are sensitive to multi perturbation, and
whether the collapse is specific to the bias PMOS group or general.

## 11. Forbidden Claims

- ❌ var_m01 is NOT a positive parasitic modeling sample
- ❌ SMCNR variants are NOT feasible with current MAGICAL flow
- ❌ cand_0031 is NOT in a stable sizing neighborhood
- ❌ DRC clean does NOT guarantee LVS clean
- ❌ Positive dataset count has NOT increased (still n=1)
