# SMCNR nf=2 Failure Taxonomy

**Date**: 2026-06-23
**Status**: Taxonomy complete — failure mechanism identified

## 1. Evidence Basis

Artifacts examined for both nf=2 candidates:

```
harness_native_sweep_nf_0001/
├── sweep_nf_01_diff_pair_keep_w/      (diff_pair_nf 1→2, w=7.52 kept)
└── sweep_nf_02_diff_pair_const_total_w/ (diff_pair_nf 1→2, w=7.52→3.76)
```

For each: `.ext`, raw extracted SPICE, connectivity-normalized SPICE, LVS log,
LVS result summary.

## 2. Observed Failure Profile

Both candidates exhibit the same failure signature:

| Symptom | sweep_nf_01 | sweep_nf_02 |
|---------|-------------|-------------|
| Extracted subckt ports | `gnda vin vip ibias vout` (5) | `gnda vin vip ibias vout` (5) |
| Missing port | `vdda` | `vdda` |
| `.ext` port definitions | 6 present (incl. vdda) | 6 present (incl. vdda) |
| `equiv` records | 1: `equiv "gnda" "vdda"` | 1: `equiv "gnda" "vdda"` |
| `substrate` | `"gnda"` | `"gnda"` |
| Source MOS count | 8 | 8 |
| Extracted raw MOS | 10 (7 PMOS + 3 NMOS) | 10 (7 PMOS + 3 NMOS) |
| PMOS source/bulk net | `gnda` | `gnda` |
| Diff-pair PMOS split | 2→4 devices, w=3.76 each | 2→4 devices, w=1.88 each |
| Netgen merge | merged 2 devices | merged 2 devices |
| LVS result | FAIL (net + device mismatch) | FAIL (net + device mismatch) |

## 3. Failure Mechanism

### 3.1 Primary: Well/substrate extraction collapse (equiv gnda-vdda)

The root cause is the same `equiv "gnda" "vdda"` well/substrate extraction
collapse seen in var_m01 and the NMCNR probe.

```
.ext evidence:
  port "vdda" 1  -340 3035  7460 3395  m5     ← vdda port EXISTS, physically on met5
  port "gnda" 2  -340 -740  7460 -380  m5     ← gnda port EXISTS, ~3.8µm away on met5
  equiv "gnda" "vdda"                          ← extraction merges them
  substrate "gnda" ...                         ← substrate = gnda
```

The physical port shapes are spatially separated (vdda at y=3035-3395, gnda at
y=-740 to -380, ~3.8µm apart on m5). The equiv is introduced during extraction,
not by physical metal shorting.

**Causal chain**:

1. `diff_pair_nf` changes from 1 to 2
2. MAGICAL places 2 parallel fingers per diff-pair PMOS instead of 1
3. Each finger has its own device GDS cell with different well/tap structure
4. The nf=2 device geometry produces a different n-well/p-substrate interface
5. Magic extraction interprets this geometry as electrically connecting vdda
   (n-well potential) to gnda (p-substrate) — `equiv "gnda" "vdda"`
6. All PMOS source/bulk terminals are extracted onto `gnda` (since vdda ≡ gnda)
7. The extracted subckt drops `vdda` because it is equiv to the substrate node

### 3.2 Secondary: Device count split (8 → 10)

nf > 1 causes MAGICAL to instantiate multiple physical device fingers. Magic
extraction sees each finger as a separate device:

```
Source (nf=1):               Extracted (nf=2):
  xm0 (diff_pair PMOS, w=7.52, nf=1)  →  X3 (w=3.76) + X4 (w=3.76)
  xm2 (diff_pair PMOS, w=7.52, nf=1)  →  X8 (w=3.76) + X9 (w=3.76)
```

Each nf=2 PMOS is extracted as two w=3.76 devices (half the original width,
since total W is preserved across fingers). Netgen's merge pass combines 2 of
the 4 back into merged devices but still produces 8 vs 8 with net mismatches
— because the merged devices have their terminals on `gnda` instead of `vdda`.

### 3.3 Tertiary: Net mismatch despite merge

Even after Netgen merges 2 devices to bring the count to 8 vs 8, LVS fails
because:

- **PMOS terminals are on wrong net**: All PMOS source/bulk = `gnda`, should
  be `vdda`. No amount of device merging can fix wrong terminal connectivity.
- **The `vdda` net doesn't exist in the extracted topology**: extracted subckt
  has only 5 ports; the source has 6. Netgen can't match nets that don't exist
  in the extracted circuit.

## 4. Why nf=2 Triggers Collapse While nf=1 (cand_0031) Doesn't

| Aspect | nf=1 (PASS) | nf=2 (FAIL) |
|--------|------------|------------|
| Diff-pair fingers per device | 1 | 2 |
| Diff-pair GDS cell count | 2 (xm0, xm2) | 4 (2 fingers × 2 devices) |
| Per-finger width | 7.52µm | 3.76µm |
| Device well structure | single-finger cell | multi-finger with different well/tap |
| Extraction well resolution | correct (n-well → vdda, p-sub → gnda) | collapsed (n-well ≡ p-sub → gnda) |

The nf parameter changes the MAGICAL device instantiation from a single-finger
cell to a multi-finger arrangement. The multi-finger cell has different
well-tap placement and n-well geometry. Magic extraction appears unable to
correctly resolve the n-well/p-substrate boundary for the nf=2 cell geometry.

## 5. Failure Classification

```
Primary failure:  well/substrate extraction collapse
  Symptom:        equiv "gnda" "vdda", PMOS S/B on gnda
  Trigger:        diff_pair_nf 1→2
  Mechanism:      nf=2 device geometry changes well/tap structure;
                  Magic extraction merges n-well into p-substrate domain
  DRC detectable: no (DRC=0 in both cases)

Secondary failure: device count split
  Symptom:        extracted 10 MOS vs source 8 MOS (2→4 diff-pair fingers)
  Trigger:        nf > 1 causes MAGICAL multi-finger instantiation
  Mechanism:      Magic extraction sees each finger as separate device

Tertiary failure: net mismatch
  Symptom:        LVS fails after Netgen merge
  Mechanism:      PMOS terminals on wrong net (gnda instead of vdda);
                  extracted circuit missing vdda net entirely
```

## 6. Trust Status

| Flag | Value |
|------|-------|
| `trust_assigned` | `false` |
| `usable_for_supervised_positive_training` | `false` |
| `usable_for_parasitic_modeling` | `false` |
| `usable_only_as_failure_case` | `true` |
| `failure_category` | `nf_triggered_well_substrate_extraction_collapse` |

## 7. Boundaries

- This taxonomy covers only `diff_pair_nf` perturbation. Other nf parameters
  (load_nmos_nf, bias_pmos_nf, etc.) may behave differently.
- The well/substrate collapse mechanism for nf=2 is the same CLASS of failure
  as NMCNR MOS-only and var_m01 multi+1, but the trigger (nf vs multi) differs.
- PEX data exists for both failed candidates but is NOT trust-safe (equiv gnda-vdda
  invalidates parasitic capacitance network).
- `cand_0031` remains the only reviewed SMCNR positive baseline.
