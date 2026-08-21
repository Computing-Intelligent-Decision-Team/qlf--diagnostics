# GRPO-to-PCS plugin-style architecture v1

Date: 2026-08-21

## Purpose

This document describes how to evolve the current GRPO-to-PCS bridge from a single-case smoke path into a plugin-style pipeline.

The goal is not to reproduce DeepSeek Harness. The useful idea to borrow is architectural:

```text
core pipeline stays generic;
source/mapping/admission/dataset behavior is injected by versioned adapters.
```

## Current state

The current smoke checkpoint proves this path works for one aligned case:

```text
AnalogGym-Opt amp_dfcfc2 fresh GRPO smoke
-> grpo_export_contract.v1
-> PCS L0 manifest input
-> leung_dfcfc2_pin_3 AnalogGym-aligned config
-> 4/4 replayable at L0
```

The weak point is that the PCS action mapping still lives partly in code. This is acceptable for a smoke checkpoint, but not enough for multi-circuit scaling.

## Target architecture

```text
GRPO / optimizer run
  |
  v
Source Adapter
  |
  v
Unified GRPO Export Contract
  |
  v
Action Mapping Adapter
  |
  v
PCS Admission Adapter
  |
  v
Dataset Adapter
```

## Adapter boundaries

### 1. Source adapter

Responsibility:

- Read one optimizer's native outputs.
- Preserve real `action_normalized`, `action_real`, rewards, pre-layout metrics, and provenance.
- Emit `grpo_export_contract.v1`.

Example:

```text
source adapter: analoggym_opt.v1
input: training_saves/grpo_amp_dfcfc2_YYYYMMDD-HHMMSS/
output: generated/grpo_exports/.../export.json
```

Non-responsibility:

- It does not map to PCS names.
- It does not decide physical admissibility.
- It does not repair missing actions.

### 2. Action mapping adapter

Responsibility:

- Map source action names to PCS sizing variable names.
- Attach units and integer semantics.
- Be versioned per source circuit and target PCS design.

Example:

```text
mapping adapter: amp_dfcfc2_to_leung_dfcfc2_pin_3.v1.yaml
W_M0 -> mosfet_0_8_w_biascm_pmos
L_M0 -> mosfet_0_8_l_biascm_pmos
M_M0 -> mosfet_0_8_m_biascm_pmos
```

Non-responsibility:

- It does not clip values to fit PCS bounds.
- It does not run layout or simulation.
- It does not imply L6 success.

### 3. PCS admission adapter

Responsibility:

- Convert mapped candidates to PCS manifest/source-state files.
- Run or summarize admission stages:

```text
L0 contract check
L1 source generation
L2 pre-layout sim
L3 layout
L4 DRC/LVS/PEX-ready physical closure
L5 raw PEX
L6 post-layout nominal/PVT
```

For smoke tests, only L0 is required.

### 4. Dataset adapter

Responsibility:

- Take only admitted raw-PEX samples.
- Parse capacitor edges from raw spice.
- Append graph-learning samples.
- Keep failed candidates as admission/failure evidence, not training labels.

## Proposed file layout

```text
tools/analog_harness/
  ml/
    grpo_export_contract.py
    action_mapping_contract.py
  action_mapping_contracts/
    amp_dfcfc2_to_leung_dfcfc2_pin_3.v1.yaml
docs/
  GRPO_export_contract_v1.md
  grpo_to_pcs_plugin_architecture_v1.md
generated/
  grpo_exports/
```

## Contract flow

### Step A: source export

```bash
python3 -m tools.analog_harness.ml.grpo_export_contract build-from-analoggym-run ...
```

Output:

```text
export.json
```

### Step B: mapping

```bash
python3 -m tools.analog_harness.ml.action_mapping_contract map-export ...
```

Output:

```text
pcs_manifest_input.jsonl
```

### Step C: PCS L0

Use the PCS admission adapter or current PCS manifest tooling:

```bash
python3 -m tools.analog_harness.analoggym_grpo_manifest ...
```

Output:

```text
pcs_l0/grpo_sizing_manifest.yaml
pcs_l0/replayable_sizing_manifest.yaml
pcs_l0/physical_closure_failure_labels.jsonl
```

## Why action order must be explicit

The 2026-08-21 smoke found a real ordering bug:

```text
Using sizing.keys() to reconstruct action order is unsafe because JSON object keys may be sorted.
```

The export contract therefore requires top-level:

```json
"action_parameter_names": ["W_M0", "L_M0", "M_M0", "..."]
```

All downstream consumers must use this vector order. They must not reconstruct it from sorted dictionaries.

## Minimum acceptance criteria for adding a new circuit

A new source/target pair can enter the pipeline only after it provides:

1. One source adapter output file following `grpo_export_contract.v1`.
2. One action mapping contract YAML.
3. A mapping validation result showing no missing source variables and no unknown PCS target variables.
4. A PCS L0 result showing replayable vs invalid counts.
5. A statement that no values were clipped or repaired during mapping.

## Near-term implementation plan

1. Keep `grpo_export_contract.py` as the source adapter for AnalogGym-Opt.
2. Add `action_mapping_contract.py`.
3. Move the current `amp_dfcfc2 -> leung_dfcfc2_pin_3` mapping out of code into YAML.
4. Rebuild the 2026-08-21 smoke `pcs_manifest_input.jsonl` through the YAML mapping.
5. Re-run PCS L0 and require the same result: 4 replayable, 0 invalid.

## Boundary

This architecture does not require changing GRPO, PCS layout, MAGICAL, Magic, Netgen, or the parasitic graph parser. It only clarifies how optimizer outputs are safely admitted into PCS.
