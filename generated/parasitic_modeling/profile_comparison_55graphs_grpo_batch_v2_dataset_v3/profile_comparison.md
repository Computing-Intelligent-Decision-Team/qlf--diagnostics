# Parasitic feature-profile comparison

- schema_version: `parasitic_profile_comparison.v1`
- profiles: 3
- rows: 27

## Metrics

| profile | model | target | MAE | max abs error | features | excluded |
|---|---|---|---:|---:|---:|---:|
| no_total_cap_leakage | mean_baseline | cap_count | 40.4997 | 66.9815 | 12 | 5 |
| no_total_cap_leakage | mean_baseline | output_node_cap_ff | 279.794 | 427.705 | 12 | 5 |
| no_total_cap_leakage | mean_baseline | total_cap_ff | 760.794 | 4960.83 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | cap_count | 3.21818 | 32 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | output_node_cap_ff | 23.2047 | 473.117 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | total_cap_ff | 169.035 | 2041.82 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | cap_count | 0.792653 | 4.92417 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | output_node_cap_ff | 36.3173 | 439.893 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | total_cap_ff | 87.5781 | 794.392 | 12 | 5 |
| structure_only | mean_baseline | cap_count | 40.4997 | 66.9815 | 9 | 8 |
| structure_only | mean_baseline | output_node_cap_ff | 279.794 | 427.705 | 9 | 8 |
| structure_only | mean_baseline | total_cap_ff | 760.794 | 4960.83 | 9 | 8 |
| structure_only | nearest_neighbor | cap_count | 2 | 21 | 9 | 8 |
| structure_only | nearest_neighbor | output_node_cap_ff | 25.9705 | 473.193 | 9 | 8 |
| structure_only | nearest_neighbor | total_cap_ff | 674.076 | 5564.38 | 9 | 8 |
| structure_only | ridge_regression | cap_count | 0.762232 | 3.97473 | 9 | 8 |
| structure_only | ridge_regression | output_node_cap_ff | 36.5678 | 466.309 | 9 | 8 |
| structure_only | ridge_regression | total_cap_ff | 678.993 | 4456.76 | 9 | 8 |
| leaky_smoke_test | mean_baseline | cap_count | 40.4997 | 66.9815 | 17 | 0 |
| leaky_smoke_test | mean_baseline | output_node_cap_ff | 279.794 | 427.705 | 17 | 0 |
| leaky_smoke_test | mean_baseline | total_cap_ff | 760.794 | 4960.83 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | cap_count | 4.21818 | 39 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | output_node_cap_ff | 20.6044 | 473.117 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | total_cap_ff | 67.0843 | 486.955 | 17 | 0 |
| leaky_smoke_test | ridge_regression | cap_count | 0.866169 | 5.44775 | 17 | 0 |
| leaky_smoke_test | ridge_regression | output_node_cap_ff | 35.5224 | 441.425 | 17 | 0 |
| leaky_smoke_test | ridge_regression | total_cap_ff | 35.2895 | 363.487 | 17 | 0 |

## Notes

- leaky_smoke_test is for pipeline smoke checks and includes direct total-cap leakage.
- no_total_cap_leakage is the default research profile.
- structure_only isolates topology/count signal by removing all capacitance value features.
