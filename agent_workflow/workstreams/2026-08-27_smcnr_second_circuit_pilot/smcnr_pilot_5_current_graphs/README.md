# SMCNR 5-Graph Pilot Pack

- source_dataset: `references/pcs-harness-align-origin-main-20260815/generated/analog_harness/parasitic_modeling/graph_learning_samples_20260817_32graphs_smcnr_combo_v1`
- purpose: baseline + selected perturbations for second-circuit parasitic-modeling pilot.

## Pilot Rows

| sample | family | closure | raw_spice_verified | cap_count | total_cap_ff | output_node_cap_ff |
|---|---|---|---:|---:|---:|---:|
| `smcnr_sizing_sweep_20260817_v1/smcnr_sweep_0000_baseline` | `smcnr_sizing_sweep_20260817_v1` | `L6_post_layout_pvt` | True | 33.0 | 764.45058 | 645.62162 |
| `smcnr_sizing_sweep_20260817_v1/smcnr_sweep_0001_diff_pair_w_m5pct` | `smcnr_sizing_sweep_20260817_v1` | `L6_post_layout_pvt` | True | 33.0 | 763.42667 | 645.54552 |
| `smcnr_sizing_sweep_20260817_v1/smcnr_sweep_0002_diff_pair_w_p5pct` | `smcnr_sizing_sweep_20260817_v1` | `L6_post_layout_pvt` | True | 33.0 | 765.46556 | 645.69675 |
| `smcnr_sizing_sweep_20260817_v1/smcnr_sweep_0005_second_stage_pmos_w_p5pct` | `smcnr_sizing_sweep_20260817_v1` | `L6_post_layout_pvt` | True | 33.0 | 764.57809 | 645.69652 |
| `smcnr_sizing_sweep_combo_20260817_v1/smcnr_combo_0014_load_p_nmos_p5` | `smcnr_sizing_sweep_combo_20260817_v1` | `L6_post_layout_pvt` | True | 32.0 | 763.67029 | 645.06645 |

## Files

- `pilot_graphs.json`
- `pilot_graphs.jsonl`

## Verification

- selected_graphs: 5
- missing_required_checks_in_source_dataset: 0
- selected rows have `metadata.closure_level == L6_post_layout_pvt` and `metadata.raw_spice_source_verified == true`.
