# Sky130 OTA Core Pipeline Trial

## 1. Goal

This trial checks whether the current Sky130 bridge flow can move beyond the
inverter case and run a five-transistor OTA core through:

1. xschem/ngspice netlist conversion;
2. MAGICAL placement/routing using `generated/sky130PDK_trial`;
3. GDS layer remap;
4. Sky130 pin label and pin shape post-processing;
5. Magic DRC;
6. Magic extraction;
7. connectivity LVS;
8. PEX summary.

The trial does not modify the inverter baseline, MAGICAL core source,
`examples/mockPDK`, or `examples/sky130PDK`.

## 2. Input and Converted Netlist

Raw xschem input:

```text
examples/ota_core_sky130_try/ota_core_raw.spice
```

Converted MAGICAL netlist:

```text
examples/ota_core_sky130_try/ota_core_magical.sp
```

The converter restores the commented xschem subckt and emits MAGICAL-readable
MOS lines:

```spice
subckt ota_core VINP VINM IB VDD VOUT GND
M6 (net1 VINP net2 GND) sky130_fd_pr__nfet_01v8 l=150n w=1.26u multi=1 nf=2
M7 (VOUT net1 VDD VDD) sky130_fd_pr__pfet_01v8 l=150n w=1.26u multi=1 nf=2
M8 (net1 net1 VDD VDD) sky130_fd_pr__pfet_01v8 l=150n w=1.26u multi=1 nf=2
M2 (VOUT VINM net2 GND) sky130_fd_pr__nfet_01v8 l=150n w=1.26u multi=1 nf=2
M1 (net2 IB GND GND) sky130_fd_pr__nfet_01v8 l=150n w=1.26u multi=1 nf=2
ends ota_core
```

## 3. Conversion Policy

The xschem/ngspice parameters `ad`, `as`, `pd`, `ps`, `nrd`, `nrs`, `sa`, `sb`,
and `sd` are removed because they are simulator geometry/parasitic expressions,
not part of the current MAGICAL device-generation input. The converter keeps:

- Sky130 model names;
- D/G/S/B order;
- `l`;
- `w`;
- `nf`;
- `multi`.

The raw netlist declares `.GLOBAL GND`. The converter appends `GND` to the
subckt port list via `--global-port GND` so Magic extraction and Netgen can
compare a fully explicit source circuit.

## 4. Pipeline Command

```bash
tools/sky130_adapter/run_ota_core_sky130_pipeline.sh
```

The summary is written to:

```text
generated/sky130_ota_core_pipeline/summary.md
```

## 5. MAGICAL and ioPin Result

MAGICAL placement/routing completed.

The generated ioPin file contains the expected external ports:

```text
VINP
VINM
IB
VDD
VOUT
GND
```

It also contains internal nets:

```text
net1
net2
```

Those internal net pins are the main new observation in this trial.

## 6. GDS Remap and Magic DRC

The pipeline generated:

```text
examples/ota_core_sky130_try/ota_core.sky130.pinned_shapes.gds
```

Magic DRC completed with:

```text
Total DRC errors found: 0
```

This remains a trial result using the current Sky130 remap and post-processing
flow; it is not a claim that the full MAGICAL Sky130 adapter is complete.

## 7. Raw Magic Extraction

Raw extracted netlist:

```text
generated/sky130_ota_core_pipeline/ota_core_extracted.raw.spice
```

Before the top-port filter, raw extraction produced:

```spice
.subckt ota_core_flat VINP VINM IB VDD VOUT GND net1 net2
```

After updating the Sky130 pin label and pin shape postprocess to use
`--only-top-ports`, raw extraction now produces:

```spice
.subckt ota_core_flat VINP VINM IB VDD VOUT GND
```

The postprocess reads the allowed pins from:

```text
examples/ota_core_sky130_try/ota_core_magical.sp
```

with top cell `ota_core`. It processes only:

```text
VINP VINM IB VDD VOUT GND
```

and skips:

```text
net1 net2
```

with reason `not in top subckt port list`.

`net1` and `net2` no longer appear in the raw subckt port list. Since they no
longer receive Sky130 pin labels or pin-purpose shapes, Magic assigns anonymous
internal names such as `a_25_264#` and `a_425_364#` in the raw extracted device
connections. Connectivity LVS still passes without net renaming, so this is a
raw naming difference rather than a connectivity failure.

Raw extracted MOS count is 10 because each `nf=2` source MOS is extracted as
two unit/finger devices. Netgen recognizes the connectivity equivalence against
the five-device source.

## 8. Connectivity LVS

Connectivity LVS uses the layered preparation flow:

```text
generated/sky130_ota_core_pipeline/ota_core_source.connectivity.spice
generated/sky130_ota_core_pipeline/ota_core_extracted.connectivity.spice
```

LVS result:

```text
Circuits match uniquely.
Netlists match uniquely.
```

The structured summary reports:

| Metric | Source | Extracted |
| --- | ---: | ---: |
| Devices | 5 | 5 |
| Nets | 8 | 8 |

No net rename was used.

## 9. PEX Summary

PEX summary:

```text
generated/sky130_ota_core_pipeline/pex_summary.md
```

Observed parasitics:

| Item | Value |
| --- | ---: |
| Parasitic capacitor count | 25 |
| Total listed capacitance | 8.23638 fF |

The largest listed capacitor is between `VDD` and `GND`.

## 10. Top-Port Filter Result

The current flow generalizes through DRC, extraction, connectivity LVS, and PEX
summary while keeping the raw Magic subckt interface limited to true OTA ports:

```text
Raw subckt: .subckt ota_core_flat VINP VINM IB VDD VOUT GND
Magic DRC error count: 0
Connectivity LVS status: yes
Netgen exit status: 0
PEX summary status: generated
Parasitic capacitor count: 25
Total listed capacitance: 8.23638 fF
```

The detailed method is documented in:

```text
docs/sky130_adapter/pin_label_top_port_filter.md
```

For larger circuits, continue using the original top-level subckt port list as
the allowed pin set before adding Sky130 label-purpose TEXT and pin-purpose
geometry. Do not infer top-level ports from `ioPin` alone.
