# Codex Review: AH-SMC-013 Fan_SMC M23 `.pin` Contract Probe

## Review Summary

Codex rejects AH-SMC-013 as `rejected_until_artifact_correction`.

The extraction artifacts do show a significant change: substrate identity shifts
from `vout` to `net31`, equivalence records become net31-centric, and M23's
extracted gate becomes `net049`. However, the claimed independent variable is
not present in the auditable artifacts. The reported modified `.pin` file still
has M23 pin 4 as `-1`, byte-identical to the baseline `.pin`.

Therefore Codex cannot accept the conclusion that the M23 `.pin` contract change
caused the extraction delta. The run may still contain useful evidence about
rerunning the Fan_SMC pipeline and Sky130 post-processing, but it is not an
accepted clean `.pin` contract experiment.

Fan_SMC remains a failure-case diagnostic sample only. It is not reward-safe,
post-simulation-safe, training-safe, or parasitic-modeling-safe.

## Blocking Finding

### 1. The Claimed `.pin` Change Is Missing

AH-SMC-013 reports:

```text
M23 pin 4: -1 -> -200 -200 1400 -150
```

Codex independently compared:

```text
generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.pin
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013/case/fan_smc_pin_3.pin
```

Both files have identical SHA256:

```text
d62cc163d43ad25f3c03584c3420b4397093975eb2f8c554728d71607f30a4c3
```

Both files contain:

```text
fan_smc_pin_3_M23 4
1150 -50 1250 1050
-50 1150 1250 1250
-50 -50 50 1050
-1
```

No file under `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013/`
contains the claimed pin box except the narrative reports:

```text
-200 -200 1400 -150
```

This fails AH-SMC-013's primary acceptance gate.

## What Is Still Useful

The generated AH-SMC-013 extraction is real and different from prior extraction:

```text
substrate "net31"
equiv "net31" "net050"
equiv "net31" "vout"
equiv "net31" "vdda"
equiv "net31" "gnda"
```

M23's extracted SPICE line also changes to:

```text
X23 net31 net049 net31 net31 sky130_fd_pr__nfet_01v8 ...
```

This means the rerun/post-processing path produced a materially different
layout/extraction state. But without the modified `.pin` artifact, the cause is
not proven. Possible explanations include nondeterministic rerouting, changed
post-processing, changed generated case state, or an unpreserved temporary
`.pin` edit that was overwritten before artifact packaging.

## Scope Gate

| Gate | Result | Notes |
| --- | --- | --- |
| Isolated output directory | Pass | AH-SMC-013 artifacts are under `ah_smc_013/` |
| MAGICAL reroute attempted | Pass | New route/place GDS artifacts exist and differ by SHA256 |
| Extraction compared | Pass | `.ext` and SPICE deltas are recorded |
| No manual GDS painting claimed | Pass with caveat | No paint script found in AH-SMC-013 artifacts |
| Only M23 `.pin` fourth entry changed | **Fail** | Auditable `.pin` files show no change at all |
| Replacement pin box preserved | **Fail** | The claimed box appears only in summary/records text |
| Causal claim accepted | **Fail** | Extraction delta cannot be attributed to `.pin` change |
| Trust remains failure-case only | Pass | No safety upgrade claimed |

There are pre-existing unrelated working-tree changes in the repository. They
are outside the AH-SMC-013 review scope and were not reverted.

## Corrected Status

Use this wording going forward:

```text
AH-SMC-013 generated a different Fan_SMC routed/extracted artifact, and the
extraction shifted from vout-centric collapse to net31-centric collapse.
However, the claimed M23 .pin modification is absent from the preserved
artifact package, so this run does not prove that the .pin contract change
caused the extraction delta.
```

Do not use AH-SMC-013 to support:

- `.pin` contract hypothesis partially supported;
- M23 body pin changed routing;
- H2 strengthened by clean `.pin` evidence;
- all-12 NMOS body-pin repair recommendation.

Those may become valid later, but AH-SMC-013 as packaged does not prove them.

## Trust Boundary Decision

AH-SMC-013 remains failure-case only:

```json
{
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true
}
```

No Fan_SMC artifact is promoted to reward, post-layout simulation, training, or
parasitic-modeling use.

## Required Correction

Proceed to AH-SMC-013R:

```text
Fan_SMC M23 .pin artifact correction and rerun
```

AH-SMC-013R must first establish an auditable pin delta before any extraction
claim is reviewed.

Acceptance evidence for AH-SMC-013R:

- preserve `before.pin` and `after.pin` in the AH-SMC-013R directory;
- include `pin.diff` showing exactly one changed line in M23 only;
- compute SHA256 for before/after `.pin`;
- show M23 pin 4 is `-200 -200 1400 -150` or a newly justified replacement;
- run MAGICAL using the preserved `after.pin`;
- after MAGICAL returns, confirm the `.pin` file was not overwritten before
  packaging;
- if Magic extraction is run, compare `.ext` and SPICE again;
- trust decision remains failure-case only.

## Phase Decision

Fan_SMC may proceed only to AH-SMC-013R artifact correction. It may not proceed
to all-NMOS repair, closure, post-layout simulation, PVT, reward, or training
use until the one-device `.pin` experiment is auditable.
