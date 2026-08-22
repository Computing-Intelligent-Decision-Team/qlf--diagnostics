# Family-aware parasitic graph evaluation

- schema_version: `parasitic_family_aware_evaluation.v1`
- feature_profile: `no_total_cap_leakage`
- splits: 15
- within_family_splits: 1
- leave_family_out_splits: 14

## Protocol summary

| protocol | model | target | samples | MAE | max abs error |
|---|---|---|---:|---:|---:|
| leave_family_out | mean_baseline | cap_count | 52 | 53.9611 | 88.303 |
| leave_family_out | mean_baseline | total_cap_ff | 52 | 548.716 | 5189.43 |
| leave_family_out | mean_baseline | output_node_cap_ff | 52 | 371.457 | 626.699 |
| leave_family_out | nearest_neighbor | cap_count | 52 | 29.0385 | 67 |
| leave_family_out | nearest_neighbor | total_cap_ff | 52 | 453.784 | 3940.58 |
| leave_family_out | nearest_neighbor | output_node_cap_ff | 52 | 241.508 | 634.094 |
| leave_family_out | ridge_regression | cap_count | 52 | 4.42811 | 9.6906 |
| leave_family_out | ridge_regression | total_cap_ff | 52 | 613.218 | 2439.51 |
| leave_family_out | ridge_regression | output_node_cap_ff | 52 | 261.261 | 2129.59 |
| within_family_even_odd | mean_baseline | cap_count | 9 | 0.530864 | 0.777778 |
| within_family_even_odd | mean_baseline | total_cap_ff | 9 | 0.705468 | 1.21475 |
| within_family_even_odd | mean_baseline | output_node_cap_ff | 9 | 0.198458 | 0.607631 |
| within_family_even_odd | nearest_neighbor | cap_count | 9 | 0 | 0 |
| within_family_even_odd | nearest_neighbor | total_cap_ff | 9 | 0.581866 | 1.02391 |
| within_family_even_odd | nearest_neighbor | output_node_cap_ff | 9 | 0.0671889 | 0.0855 |
| within_family_even_odd | ridge_regression | cap_count | 9 | 0.0175637 | 0.0555203 |
| within_family_even_odd | ridge_regression | total_cap_ff | 9 | 0.465582 | 1.05484 |
| within_family_even_odd | ridge_regression | output_node_cap_ff | 9 | 0.0788663 | 0.149337 |

## Split inventory

| protocol | split | held-out family | train | test |
|---|---|---|---:|---:|
| within_family_even_odd | `within_smcnr_se_2st_amp_even_odd` | `smcnr_se_2st_amp` | 9 | 9 |
| leave_family_out | `leave_family_out_alfio_raffc_pin_3` | `alfio_raffc_pin_3` | 47 | 5 |
| leave_family_out | `leave_family_out_fan_smc_pin_3` | `fan_smc_pin_3` | 47 | 5 |
| leave_family_out | `leave_family_out_hoilee_affc_pin_3` | `hoilee_affc_pin_3` | 51 | 1 |
| leave_family_out | `leave_family_out_leung_dfcfc1_pin_3` | `leung_dfcfc1_pin_3` | 51 | 1 |
| leave_family_out | `leave_family_out_leung_dfcfc2_pin_3` | `leung_dfcfc2_pin_3` | 47 | 5 |
| leave_family_out | `leave_family_out_leung_nmcf_pin_3` | `leung_nmcf_pin_3` | 47 | 5 |
| leave_family_out | `leave_family_out_leung_nmcnr_pin_3` | `leung_nmcnr_pin_3` | 51 | 1 |
| leave_family_out | `leave_family_out_peng_acbc_pin_3` | `peng_acbc_pin_3` | 51 | 1 |
| leave_family_out | `leave_family_out_qu2017_azc_pin_3` | `qu2017_azc_pin_3` | 51 | 1 |
| leave_family_out | `leave_family_out_ramos_pfc_pin_3` | `ramos_pfc_pin_3` | 51 | 1 |
| leave_family_out | `leave_family_out_sau_cfcc_pin_3` | `sau_cfcc_pin_3` | 47 | 5 |
| leave_family_out | `leave_family_out_smcnr_se_2st_amp` | `smcnr_se_2st_amp` | 33 | 19 |
| leave_family_out | `leave_family_out_tan_clia_pin_3` | `tan_clia_pin_3` | 51 | 1 |
| leave_family_out | `leave_family_out_yan_az_pin_3` | `yan_az_pin_3` | 51 | 1 |

## Warnings

- within_family_even_odd measures local interpolation inside the chosen design family.
- leave_family_out measures cross-family transfer and is harsh when most held-out families have only one graph.
- SMCNR currently dominates controlled sizing variants; report protocol-specific metrics instead of one random-split score.
