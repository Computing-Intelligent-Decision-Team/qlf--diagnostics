# Codex Review: AH-SMC-015R2 Final Corrected MAGICAL Body-Pin Patch Authorization

## Review Summary

Codex accepts AH-SMC-015R2 as `accepted_patch_authorization_package`.

AH-SMC-015R2 corrects all three blockers found in AH-SMC-015 and AH-SMC-015R:

- `ioLayer = 67` was replaced with MAGICAL internal `ioLayer = 6`;
- all `setIoShape` pseudo-calls use `(xLo, yLo, xHi, yHi)`;
- Option B's NMOS body-pin injection moved after the generated-pin loop, so it
  can execute when `Mosfet.pin()` omits B.

This acceptance is only approval of the patch plan. It is not approval to modify
MAGICAL. Actual changes under `/home/qlf/IOT/references/MAGICAL-/` still require
explicit user approval.

Fan_SMC remains failure-case only.

## Checked Artifacts

| Artifact | Path | Review result |
| --- | --- | --- |
| AH-SMC-015R2 authorization doc | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r2/ah_smc_015r2_patch_authorization.md` | Present |
| AH-SMC-015R2 records | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r2/ah_smc_015r2_records.json` | Present; valid JSON |
| Claude run report | `docs/claude_code_run_report.md` | Contains AH-SMC-015R2 section |

## Accepted Technical Points

### 1. Internal `ioLayer = 6` Is Valid For The `.pin` Writer

Local source confirms that `Placer.placeParsePin()` writes `-1` for layers
greater than 10:

```text
/home/qlf/IOT/references/MAGICAL-/flow/python/Placer.py:527-528
if layer > 10:
    outFile.write("-1\n")
```

AH-SMC-015R2 uses `ioLayer = 6`, which passes this check.

Local source also confirms that MAGICAL PDK layer 36 maps to `ioLayer = 6`:

```text
/home/qlf/IOT/references/MAGICAL-/flow/python/Placer.py:266-283
hardcodeConvertPdkLayerToIoLayer(36) -> 6
```

This keeps MAGICAL internal layer semantics separate from later Sky130 GDS
export semantics.

### 2. `setIoShape` Uses The Correct Coordinate Order

Local source confirms:

```text
/home/qlf/IOT/references/MAGICAL-/flow/cpp/magical_flow/src/db/GraphComponents.h:246
setIoShape(xLo, yLo, xHi, yHi)
```

AH-SMC-015R2's Option B pseudo-diff now uses this order.

### 3. Missing NMOS Body Pin Is Handled After The Pin Loop

Local `Device_generator.writeDB()` processes generated primitive pins in:

```text
/home/qlf/IOT/references/MAGICAL-/flow/python/Device_generator.py:65-81
```

For NMOS, AH-SMC-015R2 records that `self.cell.pin()` yields D/G/S and omits B.
The corrected Option B handles net 3 after the loop:

```text
if ckt.implType == magicalFlow.ImplTypePCELL_Nch
and 3 in nets
and ckt.net(nets[3]).ioLayer > 10:
    setIoShape(...)
    ioLayer = 6
```

This control flow can execute for the missing body net, unlike the AH-SMC-015R
version that waited for `net_name == 3` inside a loop that only reached 0, 1,
and 2.

## Required Caveats For AH-SMC-016

The local MAGICAL- checkout is already dirty, including files that AH-SMC-016
may touch:

```text
/home/qlf/IOT/references/MAGICAL-/flow/python/Device_generator.py
/home/qlf/IOT/references/MAGICAL-/flow/python/Placer.py
```

Codex does not attribute those pre-existing modifications to AH-SMC-015R2.
However, AH-SMC-016 must preserve an exact pre-patch baseline before editing.
At minimum, it must record:

```text
git status --short
git diff -- flow/python/Device_generator.py
sha256sum flow/python/Device_generator.py
```

AH-SMC-016 must not revert unrelated existing MAGICAL- changes.

## AH-SMC-016 Authorization Boundary

AH-SMC-016 may begin only after the user explicitly approves MAGICAL- source
modification.

The approved diagnostic direction is:

```text
Option B: Device_generator.writeDB() database-level NMOS body pin injection
```

The patch must be treated as a diagnostic probe, not as production repair or
circuit closure.

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
