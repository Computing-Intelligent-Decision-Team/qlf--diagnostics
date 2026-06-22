# SMCNR cand_0031 Evidence Audit

This note records the local evidence audit for the packaged
`smcnr_se_2st_amp/cand_0031` positive baseline. It distinguishes summary
claims, local curated artifacts, generated-only references, and backfilled
passive evidence.

## Scope

| Field | Value |
| --- | --- |
| Design ID | `smcnr_se_2st_amp` |
| Circuit | `SMCNR_SE_2st_AMP` |
| Candidate | `cand_0031` |
| Package root | `reproducibility/smcnr_se_2st_amp/` |
| Positive baseline state | `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json` |
| Evidence JSONL | `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/evidence.jsonl` |
| Candidate index | `reproducibility/smcnr_se_2st_amp/all_candidates/candidate_index.csv` |

## Package Type

This is a curated reproducibility package, not the full original `generated/`
tree. `reproducibility/smcnr_se_2st_amp/README.md` says the full local run was
about 563 MB, while this package is about 2.7 MB because bulk GDS variants,
`.ext` files, and transient logs were intentionally excluded.

Implication for diagnostics:

- Summary/state fields may be auditable from curated JSON/Markdown/SPICE files.
- Many artifact paths in `state.json` still point to original Windows or
  `generated/` locations.
- Missing raw generated files should be classified as generated-only references
  unless they are also present in the curated package.

## Summary Claims

`run_summary/summary.json` locally reports:

| Field | Value |
| --- | --- |
| `best_candidate` | `cand_0031` |
| `best_closure_level` | `L6_post_layout_pvt` |
| `verification_scope` | `mos_only_projection` |
| `best_passive_aware_scope` | `full_passive_inclusive_gds_lvs` |
| `best_full_passive_inclusive_gds_lvs_proven` | `true` |

`all_candidates/candidate_index.csv` locally contains 38 candidate rows. The
L6 candidates are `cand_0026` through `cand_0031`; the indexed best candidate
row for `cand_0031` records:

| Field | Value |
| --- | --- |
| `closure_level` | `L6_post_layout_pvt` |
| `pre_sim` | `pass` |
| `layout_verification` | `pass` |
| `passive_aware_lvs` | `pass` |
| `post_sim` | `pass` |
| `pvt_sim` | `pass` |
| `drc_count` | `0` |
| `lvs_match` | `yes` |
| `pex_total_cap_ff` | `71.4964` |
| `pvt_passed_corners` | `3` |
| `full_passive_inclusive_gds_lvs_proven` | `True` |

## EvidencePacket Audit

`state.json` records five evidence stages:

| Stage | Status | Scope | Key local metrics |
| --- | --- | --- | --- |
| `pre_sim` | `pass` | `mos_only_projection` | pre-layout metrics present |
| `layout_verification` | `pass` | `mos_only_projection` | `drc_count=0`, `lvs_match=yes`, `netgen_exit_status=0`, `pex_caps=37`, `pex_total_cap_ff=71.4964` |
| `passive_aware_lvs` | `pass` | `full_passive_inclusive_gds_lvs` | `full_passive_inclusive_gds_lvs_proven=true`, `native_cap_full_gds_trial_status=pass`, `native_passive_netgen_status=pass` |
| `post_sim` | `pass` | `mos_only_projection` | post-layout metrics present |
| `pvt_sim` | `pass` | `mos_only_projection` | `pvt_passed_corners=3`, `pvt_total_corners=3` |

The trust-gate interpretation of this packaged `state.json` is positive:

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

This is the current positive baseline for `usable_for_training=true`, subject
to the path portability caveats below.

## Passive Evidence Backfill

The packaged `state.json` and `evidence.jsonl` do not tell the exact same
passive story:

- `state.json` contains a `passive_aware_lvs` packet with status `pass` and
  scope `full_passive_inclusive_gds_lvs`.
- `evidence.jsonl` contains an earlier `passive_aware_lvs` packet with status
  `unsupported` and scope `mos_only_projection`.
- The earlier unsupported packet says 13 passive-related GDS layer/datatype
  pairs were TBD, Magic reported 13 unknown passive-related layer/datatype
  pairs, raw extraction preserved 0/2 intentional passive devices, and LVS
  preparation dropped 2 unsupported source passive devices.

This should be treated as backfilled passive evidence, not as a contradiction.
The later curated passive artifacts under
`best_candidate/cand_0031/passive_evidence/` are the support for the upgraded
passive claim.

Important passive evidence milestones:

| File | Evidence |
| --- | --- |
| `p05_passive_lvs_evidence_summary.json` | formal passive abstraction passes, but full passive-inclusive GDS LVS is still false at this milestone |
| `p13_native_cap_gencell_summary.json` | native MIM capacitor gencell probe extracts one recognized `sky130_fd_pr__cap_mim_m3_1` device |
| `p16_native_cap_replacement_summary.json` | native cap replacement candidate prepared, but full native capacitor LVS not yet ready |
| `p19_native_passive_capability_summary.json` | original source passive models require native retargeting, not layer remap only |
| `p21_native_passive_retarget_summary.json` | native resistor chain passes, but `xc0` native capacitor is still missing |
| `p25_native_cap_full_gds_trial_summary.json` | native cap full-GDS trial passes DRC/extract and proves full passive-inclusive GDS LVS |
| `p26_native_passive_retarget_summary.json` | native passive retarget is ready, no missing native source passive instances, native passive Netgen status passes |

## Artifact Portability Audit

`state.json` still contains artifact paths that are not all locally portable:

| Stage | Artifact count | Windows absolute paths | Generated-only references |
| --- | ---: | ---: | ---: |
| `pre_sim` | 22 | 6 | 0 |
| `layout_verification` | 4 | 4 | 0 |
| `passive_aware_lvs` | 41 | 13 | 28 |
| `post_sim` | 17 | 6 | 0 |
| `pvt_sim` | 2 | 1 | 0 |

Implication:

- The curated package is enough to audit the main positive baseline fields.
- It is not equivalent to the full original generated run directory.
- Any future diagnostics artifact verifier should mark original Windows paths
  and absent `generated/` paths separately from curated local evidence.

## Current Trust-Gate Baseline

For `cand_0031`, the accepted baseline decision is:

| Flag | Value | Evidence |
| --- | --- | --- |
| `usable_for_reward` | `true` | layout verification + post-sim pass |
| `usable_for_post_sim` | `true` | DRC clean, LVS match, PEX available |
| `usable_for_training` | `true` | reward-usable, PVT valid, full passive-inclusive scope in backfilled state |
| `usable_for_parasitic_modeling` | `true` | DRC clean and PEX available |
| `usable_only_as_failure_case` | `false` | positive baseline |

Do not generalize this decision to other SMCNR candidates, DFCFC2, or Fan_SMC
without separate artifact review.

## Open Follow-Up

- Decide whether to create a small curated fixture from the passive backfill
  transition: `evidence.jsonl` unsupported -> `state.json` full passive pass.
- Decide whether to emit a checked-in sample `evidence_validity_report.json`
  for this packaged state. The artifact-verifier regression test already
  covers the current `state.json` portability counts.
- Use this positive baseline as the comparison point when Claude Code returns
  `docs/dfcfc2_smc_artifact_inventory.md`.
