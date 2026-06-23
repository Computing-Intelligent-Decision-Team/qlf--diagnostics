# Parasitic Modeling Dataset v0 — Dataset Card

**Date**: 2026-06-24
**Version**: v0 (research foundation, not training-complete)
**Records**: 10

## 1. Dataset Purpose

This dataset records extracted parasitic capacitance graphs from analog circuit
layouts, with per-sample trust metadata. Each sample has been through the
AnalogHarness pipeline (MAGICAL layout → Sky130 remap → Magic DRC → extraction
→ Netgen LVS → PEX), and is classified into one of three trust tiers.

**This dataset is a research foundation, not a training-complete corpus.**
It is useful for validating schema, parser behavior, trust labels, and
baseline graph features. It is too small to support model-performance claims.

## 2. Trust Tiers

| Tier | Label | Count | Meaning |
|------|-------|-------|---------|
| T1 | `POSITIVE` | 1 | Reviewed training-positive baseline. DRC=0, LVS=PASS, PEX verified, post-sim/PVT passed. Safe for supervised training. |
| T2 | `review-pool` | 4 | LVS=PASS, PEX verified with structural diversity vs baseline. Candidate for parasitic modeling, **not yet** training-positive. Requires Codex review before promotion. |
| T3 | `failure-only` | 5 | LVS=FAIL or extraction collapse. Useful only as diagnostic/failure-case reference. Must never enter positive training. |

## 3. Sample Records

### T1 — Reviewed Positive Baseline

| sample_id | Circuit | LVS | Caps | Total (fF) | Evidence Scope | Usable For |
|-----------|---------|-----|------|------------|----------------|------------|
| `smcnr_se_2st_amp_cand_0031` | SMCNR_SE_2st_AMP | PASS | 37 | 71.50 | full_passive_inclusive_gds_lvs | Supervised positive training |

### T2 — Review-Pool (MOS-Only Projection)

| sample_id | LVS | Caps | Total (fF) | Δ vs Baseline | Diversity | Perturbation |
|-----------|-----|------|------------|---------------|-----------|-------------|
| `l_001_bias_pmos_l_m5` | PASS | 36 | 80.25 | -0.70 fF | structural | bias_pmos_l -5% |
| `l_002_bias_pmos_l_p5` | PASS | 36 | 82.05 | +1.10 fF | structural | bias_pmos_l +5% |
| `l_007_second_stage_pmos_l_m5` | PASS | 36 | 80.67 | -0.28 fF | structural | 2nd_stage_pmos_l -5% |
| `l_008_second_stage_pmos_l_p5` | PASS | 35 | 78.93 | -2.02 fF | structural | 2nd_stage_pmos_l +5% |

All T2 samples share:
- `trust_assigned=false`
- `candidate_for_parasitic_modeling_review=true`
- `evidence_scope=mos_only_projection`
- `usable_for_supervised_positive_training=false`
- Generated under MOS-only projection (R+C passives stripped before MAGICAL)

### T3 — Failure-Only

| sample_id | Circuit | LVS | Caps | Failure Mode |
|-----------|---------|-----|------|-------------|
| `fan_smc_c0_proxy_psub_tap` | Fan_SMC_Pin_3 | FAIL | 95 | substrate/equiv collapse |
| `fan_smc_c0_proxy_guardring_true` | Fan_SMC_Pin_3 | FAIL | 92 | substrate/equiv collapse |
| `dfcfc2_mim_proxy` | AMP_DFCFC2 | FAIL | 103 | substrate collapse + MIM cap |
| `dfcfc2_mos_only_rerun` | AMP_DFCFC2 | FAIL | 51 | substrate collapse |
| `leung_nmcnr_mos_only` | Leung_NMCNR_Pin_3 | FAIL | 105 | well-merging collapse |

All T3 samples share `usable_for_supervised_positive_training=false` and
`usable_only_as_failure_case=true`.

Additionally, 4 NMOS-L variants (l_003–l_006) are classified as
`marginal_numeric_diversity`: LVS PASS, PEX 37 caps (same count as baseline),
with small total capacitance changes (0.23–0.36 fF). Not yet registered in
the dataset pending further review.

## 4. Schema

Each JSONL record contains:

```text
sample_id                          Unique sample identifier
circuit                            Circuit topology name
candidate_id                       Variant/candidate identifier
lvs_status                         PASS or FAIL
trust_scope                        Evidence scope (full_passive_inclusive_gds_lvs, mos_only_projection, failure_case_only)
usable_for_supervised_positive_training   Boolean — only T1 is true
usable_for_parasitic_modeling      Boolean — T1+T2 are true; T3 is false
usable_only_as_failure_case        Boolean — only T3 is true
candidate_for_parasitic_modeling_review   Boolean — T2 review-pool flag
evidence_scope                     Detailed scope description
diversity_class                    structural_diverse | marginal_numeric | none
pex_caps                           Number of extracted parasitic capacitors
pex_total_cap_ff                   Total parasitic capacitance in fF
parasitic_edges                    Array of {cap_id, node_a, node_b, cap_ff}
per_node_cap_ff                    Per-node capacitance breakdown
graph_features                     {num_nodes, num_edges, largest_cap_ff, mos_count, ...}
source_artifacts                   Paths to raw SPICE, .ext, LVS log, etc.
provenance_note                    Human-readable provenance
```

## 5. Known Limitations

1. **Size**: 10 records is too small for any model training claim.
2. **MOS-only projection**: All T2 samples are MOS-only (R+C passives stripped before MAGICAL). Passive-inclusive PEX is not yet available for new variants.
3. **Single topology**: All verified samples are SMCNR_SE_2st_AMP. No cross-circuit diversity.
4. **Single PDK corner**: All samples use tt corner at 27°C.
5. **No post-layout simulation**: Only cand_0031 has post-sim/PVT evidence.
6. **No layout seed diversity**: All T2 samples use same MAGICAL seed; layout nondeterminism not explored.

## 6. Permissible Uses

| Use Case | T1 | T2 | T3 |
|----------|----|----|-----|
| Supervised parasitic prediction training | ✅ | ❌ | ❌ |
| Parasitic graph feature analysis | ✅ | ✅ | ❌ |
| Trust gate / evidence scope methodology | ✅ | ✅ | ✅ |
| Extraction failure taxonomy | — | — | ✅ |
| Schema/parser validation | ✅ | ✅ | ✅ |
| Baseline statistical features | ✅ | ✅ | ❌ |
| Model performance claims | ❌ | ❌ | ❌ |

## 7. Forbidden Claims

- ❌ Dataset v0 is statistically sufficient for model training
- ❌ T2 review-pool samples are training-positive
- ❌ Fan_SMC/DFCFC2/NMCNR passed LVS
- ❌ MOS-only projection equals full-passive LVS
- ❌ PEX availability alone makes a sample training-safe
- ❌ The dataset proves diffusion/Mamba performance

## 8. Provenance

Generated by `tools/analog_harness/ml/parasitic_dataset.py` from AnalogHarness
pipeline artifacts. All T1+T2 samples run through:
MAGICAL Docker → Sky130 remap → Magic DRC → Magic extraction → Netgen LVS → PEX.
T3 samples from prior diagnostic investigations.

Regeneration command:
```bash
python3 -m tools.analog_harness.ml.parasitic_dataset \
  --output generated/parasitic_modeling/dataset_v0.jsonl \
  --summary
```

Tests: `python3 -m unittest tools.analog_harness.tests.test_parasitic_dataset -v` (20/20 OK + 4 importer tests = 24/24 OK).
