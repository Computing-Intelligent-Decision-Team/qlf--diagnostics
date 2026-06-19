# Sky130 Pin Label Postprocess

## Summary

- Input GDS: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection_case/SMCNR_SE_2st_AMP.sky130.gds`
- Output GDS: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection_case/SMCNR_SE_2st_AMP.sky130.pinned.gds`
- ioPin file: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection_case/SMCNR_SE_2st_AMP.ioPin`
- Target cell: `SMCNR_SE_2st_AMP_flat`
- Top-port filtering: enabled
- Added TEXT labels: 6
- Existing geometry and existing TEXT records are preserved.
- This is a non-destructive experimental postprocess, not final native Sky130 export.

## Top-Port Filter

- Netlist: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection_case/SMCNR_SE_2st_AMP_mos_only.sp`
- Top cell: `SMCNR_SE_2st_AMP`
- Top ports: vdda, gnda, vin, vip, ibias, vout
- Processed pins: vdda, gnda, vin, vip, ibias, vout
- Skipped internal nets: outp, outn, net53

| skipped net | skipped reason |
| --- | --- |
| outp | not in top subckt port list |
| outn | not in top subckt port list |
| net53 | not in top subckt port list |

## Added Labels

| pin | ioPin layer | ioPin box | label center | Sky130 label purpose | GDS layer | texttype |
| --- | ---: | --- | --- | --- | ---: | ---: |
| vdda | 6 | (3900, 16175) - (38500, 17975) | (21200, 17075) | met5.label | 72 | 5 |
| gnda | 6 | (3900, -3700) - (38500, -1900) | (21200, -2800) | met5.label | 72 | 5 |
| vin | 1 | (22150, 10550) - (30650, 10650) | (26400, 10600) | li1.label | 67 | 5 |
| vip | 1 | (11750, 10550) - (20250, 10650) | (16000, 10600) | li1.label | 67 | 5 |
| ibias | 1 | (3950, 14550) - (14250, 14650) | (9100, 14600) | li1.label | 67 | 5 |
| vout | 1 | (11550, 3950) - (11650, 11650) | (11600, 7800) | li1.label | 67 | 5 |

## Notes

- ioPin layer 1 is mapped to `li1.label` `67/5`.
- ioPin layer 2 is mapped to `met1.label` `68/5`.
- ioPin layer 6 is mapped to `met5.label` `72/5`.
- The older MAGICAL TEXT records on `131/0` and `136/0` are intentionally retained for comparison.
- If Magic still extracts anonymous internal node names, the next check is whether Magic expects pin shapes in addition to labels.
