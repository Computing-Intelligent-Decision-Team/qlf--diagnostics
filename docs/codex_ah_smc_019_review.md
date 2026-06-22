# Codex Review: AH-SMC-019 Diffusion Semantics / Provenance Audit

## Verdict

**Accepted with terminology corrections.**

AH-SMC-019 establishes an important adapter-level finding: Fan_SMC's Sky130
`diff.drawing` is a uniform remap of MAGICAL internal `OD` layer 6/0, and that
layer is carrying multiple physical intents. The evidence supports a new
sub-hypothesis:

> H2a: remap-level semantic aliasing contributes to the Fan_SMC substrate
> collapse because MAGICAL OD is exported uniformly as Sky130 active diffusion.

This does not yet prove a repair, but it explains why local diffusion masks in
AH-SMC-018 failed: the suspect geometry is not one small path; it is a broader
OD semantics problem.

## Accepted Findings

### 1. Uniform OD -> diff.drawing mapping is real

The export map explicitly maps MAGICAL `OD` / internal layer 6 to Sky130
`diff.drawing` 65/20 and already records the risk:

> MAGICAL OD may cover both device diffusion and tap semantics; Sky130
> distinguishes diff and tap by datatype.

This aligns with AH-SMC-019's 128-to-128 shape correspondence between route GDS
layer 6/0 and remapped GDS layer 65/20.

### 2. The split-tap pass acknowledges the same semantic problem

`split_sky130_tap_from_diff.py` says MAGICAL uses one internal OD layer for both
MOS active diffusion and guard-ring/substrate-tap diffusion, while Sky130
distinguishes active diff and tap by datatype. That supports the semantic
aliasing diagnosis.

### 3. Non-device diffusion candidates exist

The audit identifies 17 `diff.drawing` shapes outside all MOS boxes. That is
enough to justify a focused proposal around non-device OD provenance.

## Required Corrections

### 1. "Guard ring" must remain inferred

Severity: medium

AH-SMC-019 labels Groups A/B/C as guard rings or nwell structures. The shape
classification supports "outside-device OD-like geometry", but not definitive
function. Use:

- `edge OD frame candidate`
- `non-device OD candidate`
- `guard-ring-like structure`

instead of stating the function as fact.

### 2. Do not claim all non-device diff is electrically responsible yet

Severity: medium

The audit proves non-device diff exists and that OD remap is semantically
aliased. It does not yet prove which of the 17 outside-device shapes directly
maintains the `.ext` `equiv` records. That remains for a controlled
shape-class experiment.

### 3. Be careful with remapping to tap.drawing as a proposed action

Severity: high

Moving non-device `diff.drawing` to `tap.drawing` may not remove substrate
connection; in Sky130, tap is also tied into substrate semantics. It might make
the geometry more correct for some shapes, but it is not guaranteed to remove
`vout/vdda/gnda` equivalence.

The next experiment should compare:

- remove outside-device OD candidates
- remap outside-device OD candidates to `tap.drawing`
- leave device-active OD untouched

and treat all variants as diagnostic only.

## Approved Next Task

Run AH-SMC-020 as a diagnostic-only non-device OD variant experiment.

Required outputs:

- `docs/ah_smc_020_non_device_od_variant_experiment.md`
- `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_020/ah_smc_020_records.json`

Required variants:

1. `control_noop_copy`
   - reproduce AH-SMC-018 control substrate/equiv.

2. `outside_device_od_removed`
   - remove only the 17 outside-device OD/diff candidate shapes.
   - keep all 111 device-box OD shapes.

3. `outside_device_od_to_tap`
   - rewrite only the 17 outside-device OD/diff candidate shapes from 65/20 to
     65/44.
   - keep all 111 device-box OD shapes on 65/20.

4. Optional if time permits: group-specific variants
   - Group A only
   - Group B only
   - Group C only

Each variant must record:

- input/output SHA256
- exact candidate shape bboxes and count
- MOS device count
- extracted `.subckt` ports
- `.ext` substrate line
- `.ext` equiv lines
- Magic short warnings
- whether `vout/vdda/gnda` collapse changed

## Stop Gate

No MAGICAL source change is authorized. No variant may be called a repair.
Masked/remapped GDS files remain diagnostic specimens only.
