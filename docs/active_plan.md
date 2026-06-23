# Active Plan: Parasitic Modeling Foundation

Last updated: 2026-06-22

## Current Judgment

The immediate goal is not to train a diffusion or Mamba model yet. The correct
next step is to use the now-repeatable SMCNR replay gate to produce a small
AnalogGym-Opt candidate batch and convert only verified candidates into
trust-labeled parasitic graph records.

## Phase 1: Research Foundation

1. Maintain literature map for ML/GNN parasitic prediction, capacitance
   extraction, Mamba in analog optimization, and diffusion in EDA.
2. Define dataset schema for extracted PEX capacitance graphs.
3. Build dataset v0 from SMCNR, Fan_SMC, and DFCFC2 artifacts.
4. Review dataset records against SMCNR positive contract and Fan_SMC/DFCFC2
   diagnostic closure.
5. Validate SMCNR local replay repeatability and PEX granularity alignment.
6. Request AnalogGym-Opt candidate batches for data expansion using
   `docs/analoggym_opt_data_request.md`.
7. Run AnalogGym-Opt small-batch data production through the AnalogHarness
   replay/trust gate.

## Phase 2: Baseline Modeling

1. Establish non-neural baselines: total capacitance, per-node capacitance,
   largest-edge statistics, degree-weighted capacitance, and source/sink
   grouping.
2. Establish GNN baseline for graph-level and node-level capacitance
   prediction.
3. Treat diffusion as a distribution model for parasitic edge sets, not as a
   first baseline.
4. Treat Mamba/SSM as a sequence model over canonicalized PEX edge streams, not
   as evidence that PEX has passed LVS.

## Dataset V0 Schema

Each JSONL record should contain:

```json
{
  "sample_id": "smcnr_se_2st_amp/cand_0031/lvs_mos_projection",
  "circuit": "SMCNR_SE_2st_AMP",
  "candidate_id": "cand_0031",
  "lvs_status": "pass",
  "trust_scope": "full_passive_inclusive_gds_lvs",
  "usable_for_supervised_positive_training": true,
  "usable_for_parasitic_modeling": true,
  "usable_only_as_failure_case": false,
  "pex_caps": 37,
  "pex_total_cap_ff": 71.4964,
  "parasitic_edges": [
    {"cap_id": "C0", "node_a": "a_2100_n30#", "node_b": "vdda", "cap_ff": 2.63138}
  ],
  "per_node_cap_ff": {"vout": 2.20939},
  "graph_features": {
    "num_nodes": 11,
    "num_edges": 37,
    "largest_cap_ff": 35.8705
  },
  "source_artifacts": []
}
```

## Claude Next Task

Dataset v0 is implemented and reviewed as a research-foundation artifact. SMCNR
local replay is repeatable at the DRC/extract/LVS level. The next Claude task is
to run real AnalogGym-Opt small-batch candidate generation and keep SMCNR replay
as the trust gate:

1. Generate a small real AnalogGym-Opt batch using the contract in
   `docs/analoggym_opt_data_request.md`.
2. Import candidates with `tools/analog_harness/ml/analoggym_importer.py`;
   all imported candidates must remain `trust_assigned=false`.
3. Run each imported candidate through AnalogHarness layout/replay diagnostics.
4. Promote only candidates with their own DRC/LVS/PEX evidence into the
   parasitic dataset.
5. Keep Fan_SMC/DFCFC2 failure-case-only.

## Acceptance Criteria

- `python3 -m unittest` or equivalent focused tests cover SPICE capacitor
  parsing and trust labeling.
- The extractor does not mutate artifact files.
- Zero-value caps are preserved or explicitly tagged; they must not silently
  disappear.
- The generated report states that dataset v0 is too small for final model
  claims.
- AnalogGym-Opt candidate batches are treated as candidate sources, not as
  parasitic ground truth.
- SMCNR local replay repeatability is backed by R1/R2 DRC, extraction, and LVS
  evidence.
- Imported AnalogGym-Opt candidates must remain pre-trust until AnalogHarness
  diagnostics assign evidence-backed trust labels.

## Forbidden Claims

- Do not present dataset v0 as statistically sufficient for model training.
- Do not use Fan_SMC/DFCFC2 failure-case graphs as clean labels.
- Do not hide the fact that Fan_SMC/DFCFC2 LVS failed.
- Do not treat raw PEX count mismatch as a clean training label without
  documenting the extraction settings and granularity.
