# Codex Artifact Inventory Review

## Review Metadata

| Field | Value |
| --- | --- |
| Reviewer | Codex |
| Review date | 2026-06-20 |
| Inventory reviewed | `docs/dfcfc2_smc_artifact_inventory.md` |
| Checklist used | `docs/codex_artifact_inventory_review_checklist.md` |
| Positive baseline | `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json` |

## Findings

1. **High: artifact paths fail the absolute-path gate.** The inventory table
   labels its path column `Absolute path`, but rows A001 through I001 use paths
   relative to the MAGICAL- repository. These must be expanded under
   `/home/qlf/IOT/references/MAGICAL-/` before fixture promotion.
2. **High: several rows use values outside the inventory schema.** Examples
   include artifact classes such as `pipeline summary`, `source connectivity
   netlist`, and `lvs_diagnosis`, plus evidence strength `structured markdown`.
   Normalize them to the allowed template values or use `other` with a note.
3. **High: H006 is marked local but is not present at the stated path.**
   `generated/analoggym_adapter_audits/fan_smc_pin_3/run_fan_smc_pin_3_trial.log`
   did not exist during Codex path verification. Correct the path or mark it
   `missing`/`unknown`.
4. **Medium: DRC=0 is stated too strongly for DFCFC2.** The direct log supports
   an observed Magic DRC count of zero, but the same run reports 12 unresolved
   layer/datatype mappings and read warnings. Describe this as `DRC count 0 in
   the audited partially remapped run`, not proof that the layout is fully
   Sky130 DRC clean or that the failure is exclusively LVS-domain.
5. **Medium: exhaustive missing-evidence claims exceed the stated scan depth.**
   The inventory says no post-layout simulation or PVT exists for any run while
   also saying most probe directories were only enumerated, not deeply read.
   Narrow this to `none found in the audited canonical runs` unless an exhaustive
   filename/content search was actually performed and recorded.
6. **Medium: trust-gate reasons mix stable reason codes with diagnostic issue
   codes.** The provisional JSON should contain only contract reason codes such
   as `lvs_not_matched`, `post_sim_invalid`, `pvt_invalid`, and
   `scope_not_full_passive_inclusive_gds_lvs`. Detailed findings such as
   `power_domain_short`, `missing_extracted_ports`, and `route_not_final` belong
   in LVS diagnosis categories or messages unless the contract is expanded in
   a separately reviewed change.

## Structure Gate

| Gate | Pass/Fail | Notes |
| --- | --- | --- |
| Scan metadata filled | Pass | Scanner, date, source, target, and commands are present. |
| Commands are read-only | Pass | Reported commands are discovery/read commands. |
| DFCFC2 rows present | Pass | Canonical and A/B artifacts are inventoried. |
| Fan_SMC rows present | Pass | Canonical and A/B artifacts are inventoried. |
| Artifact rows use absolute paths | **Fail** | Table rows use MAGICAL-relative paths. |
| Artifact rows use allowed values | **Fail** | Custom artifact classes and `structured markdown` occur. |
| No training-safe claim | Pass | Both candidates are explicitly rejected for training. |

Because a required structure gate failed, fixture promotion stops pending a
small inventory correction. This does not invalidate the audited evidence.

## Accepted Evidence After Path Correction

| Artifact ID | Circuit | Evidence strength | Diagnostic target | Accepted use | Notes |
| --- | --- | --- | --- | --- | --- |
| A002 | DFCFC2 | direct log | `artifact_verifier` | trust-gate fixture | Supports observed Magic DRC count 0 with mapping caveat. |
| A008 | DFCFC2 | direct log | `lvs_failure_taxonomy` | parser fixture | Direct Netgen mismatch evidence. |
| A011 | DFCFC2 | structured json | `lvs_failure_taxonomy` | parser fixture | Structured issue taxonomy; inspect schema before ingestion. |
| A013 | DFCFC2 | structured json | `pex_structuring` | trust-gate fixture | Supports PEX availability, not LVS validity. |
| A015 | DFCFC2 | structured json | `sample_trust_gate` | trust-gate fixture | Existing rejection is consistent with current gate. |
| F007 | Fan_SMC | structured json | `lvs_failure_taxonomy` | parser fixture | Supports 24/24 devices but 18/39 net mismatch. |
| F008 | Fan_SMC | direct log | `lvs_failure_taxonomy` | parser fixture | Direct `Netlists do not match` evidence. |
| F005 | Fan_SMC | structured json | `pex_structuring` | trust-gate fixture | Supports PEX availability only. |

## Weak Or Rejected Artifacts

| Artifact ID | Circuit | Reason | Required follow-up |
| --- | --- | --- | --- |
| H006 | Fan_SMC | File absent at inventoried path | Correct path or mark missing/unknown. |
| A001/A012/F004 | Mixed | `structured markdown` is outside allowed strength enum | Use `summary only` unless a structured schema is defined. |
| A017 and A/B directory rows | Mixed | Summary/path-reference evidence cannot drive final trust alone | Keep for documentation/manual review. |

## Provisional Trust Input

```json
{
  "candidate_id": "dfcfc2_mim_proxy_rank1",
  "drc_clean": true,
  "lvs_match": false,
  "pex_available": true,
  "post_sim_valid": false,
  "pvt_valid": false,
  "evidence_scope": "mos_only_projection"
}
```

`drc_clean=true` here means the audited Magic run reported zero DRC errors; it
does not erase the unresolved layer-mapping caveat.

## Trust Gate Result

The current `decide_sample_trust(...)` implementation returns:

| Sample | usable_for_reward | usable_for_post_sim | usable_for_training | usable_for_parasitic_modeling | usable_only_as_failure_case | Reasons |
| --- | --- | --- | --- | --- | --- | --- |
| `dfcfc2_mim_proxy_rank1` | false | false | false | true | true | `lvs_not_matched`, `post_sim_invalid`, `pvt_invalid`, `scope_not_full_passive_inclusive_gds_lvs` |

`usable_for_parasitic_modeling=true` follows the current contract's minimum of
DRC count zero plus available PEX. It means the data may support diagnostic
parasitic analysis; it does not mean the sample is topology-trusted, reward-safe,
post-simulation-safe, or training-safe.

## First Negative Fixture Decision

| Field | Value |
| --- | --- |
| Provisionally selected sample | DFCFC2 `mim_proxy_full_pipeline_with_lvs_diagnosis` |
| Selected LVS artifact | A008 `netgen_lvs_report.out` |
| Failure category | `device_mismatch`, `net_mismatch`; structured diagnosis also records a power-domain short |
| Why this is the first fixture | It combines direct LVS failure, observed DRC count 0, parseable PEX, and an existing rejection decision. |
| Test to write after correction | `test_dfcfc2_or_smc_lvs_failure_maps_to_failure_case` |
| Controller integration allowed now? | no |

Fan_SMC `smc09_no_c0` remains the preferred second fixture for proving that
matching device counts do not imply matching netlists. It is diagnostic-only
because C0 was removed and therefore does not represent the original circuit.

## Return-To-Claude Items

1. Convert every artifact-table path to an absolute path.
2. Normalize artifact class and evidence-strength values to the template enums.
3. Correct H006 and narrow claims of exhaustive missing post-sim/PVT evidence.
4. Keep trust reason codes separate from detailed LVS diagnostic categories.

## Review Decision

Decision: `return_to_claude_for_more_evidence`

Rationale: the underlying DFCFC2 and Fan_SMC evidence is strong enough to pick
the first two negative fixtures provisionally, but mandatory inventory structure
and path-verification gates must pass before the first old-artifact test is
written.
