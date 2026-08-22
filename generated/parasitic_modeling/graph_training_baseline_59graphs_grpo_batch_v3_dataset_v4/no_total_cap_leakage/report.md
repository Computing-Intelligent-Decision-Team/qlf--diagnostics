# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `no_total_cap_leakage`
- sample_count: 59
- ridge_alpha: 1.0
- excluded_features: 5

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 39.1841 | 64.6034 |
| mean_baseline | total_cap_ff | 871.479 | 4849.98 |
| mean_baseline | output_node_cap_ff | 270.003 | 442.746 |
| nearest_neighbor | cap_count | 3.10169 | 32 |
| nearest_neighbor | total_cap_ff | 193.88 | 2041.82 |
| nearest_neighbor | output_node_cap_ff | 23.5724 | 473.117 |
| ridge_regression | cap_count | 0.769415 | 4.87567 |
| ridge_regression | total_cap_ff | 89.6819 | 811.98 |
| ridge_regression | output_node_cap_ff | 34.3657 | 442.675 |

## Warnings

- Only 59 graph samples are available; metrics are smoke-test diagnostics.
- Direct full-graph capacitance sum features are excluded; this profile is the preferred non-leaky smoke check for total_cap_ff.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
