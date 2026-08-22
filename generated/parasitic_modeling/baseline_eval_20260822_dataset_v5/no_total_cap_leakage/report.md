# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `no_total_cap_leakage`
- sample_count: 64
- ridge_alpha: 1.0
- excluded_features: 5

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 37.5025 | 63.8571 |
| mean_baseline | total_cap_ff | 907.846 | 4770.04 |
| mean_baseline | output_node_cap_ff | 257.973 | 458.861 |
| nearest_neighbor | cap_count | 3.23438 | 32 |
| nearest_neighbor | total_cap_ff | 184.353 | 2041.82 |
| nearest_neighbor | output_node_cap_ff | 18.3373 | 473.117 |
| ridge_regression | cap_count | 0.698739 | 4.81071 |
| ridge_regression | total_cap_ff | 93.1313 | 830.797 |
| ridge_regression | output_node_cap_ff | 33.2938 | 447.128 |

## Warnings

- Only 64 graph samples are available; metrics are smoke-test diagnostics.
- Direct full-graph capacitance sum features are excluded; this profile is the preferred non-leaky smoke check for total_cap_ff.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
