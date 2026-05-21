# Sky130 Current Mirror Pipeline Trial

## Goal

This case adds a small `current_mirror_core` regression target on top of the
already passing `inverter_core` and `ota_core` cases. It checks whether the
generic Sky130 case pipeline handles:

- diode-connected MOS connectivity;
- a mirror branch;
- explicit `VDD` / `GND` power-net configuration;
- the internal node `NREF`;
- top-port filtering;
- Magic DRC, Netgen connectivity LVS, and PEX summary.

This trial does not modify MAGICAL core source, Anaroute, device generation,
`examples/mockPDK`, or `examples/sky130PDK`.

## Case Files

Case directory:

```text
examples/current_mirror_sky130_try/
```

MAGICAL netlist:

```text
examples/current_mirror_sky130_try/current_mirror_magical.sp
```

MAGICAL requires `subckt` / `ends` syntax for this input path. The topology is:

```spice
subckt current_mirror_core IBIAS IOUT VDD GND
M0 (NREF NREF GND GND) sky130_fd_pr__nfet_01v8 l=150n w=1.26u multi=1 nf=2
M1 (IOUT NREF GND GND) sky130_fd_pr__nfet_01v8 l=150n w=1.26u multi=1 nf=2
M2 (NREF IBIAS VDD VDD) sky130_fd_pr__pfet_01v8 l=150n w=1.26u multi=1 nf=2
M3 (IOUT IBIAS VDD VDD) sky130_fd_pr__pfet_01v8 l=150n w=1.26u multi=1 nf=2
ends current_mirror_core
```

Config:

```text
examples/current_mirror_sky130_try/current_mirror.json
```

The config points at `generated/sky130PDK_trial` and explicitly sets:

```json
"vddNetNames" : ["VDD"],
"vssNetNames" : ["GND"]
```

## Standalone Pipeline

Command:

```bash
tools/sky130_adapter/run_sky130_case_pipeline.sh \
  --case-dir examples/current_mirror_sky130_try \
  --case-name current_mirror_core \
  --top-cell current_mirror_core \
  --magical-netlist current_mirror_magical.sp \
  --config current_mirror.json \
  --vdd VDD \
  --vss GND \
  --out-dir generated/sky130_cases/current_mirror_core \
  --convert-xschem no \
  --output-node IOUT
```

Summary:

```text
generated/sky130_cases/current_mirror_core/summary.md
```

Observed result:

```text
MAGICAL_RESULT = pass
DRC_COUNT = 0
RAW_SUBCKT_PORTS = IBIAS IOUT VDD GND
ANONYMOUS_NODES = a_n15_4#
CONNECTIVITY_LVS_MATCH = yes
NET_RENAMES_USED = no
PEX_CAPS = 10
PEX_TOTAL_CAP_FF = 6.79648 fF
```

## Top-Port Filtering

The `ioPin` postprocess saw:

```text
Top ports: IBIAS, IOUT, VDD, GND
Processed pins: IBIAS, IOUT, VDD, GND
Skipped internal nets: NREF
```

`NREF` was not promoted to the raw Magic `.subckt` port list. Magic names the
same internal connectivity as `a_n15_4#` in raw extraction:

```spice
.subckt current_mirror_core_flat IBIAS IOUT VDD GND
X0 a_n15_4# a_n15_4# GND GND sky130_fd_pr__nfet_01v8 ...
X1 IOUT a_n15_4# GND GND sky130_fd_pr__nfet_01v8 ...
```

This anonymous node corresponds to the internal reference/mirror node, not to a
lost top-level power/source connection.

## PEX Summary

PEX summary:

```text
generated/sky130_cases/current_mirror_core/pex_summary.md
```

The output node estimate for `IOUT` is:

```text
IOUT: 4 connected capacitors, 0.95334 fF summed connected capacitance
```

The raw PEX data is preserved separately from the connectivity LVS netlists.

## Regression

The case is now registered in:

```text
tools/sky130_adapter/sky130_case_registry.yaml
```

Full regression:

```bash
tools/sky130_adapter/run_sky130_case_regression.sh
```

Current result:

```text
inverter_core: PASS
ota_core: PASS
current_mirror_core: PASS
failed=none
```

The aggregate summary is:

```text
generated/sky130_cases/regression_summary.md
```

## Limits

This is still connectivity LVS, not parasitic-aware LVS. The case improves
coverage of diode-connected and mirror-branch connectivity, but it is not a
claim that the Sky130 adapter is complete or that layer remapping alone is
equivalent to final Sky130 signoff.
