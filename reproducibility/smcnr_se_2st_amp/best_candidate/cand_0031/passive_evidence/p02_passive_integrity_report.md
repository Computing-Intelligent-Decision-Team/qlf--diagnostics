# Passive-Aware Extraction Integrity Report

## Summary

- Source passive devices: 2
- Generated passive GDS files: 2
- Dropped source passives during LVS preparation: 2
- Extracted intentional passive devices: 0
- Passive-related TBD remap layers: 13
- Magic unknown layers: 13

## Source Passive Instances

| instance | model | terminals | generated GDS |
| --- | --- | --- | --- |
| `xr0` | `rppolywo_m` | `net027 vout gnda` | yes |
| `xc0` | `cfmom_2t` | `outn net027` | yes |

## Layer Remap Findings

- `RPDMY:115/1` remains TBD/preserved in Sky130 remap.
- `RH:117/0` remains TBD/preserved in Sky130 remap.
- `MRDMY:150/2` remains TBD/preserved in Sky130 remap.
- `MRDMY:150/3` remains TBD/preserved in Sky130 remap.
- `MRDMY:150/4` remains TBD/preserved in Sky130 remap.
- `MRDMY:150/5` remains TBD/preserved in Sky130 remap.
- `TSV_PPI:155/2` remains TBD/preserved in Sky130 remap.
- `TSV_PPI:155/3` remains TBD/preserved in Sky130 remap.
- `TSV_PPI:155/4` remains TBD/preserved in Sky130 remap.
- `TSV_PPI:155/5` remains TBD/preserved in Sky130 remap.
- `TSV_PPI:155/27` remains TBD/preserved in Sky130 remap.
- `TSV_PPI:155/100` remains TBD/preserved in Sky130 remap.
- `LVS_DUMMY:208/1` remains TBD/preserved in Sky130 remap.

## Magic Extraction Findings

- Magic reported unknown layer/datatype `115/1`.
- Magic reported unknown layer/datatype `117/0`.
- Magic reported unknown layer/datatype `150/2`.
- Magic reported unknown layer/datatype `150/3`.
- Magic reported unknown layer/datatype `150/4`.
- Magic reported unknown layer/datatype `150/5`.
- Magic reported unknown layer/datatype `155/2`.
- Magic reported unknown layer/datatype `155/3`.
- Magic reported unknown layer/datatype `155/4`.
- Magic reported unknown layer/datatype `155/5`.
- Magic reported unknown layer/datatype `155/100`.
- Magic reported unknown layer/datatype `155/27`.
- Magic reported unknown layer/datatype `208/1`.

## Interpretation

Passive-aware LVS/PEX is not proven: 13 passive-related GDS layer/datatype pairs remain TBD in Sky130 remap; Magic reported 13 unknown passive-related layer/datatype pairs; raw extraction preserved 0/2 intentional passive devices; LVS preparation dropped 2 unsupported source passive devices.
