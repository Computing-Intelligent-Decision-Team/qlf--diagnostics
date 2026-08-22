# Batch v4 sampling recommendation from physical_closure_classifier_v1

Generated: 2026-08-22T15:14:18.256986+00:00

## Evidence scope

- Input samples: 48 GRPO→PCS admission records from configured summaries.
- Admitted L6 raw-PEX graph samples: 12.
- Status counts: {'admitted_raw_pex_graph': 12, 'physical_closure_failed': 25, 'raw_pex_available_not_l6': 8, 'simulation_timeout_or_hang': 3}.
- This is a diagnostic small-data classifier, not a production feasibility oracle.
- Action-space must not be hard-coded from this result; every candidate still needs L0→L6 admission.

## Model sanity check

- `dummy_most_frequent` LOO balanced_accuracy=0.500, accuracy=0.750, f1=0.000, cm={'tp': 0, 'tn': 36, 'fp': 0, 'fn': 12}
- `logistic_l2_balanced` LOO balanced_accuracy=0.431, accuracy=0.521, f1=0.207, cm={'tp': 3, 'tn': 22, 'fp': 14, 'fn': 9}
- `decision_tree_depth3_balanced` LOO balanced_accuracy=0.528, accuracy=0.583, f1=0.333, cm={'tp': 5, 'tn': 23, 'fp': 13, 'fn': 7}

## Strongest current feature signals

- `sizing__mosfet_18_7_m_biascm_nmos`: mean admitted=5.25, mean not-admitted=20.92, standardized effect=1.003
- `action_norm_17`: mean admitted=-0.8251, mean not-admitted=-0.1893, standardized effect=1.002
- `sizing__mosfet_23_2_w_load2_nmos`: mean admitted=4.158, mean not-admitted=6.578, standardized effect=0.737
- `action_norm_18`: mean admitted=-0.2283, mean not-admitted=0.2803, standardized effect=0.737
- `mos_width_times_m_sum`: mean admitted=1941, mean not-admitted=2865, standardized effect=0.734
- `nmos_m_max`: mean admitted=33.08, mean not-admitted=41.92, standardized effect=0.699
- `mos_w_all_max`: mean admitted=8.942, mean not-admitted=9.675, standardized effect=0.676
- `nmos_l_min`: mean admitted=0.7167, mean not-admitted=1.267, standardized effect=0.652
- `pmos_w_max`: mean admitted=8.075, mean not-admitted=9.181, standardized effect=0.633
- `nmos_m_mean`: mean admitted=18.31, mean not-admitted=24.2, standardized effect=0.624
- `nmos_m_sum`: mean admitted=54.92, mean not-admitted=72.61, standardized effect=0.624
- `sizing__mosfet_12_1_w_gmf2_pmos`: mean admitted=3.617, mean not-admitted=5.133, standardized effect=0.609

## Recommended batch v4 policy

1. Keep using the same AnalogGym action-space contract; do not shrink it by a single M12 threshold.
2. Export a larger candidate pool first, then stratify candidates by the classifier risk score into low/medium/high predicted closure likelihood.
3. Sample all three strata deliberately: high-likelihood candidates grow the training graph set, while medium/high-risk candidates keep the failure boundary visible.
4. Prefer combinations that diversify the top feature signals above, especially full W/L/M/cap/bias combinations rather than only sweeping M12.
5. For the next practical run, target 24–36 candidates and report admitted/raw-not-L6/no-raw separately.
6. Treat this classifier as a sampling guide only; final dataset admission remains actual L0→L6 + raw PEX graph evidence.
