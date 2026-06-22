# Trust Gate Evidence Contract

This contract defines how PEX/LVS diagnostics should map into AnalogHarness
evidence and trust decisions. It is observation-only until a later reviewed
integration explicitly wires it into controller, reward, or closure-level code.

## Primary AnalogHarness Schema

AnalogHarness currently represents candidate evidence with `EvidencePacket`:

```text
candidate_id
stage
fidelity
status
verification_scope
metrics
physical_feedback
artifacts
messages
timestamp
```

Diagnostics should preserve this shape. New PEX/LVS reliability data should be
represented as metrics, artifacts, or messages on evidence-like outputs before
it is promoted into any reward or redesign feedback.

## EvidencePacket Stage Mapping

| Stage | Required status meaning | Key metrics for trust gate | Key artifacts |
| --- | --- | --- | --- |
| `layout_verification` | DRC/LVS/PEX result for the layout verification run | `drc_count`, `lvs_match`, `pex_caps` | Magic DRC log, Netgen LVS report, extracted SPICE, PEX summary |
| `passive_aware_lvs` | Passive-inclusive LVS claim, if available | `full_passive_inclusive_gds_lvs_proven` | passive evidence summary, passive-aware Netgen report |
| `post_sim` | Post-layout simulation validity | simulation pass/fail metrics | post-layout ngspice output |
| `pvt_sim` | PVT sweep validity | `pvt_passed_corners`, `pvt_total_corners` | PVT sweep outputs |
| `diagnostics` | Observation-only parser/trust-gate result | trust flags and failure taxonomy | diagnostics JSON outputs |

The `diagnostics` stage is a proposed observation-only stage. It should not
change closure level or reward until reviewed separately.

## Diagnostics Outputs

Preferred structured outputs:

| Output | Producer | Purpose |
| --- | --- | --- |
| `parasitic_summary.json` | `pex_structuring` | Count capacitors and summarize per-node capacitance |
| `lvs_diagnosis.json` | `lvs_failure_taxonomy` | Classify LVS pass/fail and mismatch category |
| `evidence_validity_report.json` | `artifact_verifier` | Record artifact presence, portability, and generated-only references |
| `harness_decision.json` | `sample_trust_gate` | Record trust flags and reasons |

These outputs may be generated later under `generated/` or attached as artifact
paths in an evidence-like packet. They should remain reproducible from raw or
curated artifacts.

Expected artifact verifier statuses:

| Status | Meaning | Trust implication |
| --- | --- | --- |
| `present` | Artifact exists locally or under the reviewed repo root | Eligible for local evidence review |
| `generated_only_reference` | Path points to an absent `generated/` artifact | Needs artifact recovery or rerun |
| `not_portable` | Path is an absolute path from another environment, such as a Windows drive path | Needs curated copy, path translation, or rerun |
| `missing` | Path is neither present nor recognized as a generated-only or portability case | Cannot support a trust upgrade |

For Windows absolute paths, `artifact_verifier` should include
`reason="windows_absolute_path"`.
For artifact values that are metadata strings rather than usable paths,
`artifact_verifier` may include `reason="invalid_path_text"`.

Minimum `evidence_validity_report.json` shape:

```json
{
  "candidate_id": "cand_0031",
  "packet_count": 2,
  "artifact_count": 4,
  "status_counts": {
    "present": 1,
    "generated_only_reference": 1,
    "not_portable": 1,
    "missing": 1
  },
  "artifacts": {
    "summary": {
      "path": "curated/summary.json",
      "status": "present",
      "portable": true
    }
  },
  "stage_reports": {
    "layout_verification": {
      "artifact_count": 1,
      "status_counts": {
        "present": 1
      },
      "artifacts": {
        "summary": {
          "path": "curated/summary.json",
          "status": "present",
          "portable": true
        }
      }
    }
  }
}
```

When the input is a full `state.json`, `verify_state_artifacts(...)` is the
preferred diagnostics entry point because it preserves `candidate_id` and then
delegates to stage-level EvidencePacket artifact verification.

## Trust Gate Input

The minimal trust-gate input is:

```json
{
  "candidate_id": "cand_0031",
  "drc_clean": true,
  "lvs_match": true,
  "pex_available": true,
  "post_sim_valid": true,
  "pvt_valid": true,
  "evidence_scope": "full_passive_inclusive_gds_lvs"
}
```

Allowed `evidence_scope` values:

- `full_passive_inclusive_gds_lvs`
- `formal_passive_abstraction_with_gds_mos_bridge`
- `mos_only_projection`
- `unknown`

Do not upgrade `unknown`, missing, generated-only, or summary-only evidence to
`true` without direct local or curated artifacts.

## Trust Gate Output

The trust gate must keep these flags separate:

```json
{
  "candidate_id": "cand_0031",
  "evidence_scope": "full_passive_inclusive_gds_lvs",
  "usable_for_reward": true,
  "usable_for_post_sim": true,
  "usable_for_training": true,
  "usable_for_parasitic_modeling": true,
  "usable_only_as_failure_case": false,
  "reasons": []
}
```

Expected decision rules:

| Flag | Minimum evidence |
| --- | --- |
| `usable_for_post_sim` | DRC clean, LVS match, and PEX available |
| `usable_for_reward` | `usable_for_post_sim` and valid post-layout simulation |
| `usable_for_training` | reward-usable, PVT-valid, and `full_passive_inclusive_gds_lvs` scope |
| `usable_for_parasitic_modeling` | DRC clean and PEX available |
| `usable_only_as_failure_case` | not training-usable, but still diagnostically useful |

`usable_only_as_failure_case` does not mean the circuit is impossible to close.
It means the current evidence should only be used as a structured blocker or
negative fixture.

## Reason Codes

Initial allowed reason codes:

- `drc_not_clean`
- `lvs_not_matched`
- `pex_missing`
- `post_sim_invalid`
- `pvt_invalid`
- `scope_not_full_passive_inclusive_gds_lvs`
- `artifact_missing`
- `artifact_not_portable`
- `generated_only_reference`
- `invalid_path_text`
- `summary_only_evidence`

Reason codes should be machine-stable. Explanatory prose belongs in
`messages`, review notes, or inventory notes.

## Positive Baseline

The current positive baseline is:

```text
reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json
```

This state may include passive-aware evidence backfilled from curated passive
artifacts. Reviews must say when a passive claim is backfilled rather than
originally present in the first `evidence.jsonl` packet.

## DFCFC2/Fan_SMC Mapping

Old MAGICAL- artifacts should first enter this contract as negative or blocker
fixtures:

```json
{
  "candidate_id": "dfcfc2_or_smc_probe",
  "drc_clean": true,
  "lvs_match": false,
  "pex_available": true,
  "post_sim_valid": false,
  "pvt_valid": false,
  "evidence_scope": "unknown"
}
```

This shape is acceptable only when the corresponding DRC/LVS/PEX fields are
supported by direct local artifacts or explicitly marked unknown. It must not
be promoted to training-safe status without fresh evidence.

## Promotion Rules

Before diagnostics influence controller or reward behavior:

1. Claude Code must produce an artifact inventory.
2. Codex must review the inventory with
   `docs/codex_artifact_inventory_review_checklist.md`.
3. Codex must select a first negative fixture or return the inventory for more
   evidence.
4. A focused diagnostics test must pass.
5. Controller/reward integration must be proposed as a separate reviewed task.
