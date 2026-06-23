# Decision Log

Last updated: 2026-06-22

## Current Judgment

The project should advance parasitic modeling as a trust-aware data problem
before presenting it as a model-performance result.

## Decisions

### D-001: SMCNR/cand_0031 is the only positive baseline

Use SMCNR/cand_0031 as the only reviewed positive data point for reward,
post-sim, training, and parasitic modeling.

Evidence:
- `docs/smcnr_positive_baseline_contract.md`
- `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json`

Boundary:
- Fan_SMC and DFCFC2 must earn their own pass status.

### D-002: Fan_SMC and DFCFC2 are failure-case-only for now

Use Fan_SMC and DFCFC2 for diagnostic pressure tests and failure-case
parasitic graph records. They are not clean supervised labels.

Evidence:
- `docs/fan_smc_dfcfc2_diagnostic_closure.md`
- `docs/dfcfc2_smc_artifact_inventory.md`

Boundary:
- `pex_available: true` is not equivalent to `lvs_match: true`.

### D-003: Literature novelty must be conservative

The project may claim that directly aligned diffusion/Mamba work on analog
extracted PEX capacitance graphs is sparse. It must not claim that ML
parasitic prediction is empty or unstudied.

Evidence:
- ParaGraph uses GNNs for layout parasitics and device parameter prediction.
- MLParest and later work address custom-circuit parasitic estimation.
- Recent surveys cover deep-learning-based capacitance extraction.
- M3 uses Mamba for analog multi-circuit optimization, not directly for PEX
  graph generation.

Boundary:
- Novelty belongs to trust-aware extracted-PEX graph modeling and evaluation,
  not to "ML for parasitics" in general.

## Claude Next Task

When writing dataset or modeling docs, reference these decision IDs instead of
re-litigating sample trust in each file.

## Acceptance Criteria

- New project docs cite D-001/D-002/D-003 where relevant.
- Any future change that upgrades Fan_SMC or DFCFC2 out of failure-case-only
  status must add a new decision with evidence paths.

## Forbidden Claims

- Do not modify a decision silently by changing downstream prose.
- Do not upgrade sample status without a new evidence-backed decision.
