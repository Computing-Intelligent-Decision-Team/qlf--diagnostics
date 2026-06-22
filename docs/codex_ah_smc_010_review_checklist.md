# Codex AH-SMC-010 Review Checklist

Use this checklist after Claude Code produces the AH-SMC-010 evidence package.
The review decides whether the package localizes the next Fan_SMC
primitive/body/substrate blocker. It does not decide that Fan_SMC is closed.

## Required Inputs

Claude must provide:

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_010/ah_smc_010_summary.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_010/ah_smc_010_records.json
```

Claude must also append an AH-SMC-010 section to:

```text
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

Codex should cross-check against these source artifacts:

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/fan_smc_pin_3_flat.ext
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/fan_smc_pin_3_flat.spice
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/device_mapping.json
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/psub_substrate_geometry.json
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/ext_key_records.txt
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/trust_decision.json
```

## Scope Gate

- [ ] Claude did not modify controller, reward, GRPO, optimizer, or closure
  logic.
- [ ] Claude did not modify SMCNR artifacts or copy SMCNR pass status to
  Fan_SMC.
- [ ] Claude did not modify files under `/home/qlf/IOT/references/MAGICAL-/`.
- [ ] Claude did not run DFCFC2.
- [ ] Claude did not claim Fan_SMC closure, training safety, reward safety, or
  post-sim safety.
- [ ] Claude did not commit or push.

If any item fails, reject the run as a process violation before technical
promotion.

## Structure Gate

- [ ] `ah_smc_010_summary.md` exists and is readable.
- [ ] `ah_smc_010_records.json` exists and is valid JSON.
- [ ] `docs/claude_code_run_report.md` contains an AH-SMC-010 section.
- [ ] All evidence paths in the report are absolute.
- [ ] The report includes the three required tables from
  `docs/ah_smc_010_claude_task.md`.
- [ ] Every asserted substrate/equiv/device terminal claim cites a concrete
  artifact line or structured field.

## Evidence Tables To Verify

### 1. Substrate Identity Table

Verify for both baseline and AH-SMC-009:

- [ ] `.ext` path is absolute and exists.
- [ ] Exact `substrate` record is quoted or represented losslessly.
- [ ] Exact `equiv` records are quoted or represented losslessly.
- [ ] `vout`, `vdda`, and `gnda` collapse status is derived from the raw `.ext`
  or `ext_key_records.txt`, not inferred from the conclusion.

### 2. Device Terminal Divergence Table

For M11, M23, and one comparison PMOS:

- [ ] Source `(D G S B)` terminals are traced to a source netlist artifact.
- [ ] MAGICAL `.pin` fourth-pin status is either cited from an artifact or
  explicitly marked missing/unchecked.
- [ ] Extracted `.ext` device terminal record is captured.
- [ ] Extracted SPICE instance line is captured.
- [ ] Mismatch class is one of:
  - `body_net_changed`
  - `source_drain_collapsed`
  - `gate_collapsed`
  - `zero_area_symptom`
  - `unclassified`
- [ ] `as=0 ps=0` is treated as an extraction symptom unless backed by
  additional geometry evidence.

### 3. Baseline vs P+ Tap Delta Table

Verify:

- [ ] DRC status is supported by an artifact or marked unknown.
- [ ] Substrate/equiv records are compared side by side.
- [ ] Netgen LVS status is supported by the p+ tap Netgen report.
- [ ] Trust-gate usability flags are taken from
  `trust_decision.json`.
- [ ] Conclusion is one of `changed`, `unchanged`, or
  `insufficient_evidence`.

## Technical Decision Gate

Classify AH-SMC-010 as exactly one:

- `accepted_localization`: enough evidence to name the first likely blocker and
  design the next single-variable experiment.
- `partial_localization`: evidence narrows the search but leaves at least one
  required trace missing.
- `return_to_claude`: required artifacts, tables, or citations are missing.
- `process_rejected`: scope or trust-boundary violation.

## Trust Boundary

The default AH-SMC-010 trust decision remains:

```json
{
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true
}
```

Codex may not change any field to true unless DRC, LVS, PEX, post-layout
simulation, PVT, and evidence scope are independently reviewed and backed by
direct local or curated artifacts.

## Codex Review Output

After review, write:

```text
docs/codex_ah_smc_010_review.md
```

It should include:

- review summary
- checked artifacts
- scope-gate result
- structure-gate result
- technical findings
- trust-boundary decision
- next single-variable experiment recommendation
- whether Fan_SMC may proceed to the next phase
