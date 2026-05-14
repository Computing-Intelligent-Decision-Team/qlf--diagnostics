# MAGICAL Sky130 Adapter Agent Rules

## Project Goal

The long-term goal is to replace MAGICAL's default mockPDK flow with a real
open-source Sky130 PDK flow. MAGICAL should eventually generate layouts using
real Sky130 layer, techfile, LEF, and GDS mappings, then enter Magic DRC and
Netgen LVS verification.

## Current Progress

- `examples/inverter_sky130_try` can run with
  `sky130_fd_pr__nfet_01v8` and `sky130_fd_pr__pfet_01v8` device names.
- `flow/python/DesignDB.py` supports Sky130 MOS device-name recognition.
- `convert_sky130_netlist.py` can convert an xschem Sky130 inverter netlist to
  MAGICAL-readable format.
- `generated/sky130PDK_trial` can be read by MAGICAL and used for the inverter
  trial flow.
- `remap_gds_to_sky130.py` can generate
  `examples/inverter_sky130_try/inverter_core.sky130.gds`.
- MAGICAL `CO` is mapped to Sky130 `licon1.drawing` on GDS `66/44`.
- Local Sky130 `sky130A.lyp` and `sky130A.magicrc` have been found.

## Working Principles

- Prefer small, reversible, verifiable changes.
- Do not do a large MAGICAL flow refactor in one step.
- Do not directly overwrite `examples/mockPDK`.
- Do not directly overwrite `examples/sky130PDK` unless explicitly requested.
- Prefer writing outputs to `generated/` or `docs/`.
- Do not commit automatically.
- After each change, explain which files changed, how to test, and what success
  looks like.

## Important Paths

- `examples/inverter_sky130_try/`
- `examples/sky130PDK/`
- `generated/sky130PDK_trial/`
- `docs/sky130_adapter/`
- `tools/sky130_adapter/`
- `flow/python/DesignDB.py`

## Current Focus

- Magic DRC automation.
- DRC log analysis.
- GDS layer remap validation.
- Magic extraction.
- Netgen LVS.
- Gradual migration from the mockPDK-compatible trial PDK to a real Sky130 PDK
  interface.

## Prohibited Actions

- Do not delete existing test files.
- Do not delete `inverter_core.sky130.gds`.
- Do not modify the Docker image.
- Do not claim real Sky130 DRC-clean adaptation is complete.
- Do not treat layer/datatype remapping as equivalent to DRC clean.
- Do not treat `examples/sky130PDK` remaining a mockPDK copy as the final goal.
