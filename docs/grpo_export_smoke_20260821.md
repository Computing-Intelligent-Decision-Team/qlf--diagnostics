# GRPO export contract smoke result

Date: 2026-08-21

## Goal

Validate the proposed `grpo_export_contract.v1` with a real local AnalogGym-Opt GRPO smoke run, using the same public demo entry point documented by AnalogGym-Opt.

This is an interface validation, not a claim that the one-step GRPO policy is optimized.

## Source run

| field | value |
|---|---|
| AnalogGym-Opt checkout | `/home/qlf/IOT/references/AnalogGym-Opt-9f2cbba1463efeb5d6160311630e5d56b297f9bf` |
| command | `conda run -n analoggym python main_AMP_grpo.py --circuit amp_dfcfc2 --steps 1 --mode tt-only` |
| run id | `grpo_amp_dfcfc2_20260821-204623` |
| mode | `tt-only` |
| steps | `1` |
| total training designs | `8` |
| final TT designs | `20` |
| recommended TT candidates | `5` |

The smoke run completed and wrote AnalogGym-Opt artifacts under:

```text
/home/qlf/IOT/references/AnalogGym-Opt-9f2cbba1463efeb5d6160311630e5d56b297f9bf/training_saves/grpo_amp_dfcfc2_20260821-204623/
```

## Export artifact

The qlf diagnostics export is:

```text
generated/grpo_exports/grpo_amp_dfcfc2_smoke_20260821/export.json
```

Validation command:

```bash
python3 -m tools.analog_harness.ml.grpo_export_contract validate \
  generated/grpo_exports/grpo_amp_dfcfc2_smoke_20260821/export.json
```

Result:

```json
{
  "status": "ok",
  "candidate_count": 4
}
```

The converter found 4 unique candidates with real action vectors and skipped 13 historical/log records that did not contain both `action_normalized` and `action_real`.

## Exported candidates

| candidate | M_M12 | reward | PM feasible |
|---|---:|---:|---|
| `grpo_amp_dfcfc2_20260821-204623_tt_0001` | 363 | -0.041849874619075106 | true |
| `grpo_amp_dfcfc2_20260821-204623_tt_0002` | 178 | -0.07030978527670353 | true |
| `grpo_amp_dfcfc2_20260821-204623_tt_0003` | 127 | -0.13832257862402622 | true |
| `grpo_amp_dfcfc2_20260821-204623_tt_0004` | 500 | -0.29457988872767804 | true |

## PCS L0 ingest check

The export was converted into the PCS manifest input format:

```text
generated/grpo_exports/grpo_amp_dfcfc2_smoke_20260821/pcs_manifest_input.jsonl
```

Then PCS `analoggym_grpo_manifest` was run against the AnalogGym-aligned derived config:

```text
/home/qlf/IOT/references/pcs-harness-align-origin-main-20260815/generated/analog_harness/auto_grpo_configs_v1/leung_dfcfc2_pin_3.analoggym_action_space_v1.yaml
```

Result:

| item | count |
|---|---:|
| input candidates | 4 |
| L0 replayable candidates | 4 |
| L0 invalid candidates | 0 |

PCS L0 bundle:

```text
generated/grpo_exports/grpo_amp_dfcfc2_smoke_20260821/pcs_l0/
```

## Important bug found and fixed

During the first L0 attempt, all four candidates were incorrectly labeled invalid because the JSON export did not preserve the original action vector order. The temporary conversion used `sizing.keys()`, but JSON output sorts object keys; this mismatched `action_names` and `action_real`.

Fix:

```text
grpo_export_contract.v1 now requires top-level action_parameter_names.
Consumers must use this order and must not reconstruct action order from object keys.
```

After regenerating the export and PCS input JSONL with `action_parameter_names`, PCS L0 accepted 4/4 candidates.

## Boundary

- No GRPO reward/policy/action-space code was modified.
- No PCS layout, DRC, LVS, PEX, or post-layout simulation was run.
- These 4 candidates are only L0-replayable sizing candidates. They are not parasitic graph training samples until they pass L1--L6 and raw-PEX graph parsing.
