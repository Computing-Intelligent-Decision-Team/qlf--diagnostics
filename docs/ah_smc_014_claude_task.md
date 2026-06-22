# AH-SMC-014 Claude Task: MAGICAL `.pin` Generation Provenance Audit

## Objective

Find where MAGICAL generates or regenerates Fan_SMC `.pin` files, without
modifying MAGICAL.

AH-SMC-013R proved that external `.pin` edits are not preserved by the current
`Magical.py` flow. The next step is a read-only provenance audit: identify the
internal generator path and the likely minimal patch point, so Codex and the
user can decide whether to authorize MAGICAL- code changes later.

## Required Reading

Read these first:

```text
/home/qlf/IOT/references/AnalogHarness/AGENTS.md
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_013r_review.md
/home/qlf/IOT/references/AnalogHarness/docs/dfcfc2_smc_campaign_status.md
```

## Allowed Writes

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_014/
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Forbidden Writes

- Any file under `/home/qlf/IOT/references/MAGICAL-/`
- Original Fan_SMC artifacts outside the AH-SMC-014 output directory
- SMCNR artifacts
- Controller, reward, GRPO, optimizer, or closure-level files
- C0 changes
- GDS painting or layout repair
- DFCFC2
- Git commits or pushes

## Required Work

This is read-only. Use `rg`, `git grep`, `sed`, and short inspection scripts
only.

1. Inspect MAGICAL source paths under:

```text
/home/qlf/IOT/references/MAGICAL-
```

2. Search for `.pin` generation and overwrite code:

```text
pin
.pin
ioPin
routeMosBulkEqualBodyPins
bulk
body
DesignDB
writePin
```

3. Trace the data flow for Fan_SMC:

```text
fan_smc_pin_3.sp / fan_smc_pin_3.json
-> Magical.py
-> DesignDB / primitive generation
-> placement/routing
-> fan_smc_pin_3.pin
```

4. Identify the earliest source of NMOS fourth-pin `-1`.

5. Identify whether PMOS fourth-pin boxes and NMOS fourth-pin `-1` are produced
by:

- primitive-specific pin metadata;
- device recognition rules;
- bulk/body routing policy;
- router parameter such as `routeMosBulkEqualBodyPins`;
- post-route artifact writer.

6. Produce a minimal change proposal, but do not implement it.

## Required Outputs

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_014/ah_smc_014_summary.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_014/ah_smc_014_records.json
```

Also append an AH-SMC-014 section to:

```text
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Required JSON Fields

```json
{
  "task_id": "AH-SMC-014",
  "status": "read_only_provenance_audit",
  "magical_files_modified": false,
  "pin_generation_files": [],
  "pin_overwrite_location": "file:line or unknown",
  "nmos_pin4_minus1_source": "file:line or unknown",
  "pmos_body_pin_source": "file:line or unknown",
  "routeMosBulkEqualBodyPins_role": "finding",
  "minimal_patch_proposal": "text only",
  "blocked_by": "null or exact blocker",
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
- every claimed file/line has a cited path and line number;
- the report distinguishes observed code paths from inference;
- no layout repair, reroute, DFCFC2, post-sim, reward, or training claim is
  made;
- trust remains failure-case only.
