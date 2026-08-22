# Batch v4 sampling recommendation from physical_closure_classifier_v1

Generated: 2026-08-22T10:41:07.007043+00:00

## Evidence scope

- Input samples: 24 GRPO→PCS admission records from batch v2+v3.
- Admitted L6 raw-PEX graph samples: 7.
- Status counts: {'admitted_raw_pex_graph': 7, 'physical_closure_failed': 13, 'raw_pex_available_not_l6': 4}.
- This is a diagnostic small-data classifier, not a production feasibility oracle.
- Action-space must not be hard-coded from this result; every candidate still needs L0→L6 admission.

## Model sanity check

- `dummy_most_frequent` LOO balanced_accuracy=0.500, accuracy=0.708, f1=0.000, cm={'tp': 0, 'tn': 17, 'fp': 0, 'fn': 7}
- `logistic_l2_balanced` LOO balanced_accuracy=0.277, accuracy=0.333, f1=0.111, cm={'tp': 1, 'tn': 7, 'fp': 10, 'fn': 6}
- `decision_tree_depth3_balanced` LOO balanced_accuracy=0.727, accuracy=0.792, f1=0.615, cm={'tp': 4, 'tn': 15, 'fp': 2, 'fn': 3}

## Strongest current feature signals

- `mos_width_times_m_sum`: mean admitted=1953, mean not-admitted=2812, standardized effect=0.974
- `action_norm_12`: mean admitted=-0.4116, mean not-admitted=-0.03701, standardized effect=0.721
- `sizing__mosfet_12_1_w_gmf2_pmos`: mean admitted=3.3, mean not-admitted=5.071, standardized effect=0.718
- `action_norm_20`: mean admitted=0.1766, mean not-admitted=0.6279, standardized effect=0.693
- `sizing__mosfet_23_2_m_load2_nmos`: mean admitted=30, mean not-admitted=40.88, standardized effect=0.683
- `sizing__mosfet_25_1_m_gm3_nmos`: mean admitted=30.43, mean not-admitted=19.65, standardized effect=0.676
- `action_norm_18`: mean admitted=-0.1242, mean not-admitted=0.3056, standardized effect=0.676
- `action_norm_23`: mean admitted=0.2026, mean not-admitted=-0.2344, standardized effect=0.674
- `sizing__mosfet_23_2_w_load2_nmos`: mean admitted=4.657, mean not-admitted=6.694, standardized effect=0.674
- `mos_aspect_times_m_sum`: mean admitted=1459, mean not-admitted=2645, standardized effect=0.658
- `pmos_w_max`: mean admitted=8.171, mean not-admitted=9.324, standardized effect=0.650
- `action_norm_25`: mean admitted=0.55, mean not-admitted=0.08215, standardized effect=0.636

## Recommended batch v4 policy

1. Keep using the same AnalogGym action-space contract; do not shrink it by a single M12 threshold.
2. Export a larger candidate pool first, then stratify candidates by the classifier risk score into low/medium/high predicted closure likelihood.
3. Sample all three strata deliberately: high-likelihood candidates grow the training graph set, while medium/high-risk candidates keep the failure boundary visible.
4. Prefer combinations that diversify the top feature signals above, especially full W/L/M/cap/bias combinations rather than only sweeping M12.
5. For the next practical run, target 24–36 candidates and report admitted/raw-not-L6/no-raw separately.
6. Treat this classifier as a sampling guide only; final dataset admission remains actual L0→L6 + raw PEX graph evidence.
