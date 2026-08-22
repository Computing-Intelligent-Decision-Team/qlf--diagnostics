# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `structure_only`
- sample_count: 64
- ridge_alpha: 1.0
- excluded_features: 8

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 37.5025 | 63.8571 |
| mean_baseline | total_cap_ff | 907.846 | 4770.04 |
| mean_baseline | output_node_cap_ff | 257.973 | 458.861 |
| nearest_neighbor | cap_count | 2.03125 | 21 |
| nearest_neighbor | total_cap_ff | 694.763 | 5564.38 |
| nearest_neighbor | output_node_cap_ff | 19.4068 | 473.193 |
| ridge_regression | cap_count | 0.697597 | 3.68241 |
| ridge_regression | total_cap_ff | 684.167 | 4187.85 |
| ridge_regression | output_node_cap_ff | 32.6292 | 466.826 |

## Warnings

- Only 64 graph samples are available; metrics are smoke-test diagnostics.
- All capacitance value features are excluded; this profile isolates topology/count signal from capacitance magnitude signal.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
