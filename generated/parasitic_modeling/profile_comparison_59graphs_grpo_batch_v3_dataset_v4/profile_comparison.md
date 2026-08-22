# Parasitic feature-profile comparison

- schema_version: `parasitic_profile_comparison.v1`
- profiles: 3
- rows: 27

## Metrics

| profile | model | target | MAE | max abs error | features | excluded |
|---|---|---|---:|---:|---:|---:|
| no_total_cap_leakage | mean_baseline | cap_count | 39.1841 | 64.6034 | 12 | 5 |
| no_total_cap_leakage | mean_baseline | output_node_cap_ff | 270.003 | 442.746 | 12 | 5 |
| no_total_cap_leakage | mean_baseline | total_cap_ff | 871.479 | 4849.98 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | cap_count | 3.10169 | 32 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | output_node_cap_ff | 23.5724 | 473.117 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | total_cap_ff | 193.88 | 2041.82 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | cap_count | 0.769415 | 4.87567 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | output_node_cap_ff | 34.3657 | 442.675 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | total_cap_ff | 89.6819 | 811.98 | 12 | 5 |
| structure_only | mean_baseline | cap_count | 39.1841 | 64.6034 | 9 | 8 |
| structure_only | mean_baseline | output_node_cap_ff | 270.003 | 442.746 | 9 | 8 |
| structure_only | mean_baseline | total_cap_ff | 871.479 | 4849.98 | 9 | 8 |
| structure_only | nearest_neighbor | cap_count | 2.16949 | 21 | 9 | 8 |
| structure_only | nearest_neighbor | output_node_cap_ff | 23.9585 | 473.193 | 9 | 8 |
| structure_only | nearest_neighbor | total_cap_ff | 748.774 | 5564.38 | 9 | 8 |
| structure_only | ridge_regression | cap_count | 0.748567 | 3.89852 | 9 | 8 |
| structure_only | ridge_regression | output_node_cap_ff | 34.8419 | 466.63 | 9 | 8 |
| structure_only | ridge_regression | total_cap_ff | 672.793 | 4178.54 | 9 | 8 |
| leaky_smoke_test | mean_baseline | cap_count | 39.1841 | 64.6034 | 17 | 0 |
| leaky_smoke_test | mean_baseline | output_node_cap_ff | 270.003 | 442.746 | 17 | 0 |
| leaky_smoke_test | mean_baseline | total_cap_ff | 871.479 | 4849.98 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | cap_count | 4.18644 | 39 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | output_node_cap_ff | 21.1485 | 473.117 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | total_cap_ff | 87.8685 | 486.955 | 17 | 0 |
| leaky_smoke_test | ridge_regression | cap_count | 0.842353 | 5.41231 | 17 | 0 |
| leaky_smoke_test | ridge_regression | output_node_cap_ff | 33.0397 | 440.328 | 17 | 0 |
| leaky_smoke_test | ridge_regression | total_cap_ff | 34.1047 | 366.414 | 17 | 0 |

## Notes

- leaky_smoke_test is for pipeline smoke checks and includes direct total-cap leakage.
- no_total_cap_leakage is the default research profile.
- structure_only isolates topology/count signal by removing all capacitance value features.
