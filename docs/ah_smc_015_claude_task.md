# AH-SMC-015 Claude Task: MAGICAL NMOS Body-Pin Patch Authorization Package

## Objective

Prepare a no-code-change authorization package for the minimal internal MAGICAL
patch needed to test the Fan_SMC NMOS body-pin contract.

AH-SMC-014 identified the likely `.pin` generation root cause, but every repair
path requires modifying files under:

```text
/home/qlf/IOT/references/MAGICAL-/
```

That modification is not currently authorized. AH-SMC-015 is therefore a
read-only planning task. It should make the next approval decision precise
enough that Codex and the user can decide whether to allow an actual
MAGICAL-side diagnostic patch.

## Required Reading

Read these first:

```text
/home/qlf/IOT/references/AnalogHarness/AGENTS.md
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_014_review.md
/home/qlf/IOT/references/AnalogHarness/docs/dfcfc2_smc_campaign_status.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_014/ah_smc_014_summary.md
```

## Allowed Writes

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015/
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Forbidden Writes

- Any file under `/home/qlf/IOT/references/MAGICAL-/`
- Original Fan_SMC artifacts outside the AH-SMC-015 output directory
- SMCNR artifacts
- Controller, reward, GRPO, optimizer, or closure-level files
- C0 changes
- GDS painting or layout repair
- DFCFC2
- Git commits or pushes

## Required Work

This is read-only. Do not apply a patch.

1. Reconfirm the exact source locations for the three possible patch levels:

```text
device_generation primitive level
Device_generator / DesignDB database level
Placer .pin writer level
```

2. For each option, produce a pseudo-diff only. The pseudo-diff must include:

```text
target file
target line range
one-sentence mechanism
expected change in generated .pin
expected change in routed/extracted artifact
risk
rollback plan
why this is or is not a valid single-variable diagnostic
```

3. Recommend one diagnostic-first option and one long-term production option.

4. Define the exact acceptance test for the next actual patch run. At minimum:

```text
before/after source diff preserved
before/after .pin preserved
route.gds SHA256 recorded
extracted SPICE preserved
Magic extraction log preserved
Netgen LVS report preserved if run
trust_decision.json preserved
no closure/training/reward/post-sim claim
```

5. Define the stop condition. If the patch changes routing nondeterministically
without changing the final `.pin` body contract, the run must be classified as
blocked or contaminated, not repair.

## Required Outputs

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015/ah_smc_015_patch_authorization.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015/ah_smc_015_records.json
```

Also append an AH-SMC-015 section to:

```text
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Required JSON Fields

```json
{
  "task_id": "AH-SMC-015",
  "status": "read_only_patch_authorization_package",
  "magical_files_modified": false,
  "recommended_diagnostic_option": "A/B/C or unknown",
  "recommended_production_option": "A/B/C or unknown",
  "patch_options": [],
  "acceptance_tests": [],
  "stop_conditions": [],
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
- every proposed patch option has file/line references;
- pseudo-diffs are clearly marked as not applied;
- observed code facts are separated from design assumptions;
- the next actual code modification is explicitly marked as requiring user
  approval;
- no layout repair, reroute, DFCFC2, post-sim, reward, or training claim is
  made;
- trust remains failure-case only.
