# 52-graph GRPO-extended parasitic dataset v2

This dataset extends the 50-graph GRPO-extended dataset with two GRPO-to-PCS admission smoke samples that reached raw-PEX graph admission.

## Inputs

- Base dataset: `generated/analog_harness/parasitic_modeling/graph_learning_samples_20260821_50graphs_grpo_extended_v1`
- Admission smoke source: `generated/analog_harness/grpo_smoke_l1_l6_admission_20260822_v1/admission_smoke_v1_summary`

## Counts

- Base graphs: 50
- Added GRPO admission smoke graphs: 2
- Total graphs: 52
- Total nodes: 778
- Total edges: 4591

## Added samples

| graph_id | design_id | nodes | edges | total_cap_ff | raw_pex_sha256 |
|---|---|---:|---:|---:|---|
| `grpo_to_pcs_admission_smoke_v1/grpo_leung_dfcfc2_0000` | `leung_dfcfc2_pin_3` | 19 | 134 | 3999.37 | `8115cd3da42a76660ac578ab6d11e08ffa2d09cbd3eaba0f3027c7fc2e0865a1` |
| `grpo_to_pcs_admission_smoke_v1/grpo_leung_dfcfc2_0001` | `leung_dfcfc2_pin_3` | 19 | 127 | 3169.88 | `19a57d0079146af75d40f3eafd28f7d6c65a5e552e30e4d279e0e31b39c7b095` |

## Evidence boundary

- The admitted samples have L6 raw-PEX graph evidence.
- The remaining smoke records are retained in the admission summary and kept outside graph-training labels.
- The dataset remains MOS-only/current PCS extraction-scope aligned.
- The active smoke config records performance as observation-only.
