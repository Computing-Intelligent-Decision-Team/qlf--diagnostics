# Sky130 Pin Label Postprocess

## Summary

- Input GDS: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/case/SMCNR_SE_2st_AMP.sky130.gds`
- Output GDS: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/case/SMCNR_SE_2st_AMP.sky130.pinned.gds`
- ioPin file: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/case/SMCNR_SE_2st_AMP.ioPin`
- Target cell: `SMCNR_SE_2st_AMP_flat`
- Top-port filtering: enabled
- Added TEXT labels: 6
- Existing geometry and existing TEXT records are preserved.
- This is a non-destructive experimental postprocess, not final native Sky130 export.

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

## Added Labels

| pin | ioPin layer | ioPin box | label center | Sky130 label purpose | GDS layer | texttype |
| --- | ---: | --- | --- | --- | ---: | ---: |
| vdda | 6 | (1900, 35550) - (32900, 37350) | (17400, 36450) | met5.label | 72 | 5 |
| gnda | 6 | (1900, -3700) - (32900, -1900) | (17400, -2800) | met5.label | 72 | 5 |
| vin | 1 | (18350, 10550) - (26850, 10650) | (22600, 10600) | li1.label | 67 | 5 |
| vip | 1 | (7950, 10550) - (16450, 10650) | (12200, 10600) | li1.label | 67 | 5 |
| ibias | 1 | (-50, 12550) - (10250, 12650) | (5100, 12600) | li1.label | 67 | 5 |
| vout | 1 | (13350, 13950) - (13450, 15450) | (13400, 14700) | li1.label | 67 | 5 |

## Notes

- ioPin layer 1 is mapped to `li1.label` `67/5`.
- ioPin layer 2 is mapped to `met1.label` `68/5`.
- ioPin layer 6 is mapped to `met5.label` `72/5`.
- The older MAGICAL TEXT records on `131/0` and `136/0` are intentionally retained for comparison.
- If Magic still extracts anonymous internal node names, the next check is whether Magic expects pin shapes in addition to labels.
