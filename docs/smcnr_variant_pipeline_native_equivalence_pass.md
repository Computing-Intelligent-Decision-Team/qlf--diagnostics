# SMCNR Variant Pipeline Native Equivalence Check

**Date**: 2026-06-23
**Status**: PASS for Harness-native MOS-only layout/LVS/PEX gate

## 1. Purpose

This check reran an exact `cand_0031` sizing as `var_ref_000` through the
AnalogHarness-native path instead of the earlier simplified hand-built MAGICAL
pipeline.

The goal was to answer one question:

> Can the variant pipeline reproduce the original SMCNR case-pipeline contract
> before any sizing perturbation is tested?

## 2. Method

The run used the existing AnalogHarness components:

- `HarnessConfig`
- `SizingLegalizer`
- `SpiceCandidateCompiler`
- `LayoutVerificationAdapter.run()`

Input sizing values came from:

`reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json`

Output directory:

`generated/smcnr_variants/harness_native_equivalence/var_ref_000/`

The first attempt failed preflight because `PATH` resolved `magic` to
`/usr/bin/magic` version `8.3.105`, while the harness requires `>=8.3.411`.
The passing run used the same Magic binary recorded by the local replay report:

`/home/qlf/IOT/scripts/env/bin/magic` version `8.3.483`

## 3. Result

| Field | Value |
| --- | --- |
| Candidate | `var_ref_000` |
| Sizing | exact `cand_0031` |
| Layout input mode | `mos_only_projection` |
| Dropped source passives | 2 |
| DRC count | 0 |
| LVS mode | `mos_only_projection` |
| Net renames used | yes |
| Netgen exit status | 0 |
| Connectivity LVS | yes |
| PEX caps | 37 |
| PEX total cap | 80.9459 fF |

Primary summary:

`generated/smcnr_variants/harness_native_equivalence/var_ref_000/layout/summary.md`

MOS-only projection summary:

`generated/smcnr_variants/harness_native_equivalence/var_ref_000/layout/lvs_mos_projection/summary.md`

## 4. Evidence

Netgen report contains:

```text
Circuits match uniquely.
Netlists match uniquely.
```

LVS preparation preserved the original SMCNR rename contract:

```text
a_785_2846#=ibias
a_4024_586#=net53
a_20_494#=outn
a_2100_n30#=outp
a_4345_n10#=outp
```

The generated candidate config preserved:

```json
"connectivityLvsProjection": "mos_only"
```

and retained the five `lvsNetRenames`.

## 5. Interpretation

The earlier simplified fresh-MAGICAL variant pipeline is invalid for sizing
sensitivity claims. The Harness-native path can reproduce the SMCNR MOS-only
case-pipeline contract for exact `cand_0031` sizing when the correct Magic
binary is placed first in `PATH`.

This restores the experimental baseline needed before any perturbation sweep.

## 6. Boundaries

- This result does not add a new positive training sample; it is a reference
  replay under a variant directory.
- This result does not prove any sizing perturbation is safe.
- PEX capacitor count matches the packaged granularity (`37`), but total
  capacitance differs from the packaged SMCNR summary (`80.9459 fF` here vs
  `71.4964 fF` packaged). Do not claim exact PEX numerical reproduction.
- This is MOS-only layout/LVS evidence. Passive-aware/full-native passive
  evidence remains governed by the original `cand_0031` contract.

## 7. Next Step

Resume SMCNR variant work only through the Harness-native compiler and layout
adapter. The next valid experiment is a one-variable perturbation from
`var_ref_000`, with the same environment:

```bash
PATH=/home/qlf/IOT/scripts/env/bin:$PATH
PDK_ROOT=/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9
SKY130A=/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A
```

