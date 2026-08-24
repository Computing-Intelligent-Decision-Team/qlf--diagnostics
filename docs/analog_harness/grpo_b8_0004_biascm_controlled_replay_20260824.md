# B8-0004 biascm controlled replay audit

Date: 2026-08-24

## Purpose

This is a diagnostic-only replay. It tests whether the B10 placement/legalization
failure can be reproduced by changing only the `mosfet_18_7_*_biascm_nmos`
geometry around the B8 L6 sample `grpo_leung_dfcfc2_0004`.

It does not change MAGICAL, action-space, waivers, environment, or PCS admission
semantics. These records are excluded from the default graph-training set.

## Inputs

- PCS worktree:
  `/home/qlf/IOT/references/pcs-harness-align-origin-main-20260815`
- Sizing manifest:
  `generated/analog_harness/grpo_b8_0004_biascm_geometry_controlled_replay_20260823_v1/controlled_sizing_manifest.yaml`
- Physical replay output:
  `generated/analog_harness/grpo_b8_0004_biascm_geometry_controlled_replay_20260823_v1/physical_l1_l6/`
- Summary:
  `generated/analog_harness/grpo_b8_0004_biascm_geometry_controlled_replay_20260823_v1/physical_l1_l6/admission_summary.json`

## Result

| candidate | changed field | L | W | M | closure | raw PEX caps | total cap fF | interpretation |
|---|---:|---:|---:|---:|---|---:|---:|---|
| `ctrl_b8_0004_exact` | none | 0.5 | 5.3 | 1 | `L6_post_layout_pvt` | 142 | 5167.35053 | positive control replays B8 successfully |
| `ctrl_b8_0004_biascm_l_3p1` | L only | 3.1 | 5.3 | 1 | `L6_post_layout_pvt` | 123 | 5210.15778 | longer L alone still closes |
| `ctrl_b8_0004_biascm_w_0p5` | W only | 0.5 | 0.5 | 1 | `L2_pre_layout_pvt` | - | - | fails during MAGICAL placement/legalization |
| `ctrl_b8_0004_biascm_l_3p1_w_0p5` | L and W | 3.1 | 0.5 | 1 | `L6_post_layout_pvt` | 136 | 5179.96298 | combined L/W change closes in this baseline |

## Failure Evidence

The only non-L6 case is `ctrl_b8_0004_biascm_w_0p5`. It passes pre-layout
nominal and PVT simulation, then fails in `layout_verification` at
`magical_place_route`.

Key MAGICAL evidence:

```text
LP legalization solver: LP infeasible
Check Symmetry: symPair failed. axis 3100,
cell leung_dfcfc2_pin_3_xm20 ...
cell leung_dfcfc2_pin_3_xm21 ...
alignGrid.cpp:126: GridAligner::adjustSymPair(...) assertion failed
```

This localizes the controlled failure to the symmetric `xm20/xm21` placement
and grid-alignment path, not to ngspice, PVT simulation, LVS, raw PEX parsing, or
the runner environment.

## Interpretation

The positive control reaching L6 confirms that the current environment can
replay B8-0004. Therefore this controlled experiment should not be interpreted
as an environment drift issue.

Changing only `mosfet_18_7_l_biascm_nmos` from 0.5 to 3.1 does not break
physical closure. Changing only `mosfet_18_7_w_biascm_nmos` from 5.3 to 0.5
does break MAGICAL placement/legalization in this baseline. However, changing
both L and W together reaches L6, so W=0.5 is not a global hard rejection rule.
The failure is interaction-dependent, likely tied to the generated symmetric
array geometry and placement constraints for `xm20/xm21`.

## Dataset Policy

These four rows are diagnostic controlled replays. The output directory keeps:

- `diagnostic_admitted_raw_pex.jsonl`: three L6/raw-PEX diagnostic successes.
- `physical_closure_failure_labels.jsonl`: one MAGICAL placement/legalization
  diagnostic failure.
- `admitted_graphs.jsonl`: intentionally empty.

No row from this experiment is admitted to the default graph-training dataset
unless a later task explicitly promotes diagnostic samples under a separate
dataset policy.
