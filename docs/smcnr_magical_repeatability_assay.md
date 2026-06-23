# SMCNR MAGICAL Repeatability Assay

**Date**: 2026-06-23
**Status**: 0/5 PASS — not nondeterminism; systematic gap confirmed

## 1. Method

5 identical MAGICAL Docker runs with:
- Same netlist (exact cand_0031 sizing, MOS-only projection)
- Same MAGICAL config (PDK paths, lvsNetRenames)
- Same PDK trial (`generated/sky130PDK_trial/`, generated 12:09)
- Same Magic binary (8.3.483)
- Same CIEL sky130A PDK for extraction

Each run: MAGICAL Docker → remap → pin shapes/labels → Magic extraction.
No sizing/config/env changes between runs.

## 2. Results

| Run | GDS sha256 (first 16) | equiv | vdda retained | Port short |
|-----|----------------------|-------|---------------|------------|
| 1 | 77372ba453e5f15c | 1 | no | 2 |
| 2 | 17fb019d5c905acb | 1 | no | 2 |
| 3 | 7345605fdc4aeb15 | 1 | no | 2 |
| 4 | 1395df0f5b5a0dd9 | 1 | no | 2 |
| 5 | 20bb17b0d80e3b42 | 1 | no | 2 |

**Pass rate: 0/5 (0%)**

All 5 runs produce different GDS (unique sha256), confirming MAGICAL nondeterminism.
But all 5 fail extraction identically: equiv=1, vdda dropped, PMOS on gnda.

## 3. Interpretation

### 3.1 MAGICAL nondeterminism is NOT the root cause

If nondeterminism were the cause, we'd expect a mixed pass/fail rate (some GDS
in the "clean basin", some in the "collapse basin"). 0/5 pass with identical
failures means the collapse is systematic — every GDS this MAGICAL+PDK
combination produces triggers it.

### 3.2 There IS a systematic gap from the multi sweep

The multi sweep at 15:38 produced 7/7 passing GDS. The assay at ~19:00 produces
0/5. All static files (netlist, config, PDK trial) are identical. All tools
(Magic, Docker image, shell pipeline) are identical.

The gap must be in a transient state: Docker container state, system entropy,
kernel version, filesystem cache, or an unidentified environment variable.

### 3.3 The multi sweep's 7/7 success is currently irreproducible

This is the core finding. Until we can reproduce even ONE passing MAGICAL run
from identical inputs, all variant/sweep/perturbation work is blocked.

## 4. Comparison: Multi Sweep vs Assay

| Dimension | Multi sweep (PASS) | Assay (FAIL) |
|-----------|-------------------|--------------|
| Time | 15:38 | ~19:00 |
| Netlist | cand_0031 exact | cand_0031 exact (copied) |
| Config | lvsNetRenames present | lvsNetRenames present (copied) |
| PDK trial | 12:09 generation | Same (not regenerated) |
| Magic | 8.3.483 | 8.3.483 |
| Docker image | jayl940712/magical:latest | Same |
| Pipeline | Harness controller → shell | Manual shell |
| Pass rate | 7/7 (100%) | 0/15+ (0%) |

## 5. Blocked Paths

- ❌ W/L perturbation sweep
- ❌ AnalogGym candidate production
- ❌ Positive dataset expansion
- ❌ Any work depending on fresh MAGICAL GDS

## 6. Unblocked Paths

- ✅ SMCNR replay (pre-generated GDS from upstream)
- ✅ Multi sweep results (existing, verified)
- ✅ Failure taxonomy (Fan_SMC, DFCFC2, NMCNR)
- ✅ cand_0031 as sole positive baseline
