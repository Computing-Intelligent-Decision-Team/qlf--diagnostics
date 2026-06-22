# Codex Review: AH-SMC-020 Non-Device OD Variant Experiment

## Verdict

**Accepted as a negative diagnostic, but H2a downgrade is too strong.**

AH-SMC-020 shows that modifying the 17 outside-device OD candidates did not
change Magic's substrate/equiv records. However, both non-device variants lose
one PFET, so the shape set is not a clean "non-device only" set. This means the
experiment weakens one specific repair idea but does not fully disprove
remap-level semantic aliasing.

## Accepted Findings

### 1. Control is valid

The control reproduces:

- `substrate "vout"`
- `equiv "vout" "vdda"`
- `equiv "vout" "gnda"`
- extracted ports `vinn vinp vout`
- 12 PFET + 12 NFET

### 2. The tested outside-device candidates are not sufficient

Deleting or remapping the 17 candidate shapes leaves substrate/equiv unchanged.
That means those candidate shapes alone are not sufficient to explain the
collapse.

### 3. Tap remap is not an escape hatch

The `65/20 -> 65/44` variant also leaves substrate/equiv unchanged. This
matches the expectation that `tap.drawing` still participates in substrate
semantics.

## Required Corrections

### 1. Mark both non-device variants as device-damaged

Severity: high

Both `delete_nondev` and `remap_to_tap` extract only 23 MOS devices:

- control: 12 PFET + 12 NFET
- delete: 11 PFET + 12 NFET
- remap-to-tap: 11 PFET + 12 NFET

Therefore the 17-shape set is not cleanly outside device recognition. The
records should include:

```json
"device_recognition_damaged": true
```

for both modified variants.

### 2. H2a should be narrowed, not broadly weakened

Severity: medium

The result weakens this specific subclaim:

> The 17 currently identified outside-device OD shapes are sufficient to cause
> substrate collapse.

It does not fully weaken H2a:

> MAGICAL OD -> Sky130 diff semantic aliasing contributes to collapse.

The remaining 111 device-box OD shapes and the fact that one "outside" shape
affects PFET recognition keep H2a alive as an adapter/primitive semantics issue.

Suggested status:

- H2a outside-device-only sufficient cause: `WEAKENED`
- H2a broader OD semantic aliasing: `REMAINS_CANDIDATE`

### 3. Avoid "collapse must originate from 111 device-active diff shapes"

Severity: medium

That is plausible but not proven. More precise:

> The current evidence points away from the 17-shape outside-device candidate
> set as a sufficient cause and back toward device-active diffusion, primitive
> guard/tap geometry, or the shared OD layer semantics around device boxes.

## Recommended Next Task

Run AH-SMC-021 as a read-only PFET-loss and primitive-provenance audit before
any more masking.

Required outputs:

- `docs/ah_smc_021_pfet_loss_primitive_provenance.md`
- `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_021/ah_smc_021_records.json`

Required checks:

1. Identify exactly which PFET disappears in AH-SMC-020 variants.
2. Determine which of the 17 modified shapes caused that PFET loss.
3. Map that shape back to source instance, primitive GDS, and MAGICAL OD
   provenance if possible.
4. Classify whether the "outside-device" shape is actually primitive guard/tap
   geometry missing from the device layout box.
5. Produce a corrected classification:
   - device active
   - primitive guard/tap but outside layout_box
   - true top-level non-device OD
   - unknown

## Stop Gate

No further GDS mask/rewrite experiment should run until the PFET-loss source is
identified. No MAGICAL source modification is authorized.
