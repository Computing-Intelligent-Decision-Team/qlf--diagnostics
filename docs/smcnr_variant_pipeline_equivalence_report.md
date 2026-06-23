# SMCNR Variant Pipeline Equivalence Report

**Date**: 2026-06-23
**Status**: **Pipeline NOT equivalent — all variant results invalidated**

## 1. Executive Summary

The fresh MAGICAL variant pipeline used for SMCNR sizing perturbation experiments
is **not equivalent** to the verified SMCNR replay pipeline. A controlled
experiment with **exact cand_0031 sizing** (`var_ref_000`) proved this:

| Pipeline | GDS source | equiv | Ports | PMOS S/B | Status |
|----------|-----------|-------|-------|----------|--------|
| SMCNR local replay | Pre-prepared (full pipeline) | 0 ✅ | 6 ✅ | vdda ✅ | PASS |
| Fresh MAGICAL (var_ref_000) | Fresh MAGICAL Docker | 1 ❌ | 5 | gnda ❌ | FAIL |

**Same Magic binary (8.3.483), same sky130 magicrc, same extraction Tcl. Same
exact netlist (cand_0031 sizing).** The only difference is the GDS preparation
pathway.

**All sweep results (sweep_02 through sweep_06) and var_m01 are invalid for
assessing sizing sensitivity.** Their failures are caused by pipeline
non-equivalence, not by multi perturbation.

## 2. Control Experiment

### 2.1 Method

- **Test sample**: `var_ref_000` — exact cand_0031 sizing, zero perturbation
- **Source netlist**: `examples/smcnr_se_2st_amp_sky130_try/SMCNR_SE_2st_AMP_layout_physical_hspice.sp`
  (identical to cand_0031)
- **MAGICAL config**: simplified config without `lvsNetRenames`, using
  `/MAGICAL/examples/sky130PDK/` PDK
- **Post-processing**: manual remap + pin shapes/labels via Python tools
- **Extraction**: same Magic binary, same rcfile, same Tcl as SMCNR replay

### 2.2 Result

```
var_ref_000 extraction:
  substrate: "gnda" ✅
  equiv:     1 ❌ (equiv "gnda" "vdda")
  ports:     5 ❌ (missing vdda)
  PMOS S/B:  gnda ❌ (should be vdda)
```

### 2.3 SMCNR Replay (re-verified 2026-06-23)

```
SMCNR replay extraction:
  substrate: "gnda" ✅
  equiv:     0 ✅
  ports:     6 ✅ (vdda gnda vin vip ibias vout)
  PMOS S/B:  vdda ✅
```

## 3. Gap Analysis

### 3.1 What the SMCNR replay pipeline does (verified path)

The SMCNR replay uses a GDS prepared by the full `run_sky130_case_pipeline.sh`
which includes:

1. MAGICAL placement & routing with proper PDK paths
2. Sky130 GDS remap
3. Pin shape injection with net-name-aware labeling
4. Pin label injection
5. **LVS netlist preparation** (`prepare_lvs_netlists.py`):
   - Model alias conversion: `nch_mac→sky130_fd_pr__nfet_01v8`, `pch_mac→sky130_fd_pr__pfet_01v8`
   - **Net renaming**: `a_20_494#→outn`, `a_2100_n30#→outp`, `a_4024_586#→net53`, `a_4345_n10#→outp`, `a_785_2846#→ibias`
   - Parasitic capacitor stripping
   - MOS property removal (ad, as, pd, ps)
6. **`lvsNetRenames` in MAGICAL config** — 5 rename rules mapping Magic-generated net names to logical design nets
7. Connectivity LVS with prepared source and extracted netlists

### 3.2 What the fresh MAGICAL pipeline does (simplified)

1. MAGICAL placement & routing with `/MAGICAL/examples/sky130PDK/` PDK
2. Sky130 GDS remap (same tool)
3. Pin shape injection (same tool, different ioPin)
4. Pin label injection (same tool, different ioPin)
5. **No LVS netlist preparation** — skipped entirely
6. **No `lvsNetRenames` in MAGICAL config** — missing
7. No connectivity LVS — extraction only

### 3.3 Likely root cause

The `equiv "gnda" "vdda"` in the fresh MAGICAL pipeline is most likely caused by:

**A. PDK difference (highest probability)**

MAGICAL Docker uses `/MAGICAL/examples/sky130PDK/` (mapped to
`examples/sky130PDK/`). The original SMCNR pipeline used
`../../generated/sky130PDK_trial/` — a different PDK build. Different PDKs
may produce different device GDS cells with different well/tap structures,
affecting how Magic extraction resolves n-well/p-substrate connectivity.

**B. Pin label/net resolution (medium probability)**

Without `lvsNetRenames`, Magic extraction may not correctly associate pin
shapes with logical net names. When vdda pin shape is not linked to the
`vdda` net in the design, extraction may resolve it to the substrate node
instead.

**C. ioPin coordinate differences (lower probability)**

The fresh MAGICAL ioPin has different bounding boxes than the original.
While vdda and gnda are spatially separated in both, the coordinate
differences could affect net resolution if Magic uses pin-to-net proximity
heuristics.

## 4. Impact on Previous Results

### 4.1 Invalidated conclusions

| Previous claim | Status | Reason |
|---|---|---|
| "multi+1 triggers collapse" | ❌ RETRACTED | var_ref_000 also fails |
| "cand_0031 is narrow feasible point" | ❌ RETRACTED | pipeline equivalence not established |
| "sizing perturbation breaks routing" | ❌ RETRACTED | may be pipeline artifact |
| "PDK cell / multi cell has issues" | ❌ RETRACTED | no evidence for this |

### 4.2 Valid conclusions

| Claim | Status |
|---|---|
| Fresh MAGICAL pipeline is not equivalent to SMCNR replay | ✅ Confirmed by var_ref_000 |
| All 7 variant failures (var_m01 + sweep_02-06) cannot be attributed to sizing | ✅ Confirmed |
| SMCNR replay extraction remains equiv=0 with re-verified GDS | ✅ Confirmed |
| DRC=0 does not guarantee extraction clean | ✅ Still true |

## 5. Fix Plan

### Step 1: Align PDK paths

Use `generated/sky130PDK_trial/` (generated 2026-06-23) for MAGICAL Docker,
matching the path convention used by the original pipeline:

```json
{
    "techfile": "../../generated/sky130PDK_trial/sky130.techfile",
    "simple_tech_file": "../../generated/sky130PDK_trial/sky130.techfile.simple",
    "lef": "../../generated/sky130PDK_trial/sky130.lef"
}
```

These paths resolve correctly both inside Docker (`/MAGICAL/generated/...`)
and locally (relative to case dir).

### Step 2: Add lvsNetRenames

```json
{
    "lvsNetRenames": [
        "a_785_2846#=ibias",
        "a_4024_586#=net53",
        "a_20_494#=outn",
        "a_2100_n30#=outp",
        "a_4345_n10#=outp"
    ]
}
```

These renames must be updated for each variant's specific Magic-generated net
names (they may differ between MAGICAL runs even for the same netlist).

### Step 3: Run LVS netlist preparation

After extraction, run the equivalent of `prepare_lvs_netlists.py`:
- Convert `nch_mac`/`pch_mac` → `sky130_fd_pr__*` in source netlist
- Strip parasitic capacitors from extracted netlist
- Rename nets using `lvsNetRenames`
- Remove MOS properties (ad, as, pd, ps)

### Step 4: Re-run var_ref_000

Only after steps 1-3 are complete, re-run `var_ref_000` through the full
pipeline and verify:
- DRC = 0
- substrate = "gnda"
- equiv = 0
- 6 ports in extracted SPICE
- PMOS S/B on vdda

### Step 5: Resume sweep (only after var_ref_000 PASS)

If and only if `var_ref_000` passes all gates, resume the single-variable
multi sweep to determine sizing sensitivity.

## 6. Trust Status

| Flag | Value |
|------|-------|
| var_ref_000 usable for training | `false` |
| All sweep results valid | `false` (pipeline not equivalent) |
| SMCNR/cand_0031 positive baseline | unchanged (n=1) |
| Variant pipeline ready | `false` — requires repair |

## 7. Forbidden Claims

- ❌ Multi perturbation effects are NOT established
- ❌ SMCNR sizing sensitivity is NOT characterized
- ❌ cand_0031 neighborhood stability is NOT assessed
- ❌ MAGICAL PDK cell quality is NOT implicated
- ❌ Fresh MAGICAL pipeline is NOT equivalent to verified replay pipeline
