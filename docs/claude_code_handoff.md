# Claude Code Handoff

## Active Task: AH-SMC-016 Pending User Approval

### Objective

Wait for explicit user approval before running the MAGICAL Option B diagnostic
patch described in:

```text
/home/qlf/IOT/references/AnalogHarness/docs/ah_smc_016_claude_task.md
```

Do not execute AH-SMC-016 unless the user explicitly says:

```text
批准 AH-SMC-016 修改 MAGICAL-
```

Without that exact approval, report that the task is blocked on user
authorization.

### Required Reading

Read these first:

```text
/home/qlf/IOT/references/AnalogHarness/AGENTS.md
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_015r2_review.md
/home/qlf/IOT/references/AnalogHarness/docs/ah_smc_016_claude_task.md
/home/qlf/IOT/references/AnalogHarness/docs/dfcfc2_smc_campaign_status.md
```

### Current Reviewed State

- `SMCNR_SE_2st_AMP/cand_0031` remains the sole positive baseline.
- Fan_SMC remains failure-case only.
- AH-SMC-009 p+ tap did not repair `substrate "vout"` or
  `equiv "vout" "vdda"` / `equiv "vout" "gnda"`.
- AH-SMC-010 localized the first auditable divergence to the NMOS `.pin`
  contract: source netlist uses `B=gnda`, but all NMOS fourth pins are `-1`.
- AH-SMC-011 directly painted an M23 body-contact stack and a horizontal met5
  connector to gnda. Magic extraction still left M23 body, substrate, and
  supply equivalence collapsed to `vout`.
- AH-SMC-012 confirms AH-SMC-011 was contaminated: the manually painted met5
  connector bridged a gnda-confirmed left tree to a previously separate
  right-side unknown tree. AH-SMC-011 no longer counts as a clean disproof of
  the `.pin` contract hypothesis.
- AH-SMC-013 generated a different extraction, but the preserved `.pin`
  artifact did not contain the claimed M23 fourth-pin change. Codex rejected it
  until the artifact chain is corrected.
- AH-SMC-013R preserved the pin delta and proved exactly one intended M23
  fourth-pin change, but `Magical.py` overwrote the final `.pin` back to
  baseline. External `.pin` editing is blocked as a clean experiment path.
- AH-SMC-014 traced the `.pin` generation path. `Placer.placeParsePin()`
  regenerates `.pin`; `ioLayer > 10` writes `-1`; `DesignDB` classifies NMOS
  pin 3 as `PSUB` and PMOS pin 3 as `NWELL`; `Device_generator.writeDB()` copies
  primitive pin-shape layer data into `net.ioLayer`.
- AH-SMC-014's only important caveat: the exact `device_generation.Mosfet.pin()`
  primitive geometry is partially inferred because the external submodule is
  not initialized locally.
- AH-SMC-015 produced a read-only authorization package but is rejected pending
  correction. It used Sky130 GDS layer number `67` as MAGICAL internal
  `ioLayer`. Since `Placer.py` writes `-1` when `ioLayer > 10`, that plan would
  not produce the intended `.pin` change.
- AH-SMC-015R fixed `ioLayer = 6` and `setIoShape(xLo,yLo,xHi,yHi)`, but is
  rejected pending control-flow correction. Its Option B injection sits inside
  `for pin in self.cell.pin()`, while the target NMOS path omits B; the
  `net_name == 3` injection may never execute.
- AH-SMC-015R2 is accepted as the final patch authorization package. Option B
  now injects after the generated-pin loop, preserving `ioLayer = 6` and
  `setIoShape(xLo,yLo,xHi,yHi)`.
- AH-SMC-016 requires explicit user approval because it modifies MAGICAL-.
  MAGICAL- is already dirty, so pre-patch status, diff, and SHA evidence must
  be preserved before any edit.

### Allowed Writes

```text
/home/qlf/IOT/references/MAGICAL-/flow/python/Device_generator.py
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016/
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

### Forbidden Writes

- Any MAGICAL- file other than `/home/qlf/IOT/references/MAGICAL-/flow/python/Device_generator.py`
- Original Fan_SMC artifacts outside the AH-SMC-016 output directory
- SMCNR artifacts
- Controller, reward, GRPO, optimizer, or closure-level files
- C0 changes
- GDS painting or layout repair
- DFCFC2
- Git commits or pushes
- Reverting unrelated existing MAGICAL- changes

### Required Outputs

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016/pre_patch_magical_status.txt
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016/pre_patch_device_generator.diff
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016/patch.diff
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016/trust_decision.json
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016/ah_smc_016_summary.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016/ah_smc_016_records.json
```

Also append an AH-SMC-016 section to:

```text
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

### Acceptance Gate

Codex will review only if:

- user approval for AH-SMC-016 is quoted in the report;
- pre-patch MAGICAL status, diff, and SHA evidence are preserved;
- only the approved Option B patch is applied;
- `final.pin` evidence is preserved if MAGICAL is run;
- all evidence paths are absolute;
- trust remains failure-case only;
- no closure/training/reward/post-sim safety is claimed.

No commit or push.
