# Codex Review: AH-SMC-023 SMCNR Geometry Gap Fill

## Review Status

**Accepted with required wording and reference corrections.**

AH-SMC-023 successfully fills the main artifact gap from AH-SMC-022 by
regenerating an SMCNR `.ext` from the local pinned-shapes GDS. This makes the
SMCNR/Fan_SMC comparison materially stronger.

Fan_SMC remains **failure-case only**.

## Verified Evidence

| Check | Result |
| --- | --- |
| SMCNR `.ext` regenerated | Present at `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_023/SMCNR_SE_2st_AMP_flat.ext` |
| Extraction command captured | `_extract.tcl` and `smcnr_extract.log` are present |
| SMCNR substrate | `substrate "gnda"` |
| SMCNR equiv records | None found in regenerated `.ext` |
| SMCNR extracted ports | `vdda gnda vin vip ibias vout` all present |
| SMCNR extracted NMOS bodies | 3/3 tied to `gnda` in regenerated SPICE |
| Fan_SMC contrast | Fan_SMC artifacts show substrate/equiv collapse and missing `gnda`/`vdda` ports |
| Trust boundary | Correctly remains failure-case only for Fan_SMC |

## Required Corrections

### 1. Unify the Fan_SMC comparison reference

The AH-SMC-023 report mixes two Fan_SMC references:

- AH-SMC-021 baseline: `substrate "net31"` with 4 equiv records.
- Earlier baseline/control artifacts: `substrate "vout"` with 2 equiv records.

Both support the same high-level conclusion: Fan_SMC collapses and loses
`gnda`/`vdda`. But one table should not silently combine them.

Required fix:

> Name the exact Fan_SMC reference artifact used in each comparison table.

Recommended wording:

> Fan_SMC collapse is stable across references: earlier control artifacts show
> `substrate "vout"` with 2 equiv records; AH-SMC-021 baseline shows
> `substrate "net31"` with 4 equiv records; AH-SMC-021 guardring shows
> `substrate "net050"` with 3 equiv records. All lose `gnda`/`vdda` and fail
> LVS.

### 2. Do not imply AH-SMC-023 reran SMCNR LVS

AH-SMC-023 regenerated SMCNR `.ext` and SPICE. I did not find a new Netgen LVS
run log for this regenerated extraction. The SMCNR LVS PASS statement remains
supported by the existing reproducibility package, not by a new AH-SMC-023
Netgen run.

Required fix:

> SMCNR LVS PASS is inherited from the reviewed cand_0031 reproducibility
> evidence; AH-SMC-023 adds regenerated `.ext`/SPICE evidence.

### 3. Soften "Magic correctly resolves substrate"

The regenerated `.ext` proves that under this extraction run, SMCNR substrate
is named `gnda` and no equiv records appear. It does not prove global physical
correctness of Magic substrate semantics.

Use:

> Magic resolves SMCNR substrate to `gnda` under the current setup.

not:

> Magic correctly resolves substrate.

### 4. Keep H6 at `CANDIDATE_STRONG / Medium`

AH-SMC-023 strengthens H6 substantially, but the report correctly keeps H6 at
`CANDIDATE_STRONG / Medium` because no controlled causal isolation has been
performed. Do not upgrade H6 to proven/root cause yet.

### 5. Fix the geometry-stats ratio text

The stats script prints:

> Fan_SMC diff.drawing: 128 (3.2x more)

but `128 / 56 = 2.29`, matching the report's 2.3x table. The script text should
be corrected if it is retained as an artifact.

## Accepted Interpretation

AH-SMC-023 now supports:

- `.pin=-1` is not sufficient to cause collapse.
- SMCNR can extract with `substrate "gnda"`, zero equiv records, preserved
  ports, and 3/3 NMOS bodies tied to `gnda`.
- Fan_SMC collapse persists across multiple variants/reference artifacts.
- The most plausible current explanation is layout/topology/diffusion-domain
  complexity, not `.pin`, simple Netgen renames, or a missing top-level psub tap.
- H6 should remain `CANDIDATE_STRONG / Medium`, not final root cause.

AH-SMC-023 does **not** prove:

- the exact Fan_SMC shape or primitive causing collapse,
- that Magic must be patched,
- that MAGICAL must be patched,
- that layout complexity alone is sufficient/necessary,
- that Fan_SMC is usable for reward, training, post-sim, or parasitic modeling.

## Recommended Next Task

Run **AH-SMC-024: Fan_SMC collapse localization by comparable substrate graph**.

Goal: move from "Fan_SMC is more complex" to "these exact Fan_SMC shapes/nets
cause substrate/equiv collapse."

Minimum requirements:

1. Do not modify MAGICAL, Magic, Netgen, controller, reward, or closure logic.
2. Use one canonical Fan_SMC reference for the main comparison, preferably
   AH-SMC-021 baseline, and list earlier `vout` references only as supporting
   stability evidence.
3. Build a substrate/equiv graph from Fan_SMC `.ext`:
   - substrate anchor,
   - equiv records,
   - all devices touching the substrate/equiv net,
   - all ports lost into the substrate/equiv net,
   - layer/node names around `vout`, `vdda`, `gnda`, `net31`, `net050`.
4. Cross-reference those nodes back to GDS/layer shapes when possible.
5. Compare against SMCNR `.ext` graph from AH-SMC-023.
6. Output:
   - `docs/ah_smc_024_fan_smc_substrate_graph_localization.md`
   - `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_024/ah_smc_024_records.json`

Stop condition: no patch recommendation until the collapse graph identifies a
specific local mechanism rather than only broad layout complexity.

