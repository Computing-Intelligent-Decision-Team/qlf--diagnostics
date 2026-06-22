# Codex Review: AH-SMC-014 MAGICAL `.pin` Generation Provenance Audit

## Review Summary

Codex accepts AH-SMC-014 as `accepted_provenance_audit`.

AH-SMC-014 successfully traces the local MAGICAL `.pin` generation path and
explains why external `.pin` edits from AH-SMC-013R do not survive the normal
flow. The strongest locally verified facts are:

- `Placer.placeParsePin()` opens `<ckt>.pin` in write mode and regenerates it
  from the internal database.
- `Placer.placeParsePin()` writes `-1` whenever `net.ioLayer > 10`.
- `DesignDB.connect_children()` classifies NMOS pin index 3 as `PSUB` and PMOS
  pin index 3 as `NWELL`.
- `Device_generator.writeDB()` copies the first field of each generated device
  pin shape into `net.ioLayer`.

Fan_SMC remains a failure-case diagnostic sample only. AH-SMC-014 is not a
closure, repair, reward, training, post-simulation, or parasitic-modeling proof.

## Checked Artifacts

| Artifact | Path | Review result |
| --- | --- | --- |
| AH-SMC-014 summary | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_014/ah_smc_014_summary.md` | Present |
| AH-SMC-014 records | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_014/ah_smc_014_records.json` | Present; valid JSON |
| Claude run report | `docs/claude_code_run_report.md` | Contains AH-SMC-014 section |

## Independent Source Review

### 1. `.pin` Regeneration Is Verified

`/home/qlf/IOT/references/MAGICAL-/flow/python/Placer.py:505` defines
`placeParsePin()`.

At line 509 it constructs the `.pin` path, and at line 511 it opens the file in
write mode. This supports the AH-SMC-013R blocker: editing the generated `.pin`
externally is not a stable single-variable experiment because the next MAGICAL
run can regenerate the file from the internal database.

The direct sentinel rule is at lines 524-528:

```text
shape = net.ioShape()
layer = net.ioLayer
if layer > 10:
    outFile.write("-1\n")
```

This is accepted as the immediate writer-side reason NMOS body pins can become
`-1`.

### 2. NMOS `PSUB` And PMOS `NWELL` Classification Is Verified

`/home/qlf/IOT/references/MAGICAL-/flow/python/DesignDB.py:470` sets:

```text
psub = inst.reference in nmos_set and i == 3
```

`/home/qlf/IOT/references/MAGICAL-/flow/python/DesignDB.py:471` sets:

```text
nwell = inst.reference in pmos_set and i == 3
```

Lines 497-501 then assign `PinType.PSUB` or `PinType.NWELL`. The TODO at
lines 479-481 is also relevant because it states that MOSFET bulk handling is
deferred to a later well-generation path.

### 3. `ioLayer` Source Is Verified, But Primitive Geometry Is Partly Inferred

`/home/qlf/IOT/references/MAGICAL-/flow/python/Device_generator.py:69-80`
iterates over `self.cell.pin()`, normalizes each shape, and assigns
`ckt.net(...).ioLayer = shape[0]`.

This verifies the data path from generated primitive pin shapes into
`net.ioLayer`.

The exact implementation of `device_generation.Mosfet.pin()` was not locally
inspectable because the `device_generation` submodule is not initialized in the
available MAGICAL checkout. Therefore the specific statement:

```text
NMOS PSUB has no routable metal pin shape, so ioLayer > 10.
```

is accepted as an inference from the observed `.pin` output plus the verified
`Device_generator.writeDB()` and `Placer.placeParsePin()` chain, not as a
directly inspected primitive-source fact.

### 4. Bulk Routing Parameters Do Not Provide A Clean NMOS Fix

`/home/qlf/IOT/references/MAGICAL-/flow/python/Params.py:57-60` confirms the
defaults:

```text
useDeviceSubGuardRing = False
preserveMosBulkEqualPins = False
routeMosBulkEqualBodyPins = True
```

`/home/qlf/IOT/references/MAGICAL-/flow/python/DesignDB.py:421-428` applies
`routeMosBulkEqualBodyPins` in the PMOS branch. The NMOS branch at lines
429-432 records `bulkCon` but does not apply the same `routeBulkEqualBodyPin`
validity control.

Codex accepts the AH-SMC-014 conclusion that this parameter does not by itself
solve NMOS fourth-pin `-1`.

## Scope Caveats

- AH-SMC-014 did not initialize or inspect the external `device_generation`
  submodule, so primitive-internal NMOS body geometry remains indirectly
  evidenced.
- AH-SMC-014 did not run a repair, reroute, DRC, LVS, PEX, post-layout
  simulation, or PVT experiment.
- The proposed patch points are design proposals only. No MAGICAL- code change
  is authorized by this review.

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

## Next Step

Proceed to AH-SMC-015 as a read-only authorization package:

```text
MAGICAL NMOS body-pin patch authorization package
```

AH-SMC-015 should prepare an exact, reviewable patch plan with file/line
targets, expected artifacts, rollback plan, and acceptance tests. It must not
modify `/home/qlf/IOT/references/MAGICAL-/`. Actual MAGICAL- modification
requires explicit user approval after AH-SMC-015.
