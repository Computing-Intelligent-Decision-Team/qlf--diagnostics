# Prompt for Senior Codex Review — PCS Harness Progress 2026-08-20

Please review the current PCS Harness / parasitic modeling progress for
consistency with your intended experimental flow.

## Context

The working PCS branch is:

```text
repo: https://github.com/Computing-Intelligent-Decision-Team/pcs-harness.git
branch: align/origin-main-20260815
local HEAD referenced by this handoff: 075382809bfa65b981eacfb645a28fe35f52b1e3
```

The lightweight handoff docs are in:

```text
https://github.com/Computing-Intelligent-Decision-Team/qlf--diagnostics
branch: pcs-harness-progress-20260820
docs/pcs_harness_progress_20260820.md
docs/sample_admission_registry_summary_20260820.md
```

## What I need you to check

Please inspect whether the following interpretation is aligned with your PCS
workflow:

1. L0 should mean only `ingest_contract_check`, not physical closure.
2. L1-L6 should remain the PCS physical-flow levels.
3. A graph-training row should require:
   - L0 pass,
   - L6 physical closure,
   - raw PEX availability,
   - raw PEX SHA match with graph row.
4. GRPO sizing rows should not enter graph training directly. They should pass
   through the same admission chain.
5. The three graph rows currently labeled `graph_without_l0_match` should be
   excluded from default training until matching L6 provenance is available.

## Key results to review

Existing local L6 backfill:

```text
70 existing L6 state files
14 designs
70/70 L0 ingest-contract backfill pass
```

Sample admission registry:

```text
records: 89
graph_training_admitted: 48
graph_without_l0_match: 3
incomplete_admission: 19
l0_invalid_sizing: 8
l6_not_in_graph_dataset: 5
physical_replay_failed: 6
```

The three `graph_without_l0_match` rows are:

```text
Leung NMCNR
Qu2017 AZC
Tan CLIA
```

Observed issue: their graph metadata points to regenerated raw PEX, but the
corresponding local regenerated `state.json` files are only
`L4_layout_verified_mos_only`.  Current policy is to keep the original 51-graph
dataset for forensics but exclude these 3 from default research training,
leaving 48 admitted graph samples.

GRPO smoke:

```text
Default PCS config:
  8/8 GRPO candidates rejected at L0_invalid_sizing_for_pcs_config
  reason: M_M12 maps to 227..481, current PCS config max is 50

M12 max=500 diagnostic:
  2/8 reached L6_post_layout_pvt
  5/8 failed MAGICAL place-route
  1/8 failed connectivity LVS
```

## Specific questions

Please answer:

1. Is the L0 naming/semantics acceptable, or should it be renamed to avoid
   confusion with PCS physical levels?
2. Should the default graph-training command require an admission registry
   rather than making it optional?
3. Are the 3 `graph_without_l0_match` rows correctly quarantined, or do you
   have matching L6 evidence for them that should be supplied?
4. Is the M12 max=500 run acceptable as a diagnostic-only boundary experiment?
5. Do you want this admission registry format to become the official interface
   for future GRPO sizing exports?

Please focus on experimental contract/provenance consistency rather than model
accuracy; the current graph baselines are still smoke diagnostics.
