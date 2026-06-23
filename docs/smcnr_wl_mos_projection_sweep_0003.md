# SMCNR W/L MOS-Only Projection Sweep 0003

**Date**: 2026-06-23
**Status**: 3/6 PASS extraction under MOS-only projection

## 1. Method

All candidates use MOS-only netlists (R+C passives stripped before MAGICAL).
Same PDK trial, same Magic 8.3.483, same CIEL sky130A for extraction.

| Candidate | Change | Netlist |
|-----------|--------|---------|
| var_ref_001 | exact cand_0031 repeat | MOS-only |
| wl_001 | diff_pair_w +5% (7.52→7.90) | MOS-only |
| wl_002 | diff_pair_w -5% (7.52→7.14) | MOS-only |
| wl_003 | load_nmos_w +5% (1.5→1.58) | MOS-only |
| wl_004 | diff_pair_l +5% (8.24→8.65) | MOS-only |
| wl_005 | bias_pmos_l -5% (10→9.5) | MOS-only |

## 2. Results

| Candidate | MAGICAL | equiv | MOS count | PEX caps | Status |
|-----------|---------|-------|-----------|----------|--------|
| var_ref_001 | ✅ | 0 | 8 | 37 | PASS |
| wl_001 | ❌ crash | — | — | — | FAIL (Anaroute grid assertion) |
| wl_002 | ❌ crash | — | — | — | FAIL (Anaroute grid assertion) |
| wl_003 | ✅ | 0 | 8 | 37 | PASS |
| wl_004 | ❌ crash | — | — | — | FAIL (Anaroute grid assertion) |
| wl_005 | ✅ | 0 | 8 | 36 | PASS |

### 2.1 Extraction-passing candidates

| Candidate | Change | equiv | MOS | PEX caps | wl_003 PEX diff? |
|-----------|--------|-------|-----|----------|-------------------|
| var_ref_001 | none (baseline) | 0 | 8 | 37 | — |
| wl_003 | load_nmos_w +5% | 0 | 8 | 37 | TBD |
| wl_005 | bias_pmos_l -5% | 0 | 8 | 36 | TBD |

wl_005 shows 36 caps vs 37 — one fewer parasitic capacitor, suggesting the
L perturbation changed the extracted geometry enough to affect parasitic
extraction. This is preliminary evidence of PEX diversity.

### 2.2 MAGICAL crashes

W perturbations (wl_001, wl_002: diff_pair_w ±5%) and L perturbation on
diff_pair (wl_004: diff_pair_l +5%) all crash MAGICAL with the same
Anaroute grid alignment assertion:

```
OVERFLOW: crf 0
python3.7: .../parser.cpp:124: void ANAROUTE::Parser::correctPinNBlkLoc():
  Assertion 'abs(pBox->yl()) % 10 == 0 or abs(pBox->yl()) % 10 == 8' failed.
```

This is the known MAGICAL PDK grid constraint — W/L values must align to
the PDK device cell grid. The cand_0031 values happen to align; perturbing
them breaks alignment.

## 3. Key Findings

1. **MOS-only projection works**: 3/3 non-crashing candidates produce equiv=0,
   clean extraction. Confirms the root cause (passives trigger collapse).

2. **W perturbations crash MAGICAL**: The diff_pair W/L values are at the edge
   of MAGICAL's PDK grid tolerance. Any change breaks placement.

3. **L perturbations on non-diff-pair devices survive**: load_nmos_w and
   bias_pmos_l changes pass through MAGICAL and extraction.

4. **PEX diversity possible**: wl_005 (36 caps) vs var_ref_001 (37 caps)
   suggests real parasitic variation from sizing change.

## 4. Trust Status

| Flag | All candidates |
|------|---------------|
| `trust_assigned` | `false` |
| `usable_for_supervised_positive_training` | `false` |
| `usable_for_parasitic_modeling` | `false` |
| `review_pool` | `true` |

No candidate promoted to training-positive. PEX diversity evidence is
preliminary — requires LVS pass and full connectivity verification.

## 5. Next Steps

1. **Complete LVS for passing candidates**: var_ref_001, wl_003, wl_005
   need full Netgen LVS with lvsNetRenames.
2. **Compare PEX signatures**: cap edge lists, total capacitance,
   per-node capacitance for wl_003 and wl_005 vs var_ref_001.
3. **Explore W-safe perturbation axes**: Only certain sizing parameters
   survive MAGICAL grid constraints. Map the safe perturbation space.
4. **Scale up**: If LVS passes and PEX diversity confirmed, expand to
   more candidates on the safe axes.
