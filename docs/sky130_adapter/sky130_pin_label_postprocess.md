# Sky130 Pin Label Postprocess

## Summary

- Input GDS: `generated/smcnr_variants/mc_pmos_l_0001/mc_second_stage_pmos_1p05/case/pinned.gds`
- Output GDS: `generated/smcnr_variants/mc_pmos_l_0001/mc_second_stage_pmos_1p05/case/pinned.gds`
- ioPin file: `generated/smcnr_variants/mc_pmos_l_0001/mc_second_stage_pmos_1p05/case/SMCNR_SE_2st_AMP.ioPin`
- Target cell: `inverter_core_flat`
- Top-port filtering: enabled
- Added TEXT labels: 6
- Existing geometry and existing TEXT records are preserved.
- This is a non-destructive experimental postprocess, not final native Sky130 export.

## Top-Port Filter

- Netlist: `generated/smcnr_variants/mc_pmos_l_0001/mc_second_stage_pmos_1p05/case/netlist.sp`
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
| vdda | 6 | (1900, 18775) - (32100, 20575) | (17000, 19675) | met5.label | 72 | 5 |
| gnda | 6 | (1900, -3700) - (32100, -1900) | (17000, -2800) | met5.label | 72 | 5 |
| vin | 1 | (17950, 10550) - (26450, 10650) | (22200, 10600) | li1.label | 67 | 5 |
| vip | 1 | (7550, 10550) - (16050, 10650) | (11800, 10600) | li1.label | 67 | 5 |
| ibias | 1 | (6550, 15150) - (17450, 15250) | (12000, 15200) | li1.label | 67 | 5 |
| vout | 1 | (10150, 13350) - (18050, 13450) | (14100, 13400) | li1.label | 67 | 5 |

## Notes

- ioPin layer 1 is mapped to `li1.label` `67/5`.
- ioPin layer 2 is mapped to `met1.label` `68/5`.
- ioPin layer 3 is mapped to `met2.label` `69/5`.
- ioPin layer 4 is mapped to `met3.label` `70/5`.
- ioPin layer 5 is mapped to `met4.label` `71/5`.
- ioPin layer 6 is mapped to `met5.label` `72/5`.
- The older MAGICAL TEXT records on `131/0` and `136/0` are intentionally retained for comparison.
- If Magic still extracts anonymous internal node names, the next check is whether Magic expects pin shapes in addition to labels.
