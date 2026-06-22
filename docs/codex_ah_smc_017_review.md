# Codex Review: AH-SMC-017 Geometry Localization

## Verdict

**Accepted with boundary corrections.**

AH-SMC-017 provides the strongest localization so far for Fan_SMC's
`vout/vdda/gnda` collapse. The evidence supports H2 as the primary current
candidate:

- Magic `.ext` reports `substrate "vout"`.
- Magic `.ext` reports `equiv "vout" "vdda"` and `equiv "vout" "gnda"`.
- The psub component includes `gnda`, `vdda`, and `vout` when `diff.drawing` is
  included.
- The diagnostic graph loses the `vdda/vout` overlap when `diff.drawing` is
  excluded.
- The reported path traverses diffusion/contact stacks around M20/M22/M23,
  whose bodies collapse to `vout`.

This is enough to prioritize diffusion/psub geometry over Netgen setup,
renames, or a `.pin=-1` single-cause patch.

## Required Boundary Corrections

### 1. "Without diffusion" is graph diagnosis, not re-extraction

Severity: medium

AH-SMC-017 should state explicitly that the no-diff result comes from
`psub_substrate_geometry.json` graph analysis, not from a modified GDS followed
by Magic extraction. It proves diffusion is necessary in the diagnostic graph,
but it does not yet prove that a specific GDS mask will remove Magic's `.ext`
`equiv` records.

Correct wording:

> The no-diff graph diagnostic removes the vdda/vout overlap from the psub
> component. A real GDS masking/re-extraction experiment is still required
> before claiming the Magic `.ext` records can be removed.

### 2. Do not say SMCNR GDS is missing

Severity: low

SMCNR packaged GDS files exist locally under:

- `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/gds/`

What is missing for direct apples-to-apples comparison is the original SMCNR
`.ext` and exact original generated LVS case tree/logs. D2 should be phrased as:

> blocked on SMCNR `.ext` / exact extraction artifacts, not all GDS artifacts.

### 3. "Connects all diffusions" is too broad

Severity: low

The current evidence shows that the audited psub-connected component reaches
the specific vout/vdda/gnda-connected diffusion/contact network. Avoid saying
it connects "all diffusions" unless the script has proven every diffusion
rectangle is in the same component.

## D1 Proposal Review

**Approved as a diagnostic-only experiment with stricter scope.**

D1 should not be a broad 128-rectangle diff mask. That would likely destroy
device recognition and produce a result that is hard to interpret. Instead, run
the smallest reversible set of variants:

1. `bottom_psub_stripe_mask`: mask only the horizontal bottom diff stripe
   `[-1050, -450, 15050, -350]`.
2. `path_contact_stack_mask`: mask only the diff/contact participation around
   the localized M22/M23/M20 path segment.
3. `control_noop_copy`: copy GDS, re-extract without masking, prove the
   experiment harness reproduces the same `.ext` substrate/equiv records.

Each variant must record:

- input GDS SHA256
- output GDS SHA256
- mask region and layers
- Magic extraction command
- `.ext` substrate line
- `.ext` equiv lines
- extracted `.subckt` ports
- MOS device count before/after
- whether device recognition was destroyed

Interpretation:

- If `equiv vout<->gnda/vdda` disappears but MOS devices vanish, the test is
  diagnostic but not a repair.
- If `equiv` disappears while most MOS devices remain, H2 becomes strongly
  actionable.
- If `equiv` remains after bottom stripe masking, the bridge is not only the
  bottom psub stripe and the path-local masks become more important.

## Updated Hypothesis State

| Hypothesis | Status |
| --- | --- |
| H1 `.pin=-1` sole root cause | Disproven |
| H2 diffusion/psub geometry | Primary candidate, high confidence |
| H3 routing/met5 contamination | Secondary candidate |
| H4 Netgen/LVS setup divergence | Downgraded |

## Next Task

Run AH-SMC-018 as the approved diagnostic-only layout mask/re-extract
experiment.

Required outputs:

- `docs/ah_smc_018_diffusion_mask_experiment.md`
- `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_018/ah_smc_018_records.json`

Strict limits:

- Do not modify MAGICAL source.
- Do not overwrite previous artifacts.
- Do not claim closure, LVS pass, reward safety, training safety, or repair.
- Treat any masked GDS as a diagnostic specimen only.

## Stop Gate

After AH-SMC-018, Codex must review whether any result is interpretable before
authorizing further layout-side or MAGICAL-side changes.
