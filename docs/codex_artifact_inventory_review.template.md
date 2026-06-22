# Codex Artifact Inventory Review Template

Copy this template to a dated review note after Claude Code produces
`docs/dfcfc2_smc_artifact_inventory.md`.

Suggested filename:

```text
docs/codex_artifact_inventory_review_YYYY_MM_DD.md
```

The review decides whether old MAGICAL- artifacts are strong enough to become
AnalogHarness diagnostics fixtures. It does not decide that DFCFC2 or Fan_SMC
are permanently failing.

## Review Metadata

| Field | Value |
| --- | --- |
| Reviewer | Codex |
| Review date | YYYY-MM-DD |
| Inventory reviewed | `docs/dfcfc2_smc_artifact_inventory.md` |
| Checklist used | `docs/codex_artifact_inventory_review_checklist.md` |
| Positive baseline | `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json` |

## Structure Gate

| Gate | Pass/Fail | Notes |
| --- | --- | --- |
| Scan metadata filled |  |  |
| Commands are read-only |  |  |
| DFCFC2 rows or explicit none-found statement |  |  |
| Fan_SMC/Fan_SMC_Pin_3 rows or explicit none-found statement |  |  |
| Artifact rows use absolute paths |  |  |
| Artifact rows use allowed values |  |  |
| No training-safe claim |  |  |

If any gate fails, stop promotion and return the inventory to Claude Code.

## Accepted Artifacts

| Artifact ID | Circuit | Evidence strength | Diagnostic target | Accepted use | Notes |
| --- | --- | --- | --- | --- | --- |
| A001 | DFCFC2 | direct log | `lvs_failure_taxonomy` | parser fixture | Fill from inventory |

Allowed `Accepted use` values:

- `parser fixture`
- `trust-gate fixture`
- `documentation only`
- `manual review only`

## Weak Or Rejected Artifacts

| Artifact ID | Circuit | Reason | Required follow-up |
| --- | --- | --- | --- |
| A002 | Fan_SMC | path reference only | recover artifact or rerun |

## Provisional Trust Inputs

For each proposed negative sample, record the exact input that should be passed
to `decide_sample_trust(...)`.

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

## Trust Gate Result

| Sample | usable_for_reward | usable_for_post_sim | usable_for_training | usable_for_parasitic_modeling | usable_only_as_failure_case | Reasons |
| --- | --- | --- | --- | --- | --- | --- |
| `<sample-id>` | false | false | false | false | true | `lvs_not_matched` |

Do not mark `usable_for_training` true for old MAGICAL- artifacts unless DRC,
LVS, PEX, post-sim, PVT, and evidence scope are all backed by direct local or
curated artifacts.

## First Negative Fixture Decision

| Field | Value |
| --- | --- |
| Selected sample |  |
| Selected LVS artifact |  |
| Failure category |  |
| Why this is the first fixture |  |
| Test to write | `test_dfcfc2_or_smc_lvs_failure_maps_to_failure_case` |
| Controller integration allowed now? | no |

## Return-To-Claude Items

- Item 1:
- Item 2:
- Item 3:

## Review Decision

Choose one:

- `accept_for_first_negative_fixture`
- `return_to_claude_for_more_evidence`
- `documentation_only_no_fixture_yet`

Decision:

Rationale:
