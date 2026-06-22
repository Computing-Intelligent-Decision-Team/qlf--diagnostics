# DFCFC2 and SMC Diagnostics Mapping

This note defines how prior DFCFC2 and Fan_SMC work from
`references/MAGICAL-` should be mapped into AnalogHarness diagnostics. It is a
coordination document only; it does not claim those circuits are permanently
failing or training-safe.

## Purpose

AnalogHarness is the primary closed-loop framework. DFCFC2 and Fan_SMC should
continue to be debugged, but their intermediate failures should also become
structured evidence for the Harness.

Use `docs/trust_gate_evidence_contract.md` as the field-level contract for
mapping diagnostics into trust decisions and evidence-like outputs.
Use `docs/smcnr_cand0031_evidence_audit.md` as the positive-baseline audit
record for comparing DFCFC2 and Fan_SMC blocker samples.

Use the current SMCNR package as the positive baseline:

- Design: `smcnr_se_2st_amp`
- Candidate: `cand_0031`
- Reference evidence:
  `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/`
- Closure claim: `L6_post_layout_pvt`
- Main verification scope: `mos_only_projection`
- Passive evidence scope: `full_passive_inclusive_gds_lvs`, backfilled from
  curated passive artifacts

Use DFCFC2 and Fan_SMC as pressure-test cases while they are being repaired.
They are not "give up" cases. They are current blocker cases that should become
more useful as they move from failed runs to stress tests and eventually to
passing candidates.

## Source Artifact Classes

The prior MAGICAL- work produced several useful artifact classes:

| Old artifact class | Meaning | AnalogHarness target |
| --- | --- | --- |
| Magic DRC log | Whether the layout is DRC clean and which rules fail | `artifact_verifier` diagnostics and `EvidencePacket.metrics.drc_count` |
| Magic extracted raw SPICE | PEX and extracted connectivity source | `pex_structuring` and layout verification artifacts |
| PEX/parasitic summary | Structured capacitor counts and per-node capacitance | `parasitic_summary.json` and `usable_for_parasitic_modeling` |
| Netgen LVS report | Match/fail status plus device/net/property mismatch details | `lvs_diagnosis.json` and `lvs_failure_taxonomy` |
| A/B experiment directories | Evidence for whether a repair changed the failure mode | `evidence_validity_report.json` and redesign feedback |
| Harness/risk decisions from experiments | Prior sample trust decisions | `sample_trust_gate` input comparison |

## Mapping Rules

1. Do not import old artifacts as proof of AnalogHarness closure by themselves.
   Treat them as diagnostic inputs until they are replayed or represented in
   AnalogHarness evidence.
2. Preserve the distinction between PEX availability and LVS correctness.
   PEX can exist for samples that are not usable for reward or training.
3. Preserve the distinction between MOS-only LVS, formal passive abstraction,
   and full passive-inclusive GDS LVS.
4. Record whether an artifact is directly present, summarized, backfilled, or
   only referenced by an absolute/generated path.
5. Keep failed samples useful by assigning them a failure taxonomy and a trust
   decision instead of discarding them.

## Candidate Trust Outcomes

Diagnostics should produce a trust decision with these separate flags:

| Flag | Meaning |
| --- | --- |
| `usable_for_reward` | Safe to influence optimizer reward |
| `usable_for_post_sim` | Safe to run/use post-layout simulation results |
| `usable_for_training` | Safe as a positive training sample |
| `usable_for_parasitic_modeling` | Safe for parasitic modeling or regression |
| `usable_only_as_failure_case` | Useful only as a structured negative/blocker case |

Example current SMCNR positive baseline:

```json
{
  "candidate_id": "cand_0031",
  "drc_clean": true,
  "lvs_match": true,
  "pex_available": true,
  "post_sim_valid": true,
  "pvt_valid": true,
  "usable_for_training": true,
  "evidence_scope": "full_passive_inclusive_gds_lvs"
}
```

Example current DFCFC2/Fan_SMC blocker shape:

```json
{
  "drc_clean": true,
  "pex_available": true,
  "lvs_match": false,
  "usable_for_training": false,
  "usable_only_as_failure_case": true
}
```

## Known Blocker Categories

These categories should be represented in `lvs_failure_taxonomy` instead of
being kept only as prose:

- power-domain short or collapse
- pin label overlap or missing top-port label
- source/extracted net name normalization mismatch
- MOS body/well/substrate semantic mismatch
- MIM/cfmom/native-capacitor mapping failure
- resistor/passive retargeting failure
- device count mismatch
- net count mismatch
- property-only mismatch after connectivity match
- generated artifact missing or not portable

## Initial File Targets

The first implementation should be observation-only and should not change the
controller reward path.

Preferred module location:

```text
tools/analog_harness/diagnostics/
  __init__.py
  pex_structuring.py
  lvs_failure_taxonomy.py
  artifact_verifier.py
  sample_trust_gate.py
```

Preferred generated artifacts:

```text
parasitic_summary.json
lvs_diagnosis.json
evidence_validity_report.json
harness_decision.json
```

## Audit Checklist Before Using A Sample

- Is the candidate ID known and stable?
- Is `state.json` present?
- Is `evidence.jsonl` present?
- Are summary fields backed by local artifacts, curated artifacts, or only
  original `generated/` paths?
- Is the LVS claim MOS-only, formal passive, or full passive-inclusive?
- Is passive evidence original, unsupported, formalized, or backfilled?
- Are post-layout and PVT outputs present and parseable?
- Should the sample be a positive training sample, a parasitic-only sample, or
  a failure case?
