# Family-aware parasitic graph evaluation

- schema_version: `parasitic_family_aware_evaluation.v1`
- feature_profile: `structure_only`
- splits: 15
- within_family_splits: 1
- leave_family_out_splits: 14

## Protocol summary

| protocol | model | target | samples | MAE | max abs error |
|---|---|---|---:|---:|---:|
| leave_family_out | mean_baseline | cap_count | 64 | 48.2225 | 89.1111 |
| leave_family_out | mean_baseline | total_cap_ff | 64 | 1094.44 | 5271.82 |
| leave_family_out | mean_baseline | output_node_cap_ff | 64 | 330.381 | 631.791 |
| leave_family_out | nearest_neighbor | cap_count | 64 | 22.7969 | 67 |
| leave_family_out | nearest_neighbor | total_cap_ff | 64 | 1227.57 | 5564.38 |
| leave_family_out | nearest_neighbor | output_node_cap_ff | 64 | 197.202 | 643.379 |
| leave_family_out | ridge_regression | cap_count | 64 | 4.0664 | 9.79519 |
| leave_family_out | ridge_regression | total_cap_ff | 64 | 3812.36 | 9612.46 |
| leave_family_out | ridge_regression | output_node_cap_ff | 64 | 179.707 | 547.661 |
| within_family_even_odd | mean_baseline | cap_count | 6 | 7.33333 | 12.5 |
| within_family_even_odd | mean_baseline | total_cap_ff | 6 | 940.354 | 3531.9 |
| within_family_even_odd | mean_baseline | output_node_cap_ff | 6 | 0 | 0 |
| within_family_even_odd | nearest_neighbor | cap_count | 6 | 5.5 | 10 |
| within_family_even_odd | nearest_neighbor | total_cap_ff | 6 | 1266.29 | 4336.25 |
| within_family_even_odd | nearest_neighbor | output_node_cap_ff | 6 | 0 | 0 |
| within_family_even_odd | ridge_regression | cap_count | 6 | 0.352636 | 0.557627 |
| within_family_even_odd | ridge_regression | total_cap_ff | 6 | 1109.04 | 3578.97 |
| within_family_even_odd | ridge_regression | output_node_cap_ff | 6 | 0 | 0 |

## Split inventory

| protocol | split | held-out family | train | test |
|---|---|---|---:|---:|
| within_family_even_odd | `within_leung_dfcfc2_pin_3_even_odd` | `leung_dfcfc2_pin_3` | 6 | 6 |
| leave_family_out | `leave_family_out_alfio_raffc_pin_3` | `alfio_raffc_pin_3` | 59 | 5 |
| leave_family_out | `leave_family_out_fan_smc_pin_3` | `fan_smc_pin_3` | 59 | 5 |
| leave_family_out | `leave_family_out_hoilee_affc_pin_3` | `hoilee_affc_pin_3` | 63 | 1 |
| leave_family_out | `leave_family_out_leung_dfcfc1_pin_3` | `leung_dfcfc1_pin_3` | 63 | 1 |
| leave_family_out | `leave_family_out_leung_dfcfc2_pin_3` | `leung_dfcfc2_pin_3` | 47 | 17 |
| leave_family_out | `leave_family_out_leung_nmcf_pin_3` | `leung_nmcf_pin_3` | 59 | 5 |
| leave_family_out | `leave_family_out_leung_nmcnr_pin_3` | `leung_nmcnr_pin_3` | 63 | 1 |
| leave_family_out | `leave_family_out_peng_acbc_pin_3` | `peng_acbc_pin_3` | 63 | 1 |
| leave_family_out | `leave_family_out_qu2017_azc_pin_3` | `qu2017_azc_pin_3` | 63 | 1 |
| leave_family_out | `leave_family_out_ramos_pfc_pin_3` | `ramos_pfc_pin_3` | 63 | 1 |
| leave_family_out | `leave_family_out_sau_cfcc_pin_3` | `sau_cfcc_pin_3` | 59 | 5 |
| leave_family_out | `leave_family_out_smcnr_se_2st_amp` | `smcnr_se_2st_amp` | 45 | 19 |
| leave_family_out | `leave_family_out_tan_clia_pin_3` | `tan_clia_pin_3` | 63 | 1 |
| leave_family_out | `leave_family_out_yan_az_pin_3` | `yan_az_pin_3` | 63 | 1 |

## Warnings

- within_family_even_odd measures local interpolation inside the chosen design family.
- leave_family_out measures cross-family transfer and is harsh when most held-out families have only one graph.
- SMCNR currently dominates controlled sizing variants; report protocol-specific metrics instead of one random-split score.
