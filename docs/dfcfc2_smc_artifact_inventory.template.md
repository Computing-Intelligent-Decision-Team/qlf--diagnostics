# DFCFC2/Fan_SMC Artifact Inventory Template

Copy this template to `docs/dfcfc2_smc_artifact_inventory.md` and fill it from
a read-only scan of `/home/qlf/IOT/references/MAGICAL-`.

Do not treat an artifact as proof of AnalogHarness closure by itself. The goal
is to make old MAGICAL- evidence auditable and mappable into AnalogHarness
diagnostics/trust-gate decisions.

## Scan Metadata

| Field | Value |
| --- | --- |
| Scanner | Claude Code |
| Scan date | YYYY-MM-DD |
| Source repo | `/home/qlf/IOT/references/MAGICAL-` |
| Target repo | `/home/qlf/IOT/references/AnalogHarness` |
| Commands run | `rg --files ...`; `find ...`; other read-only commands |
| Files modified | `docs/dfcfc2_smc_artifact_inventory.md` only |

## Executive Summary

- DFCFC2 artifact count:
- Fan_SMC/Fan_SMC_Pin_3 artifact count:
- Strongest negative sample candidate:
- Most common failure category:
- Missing evidence that blocks trust-gate conversion:

## Artifact Inventory

| ID | Circuit | Absolute path | Artifact class | Local status | Failure category | Feeds diagnostic | Evidence strength | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A001 | DFCFC2 | `/home/qlf/IOT/references/MAGICAL-/...` | Netgen LVS report | local | net_mismatch | `lvs_failure_taxonomy` | direct log | Fill exact reason |

Allowed `Circuit` values:

- `DFCFC2`
- `Fan_SMC`
- `Fan_SMC_Pin_3`
- `Other`

Allowed `Artifact class` values:

- `magic_drc_log`
- `magic_extract_log`
- `extracted_raw_spice`
- `netgen_lvs_report`
- `pex_summary`
- `parasitic_summary`
- `risk_report`
- `harness_decision`
- `ab_experiment_dir`
- `other`

Allowed `Local status` values:

- `local`
- `generated_only_reference`
- `missing`
- `not_portable`
- `unknown`

Allowed `Failure category` values:

- `power_domain_short`
- `pin_label_overlap`
- `missing_top_port_label`
- `net_name_normalization_mismatch`
- `body_well_substrate_mismatch`
- `passive_mapping_failure`
- `native_cap_mapping_failure`
- `device_mismatch`
- `net_mismatch`
- `property_mismatch`
- `pex_without_lvs`
- `artifact_missing`
- `unknown`

Allowed `Feeds diagnostic` values:

- `artifact_verifier`
- `lvs_failure_taxonomy`
- `pex_structuring`
- `sample_trust_gate`
- `manual_review`

Allowed `Evidence strength` values:

- `direct log`
- `structured json`
- `summary only`
- `path reference only`
- `inferred`

## Candidate Negative Samples

For each proposed negative sample, fill this block.

### Candidate N1: `<short-name>`

| Field | Value |
| --- | --- |
| Circuit | DFCFC2 or Fan_SMC |
| Candidate/run directory | absolute path |
| Main failure | one failure category |
| DRC status | pass/fail/unknown |
| LVS status | pass/fail/unknown |
| PEX available | yes/no/unknown |
| Post-sim valid | yes/no/unknown |
| PVT valid | yes/no/unknown |
| Suggested trust outcome | `usable_only_as_failure_case` or other |

Required supporting artifacts:

- DRC evidence:
- LVS evidence:
- PEX evidence:
- Notes on missing evidence:

## Open Questions For Codex Review

- Question 1:
- Question 2:
- Question 3:

## Do-Not-Claim List

List anything that should not be claimed from this inventory.

- Do not claim DFCFC2/Fan_SMC is permanently impossible to close.
- Do not claim PEX availability means LVS passed.
- Do not claim a sample is training-safe without DRC/LVS/PEX/post-sim/PVT and
  scope review.
