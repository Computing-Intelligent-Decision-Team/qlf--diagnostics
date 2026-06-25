# Parasitic Modeling Dataset v0.3 Card

**Date**: 2026-06-25
**Records**: 40
**Version**: v0.3 (NMOS-L marginal samples added; seed-stability confirmed)

## Composition

| Tier | Count | Description |
|------|-------|-------------|
| T1: Reviewed Positive | 1 | cand_0031. Only training-positive. |
| T2: Review-Pool (PMOS-L, structural) | 29 | L-only + MC0001 + MC0002 PMOS-L variants. LVS PASS, structural PEX diversity. |
| T3: Failure-Only | 6 | Fan_SMC×2, DFCFC2×2, NMCNR, MC0002-rejected. |
| T4: Marginal Numeric (NMOS-L) | 4 | l_003–l_006. LVS PASS, numeric-only PEX diversity. |

## Source Batches

| Batch | Candidates | Accepted | Axes |
|-------|-----------|----------|------|
| L-only sweep | 8 | 8 | bias_pmos_l, second_stage_pmos_l, load_nmos_l, 2nd_nmos_l |
| MC0001 | 16 | 15 | bias_pmos_l, second_stage_pmos_l |
| MC0002 | 26 | 25 | bias_pmos_l, second_stage_pmos_l |

## Key Properties

- **Seed-stable**: 9/9 identical-input repeats produce identical PEX (0.0 fF variance).
- **PMOS-L axes**: bias_pmos_l, second_stage_pmos_l — proven safe, structural diversity.
- **NMOS-L axes**: load_nmos_l, second_stage_nmos_l — marginal numeric diversity only.
- **Step size**: 0.005 (proven reliable; 0.0025 blocked by MAGICAL crashes).
- **Pass rate**: 48/50 accepted across all PMOS-L batches (96%).
- **Rejected boundary**: second_stage_pmos_l=1.05 (device_mismatch 8 vs 7).

## Boundaries

- cand_0031 is the only reviewed positive baseline.
- All review-pool/marginal samples are MOS-only projection.
- No candidate is training-positive without Codex review.
- Full passive-inclusive LVS is not claimed.

## Regeneration

```bash
python3 -m tools.analog_harness.ml.parasitic_dataset \
  --output generated/parasitic_modeling/dataset_v0_3.jsonl \
  --summary
python3 -m unittest tools.analog_harness.tests.test_parasitic_dataset \
  tools.analog_harness.tests.test_analoggym_importer -v
```
