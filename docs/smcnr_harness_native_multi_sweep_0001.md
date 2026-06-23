# SMCNR Harness-Native Multi Sweep 0001

**Date**: 2026-06-23
**Status**: PASS under MOS-only DRC/LVS/PEX gate

## 1. Purpose

This sweep re-runs the invalidated `multi +1` experiment on the restored
AnalogHarness-native path:

```text
state.json values -> SpiceCandidateCompiler -> LayoutVerificationAdapter.run()
```

The old simplified MAGICAL/Magic sweep results are not used for conclusions
here. `var_ref_000` is included only as the calibrated baseline reference and
is not counted as a new sample.

## 2. Environment

```text
magic: /home/qlf/IOT/scripts/env/bin/magic
magic --version: 8.3.483
netgen-lvs: /usr/bin/netgen-lvs
PDK_ROOT: /home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9
SKY130A: /home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A
```

Batch root:

```text
generated/smcnr_variants/harness_native_sweep_multi_0001/
```

## 3. Method

The exact `cand_0031` sizing values were loaded from:

```text
reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json
```

Each sweep point changes exactly one `*_multi` variable. `nf` is intentionally
excluded. No post-layout simulation or PVT rerun is performed in this sweep.

Positive gate criteria for this report:

```text
DRC_COUNT=0
LVS_MODE=mos_only_projection
NET_RENAMES_USED=yes
CONNECTIVITY_LVS_MATCH=yes
NETGEN_EXIT_STATUS=0
PEX_CAPS > 0
```

## 4. Results

| Candidate | Perturbation | DRC | LVS mode | Net renames | LVS match | Netgen | PEX caps | PEX total | Trust status |
|---|---:|---:|---|---|---|---:|---:|---:|---|
| `var_ref_000` | baseline exact `cand_0031` | 0 | `mos_only_projection` | yes | yes | 0 | 37 | 80.9459 fF | reference only |
| `sweep_multi_01_bias_tail` | `bias_tail_multi 2 -> 3` | 0 | `mos_only_projection` | yes | yes | 0 | 37 | 80.9459 fF | review candidate |
| `sweep_multi_02_bias_ref` | `bias_ref_multi 1 -> 2` | 0 | `mos_only_projection` | yes | yes | 0 | 37 | 80.9459 fF | review candidate |
| `sweep_multi_03_second_stage_pmos` | `second_stage_pmos_multi 10 -> 11` | 0 | `mos_only_projection` | yes | yes | 0 | 37 | 80.9459 fF | review candidate |
| `sweep_multi_04_second_stage_nmos` | `second_stage_nmos_multi 10 -> 11` | 0 | `mos_only_projection` | yes | yes | 0 | 37 | 80.9459 fF | review candidate |
| `sweep_multi_05_diff_pair` | `diff_pair_multi 1 -> 2` | 0 | `mos_only_projection` | yes | yes | 0 | 37 | 80.9459 fF | review candidate |
| `sweep_multi_06_load_nmos` | `load_nmos_multi 1 -> 2` | 0 | `mos_only_projection` | yes | yes | 0 | 37 | 80.9459 fF | review candidate |

All six single-variable perturbation points pass the same MOS-only DRC/LVS/PEX
gate as `var_ref_000`.

## 5. Trust Decisions

`var_ref_000`:

```text
usable_for_supervised_positive_training=false
usable_for_parasitic_modeling=false
usable_only_as_failure_case=false
candidate_for_parasitic_modeling_review=false
```

Each sweep point:

```text
usable_for_supervised_positive_training=false
usable_for_parasitic_modeling=false
usable_only_as_failure_case=false
candidate_for_parasitic_modeling_review=true
```

The sweep points are therefore not promoted into the training-positive pool by
this report. They are only candidates for later parasitic-modeling review or
dataset import.

## 6. Interpretation

The earlier simplified-pipeline conclusion that `multi +1` immediately causes
substrate collapse is invalid for SMCNR. With the calibrated Harness-native
path, all six tested `multi +1` points pass the MOS-only gate.

However, the PEX cap count and total capacitance are identical across all
points. That means this sweep proves gate robustness of the Harness-native
path, but it does not yet prove useful geometry or parasitic diversity. The
next audit should compare generated device parameters and layout geometry to
confirm whether the `multi` perturbations are materially reflected downstream.

## 7. Artifacts

Structured results:

```text
generated/smcnr_variants/harness_native_sweep_multi_0001/batch_results.json
```

Per-candidate evidence:

```text
generated/smcnr_variants/harness_native_sweep_multi_0001/<candidate>/sweep_result.json
generated/smcnr_variants/harness_native_sweep_multi_0001/<candidate>/evidence_layout_verification.json
generated/smcnr_variants/harness_native_sweep_multi_0001/<candidate>/layout/summary.md
generated/smcnr_variants/harness_native_sweep_multi_0001/<candidate>/layout/lvs_mos_projection/summary.md
```

## 8. Boundaries

- This is MOS-only projection evidence only.
- This is not passive-aware/full-native passive LVS evidence.
- This does not include post-layout simulation or PVT.
- Passing sweep points are not automatically training-positive.
- Identical PEX totals mean the batch should not yet be treated as a diverse
  parasitic-modeling dataset.
