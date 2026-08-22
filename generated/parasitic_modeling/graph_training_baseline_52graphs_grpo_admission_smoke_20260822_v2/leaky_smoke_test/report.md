# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `leaky_smoke_test`
- sample_count: 52
- ridge_alpha: 1.0
- excluded_features: 0

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 41.4306 | 69.0392 |
| mean_baseline | total_cap_ff | 523.633 | 5048.19 |
| mean_baseline | output_node_cap_ff | 287.054 | 414.876 |
| nearest_neighbor | cap_count | 3.71154 | 32 |
| nearest_neighbor | total_cap_ff | 110.576 | 1699.29 |
| nearest_neighbor | output_node_cap_ff | 19.591 | 473.117 |
| ridge_regression | cap_count | 0.902883 | 5.72675 |
| ridge_regression | total_cap_ff | 32.3003 | 302.995 |
| ridge_regression | output_node_cap_ff | 25.0442 | 402.185 |

## Warnings

- Only 52 graph samples are available; metrics are smoke-test diagnostics.
- edge_total_cap_ff is included to validate graph-edge aggregation and leaks the total_cap_ff target; do not treat that target as a predictive claim.
- Use feature_profile=no_total_cap_leakage for non-leaky smoke checks of total_cap_ff.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
