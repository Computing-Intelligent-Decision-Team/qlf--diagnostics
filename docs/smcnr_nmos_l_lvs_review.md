# SMCNR NMOS-L LVS Review

**Date**: 2026-06-24
**Status**: 4/4 LVS PASS — marginal_numeric_diversity candidates

## Results

| Candidate | Change | DRC | equiv | LVS | Src Dev | Ext Dev | Src Net | Ext Net | PEX Caps | PEX Total (fF) | Diversity |
|-----------|--------|-----|-------|-----|---------|---------|---------|---------|----------|-----------------|-----------|
| l_003 | load_nmos_l -5% (10.0→9.5) | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 37 | 80.6173 | marginal_numeric |
| l_004 | load_nmos_l +5% (10.0→10.5) | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 37 | 81.3069 | marginal_numeric |
| l_005 | 2nd_nmos_l -5% (10.0→9.5) | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 37 | 80.7200 | marginal_numeric |
| l_006 | 2nd_nmos_l +5% (10.0→10.5) | 0 | 0 | PASS | 8 | 8 | 9 | 9 | 37 | 81.2729 | marginal_numeric |

## Classification

All four NMOS-L candidates pass DRC (0 errors), extraction (equiv=0), and
LVS (circuits match uniquely, 8/8 devices, 9/9 nets). However, unlike the
PMOS-L candidates, the NMOS-L perturbations do not change the parasitic
capacitor count (37 caps = baseline). The total capacitance changes by
0.23-0.36 fF, which is measurable but represents numerical diversity only,
not structural diversity.

**Classification**: `marginal_numeric_diversity` — useful as supplementary
data points but not primary structural-diverse samples for parasitic
modeling training.

## Trust Status

| Flag | Value |
|------|-------|
| trust_assigned | false |
| usable_for_supervised_positive_training | false |
| candidate_for_parasitic_modeling_review | false |
| diversity_class | marginal_numeric_diversity |
| evidence_scope | mos_only_projection |

## Boundaries

- NMOS-L candidates are NOT training-positive.
- MOS-only projection — not passive-inclusive LVS.
- cand_0031 remains the only reviewed positive baseline.
