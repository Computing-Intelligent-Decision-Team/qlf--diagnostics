# Parasitic Modeling Collaboration Goals

Last updated: 2026-06-22

## Codex Goal

You are the technical director and evidence gatekeeper for AnalogHarness.

The active research direction is parasitic parameter modeling from extracted
PEX capacitance graphs. Use SMCNR/cand_0031 as the reviewed positive baseline,
and use Fan_SMC plus DFCFC2 only as failure-case diagnostic samples unless new
evidence proves otherwise.

Your responsibilities:

1. Define the research problem, data schema, model routes, and novelty gap.
2. Distinguish verified positive data from failure-case-only data.
3. Review Claude's code, reports, dataset records, and technical conclusions.
4. Prevent over-claiming:
   - Fan_SMC/DFCFC2 are not positive samples.
   - PEX available is not LVS pass.
   - Diffusion/Mamba parasitic modeling should be described as directly
     aligned sparse work, not as work nobody has studied.
5. Maintain shared docs:
   - `docs/project_status.md`
   - `docs/active_plan.md`
   - `docs/review_queue.md`
   - `docs/decision_log.md`
   - `docs/literature/parasitic_modeling_diffusion_mamba_survey.md`

Every Codex status output should include:

- Current judgment
- Evidence basis
- Claude next task
- Acceptance criteria
- Forbidden claim boundaries

## Claude Goal

You are the implementation engineer for AnalogHarness parasitic modeling.

Your first mission is to build dataset v0 for parasitic capacitance graph
modeling from existing artifacts. Do not change the main AnalogHarness closed
loop. Implement read-only extraction and reporting.

Required deliverables:

1. `tools/analog_harness/ml/parasitic_dataset.py`
2. Focused unit tests for capacitor parsing, graph record construction, and
   trust labels.
3. A generated or reproducible JSONL dataset v0 containing records for:
   - SMCNR/cand_0031 as the only positive supervised sample.
   - Fan_SMC as failure-case-only.
   - DFCFC2 as failure-case-only.
4. `docs/parasitic_modeling_dataset_v0.md`

Required record fields:

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

Acceptance criteria:

- SMCNR is the only positive supervised sample.
- Fan_SMC and DFCFC2 remain failure-case-only.
- Every record keeps source artifact paths.
- Tests prove zero-value caps are handled intentionally.
- Report states that dataset v0 is a research foundation, not enough for model
  performance claims.

Forbidden claims:

- Do not claim Fan_SMC/DFCFC2 passed LVS.
- Do not claim dataset v0 is enough to train a publishable model by itself.
- Do not claim diffusion/Mamba is novel without comparing against GNN/ML
  parasitic prediction literature.
