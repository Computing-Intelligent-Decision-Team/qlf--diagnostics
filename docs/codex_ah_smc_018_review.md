# Codex Review: AH-SMC-018 Diffusion Mask / Re-Extract Experiment

## Verdict

**Accepted as a diagnostic negative result.**

AH-SMC-018 establishes that the tested local masks are not sufficient to remove
Fan_SMC's substrate collapse:

- The no-op control reproduces `substrate "vout"` and
  `equiv "vout" "vdda"/"gnda"`.
- Masking only the bottom psub diffusion stripe removes 3 shapes, preserves 24
  MOS devices, and leaves substrate/equiv unchanged.
- Masking the M20/M22/M23 path region removes 23 diffusion shapes, loses 5 MOS
  devices, and still leaves substrate/equiv unchanged.

This is useful: it prevents us from chasing a single local stripe or one
localized path as the sole cause.

## Accepted Findings

### 1. The control harness is valid

The control copy re-extracts to the same three-port subckt and the same
substrate/equiv records. Therefore the experiment harness itself is usable.

### 2. The bottom psub stripe is not sufficient

The bottom stripe mask preserves all 24 MOS devices but does not change the
collapse. This means the bottom stripe alone is not sufficient to explain
`vout/vdda/gnda`.

### 3. The M20/M22/M23 path is not sufficient

The path-stack mask damages device recognition and still does not remove the
collapse. That means the collapse is either distributed across other device
diffusions or caused by a more global layer/primitive/export semantic.

## Boundary Corrections

### 1. Do not say local masks prove diffusion is necessary

Severity: low

AH-SMC-018 does not itself prove diffusion is necessary. AH-SMC-017's graph
diagnostic provided the no-diff evidence. AH-SMC-018 shows that the two tested
local masks are insufficient to eliminate the Magic `.ext` collapse.

### 2. Avoid "clean isolation impossible" as a final claim

Severity: medium

The tested masks failed, but that does not prove no clean diagnostic isolation
exists. It proves these two local masks are insufficient. A semantic mask based
on device-vs-non-device diffusion, implant context, or generated OD route
provenance may still be interpretable.

### 3. Treat path-stack results as damaged-circuit evidence

Severity: medium

Variant C loses 5 MOS devices. Its unchanged substrate/equiv records are
important, but any conclusions from that variant must be marked
`device_recognition_damaged`.

## Updated Hypothesis State

| Hypothesis | Status |
| --- | --- |
| H1 `.pin=-1` sole root cause | Disproven |
| H2 diffusion/psub geometry | Primary candidate, but local-mask unresolved |
| H3 routing/met5 contamination | Secondary |
| H4 Netgen/LVS setup divergence | Downgraded |

## Recommended Next Task

Run AH-SMC-019 as a read-only diffusion semantics/provenance audit, not another
large mask.

Required goal:

1. Trace every `diff.drawing` shape in the psub-connected component back to its
   provenance class:
   - device active diffusion
   - generated substrate tap / psub route
   - MAGICAL route layer 6 / OD artifact
   - pin-shape or label-derived geometry
   - unknown
2. Separate device-recognition-critical diffusion from suspicious non-device
   diffusion.
3. Identify whether Fan_SMC's collapse is caused by an exporter/remap semantic
   issue, a primitive geometry issue, or an unavoidable Magic substrate model
   outcome for this generated layout.

Required outputs:

- `docs/ah_smc_019_diffusion_semantics_provenance.md`
- `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_019/ah_smc_019_records.json`

Suggested checks:

- Compare route GDS layer `6/0 OD` to Sky130 `65/20 diff.drawing`.
- Use per-instance GDS boxes to classify diff shapes by overlap with MOS
  layout boxes.
- Inspect export map entries for MAGICAL internal layer 6.
- Count diff shapes that are outside all device boxes.
- Count diff shapes that overlap top-level psub route / tap geometry.
- If possible, generate a proposed "non-device diff only" mask plan, but do
  not run it until Codex review.

## Stop Gate

Do not authorize MAGICAL source modification or broad GDS masks yet. The next
step is provenance classification of diffusion shapes.
