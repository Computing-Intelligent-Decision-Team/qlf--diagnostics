# Codex Review: AH-SMC-011 Fan_SMC M23 Body-Contact Probe

## Review Summary

Codex accepts AH-SMC-011 as `accepted_negative_diagnostic_with_scope_caveat`.

The accepted finding is narrow: the GDS-level M23 body-contact injection did not
change Magic extraction. The extracted substrate remained `vout`, the
`vout`/`vdda`/`gnda` equivalence records remained present, and M23's extracted
body terminal remained `vout`.

This weakens the hypothesis that a single local M23 body-contact shape can fix
the current extraction collapse. It does not cleanly disprove the broader
NMOS `.pin` contract hypothesis, because AH-SMC-011 did not modify the `.pin`
contract. It added geometry directly to GDS and used a long horizontal met5
connection that may intersect existing vout-associated met5 routing.

Fan_SMC remains a failure-case diagnostic sample only. It is not reward-safe,
post-simulation-safe, training-safe, or parasitic-modeling-safe.

## Checked Artifacts

| Artifact | Path | Review result |
| --- | --- | --- |
| AH-SMC-011 summary | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/ah_smc_011_summary.md` | Present; includes before/after extraction and trust boundary |
| AH-SMC-011 records | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/ah_smc_011_records.json` | Present; valid JSON |
| Modified GDS | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/fan_smc_pin_3.m23_body.gds` | Present; generated in isolated AH-SMC-011 directory |
| After `.ext` | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/fan_smc_pin_3.m23_body.ext` | Confirms substrate/equiv/device state remains collapsed |
| After extracted SPICE | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/fan_smc_pin_3.m23_body.spice` | Confirms M23 and all NMOS bodies remain `vout` |
| Magic TCL | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/magic_body_contact.tcl` | Shows direct GDS paint plus horizontal met5 connector |
| Claude run report | `docs/claude_code_run_report.md` | Contains AH-SMC-011 section |

## Scope Gate

| Gate | Result | Notes |
| --- | --- | --- |
| Observation-only diagnostic | Pass | No closure or controller integration claimed |
| Isolated output directory | Pass | New artifacts are under `ah_smc_011/` |
| No controller/reward/GRPO/closure changes | Pass | No such changes are part of this review |
| No SMCNR status copied to Fan_SMC | Pass | Fan_SMC remains separate from the SMCNR positive baseline |
| No DFCFC2 execution | Pass | Scope remains Fan_SMC only |
| No post-sim/PVT/training claim | Pass | Trust remains failure-case only |
| Clean NMOS `.pin` contract probe | Fail as phrased | The `.pin` fourth pin was not modified; geometry was added directly to GDS |
| Single-variable purity | Pass with caveat | Only one local body-contact stack was intended, but the long met5 connector is a possible contaminating route |

There are pre-existing unrelated working-tree changes in the repository. They
are outside the AH-SMC-011 review scope and were not reverted.

## Technical Findings

### 1. Magic Extraction Remained Collapsed

Codex independently checked the after `.ext` file. It still contains:

```text
substrate "vout"
equiv "vout" "vdda"
equiv "vout" "gnda"
```

The M23 device record also remains unchanged in the key terminal fields:

```text
device msubckt sky130_fd_pr__nfet_01v8 ... "vout" ... "vout" ... "vout" ...
```

This supports Claude's core result: adding the M23 body-contact geometry did not
move the extracted body/substrate identity from `vout` to `gnda`.

### 2. Extracted SPICE Confirms No Body-Terminal Repair

The after SPICE still includes:

```text
X23 vout a_220_2930# vout vout sky130_fd_pr__nfet_01v8 ...
```

All NMOS extracted body terminals remain `vout`. No Fan_SMC trust flag can be
upgraded from this run.

### 3. AH-SMC-011 Did Not Actually Modify The `.pin` Contract

The records file says:

```text
after_pin_fourth = -1 (pin file not modified; geometry added directly to GDS)
```

That means AH-SMC-011 is not a clean test of the hypothesis from AH-SMC-010:
"if the generated NMOS `.pin` contract provides a real fourth body pin geometry
tied to `gnda`, Magic extraction should change."

Instead, AH-SMC-011 tested a narrower GDS intervention:
"if a directly painted M23 body-contact stack is connected to gnda by met5,
Magic extraction should change."

That narrower hypothesis is not supported by the artifacts.

### 4. The Horizontal Met5 Connector Is A Plausible Contaminant

The Magic TCL paints:

```text
box 400 11200 5550 11500
paint met5
```

This is a long horizontal met5 span across a dense layout. Claude's own report
records 2258 Magic GDS write problems and says the connector likely crossed
existing vout-associated met5. Codex agrees this is a credible contamination
risk.

Therefore AH-SMC-011 strengthens the psub/diffusion-connectivity concern, but
it should not be used as a final proof that `.pin` repair via the proper router
would fail.

## Trust Boundary Decision

AH-SMC-011 remains failure-case only:

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

## Corrected Conclusion

Use this wording going forward:

```text
AH-SMC-011 disproves the narrow GDS-level intervention: directly adding an M23
body-contact stack and met5 connection to gnda did not change Magic's extracted
body/substrate assignment.

It does not fully disprove the broader NMOS .pin contract hypothesis, because
the .pin contract was not modified and the met5 connector may have crossed
existing vout routing.

H2, diffusion/psub connectivity dominance, is strengthened but still needs a
cleaner contamination audit or direct single-variable test.
```

## Next Single-Variable Experiment

Proceed to AH-SMC-012:

```text
Fan_SMC AH-SMC-011 met5 contamination audit and clean-router feasibility check
```

Recommended hypothesis:

```text
If AH-SMC-011's horizontal met5 connector intersects existing vout-associated
geometry, then the AH-SMC-011 negative result is contaminated and cannot be used
to reject a clean NMOS .pin/router repair.
```

Constraints:

- read-only audit first; do not create another repaired candidate in AH-SMC-012;
- inspect the AH-SMC-011 horizontal met5 box against baseline met5 geometry;
- report whether any overlapped met5 shape is plausibly tied to `vout`,
  `vdda`, `gnda`, or unknown;
- keep all outputs under `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_012/`;
- do not change C0;
- do not modify controller, reward, GRPO, optimizer, or closure logic;
- do not run DFCFC2;
- do not claim closure, post-layout simulation, PVT, reward, or training use.

Acceptance evidence for AH-SMC-012 should include:

- the exact AH-SMC-011 met5 connector box under audit;
- a table of all intersecting baseline met5 shapes with coordinates and
  inferred/unknown net labels;
- explicit conclusion: `contaminated`, `not_contaminated`, or `inconclusive`;
- a recommended next clean experiment if contamination is found;
- trust decision remains failure-case only.

## Phase Decision

Fan_SMC may proceed to the next diagnostic phase: AH-SMC-012 read-only met5
contamination audit.

Fan_SMC may not proceed to closure, post-layout simulation, PVT, reward, or
training use.

DFCFC2 remains pending until the Fan_SMC diagnostics path produces a verified
repair pattern or a clearer adapter-level boundary.
