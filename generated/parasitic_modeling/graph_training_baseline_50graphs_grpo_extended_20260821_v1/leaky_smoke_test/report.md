# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `leaky_smoke_test`
- sample_count: 50
- ridge_alpha: 1.0
- excluded_features: 0

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 41.8122 | 70.8163 |
| mean_baseline | total_cap_ff | 415.311 | 5167.95 |
| mean_baseline | output_node_cap_ff | 291.75 | 405.451 |
| nearest_neighbor | cap_count | 4.08 | 37 |
| nearest_neighbor | total_cap_ff | 116.174 | 3940.58 |
| nearest_neighbor | output_node_cap_ff | 23.1948 | 473.117 |
| ridge_regression | cap_count | 1.31282 | 20.1482 |
| ridge_regression | total_cap_ff | 22.8899 | 288.098 |
| ridge_regression | output_node_cap_ff | 50.8269 | 1367.83 |

## Warnings

- Only 50 graph samples are available; metrics are smoke-test diagnostics.
- edge_total_cap_ff is included to validate graph-edge aggregation and leaks the total_cap_ff target; do not treat that target as a predictive claim.
- Use feature_profile=no_total_cap_leakage for non-leaky smoke checks of total_cap_ff.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
