# AH-SMC-012 Claude Task: Fan_SMC Met5 Contamination Audit

## Objective

Audit whether AH-SMC-011's horizontal met5 connector contaminated the M23 body
contact experiment by crossing existing Fan_SMC met5 routing.

This is a read-only diagnostic task. Do not generate a new repaired candidate.

## Required Reading

Read these first:

```text
/home/qlf/IOT/references/AnalogHarness/AGENTS.md
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_011_review.md
/home/qlf/IOT/references/AnalogHarness/docs/dfcfc2_smc_campaign_status.md
```

## Background

AH-SMC-011 directly painted a body-contact stack at M23 and connected it to the
gnda rail with this met5 box:

```text
[400, 11200, 5550, 11500]
```

Magic extraction did not change: M23 body remained `vout`, the substrate
remained `vout`, and `vout` remained equivalent to both `vdda` and `gnda`.

Codex accepts this as a negative GDS-level diagnostic, but not as a clean
disproof of the broader NMOS `.pin` contract hypothesis. The long horizontal
met5 connection may have crossed existing vout-associated routing.

## Hypothesis

```text
If AH-SMC-011's horizontal met5 connector intersects existing vout-associated
geometry, then the AH-SMC-011 negative result is contaminated and cannot be used
to reject a clean NMOS .pin/router repair.
```

## Allowed Writes

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_012/
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Forbidden Writes

- Any file under `/home/qlf/IOT/references/MAGICAL-/`
- Original Fan_SMC artifacts outside the AH-SMC-012 output directory
- SMCNR artifacts
- Controller, reward, GRPO, optimizer, or closure-level files
- C0 changes
- New substrate/body-contact repairs
- DFCFC2
- Git commits or pushes

## Required Work

1. Locate the AH-SMC-011 horizontal met5 connector:

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/ah_smc_011_records.json
```

2. Inspect baseline met5 geometry from the AH-SMC-011 input GDS:

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds
```

3. Produce an intersection table for every baseline met5 shape that overlaps or
touches the connector box `[400, 11200, 5550, 11500]`.

4. Where possible, infer whether each intersecting shape is associated with
`vout`, `vdda`, `gnda`, or unknown. Use nearby labels, known pin rails, Magic
extraction records, and coordinates. If a net cannot be inferred, mark it
`unknown`; do not guess.

5. Classify AH-SMC-011 as exactly one of:

```text
contaminated
not_contaminated
inconclusive
```

6. Recommend the next clean experiment:

- if contaminated: propose a clean `.pin`/router-level test or an isolated
  minimal fixture, not another long manual met5 route;
- if not contaminated: propose a direct H2 psub/diffusion test;
- if inconclusive: state the missing evidence needed before another geometry
  change.

## Required Outputs

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_012/ah_smc_012_summary.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_012/ah_smc_012_records.json
```

Also append an AH-SMC-012 section to:

```text
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Required Report Fields

The JSON report must include:

```json
{
  "task_id": "AH-SMC-012",
  "status": "observation_only_diagnostic",
  "connector_box": [400, 11200, 5550, 11500],
  "baseline_gds": "...absolute path...",
  "intersections": [
    {
      "layer": "met5",
      "gds_layer": 72,
      "gds_datatype": 20,
      "bbox": [0, 0, 0, 0],
      "overlap_bbox": [0, 0, 0, 0],
      "inferred_net": "vout|vdda|gnda|unknown",
      "evidence": "nearby label / known rail / extraction coordinate / unknown"
    }
  ],
  "classification": "contaminated|not_contaminated|inconclusive",
  "trust_decision": {
    "usable_for_reward": false,
    "usable_for_post_sim": false,
    "usable_for_training": false,
    "usable_for_parasitic_modeling": false,
    "usable_only_as_failure_case": true
  }
}
```

## Acceptance Gate

Codex will review only if:

- AH-SMC-012 is read-only with respect to layout repair;
- all paths are absolute;
- the connector box and baseline GDS are recorded exactly;
- every overlapping/touching met5 shape is reported;
- net inference is evidence-backed or marked `unknown`;
- the classification is one of the three allowed values;
- trust remains failure-case only;
- no closure/training/reward/post-sim/PVT safety is claimed.
