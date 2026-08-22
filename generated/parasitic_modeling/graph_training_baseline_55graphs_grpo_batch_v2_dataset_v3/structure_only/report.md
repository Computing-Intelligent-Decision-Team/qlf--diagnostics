# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `structure_only`
- sample_count: 55
- ridge_alpha: 1.0
- excluded_features: 8

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 40.4997 | 66.9815 |
| mean_baseline | total_cap_ff | 760.794 | 4960.83 |
| mean_baseline | output_node_cap_ff | 279.794 | 427.705 |
| nearest_neighbor | cap_count | 2 | 21 |
| nearest_neighbor | total_cap_ff | 674.076 | 5564.38 |
| nearest_neighbor | output_node_cap_ff | 25.9705 | 473.193 |
| ridge_regression | cap_count | 0.762232 | 3.97473 |
| ridge_regression | total_cap_ff | 678.993 | 4456.76 |
| ridge_regression | output_node_cap_ff | 36.5678 | 466.309 |

## Warnings

- Only 55 graph samples are available; metrics are smoke-test diagnostics.
- All capacitance value features are excluded; this profile isolates topology/count signal from capacitance magnitude signal.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
