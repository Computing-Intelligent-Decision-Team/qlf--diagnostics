# Codex Review: AH-SMC-016C Setup-Normalized Fan_SMC Rerun

## Verdict

**Accepted with minor record corrections.**

AH-SMC-016C successfully tests the AH-SMC-016B follow-up question: whether an
SMCNR-style rename layer can plausibly normalize Fan_SMC LVS. The answer is no
for the current psub-tap artifact. The extracted topology is already collapsed:

- `.ext` contains `substrate "vout"`.
- `.ext` contains `equiv "vout" "vdda"` and `equiv "vout" "gnda"`.
- Extracted top ports are `vinn vinp vout`, while source ports are
  `gnda vdda vinn vinp vout`.
- Zero of 12 extracted NMOS body terminals resolve to source `gnda`.

This confirms that H4 is not currently an independent root-cause path. Netgen
renames cannot honestly repair a layout extraction that already equates output,
power, and ground.

## Accepted Findings

### 1. Baseline LVS reproduction is valid

The rerun reproduces Fan_SMC LVS failure with 24 vs 24 devices and 18 vs 19 nets.
That keeps the result comparable to the previous psub-tap LVS artifacts.

### 2. Candidate rename map has zero usable entries

The file `candidate_lvs_renames.txt` is comment-only. It is not 0 bytes, but it
contains zero rename entries. That is acceptable, and future scripts should
treat it as "no candidate mappings", not as a literal empty file.

### 3. H4 should be downgraded

SMCNR had clean internal aliases because extraction preserved topology. Fan_SMC
does not: source power/ground and multiple internal source nets are no longer
represented by one-to-one extracted nets. Therefore the absence of an
`lvs_renames.txt` is a symptom of extraction collapse, not an actionable setup
fix.

## Required Minor Corrections

### 1. Do not call the candidate rename file empty

Severity: low

Use:

> comment-only; zero rename entries

instead of:

> empty file

### 2. Separate device-count match from device-class/mapping mismatch

Severity: low

The JSON records say `device_mismatch: true` while also reporting 24 vs 24
devices. This can be confusing. Prefer:

- `device_count_match: true`
- `device_class_count_match: true`
- `device_mapping_or_net_mismatch: true`

The failure is not caused by a raw device-count mismatch.

### 3. Soften "3/18 survive intact"

Severity: low

Only `vinn`, `vinp`, and `vout` appear by name in both source and extracted
netlists. `vout` is not intact because it absorbs `gnda` and `vdda`. Phrase as:

> Only three source net names remain visible in extraction; only `vinn` and
> `vinp` appear plausibly intact, while `vout` is contaminated by power/ground
> equivalence.

## Updated Hypothesis State

| Hypothesis | Status |
| --- | --- |
| H1 `.pin=-1` sole root cause | Disproven |
| H2 diffusion/psub geometry collapse | Primary supported candidate for Fan_SMC |
| H3 routing/met5 co-contamination | Still candidate |
| H4 Netgen/LVS rename setup divergence | Downgraded; not independent for current artifact |

## Next Task

Run AH-SMC-017 as a geometry-level localization task. Do not modify MAGICAL
source yet.

Required goal:

1. Localize which Fan_SMC geometry creates `substrate "vout"` and
   `equiv vout<->vdda/gnda`.
2. Distinguish diffusion/psub overreach from met5/pin-label/routing
   contamination.
3. Produce a minimal, reversible layout-side diagnostic experiment if possible,
   without claiming closure.

Required outputs:

- `docs/ah_smc_017_geometry_localization.md`
- `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_017/ah_smc_017_records.json`

Required checks:

- Trace `.ext` substrate and equiv records to GDS shapes/layers.
- Identify which source nets overlap the psub/tap/diffusion connected
  component.
- Compare with/without diff-layer participation if a diagnostic script already
  exists.
- Check whether M23/M22/M20/M18/M17 vout-body collapse shares a common geometry
  region.
- Keep all trust flags failure-case only.

## Stop Gate

No MAGICAL source patch is authorized. The next valid work is geometry
localization and a diagnostic-only layout-side experiment.
