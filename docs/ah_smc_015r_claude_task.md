# AH-SMC-015R Claude Task: Correct MAGICAL Body-Pin Patch Authorization

## Objective

Correct the AH-SMC-015 patch authorization package. Do not modify MAGICAL.

Codex rejected AH-SMC-015 because it uses Sky130 GDS layer numbers such as
`67` and `68` as MAGICAL internal `ioLayer` values. That cannot work with
`Placer.placeParsePin()`, which writes `-1` whenever `ioLayer > 10`.

AH-SMC-015R must produce a corrected authorization package that uses verified
MAGICAL internal layer indices before GDS remap.

## Required Reading

Read these first:

```text
/home/qlf/IOT/references/AnalogHarness/AGENTS.md
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_015_review.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015/ah_smc_015_patch_authorization.md
/home/qlf/IOT/references/AnalogHarness/docs/dfcfc2_smc_campaign_status.md
```

## Allowed Writes

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r/
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Forbidden Writes

- Any file under `/home/qlf/IOT/references/MAGICAL-/`
- Original Fan_SMC artifacts outside the AH-SMC-015R output directory
- SMCNR artifacts
- Controller, reward, GRPO, optimizer, or closure-level files
- C0 changes
- GDS painting or layout repair
- DFCFC2
- Git commits or pushes
- Applying any pseudo-diff or actual MAGICAL patch

## Required Corrections

This is read-only. Do not apply a patch.

1. Determine the correct MAGICAL internal routable layer index for the synthetic
   NMOS body pin.

   Do not use Sky130 GDS layer numbers directly as `ioLayer`.

   Verify with source/artifacts such as:

```text
/home/qlf/IOT/references/MAGICAL-/flow/python/Placer.py
/home/qlf/IOT/references/MAGICAL-/flow/python/Router.py
/home/qlf/IOT/references/MAGICAL-/flow/python/Device_generator.py
/home/qlf/IOT/references/MAGICAL-/generated/sky130PDK_trial/sky130.techfile.simple
/home/qlf/IOT/references/MAGICAL-/docs/sky130_adapter/trial_gds_layer_report.md
/home/qlf/IOT/references/MAGICAL-/tools/sky130_adapter/add_sky130_pin_labels_from_iopin.py
/home/qlf/IOT/references/MAGICAL-/tools/sky130_adapter/add_sky130_pin_shapes_from_iopin.py
```

2. Correct every pseudo-diff so `setIoShape` uses:

```text
setIoShape(xLo, yLo, xHi, yHi)
```

3. Correct Option A, B, and C layer language:

```text
MAGICAL internal ioLayer -> Sky130 exported layer/datatype
```

Do not write:

```text
ioLayer = 67
```

unless you also prove that this path expects final Sky130 GDS layer numbers,
which currently contradicts `Placer.py:527`.

4. Add a preflight gate for the next actual patch:

```text
assert chosen_body_ioLayer <= 10
assert final.pin M23 body entry is not -1
```

5. Preserve the recommendation structure:

```text
Option B = diagnostic candidate, if corrected
Option A = production candidate, if primitive geometry is eventually changed
Option C = not recommended
```

## Required Outputs

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r/ah_smc_015r_patch_authorization.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r/ah_smc_015r_records.json
```

Also append an AH-SMC-015R section to:

```text
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Required JSON Fields

```json
{
  "task_id": "AH-SMC-015R",
  "status": "read_only_patch_authorization_correction",
  "magical_files_modified": false,
  "corrected_internal_body_ioLayer": "integer or unknown",
  "sky130_export_target_for_layer": "text",
  "setIoShape_argument_order_corrected": true,
  "recommended_diagnostic_option": "B or unknown",
  "patch_options": [],
  "preflight_gates": [],
  "requires_user_approval_for_next_step": true,
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

- no MAGICAL- file is modified;
- no final Sky130 GDS layer number is used as MAGICAL `ioLayer` without proof;
- the chosen internal body `ioLayer` is proven to satisfy `ioLayer <= 10`;
- every `setIoShape` pseudo-call uses `(xLo, yLo, xHi, yHi)`;
- pseudo-diffs are clearly marked as not applied;
- observed code facts are separated from design assumptions;
- actual MAGICAL- modification is explicitly marked as requiring future user
  approval;
- no layout repair, reroute, DFCFC2, post-sim, reward, or training claim is
  made;
- trust remains failure-case only.
