# Codex Review: AH-SMC-021 `useDeviceSubGuardRing` Probe

## Review Status

**Accepted with scope corrections.**

AH-SMC-021 is a useful, clean A/B diagnostic. The artifact set supports the
main result: `useDeviceSubGuardRing: true` measurably changes MAGICAL P&R
output and Magic extraction, but it does not restore Fan_SMC LVS correctness.

Fan_SMC remains **failure-case only**.

## Verified Evidence

| Check | Result |
| --- | --- |
| MAGICAL source modified | No evidence of source modification in this experiment |
| Config semantic delta | `useDeviceSubGuardRing: true` only; JSON formatting also changed |
| GDS changed | Yes; `place.gds`, `route.gds`, and `init.gds` sizes increase |
| MOS count | Preserved at 24 in both variants |
| Baseline substrate/equiv | `substrate "net31"`; `net31` equated with `net050`, `vout`, `vdda`, `gnda` |
| Guardring substrate/equiv | `substrate "net050"`; `net050` equated with `vout`, `vdda`, `gnda` |
| Extracted gnda/vdda ports | Still absent in guardring variant |
| LVS | Both variants fail with `Netlists do not match.` |
| Trust boundary | Correctly remains `usable_only_as_failure_case: true` |

## Required Corrections

### 1. Do not imply the NMOS `.pin` contract was fixed

The generated `.pin` files still show NMOS fourth pins as `-1` in both
baseline and `useDeviceSubGuardRing: true` variants. The experiment proves
that the guard-ring configuration changes generated geometry/extraction, but
it does **not** repair the NMOS body-pin contract.

Correct wording:

> `useDeviceSubGuardRing` activates a geometry path that affects extraction,
> while NMOS `.pin` fourth entries remain `-1`.

### 2. Soften the "guard rings generated" claim unless geometry is classified

The GDS size increase is strong evidence that the config changed generated
layout. Given the code path, guard-ring generation is plausible. But this
review did not independently classify the added geometry by layer, datatype,
and instance ownership.

Correct wording:

> The GDS size increase is consistent with additional device-level guard/tap
> geometry from the `useDeviceSubGuardRing` path.

### 3. Do not claim Magic extraction is physically correct

The report currently says the substrate connection is physically correct. That
is too strong. The evidence proves what Magic extracted, not that the extracted
short is physically correct for Sky130 device semantics. In CMOS, substrate
coupling, wells, taps, active diffusion, and source/drain junction semantics
must not be collapsed into a simple metal-like short without checking the PDK
extraction rules.

Correct wording:

> Under the current Magic/Sky130 extraction setup, these shapes are still
> collapsed into a common substrate/equiv domain.

### 4. Do not jump straight to "Magic substrate model modification"

The next fix may be in extraction setup, layer/datatype mapping, primitive
generation, tap/well semantics, or Netgen abstraction. A Magic model change is
one possible endpoint, not the next default action.

Correct wording:

> The next step is to compare SMCNR PASS and Fan_SMC FAIL extraction semantics
> at the layer/rule level before proposing Magic or MAGICAL source changes.

## Accepted Interpretation

AH-SMC-021 supports:

- H5 confirmed in the narrow sense:
  `useDeviceSubGuardRing` changes extraction but does not resolve collapse.
- A pure Fan_SMC top-level tap fix is insufficient.
- A pure NMOS `.pin=-1` explanation remains disproven.
- Fan_SMC's failure is now best treated as a substrate/extraction semantics
  mismatch under the current Sky130 remap and Magic extraction setup.

AH-SMC-021 does **not** prove:

- that generated guard-ring geometry is electrically correct,
- that Magic is physically correct,
- that Magic must be patched,
- that MAGICAL source must be patched,
- that Fan_SMC can enter reward/training/post-sim.

## Recommended Next Task

Run **AH-SMC-022: SMCNR-vs-Fan_SMC extraction semantics diff**.

Goal: explain why SMCNR can LVS-pass with NMOS `.pin=-1`, while Fan_SMC still
collapses after guard-ring activation.

Minimum requirements:

1. Do not modify MAGICAL or Magic source.
2. Use SMCNR/cand_0031 only as the positive baseline defined by
   `docs/smcnr_positive_baseline_contract.md`.
3. Compare the exact extraction/LVS setup files used by SMCNR and Fan_SMC.
4. Compare source and extracted ports, device counts, substrate/equiv records,
   and passive abstraction rules.
5. Compare layer/datatype treatment for `diff`, `tap`, `nwell`, `psub`, and
   local interconnect/metal where artifacts exist.
6. If SMCNR `.ext` is missing, state that directly and limit claims to
   available artifacts.
7. Output:
   - `docs/ah_smc_022_smcnr_fan_smc_extraction_semantics_diff.md`
   - `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_022/ah_smc_022_records.json`

Stop condition: no patch recommendation unless the SMCNR/Fan_SMC rule or
artifact difference is locally auditable.

