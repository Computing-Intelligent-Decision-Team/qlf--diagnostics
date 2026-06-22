# AH-SMC-015R2 Claude Task: Correct Option B Missing-Pin Control Flow

## Objective

Correct the AH-SMC-015R authorization package. Do not modify MAGICAL.

AH-SMC-015R fixed the layer-numbering and `setIoShape` argument-order errors,
but its recommended Option B still places the NMOS body-pin injection inside:

```python
for pin in self.cell.pin():
```

For the target failure case, NMOS `Mosfet.pin()` returns only D/G/S and no B
pin. Therefore a block waiting for `net_name == 3` inside that loop may never
execute. AH-SMC-015R2 must revise the pseudo-diff so the missing body net is
handled after the generated pin loop, or otherwise prove the loop processes
`net_name == 3`.

## Required Reading

Read these first:

```text
/home/qlf/IOT/references/AnalogHarness/AGENTS.md
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_015r_review.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r/ah_smc_015r_patch_authorization.md
/home/qlf/IOT/references/AnalogHarness/docs/dfcfc2_smc_campaign_status.md
```

## Allowed Writes

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r2/
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Forbidden Writes

- Any file under `/home/qlf/IOT/references/MAGICAL-/`
- Original Fan_SMC artifacts outside the AH-SMC-015R2 output directory
- SMCNR artifacts
- Controller, reward, GRPO, optimizer, or closure-level files
- C0 changes
- GDS painting or layout repair
- DFCFC2
- Git commits or pushes
- Applying any pseudo-diff or actual MAGICAL patch

## Required Corrections

This is read-only. Do not apply a patch.

1. Preserve the accepted corrections:

```text
ioLayer = 6
setIoShape(xLo, yLo, xHi, yHi)
```

2. Revise Option B's pseudo-diff so the NMOS missing body pin is handled after
   the generated pin loop. The concept should be:

```text
for pin in self.cell.pin():
    process generated D/G/S pins

if ckt.implType == magicalFlow.ImplTypePCELL_Nch and 3 in nets:
    if ckt.net(nets[3]).ioLayer is default/uninitialized or > 10:
        bbox = ckt.layout().boundary()
        ckt.net(nets[3]).setIoShape(bbox.xLo, bbox.yLo, bbox.xHi, bbox.yLo + 50)
        ckt.net(nets[3]).ioLayer = 6
```

3. Verify the exact way to check for an uninitialized/default `ioLayer` in
   Python. If direct comparison to `INDEX_TYPE_MAX` is awkward, the pseudo-diff
   may use the conservative condition:

```text
if ckt.net(nets[3]).ioLayer > 10:
```

4. Add preflight gates:

```text
before injection: body net exists and body ioLayer > 10
after injection: body ioLayer == 6
after MAGICAL: final.pin M23 body line is not -1
```

5. Keep Option A as production and Option C as not recommended.

## Required Outputs

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r2/ah_smc_015r2_patch_authorization.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r2/ah_smc_015r2_records.json
```

Also append an AH-SMC-015R2 section to:

```text
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

## Required JSON Fields

```json
{
  "task_id": "AH-SMC-015R2",
  "status": "read_only_patch_authorization_control_flow_correction",
  "magical_files_modified": false,
  "corrected_internal_body_ioLayer": 6,
  "setIoShape_argument_order_corrected": true,
  "injection_location": "after generated pin loop or proven equivalent",
  "missing_pin_loop_issue_corrected": true,
  "recommended_diagnostic_option": "B",
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
- Option B injection can execute even when NMOS `Mosfet.pin()` omits B;
- `ioLayer = 6` is preserved and proven to satisfy `ioLayer <= 10`;
- every `setIoShape` pseudo-call uses `(xLo, yLo, xHi, yHi)`;
- pseudo-diffs are clearly marked as not applied;
- observed code facts are separated from design assumptions;
- actual MAGICAL- modification is explicitly marked as requiring future user
  approval;
- no layout repair, reroute, DFCFC2, post-sim, reward, or training claim is
  made;
- trust remains failure-case only.
