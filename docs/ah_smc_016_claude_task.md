# AH-SMC-016 Claude Task: MAGICAL Option B NMOS Body-Pin Diagnostic Patch

## Authorization Gate

Do not execute this task unless the user explicitly says:

```text
批准 AH-SMC-016 修改 MAGICAL-
```

Without that approval, stop and report that AH-SMC-016 is waiting for user
authorization.

## Objective

Run the minimal diagnostic patch approved by Codex in AH-SMC-015R2:

```text
Device_generator.writeDB() database-level NMOS body pin injection
```

This is a single-variable diagnostic probe. It is not a production fix, not a
closure claim, and not a training/reward/post-sim-safe sample promotion.

## Required Reading

Read these first:

```text
/home/qlf/IOT/references/AnalogHarness/AGENTS.md
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_015r2_review.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r2/ah_smc_015r2_patch_authorization.md
/home/qlf/IOT/references/AnalogHarness/docs/dfcfc2_smc_campaign_status.md
```

## Allowed Writes After User Approval

```text
/home/qlf/IOT/references/MAGICAL-/flow/python/Device_generator.py
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016/
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Forbidden Writes

- Other MAGICAL- source files unless Codex/user explicitly expands scope
- SMCNR artifacts
- Controller, reward, GRPO, optimizer, or closure-level files
- C0 changes
- Manual GDS painting unrelated to this diagnostic patch
- DFCFC2
- Git commits or pushes
- Reverting unrelated existing MAGICAL- changes

## Required Pre-Patch Baseline

Before editing MAGICAL-, preserve:

```text
git status --short
git diff -- flow/python/Device_generator.py
sha256sum flow/python/Device_generator.py
```

Write these to:

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016/pre_patch_magical_status.txt
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016/pre_patch_device_generator.diff
```

## Patch Shape

Patch only `Device_generator.writeDB()` after the generated-pin loop.

The intended control flow is:

```python
for pin in self.cell.pin():
    process generated D/G/S pins

if (ckt.implType == magicalFlow.ImplTypePCELL_Nch
        and 3 in nets
        and ckt.net(nets[3]).ioLayer > 10):
    bbox = ckt.layout().boundary()
    ckt.net(nets[3]).setIoShape(
        bbox.xLo, bbox.yLo,
        bbox.xHi, bbox.yLo + 50)
    ckt.net(nets[3]).ioLayer = 6
```

Required invariants:

```text
ioLayer = 6
setIoShape(xLo, yLo, xHi, yHi)
injection after the for pin loop
only NMOS Nch body net 3
```

## Required Evidence

Collect these artifacts under:

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016/
```

Required minimum:

```text
pre_patch_magical_status.txt
pre_patch_device_generator.diff
patch.diff
post_patch_device_generator.sha256
before.pin + SHA256
final.pin + SHA256
pin.diff
route.gds + SHA256, if generated
magic_extract.log, if extraction is run
fan_smc_pin_3_flat.ext, if extraction is run
fan_smc_pin_3_flat.spice, if extraction is run
trust_decision.json
ah_smc_016_summary.md
ah_smc_016_records.json
```

## Stop Conditions

Classify the run without repair claims if any condition occurs:

```text
final.pin == before.pin                         -> blocked
M23 body line remains -1                        -> blocked
route changes but extraction is unchanged       -> inconclusive
extraction changes but baseline variance exists -> contaminated
new extraction errors appear                    -> regression
LVS appears to pass                             -> do not claim closure; record for Codex review
```

## Trust Decision

The trust decision must remain:

```json
{
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true
}
```

## Acceptance Gate

Codex will review only if:

- user approval for AH-SMC-016 is stated in the report;
- pre-patch MAGICAL status and diff are preserved;
- only the approved Option B patch is applied;
- `final.pin` evidence is preserved;
- trust remains failure-case only;
- no closure/training/reward/post-sim safety is claimed;
- no commit or push is made.
