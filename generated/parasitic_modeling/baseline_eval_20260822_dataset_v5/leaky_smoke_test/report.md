# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `leaky_smoke_test`
- sample_count: 64
- ridge_alpha: 1.0
- excluded_features: 0

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 37.5025 | 63.8571 |
| mean_baseline | total_cap_ff | 907.846 | 4770.04 |
| mean_baseline | output_node_cap_ff | 257.973 | 458.861 |
| nearest_neighbor | cap_count | 4.65625 | 39 |
| nearest_neighbor | total_cap_ff | 85.9805 | 486.955 |
| nearest_neighbor | output_node_cap_ff | 20.4123 | 473.117 |
| ridge_regression | cap_count | 0.761944 | 5.38866 |
| ridge_regression | total_cap_ff | 31.8755 | 362.685 |
| ridge_regression | output_node_cap_ff | 31.498 | 438.773 |

## Warnings

- Only 64 graph samples are available; metrics are smoke-test diagnostics.
- edge_total_cap_ff is included to validate graph-edge aggregation and leaks the total_cap_ff target; do not treat that target as a predictive claim.
- Use feature_profile=no_total_cap_leakage for non-leaky smoke checks of total_cap_ff.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
