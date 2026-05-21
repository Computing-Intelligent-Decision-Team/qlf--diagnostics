# Sky130 Case Regression

## Goal

The Sky130 adapter work now has two working baseline cases:

- `inverter_core`
- `ota_core`

Both run through the generic case pipeline. The regression framework keeps these
cases in one registry and produces one summary table so future Sky130 flow
changes can be checked against known-good behavior.

This regression is intentionally small. It does not add a new complex netlist
and does not modify MAGICAL core source, Anaroute, device generation,
`examples/mockPDK`, or `examples/sky130PDK`.

## Files

Registry:

```text
tools/sky130_adapter/sky130_case_registry.yaml
```

Runner:

```text
tools/sky130_adapter/run_sky130_case_regression.sh
```

Summary collector:

```text
tools/sky130_adapter/collect_sky130_case_summaries.py
```

Regression output:

```text
generated/sky130_cases/regression_summary.md
```

## Current Cases

`inverter_core`:

- case directory: `examples/inverter_sky130_try`
- top cell: `inverter_core`
- power nets: `VPWR` / `VGND`
- xschem conversion: no
- output node estimate: `Y`

`ota_core`:

- case directory: `examples/ota_core_sky130_try`
- top cell: `ota_core`
- power nets: `VDD` / `GND`
- xschem conversion: yes
- output node estimate: `VOUT`

## Running Regression

```bash
tools/sky130_adapter/run_sky130_case_regression.sh
```

The runner reads the registry, invokes `run_sky130_case_pipeline.sh` once per
case, preserves each case directory under `generated/sky130_cases/<case>/`, and
then writes the aggregate markdown table.

If one case fails, the runner does not delete prior outputs. The final exit code
is nonzero if any case fails or if summary collection fails.

## Pass Criteria

A case is considered passing in the regression table when:

- `DRC_COUNT` is `0`;
- `CONNECTIVITY_LVS_MATCH` is `yes`.

The table also reports:

- raw Magic `.subckt` ports;
- anonymous extracted nodes;
- net renaming status;
- parasitic capacitor count;
- total listed capacitance.

For `ota_core`, `net1` and `net2` must not appear in `RAW_SUBCKT_PORTS`; they
are internal routed nets, not top-level ports.

## LVS and PEX Roles

Regression LVS is connectivity LVS. The preparation step removes parasitic
capacitors and selected MOS parasitic properties from the comparison netlists.
The raw Magic extraction is preserved separately, and `pex_summary.md` reports
parasitic capacitor statistics.

PEX now includes:

- total listed capacitance;
- per-node connected capacitor count;
- per-node summed connected capacitance;
- an output-node estimate when the registry declares `output_node`.

This is not parasitic-aware LVS. Passing this regression does not imply final
native Sky130 PDK adaptation or full DRC-clean signoff.

## Adding Another Case

Add a new block to:

```text
tools/sky130_adapter/sky130_case_registry.yaml
```

Recommended case layout:

```text
examples/<case_name>/
  <case_name>_raw.spice       # if xschem/ngspice input exists
  <top_cell>_magical.sp       # MAGICAL-readable netlist
  <top_cell>.json             # explicit vddNetNames/vssNetNames
generated/sky130_cases/<case_name>/
docs/sky130_adapter/<case_name>_trial.md
```

Keep the first new case small enough to diagnose quickly. Good next candidates
are a Sky130 diff pair, a current mirror, or a small comparator/preamp slice.
