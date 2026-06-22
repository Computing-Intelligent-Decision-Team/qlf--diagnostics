# SMCNR Positive Baseline Contract

## Identity

The sole reviewed positive circuit baseline is:

| Field | Value |
| --- | --- |
| Design | `smcnr_se_2st_amp` |
| Circuit | `SMCNR_SE_2st_AMP` |
| Candidate | `cand_0031` |
| Evidence class | curated reproducibility package |
| State | `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json` |

`Fan_SMC_Pin_3` and DFCFC2 are different circuits. They must never inherit
this candidate's pass status merely because their names or flow stages are
similar.

## Harness Contract Demonstrated By The Baseline

The positive baseline demonstrates the intended AnalogHarness lifecycle:

```text
candidate proposal
-> sizing legalizer / compiled candidate
-> pre_sim EvidencePacket
-> layout_verification EvidencePacket
-> passive_aware_lvs EvidencePacket
-> post_sim EvidencePacket
-> pvt_sim EvidencePacket
-> candidate state / summary / archive feedback
```

Every `EvidencePacket` preserves:

```text
candidate_id, stage, fidelity, status, verification_scope,
metrics, physical_feedback, artifacts, messages, timestamp
```

Diagnostics for Fan_SMC/DFCFC2 must map into this contract instead of creating
a parallel state or decision system.

## Fresh Positive Evidence

The packaged summary and state currently establish:

| Gate | Reviewed evidence |
| --- | --- |
| Candidate selection | `best_candidate=cand_0031` |
| Closure | `L6_post_layout_pvt` |
| Pre-layout simulation | `pre_sim=pass` |
| Layout verification | `drc_count=0`, `lvs_match=yes`, PEX available |
| Post-layout simulation | `post_sim=pass` |
| PVT | 3/3 corners pass |
| Passive scope | `full_passive_inclusive_gds_lvs` |
| Native resistor | 31-device native resistor chain, Netgen pass |
| Native capacitor | one recognized `sky130_fd_pr__cap_mim_m3_1`, Netgen pass |

Closure level and passive scope are separate claims. The YAML default remains
`mos_only_projection`; full passive scope comes from later curated passive
artifacts and must not be inferred from L6 alone.

## Backfill Rule

The original packaged `evidence.jsonl` records an earlier unsupported
`passive_aware_lvs` probe. The curated `state.json` upgrades that stage to
`pass/full_passive_inclusive_gds_lvs` using later passive artifacts, especially:

- `p25_native_cap_full_gds_trial_summary.json`
- `p26_native_passive_retarget_summary.json`

Therefore the positive passive result is accepted as **backfilled evidence**.
Reviews must preserve that provenance; they must not rewrite the earlier event
as if it had originally passed.

## Positive Trust Decision

Fresh evaluation of the packaged state yields:

| Field | Value |
| --- | --- |
| `usable_for_reward` | true |
| `usable_for_post_sim` | true |
| `usable_for_training` | true |
| `usable_for_parasitic_modeling` | true |
| `usable_only_as_failure_case` | false |

This decision is candidate-specific.

## Artifact Caveat

The curated state contains 86 artifact references across five packets. Current
artifact verification classifies 30 as non-portable Windows paths, 28 as
generated-only references, and 28 as missing relative to the repository root.
The package is sufficient to audit the reviewed summary/state/passive
milestones, but it is not the full original generated run tree.

Do not describe the package as a fresh local end-to-end rerun.

## Required Use For Fan_SMC And DFCFC2

Use cand_0031 as:

1. the positive fixture for diagnostics and trust-gate tests;
2. the canonical `EvidencePacket` and candidate-state shape;
3. the stage-by-stage acceptance reference;
4. the example for recording passive evidence scope and backfill provenance.

Do not use it as:

1. proof that another SMC-named circuit passed;
2. permission to copy trust flags into Fan_SMC or DFCFC2;
3. proof that design-specific MAGICAL repairs generalize;
4. a substitute for direct DRC, Netgen, PEX, post-sim, and PVT artifacts.

Fan_SMC and DFCFC2 become positive samples only after independently satisfying
the same evidence gates.
