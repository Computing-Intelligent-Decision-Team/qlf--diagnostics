# AH-SMC-010 Claude Task: Fan_SMC Primitive/Body/Substrate Minimization

## Objective

Create a minimal, auditable evidence package that localizes the first
Fan_SMC extraction divergence after AH-SMC-009.

This task is not a closure attempt. It must not claim that Fan_SMC is DRC/LVS
closed, post-sim safe, reward safe, or training safe.

## Starting Point

Use these reviewed facts as the baseline:

- AH-SMC-009 added one top-level p+ substrate tap tied to `gnda`.
- The added tap is present and Magic DRC reports zero errors.
- Magic extraction still records:

```text
substrate "vout"
equiv "vout" "vdda"
equiv "vout" "gnda"
```

- Netgen LVS still fails.
- Trust gate remains failure-case only.

Primary review:

```text
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_009_review.md
```

## Hypothesis

The next likely blocker is not "missing any p+ tap anywhere". The next blocker
is a lower-level primitive/body/substrate semantic mismatch, such as:

- Magic chooses `vout` as the extracted substrate identity before the added tap
  can anchor the intended `gnda` substrate domain.
- The generated NMOS primitive/pin contract lacks a physical fourth body pin
  while the source netlist uses explicit `B=gnda`.
- A local terminal-collapse issue around M11/M23 causes source/body/power nets
  to merge before LVS normalization.

AH-SMC-010 should gather evidence to separate these possibilities.

## Inputs

Read these artifacts first:

```text
/home/qlf/IOT/references/AnalogHarness/AGENTS.md
/home/qlf/IOT/references/AnalogHarness/docs/dfcfc2_smc_campaign_status.md
/home/qlf/IOT/references/AnalogHarness/docs/codex_ah_smc_009_review.md
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/fan_smc_pin_3_flat.ext
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/fan_smc_pin_3_flat.spice
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/device_mapping.json
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/psub_substrate_geometry.json
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/ext_key_records.txt
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/trust_decision.json
```

If a listed file is missing, record the missing path exactly and stop before
inventing replacement evidence.

## Allowed Work

Observation-only analysis is preferred.

Allowed outputs:

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_010/
/home/qlf/IOT/references/AnalogHarness/docs/claude_code_run_report.md
```

Allowed operations:

- Extract and tabulate `.ext` substrate, `equiv`, and device terminal records.
- Compare baseline bounded-C0 artifacts against AH-SMC-009 psub-tap artifacts.
- Produce small JSON/Markdown reports under the AH-SMC-010 output directory.
- If needed, create one read-only Python analysis script under the AH-SMC-010
  output directory.
- Run focused diagnostics tests after analysis if any diagnostic helper is used:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

## Forbidden Work

Do not:

- Modify controller, reward, GRPO, closure-level, or optimizer behavior.
- Modify SMCNR artifacts or copy SMCNR pass status to Fan_SMC.
- Modify files under `/home/qlf/IOT/references/MAGICAL-/`.
- Run a full new P&R campaign.
- Run DFCFC2.
- Change MOS primitive definitions, C0, or add another GDS repair.
- Commit or push.
- Claim closure, training safety, reward safety, or post-sim safety.

## Required Evidence Tables

Produce a concise AH-SMC-010 report containing these tables.

### 1. Substrate Identity Table

Compare baseline and AH-SMC-009:

- `.ext` path
- exact `substrate` record
- exact `equiv` records
- whether `vout`, `vdda`, and `gnda` are still collapsed

### 2. Device Terminal Divergence Table

For M11, M23, and one comparison PMOS instance:

- source terminals `(D G S B)`
- MAGICAL `.pin` fourth-pin status if available
- extracted terminal record from `.ext`
- extracted SPICE instance line
- first observed mismatch class:
  - `body_net_changed`
  - `source_drain_collapsed`
  - `gate_collapsed`
  - `zero_area_symptom`
  - `unclassified`

### 3. Baseline vs P+ Tap Delta Table

Compare baseline bounded-C0 and AH-SMC-009:

- DRC status
- substrate record
- `equiv` records
- Netgen LVS status
- trust-gate usability flags
- conclusion: `changed`, `unchanged`, or `insufficient_evidence`

## Required Output Files

Write:

```text
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_010/ah_smc_010_summary.md
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_010/ah_smc_010_records.json
```

Append a short AH-SMC-010 section to:

```text
docs/claude_code_run_report.md
```

## Acceptance Criteria

Codex will review AH-SMC-010 only if:

- All evidence paths are absolute paths.
- Every table cell that claims a signal/net comes from a concrete artifact line
  or structured field.
- The report explicitly says AH-SMC-009 did not repair the short/equiv collapse.
- The report does not propose a new repair unless it is clearly marked as a
  hypothesis for Codex review.
- Trust flags remain failure-case only.
- No controller/reward/GRPO/closure files changed.
- No commit or push.
