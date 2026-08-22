# GRPO-to-PCS admission smoke and 52-graph parasitic dataset v2

Date: 2026-08-22

## Current result

The current GRPO-to-PCS smoke adds two raw-PEX graph samples to the existing 50-graph parasitic dataset, producing a 52-graph dataset for the present graph-learning pipeline.

## Machine-readable artifacts

- Admission smoke summary: `generated/grpo_to_pcs_admission_smoke_20260822_v1/`
- 52-graph dataset: `generated/parasitic_modeling/graph_learning_samples_20260822_52graphs_grpo_admission_smoke_v2/`
- Profile baselines: `generated/parasitic_modeling/graph_training_baseline_52graphs_grpo_admission_smoke_20260822_v2/`
- Profile comparison: `generated/parasitic_modeling/profile_comparison_52graphs_grpo_admission_smoke_20260822_v2/`
- Family-aware evaluation: `generated/parasitic_modeling/family_aware_eval_52graphs_grpo_admission_smoke_20260822_v2/`

## Dataset counts

| item | count |
|---|---:|
| base graphs | 50 |
| added GRPO admission smoke graphs | 2 |
| total graphs | 52 |
| total nodes | 778 |
| total capacitor edges | 4591 |
| smoke candidates | 4 |
| smoke records admitted as raw-PEX graph | 2 |
| smoke records retained as admission evidence | 2 |

## Added graph samples

| graph_id | design_id | nodes | capacitor edges | total_cap_ff | raw_pex_sha256 |
|---|---|---:|---:|---:|---|
| `grpo_to_pcs_admission_smoke_v1/grpo_leung_dfcfc2_0000` | `leung_dfcfc2_pin_3` | 19 | 134 | 3999.37 | `8115cd3da42a76660ac578ab6d11e08ffa2d09cbd3eaba0f3027c7fc2e0865a1` |
| `grpo_to_pcs_admission_smoke_v1/grpo_leung_dfcfc2_0001` | `leung_dfcfc2_pin_3` | 19 | 127 | 3169.88 | `19a57d0079146af75d40f3eafd28f7d6c65a5e552e30e4d279e0e31b39c7b095` |

## Admission evidence table

| GRPO candidate | PCS candidate | M12.M | status | closure level | stage evidence | PEX caps | PEX total fF |
|---|---|---:|---|---|---|---:|---:|
| `grpo_leung_dfcfc2_0000` | `cand_0006` | 363 | `admitted_raw_pex_graph` | `L6_post_layout_pvt` | `` | 134 | 3999.37 |
| `grpo_leung_dfcfc2_0001` | `cand_0007` | 178 | `admitted_raw_pex_graph` | `L6_post_layout_pvt` | `` | 127 | 3169.88 |
| `grpo_leung_dfcfc2_0002` | `cand_0008` | 127 | `rejected_before_raw_pex_graph` | `L2_pre_layout_pvt` | `magical_place_route` |  |  |
| `grpo_leung_dfcfc2_0003` | `cand_0009` | 500 | `rejected_before_raw_pex_graph` | `L2_pre_layout_pvt` | `magical_place_route` |  |  |

## Profile comparison highlights

Ridge regression rows are listed as compact smoke-level indicators. Full metrics are in `profile_comparison.csv` and `profile_comparison.json`.

| feature profile | target | MAE | max abs error | samples |
|---|---|---:|---:|---:|
| `no_total_cap_leakage` | `cap_count` | 0.809816 | 5.13609 | 52 |
| `no_total_cap_leakage` | `total_cap_ff` | 92.924 | 805.857 | 52 |
| `structure_only` | `cap_count` | 0.746151 | 4.34514 | 52 |
| `structure_only` | `total_cap_ff` | 517.903 | 4414.05 | 52 |
| `leaky_smoke_test` | `cap_count` | 0.902883 | 5.72675 | 52 |
| `leaky_smoke_test` | `total_cap_ff` | 32.3003 | 302.995 | 52 |

## Family-aware evaluation highlights

The within-family row measures local interpolation on the currently configured family split. The leave-family-out row measures cross-family transfer under the same graph format.

| feature profile | protocol | target | MAE | max abs error | samples |
|---|---|---|---:|---:|---:|
| `no_total_cap_leakage` | `within_family_even_odd` | `cap_count` | 0.0175637 | 0.0555203 | 9 |
| `no_total_cap_leakage` | `within_family_even_odd` | `total_cap_ff` | 0.465582 | 1.05484 | 9 |
| `no_total_cap_leakage` | `leave_family_out` | `cap_count` | 4.42811 | 9.6906 | 52 |
| `no_total_cap_leakage` | `leave_family_out` | `total_cap_ff` | 613.218 | 2439.51 | 52 |
| `structure_only` | `within_family_even_odd` | `cap_count` | 0.0234598 | 0.0348505 | 9 |
| `structure_only` | `within_family_even_odd` | `total_cap_ff` | 0.562414 | 1.40102 | 9 |
| `structure_only` | `leave_family_out` | `cap_count` | 4.69996 | 10.4354 | 52 |
| `structure_only` | `leave_family_out` | `total_cap_ff` | 3749.49 | 8705.5 | 52 |

## Evidence boundary

- GRPO output is treated as a candidate source. A graph-training row enters this dataset after PCS produces raw PEX and the capacitor edge table is parsed into graph JSONL.
- The two admitted smoke records have `L6_post_layout_pvt`, DRC 0, connectivity LVS match, raw PEX paths, and raw PEX SHA-256 hashes.
- The two place-route records remain useful admission evidence and are intentionally kept outside graph-training labels.
- The smoke config uses `performance={}`, so `reward=-1.0` is an observation marker for this path rather than a performance-quality label.
- The dataset remains MOS-only/current PCS extraction-scope aligned.

## Reproduction commands used in PCS worktree

```bash
GRAPHS=generated/analog_harness/parasitic_modeling/graph_learning_samples_20260822_52graphs_grpo_admission_smoke_v2/graphs.jsonl
ROOT=generated/analog_harness/parasitic_modeling/graph_training_baseline_52graphs_grpo_admission_smoke_20260822_v2

for profile in no_total_cap_leakage structure_only leaky_smoke_test; do
  python3 -m tools.analog_harness.parasitic_graph_training_baseline \
    --graphs-jsonl "$GRAPHS" \
    --feature-profile "$profile" \
    --output-dir "$ROOT/$profile"
done

python3 -m tools.analog_harness.parasitic_profile_comparison \
  --profile-root "$ROOT" \
  --output-dir generated/analog_harness/parasitic_modeling/profile_comparison_52graphs_grpo_admission_smoke_20260822_v2

for profile in no_total_cap_leakage structure_only; do
  python3 -m tools.analog_harness.parasitic_family_aware_evaluation \
    --graphs-jsonl "$GRAPHS" \
    --feature-profile "$profile" \
    --output-dir generated/analog_harness/parasitic_modeling/family_aware_eval_52graphs_grpo_admission_smoke_20260822_v2/"$profile"
done
```

## Suggested next work

1. Feed additional AnalogGym-aligned GRPO exports through the same PCS admission path.
2. Add at least 3 to 5 admitted samples for non-SMCNR families so cross-family evaluation is less dominated by small family counts.
3. Keep `no_total_cap_leakage` as the default research profile and use `leaky_smoke_test` only as a pipeline wiring check.
