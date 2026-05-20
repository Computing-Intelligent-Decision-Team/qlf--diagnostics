# GDS Pin Shape Analysis

## Summary

- GDS: `examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds`
- ioPin file: `examples/inverter_sky130_try/inverter_core.ioPin`
- TEXT elements: 8
- BOUNDARY elements: 472

## Per-Pin Check

| pin | ioPin layer | ioPin box | expected Sky130 stack | label TEXT present | pin BOUNDARY present | drawing geometry present |
| --- | ---: | --- | --- | --- | --- | --- |
| A | 1 | (350, 2150) - (1850, 2250) | li1: drawing 67/20, label 67/5, pin 67/16 | yes | yes | yes |
| VGND | 6 | (-650, -1050) - (3250, -950) | met5: drawing 72/20, label 72/5, pin 72/16 | yes | yes | yes |
| VPWR | 6 | (1350, -450) - (2650, -350) | met5: drawing 72/20, label 72/5, pin 72/16 | yes | yes | yes |
| Y | 2 | (350, 550) - (2250, 650) | met1: drawing 68/20, label 68/5, pin 68/16 | yes | yes | yes |

## Matching Pin-Purpose Boundaries

| pin | expected pin layer/datatype | matching boundary boxes |
| --- | --- | --- |
| A | 67/16 | (350, 2150) - (1850, 2250) |
| VGND | 72/16 | (-650, -1050) - (3250, -950) |
| VPWR | 72/16 | (1350, -450) - (2650, -350) |
| Y | 68/16 | (350, 550) - (2250, 650) |

## Matching Label TEXT

| pin | expected label layer/texttype | matching labels |
| --- | --- | --- |
| A | 67/5 | A@(1100, 2200) |
| VGND | 72/5 | VGND@(1300, -1000) |
| VPWR | 72/5 | VPWR@(2000, -400) |
| Y | 68/5 | Y@(1300, 600) |

## Notes

- `label TEXT present` requires the Sky130 label layer/texttype and a coordinate inside the ioPin box.
- `pin BOUNDARY present` requires a Sky130 pin-purpose boundary overlapping the ioPin box.
- `drawing geometry present` checks for overlapping Sky130 drawing geometry on the same routing layer.
- This report is diagnostic only and does not modify the GDS.
