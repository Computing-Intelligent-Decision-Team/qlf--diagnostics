# Codex Review: AH-SMC-012 Fan_SMC Met5 Contamination Audit

## Review Summary

Codex accepts AH-SMC-012 as `accepted_contamination_audit`.

The accepted finding is: AH-SMC-011's manually painted horizontal met5 connector
bridged a 300-unit met5-layer gap between a gnda-confirmed left tree and a
previously separate right-side met5 tree of unknown net assignment. That makes
AH-SMC-011 an impure experiment and invalidates it as a clean test of the NMOS
body-contact or `.pin` contract hypothesis.

The accepted finding is intentionally narrower than "the right tree is proven
vout." AH-SMC-012 supports that the right tree is suspicious because it reaches
the M23 device area, and AH-SMC-011 extraction assigned M23 terminals to `vout`.
But the right tree's net remains `unknown` in the met5 audit. Therefore the
safe conclusion is contamination, not a proven vout short.

Fan_SMC remains a failure-case diagnostic sample only. It is not reward-safe,
post-simulation-safe, training-safe, or parasitic-modeling-safe.

## Checked Artifacts

| Artifact | Path | Review result |
| --- | --- | --- |
| AH-SMC-012 summary | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_012/ah_smc_012_summary.md` | Present; includes method, intersection table, classification, trust boundary |
| AH-SMC-012 records | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_012/ah_smc_012_records.json` | Present; valid JSON |
| Audit script | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_012/met5_contamination_audit.py` | Present; parses baseline GDS and connector intersections |
| Claude run report | `docs/claude_code_run_report.md` | Contains AH-SMC-012 section |
| AH-SMC-011 connector source | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/magic_body_contact.tcl` | Connector box matches `[400, 11200, 5550, 11500]` |

## Scope Gate

| Gate | Result | Notes |
| --- | --- | --- |
| Read-only with respect to layout repair | Pass | AH-SMC-012 produced reports/scripts only |
| Connector box audited exactly | Pass | `[400, 11200, 5550, 11500]` |
| Baseline GDS recorded with absolute path | Pass | Uses AH-SMC-009 psub-tap baseline GDS |
| Every intersecting met5 shape reported | Pass | 18 intersections recorded |
| Net inference is evidence-backed or unknown | Pass | 8 gnda, 10 unknown |
| Classification is allowed value | Pass | `contaminated` |
| No controller/reward/GRPO/closure changes | Pass | No such changes are in scope |
| No SMCNR status copied to Fan_SMC | Pass | Fan_SMC remains separate from positive baseline |
| No DFCFC2 run | Pass | Scope remains Fan_SMC only |
| No closure/training/reward/post-sim claim | Pass | Trust remains failure-case only |

There are pre-existing unrelated working-tree changes in the repository. They
are outside the AH-SMC-012 review scope and were not reverted.

## Technical Findings

### 1. The Connector Intersects Both Gnda And Unknown Met5 Regions

The records file confirms:

```text
connector_box = [400, 11200, 5550, 11500]
total_intersecting_met5_shapes = 18
inferred nets = 8 gnda, 10 unknown
```

This already fails the clean-path requirement. A connector intended to tie M23
body contact to gnda cannot be treated as clean if it also intersects an unknown
met5 tree in the device area.

### 2. The 300-Unit Met5 Gap Makes AH-SMC-011 A New Bridge

AH-SMC-012 identifies:

```text
left_tree_max_x = 1850
right_tree_min_x = 2150
gap_width_units = 300
gap_y_range = [11200, 11500]
```

The AH-SMC-011 connector spans x=400 to x=5550 across the same y-band, so it
created a met5-layer bridge across a region that previously had no met5 shape.
That is enough to classify AH-SMC-011 as contaminated.

### 3. The Right Tree Is Suspicious But Still Unknown

The right tree reaches the M23 device area. Shape #18 is recorded at:

```text
[5150, 11350, 5250, 12450]
```

This lies inside the recorded M23 layout box, and AH-SMC-011 extraction kept M23
source/body/drain assigned to `vout`. That makes the right tree suspicious.

However, AH-SMC-012 correctly marks the right tree's met5 net as `unknown`. Codex
does not promote it to proven `vout` without a label, extracted net backtrace,
or multi-layer connectivity proof.

### 4. Documentation Caveat

`ah_smc_012_records.json` contains a small consistency issue:

```text
right_tree_unknown.shape_count = 10
right_tree_unknown.shapes = [11, 12, 13, 14, 15, 16, 17, 18]
```

The listed right-tree shapes are 8 entries. The other 2 unknown shapes are
reported separately as bridge shapes #9 and #10. This does not change the review
decision because the global intersection count is correct: 18 total
intersections, 8 gnda, and 10 unknown.

### 5. Script Caveat

The saved audit script's internal fallback classification logic would classify
"gnda + unknown" as `inconclusive`. The final report upgrades the classification
to `contaminated` using the added gap/tree analysis. Codex accepts the final
classification because a manual connector bridging gnda to an unknown previously
separate tree is sufficient to invalidate AH-SMC-011 as a clean experiment.

## Impact On AH-SMC-011

AH-SMC-011 should now be treated as:

```text
invalidated_as_clean_experiment
```

The following AH-SMC-011 conclusions are withdrawn or narrowed:

- Withdraw: "H1 is disproven at the single-variable level."
- Withdraw: "H2 is strengthened by the negative body-contact result."
- Keep: "The manually injected geometry was detected, but the run did not repair extraction."
- Keep: "Fan_SMC remains failure-case only."

The broader NMOS `.pin` contract hypothesis remains untested by a clean
experiment.

## Trust Boundary Decision

AH-SMC-012 remains failure-case only:

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

## Next Single-Variable Experiment

Proceed to AH-SMC-013:

```text
Fan_SMC M23 .pin contract repair feasibility probe
```

Recommended hypothesis:

```text
If M23's NMOS fourth `.pin` entry is replaced with a real body-pin geometry and
MAGICAL's own legalizer/router is used to generate routing, then the experiment
tests the NMOS `.pin` contract without manual met5 contamination.
```

Constraints:

- use an isolated copy under `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013/`;
- change only M23's fourth `.pin` entry in the first probe;
- do not manually paint met5, contacts, taps, or body-contact geometry into GDS;
- prefer MAGICAL legalizer/router or the repo's existing Fan_SMC pipeline entry;
- if the full reroute cannot be reproduced, stop and record the exact blocker;
- do not change C0;
- do not modify controller, reward, GRPO, optimizer, or closure logic;
- do not run DFCFC2;
- do not claim closure, post-layout simulation, PVT, reward, or training use.

Acceptance evidence for AH-SMC-013 should include:

- before/after `.pin` snippet for M23 only;
- exact rationale for the replacement body-pin box;
- command log for the attempted MAGICAL reroute or the exact reproducibility
  blocker;
- if a new GDS is generated, Magic extraction `.ext` and SPICE before/after
  comparison for substrate/equiv/M23 body;
- no manual GDS paint steps;
- trust decision remains failure-case only.

## Phase Decision

Fan_SMC may proceed to the next diagnostic phase: AH-SMC-013 isolated M23
`.pin` contract repair feasibility probe.

Fan_SMC may not proceed to closure, post-layout simulation, PVT, reward, or
training use.

DFCFC2 remains pending until the Fan_SMC diagnostics path produces a verified
repair pattern or a clearer adapter-level boundary.
