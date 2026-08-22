# Parasitic feature-profile comparison

- schema_version: `parasitic_profile_comparison.v1`
- profiles: 3
- rows: 27

## Metrics

| profile | model | target | MAE | max abs error | features | excluded |
|---|---|---|---:|---:|---:|---:|
| no_total_cap_leakage | mean_baseline | cap_count | 41.4306 | 69.0392 | 12 | 5 |
| no_total_cap_leakage | mean_baseline | output_node_cap_ff | 287.054 | 414.876 | 12 | 5 |
| no_total_cap_leakage | mean_baseline | total_cap_ff | 523.633 | 5048.19 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | cap_count | 3.46154 | 32 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | output_node_cap_ff | 21.2647 | 473.117 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | total_cap_ff | 145.454 | 2528.78 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | cap_count | 0.809816 | 5.13609 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | output_node_cap_ff | 32.6512 | 413.193 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | total_cap_ff | 92.924 | 805.857 | 12 | 5 |
| structure_only | mean_baseline | cap_count | 41.4306 | 69.0392 | 9 | 8 |
| structure_only | mean_baseline | output_node_cap_ff | 287.054 | 414.876 | 9 | 8 |
| structure_only | mean_baseline | total_cap_ff | 523.633 | 5048.19 | 9 | 8 |
| structure_only | nearest_neighbor | cap_count | 2.05769 | 21 | 9 | 8 |
| structure_only | nearest_neighbor | output_node_cap_ff | 27.9658 | 473.193 | 9 | 8 |
| structure_only | nearest_neighbor | total_cap_ff | 428.687 | 5564.38 | 9 | 8 |
| structure_only | ridge_regression | cap_count | 0.746151 | 4.34514 | 9 | 8 |
| structure_only | ridge_regression | output_node_cap_ff | 38.3082 | 466.287 | 9 | 8 |
| structure_only | ridge_regression | total_cap_ff | 517.903 | 4414.05 | 9 | 8 |
| leaky_smoke_test | mean_baseline | cap_count | 41.4306 | 69.0392 | 17 | 0 |
| leaky_smoke_test | mean_baseline | output_node_cap_ff | 287.054 | 414.876 | 17 | 0 |
| leaky_smoke_test | mean_baseline | total_cap_ff | 523.633 | 5048.19 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | cap_count | 3.71154 | 32 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | output_node_cap_ff | 19.591 | 473.117 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | total_cap_ff | 110.576 | 1699.29 | 17 | 0 |
| leaky_smoke_test | ridge_regression | cap_count | 0.902883 | 5.72675 | 17 | 0 |
| leaky_smoke_test | ridge_regression | output_node_cap_ff | 25.0442 | 402.185 | 17 | 0 |
| leaky_smoke_test | ridge_regression | total_cap_ff | 32.3003 | 302.995 | 17 | 0 |

## Notes

- leaky_smoke_test is for pipeline smoke checks and includes direct total-cap leakage.
- no_total_cap_leakage is the default research profile.
- structure_only isolates topology/count signal by removing all capacitance value features.
