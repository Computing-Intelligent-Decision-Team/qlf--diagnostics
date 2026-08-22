# Parasitic feature-profile comparison

- schema_version: `parasitic_profile_comparison.v1`
- profiles: 3
- rows: 27

## Metrics

| profile | model | target | MAE | max abs error | features | excluded |
|---|---|---|---:|---:|---:|---:|
| no_total_cap_leakage | mean_baseline | cap_count | 37.5025 | 63.8571 | 12 | 5 |
| no_total_cap_leakage | mean_baseline | output_node_cap_ff | 257.973 | 458.861 | 12 | 5 |
| no_total_cap_leakage | mean_baseline | total_cap_ff | 907.846 | 4770.04 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | cap_count | 3.23438 | 32 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | output_node_cap_ff | 18.3373 | 473.117 | 12 | 5 |
| no_total_cap_leakage | nearest_neighbor | total_cap_ff | 184.353 | 2041.82 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | cap_count | 0.698739 | 4.81071 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | output_node_cap_ff | 33.2938 | 447.128 | 12 | 5 |
| no_total_cap_leakage | ridge_regression | total_cap_ff | 93.1313 | 830.797 | 12 | 5 |
| structure_only | mean_baseline | cap_count | 37.5025 | 63.8571 | 9 | 8 |
| structure_only | mean_baseline | output_node_cap_ff | 257.973 | 458.861 | 9 | 8 |
| structure_only | mean_baseline | total_cap_ff | 907.846 | 4770.04 | 9 | 8 |
| structure_only | nearest_neighbor | cap_count | 2.03125 | 21 | 9 | 8 |
| structure_only | nearest_neighbor | output_node_cap_ff | 19.4068 | 473.193 | 9 | 8 |
| structure_only | nearest_neighbor | total_cap_ff | 694.763 | 5564.38 | 9 | 8 |
| structure_only | ridge_regression | cap_count | 0.697597 | 3.68241 | 9 | 8 |
| structure_only | ridge_regression | output_node_cap_ff | 32.6292 | 466.826 | 9 | 8 |
| structure_only | ridge_regression | total_cap_ff | 684.167 | 4187.85 | 9 | 8 |
| leaky_smoke_test | mean_baseline | cap_count | 37.5025 | 63.8571 | 17 | 0 |
| leaky_smoke_test | mean_baseline | output_node_cap_ff | 257.973 | 458.861 | 17 | 0 |
| leaky_smoke_test | mean_baseline | total_cap_ff | 907.846 | 4770.04 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | cap_count | 4.65625 | 39 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | output_node_cap_ff | 20.4123 | 473.117 | 17 | 0 |
| leaky_smoke_test | nearest_neighbor | total_cap_ff | 85.9805 | 486.955 | 17 | 0 |
| leaky_smoke_test | ridge_regression | cap_count | 0.761944 | 5.38866 | 17 | 0 |
| leaky_smoke_test | ridge_regression | output_node_cap_ff | 31.498 | 438.773 | 17 | 0 |
| leaky_smoke_test | ridge_regression | total_cap_ff | 31.8755 | 362.685 | 17 | 0 |

## Notes

- leaky_smoke_test is for pipeline smoke checks and includes direct total-cap leakage.
- no_total_cap_leakage is the default research profile.
- structure_only isolates topology/count signal by removing all capacitance value features.
