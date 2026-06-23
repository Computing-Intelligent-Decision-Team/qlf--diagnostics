# SMCNR multi Geometry Audit 0001

**Date**: 2026-06-23
**Status**: audit complete

## Summary

This audit checks whether the six `multi +1` candidates in the calibrated
Harness-native batch actually create downstream layout/extraction/PEX diversity.

Batch audited:

```text
generated/smcnr_variants/harness_native_sweep_multi_0001/
```

Structured audit output:

```text
generated/smcnr_variants/harness_native_sweep_multi_0001/multi_geometry_audit_0001.json
```

## Stage Verdicts

| Candidate | Variable | Compiled source | MAGICAL input | MOS-only LVS source | LVS normalized source | Extracted devices | Geometry indicators | PEX graph | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| `sweep_multi_01_bias_tail` | `bias_tail_multi 2 -> 3` | preserved | preserved | preserved | normalized | normalized | unresolved artifact-hash-only change | ignored | gate pass but no confirmed parasitic diversity |
| `sweep_multi_02_bias_ref` | `bias_ref_multi 1 -> 2` | preserved | preserved | preserved | normalized | normalized | unresolved artifact-hash-only change | ignored | gate pass but no confirmed parasitic diversity |
| `sweep_multi_03_second_stage_pmos` | `second_stage_pmos_multi 10 -> 11` | preserved | preserved | preserved | normalized | normalized | unresolved artifact-hash-only change | ignored | gate pass but no confirmed parasitic diversity |
| `sweep_multi_04_second_stage_nmos` | `second_stage_nmos_multi 10 -> 11` | preserved | preserved | preserved | normalized | normalized | unresolved artifact-hash-only change | ignored | gate pass but no confirmed parasitic diversity |
| `sweep_multi_05_diff_pair` | `diff_pair_multi 1 -> 2` | preserved | preserved | preserved | normalized | normalized | unresolved artifact-hash-only change | ignored | gate pass but no confirmed parasitic diversity |
| `sweep_multi_06_load_nmos` | `load_nmos_multi 1 -> 2` | preserved | preserved | preserved | normalized | normalized | unresolved artifact-hash-only change | ignored | gate pass but no confirmed parasitic diversity |

## Evidence Details

The `multi` values are preserved in:

```text
case/*.sp
layout/layout_mos_projection_case/SMCNR_SE_2st_AMP_layout_mos_only.sp
layout/lvs_mos_projection_case/SMCNR_SE_2st_AMP_mos_only.sp
```

After connectivity normalization, the `multi` parameters are removed from:

```text
layout/lvs_mos_projection/SMCNR_SE_2st_AMP_source.connectivity.spice
layout/lvs_mos_projection/SMCNR_SE_2st_AMP_extracted*.spice
```

All six candidates still pass MOS-only DRC/LVS/PEX, but all six have the same
normalized extracted device properties as `var_ref_000`.

PEX numeric comparison against `var_ref_000`:

```text
cap_edge_value_signature_same_as_ref=true
cap_count=37
total_ff=80.9459
```

Raw GDS, `.ext`, and extracted SPICE file hashes differ, but the normalized
cap-edge/value signature and extracted MOS AD/AS/PD/PS/W/L properties do not.
The hash differences are therefore not enough to claim useful parasitic
diversity.

## Conclusion

The `multi +1` perturbations are real at the front-end and MAGICAL input levels,
but the current Harness-native MOS-only LVS/PEX path normalizes them away before
trusted extracted-device and PEX evidence.

The correct trust label for these six candidates is:

```text
gate pass but no confirmed parasitic diversity
```

They should not be imported as independent positive parasitic-modeling samples
without a deeper geometry parser or a flow change that preserves `multi`
semantics into extracted geometry.

## Boundaries

- This audit does not invalidate the MOS-only gate pass result.
- This audit does invalidate treating these six points as confirmed diverse PEX
  samples.
- No candidate is promoted to training-positive.
- No post-layout simulation or PVT was run.
- `cand_0031` remains the sole reviewed positive SMCNR baseline.
