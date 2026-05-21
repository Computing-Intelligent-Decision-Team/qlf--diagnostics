# Native Sky130 GDS Export Map

## Summary

- Source YAML: `/home/to/eda/tools/src/MAGICAL/generated/sky130PDK_trial/sky130_gds_export_map.yaml`
- Anaroute map: `/home/to/eda/tools/src/MAGICAL/generated/sky130PDK_native_trial/sky130_anaroute_gds_export.map`
- Scope: confirmed drawing/well/implant/contact/via mappings only.
- Phase 1.5 adds NW/PP/NP to remove known Magic GDS-read unknown layers from the native inverter trial.
- Excluded in Phase 1.5: STDPIN, label layers, pin-purpose layers, markers without confirmed need, and TBD layers.

## Export Rows

| MAGICAL layer | input layer | input datatype | Sky130 layer/datatype | Sky130 name |
| --- | ---: | ---: | --- | --- |
| NW | 3 | 0 | 64/20 | nwell.drawing |
| OD | 6 | 0 | 65/20 | diff.drawing |
| PO | 17 | 0 | 66/20 | poly.drawing |
| PP | 25 | 0 | 94/20 | psdm.drawing |
| NP | 26 | 0 | 93/44 | nsdm.drawing |
| CO | 30 | 0 | 66/44 | licon1.drawing |
| M1 | 31 | 0 | 67/20 | li1 |
| VIA1 | 51 | 0 | 67/44 | mcon |
| M2 | 32 | 0 | 68/20 | met1 |
| VIA2 | 52 | 0 | 68/44 | via |
| M3 | 33 | 0 | 69/20 | met2 |
| VIA3 | 53 | 0 | 69/44 | via2 |
| M4 | 34 | 0 | 70/20 | met3 |
| VIA4 | 54 | 0 | 70/44 | via3 |
| M5 | 35 | 0 | 71/20 | met4 |
| VIA5 | 55 | 0 | 71/44 | via4 |
| M6 | 36 | 0 | 72/20 | met5 |

## Notes

- The C++ writer reads this file only when `MAGICAL_GDS_EXPORT_MAP` is set.
- Rows not listed here remain unchanged and are reported by the writer-side export-map report.
- Text records are intentionally left unchanged in Phase 1.5 because native pin label and pin-purpose export is a separate step.
