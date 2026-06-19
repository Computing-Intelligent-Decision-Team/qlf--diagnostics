# Sky130 Pin Shape Postprocess

## Summary

- Input GDS: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/case/SMCNR_SE_2st_AMP.sky130.pinned.gds`
- Output GDS: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/case/SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds`
- ioPin file: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/case/SMCNR_SE_2st_AMP.ioPin`
- Target cell: `SMCNR_SE_2st_AMP_flat`
- Top-port filtering: enabled
- Added pin-purpose BOUNDARY elements: 6
- Existing drawing geometry, old TEXT, and new label TEXT are preserved.
- This is an experimental postprocess, not final native Sky130 export.

## Top-Port Filter

- Netlist: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/case/SMCNR_SE_2st_AMP_cand_0031.sp`
- Top cell: `SMCNR_SE_2st_AMP`
- Top ports: vdda, gnda, vin, vip, ibias, vout
- Processed pins: vdda, gnda, vin, vip, ibias, vout
- Skipped internal nets: outp, outn, net53, net027

| skipped net | skipped reason |
| --- | --- |
| outp | not in top subckt port list |
| outn | not in top subckt port list |
| net53 | not in top subckt port list |
| net027 | not in top subckt port list |

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
| vdda | 6 | (1900, 35550) - (32900, 37350) | met5.pin | 72 | 16 | met5.drawing 72/20 | met5.label 72/5 |
| gnda | 6 | (1900, -3700) - (32900, -1900) | met5.pin | 72 | 16 | met5.drawing 72/20 | met5.label 72/5 |
| vin | 1 | (18350, 10550) - (26850, 10650) | li1.pin | 67 | 16 | li1.drawing 67/20 | li1.label 67/5 |
| vip | 1 | (7950, 10550) - (16450, 10650) | li1.pin | 67 | 16 | li1.drawing 67/20 | li1.label 67/5 |
| ibias | 1 | (-50, 12550) - (10250, 12650) | li1.pin | 67 | 16 | li1.drawing 67/20 | li1.label 67/5 |
| vout | 1 | (13350, 13950) - (13450, 15450) | li1.pin | 67 | 16 | li1.drawing 67/20 | li1.label 67/5 |

## Notes

- Pin shape boxes are copied directly from `inverter_core.ioPin`.
- The output GDS keeps the existing `131/0` and `136/0` TEXT labels and the Sky130 label-purpose TEXT labels from the previous postprocess.
- This experiment tests whether Magic extraction needs both label TEXT and pin-purpose geometry to preserve top-level port names.
