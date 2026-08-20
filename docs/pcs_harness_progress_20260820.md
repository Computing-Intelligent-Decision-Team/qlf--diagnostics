# PCS Harness / Parasitic Modeling Progress Handoff — 2026-08-20

This is a lightweight progress handoff for senior review.  It intentionally
does not include raw GDS, raw SPICE, or the full `generated/analog_harness/`
tree.  The purpose is to let another Codex session inspect whether the
experiment contract and provenance decisions are consistent with the upstream
PCS Harness direction.

## Source workspace

| item | value |
|---|---|
| PCS repo | `https://github.com/Computing-Intelligent-Decision-Team/pcs-harness.git` |
| local branch | `align/origin-main-20260815` |
| local HEAD used for this handoff | `075382809bfa65b981eacfb645a28fe35f52b1e3` |
| diagnostics repo branch | `pcs-harness-progress-20260820` |

## What changed conceptually

The current work did not try to modify MAGICAL behavior or manually tune
layouts.  The main result is an admission/provenance layer for parasitic
modeling:

```text
upstream/control sizing
  -> L0 ingest-contract check
  -> PCS physical replay / L1-L6 evidence
  -> raw PEX graph parsing
  -> sample admission registry
  -> default graph-training filter
```

L0 is now an explicit source-state/evidence concept:

```text
closure_level = L0_ingest_contract_checked
evidence[0].stage = ingest_contract_check
```

L0 means the candidate can be named, mapped, unit-checked, hashed, and checked
against a target PCS config.  It does **not** mean layout, DRC, LVS, PEX, or
post-layout simulation succeeded.  L1-L6 remain the physical-flow levels.

## Current evidence summary

### Existing local L6 backfill

Artifact in PCS workspace:

```text
generated/analog_harness/l0_existing_l6_audit_20260819_v1/
```

Result:

| metric | count |
|---|---:|
| existing `L6_post_layout_pvt` state files | 70 |
| designs covered | 14 |
| L0 backfill pass | 70 |
| L0 backfill warn | 0 |

The backfill writes standalone L0 records instead of mutating historical
`state.json` files.

### Unified sample admission registry

Artifact in PCS workspace:

```text
generated/analog_harness/sample_admission_registry_20260820_v1/
```

Result:

| status | count |
|---|---:|
| `graph_training_admitted` | 48 |
| `graph_without_l0_match` | 3 |
| `incomplete_admission` | 19 |
| `l0_invalid_sizing` | 8 |
| `l6_not_in_graph_dataset` | 5 |
| `physical_replay_failed` | 6 |

The join key for graph admission is raw PEX SHA256, not `candidate_id`, because
many local runs reuse names such as `cand_0001`.

### GRPO smoke/admission status

Accessible public AnalogGym-Opt GRPO code was smoke-run locally for
`amp_dfcfc2`, yielding 8 real sizing candidates.

Default PCS config result:

```text
8/8 rejected at L0_invalid_sizing_for_pcs_config
reason: M_M12 maps to mosfet_12_1_m_gmf2_pmos = 227..481
current PCS generated config max = 50
```

M12 max=500 diagnostic result:

| result | count |
|---|---:|
| `L6_post_layout_pvt` | 2 |
| `magical_place_route` fail | 5 |
| `connectivity_lvs` fail | 1 |
| post-sim/PVT fail | 0 |
| timeout | 0 |

This falsifies “M12 > 50 is impossible to enter physical replay,” but it does
not prove that widening to 500 is a stable production admission rule.

## Important quarantine decision

The selected 51-graph dataset contains 3 rows marked
`graph_without_l0_match`:

```text
Leung NMCNR
Qu2017 AZC
Tan CLIA
```

These are not simple path-join misses.  Their graph metadata points at
regenerated raw PEX, but the corresponding local regenerated `state.json` files
are only:

```text
L4_layout_verified_mos_only
```

Therefore the default research training baseline now excludes them via the
sample admission registry.  The original 51-graph dataset is kept for forensics;
the default training matrix uses only 48 `graph_training_admitted` rows.

### Filtered baseline

Artifacts in PCS workspace:

```text
generated/analog_harness/parasitic_modeling/graph_training_baseline_48admitted_20260820_v1/
generated/analog_harness/parasitic_modeling/profile_comparison_48admitted_20260820_v1/
```

Non-leaky profile smoke metric:

| profile | model | target | MAE |
|---|---|---|---:|
| `no_total_cap_leakage` | ridge regression | `total_cap_ff` | 88.1332 fF |

This remains a smoke/pipeline metric, not a final model-quality claim.

## Files added/changed in PCS branch

Representative new tools:

```text
tools/analog_harness/analoggym_grpo_candidate_export.py
tools/analog_harness/analoggym_grpo_manifest.py
tools/analog_harness/grpo_admission_audit.py
tools/analog_harness/l0_existing_l6_audit.py
tools/analog_harness/sample_admission_registry.py
```

Representative modified tools:

```text
tools/analog_harness/cli.py
tools/analog_harness/sizing_candidate_manifest.py
tools/analog_harness/parasitic_graph_training_baseline.py
```

Representative docs:

```text
docs/analog_harness/CURRENT_STATUS.md
docs/analog_harness/parasitic_modeling_runbook_20260816.md
docs/analog_harness/parasitic_modeling_status_20260816.md
agent_workflow/workstreams/2026-08-19_grpo_to_pex_admission/
```

## Verification already run locally

Latest focused verification in PCS workspace:

```text
Ran 20 tests in 0.482s
OK
```

The test set covered:

```text
test_parasitic_graph_training_baseline
test_sample_admission_registry
test_l0_existing_l6_audit
test_sizing_candidate_manifest
test_analoggym_grpo_manifest
test_grpo_admission_audit
```

## Open review questions

1. Is the L0 definition consistent with the intended PCS/AnalogOpt boundary?
2. Should the 3 `graph_without_l0_match` rows remain excluded from default
   training until true L6 evidence is available?
3. Is the M12 max=500 diagnostic acceptable as a diagnostic-only experiment,
   or should it be removed/renamed before upstream merge?
4. Should GRPO exports be admitted only through the new registry flow?
5. Should the default graph-training command require an admission registry,
   rather than making it optional?
