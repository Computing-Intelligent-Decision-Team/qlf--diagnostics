# AH-SMC-013 Claude Task: Fan_SMC M23 `.pin` Contract Repair Feasibility Probe

## Objective

Test the NMOS `.pin` contract hypothesis without manual GDS painting.

AH-SMC-012 showed that AH-SMC-011's hand-painted horizontal met5 connector
bridged a gnda tree to an unknown right-side met5 tree. Therefore AH-SMC-011 is
not a clean body-contact experiment. AH-SMC-013 must use an isolated `.pin`
contract change and the existing MAGICAL/Fan_SMC pipeline, or stop with a precise
reproducibility blocker.

## Required Reading

Read these first:

```text
/home/qlf/IOT/references/AnalogHarness/AGENTS.md
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_012_review.md
/home/qlf/IOT/references/AnalogHarness/docs/dfcfc2_smc_campaign_status.md
```

## Hypothesis

```text
If M23's NMOS fourth .pin entry is replaced with a real body-pin geometry and
MAGICAL's own legalizer/router is used to generate routing, then the experiment
tests whether the missing NMOS body pin is the next repairable contract gap.
```

## Allowed Writes

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013/
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Forbidden Writes

- Any file under `/home/qlf/IOT/references/MAGICAL-/`
- Original Fan_SMC artifacts outside the AH-SMC-013 output directory
- SMCNR artifacts
- Controller, reward, GRPO, optimizer, or closure-level files
- C0 changes
- Manual GDS painting of met5, contacts, taps, or body-contact geometry
- More than one NMOS `.pin` body entry change in the first probe
- DFCFC2
- Git commits or pushes

## Required Work

1. Copy the required Fan_SMC case files into:

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013/case/
```

2. Record the original M23 `.pin` entry exactly. The current fourth pin is:

```text
-1
```

3. Propose one replacement body-pin box for M23 and justify it from local
evidence. Acceptable sources include:

- analogous PMOS fourth-pin boxes in the same `.pin` file;
- M23 primitive geometry;
- existing Fan_SMC route/pin mapping reports.

Do not guess silently. If the correct body-pin box cannot be justified, stop and
record the blocker.

4. Modify only M23's fourth `.pin` entry in the isolated copy.

5. Attempt to rerun the existing MAGICAL/Fan_SMC legalizer/router or pipeline
entry from the isolated copy.

6. If a new GDS is generated, run Magic extraction and compare:

- `substrate` record;
- `equiv "vout" "vdda"` / `equiv "vout" "gnda"`;
- M23 `.ext` device record;
- M23 extracted SPICE instance;
- trust decision.

7. If reroute cannot run, do not invent a result. Record the exact missing
command, missing file, environment blocker, or unsupported pipeline boundary.

## Required Outputs

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013/ah_smc_013_summary.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013/ah_smc_013_records.json
```

Also append an AH-SMC-013 section to:

```text
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Required Report Fields

The JSON report must include:

```json
{
  "task_id": "AH-SMC-013",
  "status": "observation_only_diagnostic",
  "changed_instance": "M23",
  "changed_field": "pin_4_body",
  "before_pin_4": "-1",
  "after_pin_4": "box or blocked",
  "pin_box_rationale": "evidence-backed rationale or blocker",
  "manual_gds_painting_used": false,
  "reroute_attempted": true,
  "reroute_status": "generated_gds|blocked",
  "blocker": "null or exact blocker",
  "extraction_compared": true,
  "trust_decision": {
    "usable_for_reward": false,
    "usable_for_post_sim": false,
    "usable_for_training": false,
    "usable_for_parasitic_modeling": false,
    "usable_only_as_failure_case": true
  }
}
```

If no GDS is generated, set `extraction_compared` to `false` and record the
blocker exactly.

## Acceptance Gate

Codex will review only if:

- AH-SMC-013 changes only the isolated M23 `.pin` fourth entry;
- no manual GDS painting is used;
- the replacement pin box is justified or the blocker is explicit;
- reroute is attempted through the existing MAGICAL/Fan_SMC flow, or the exact
  missing entry point is recorded;
- all paths are absolute;
- trust remains failure-case only;
- no closure/training/reward/post-sim/PVT safety is claimed.
