# MAGICAL Sky130 Adapter Agent Rules

## Project Goal

The long-term goal is to replace MAGICAL's default mockPDK flow with a real
open-source Sky130 PDK flow. MAGICAL should eventually generate layouts using
real Sky130 layer, techfile, LEF, and GDS mappings, then enter Magic DRC and
Netgen LVS verification.

## Current Progress

- `examples/inverter_sky130_try` can run with
  `sky130_fd_pr__nfet_01v8` and `sky130_fd_pr__pfet_01v8` device names.
- `flow/python/DesignDB.py` supports Sky130 MOS device-name recognition.
- `convert_sky130_netlist.py` can convert an xschem Sky130 inverter netlist to
  MAGICAL-readable format.
- `generated/sky130PDK_trial` can be read by MAGICAL and used for the inverter
  trial flow.
- `remap_gds_to_sky130.py` can generate
  `examples/inverter_sky130_try/inverter_core.sky130.gds`.
- MAGICAL `CO` is mapped to Sky130 `licon1.drawing` on GDS `66/44`.
- Local Sky130 `sky130A.lyp` and `sky130A.magicrc` have been found.

## Working Principles

- Prefer small, reversible, verifiable changes.
- Do not do a large MAGICAL flow refactor in one step.
- Do not directly overwrite `examples/mockPDK`.
- Do not directly overwrite `examples/sky130PDK` unless explicitly requested.
- Prefer writing outputs to `generated/` or `docs/`.
- Do not commit automatically.
- After each change, explain which files changed, how to test, and what success
  looks like.

## Important Paths

- `examples/inverter_sky130_try/`
- `examples/sky130PDK/`
- `generated/sky130PDK_trial/`
- `docs/sky130_adapter/`
- `tools/sky130_adapter/`
- `flow/python/DesignDB.py`

## Current Focus

- Magic DRC automation.
- DRC log analysis.
- GDS layer remap validation.
- Magic extraction.
- Netgen LVS.
- Gradual migration from the mockPDK-compatible trial PDK to a real Sky130 PDK
  interface.

## Prohibited Actions

- Do not delete existing test files.
- Do not delete `inverter_core.sky130.gds`.
- Do not modify the Docker image.
- Do not claim real Sky130 DRC-clean adaptation is complete.
- Do not treat layer/datatype remapping as equivalent to DRC clean.
- Do not treat `examples/sky130PDK` remaining a mockPDK copy as the final goal.

## AnalogHarness Workflow Rules

- Treat AnalogHarness as the primary closed-loop framework. Do not build a
  parallel harness unless explicitly requested.
- Preserve the main flow shape:
  sizing/GRPO -> legalizer -> candidate netlist -> pre-layout simulation ->
  MAGICAL layout -> DRC/LVS/PEX -> post-layout simulation/PVT ->
  `EvidencePacket` -> reward/redesign feedback.
- Add PEX/LVS reliability work as an incremental diagnostics/trust-gate layer
  under AnalogHarness, not as a replacement for `tools/analog_harness`.
- Prefer observation-only integration first: produce structured diagnostics and
  trust decisions before changing reward, closure level, or controller behavior.
- Keep DFCFC2/Fan_SMC history in `references/MAGICAL-` as prior experiment
  evidence and pressure-test material. Do not move, delete, or rewrite those
  artifacts from this repository.

## Evidence Audit Rules

- Treat `SMCNR_SE_2st_AMP/cand_0031` as the sole reviewed positive circuit
  baseline. Its governing contract is
  `docs/smcnr_positive_baseline_contract.md`.
- Never conflate `SMCNR_SE_2st_AMP` with `Fan_SMC_Pin_3`. The former is the
  curated positive baseline; the latter is a separate circuit that must earn
  every DRC/LVS/PEX/post-sim/PVT/trust result from its own artifacts.
- Reuse cand_0031's `EvidencePacket`, state, stage-gate, passive-scope, and
  trust-decision schema. Do not copy its pass statuses to another candidate.
- Always distinguish report claims from locally auditable artifacts.
- For SMCNR, audit these first:
  `reproducibility/smcnr_se_2st_amp/run_summary/summary.json`,
  `best_candidate/cand_0031/state.json`, `evidence.jsonl`,
  `all_candidates/candidate_index.csv`, layout summaries, passive evidence,
  post-layout outputs, and PVT corner evidence.
- Do not equate `best_closure_level = L6_post_layout_pvt` with full native
  passive LVS evidence. Closure level and passive evidence scope are separate
  claims.
- Distinguish these scopes explicitly:
  `mos_only_projection`, `formal_passive_abstraction_with_gds_mos_bridge`, and
  `full_passive_inclusive_gds_lvs`.
- When passive evidence is backfilled from artifacts, say so. In the packaged
  SMCNR evidence, `state.json` may contain the backfilled passive pass while
  `evidence.jsonl` can still show an earlier unsupported passive probe.
- Treat the uploaded `reproducibility/` tree as a curated reproducibility
  package, not as the full original `generated/` run tree. Missing bulk logs,
  `.ext` files, and original generated paths are expected unless explicitly
  archived.
- Watch for portability issues in artifacts, including Windows/WSL absolute
  paths, `generated/...` paths that are not present locally, and UTF-8 BOM in
  CSV/JSON files.

## Diagnostics And Trust Gate Direction

- The intended module direction is:
  `LayoutVerificationAdapter` raw artifacts -> diagnostics ->
  `EvidencePacket`/trust decision -> reward/redesign feedback.
- Preferred future module location:
  `tools/analog_harness/diagnostics/`.
- Candidate diagnostics should cover:
  Magic PEX structuring, Netgen LVS failure taxonomy, artifact verification,
  and sample trust gating.
- Trust decisions should separately track:
  `usable_for_reward`, `usable_for_post_sim`, `usable_for_training`,
  `usable_for_parasitic_modeling`, and `usable_only_as_failure_case`.
- Never claim a sample is training-safe only because PEX exists. PEX success,
  LVS match, post-layout simulation validity, PVT validity, and evidence scope
  must be evaluated separately.
