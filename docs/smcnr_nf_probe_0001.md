# SMCNR nf Probe 0001

**Date**: 2026-06-23
**Status**: completed; both nf candidates failed MOS-only LVS

## Summary

This probe tested whether `diff_pair_nf 1 -> 2` can pass the calibrated
AnalogHarness-native path:

```text
state.json values -> SpiceCandidateCompiler -> LayoutVerificationAdapter.run()
```

The run used Magic `8.3.483` from `/home/qlf/IOT/scripts/env/bin/magic`.
No post-sim or PVT was run. No candidate is promoted to training-positive.

Artifacts:

```text
generated/smcnr_variants/harness_native_sweep_nf_0001/
```

## Results

| Candidate | Change | Status | Failed stage | Source MOS | Extracted MOS before merge | Netgen devices | PEX caps | PEX total |
|---|---|---|---|---:|---:|---:|---:|---:|
| `sweep_nf_01_diff_pair_keep_w` | `diff_pair_nf 1 -> 2`, `diff_pair_w=7.52` | fail | `mos_only_projection_lvs` | 8 | 10 | 8 vs 8, mismatch | 29 | 46.3999 fF |
| `sweep_nf_02_diff_pair_const_total_w` | `diff_pair_nf 1 -> 2`, `diff_pair_w 7.52 -> 3.76` | fail | `mos_only_projection_lvs` | 8 | 10 | 8 vs 8, mismatch | 30 | 44.4039 fF |

Both candidates completed layout/extraction far enough to produce extracted
SPICE and PEX summaries, but Netgen LVS failed with both net and device
mismatches.

## Key Evidence

- `nf=2` is preserved into the compiled candidate netlist and MAGICAL MOS-only
  projection input.
- Magic extraction splits the two diff-pair PMOS devices into four physical
  extracted devices, so extracted raw MOS count becomes 10 while source remains
  8.
- Netgen reports `Class SMCNR_SE_2st_AMP_flat: Merged 2 devices`, then still
  fails LVS with net/device mismatches.
- Extracted subckt ports drop `vdda`; the extracted subckt begins with:

```text
.subckt SMCNR_SE_2st_AMP_flat gnda vin vip ibias vout
```

- Extracted PMOS bodies/sources are tied to `gnda` in the failed nf runs, so
  this is not a training-safe layout.

For `sweep_nf_01_diff_pair_keep_w`, each split diff-pair PMOS extracts as
`w=3.76 l=8.24`, which is half of the original `7.52` width. For
`sweep_nf_02_diff_pair_const_total_w`, each split device extracts as
`w=1.88 l=8.24`, half of the adjusted `3.76` width.

## Trust Decision

```text
usable_for_supervised_positive_training=false
usable_for_parasitic_modeling=false
usable_only_as_failure_case=true
```

The nf candidates are useful as failure-case evidence for nf semantics and LVS
debugging, not as positive parasitic-modeling samples.

## Interpretation

`diff_pair_nf=2` is not a safe "just change the field" operation in the current
SMCNR Harness-native flow. It changes physical extraction behavior, triggers
multi-finger splitting, and breaks MOS-only LVS. The constant-total-width
variant does not fix the LVS failure.

This directly answers the师兄-facing question: yes, nf changes the front-end and
extraction semantics, and in the current flow it creates a source/extracted
device-count split before Netgen merge. The final LVS still fails.

## Boundaries

- This is MOS-only projection evidence only.
- This is not passive-aware/full-native passive LVS evidence.
- PEX exists for failed candidates, but PEX is not trust-safe without LVS.
- No post-layout simulation or PVT was run.
- `cand_0031` remains the only reviewed positive SMCNR baseline.
