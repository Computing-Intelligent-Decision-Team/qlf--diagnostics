# GDS Remap Report

## Summary

- Input GDS: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection_case/SMCNR_SE_2st_AMP.route.gds`
- Output GDS: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection_case/SMCNR_SE_2st_AMP.sky130.gds`
- Export map: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/sky130PDK_trial/sky130_gds_export_map.yaml`
- Unique input layer/datatype pairs: 20
- Successfully remapped pairs: 17
- Preserved TBD pairs: 1
- Preserved unmapped pairs: 2

The original MAGICAL GDS is not modified. This post-processing step rewrites confirmed MAGICAL internal layers to their proposed Sky130 GDS layer/datatype targets. TBD and unmapped layers are left unchanged.

## Layer Actions

| input layer | input datatype | element type | output layer | output datatype | action | mapping |
| ---: | ---: | --- | ---: | ---: | --- | --- |
| 3 | 0 | BOUNDARY | 64 | 20 | remapped | NW -> nwell.drawing 64/20 |
| 6 | 0 | BOUNDARY | 65 | 20 | remapped | OD -> diff.drawing 65/20 |
| 17 | 0 | BOUNDARY | 66 | 20 | remapped | PO -> poly.drawing 66/20 |
| 25 | 0 | BOUNDARY | 94 | 20 | remapped | PP -> psdm.drawing 94/20 |
| 26 | 0 | BOUNDARY | 93 | 44 | remapped | NP -> nsdm.drawing 93/44 |
| 30 | 0 | BOUNDARY | 66 | 44 | remapped | CO -> licon1.drawing 66/44 |
| 31 | 0 | BOUNDARY | 67 | 20 | remapped | M1 -> li1 67/20 |
| 32 | 0 | BOUNDARY | 68 | 20 | remapped | M2 -> met1 68/20 |
| 33 | 0 | BOUNDARY | 69 | 20 | remapped | M3 -> met2 69/20 |
| 34 | 0 | BOUNDARY | 70 | 20 | remapped | M4 -> met3 70/20 |
| 35 | 0 | BOUNDARY | 71 | 20 | remapped | M5 -> met4 71/20 |
| 36 | 0 | BOUNDARY | 72 | 20 | remapped | M6 -> met5 72/20 |
| 51 | 0 | BOUNDARY | 67 | 44 | remapped | VIA1 -> mcon 67/44 |
| 52 | 0 | BOUNDARY | 68 | 44 | remapped | VIA2 -> via 68/44 |
| 53 | 0 | BOUNDARY | 69 | 44 | remapped | VIA3 -> via2 69/44 |
| 54 | 0 | BOUNDARY | 70 | 44 | remapped | VIA4 -> via3 70/44 |
| 55 | 0 | BOUNDARY | 71 | 44 | remapped | VIA5 -> via4 71/44 |
| 131 | 0 | TEXT | 131 | 0 | preserved_unmapped | not listed in export map |
| 136 | 0 | TEXT | 136 | 0 | preserved_unmapped | not listed in export map |
| 208 | 1 | BOUNDARY | 208 | 1 | preserved_tbd | LVS_DUMMY -> TBD |

## Notes

- `remapped` means both GDS layer and datatype were replaced from `sky130_gds_export_map.yaml`.
- `preserved_tbd` means the MAGICAL layer exists in the export map but its Sky130 target is not confirmed.
- `preserved_unmapped` means the input GDS layer is not listed in the export map.
- This remap is a layer/datatype translation only; it does not make the layout Sky130 DRC-clean.
