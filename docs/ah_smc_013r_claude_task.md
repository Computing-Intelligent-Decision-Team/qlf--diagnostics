# AH-SMC-013R Claude Task: Fan_SMC M23 `.pin` Artifact Correction

## Objective

Correct AH-SMC-013 by producing an auditable one-device `.pin` delta before
making any extraction or hypothesis claim.

AH-SMC-013 reported that M23 pin 4 changed from `-1` to
`-200 -200 1400 -150`, but the preserved `.pin` artifact still contains `-1`
and is byte-identical to the baseline `.pin`. AH-SMC-013R must fix that artifact
gap.

## Required Reading

Read these first:

```text
/home/qlf/IOT/references/AnalogHarness/AGENTS.md
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_013_review.md
/home/qlf/IOT/references/AnalogHarness/docs/dfcfc2_smc_campaign_status.md
```

## Allowed Writes

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013r/
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Forbidden Writes

- Any file under `/home/qlf/IOT/references/MAGICAL-/`
- Original Fan_SMC artifacts outside the AH-SMC-013R output directory
- SMCNR artifacts
- Controller, reward, GRPO, optimizer, or closure-level files
- C0 changes
- Manual GDS painting of met5, contacts, taps, or body-contact geometry
- More than one NMOS `.pin` body entry change
- DFCFC2
- Git commits or pushes

## Required Work

1. Create an isolated AH-SMC-013R case directory.

2. Preserve these files before modification:

```text
before.pin
before.pin.sha256
```

3. Modify only M23's fourth `.pin` entry in the isolated `after.pin`.

4. Preserve:

```text
after.pin
after.pin.sha256
pin.diff
```

The diff must show exactly one changed line:

```text
- -1
+ -200 -200 1400 -150
```

or a different replacement box if explicitly justified.

5. Validate with a script or command that:

- only `fan_smc_pin_3_M23` differs;
- M23 pin 4 is no longer `-1`;
- all other instances and pins are identical.

6. Run MAGICAL using the preserved modified `.pin`.

7. Immediately after MAGICAL returns, re-check and preserve the final `.pin`:

```text
final.pin
final.pin.sha256
```

If MAGICAL overwrites the `.pin`, stop and record that as the blocker. Do not
claim a `.pin` experiment succeeded if `final.pin` no longer contains the
modified M23 fourth pin.

8. If and only if the modified `.pin` survives into the routed case, continue
Sky130 remap and Magic extraction, then compare substrate/equiv/M23 SPICE.

## Required Outputs

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013r/ah_smc_013r_summary.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013r/ah_smc_013r_records.json
```

Also append an AH-SMC-013R section to:

```text
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Required JSON Fields

```json
{
  "task_id": "AH-SMC-013R",
  "status": "artifact_correction",
  "changed_instance": "M23",
  "before_pin_4": "-1",
  "after_pin_4": "box or blocked",
  "pin_diff_preserved": true,
  "only_m23_changed": true,
  "magical_overwrote_pin": false,
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

If MAGICAL overwrites the `.pin` or refuses to use it, set
`reroute_status = "blocked"`, `extraction_compared = false`, and record the
exact blocker.

## Acceptance Gate

Codex will review only if:

- `before.pin`, `after.pin`, `final.pin`, and `pin.diff` are preserved;
- `pin.diff` shows exactly one M23 fourth-pin change;
- no manual GDS painting is used;
- MAGICAL either uses the modified `.pin` or the overwrite/blocker is recorded;
- all paths are absolute;
- trust remains failure-case only;
- no closure/training/reward/post-sim/PVT safety is claimed.
