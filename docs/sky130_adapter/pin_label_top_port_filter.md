# Sky130 Pin Top-Port Filter

## Problem

MAGICAL `ioPin` can contain more than the external subckt interface. In the OTA
trial, `ota_core.ioPin` listed both true top ports and routed internal nets:

```text
VINP VINM IB VDD VOUT GND net1 net2
```

The previous Sky130 postprocess treated every `ioPin` entry as a Sky130 pin by
adding both label-purpose TEXT and pin-purpose geometry. Magic extraction then
promoted every one of those names into the raw extracted subckt interface:

```spice
.subckt ota_core_flat VINP VINM IB VDD VOUT GND net1 net2
```

That is not the intended top-level interface. `net1` and `net2` are internal
routed nets from the source OTA, not module ports.

## Filter Logic

The pin label and pin shape postprocess scripts now accept:

```text
--netlist <path>
--top-cell <cell_name>
--only-top-ports
```

When `--only-top-ports` is set, the scripts parse the requested top cell from a
source netlist and use that subckt port list as the allowed pin set. Both
SPICE-style `.subckt ota_core ...` and MAGICAL-style `subckt ota_core ...` are
accepted.

Entries in `ioPin` whose names are not in the top subckt port list are skipped
and reported as internal nets with reason `not in top subckt port list`.

If `--only-top-ports` is not set, the old behavior is preserved and the scripts
print/report a warning that all `ioPin` entries will be treated as pins.

## OTA Result

Pipeline:

```bash
tools/sky130_adapter/run_ota_core_sky130_pipeline.sh
```

The OTA pipeline now passes:

```text
--netlist examples/ota_core_sky130_try/ota_core_magical.sp
--top-cell ota_core
--only-top-ports
```

The postprocess reports show:

```text
Top ports: VINP, VINM, IB, VDD, VOUT, GND
Processed pins: VINP, VINM, IB, VDD, VOUT, GND
Skipped internal nets: net1, net2
```

Raw extraction after filtering:

```spice
.subckt ota_core_flat VINP VINM IB VDD VOUT GND
```

`net1` and `net2` no longer appear as top-level ports. Because their Sky130 pin
labels and pin-purpose shapes are no longer emitted, Magic names the same
internal connectivity with anonymous extracted node names in the raw netlist:

```spice
X2 a_25_264# VINP a_425_364# GND sky130_fd_pr__nfet_01v8 ...
```

This is acceptable for the current connectivity LVS flow, which does not rely on
internal source net names matching Magic's raw internal node names.

## Verification

OTA pipeline summary:

```text
Raw subckt: .subckt ota_core_flat VINP VINM IB VDD VOUT GND
Magic DRC error count: 0
Connectivity LVS status: yes
Netgen exit status: 0
PEX summary status: generated
Parasitic capacitor count: 25
Total listed capacitance: 8.23638 fF
```

Inverter regression:

```bash
tools/sky130_adapter/run_inverter_sky130_powernet_pipeline.sh
```

Summary:

```text
Raw subckt: .subckt inverter_core_flat A Y VPWR VGND
Anonymous extracted nodes: none
Magic DRC error count: 0
Connectivity LVS status: yes
Net renaming used: no
Parasitic capacitor count: 6
```

## Notes for Larger Blocks

For diff pairs, OTA variants, comparators, and other multi-net examples, use the
original top subckt declaration as the source of truth for external pins. Do not
infer top-level ports from `ioPin` alone, because `ioPin` may include routed
internal nets that MAGICAL exposed for routing or bookkeeping.

This filter only fixes which names become Sky130 pins in the postprocessed GDS.
It is not a claim that the full Sky130 PDK adaptation is complete, and it does
not make layer/datatype remapping equivalent to DRC-clean native Sky130 layout.
