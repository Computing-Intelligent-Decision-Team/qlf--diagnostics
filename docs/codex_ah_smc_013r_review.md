# Codex Review: AH-SMC-013R Fan_SMC M23 `.pin` Artifact Correction

## Review Summary

Codex accepts AH-SMC-013R as `accepted_blocker`.

AH-SMC-013R corrects the AH-SMC-013 artifact gap: it preserves `before.pin`,
`after.pin`, `final.pin`, SHA256 files, and `pin.diff`. The pin delta is now
auditable and shows exactly one intended change: M23 pin 4 from `-1` to
`-200 -200 1400 -150`.

The experiment is blocked because the preserved post-P&R `final.pin` is
byte-identical to `before.pin`. The current `Magical.py` entry point does not
leave the external `.pin` edit in the final case artifact, so the external
`.pin` edit cannot be used as a stable, auditable single-variable contract
through this flow.

Fan_SMC remains a failure-case diagnostic sample only. It is not reward-safe,
post-simulation-safe, training-safe, or parasitic-modeling-safe.

## Checked Artifacts

| Artifact | Path | Review result |
| --- | --- | --- |
| AH-SMC-013R summary | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013r/ah_smc_013r_summary.md` | Present |
| AH-SMC-013R records | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013r/ah_smc_013r_records.json` | Present; valid JSON |
| `before.pin` | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013r/case/before.pin` | M23 pin 4 is `-1` |
| `after.pin` | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013r/case/after.pin` | M23 pin 4 is `-200 -200 1400 -150` |
| `final.pin` | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013r/case/final.pin` | M23 pin 4 reverted to `-1` |
| `pin.diff` | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013r/case/pin.diff` | Exactly one changed line |
| Claude run report | `docs/claude_code_run_report.md` | Contains AH-SMC-013R section |

## Technical Findings

### 1. The Pin Delta Is Now Auditable

Codex independently parsed the three `.pin` files:

```text
before -> after diffs: fan_smc_pin_3_M23 only
before -> final diffs: none
after -> final diffs: fan_smc_pin_3_M23 only
```

The preserved diff is:

```diff
66c66
< -1
---
> -200 -200 1400 -150
```

This satisfies the artifact-correction requirement that AH-SMC-013 failed.

### 2. The Final Routed Case Does Not Preserve The External Edit

The SHA256 evidence is decisive:

```text
before.pin = d62cc163d43ad25f3c03584c3420b4397093975eb2f8c554728d71607f30a4c3
final.pin  = d62cc163d43ad25f3c03584c3420b4397093975eb2f8c554728d71607f30a4c3
after.pin  = 657e6533c33c4352760c213e77febf6cf9526bbfc814af1fb326097f1e09844a
```

The routed case artifact ends with M23 pin 4 restored to `-1`. Therefore this
flow cannot prove that the routed GDS was generated from the modified `.pin`
contract in a stable, inspectable way.

### 3. Reroute Variance Invalidates AH-SMC-013's Causal Claim

AH-SMC-013R records three different route hashes across the original run,
AH-SMC-013, and AH-SMC-013R. Since AH-SMC-013's preserved `.pin` also ended with
M23 pin 4 as `-1`, the AH-SMC-013 extraction delta must not be attributed to the
claimed `.pin` change.

Codex accepts the narrower claim:

```text
The current external .pin editing workflow is not a valid single-variable test.
```

Codex does not claim:

```text
MAGICAL never read after.pin at any intermediate moment.
```

That would require instrumentation inside MAGICAL, which is outside the current
allowed write scope.

## Scope Gate

| Gate | Result | Notes |
| --- | --- | --- |
| `before.pin`, `after.pin`, `final.pin` preserved | Pass | All present |
| `pin.diff` preserved | Pass | Present |
| Exactly one M23 pin change in `before -> after` | Pass | Parser confirmed |
| MAGICAL overwrite/blocker recorded | Pass | `before == final` |
| No manual GDS painting | Pass | No GDS repair script in this task |
| No controller/reward/GRPO/closure changes | Pass | No such changes in scope |
| No SMCNR status copied to Fan_SMC | Pass | Fan_SMC remains separate from positive baseline |
| No DFCFC2 run | Pass | Scope remains Fan_SMC only |
| No closure/training/reward/post-sim claim | Pass | Trust remains failure-case only |

There are pre-existing unrelated working-tree changes in the repository. They
are outside the AH-SMC-013R review scope and were not reverted.

## Corrected Campaign Status

The current Fan_SMC status is:

```text
External .pin editing is blocked as a clean experiment path.
The NMOS .pin/body contract hypothesis remains unresolved.
Testing it now requires read-only provenance analysis of MAGICAL's pin
generation path, followed by explicit permission before any MAGICAL- code
change.
```

## Trust Boundary Decision

AH-SMC-013R remains failure-case only:

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

## Next Step

Proceed to AH-SMC-014:

```text
Fan_SMC MAGICAL .pin generation provenance audit
```

AH-SMC-014 must be read-only. It should identify where MAGICAL generates or
regenerates `.pin`, whether `routeMosBulkEqualBodyPins` or related primitive
metadata controls NMOS body pins, and what minimal internal change would be
needed if the user later approves MAGICAL- modifications.

No MAGICAL- file writes are allowed in AH-SMC-014.
