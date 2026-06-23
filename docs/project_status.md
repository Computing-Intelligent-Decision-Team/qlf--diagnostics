# AnalogHarness Project Status

Last updated: 2026-06-22

## Current Judgment

The active research direction is parasitic parameter modeling over extracted
PEX capacitance graphs. The current data foundation is deliberately
trust-aware:

| Circuit/run | Status | Modeling use |
| --- | --- | --- |
| `SMCNR_SE_2st_AMP/cand_0031` | Reviewed positive baseline | Positive supervised sample and schema fixture |
| `Fan_SMC_Pin_3` | LVS-failing diagnostic sample | Failure-case-only parasitic graph and trust-gate pressure test |
| `DFCFC2/AMP_DFCFC2` | LVS-failing diagnostic sample | Failure-case-only parasitic graph and future recovery target |

The safest novelty statement is:

> Existing ML parasitic prediction work is real and non-trivial, especially
> GNN/MLP/DNN approaches. Our gap is a trust-aware analog extracted-PEX graph
> dataset and evaluation path for diffusion or Mamba/SSM modeling of parasitic
> capacitance networks.

## Evidence Basis

- SMCNR/cand_0031 is governed by
  `docs/smcnr_positive_baseline_contract.md`.
- Fan_SMC and DFCFC2 are governed as failure-case references by
  `docs/fan_smc_dfcfc2_diagnostic_closure.md` and
  `docs/dfcfc2_smc_artifact_inventory.md`.
- SMCNR packaged PEX evidence is in
  `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/pex_summary.md`.
- SMCNR has 37 parasitic capacitors and 71.4964 fF total listed capacitance.
  The `vout` connected capacitance is 2.20939 fF. The largest listed capacitor
  is `C31` between `vdda` and `gnda` at 35.8705 fF.
- The `state.json` positive passive result is accepted as backfilled evidence;
  the original `evidence.jsonl` can still show an earlier unsupported passive
  probe.

## Claude Next Task

Build a read-only dataset v0 extractor for parasitic modeling:

1. Parse SMCNR raw extracted SPICE into a graph-ready JSONL record.
2. Parse Fan_SMC and DFCFC2 PEX artifacts as failure-case-only records.
3. Attach trust fields to every record:
   `lvs_status`, `trust_scope`, `usable_for_supervised_positive_training`,
   `usable_for_parasitic_modeling`, and `usable_only_as_failure_case`.
4. Write a short dataset report in `docs/parasitic_modeling_dataset_v0.md`.

## Acceptance Criteria

- SMCNR/cand_0031 is the only record marked
  `usable_for_supervised_positive_training: true`.
- Fan_SMC and DFCFC2 are marked `usable_only_as_failure_case: true`.
- PEX availability is recorded separately from LVS status.
- Every JSONL record includes source artifact paths and a provenance note.
- Dataset code is placed under `tools/analog_harness/ml/` and reuses
  diagnostics helpers where practical.

## Forbidden Claims

- Do not claim Fan_SMC or DFCFC2 is a positive sample.
- Do not claim PEX availability implies LVS pass.
- Do not claim diffusion/Mamba parasitic modeling has never been studied.
- Do not claim SMCNR is a fresh local end-to-end rerun unless a local replay
  report proves that exact chain.
- Do not copy SMCNR trust flags to any other circuit.
