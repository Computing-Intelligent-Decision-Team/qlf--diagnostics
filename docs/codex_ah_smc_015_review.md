# Codex Review: AH-SMC-015 MAGICAL NMOS Body-Pin Patch Authorization Package

## Review Summary

Codex rejects AH-SMC-015 pending correction as `rejected_patch_plan_layer_semantics`.

AH-SMC-015 satisfies the read-only packaging shape: it produced a valid JSON
record, a detailed authorization document, and did not present any Fan_SMC
closure, training, reward, post-simulation, or LVS pass claim.

However, the recommended Option B is not technically executable as written. It
mixes Sky130 GDS layer numbers with MAGICAL internal `ioLayer` indices. The
proposal repeatedly sets `ioLayer = 67` for `li1`, but
`/home/qlf/IOT/references/MAGICAL-/flow/python/Placer.py:527-528` writes `-1`
whenever `layer > 10`. Therefore an `ioLayer` value of 67 would still be
classified as an absent pin.

This is a blocking issue for an authorization package because AH-SMC-016 would
otherwise start from a patch plan that cannot produce the claimed `.pin`
change.

## Checked Artifacts

| Artifact | Path | Review result |
| --- | --- | --- |
| AH-SMC-015 authorization doc | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015/ah_smc_015_patch_authorization.md` | Present |
| AH-SMC-015 records | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015/ah_smc_015_records.json` | Present; valid JSON |
| Claude run report | `docs/claude_code_run_report.md` | Contains AH-SMC-015 section |

## Blocking Findings

### 1. `ioLayer = 67` Cannot Avoid The `-1` Sentinel

AH-SMC-015 recommends Option B:

```text
Inject synthetic body pin ioShape with metal ioLayer=67 (li1)
```

But the local MAGICAL writer uses the internal layer threshold:

```text
/home/qlf/IOT/references/MAGICAL-/flow/python/Placer.py:527
if layer > 10:
    outFile.write("-1\n")
```

So the proposed `ioLayer = 67` would still satisfy `layer > 10` and would still
write `-1`. The authorization package must use a verified MAGICAL internal
routable layer index, not a final Sky130 GDS layer number.

Likely relevant prior evidence: older Sky130 adapter docs distinguish MAGICAL
internal layers from final Sky130 GDS export layers. For example, the trial GDS
mapping records MAGICAL internal `31` as exported to Sky130 `li1 67/20`, while
top-level `ioPin` post-processing maps internal `ioPin` layer `1` to Sky130
`li1.label 67/5`. AH-SMC-015R must verify the exact layer index used by this
MAGICAL `.pin`/placer path before recommending a patch.

### 2. `setIoShape` Argument Order Is Wrong In The Pseudo-Diff

AH-SMC-015's Option B pseudo-diff calls:

```text
setIoShape(body_y1, body_x1, body_y2, body_x2)
```

The local API expects:

```text
setIoShape(xLo, yLo, xHi, yHi)
```

This is confirmed by:

```text
/home/qlf/IOT/references/MAGICAL-/flow/cpp/magical_flow/src/db/GraphComponents.h:246
/home/qlf/IOT/references/MAGICAL-/flow/python/Router.py:47
/home/qlf/IOT/references/MAGICAL-/flow/python/Device_generator.py:75-77
```

The same coordinate-order issue appears in the alternative `DesignDB.py`
pseudo-diff. This must be corrected before any patch run is authorized.

### 3. Option A And Option C Repeat The Same Layer-Semantics Problem

Option A says the primitive should use `li1 (67)` or `met1 (68)` as the
`ioLayer`. Option C also assigns `layer = 67`.

Those are Sky130 GDS layer numbers, not necessarily MAGICAL internal `ioLayer`
values. AH-SMC-015R must revise every option so that:

- MAGICAL internal layer indices are used before GDS remap;
- Sky130 GDS layer/datatype pairs are mentioned only as export targets;
- the chosen internal layer is proven to pass `layer <= 10` in
  `Placer.placeParsePin()`.

## Non-Blocking Notes

- Option B remains a reasonable diagnostic direction after correction because
  it avoids initializing the external `device_generation` submodule and tests
  whether the database-visible body pin metadata changes `.pin`, routing, and
  extraction.
- Option A remains the likely production direction if the diagnostic confirms
  the hypothesis, because a metadata-only body pin without actual p+ tap
  geometry may not be enough for Magic extraction.
- The current MAGICAL- repository has many pre-existing dirty files from prior
  work. This review does not attribute those to AH-SMC-015, but the next actual
  patch run must preserve an exact before/after source diff for any MAGICAL
  files it modifies.

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

## Required Correction

Proceed to AH-SMC-015R:

```text
Correct the patch authorization package before any MAGICAL source change.
```

AH-SMC-015R must not modify MAGICAL. It should revise the authorization package
to:

- replace `ioLayer = 67/68` with a verified MAGICAL internal routable layer
  index;
- cite the source proving that internal layer maps to the intended Sky130
  export layer;
- correct all `setIoShape(xLo, yLo, xHi, yHi)` calls;
- include a preflight assertion that the chosen body pin `ioLayer <= 10`;
- keep actual MAGICAL modification behind explicit user approval.
