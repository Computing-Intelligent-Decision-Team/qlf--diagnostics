# Codex Artifact Inventory Final Review

## Review Metadata

| Field | Value |
| --- | --- |
| Reviewer | Codex |
| Review date | 2026-06-20 |
| Inventory | `docs/dfcfc2_smc_artifact_inventory.md` |
| Prior review | `docs/codex_artifact_inventory_review_2026_06_20.md` |
| Checklist | `docs/codex_artifact_inventory_review_checklist.md` |

## Final Gate Results

| Gate | Result | Verification |
| --- | --- | --- |
| Scan metadata and read-only commands recorded | Pass | Metadata includes the canonical-run post/PVT search. |
| DFCFC2 and Fan_SMC evidence present | Pass | Both circuits have direct and structured evidence. |
| Artifact paths are absolute | Pass | 76/76 artifact rows. |
| Local artifacts exist | Pass | 76/76 rows marked local resolve on this machine. |
| Artifact classes are allowed | Pass | 76/76 rows use template values. |
| Diagnostic targets are allowed | Pass | 76/76 rows use template values. |
| Evidence strengths are allowed | Pass | 76/76 rows use template values. |
| H006 corrected | Pass | Corrected `magical_case/` path exists. |
| DRC and missing-evidence claims scoped | Pass | DRC caveat and audited-canonical-run wording are explicit. |
| Trust reasons follow the contract | Pass | Only stable trust-gate reason codes are used. |
| No training-safe claim | Pass | Both candidates remain failure-only samples. |

Rows with no applicable failure category use an em dash. This is accepted as
an explicit not-applicable display value and does not affect machine ingestion
of rows that carry diagnostic categories.

## Evidence Decisions

### Fan_SMC Priority Fixture

Selected diagnostic run:

```text
/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/
fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/
```

Accepted direct evidence:

- Netgen reports 24 source and 24 extracted devices.
- Netgen reports 18 source and 39 extracted nets.
- Netgen concludes `Netlists do not match`.
- PEX is present, but the run is not reward-, post-simulation-, or
  training-safe.
- The run is a C0-removed diagnostic control, not the original AnalogGym
  Fan_SMC circuit.

This is the first small parser/trust-gate fixture because it cleanly proves the
rule that matching device counts do not imply LVS equivalence. Formal Fan_SMC
closure work must return to the original circuit and use this run only as a
differential diagnosis.

### DFCFC2 Follow-Up Fixture

`mim_proxy_full_pipeline_with_lvs_diagnosis` remains the strongest composite
negative sample: observed Magic DRC count 0 in a partially remapped run, PEX
present, and direct device/net LVS mismatch. It follows Fan_SMC in the formal
attack order.

## Trust Decision

The accepted old artifacts support diagnostics and failure-case fixtures only.
They do not support AnalogHarness closure, reward, post-layout simulation,
training safety, or full passive-inclusive LVS claims.

## Final Decision

Decision: `accept_for_first_negative_fixture`

Controller/reward integration allowed now: **no**

Next implementation task:

```text
test_dfcfc2_or_smc_lvs_failure_maps_to_failure_case
```

The test should begin with the small Fan_SMC Netgen mismatch snippet, then map
the resulting LVS diagnosis into a trust input whose output includes
`usable_for_training=false` and `usable_only_as_failure_case=true`.
