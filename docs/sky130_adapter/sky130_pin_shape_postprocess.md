# Sky130 Pin Shape Postprocess

## Summary

- Input GDS: `examples/inverter_sky130_try/inverter_core.sky130.pinned.gds`
- Output GDS: `examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds`
- ioPin file: `examples/inverter_sky130_try/inverter_core.ioPin`
- Target cell: `inverter_core_flat`
- Added pin-purpose BOUNDARY elements: 4
- Existing drawing geometry, old TEXT, and new label TEXT are preserved.
- This is an experimental postprocess, not final native Sky130 export.

## Local PDK Datatype Confirmation

| purpose | GDS layer/datatype | source |
| --- | --- | --- |
| li1.label | 67/5 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |
| li1.pin | 67/16 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |
| met1.label | 68/5 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |
| met1.pin | 68/16 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |
| met5.label | 72/5 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |
| met5.pin | 72/16 | KLayout `sky130A.lyp`, `sky130A.map`; Magic `sky130A.tech` |

Checked PDK files:
- `libs.tech/klayout/tech/sky130A.lyp`
- `libs.tech/klayout/tech/sky130A.map`
- `libs.tech/magic/sky130A.tech`
- `libs.tech/magic/sky130A-GDS.tech`

## Added Pin Shapes

| pin | ioPin layer | box | Sky130 pin purpose | GDS layer | datatype | expected drawing layer | expected label layer |
| --- | ---: | --- | --- | ---: | ---: | --- | --- |
| A | 1 | (350, 2150) - (1850, 2250) | li1.pin | 67 | 16 | li1.drawing 67/20 | li1.label 67/5 |
| Y | 2 | (350, 550) - (2250, 650) | met1.pin | 68 | 16 | met1.drawing 68/20 | met1.label 68/5 |
| VPWR | 6 | (1350, -450) - (2650, -350) | met5.pin | 72 | 16 | met5.drawing 72/20 | met5.label 72/5 |
| VGND | 6 | (-650, -1050) - (3250, -950) | met5.pin | 72 | 16 | met5.drawing 72/20 | met5.label 72/5 |

## Notes

- Pin shape boxes are copied directly from `inverter_core.ioPin`.
- The output GDS keeps the existing `131/0` and `136/0` TEXT labels and the Sky130 label-purpose TEXT labels from the previous postprocess.
- This experiment tests whether Magic extraction needs both label TEXT and pin-purpose geometry to preserve top-level port names.
