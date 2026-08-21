# 50-graph GRPO-extended parasitic dataset v1

Date: 2026-08-21

This checkpoint is a review snapshot for the parasitic-modeling direction. It is intentionally stored in `qlf--diagnostics`, not in the senior-maintained `pcs-harness` repository.

## What this checkpoint contains

The dataset starts from the previous 48 graph-training-admitted parasitic graph samples and appends only the GRPO candidates that passed the formal admission gate:

```text
GRPO sizing export
-> AnalogGym-aligned PCS action-space contract
-> L0 ingest contract
-> existing L1--L6 physical replay evidence
-> raw *_extracted.raw.spice direct capacitor parsing
-> graph-training-admitted sample
```

Result:

| item | count |
|---|---:|
| Base graph-training-admitted graphs | 48 |
| Added GRPO raw-PEX graphs | 2 |
| Final graphs | 50 |
| Final nodes | 740 |
| Final capacitor edges | 4330 |
| GRPO records skipped as non-admitted | 6 |

The six skipped GRPO records are not hidden: they remain admission/failure evidence, but are not mixed into graph-training labels.

## Added GRPO graph samples

| candidate | M12.M | nodes | capacitor edges | total cap fF | raw PEX SHA256 |
|---|---:|---:|---:|---:|---|
| `grpo_leung_dfcfc2_0001` | 227 | 19 | 131 | 1557.8 | `12aa25a1d5fef2ae9eb1d1dcfe8371fa52df5c56401e0b044e65e46c00d17441` |
| `grpo_leung_dfcfc2_0006` | 421 | 19 | 151 | 5698.66 | `47f7997cf2c869921f78031e56c15b4a468fd3de8af2c2e6095c03c63e8b4f58` |

Interpretation: these two GRPO points are not tiny local perturbations. They extend the capacitance distribution substantially, especially `M12.M=421` with `5698.66 fF` total extracted capacitance.

## Files for review

- Dataset:
  `generated/parasitic_modeling/graph_learning_samples_20260821_50graphs_grpo_extended_v1/`
- Baseline/profile runs:
  `generated/parasitic_modeling/graph_training_baseline_50graphs_grpo_extended_20260821_v1/`
- Profile comparison:
  `generated/parasitic_modeling/profile_comparison_50graphs_grpo_extended_20260821_v1/`
- Family-aware evaluation:
  `generated/parasitic_modeling/family_aware_eval_50graphs_grpo_extended_20260821_v1/`

## Profile-comparison result

The default research profile is `no_total_cap_leakage`. It removes direct total-cap leakage while preserving aggregate capacitor-distribution features. `structure_only` removes capacitance values and keeps only graph structure/count markers. `leaky_smoke_test` is only a wiring sanity check.

| profile | model | target | MAE | max abs error |
|---|---|---|---:|---:|
| `no_total_cap_leakage` | ridge | total cap fF | 117.329 | 1648.87 |
| `no_total_cap_leakage` | ridge | cap count | 1.05471 | 11.2451 |
| `structure_only` | ridge | total cap fF | 399.463 | 5134.12 |
| `structure_only` | ridge | cap count | 0.788947 | 4.53047 |
| `leaky_smoke_test` | ridge | total cap fF | 22.8899 | 288.098 |

Takeaway:

- `structure_only` is much weaker for total-cap prediction, so the capacitance-value distribution contains useful information beyond pure topology.
- `leaky_smoke_test` is not a research result because it intentionally includes direct leakage features.

## Family-aware evaluation

| profile | protocol | model | target | samples | MAE |
|---|---|---|---|---:|---:|
| `no_total_cap_leakage` | within SMCNR | ridge | total cap fF | 9 | 0.465582 |
| `no_total_cap_leakage` | leave-family-out | ridge | total cap fF | 50 | 705.288 |
| `structure_only` | within SMCNR | ridge | total cap fF | 9 | 0.562414 |
| `structure_only` | leave-family-out | ridge | total cap fF | 50 | 2933.07 |

Takeaway:

- Local within-family interpolation is much easier than cross-family generalization.
- Cross-family claims are still premature because many families have only one admitted graph.
- The next useful data work is to admit more true GRPO candidates and/or add multi-sizing variants for non-SMCNR families.

## Boundary

- This checkpoint does not modify the senior-maintained `pcs-harness` repository.
- This checkpoint does not claim the six failed GRPO candidates are training samples.
- This checkpoint does not rerun MAGICAL, DRC, LVS, PEX, or simulation inside `qlf--diagnostics`.
- This checkpoint is a review/export snapshot of the admitted parasitic graph dataset and its baseline evaluations.

## Suggested senior review questions

1. Is the GRPO-to-PEX admission boundary correct: only L0/L6/raw-PEX admitted rows enter graph training?
2. Are the two GRPO-added Leung DFCFC2 samples acceptable as first GRPO distribution-shift samples?
3. Should the next batch prioritize more GRPO candidates in the same family, or more non-SMCNR/non-Leung multi-sizing variants?
4. Are there additional PCS-side evidence files that should accompany future dataset checkpoints?
