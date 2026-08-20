# Sample Admission Registry Summary — 2026-08-20

This document summarizes the current admission table used to decide which
parasitic graph rows are safe for default research training.

## Inputs

The registry joins four evidence sources from the PCS workspace:

```text
generated/analog_harness/l0_existing_l6_audit_20260819_v1/l0_ingest_contract_records.jsonl
generated/analog_harness/parasitic_modeling/graph_learning_samples_20260819_51graphs_alfio_effective_v2_v1/graphs.jsonl
generated/analog_harness/grpo_admission_20260819_v1/admission_summary.json
generated/analog_harness/grpo_m12_bound_experiment_20260819_v1/full_l6_all8_admission_audit.json
```

## Rebuild command

```bash
python3 -m tools.analog_harness.cli sample-admission-registry \
  --l0-records-jsonl generated/analog_harness/l0_existing_l6_audit_20260819_v1/l0_ingest_contract_records.jsonl \
  --graphs-jsonl generated/analog_harness/parasitic_modeling/graph_learning_samples_20260819_51graphs_alfio_effective_v2_v1/graphs.jsonl \
  --default-grpo-admission-json generated/analog_harness/grpo_admission_20260819_v1/admission_summary.json \
  --grpo-diagnostic-json generated/analog_harness/grpo_m12_bound_experiment_20260819_v1/full_l6_all8_admission_audit.json \
  --output-dir generated/analog_harness/sample_admission_registry_20260820_v1
```

## Registry counts

| metric | count |
|---|---:|
| records | 89 |
| designs | 14 |
| L0 pass | 78 |
| L6 pass | 75 |
| raw PEX available | 56 |
| selected graph dataset rows | 51 |
| GRPO-related records | 18 |

## Status buckets

| status | meaning | count |
|---|---|---:|
| `graph_training_admitted` | L0/L6/raw-PEX provenance matched selected graph row | 48 |
| `graph_without_l0_match` | graph row exists but no clean matching L0/L6 record | 3 |
| `incomplete_admission` | historical L6 backfill exists but raw-PEX/local path provenance is incomplete | 19 |
| `l0_invalid_sizing` | default PCS config rejects GRPO sizing at L0 | 8 |
| `l6_not_in_graph_dataset` | L6/raw-PEX exists but not in the selected graph dataset | 5 |
| `physical_replay_failed` | candidate passed diagnostic L0 but did not reach L6 | 6 |

## Default training policy

Default research training uses only:

```text
sample_admission_status = graph_training_admitted
```

This keeps 48 of the selected 51 graph rows.

Excluded provenance-warning rows:

```text
leung_nmcnr_pin_3:cand_0001
qu2017_azc_pin_3:cand_0001
tan_clia_pin_3:cand_0001
```

Reason: each has a regenerated raw-PEX graph row, but the corresponding local
regenerated state is only `L4_layout_verified_mos_only`.  They should not be
silently used as L6-backed training samples.

## Filtered baseline command

```bash
for profile in no_total_cap_leakage structure_only leaky_smoke_test; do
  python3 -m tools.analog_harness.parasitic_graph_training_baseline \
    --graphs-jsonl generated/analog_harness/parasitic_modeling/graph_learning_samples_20260819_51graphs_alfio_effective_v2_v1/graphs.jsonl \
    --admission-registry-json generated/analog_harness/sample_admission_registry_20260820_v1/sample_admission_registry.json \
    --feature-profile "$profile" \
    --output-dir "generated/analog_harness/parasitic_modeling/graph_training_baseline_48admitted_20260820_v1/$profile"
done

python3 -m tools.analog_harness.parasitic_profile_comparison \
  --profile-root generated/analog_harness/parasitic_modeling/graph_training_baseline_48admitted_20260820_v1 \
  --output-dir generated/analog_harness/parasitic_modeling/profile_comparison_48admitted_20260820_v1
```

## Current filtered smoke metrics

For `no_total_cap_leakage`:

| model | cap_count MAE | total_cap_ff MAE | output_node_cap_ff MAE |
|---|---:|---:|---:|
| mean baseline | 41.9778 | 293.482 | 295.907 |
| nearest neighbor | 1.52083 | 84.2825 | 20.415 |
| ridge regression | 0.906265 | 88.1332 | 21.7339 |

These are data-pipeline diagnostics only.  The dataset is still too small and
too family-skewed for final modeling claims.
