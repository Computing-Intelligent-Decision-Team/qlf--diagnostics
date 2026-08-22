# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `structure_only`
- sample_count: 52
- ridge_alpha: 1.0
- excluded_features: 8

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 41.4306 | 69.0392 |
| mean_baseline | total_cap_ff | 523.633 | 5048.19 |
| mean_baseline | output_node_cap_ff | 287.054 | 414.876 |
| nearest_neighbor | cap_count | 2.05769 | 21 |
| nearest_neighbor | total_cap_ff | 428.687 | 5564.38 |
| nearest_neighbor | output_node_cap_ff | 27.9658 | 473.193 |
| ridge_regression | cap_count | 0.746151 | 4.34514 |
| ridge_regression | total_cap_ff | 517.903 | 4414.05 |
| ridge_regression | output_node_cap_ff | 38.3082 | 466.287 |

## Warnings

- Only 52 graph samples are available; metrics are smoke-test diagnostics.
- All capacitance value features are excluded; this profile isolates topology/count signal from capacitance magnitude signal.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
