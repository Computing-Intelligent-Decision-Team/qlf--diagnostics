# Graph training baseline v1

- schema_version: `parasitic_graph_training_baseline.v1`
- protocol: `leave_one_out`
- feature_profile: `structure_only`
- sample_count: 59
- ridge_alpha: 1.0
- excluded_features: 8

## Metrics

| model | target | MAE | max abs error |
|---|---|---:|---:|
| mean_baseline | cap_count | 39.1841 | 64.6034 |
| mean_baseline | total_cap_ff | 871.479 | 4849.98 |
| mean_baseline | output_node_cap_ff | 270.003 | 442.746 |
| nearest_neighbor | cap_count | 2.16949 | 21 |
| nearest_neighbor | total_cap_ff | 748.774 | 5564.38 |
| nearest_neighbor | output_node_cap_ff | 23.9585 | 473.193 |
| ridge_regression | cap_count | 0.748567 | 3.89852 |
| ridge_regression | total_cap_ff | 672.793 | 4178.54 |
| ridge_regression | output_node_cap_ff | 34.8419 | 466.63 |

## Warnings

- Only 59 graph samples are available; metrics are smoke-test diagnostics.
- All capacitance value features are excluded; this profile isolates topology/count signal from capacitance magnitude signal.
- Ridge regression is implemented without external dependencies for reproducible plumbing checks.
- Performance labels are excluded because Stage3 performance remains observation-only.
