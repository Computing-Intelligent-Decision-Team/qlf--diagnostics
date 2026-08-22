# Family-aware parasitic graph evaluation

- schema_version: `parasitic_family_aware_evaluation.v1`
- feature_profile: `leaky_smoke_test`
- splits: 15
- within_family_splits: 1
- leave_family_out_splits: 14

## Protocol summary

| protocol | model | target | samples | MAE | max abs error |
|---|---|---|---:|---:|---:|
| leave_family_out | mean_baseline | cap_count | 59 | 50.205 | 88.9 |
| leave_family_out | mean_baseline | total_cap_ff | 59 | 1008.07 | 5271.82 |
| leave_family_out | mean_baseline | output_node_cap_ff | 59 | 344.292 | 630.04 |
| leave_family_out | nearest_neighbor | cap_count | 59 | 26.7119 | 67 |
| leave_family_out | nearest_neighbor | total_cap_ff | 59 | 525.023 | 4022.97 |
| leave_family_out | nearest_neighbor | output_node_cap_ff | 59 | 227.25 | 634.094 |
| leave_family_out | ridge_regression | cap_count | 59 | 4.33753 | 10.0359 |
| leave_family_out | ridge_regression | total_cap_ff | 59 | 208.857 | 620.472 |
| leave_family_out | ridge_regression | output_node_cap_ff | 59 | 327.592 | 1934.08 |
| within_family_even_odd | mean_baseline | cap_count | 9 | 0.530864 | 0.777778 |
| within_family_even_odd | mean_baseline | total_cap_ff | 9 | 0.705468 | 1.21475 |
| within_family_even_odd | mean_baseline | output_node_cap_ff | 9 | 0.198458 | 0.607631 |
| within_family_even_odd | nearest_neighbor | cap_count | 9 | 0 | 0 |
| within_family_even_odd | nearest_neighbor | total_cap_ff | 9 | 0.299884 | 1.02383 |
| within_family_even_odd | nearest_neighbor | output_node_cap_ff | 9 | 0.0941967 | 0.25646 |
| within_family_even_odd | ridge_regression | cap_count | 9 | 0.0199948 | 0.0641209 |
| within_family_even_odd | ridge_regression | total_cap_ff | 9 | 0.0647768 | 0.143008 |
| within_family_even_odd | ridge_regression | output_node_cap_ff | 9 | 0.100423 | 0.21406 |

## Split inventory

| protocol | split | held-out family | train | test |
|---|---|---|---:|---:|
| within_family_even_odd | `within_smcnr_se_2st_amp_even_odd` | `smcnr_se_2st_amp` | 9 | 9 |
| leave_family_out | `leave_family_out_alfio_raffc_pin_3` | `alfio_raffc_pin_3` | 54 | 5 |
| leave_family_out | `leave_family_out_fan_smc_pin_3` | `fan_smc_pin_3` | 54 | 5 |
| leave_family_out | `leave_family_out_hoilee_affc_pin_3` | `hoilee_affc_pin_3` | 58 | 1 |
| leave_family_out | `leave_family_out_leung_dfcfc1_pin_3` | `leung_dfcfc1_pin_3` | 58 | 1 |
| leave_family_out | `leave_family_out_leung_dfcfc2_pin_3` | `leung_dfcfc2_pin_3` | 47 | 12 |
| leave_family_out | `leave_family_out_leung_nmcf_pin_3` | `leung_nmcf_pin_3` | 54 | 5 |
| leave_family_out | `leave_family_out_leung_nmcnr_pin_3` | `leung_nmcnr_pin_3` | 58 | 1 |
| leave_family_out | `leave_family_out_peng_acbc_pin_3` | `peng_acbc_pin_3` | 58 | 1 |
| leave_family_out | `leave_family_out_qu2017_azc_pin_3` | `qu2017_azc_pin_3` | 58 | 1 |
| leave_family_out | `leave_family_out_ramos_pfc_pin_3` | `ramos_pfc_pin_3` | 58 | 1 |
| leave_family_out | `leave_family_out_sau_cfcc_pin_3` | `sau_cfcc_pin_3` | 54 | 5 |
| leave_family_out | `leave_family_out_smcnr_se_2st_amp` | `smcnr_se_2st_amp` | 40 | 19 |
| leave_family_out | `leave_family_out_tan_clia_pin_3` | `tan_clia_pin_3` | 58 | 1 |
| leave_family_out | `leave_family_out_yan_az_pin_3` | `yan_az_pin_3` | 58 | 1 |

## Warnings

- within_family_even_odd measures local interpolation inside the chosen design family.
- leave_family_out measures cross-family transfer and is harsh when most held-out families have only one graph.
- SMCNR currently dominates controlled sizing variants; report protocol-specific metrics instead of one random-split score.
