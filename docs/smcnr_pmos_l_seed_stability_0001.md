# SMCNR PMOS-L Seed Stability Experiment 0001

**Date**: 2026-06-24
**Status**: PASS — 9/9 LVS PASS (100%), zero PEX variance per parameter point

## 1. Method

3 parameter points x 3 MAGICAL seeds. MOS-only projection, auto-rename + Netgen LVS.

## 2. Results

| Sample | Axis | Factor | Seed | DRC | equiv | LVS | SrcD | ExtD | SrcN | ExtN | Caps | Total fF |
|--------|------|--------|------|-----|-------|-----|------|------|------|------|------|----------|
| stab_baseline_1p00_seed01 | baseline | N/A | 1 | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 36 | 80.9455 |
| stab_baseline_1p00_seed02 | baseline | N/A | 2 | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 36 | 80.9455 |
| stab_baseline_1p00_seed03 | baseline | N/A | 3 | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 36 | 80.9455 |
| stab_bias_0p95_seed01 | bias_pmos_l | 0.9500 | 1 | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 35 | 80.2483 |
| stab_bias_0p95_seed02 | bias_pmos_l | 0.9500 | 2 | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 35 | 80.2483 |
| stab_bias_0p95_seed03 | bias_pmos_l | 0.9500 | 3 | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 35 | 80.2483 |
| stab_2nd_stage_1p03_seed01 | second_stage_pmos_l | 1.0300 | 1 | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 35 | 81.2618 |
| stab_2nd_stage_1p03_seed02 | second_stage_pmos_l | 1.0300 | 2 | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 35 | 81.2618 |
| stab_2nd_stage_1p03_seed03 | second_stage_pmos_l | 1.0300 | 3 | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 35 | 81.2618 |

## 3. Per-Point Statistics

| Point | Seeds | LVS Pass Rate | Caps | Total fF | PEX Variance |
|-------|-------|---------------|------|----------|-------------|
| baseline | 3 | 3/3 (100%) | [36] | [80.9455] | **0.0000 fF** |
| bias_pmos_l | 3 | 3/3 (100%) | [35] | [80.2483] | **0.0000 fF** |
| second_stage_pmos_l | 3 | 3/3 (100%) | [35] | [81.2618] | **0.0000 fF** |

## 4. Decision

Overall: 9/9 LVS PASS (100%).
Zero PEX variance within each parameter point — parasitic signature is
fully determined by sizing, not by layout seed.
**Production line cleared for expansion to 100+ candidates.**

## 5. Artifacts

- `generated/smcnr_variants/mc_pmos_l_seed_stability_0001/stability_results.json` (9 records, all fields populated)
- Tests: 24/24 OK
