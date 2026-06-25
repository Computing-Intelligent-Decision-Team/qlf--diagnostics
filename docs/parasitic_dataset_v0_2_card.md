# Parasitic Modeling Dataset v0.2 Card

**Date**: 2026-06-24
**Records**: 36
**Version**: v0.2 (MC batch 0002 expansion)

## Composition

| Tier | Count | Description |
|------|-------|-------------|
| T1: Reviewed Positive | 1 | cand_0031. Full passive-inclusive LVS/PEX/post-sim/PVT. Only training-positive. |
| T2: Review-Pool (MOS-only) | 29 | L-only + MC0001 + MC0002 PMOS-L variants. LVS PASS, PEX structural diversity. Not training-positive. |
| T3: Failure-Only | 5 | Fan_SMC, DFCFC2, NMCNR. Extraction/LVS failures. |
| Rejected | 1 | mc0002_second_stage_pmos_l_1p05: device_mismatch 8 vs 7. |

## New in v0.2

- MC batch 0002: 25 accepted + 1 rejected across 13 perturbation levels on 2 PMOS-L axes.
- Total verified parasitic samples: 1 baseline + 8 L-only/MC0001 + 25 MC0002 = 34 review-pool candidates.
- All MC0002 entries recorded with drc_count, source/extracted devices/nets, and evidence_scope.

## Boundaries

- cand_0031 remains the only reviewed positive baseline.
- All review-pool samples are MOS-only projection — not passive-inclusive.
- No candidate is training-positive without Codex review.
- Rejected sample has evidence_scope=mos_only_projection_lvs_failed.

## Regeneration

```bash
python3 -m tools.analog_harness.ml.parasitic_dataset \
  --output generated/parasitic_modeling/dataset_v0_2.jsonl \
  --summary

python3 -m unittest tools.analog_harness.tests.test_parasitic_dataset \
  tools.analog_harness.tests.test_analoggym_importer -v
# 24/24 OK
```
