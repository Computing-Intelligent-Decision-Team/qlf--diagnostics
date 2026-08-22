# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `no_total_cap_leakage`
- sample_count: 52
- ridge_alpha: 1.0
- excluded_features: 5

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 41.4306 | 69.0392 |
| mean_baseline | total_cap_ff | 523.633 | 5048.19 |
| mean_baseline | output_node_cap_ff | 287.054 | 414.876 |
| nearest_neighbor | cap_count | 3.46154 | 32 |
| nearest_neighbor | total_cap_ff | 145.454 | 2528.78 |
| nearest_neighbor | output_node_cap_ff | 21.2647 | 473.117 |
| ridge_regression | cap_count | 0.809816 | 5.13609 |
| ridge_regression | total_cap_ff | 92.924 | 805.857 |
| ridge_regression | output_node_cap_ff | 32.6512 | 413.193 |

## Warnings

- Only 52 graph samples are available; metrics are smoke-test diagnostics.
- Direct full-graph capacitance sum features are excluded; this profile is the preferred non-leaky smoke check for total_cap_ff.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
