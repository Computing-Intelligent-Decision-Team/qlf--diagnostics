# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `no_total_cap_leakage`
- sample_count: 55
- ridge_alpha: 1.0
- excluded_features: 5

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 40.4997 | 66.9815 |
| mean_baseline | total_cap_ff | 760.794 | 4960.83 |
| mean_baseline | output_node_cap_ff | 279.794 | 427.705 |
| nearest_neighbor | cap_count | 3.21818 | 32 |
| nearest_neighbor | total_cap_ff | 169.035 | 2041.82 |
| nearest_neighbor | output_node_cap_ff | 23.2047 | 473.117 |
| ridge_regression | cap_count | 0.792653 | 4.92417 |
| ridge_regression | total_cap_ff | 87.5781 | 794.392 |
| ridge_regression | output_node_cap_ff | 36.3173 | 439.893 |

## Warnings

- Only 55 graph samples are available; metrics are smoke-test diagnostics.
- Direct full-graph capacitance sum features are excluded; this profile is the preferred non-leaky smoke check for total_cap_ff.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
