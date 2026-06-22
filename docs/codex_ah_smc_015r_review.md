# Codex Review: AH-SMC-015R Corrected MAGICAL Body-Pin Patch Authorization

## Review Summary

Codex rejects AH-SMC-015R pending control-flow correction as
`rejected_patch_plan_missing_pin_loop`.

AH-SMC-015R correctly fixes the two blocking errors from AH-SMC-015:

- it replaces Sky130 GDS layer `67` with MAGICAL internal `ioLayer = 6`;
- it corrects `setIoShape` argument order to `(xLo, yLo, xHi, yHi)`.

Those corrections are technically sound. `ioLayer = 6` satisfies the
`Placer.placeParsePin()` threshold because `6 <= 10`, and the local MAGICAL
source confirms the internal layer mapping from PDK layer `36` to `ioLayer 6`.

However, the recommended Option B pseudo-diff is still not executable as
written. It places the missing NMOS body-pin injection inside:

```python
for pin in self.cell.pin():
```

For the exact failure case AH-SMC-015R describes, NMOS `Mosfet.pin()` returns
only D/G/S and no B pin. Therefore the loop can end before `net_name == 3` is
processed. The proposed injected block may never run, so the intended body
`ioShape` may not be written.

AH-SMC-016 must not start from this plan until the Option B control flow is
corrected.

## Checked Artifacts

| Artifact | Path | Review result |
| --- | --- | --- |
| AH-SMC-015R authorization doc | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r/ah_smc_015r_patch_authorization.md` | Present |
| AH-SMC-015R records | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r/ah_smc_015r_records.json` | Present; valid JSON |
| Claude run report | `docs/claude_code_run_report.md` | Contains AH-SMC-015R section |

## Accepted Corrections

### 1. Layer Semantics Are Corrected

Codex accepts the correction from `ioLayer = 67` to `ioLayer = 6`.

Local evidence:

```text
/home/qlf/IOT/references/MAGICAL-/flow/python/Placer.py:527-528
if layer > 10:
    outFile.write("-1\n")
```

Therefore `ioLayer = 6` passes the `.pin` coordinate writer.

Additional local evidence:

```text
/home/qlf/IOT/references/MAGICAL-/flow/python/Placer.py:266-283
hardcodeConvertPdkLayerToIoLayer(36) -> 6
```

and:

```text
/home/qlf/IOT/references/MAGICAL-/generated/sky130PDK_trial/sky130.techfile.simple
M6 36 -> sky130_export=met5 72/20
```

This resolves AH-SMC-015's layer-numbering error.

### 2. `setIoShape` Argument Order Is Corrected

Codex accepts the corrected order:

```text
setIoShape(xLo, yLo, xHi, yHi)
```

Local evidence:

```text
/home/qlf/IOT/references/MAGICAL-/flow/cpp/magical_flow/src/db/GraphComponents.h:246
void setIoShape(LocType xLo, LocType yLo, LocType xHi, LocType yHi)
```

## Blocking Finding

### Option B Injection Is Still In The Wrong Control-Flow Location

Current `Device_generator.writeDB()` is:

```text
/home/qlf/IOT/references/MAGICAL-/flow/python/Device_generator.py:68-81
net_name = 0
for pin in self.cell.pin():
    ...
    net_name += 1
```

AH-SMC-015R says NMOS has no B pin generated. If `self.cell.pin()` yields only
three pins, the loop runs only for `net_name = 0, 1, 2`. A block placed inside
that loop with:

```python
if net_name == 3 and ckt.implType == magicalFlow.ImplTypePCELL_Nch:
```

will not execute for the missing fourth pin.

The corrected Option B must handle the missing body net after the generated
pin loop, for example:

```text
After processing all generated pins, if the device is NMOS and net 3 exists
but still has default/uninitialized ioLayer, assign body ioShape and ioLayer=6.
```

The exact patch must remain a pseudo-diff until the user explicitly approves
MAGICAL- modification.

## Required Correction

Proceed to AH-SMC-015R2:

```text
Correct Option B control flow before authorizing AH-SMC-016.
```

AH-SMC-015R2 must:

- preserve the accepted `ioLayer = 6` correction;
- preserve the accepted `setIoShape(xLo, yLo, xHi, yHi)` correction;
- move Option B's missing-body injection outside the `for pin in
  self.cell.pin()` loop or otherwise prove the loop processes `net_name == 3`;
- add a preflight gate that checks the target net had default/uninitialized
  `ioLayer` before injection and `ioLayer == 6` after injection;
- still apply no MAGICAL- patch.

## Trust Boundary Decision

Fan_SMC remains failure-case only:

```json
{
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true
}
```

No Fan_SMC closure, reward, training, post-layout simulation, PVT, or LVS pass
claim is accepted.
