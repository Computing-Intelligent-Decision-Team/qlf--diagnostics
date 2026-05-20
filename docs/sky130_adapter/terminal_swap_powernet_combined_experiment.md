# terminal-swap powernets Experiment

## Inputs

- Case directory: `examples/inverter_sky130_try_terminal_swap_powernets`
- Netlist variant: `terminal_swap`
- Power mode: `vpwr_vgnd`
- NMOS line: `M0 (VGND A Y VGND) sky130_fd_pr__nfet_01v8 l=150n w=1u multi=1 nf=1`

## Outputs

- MAGICAL log: `/home/to/eda/tools/src/MAGICAL/generated/sky130_terminal_experiments/terminal-swap_powernets/magical_place_route.log`
- Remapped GDS: `examples/inverter_sky130_try_terminal_swap_powernets/inverter_core.sky130.gds`
- Pinned-shapes GDS: `examples/inverter_sky130_try_terminal_swap_powernets/inverter_core.sky130.pinned_shapes.gds`
- Magic extraction log: `/home/to/eda/tools/src/MAGICAL/generated/sky130_terminal_experiments/terminal-swap_powernets/magic_extract.log`
- Raw extracted netlist: `/home/to/eda/tools/src/MAGICAL/generated/sky130_terminal_experiments/terminal-swap_powernets/inverter_core_extracted.spice`
- Normalized extracted netlist: `/home/to/eda/tools/src/MAGICAL/generated/sky130_terminal_experiments/terminal-swap_powernets/inverter_core_extracted_normalized.spice`
- Netgen report: `/home/to/eda/tools/src/MAGICAL/generated/sky130_terminal_experiments/terminal-swap_powernets/netgen_lvs_report.out`

## Results

| item | value |
| --- | --- |
| VPWR isPower | False |
| VGND isPower | False |
| VPWR recognized as VDD for power stripe | yes |
| VGND recognized as VSS for power stripe | yes |
| raw .subckt | `.subckt inverter_core_flat A Y VPWR VGND` |
| raw NMOS extraction | `X1 VGND A Y VGND sky130_fd_pr__nfet_01v8 ad=0.2 pd=2.4 as=0.2 ps=2.4 w=1 l=0.15` |
| raw PMOS extraction | `X0 Y A VPWR VPWR sky130_fd_pr__pfet_01v8 ad=0.4 pd=4.4 as=0.4 ps=4.4 w=2 l=0.15` |
| a_n15_90# exists | no |
| anonymous internal nodes exist | no |
| anonymous internal nodes | none |
| normalized LVS match | yes |
| netgen exit status | 0 |

## Notes

- Raw extraction is the primary signal for this experiment.
- Normalized LVS still uses the existing inverter-specific normalizer and is reported separately.
