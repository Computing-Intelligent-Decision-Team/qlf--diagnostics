# NMOS Terminal Mapping Diagnosis

## Inputs

- GDS: `examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds`
- Raw extracted netlist: `generated/sky130_lvs_pinned_shapes/inverter_core_extracted_pinned_shapes.spice`
- Previous connectivity report: `docs/sky130_adapter/gds_connectivity_diagnosis.md`
- ioPin file: `examples/inverter_sky130_try/inverter_core.ioPin`
- Debug GDS: `examples/inverter_sky130_try/inverter_core.nmos_terminal_debug.gds`

## Raw Magic NMOS Interpretation

- `.subckt`: `.subckt inverter_core_flat A Y VPWR VGND`
- NMOS line: `X0 Y A a_n15_90# VGND sky130_fd_pr__nfet_01v8 ad=0.2 pd=2.4 as=0.2 ps=2.4 w=1 l=0.15`
- D-like terminal: `Y`
- G terminal: `A`
- S-like terminal: `a_n15_90#`
- B terminal: `VGND`

## Located NMOS Device

- Device diff bbox: `(-75, 450) - (475, 1450)`
- Gate poly bbox: `(125, 350) - (275, 1550)`
- Left terminal bbox: `(-75, 450) - (125, 1450)`
- Right terminal bbox: `(275, 450) - (475, 1450)`
- Source node coordinate hint: raw `(-15, 90)`, GDS `(-75, 450)`

## Terminal Component Summary

| terminal | bbox | seed licon1 count | component roots | layer contents | pin-purpose overlaps | met5 present |
| --- | --- | ---: | --- | --- | --- | --- |
| left | (-75, 450) - (125, 1450) | 6 | 171 | li1.drawing=3, licon1.drawing=6, mcon.drawing=2, met1.drawing=3, met2.drawing=3, via.drawing=4 | none | no |
| right | (275, 450) - (475, 1450) | 6 | 179 | li1.drawing=6, licon1.drawing=19, mcon.drawing=4, met1.drawing=3, met1.pin=1 | Y: met1.pin (350, 550) - (2250, 650) | no |

## Terminal Seed Contacts

| terminal | licon1 contact boxes |
| --- | --- |
| left | (-25, 510) - (25, 560); (-25, 675) - (25, 725); (-25, 840) - (25, 890); (-25, 1005) - (25, 1055); (-25, 1170) - (25, 1220); (-25, 1335) - (25, 1385) |
| right | (375, 510) - (425, 560); (375, 675) - (425, 725); (375, 840) - (425, 890); (375, 1005) - (425, 1055); (375, 1170) - (425, 1220); (375, 1335) - (425, 1385) |

## Diagnosis

- Terminal connected to Y: `right`
- Terminal associated with `a_n15_90#`: `left`
- VGND pin-purpose geometry overlaps an NMOS terminal component: no
- Current classification: **actual routing connectivity or terminal association issue**.
- Reason: Y terminal side: right; `a_n15_90#` terminal side: left; VGND terminal side: none. Magic's S-like terminal is `a_n15_90#`, associated here with the left terminal, but neither NMOS terminal component overlaps the VGND pin-purpose geometry.

The NMOS source/drain terminals identified around the gate do not overlap the VGND pin-purpose component. This points away from Magic terminal ordering as the main issue and toward MAGICAL routing or terminal association: the device terminal that should be tied to VGND is currently left as an independent routed component.

## Next Minimum Step

Trace how MAGICAL assigns the NMOS source/drain pins from the device generator into the router. The smallest likely fix is to align the NMOS terminal pin association so the terminal Magic extracts as `a_n15_90#` is routed to `VGND`, or to swap/normalize source-drain pin mapping before routing if MAGICAL and Magic disagree on terminal orientation.

Keep `normalize_lvs_netlists_inverter.py` for now. It is still required because raw extraction keeps `a_n15_90#`.
