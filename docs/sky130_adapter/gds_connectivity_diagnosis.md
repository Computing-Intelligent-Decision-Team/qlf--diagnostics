# GDS Connectivity Diagnosis

## 1. Current Problem

The pinned-shapes GDS now has Sky130 label TEXT and pin-purpose BOUNDARY geometry for `A/Y/VPWR/VGND`. Magic extraction preserves the top-level port list, but the NMOS source terminal still appears as `a_n15_90#` instead of being merged into `VGND`.

This report checks geometry connectivity rather than adding more labels.

## 2. Inputs

- GDS: `examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds`
- Extracted netlist: `generated/sky130_lvs_pinned_shapes/inverter_core_extracted_pinned_shapes.spice`
- ioPin file: `examples/inverter_sky130_try/inverter_core.ioPin`
- Raw coordinate implied by `a_n15_90#`: `(-15, 90)`
- GDS coordinate used for search: `(-75, 450)` (`raw * 5`)
- Source search radius: `600` GDS units

## 3. Extracted Netlist Evidence

- `.subckt` line: `.subckt inverter_core_flat A Y VPWR VGND`
- NMOS line: `X0 Y A a_n15_90# VGND sky130_fd_pr__nfet_01v8 ad=0.2 pd=2.4 as=0.2 ps=2.4 w=1 l=0.15`
- NMOS source terminal: `a_n15_90#`
- `a_n15_90#` appears in extracted netlist: yes

## 4. Layer Counts Parsed From GDS

| purpose | count |
| --- | ---: |
| diff.drawing | 18 |
| li1.drawing | 37 |
| li1.pin | 1 |
| licon1.drawing | 146 |
| mcon.drawing | 36 |
| met1.drawing | 18 |
| met1.pin | 1 |
| met2.drawing | 15 |
| met3.drawing | 15 |
| met4.drawing | 15 |
| met5.drawing | 14 |
| met5.pin | 2 |
| poly.drawing | 6 |
| via.drawing | 34 |
| via2.drawing | 30 |
| via3.drawing | 32 |
| via4.drawing | 32 |

## 5. VGND Rail Check

- VGND ioPin box: `(-650, -1050) - (3250, -950)`
- VGND box overlaps `met5.drawing` or `met5.pin`: yes
- VGND rail component roots: `186`

### VGND Overlapping Elements

| layer | datatype | purpose | kind | bbox |
| ---: | ---: | --- | --- | --- |
| 72 | 20 | met5.drawing | drawing | (-525, -1050) - (3125, -950) |
| 72 | 20 | met5.drawing | drawing | (-650, -1050) - (-550, -950) |
| 72 | 20 | met5.drawing | drawing | (-650, -950) - (-550, -925) |
| 72 | 20 | met5.drawing | drawing | (-550, -1050) - (-525, -950) |
| 72 | 20 | met5.drawing | drawing | (3150, -1050) - (3250, -950) |
| 72 | 20 | met5.drawing | drawing | (3150, -950) - (3250, -925) |
| 72 | 20 | met5.drawing | drawing | (3125, -1050) - (3150, -950) |
| 72 | 20 | met5.drawing | drawing | (-650, -1050) - (-550, 450) |
| 72 | 16 | met5.pin | pin | (-650, -1050) - (3250, -950) |

### VGND Component `186`

- Element count: 292
- Layer contents: diff.drawing=8, li1.drawing=16, licon1.drawing=100, mcon.drawing=24, met1.drawing=7, met2.drawing=7, met3.drawing=10, met4.drawing=10, met5.drawing=9, met5.pin=1, via.drawing=24, via2.drawing=24, via3.drawing=26, via4.drawing=26

## 6. Source Node Neighborhood

- Source candidate elements selected near `(-75, 450)`: 2
- Source component root: `25`
- Source component element count: 147
- Source component layer contents: diff.drawing=10, li1.drawing=17, licon1.drawing=44, mcon.drawing=12, met1.drawing=11, met1.pin=1, met2.drawing=8, met3.drawing=5, met4.drawing=5, met5.drawing=5, met5.pin=1, via.drawing=10, via2.drawing=6, via3.drawing=6, via4.drawing=6
- Source component overlaps pin-purpose shapes for: VPWR: met5.pin (1350, -450) - (2650, -350); Y: met1.pin (350, 550) - (2250, 650)
- Source and VGND are in the same simplified component: no

### Source Candidate Diffusion Elements

| layer | datatype | purpose | kind | bbox |
| ---: | ---: | --- | --- | --- |
| 65 | 20 | diff.drawing | drawing | (-75, 450) - (475, 1450) |
| 65 | 20 | diff.drawing | drawing | (-675, -925) - (-525, 3125) |

### Source Candidate Component Summary

| candidate bbox | component root | same as VGND | component layers | pin-purpose overlaps |
| --- | ---: | --- | --- | --- |
| (-75, 450) - (475, 1450) | 25 | no | diff.drawing=10, li1.drawing=17, licon1.drawing=44, mcon.drawing=12, met1.drawing=11, met1.pin=1, met2.drawing=8, met3.drawing=5, met4.drawing=5, met5.drawing=5, met5.pin=1, via.drawing=10, via2.drawing=6, via3.drawing=6, via4.drawing=6 | VPWR: met5.pin (1350, -450) - (2650, -350); Y: met1.pin (350, 550) - (2250, 650) |
| (-675, -925) - (-525, 3125) | 186 | yes | diff.drawing=8, li1.drawing=16, licon1.drawing=100, mcon.drawing=24, met1.drawing=7, met2.drawing=7, met3.drawing=10, met4.drawing=10, met5.drawing=9, met5.pin=1, via.drawing=24, via2.drawing=24, via3.drawing=26, via4.drawing=26 | VGND: met5.pin (-650, -1050) - (3250, -950) |

### Nearest Stack Elements Around a_n15_90#

| layer | datatype | purpose | kind | bbox |
| ---: | ---: | --- | --- | --- |
| 65 | 20 | diff.drawing | drawing | (-75, 450) - (475, 1450) |
| 68 | 20 | met1.drawing | drawing | (-850, 350) - (50, 450) |
| 67 | 20 | li1.drawing | drawing | (-160, 350) - (160, 450) |
| 67 | 44 | mcon.drawing | contact | (-130, 350) - (-30, 450) |
| 68 | 20 | met1.drawing | drawing | (-160, 350) - (160, 450) |
| 67 | 20 | li1.drawing | drawing | (-50, 450) - (50, 1450) |
| 67 | 20 | li1.drawing | drawing | (-50, 350) - (50, 1450) |
| 66 | 44 | licon1.drawing | contact | (-25, 510) - (25, 560) |
| 67 | 44 | mcon.drawing | contact | (30, 350) - (130, 450) |
| 66 | 44 | licon1.drawing | contact | (-25, 675) - (25, 725) |
| 67 | 20 | li1.drawing | drawing | (240, 550) - (560, 650) |
| 68 | 20 | met1.drawing | drawing | (240, 550) - (560, 650) |
| 67 | 44 | mcon.drawing | contact | (270, 550) - (370, 650) |
| 71 | 20 | met4.drawing | drawing | (-760, 320) - (-440, 480) |
| 72 | 20 | met5.drawing | drawing | (-760, 320) - (-440, 480) |
| 69 | 20 | met2.drawing | drawing | (-760, 350) - (-440, 450) |

## 7. Source-to-VGND Stack Check

| transition | status |
| --- | --- |
| `diff.drawing -> licon1.drawing` | present in source component |
| `licon1.drawing -> li1.drawing` | present in source component |
| `li1.drawing -> mcon.drawing` | present in source component |
| `mcon.drawing -> met1.drawing` | present in source component |
| `met1.drawing -> via.drawing` | present in source component |
| `via.drawing -> met2.drawing` | present in source component |
| `met2.drawing -> via2.drawing` | present in source component |
| `via2.drawing -> met3.drawing` | present in source component |
| `met3.drawing -> via3.drawing` | present in source component |
| `via3.drawing -> met4.drawing` | present in source component |
| `met4.drawing -> via4.drawing` | present in source component |
| `via4.drawing -> met5.drawing` | present in source component |

## 8. Diagnosis

- Most likely break: `not a vertical layer-stack break; source candidate is a separate routed component from VGND`
- Current classification: **actual routing connectivity or device-terminal association issue**.

This is not primarily a pin annotation problem: the pinned-shapes GDS has labels and pin-purpose geometry, and Magic now writes the top-level port list. The remaining issue is that the source-side geometry component selected near `a_n15_90#` is not merged with the `VGND` rail component in the simplified GDS connectivity graph.

## 9. Next Minimum Step

Use Magic/KLayout visual probing around the NMOS source diffusion to confirm which physical diffusion terminal is connected to the `a_n15_90#` component. The simplified graph shows that this component has a complete vertical stack but is routed as a separate component from the VGND rail.

Keep `normalize_lvs_netlists_inverter.py` for now. It is still required because raw Magic extraction keeps `a_n15_90#`.
