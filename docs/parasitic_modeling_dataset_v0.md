# Parasitic Modeling Dataset v0

Last updated: 2026-06-22

## Current Judgment

Dataset v0 is a research foundation, not a training-complete corpus. It is
useful for validating schema, parser behavior, trust labels, and baseline graph
features. It is too small to support model-performance claims.

## Evidence Basis

Generated with:

```bash
python3 -m tools.analog_harness.ml.parasitic_dataset \
  --output generated/parasitic_modeling/dataset_v0.jsonl \
  --summary
```

Focused verification:

```bash
python3 -m unittest tools.analog_harness.tests.test_parasitic_dataset -v
```

The focused test suite covers:

- SPICE capacitor parsing.
- `p` suffix conversion to fF.
- `$ **FLOATING` capacitor comments.
- Zero-value capacitor preservation.
- SMCNR-only positive supervised labeling.
- Fan_SMC/DFCFC2 failure-only labeling.
- DFCFC2 `mim_proxy` count and total matching the audited PEX summary.

## Dataset Records

| Sample | Circuit | LVS | Trust scope | Caps | Total cap | Training-positive |
| --- | --- | --- | --- | ---: | ---: | --- |
| `smcnr_se_2st_amp_cand_0031` | `SMCNR_SE_2st_AMP` | PASS | `full_passive_inclusive_gds_lvs` | 37 | 71.4964 fF | yes |
| `fan_smc_c0_proxy_psub_tap` | `Fan_SMC_Pin_3` | FAIL | `failure_case_only` | 95 | 23.8473 fF | no |
| `fan_smc_c0_proxy_guardring_true` | `Fan_SMC_Pin_3` | FAIL | `failure_case_only` | 92 | 30.0572 fF | no |
| `dfcfc2_mim_proxy` | `AMP_DFCFC2` | FAIL | `failure_case_only` | 103 | 865.0103 fF | no |
| `dfcfc2_mos_only_rerun` | `AMP_DFCFC2` | FAIL | `failure_case_only` | 51 | 34.8776 fF | no |

## Schema

Each JSONL record contains:

```text
sample_id
circuit
candidate_id
lvs_status
trust_scope
usable_for_supervised_positive_training
usable_for_parasitic_modeling
usable_only_as_failure_case
pex_caps
pex_total_cap_ff
parasitic_edges
per_node_cap_ff
graph_features
source_artifacts
provenance_note
```

`parasitic_edges` currently uses:

```text
src
dst
cap_ff
cap_id
```

## Claude Next Task

The next implementation task is to harden dataset v0 into a reviewable
artifact:

1. Add an optional CLI flag that writes a compact summary table next to the
   JSONL file.
2. Add parser support tests for uppercase suffixes and `ff`/`pf` spellings if
   those appear in future artifacts.
3. Add a schema validator test that checks every required field in every JSONL
   record.
4. Keep Fan_SMC and DFCFC2 records failure-case-only unless new LVS/passive
   evidence is added and reviewed.

## Acceptance Criteria

- `generated/parasitic_modeling/dataset_v0.jsonl` can be regenerated from
  current local artifacts.
- SMCNR/cand_0031 remains the only `PASS` and only
  `usable_for_supervised_positive_training: true` record.
- DFCFC2 `mim_proxy` remains aligned with its PEX summary:
  103 caps and 865.01 fF.
- No model experiment claims are made from dataset v0 alone.

## Forbidden Claims

- Do not claim Fan_SMC or DFCFC2 passed LVS.
- Do not claim `usable_for_parasitic_modeling` means training-safe.
- Do not claim dataset v0 proves diffusion or Mamba performance.
- Do not hide that the dataset includes failure-case-only PEX graphs.
