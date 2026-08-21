# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `no_total_cap_leakage`
- sample_count: 50
- ridge_alpha: 1.0
- excluded_features: 5

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 41.8122 | 70.8163 |
| mean_baseline | total_cap_ff | 415.311 | 5167.95 |
| mean_baseline | output_node_cap_ff | 291.75 | 405.451 |
| nearest_neighbor | cap_count | 3.24 | 32 |
| nearest_neighbor | total_cap_ff | 150.334 | 4140.86 |
| nearest_neighbor | output_node_cap_ff | 22.1152 | 473.117 |
| ridge_regression | cap_count | 1.05471 | 11.2451 |
| ridge_regression | total_cap_ff | 117.329 | 1648.87 |
| ridge_regression | output_node_cap_ff | 62.385 | 1654.02 |

## Warnings

- Only 50 graph samples are available; metrics are smoke-test diagnostics.
- Direct full-graph capacitance sum features are excluded; this profile is the preferred non-leaky smoke check for total_cap_ff.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
