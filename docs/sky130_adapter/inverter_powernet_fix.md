# Sky130 Inverter Power-Net Fix

## 1. Problem Background

The baseline Sky130 inverter netlist uses the expected MOS terminal order:

```spice
M0 (Y A VGND VGND) sky130_fd_pr__nfet_01v8 l=150n w=1u multi=1 nf=1
M1 (Y A VPWR VPWR) sky130_fd_pr__pfet_01v8 l=150n w=2u multi=1 nf=1
```

Earlier Magic raw extraction from the pinned-shapes GDS produced an anonymous
NMOS source node:

```spice
X0 Y A a_n15_90# VGND sky130_fd_pr__nfet_01v8 ...
```

This showed that the cell ports and pin labels were usable, but the NMOS source
was not physically merged into `VGND` in the raw extracted netlist.

## 2. Control Experiment Results

| Experiment | Change | Raw NMOS extraction | Anonymous node | Result |
| --- | --- | --- | --- | --- |
| baseline pinned_shapes | `M0 (Y A VGND VGND)`, no VPWR/VGND power config | `X0 Y A a_n15_90# VGND ...nfet...` | yes | failing raw extraction |
| terminal-swap only | `M0 (VGND A Y VGND)`, no power config | `X0 a_415_90# A Y VGND ...nfet...` | yes | not a fix |
| power-net only | original `M0 (Y A VGND VGND)`, add VPWR/VGND power config | `X1 Y A VGND VGND ...nfet...` | no | correct direction |
| terminal-swap + powernets | terminal-swapped netlist plus power config | `X1 VGND A Y VGND ...nfet...` | no | clean but wrong inverter direction |

The correct fix direction is therefore power-net recognition, not terminal
swapping.

## 3. Applied Baseline Config Change

Updated baseline configuration:

- `examples/inverter_sky130_try/inverter.json`
- `examples/inverter_sky130_try/run_with_trial_sky130PDK.sh`

Both now explicitly set:

```json
"vddNetNames" : ["VPWR"],
"vssNetNames" : ["VGND"]
```

This keeps the MOS netlist unchanged and makes MAGICAL recognize the Sky130
power names during placement/power-stripe generation.

## 4. Verification Pipeline

Added:

```bash
tools/sky130_adapter/run_inverter_sky130_powernet_pipeline.sh
```

This enhanced baseline pipeline runs:

1. MAGICAL placement/routing in Docker using `run_with_trial_sky130PDK.sh`.
2. GDS remap to Sky130 layers.
3. Sky130 pin label postprocess.
4. Sky130 pin shape postprocess.
5. Magic DRC on the pinned-shapes GDS.
6. Magic extraction on the pinned-shapes GDS.
7. Netgen LVS using the existing normalization script.
8. Raw extraction checks.

## 5. Raw Extraction After Fix

Output:

```text
generated/sky130_powernet_pipeline/inverter/inverter_core_extracted.spice
```

Raw Magic extraction now contains:

```spice
.subckt inverter_core_flat A Y VPWR VGND
X0 Y A VPWR VPWR sky130_fd_pr__pfet_01v8 ad=0.4 pd=4.4 as=0.4 ps=4.4 w=2 l=0.15
X1 Y A VGND VGND sky130_fd_pr__nfet_01v8 ad=0.2 pd=2.4 as=0.2 ps=2.4 w=1 l=0.15
```

There are no anonymous `a_*#` or `w_*#` source/drain nodes in the raw MOS
connectivity.

## 6. DRC and LVS Results

Latest enhanced pipeline summary:

```text
generated/sky130_powernet_pipeline/inverter/summary.md
```

Observed results:

| Check | Result |
| --- | --- |
| VPWR recognized as VDD | yes |
| VGND recognized as VSS | yes |
| Raw NMOS | `X1 Y A VGND VGND ...nfet...` |
| Anonymous extracted nodes | none |
| Magic DRC error count | 0 |
| Netgen LVS match after normalization | yes |

Netgen report contains:

```text
Circuits match uniquely.
Netlists match uniquely.
```

## 7. Normalization Status

Keep:

```text
tools/sky130_adapter/normalize_lvs_netlists_inverter.py
```

Even though the raw net names are now clean for the power-net-fixed baseline,
normalization is still used for connectivity LVS because Magic extraction still
adds:

- parasitic capacitor lines;
- layout-derived MOS properties such as `ad`, `as`, `pd`, and `ps`.

For the power-net-fixed baseline, the `NET_RENAMES` entry
`a_n15_90# -> VGND` should no longer be needed in theory, but keeping it is
harmless for the current inverter-specific LVS wrapper.

PEX-oriented flows should not remove parasitics or layout-derived properties.
This normalization remains a temporary connectivity-LVS helper.

## 8. Next Step

The next small fix should be to make Sky130 adapter configuration generation
emit the appropriate default power net names:

```json
"vddNetNames" : ["VPWR"],
"vssNetNames" : ["VGND"]
```

Do this in the Sky130 adapter config/generation layer rather than changing
MAGICAL's global default `VDD/GND` behavior.
