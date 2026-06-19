# LVS Preparation Report

## Outputs

- Input source netlist: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection_case/SMCNR_SE_2st_AMP_mos_only.sp`
- Input Magic raw extracted netlist: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.spice`
- Raw extracted netlist copy: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.raw.spice`
- Connectivity source netlist: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection/SMCNR_SE_2st_AMP_source.connectivity.spice`
- Connectivity extracted netlist: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.connectivity.spice`

## Connectivity Normalization

- Dropped unsupported source passive devices: 0
- Deleted parasitic capacitor lines: 37
- Source MOS model aliases:
  - `nch_mac->sky130_fd_pr__nfet_01v8`: 3
  - `pch_mac->sky130_fd_pr__pfet_01v8`: 5
- Dropped source passive models:
  - none
- Removed MOS properties:
  - `ad`: 8
  - `as`: 8
  - `pd`: 8
  - `ps`: 8

## Net Renames

| Extracted net | Connectivity net |
| --- | --- |
| `a_20_494#` | `outn` |
| `a_2100_n30#` | `outp` |
| `a_4024_586#` | `net53` |
| `a_4345_n10#` | `outp` |
| `a_785_2846#` | `ibias` |

Renamed lines: 7

## LVS Type

This output is for connectivity LVS, not parasitic-aware LVS.
The raw Magic extraction is preserved separately so parasitic information is not lost.
