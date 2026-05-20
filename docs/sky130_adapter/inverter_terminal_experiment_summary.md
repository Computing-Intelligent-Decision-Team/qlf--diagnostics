# Inverter Terminal Experiment Summary

## Cases

| Case | NMOS netlist | VPWR/VGND power recognition | Anaroute isPower | raw .subckt ports | raw NMOS extraction | anonymous internal nodes | normalized LVS | conclusion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline pinned_shapes | `M0 (Y A VGND VGND)` | no / no | False / False | `.subckt inverter_core_flat A Y VPWR VGND` | `X0 Y A a_n15_90# VGND sky130_fd_pr__nfet_01v8 ad=0.2 pd=2.4 as=0.2 ps=2.4 w=1 l=0.15` | yes: a_n15_90# | yes | baseline issue |
| terminal-swap only | `M0 (VGND A Y VGND)` | no / no | False / False | `.subckt inverter_core_flat A Y VPWR VGND` | `X0 a_415_90# A Y VGND sky130_fd_pr__nfet_01v8 ad=0.2 pd=2.4 as=0.2 ps=2.4 w=1 l=0.15` | yes: a_415_90# | no | terminal swap changes anonymous node but does not clean raw extraction |
| power-net only | `M0 (Y A VGND VGND)` | yes / yes | False / False | `.subckt inverter_core_flat A Y VPWR VGND` | `X1 Y A VGND VGND sky130_fd_pr__nfet_01v8 ad=0.2 pd=2.4 as=0.2 ps=2.4 w=1 l=0.15` | no: none | yes | power-net recognition fixes raw NFET connectivity in this trial |
| combined optional | `M0 (VGND A Y VGND)` | yes / yes | False / False | `.subckt inverter_core_flat A Y VPWR VGND` | `X1 VGND A Y VGND sky130_fd_pr__nfet_01v8 ad=0.2 pd=2.4 as=0.2 ps=2.4 w=1 l=0.15` | no: none | yes | run because one single-variable experiment improved raw extraction |

## Reports

- Terminal-swap report: `docs/sky130_adapter/terminal_swap_experiment.md`
- Power-net report: `docs/sky130_adapter/powernet_recognition_experiment.md`
- Combined report: `docs/sky130_adapter/terminal_swap_powernet_combined_experiment.md`

## Interpretation

- Terminal swap did not clean raw extraction; it replaced `a_n15_90#` with another anonymous node in this run, so D/S order alone is not sufficient.
- Power-net JSON fields are effective at the MAGICAL/placer level: VPWR and VGND generate power stripes.
- In these tiny inverter runs, Anaroute `isPower` remains False because PnR passes `net.isPower() and not self.isSmallModule`; power recognition is still visible through power-stripe generation.
- Power-net recognition removed anonymous internal NMOS terminal nodes; next fix should focus on Sky130 adapter power-net configuration.
- Keep `normalize_lvs_netlists_inverter.py` until raw Magic extraction no longer contains anonymous internal NMOS terminal nodes.
