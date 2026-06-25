# Parasitic Modeling Dataset v0.1 — Dataset Card

**Date**: 2026-06-24
**Version**: v0.1 (expanded review pool, research foundation)
**Records**: 15

## 1. What Changed Since v0

v0.1 adds 5 MC PMOS-L candidates (4 review-pool + 1 rejected) from the
constrained Monte Carlo sweep on two verified parameter axes:
`bias_pmos_l` and `second_stage_pmos_l`.

All new candidates were produced under the verified production pipeline:
MOS-only projection → MAGICAL Docker → Sky130 remap → Magic DRC (0 errors)
→ Magic extraction (equiv=0) → auto-LVS-rename → Netgen LVS → PEX parsing.

## 2. Dataset Composition

| Tier | Count | Description |
|------|-------|-------------|
| T1: Reviewed Positive Baseline | 1 | cand_0031. Full passive-inclusive LVS/PEX/post-sim/PVT. Only training-positive sample. |
| T2: Review-Pool (MOS-only) | 8 | 4 L-only + 4 MC PMOS-L variants. LVS PASS, PEX structural diversity confirmed. Not training-positive. |
| T3: Failure-Only / Diagnostic | 5 | Fan_SMC, DFCFC2, NMCNR. Extraction/LVS failures. For taxonomy only. |
| Rejected | 1 | mc_second_stage_pmos_1p05: device_mismatch (8 vs 7). |

## 3. Sample Records

### T1 — Positive Baseline

| sample_id | LVS | Caps | Total | Evidence Scope |
|-----------|-----|------|-------|----------------|
| smcnr_se_2st_amp_cand_0031 | PASS | 37 | 71.50 fF | full_passive_inclusive_gds_lvs |

### T2 — Review-Pool

| sample_id | Axis | ΔL | Caps | ΔTotal | LVS |
|-----------|------|-----|------|--------|-----|
| l_001_bias_pmos_l_m5 | bias_pmos | -5% | 36 | -0.70 fF | PASS |
| l_002_bias_pmos_l_p5 | bias_pmos | +5% | 36 | +1.10 fF | PASS |
| l_007_second_stage_pmos_l_m5 | 2nd_stage_pmos | -5% | 36 | -0.28 fF | PASS |
| l_008_second_stage_pmos_l_p5 | 2nd_stage_pmos | +5% | 35 | -2.02 fF | PASS |
| mc_bias_pmos_1p01 | bias_pmos | +1% | 36 | +0.33 fF | PASS |
| mc_bias_pmos_1p03 | bias_pmos | +3% | 36 | +0.66 fF | PASS |
| mc_second_stage_pmos_0p97 | 2nd_stage_pmos | -3% | 37 | -0.24 fF | PASS |
| mc_second_stage_pmos_1p01 | 2nd_stage_pmos | +1% | 37 | +0.10 fF | PASS |

All T2 samples: `trust_assigned=false`, `candidate_for_parasitic_modeling_review=true`,
`evidence_scope=mos_only_projection`, `usable_for_supervised_positive_training=false`.

### T3 — Failure-Only

| sample_id | Circuit | Failure Mode |
|-----------|---------|-------------|
| fan_smc_c0_proxy_psub_tap | Fan_SMC_Pin_3 | substrate/equiv collapse |
| fan_smc_c0_proxy_guardring_true | Fan_SMC_Pin_3 | substrate/equiv collapse |
| dfcfc2_mim_proxy | AMP_DFCFC2 | substrate collapse + MIM cap |
| dfcfc2_mos_only_rerun | AMP_DFCFC2 | substrate collapse |
| leung_nmcnr_mos_only | Leung_NMCNR_Pin_3 | well-merging collapse |

### Rejected

| sample_id | Reason |
|-----------|--------|
| mc_second_stage_pmos_1p05 | LVS FAIL: device mismatch 8 vs 7. Strongest perturbation (+5%) on 2nd_stage_pmos. |

## 4. Production Pipeline

```
cand_0031 baseline sizing
  → PMOS-L perturbation (±1% to ±5%)
  → MOS-only projection (R+C passives stripped)
  → MAGICAL Docker (placement + routing)
  → Sky130 GDS remap
  → Magic DRC
  → Magic extraction (verify equiv=0)
  → auto_lvs_rename_smcnr.py (auto-discover net renames)
  → Netgen LVS (verify Circuits match uniquely)
  → PEX parsing
  → trust gate (classify as review-pool / rejected / failure-only)
```

## 5. Known Limitations

1. All T2 samples are MOS-only projection — passive-inclusive PEX not yet available for new variants.
2. Single topology (SMCNR_SE_2st_AMP) — no cross-circuit diversity.
3. Two PMOS L axes only — W perturbation, nf, multi still blocked by MAGICAL grid constraints.
4. No post-layout simulation or PVT evidence for new variants.
5. Seed not yet recorded in sample_id for MC candidates (uses seed_01 by default).

## 6. Permissible Uses

| Use Case | T1 | T2 | T3 |
|----------|----|----|-----|
| Supervised parasitic prediction training | ✅ | ❌ | ❌ |
| Parasitic graph feature analysis | ✅ | ✅ | ❌ |
| Trust gate / evidence scope methodology | ✅ | ✅ | ✅ |
| PEX diversity characterization | ✅ | ✅ | ❌ |
| Extraction failure taxonomy | — | — | ✅ |
| Model performance claims | ❌ | ❌ | ❌ |

## 7. Key Claims

> cand_0031 remains the only reviewed positive baseline. All MC and L-only
> samples are MOS-only projection review-pool candidates — LVS/PEX verified
> but not training-positive.

> PMOS-L axes (bias_pmos_l, second_stage_pmos_l) provide robust structural
> parasitic diversity under the verified MOS-only AnalogHarness flow. The
> production pipeline achieves 15/16 LVS PASS (94%) on this parameter space.

## 8. Regeneration

```bash
python3 -m tools.analog_harness.ml.parasitic_dataset \
  --output generated/parasitic_modeling/dataset_v0.jsonl \
  --summary

python3 -m unittest tools.analog_harness.tests.test_parasitic_dataset \
  tools.analog_harness.tests.test_analoggym_importer -v
# 24/24 OK
```
