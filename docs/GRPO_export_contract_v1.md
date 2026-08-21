# GRPO export contract v1

Date: 2026-08-21

## Purpose

This document defines the minimum exchange format for sending AnalogGym-Opt / GRPO sizing candidates into the PCS admission pipeline.

The contract exists to prevent a common but dangerous shortcut:

```text
GRPO produced a sizing-like record
=> treat it as a PEX training sample
```

That shortcut is invalid. A GRPO record is only an upstream candidate. It becomes a parasitic graph training sample only after the PCS side accepts it through:

```text
GRPO export
-> action-space contract check
-> L0 ingest contract
-> L1--L6 physical replay
-> raw *_extracted.raw.spice capacitor parsing
-> graph_training_admitted
```

## Scope

This v1 contract targets the first aligned smoke case:

| field | value |
|---|---|
| AnalogGym circuit | `amp_dfcfc2` |
| PCS design | `leung_dfcfc2_pin_3` |
| action-space contract | `amp_dfcfc2_to_leung_dfcfc2_pin_3.analoggym_action_space_v1` |
| first validation mode | `tt-only`, `steps=1` |

The smoke run is not meant to prove GRPO quality. It proves the export interface can preserve enough provenance and action data for PCS L0 admission.

## Required top-level JSON fields

```json
{
  "schema_version": "grpo_export_contract.v1",
  "source_repo": "/absolute/path/to/AnalogGym-Opt checkout",
  "source_commit": "git commit hash or unknown",
  "circuit_id": "amp_dfcfc2",
  "pcs_design_id": "leung_dfcfc2_pin_3",
  "action_space_contract_id": "amp_dfcfc2_to_leung_dfcfc2_pin_3.analoggym_action_space_v1",
  "action_parameter_names": ["W_M0", "L_M0", "M_M0"],
  "run_id": "grpo_amp_dfcfc2_YYYYMMDD-HHMMSS",
  "run_dir": "/absolute/path/to/training_saves/run_id",
  "mode": "tt-only",
  "steps": 1,
  "seed": null,
  "candidate_count": 1,
  "skipped_records_without_actions": 0,
  "candidates": []
}
```

## Required candidate fields

Each candidate must contain the actual GRPO action, not just metrics:

```json
{
  "candidate_id": "grpo_amp_dfcfc2_YYYYMMDD-HHMMSS_tt_0001",
  "provenance_kind": "fresh_local_grpo_smoke",
  "source_file_group": "recommended_candidates_tt",
  "episode": "final_0",
  "design_idx": 0,
  "rank": 1,
  "candidate_source": "final_test",
  "evaluation_source": "tt",
  "action_normalized": [0.0],
  "action_real": [1.0],
  "sizing": {
    "W_M0": 1.0,
    "L_M0": 1.0,
    "M_M0": 4
  },
  "reward": -0.25,
  "utility": -0.25,
  "pm_feasible": true,
  "pm_violation": 0.0,
  "objective_rewards": {},
  "pre_layout_metrics": {}
}
```

The exact vector length for `amp_dfcfc2` is 27. The action order is inherited from `circuit_configs/amp_dfcfc2.yaml` by iterating `device` entries and each device's `range` keys in YAML order.
The exporter must store this order explicitly in top-level `action_parameter_names`; consumers must not reconstruct the order from sorted JSON object keys.

For the current public demo config, the order is:

```text
W_M0, L_M0, M_M0,
W_M8, L_M8, M_M8,
W_M10, L_M10, M_M10,
W_M11, L_M11, M_M11,
W_M12, L_M12, M_M12,
W_M18, L_M18, M_M18,
W_M23, L_M23, M_M23,
W_M25, L_M25, M_M25,
I_Ib,
M_C0,
M_C1
```

## Explicit rejection rules

A record is not a valid GRPO export candidate if:

- `action_normalized` is missing.
- `action_real` is missing.
- `action_real` length differs from the circuit action dimension.
- `action_real` length differs from `action_parameter_names`.
- only metrics/reward are available.
- the candidate is manually edited after GRPO generation.
- the action-space contract id is missing or mismatched.

Metrics-only historical records can still be useful for narrative debugging, but they cannot be used as PCS replay inputs because sizing cannot be reconstructed safely from performance.

## Provenance kinds

| provenance_kind | meaning |
|---|---|
| `fresh_local_grpo_smoke` | locally rerun from the AnalogGym-Opt entry point only to validate export wiring |
| `historical_grpo_search` | historical training/evaluation candidate with saved action vectors |
| `checkpoint_inference` | candidate sampled from a saved GRPO checkpoint |

This task uses `fresh_local_grpo_smoke`.

## Minimal validation commands

Build from an AnalogGym-Opt run:

```bash
python3 -m tools.analog_harness.ml.grpo_export_contract build-from-analoggym-run \
  --run-dir /path/to/AnalogGym-Opt/training_saves/grpo_amp_dfcfc2_YYYYMMDD-HHMMSS \
  --circuit-config /path/to/AnalogGym-Opt/circuit_configs/amp_dfcfc2.yaml \
  --source-repo /path/to/AnalogGym-Opt \
  --circuit-id amp_dfcfc2 \
  --pcs-design-id leung_dfcfc2_pin_3 \
  --action-space-contract-id amp_dfcfc2_to_leung_dfcfc2_pin_3.analoggym_action_space_v1 \
  --mode tt-only \
  --steps 1 \
  --output generated/grpo_exports/grpo_amp_dfcfc2_smoke_YYYYMMDD/export.json
```

Validate an export:

```bash
python3 -m tools.analog_harness.ml.grpo_export_contract validate \
  generated/grpo_exports/grpo_amp_dfcfc2_smoke_YYYYMMDD/export.json
```

## Boundary

This contract does not require a candidate to reach L6. It only proves that the upstream GRPO run produced replayable sizing information. PCS physical closure remains a later admission stage.
