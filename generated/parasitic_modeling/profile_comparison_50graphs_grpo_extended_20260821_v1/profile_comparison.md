# Parasitic feature-profile comparison

- schema_version: `parasitic_profile_comparison.v1`
- profiles: 3
- rows: 27

## Metrics

| profile | model | target | MAE | max abs error | features | excluded |
|---|---|---|---:|---:|---:|---:|
| no_total_cap_leakage | mean_baseline | cap_count | 41.8122 | 70.8163 | 12 | 5 |
| no_total_cap_leakage | mean_baseline | output_node_cap_ff | 291.75 | 405.451 | 12 | 5 |
| no_total_cap_leakage | mean_baseline | total_cap_ff | 415.311 | 5167.95 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | cap_count | 3.24 | 32 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | output_node_cap_ff | 22.1152 | 473.117 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | total_cap_ff | 150.334 | 4140.86 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | cap_count | 1.05471 | 11.2451 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | output_node_cap_ff | 62.385 | 1654.02 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | total_cap_ff | 117.329 | 1648.87 | 12 | 5 |
| structure_only | mean_baseline | cap_count | 41.8122 | 70.8163 | 9 | 8 |
| structure_only | mean_baseline | output_node_cap_ff | 291.75 | 405.451 | 9 | 8 |
| structure_only | mean_baseline | total_cap_ff | 415.311 | 5167.95 | 9 | 8 |
| structure_only | nearest_neighbor | cap_count | 2.14 | 21 | 9 | 8 |
| structure_only | nearest_neighbor | output_node_cap_ff | 28.9889 | 473.193 | 9 | 8 |
| structure_only | nearest_neighbor | total_cap_ff | 282.64 | 5564.38 | 9 | 8 |
| structure_only | ridge_regression | cap_count | 0.788947 | 4.53047 | 9 | 8 |
| structure_only | ridge_regression | output_node_cap_ff | 39.3376 | 465.827 | 9 | 8 |
| structure_only | ridge_regression | total_cap_ff | 399.463 | 5134.12 | 9 | 8 |
| leaky_smoke_test | mean_baseline | cap_count | 41.8122 | 70.8163 | 17 | 0 |
| leaky_smoke_test | mean_baseline | output_node_cap_ff | 291.75 | 405.451 | 17 | 0 |
| leaky_smoke_test | mean_baseline | total_cap_ff | 415.311 | 5167.95 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | cap_count | 4.08 | 37 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | output_node_cap_ff | 23.1948 | 473.117 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | total_cap_ff | 116.174 | 3940.58 | 17 | 0 |
| leaky_smoke_test | ridge_regression | cap_count | 1.31282 | 20.1482 | 17 | 0 |
| leaky_smoke_test | ridge_regression | output_node_cap_ff | 50.8269 | 1367.83 | 17 | 0 |
| leaky_smoke_test | ridge_regression | total_cap_ff | 22.8899 | 288.098 | 17 | 0 |

## Notes

- leaky_smoke_test is for pipeline smoke checks and includes direct total-cap leakage.
- no_total_cap_leakage is the default research profile.
- structure_only isolates topology/count signal by removing all capacitance value features.
