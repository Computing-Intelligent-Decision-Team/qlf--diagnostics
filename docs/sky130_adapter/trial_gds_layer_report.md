# Trial GDS Layer Report

## Summary

- GDS file: `/home/to/eda/tools/src/MAGICAL/examples/inverter_sky130_try/inverter_core.route.gds`
- Export map: `/home/to/eda/tools/src/MAGICAL/generated/sky130PDK_trial/sky130_gds_export_map.yaml`
- Unique layer/datatype pairs found: 19
- Pairs with confirmed Sky130 export target: 16
- Pairs whose MAGICAL layer is still TBD: 1
- Pairs not listed in export map: 2

The current `generated/sky130PDK_trial` keeps MAGICAL/mock internal layer numbers in the PDK files so MAGICAL can parse them. Therefore the layer/datatype pairs below are the layers actually present in the trial GDS today, not final Sky130 DRC-clean layer/datatype output.

## Observed GDS Layers

| GDS layer | datatype | element type | datatype record | current interpretation | Sky130 export target | status |
| ---: | ---: | --- | --- | --- | --- | --- |
| 3 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | NW -> nwell.drawing 64/20 | confirmed_target |
| 6 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | OD -> diff.drawing 65/20 | confirmed_target |
| 17 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | PO -> poly.drawing 66/20 | confirmed_target |
| 25 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | PP -> psdm.drawing 94/20 | confirmed_target |
| 26 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | NP -> nsdm.drawing 93/44 | confirmed_target |
| 30 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | CO -> TBD | tbd |
| 31 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | M1 -> li1 67/20 | confirmed_target |
| 32 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | M2 -> met1 68/20 | confirmed_target |
| 33 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | M3 -> met2 69/20 | confirmed_target |
| 34 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | M4 -> met3 70/20 | confirmed_target |
| 35 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | M5 -> met4 71/20 | confirmed_target |
| 36 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | M6 -> met5 72/20 | confirmed_target |
| 51 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | VIA1 -> mcon 67/44 | confirmed_target |
| 52 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | VIA2 -> via 68/44 | confirmed_target |
| 53 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | VIA3 -> via2 69/44 | confirmed_target |
| 54 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | VIA4 -> via3 70/44 | confirmed_target |
| 55 | 0 | BOUNDARY | DATATYPE | MAGICAL internal/mock layer | VIA5 -> via4 71/44 | confirmed_target |
| 131 | 0 | TEXT | TEXTTYPE | MAGICAL internal/mock layer | not listed in export map | not_mapped |
| 136 | 0 | TEXT | TEXTTYPE | MAGICAL internal/mock layer | not listed in export map | not_mapped |

## Notes

- `sky130_gds_export_map.yaml` is a target map for future GDS remapping or post-processing.
- A `confirmed_target` row means the MAGICAL internal layer has a proposed Sky130 layer/datatype target.
- A `tbd` row means the layer appears in the trial GDS but the Sky130 target is not yet confirmed.
- This report does not claim the trial GDS is Sky130 DRC-clean.
