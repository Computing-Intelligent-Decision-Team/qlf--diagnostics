# Codex Artifact Inventory Review Checklist

Use this checklist when reviewing
`docs/dfcfc2_smc_artifact_inventory.md` from Claude Code.

The review goal is not to prove that DFCFC2 or Fan_SMC can never close. The
goal is to decide whether each old MAGICAL- artifact is strong enough to become
AnalogHarness diagnostics evidence or whether it needs more data.

## Required Inputs

- `AGENTS.md`
- `docs/dfcfc2_smc_diagnostics_mapping.md`
- `docs/dfcfc2_smc_artifact_inventory.md`
- `tools/analog_harness/diagnostics/`
- Current SMCNR positive baseline:
  `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json`

## Review Pass/Fail Gates

### 1. Inventory Structure

- [ ] The scan metadata table is filled.
- [ ] Commands are read-only commands.
- [ ] The inventory has at least one DFCFC2 row or explicitly states none was
  found.
- [ ] The inventory has at least one Fan_SMC/Fan_SMC_Pin_3 row or explicitly
  states none was found.
- [ ] Every artifact row has an absolute path.
- [ ] Every artifact row uses allowed values from the template.
- [ ] No row claims training safety.

If any item fails, return the inventory to Claude Code for correction before
using it as diagnostics input.

### 2. Artifact Evidence Strength

Classify each row:

| Evidence strength | Codex action |
| --- | --- |
| `direct log` | Eligible for parser/test fixture if locally readable |
| `structured json` | Eligible for trust-gate fixture after schema inspection |
| `summary only` | Eligible for documentation, not final trust decision alone |
| `path reference only` | Needs artifact recovery or rerun |
| `inferred` | Manual review only |

### 3. Diagnostic Target Mapping

For each artifact row, verify the diagnostic target:

- `artifact_verifier`: path existence, portability, generated-only references,
  missing artifacts
- `lvs_failure_taxonomy`: Netgen reports, LVS summaries, mismatch summaries
- `pex_structuring`: raw extracted SPICE, PEX summaries, parasitic summaries
- `sample_trust_gate`: candidate-level DRC/LVS/PEX/post/PVT status
- `manual_review`: anything ambiguous, inferred, or missing raw evidence

Rows that map to multiple targets should be split or clearly annotated.

### 4. Trust Gate Pre-Decision

For every proposed negative sample, derive a provisional trust input:

```json
{
  "candidate_id": "<sample-id>",
  "drc_clean": false,
  "lvs_match": false,
  "pex_available": false,
  "post_sim_valid": false,
  "pvt_valid": false,
  "evidence_scope": "unknown"
}
```

Then apply `decide_sample_trust(...)` and inspect:

- `usable_for_reward`
- `usable_for_post_sim`
- `usable_for_training`
- `usable_for_parasitic_modeling`
- `usable_only_as_failure_case`
- `reasons`

Do not upgrade any unknown field to true without a direct artifact.

## First Acceptable Conversion

The first old MAGICAL- conversion should be a small negative fixture, not a
controller integration. It is acceptable when:

- One DFCFC2 or Fan_SMC run directory is identified.
- At least one direct LVS failure artifact is readable.
- DRC status is known or explicitly unknown.
- PEX availability is known or explicitly unknown.
- The sample is classified as `usable_only_as_failure_case`.
- The test uses a small inline fixture or a stable curated text snippet, not a
  large raw generated file.

Preferred first test:

```text
test_dfcfc2_or_smc_lvs_failure_maps_to_failure_case
```

Preferred output shape:

```json
{
  "usable_for_training": false,
  "usable_only_as_failure_case": true,
  "reasons": ["lvs_not_matched"]
}
```

## Return-To-Claude Conditions

Return the inventory for more work if:

- Paths are relative or ambiguous.
- Artifact classes are not assigned.
- Failure categories are guessed without notes.
- PEX availability is claimed without raw SPICE or summary evidence.
- LVS pass/fail is claimed without Netgen report or LVS summary evidence.
- A sample is called training-safe.
- The inventory mixes report claims with locally auditable artifacts.

## Codex Review Output

After review, Codex should produce a short review note using:

```text
docs/codex_artifact_inventory_review.template.md
```

The note should include:

- accepted artifacts
- rejected or weak artifacts
- first negative sample candidate
- required follow-up from Claude Code
- whether to write the first old-artifact diagnostics test
