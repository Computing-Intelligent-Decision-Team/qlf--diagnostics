# AH-SMC-011 Claude Task: Fan_SMC NMOS Body-Pin Contract Probe

## Objective

Execute a bounded single-variable diagnostic probe for the AH-SMC-010 finding:
all Fan_SMC NMOS instances have fourth-pin `-1` in the MAGICAL `.pin` contract,
while the source netlist requires explicit `B=gnda`.

This task should test whether a real NMOS fourth body-pin geometry can be
introduced in an isolated diagnostic copy and whether that changes the local
evidence around Magic extraction. It is not a closure task.

## Required Reading

Read these first:

```text
/home/qlf/IOT/references/AnalogHarness/AGENTS.md
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_010_review.md
/home/qlf/IOT/references/AnalogHarness/docs/dfcfc2_smc_campaign_status.md
/home/qlf/IOT/references/AnalogHarness/docs/trust_gate_evidence_contract.md
```

## Hypothesis

```text
If a selected NMOS instance receives a real fourth body-pin geometry tied to the
intended gnda body/substrate domain, then its extracted body terminal should no
longer default to vout.
```

This is a hypothesis, not a claim. AH-SMC-011 may disprove it.

## Scope

Use the bounded-C0 Fan_SMC diagnostic path. Start with one selected NMOS
instance, preferably M23, because AH-SMC-010 shows:

```text
source:    M23 (vout net049 gnda gnda)
.pin:      fourth pin = -1
extracted: body = vout
```

Use M11 only as a nearby PMOS comparison instance, not as the changed variable.

## Allowed Writes

Write only under:

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

Allowed operations:

- Copy required local Fan_SMC diagnostic artifacts into the AH-SMC-011 output
  directory.
- Create a copied `.pin` variant for one selected NMOS instance.
- Produce before/after tables for `.pin`, `.ext`, and extracted SPICE evidence.
- If a local extraction rerun is attempted, keep it isolated under AH-SMC-011
  output paths and record the exact command and result.
- If extraction cannot be rerun safely, stop after producing a static feasibility
  report and explain exactly what additional tool invocation is needed.

## Forbidden Work

Do not:

- Modify files under `/home/qlf/IOT/references/MAGICAL-/`.
- Modify original Fan_SMC artifacts outside the AH-SMC-011 output directory.
- Modify SMCNR artifacts.
- Modify controller, reward, GRPO, optimizer, or closure-level logic.
- Change C0 or add another substrate tap in the same run.
- Change more than one NMOS fourth-pin contract in the first probe.
- Run DFCFC2.
- Claim Fan_SMC closure, reward safety, training safety, or post-sim safety.
- Commit or push.

## Required Outputs

Write:

```text
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/ah_smc_011_summary.md
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/ah_smc_011_records.json
```

Append an AH-SMC-011 section to:

```text
docs/claude_code_run_report.md
```

## Required Evidence

### 1. Before/After Pin Contract Table

For the selected NMOS:

- source netlist instance line
- original `.pin` fourth-pin record
- copied diagnostic `.pin` fourth-pin record
- whether only one NMOS instance changed

### 2. Extraction Evidence Table

If extraction is rerun:

- Magic extraction command
- `.ext` substrate record
- `.ext` equiv records
- selected NMOS `.ext` device line
- selected NMOS extracted SPICE line
- whether body changed from `vout` to `gnda`, stayed unchanged, or became
  another net

If extraction is not rerun:

- exact blocker
- missing command/tool/config
- why no trust status can be upgraded

### 3. Trust Boundary Table

Always report:

```json
{
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true
}
```

Do not upgrade any trust flag in AH-SMC-011.

## Acceptance Criteria

Codex will review only if:

- the run changes at most one NMOS body-pin contract in an isolated copy;
- all paths are absolute;
- every claim cites a concrete artifact line or structured field;
- no C0, substrate-tap, controller, reward, GRPO, closure, DFCFC2, or SMCNR
  change is made;
- the report clearly states whether AH-SMC-011 supports, weakens, or leaves
  unresolved the NMOS body-pin hypothesis.
