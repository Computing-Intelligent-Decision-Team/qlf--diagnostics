# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `leaky_smoke_test`
- sample_count: 55
- ridge_alpha: 1.0
- excluded_features: 0

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 40.4997 | 66.9815 |
| mean_baseline | total_cap_ff | 760.794 | 4960.83 |
| mean_baseline | output_node_cap_ff | 279.794 | 427.705 |
| nearest_neighbor | cap_count | 4.21818 | 39 |
| nearest_neighbor | total_cap_ff | 67.0843 | 486.955 |
| nearest_neighbor | output_node_cap_ff | 20.6044 | 473.117 |
| ridge_regression | cap_count | 0.866169 | 5.44775 |
| ridge_regression | total_cap_ff | 35.2895 | 363.487 |
| ridge_regression | output_node_cap_ff | 35.5224 | 441.425 |

## Warnings

- Only 55 graph samples are available; metrics are smoke-test diagnostics.
- edge_total_cap_ff is included to validate graph-edge aggregation and leaks the total_cap_ff target; do not treat that target as a predictive claim.
- Use feature_profile=no_total_cap_leakage for non-leaky smoke checks of total_cap_ff.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
