# GRPO-to-PCS admission batch v2 failure-pattern analysis

Date: 2026-08-22

## Executive summary

This note summarizes the 12-candidate `leung_dfcfc2_pin_3` GRPO-to-PCS batch v2 admission result. It is an evidence snapshot for deciding the next GRPO sampling batch, not a final statistical claim.

Key result:

- 3 / 12 candidates entered the strict graph-training dataset (`L6_post_layout_pvt + raw PEX`).
- 2 candidates produced raw PEX but failed connectivity LVS; these remain diagnostic raw-PEX rows.
- 7 candidates stopped at MAGICAL place-route and have no raw PEX graph.

## Artifact map

- `generated/grpo_to_pcs_admission_batch_v2_20260822/admission_summary_v2.json`
- `generated/grpo_to_pcs_admission_batch_v2_20260822/admitted_graphs_v2.jsonl`
- `generated/grpo_to_pcs_admission_batch_v2_20260822/physical_closure_failure_labels_v2.jsonl`
- `generated/grpo_to_pcs_admission_batch_v2_20260822/raw_pex_available_not_l6_v2.jsonl`
- `generated/parasitic_modeling/graph_learning_samples_20260822_55graphs_grpo_batch_v2_dataset_v3/graphs.jsonl`
- `generated/parasitic_modeling/profile_comparison_55graphs_grpo_batch_v2_dataset_v3/profile_comparison.md`
- `generated/parasitic_modeling/family_aware_eval_55graphs_grpo_batch_v2_dataset_v3/no_total_cap_leakage/report.md`

## Candidate-level admission table

| candidate | status | closure | fail stage | M12.M | C0 | C1 | Ibias | raw caps | total cap fF |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| `grpo_leung_dfcfc2_0000` | `admitted_raw_pex_graph` | `L6_post_layout_pvt` | `` | 389 | 19 | 1 | 20.4375 | 131 | 1762.34 |
| `grpo_leung_dfcfc2_0001` | `physical_closure_failed` | `L2_pre_layout_pvt` | `magical_place_route` | 442 | 30 | 1 | 30 |  |  |
| `grpo_leung_dfcfc2_0002` | `physical_closure_failed` | `L2_pre_layout_pvt` | `magical_place_route` | 393 | 23 | 1 | 15.2713 |  |  |
| `grpo_leung_dfcfc2_0003` | `physical_closure_failed` | `L2_pre_layout_pvt` | `magical_place_route` | 444 | 1 | 22 | 1 |  |  |
| `grpo_leung_dfcfc2_0004` | `physical_closure_failed` | `L2_pre_layout_pvt` | `magical_place_route` | 437 | 22 | 1 | 15.3054 |  |  |
| `grpo_leung_dfcfc2_0005` | `raw_pex_available_not_l6` | `L2_pre_layout_pvt` | `connectivity_lvs` | 339 | 1 | 15 | 30 | 119 | 2631.76 |
| `grpo_leung_dfcfc2_0006` | `raw_pex_available_not_l6` | `L2_pre_layout_pvt` | `connectivity_lvs` | 350 | 30 | 25 | 15.8744 | 105 | 4025.12 |
| `grpo_leung_dfcfc2_0007` | `physical_closure_failed` | `L2_pre_layout_pvt` | `magical_place_route` | 449 | 29 | 10 | 2.89453 |  |  |
| `grpo_leung_dfcfc2_0008` | `admitted_raw_pex_graph` | `L6_post_layout_pvt` | `` | 367 | 30 | 20 | 1 | 112 | 5781.05 |
| `grpo_leung_dfcfc2_0009` | `physical_closure_failed` | `L2_pre_layout_pvt` | `magical_place_route` | 352 | 18 | 2 | 1 |  |  |
| `grpo_leung_dfcfc2_0010` | `physical_closure_failed` | `L2_pre_layout_pvt` | `magical_place_route` | 397 | 30 | 1 | 30 |  |  |
| `grpo_leung_dfcfc2_0011` | `admitted_raw_pex_graph` | `L6_post_layout_pvt` | `` | 337 | 7 | 28 | 17.9361 | 129 | 3656.84 |

## Observed patterns

### Pattern A: high `M12.M` region is currently high-risk for place-route

In this batch, all 6 candidates with `M12.M >= 393` stopped at `magical_place_route`: `grpo_leung_dfcfc2_0001=442`, `grpo_leung_dfcfc2_0002=393`, `grpo_leung_dfcfc2_0003=444`, `grpo_leung_dfcfc2_0004=437`, `grpo_leung_dfcfc2_0007=449`, `grpo_leung_dfcfc2_0010=397`.

This is a strong batch-local signal, but not yet a universal hard bound. It should guide batch v3 sampling and contract annotation, not immediately rewrite the global AnalogGym action-space.

### Pattern B: lower `M12.M` is not sufficient for L6

For `M12.M < 393`, the outcomes were mixed: 3 L6, 2 raw-PEX/LVS diagnostic, and 1 place-route failure.

So `M12.M` alone cannot be the admission rule. It is one visible correlate; combinations with capacitor, current, and other multiplicity/geometry parameters still matter.

### Pattern C: raw PEX but non-L6 rows are useful diagnostics, not default training labels

The two raw-PEX diagnostic rows are:

- `grpo_leung_dfcfc2_0005`: M12.M=339, caps=119, total_cap_ff=2631.76, failure_stage=`connectivity_lvs`.
- `grpo_leung_dfcfc2_0006`: M12.M=350, caps=105, total_cap_ff=4025.12, failure_stage=`connectivity_lvs`.

They can be used to debug connectivity/LVS sensitivity, but the default graph-learning dataset keeps the cleaner rule: only `L6_post_layout_pvt + raw PEX`.

## Parameter summary by admission status

| parameter | admitted mean/range | raw-PEX-not-L6 mean/range | no-raw failure mean/range |
|---|---:|---:|---:|
| `mosfet_12_1_m_gmf2_pmos` | 364.3 / [337, 389] | 344.5 / [339, 350] | 416.3 / [352, 449] |
| `capacitor_0` | 18.67 / [7, 30] | 15.5 / [1, 30] | 21.86 / [1, 30] |
| `capacitor_1` | 16.33 / [1, 28] | 20 / [15, 25] | 5.429 / [1, 22] |
| `current_0_bias` | 13.12 / [1, 20.44] | 22.94 / [15.87, 30] | 13.64 / [1, 30] |
| `mosfet_8_2_m_gm1_pmos` | 34 / [15, 45] | 50 / [50, 50] | 27.86 / [3, 50] |
| `mosfet_23_2_m_load2_nmos` | 34.67 / [18, 46] | 47.5 / [45, 50] | 46.43 / [25, 50] |
| `mosfet_11_1_m_gm2_pmos` | 20.67 / [17, 23] | 17.5 / [1, 34] | 21.71 / [5, 39] |
| `mosfet_25_1_m_gm3_nmos` | 27.67 / [3, 50] | 1.5 / [1, 2] | 19 / [5, 33] |
| `mosfet_0_8_l_biascm_pmos` | 2.4 / [1.1, 4] | 1.85 / [0.5, 3.2] | 0.9 / [0.5, 3.2] |
| `mosfet_11_1_w_gm2_pmos` | 3.567 / [2.2, 5.5] | 2.85 / [1.3, 4.4] | 1.743 / [0.5, 3.6] |
| `mosfet_12_1_w_gmf2_pmos` | 5.167 / [4.5, 5.6] | 5.6 / [4.4, 6.8] | 3.671 / [2.4, 4.8] |
| `mosfet_18_7_l_biascm_nmos` | 2.8 / [2.2, 3.5] | 2.05 / [1.6, 2.5] | 1.614 / [0.6, 2.1] |
| `mosfet_18_7_m_biascm_nmos` | 5.333 / [1, 13] | 1 / [1, 1] | 21.14 / [1, 39] |

## Recommended batch v3 design

1. Keep the same PCS admission gate: `L0 replayable → L1/L2 → layout/DRC/LVS/PEX → raw graph`, with default graph training admission requiring `L6 + raw PEX`.
2. Allocate batch v3 candidates into three buckets:
   - L6-neighborhood bucket around the admitted M12 values 337, 367, and 389.
   - Boundary bucket around M12 389 to 397 to test whether the observed high-risk transition repeats.
   - Diagnostic bucket near the two raw-PEX/LVS rows 339 and 350 to study connectivity failure without mixing them into default training.
3. Keep rejected rows as admission labels. They are not parasitic graph samples, but they are evidence for physical feasibility modeling.

## Boundary of interpretation

This batch has only 12 candidates, so it should not be used to declare a universal physical constraint. The correct interpretation is: batch v2 provides a first local admission map for `leung_dfcfc2_pin_3` under the current PCS/Magic/MOS-only extraction contract.
