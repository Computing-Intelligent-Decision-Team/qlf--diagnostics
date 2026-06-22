# Codex Review: AH-SMC-022 SMCNR vs Fan_SMC Extraction Semantics Diff

## Review Status

**Partially accepted with one blocking scope correction.**

AH-SMC-022 correctly reinforces that NMOS `.pin=-1` is not the differentiator
between SMCNR PASS and Fan_SMC FAIL. However, the report overstates the
strength of the "layout complexity is the root differentiator" conclusion.

Fan_SMC remains **failure-case only**.

## Verified Evidence

| Check | Result |
| --- | --- |
| SMCNR positive baseline | Locally available reproducibility package reports LVS PASS |
| SMCNR extracted ports | `vdda gnda vin vip ibias vout` are preserved |
| SMCNR extracted NMOS bodies | Extracted SPICE shows 3/3 NMOS bodies tied to `gnda` |
| SMCNR `.pin` NMOS body entries | 3/3 use fourth-pin `-1` |
| Fan_SMC extracted ports | `gnda` and `vdda` are absent in AH-SMC-021 baseline extraction |
| Fan_SMC `.ext` substrate/equiv | `substrate "net31"` and equiv records merging `net31` with `net050`, `vout`, `vdda`, `gnda` are present |
| Fan_SMC LVS | Fails with `Netlists do not match.` |
| MAGICAL source changes | None claimed in AH-SMC-022 |

## Blocking Correction

### H6 confidence must be downgraded

The report states:

> Circuit scale and layout complexity are the root differentiators.

This is plausible, but not proven at **high** confidence by the available
artifacts. The local SMCNR reproducibility package contains extracted SPICE and
LVS summaries, but no SMCNR `.ext`, Magic extraction log, or diffusion-geometry
graph comparable to Fan_SMC's AH-SMC-017/AH-SMC-021 artifacts.

Therefore AH-SMC-022 can support:

> SMCNR and Fan_SMC differ strongly in scale/topology, and this is a strong
> candidate explanation for why Fan_SMC collapses while SMCNR does not.

It cannot yet prove:

> Layout complexity is the root differentiator.

Required status correction:

| Hypothesis | Current | Corrected |
| --- | --- | --- |
| H6: circuit scale/layout complexity root differentiator | `SUPPORTED`, confidence `High` | `CANDIDATE_STRONG`, confidence `Medium` |

## Additional Required Wording Changes

### 1. Do not claim SMCNR has no `equiv` records unless `.ext` is present

SMCNR extracted SPICE preserves ports and LVS passes, but AH-SMC-022 did not
audit SMCNR `.ext` because no `.ext` file is present in the local
reproducibility package. The report should say:

> No SMCNR substrate/equiv collapse is visible in the packaged extracted
> SPICE/LVS evidence.

not:

> SMCNR has no equiv records.

### 2. Do not say Magic "correctly" resolves physical substrate connectivity

The evidence shows what the current extraction flow produced. It does not prove
that the substrate handling is physically correct for all Sky130 device/tap/well
semantics.

Use:

> Under the current extraction setup, Fan_SMC collapses into a common
> substrate/equiv domain.

not:

> Magic correctly identifies this electrical connection.

### 3. Do not treat SMCNR geometry separation as directly observed

The report describes SMCNR diffusion domains as compact and well-separated.
That is plausible from circuit size and extracted success, but the local
artifact set lacks SMCNR `.ext`/geometry graph evidence comparable to Fan_SMC.

Use:

> SMCNR's smaller device count and preserved extracted connectivity are
> consistent with sufficient geometry separation.

not:

> SMCNR's diffusions are physically well-separated.

## Accepted Interpretation

AH-SMC-022 supports:

- `.pin=-1` is not the differentiator by itself.
- SMCNR proves that NMOS fourth-pin `-1` can coexist with LVS PASS in this
  harness when extraction preserves body connectivity.
- Fan_SMC's failure is not a simple Netgen rename/setup issue.
- Fan_SMC's failure mode remains substrate/equiv collapse under current
  extraction.
- Scale/topology/interleaving is now a strong candidate differentiator, but not
  yet a proven root cause.

AH-SMC-022 does **not** prove:

- the exact geometry mechanism in SMCNR,
- that SMCNR has no `.ext` equiv records,
- that layout complexity alone is sufficient or necessary,
- that Magic or MAGICAL source must be changed,
- that Fan_SMC can be used for reward, training, post-sim, or parasitic model
  training.

## Recommended Next Task

Run **AH-SMC-023: SMCNR geometry artifact gap and comparable geometry audit**.

Goal: decide whether H6 can be upgraded from `CANDIDATE_STRONG` to supported.

Minimum requirements:

1. Do not modify MAGICAL, Magic, Netgen, or controller/reward code.
2. Locate or regenerate SMCNR `.ext` and Magic extraction log if possible from
   packaged GDS and existing extraction Tcl.
3. If regeneration is performed, keep it in a new diagnostics directory and
   record all commands, rc files, and SHA256 values.
4. Build a comparable SMCNR geometry summary:
   - substrate record,
   - equiv records,
   - diff/tap/nwell shape counts,
   - pin overlaps,
   - source/extracted port preservation,
   - NMOS body terminal mapping.
5. Compare that directly against Fan_SMC AH-SMC-021 baseline and guardring
   variants.
6. If SMCNR `.ext` cannot be regenerated reproducibly, mark H6 as
   `CANDIDATE_STRONG` and stop before patch proposals.
7. Output:
   - `docs/ah_smc_023_smcnr_geometry_artifact_gap.md`
   - `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_023/ah_smc_023_records.json`

Stop condition: no new fix proposal until SMCNR and Fan_SMC have comparable
geometry/extraction artifacts.

