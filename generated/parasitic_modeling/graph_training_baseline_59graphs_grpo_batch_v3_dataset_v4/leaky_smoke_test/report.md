# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `leaky_smoke_test`
- sample_count: 59
- ridge_alpha: 1.0
- excluded_features: 0

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 39.1841 | 64.6034 |
| mean_baseline | total_cap_ff | 871.479 | 4849.98 |
| mean_baseline | output_node_cap_ff | 270.003 | 442.746 |
| nearest_neighbor | cap_count | 4.18644 | 39 |
| nearest_neighbor | total_cap_ff | 87.8685 | 486.955 |
| nearest_neighbor | output_node_cap_ff | 21.1485 | 473.117 |
| ridge_regression | cap_count | 0.842353 | 5.41231 |
| ridge_regression | total_cap_ff | 34.1047 | 366.414 |
| ridge_regression | output_node_cap_ff | 33.0397 | 440.328 |

## Warnings

- Only 59 graph samples are available; metrics are smoke-test diagnostics.
- edge_total_cap_ff is included to validate graph-edge aggregation and leaks the total_cap_ff target; do not treat that target as a predictive claim.
- Use feature_profile=no_total_cap_leakage for non-leaky smoke checks of total_cap_ff.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
