# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `structure_only`
- sample_count: 50
- ridge_alpha: 1.0
- excluded_features: 8

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 41.8122 | 70.8163 |
| mean_baseline | total_cap_ff | 415.311 | 5167.95 |
| mean_baseline | output_node_cap_ff | 291.75 | 405.451 |
| nearest_neighbor | cap_count | 2.14 | 21 |
| nearest_neighbor | total_cap_ff | 282.64 | 5564.38 |
| nearest_neighbor | output_node_cap_ff | 28.9889 | 473.193 |
| ridge_regression | cap_count | 0.788947 | 4.53047 |
| ridge_regression | total_cap_ff | 399.463 | 5134.12 |
| ridge_regression | output_node_cap_ff | 39.3376 | 465.827 |

## Warnings

- Only 50 graph samples are available; metrics are smoke-test diagnostics.
- All capacitance value features are excluded; this profile isolates topology/count signal from capacitance magnitude signal.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
