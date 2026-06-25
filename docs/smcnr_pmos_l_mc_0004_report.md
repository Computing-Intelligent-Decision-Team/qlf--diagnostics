# SMCNR PMOS-L MC Batch 0004 Report

**Date**: 2026-06-25
**Status**: **0/30 accepted — half-step factors crash MAGICAL**

## Result

| Metric | Value |
|--------|-------|
| Total candidates | 30 |
| Accepted | 0 |
| Rejected | 30 |
| Pass rate | 0% |
| Failure mode | 100% magical_crash |

## Root Cause

Half-step factors (0.9525, 0.9575, 0.9625, ...) produce L values (e.g., 9.525µm)
that do not align to the MAGICAL PDK device cell grid. MAGICAL's Anaroute router
crashes with grid alignment assertion:

```
abs(pBox->yl()) % 10 == 0 or abs(pBox->yl()) % 10 == 8
```

Only the 13 known-working factors are MAGICAL-compatible:
0.95, 0.96, 0.97, 0.98, 0.99, 1.005, 1.01, 1.015, 1.02, 1.025, 1.03, 1.04, 1.05.

The DRC count fix itself is verified: the smoke test with factor 0.95
produced `accepted, drc_count=0, equiv_count=0, lvs_pass=true`.

## Current Safe Parameter Space

| Axis | Safe factors | Step | Max candidates per axis |
|------|-------------|------|------------------------|
| bias_pmos_l | 13 values | 0.005 (irregular) | 13 |
| second_stage_pmos_l | 13 values | 0.005 (irregular) | 13 |

**Total unique PMOS-L candidates possible: 26** (2 axes × 13 factors).

The 13-factor set is the practical maximum for this PDK version. Smaller
step sizes are blocked by MAGICAL grid constraints. This is a fundamental
PDK limitation, not a runner or pipeline issue.
