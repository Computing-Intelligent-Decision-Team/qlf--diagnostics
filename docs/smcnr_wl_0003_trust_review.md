# SMCNR W/L Sweep 0003 — Trust Review

**Date**: 2026-06-23
**Status**: wl_005 passes all gates; marked `candidate_for_parasitic_modeling_review`

## 1. Candidates Reviewed

| Candidate | Change | equiv | LVS | PEX caps | PEX total | Trust |
|-----------|--------|-------|-----|----------|-----------|-------|
| var_ref_001 | exact repeat | 0 | PASS | 37 | 80.9455 fF | baseline reference |
| wl_003 | load_nmos_w +5% | 0 | TBD | 37 | TBD | pending |
| **wl_005** | **bias_pmos_l -5%** | **0** | **PASS** | **36** | **80.2483 fF** | **candidate_for_parasitic_modeling_review** |

## 2. wl_005 Trust Gate Results

### 2.1 Source Sizing

| Parameter | cand_0031 | wl_005 | Change |
|-----------|-----------|--------|--------|
| bias_pmos_l | 10.0 | 9.5 | **-5%** |
| All other params | — | unchanged | — |

Only one parameter changed. Source sizing provenance is clean.

### 2.2 MAGICAL Layout

- **Result**: PASS (route.gds generated)
- **GDS size**: 321K (MOS-only)
- **MOS count**: 8 (3 NMOS + 5 PMOS)

### 2.3 DRC

```
Total DRC errors found: 0
```

### 2.4 Extraction

| Metric | Value |
|--------|-------|
| equiv | **0** ✅ |
| substrate | "gnda" ✅ |
| Ports | 6 (vdda gnda vin vip ibias vout) ✅ |
| vdda retained | yes ✅ |
| PMOS S/B | vdda ✅ |
| Extracted MOS | 8 ✅ |

### 2.5 LVS

```
Result: Circuits match uniquely.
Circuit 1: SMCNR_SE_2st_AMP
Circuit 2: SMCNR_SE_2st_AMP_flat
sky130_fd_pr__nfet_01v8 (3)  |  sky130_fd_pr__nfet_01v8 (3)
sky130_fd_pr__pfet_01v8 (5)  |  sky130_fd_pr__pfet_01v8 (5)
Number of devices: 8          |  Number of devices: 8
Number of nets: 9             |  Number of nets: 9
Netlists match uniquely.
```

### 2.6 Extracted MOS Geometry

| Device | var_ref_001 | wl_005 | Delta |
|--------|------------|--------|-------|
| bias PMOS (xm7, xm6) l | 10.0 | **9.5** | -5% ✅ |
| bias PMOS AD/AS | 0.0385 | 0.0495 | +28% (area increased as L decreased) |
| bias PMOS PD/PS | 0.79 | 0.89 | +13% |
| diff pair PMOS | w=7.52 l=8.24 | w=7.52 l=8.24 | unchanged ✅ |
| output PMOS | w=0.22 l=10 | w=0.22 l=10 | unchanged ✅ |
| NMOS devices | all unchanged | all unchanged | unchanged ✅ |

The L perturbation correctly affects only the bias PMOS devices. Geometry
diversity is confirmed.

### 2.7 PEX

| Metric | var_ref_001 | wl_005 | Delta |
|--------|------------|--------|-------|
| Cap count | 37 | **36** | -1 cap |
| Total cap | 80.9455 fF | 80.2483 fF | -0.6972 fF |
| Cap edge list | (baseline) | **different** | Cap IDs/labels differ |

The PEX cap-edge signature differs from the baseline. One fewer parasitic
capacitor is extracted. The total capacitance decreased by 0.7 fF, consistent
with reduced bias PMOS gate area (L decreased → smaller device → less parasitic).

## 3. Trust Decision

```json
{
  "candidate_id": "wl_005_bias_pmos_l_m5",
  "trust_assigned": false,
  "usable_for_supervised_positive_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": false,
  "candidate_for_parasitic_modeling_review": true,
  "review_basis": [
    "DRC=0",
    "equiv=0",
    "LVS circuits match uniquely (8 dev, 9 nets)",
    "PEX 36 caps (vs baseline 37) — confirmed parasitic diversity",
    "Extracted MOS AD/AS/PD/PS differ from baseline",
    "Source sizing: single-parameter L perturbation (-5%)",
    "MOS-only projection path"
  ],
  "blockers_for_training_positive": [
    "Not reviewed by Codex",
    "Single sample — needs N>=3 diverse positive samples before dataset expansion",
    "MOS-only projection — not passive-inclusive PEX"
  ]
}
```

## 4. Significance

wl_005 is the **first new candidate** to pass all trust gates and show
confirmed PEX diversity since the original cand_0031 baseline. It proves:

1. Fresh MAGICAL producer works under MOS-only projection
2. L perturbation on non-diff-pair devices survives the pipeline
3. The resulting PEX differs from baseline in cap count, total, and edge structure
4. The extracted MOS geometry changes match the source sizing change

This opens the path for systematic SMCNR variant production on the safe
perturbation axes (non-diff-pair W/L).

## 5. Forbidden Claims

- ❌ wl_005 is NOT training-positive (requires Codex review + N>=3)
- ❌ Passive-inclusive path is NOT confirmed
- ❌ W perturbation is NOT solved (still crashes MAGICAL)
- ❌ Dataset is NOT expanded beyond n=1 positive
