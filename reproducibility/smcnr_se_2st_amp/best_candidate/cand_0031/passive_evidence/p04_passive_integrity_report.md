# Passive-Aware Extraction Integrity Report

## Summary

- Probe pipeline status: PASS
- Probe failed stage: None
- Probe return code: 0
- Source passive devices: 2
- Generated passive GDS files: 2
- Dropped source passives during LVS preparation: None
- Extracted physical passive devices: 8
- Extracted intentional passive devices: 0
- Passive-related TBD remap layers: 0
- Magic unknown layers: 0
- GDS remap report present: yes
- Magic extract log present: yes
- Raw extracted netlist present: yes

## Source Passive Instances

| instance | model | terminals | generated GDS |
| --- | --- | --- | --- |
| `xr0` | `rppolywo_m` | `net027 vout gnda` | yes |
| `xc0` | `cfmom_2t` | `outn net027` | yes |

## Extracted Physical Passive Models

| model | count |
| --- | ---: |
| `sky130_fd_pr__res_generic_m1` | 2 |
| `sky130_fd_pr__res_generic_m2` | 2 |
| `sky130_fd_pr__res_generic_m3` | 2 |
| `sky130_fd_pr__res_generic_m4` | 2 |

## Layer Remap Findings

- No passive-related TBD remap layers found.

## Magic Extraction Findings

- No Magic unknown layer/datatype messages found.

## Interpretation

Passive-aware LVS/PEX is not proven: raw extraction produced 8 physical passive devices, but preserved only 0/2 source passive instances; LVS preparation did not report source passive preservation status.
