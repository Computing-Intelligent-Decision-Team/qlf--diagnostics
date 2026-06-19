# Magic PEX Summary

- Raw extracted netlist: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout/lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.raw.spice`
- Parasitic capacitor count: 37
- Total listed capacitance: 71.4964 fF

## Per-Node Capacitance

| Node | Capacitor count | Sum connected capacitance |
| --- | --- | --- |
| `vdda` | 10 | 54.5395 fF |
| `gnda` | 10 | 49.1385 fF |
| `a_2100_n30#` | 8 | 9.9677 fF |
| `ibias` | 8 | 9.1607 fF |
| `vip` | 8 | 5.22407 fF |
| `vin` | 6 | 5.13997 fF |
| `a_20_494#` | 6 | 4.76097 fF |
| `a_4024_586#` | 6 | 2.60956 fF |
| `vout` | 6 | 2.20939 fF |
| `a_4345_n10#` | 3 | 0.19183 fF |
| `a_785_2846#` | 3 | 0.0506 fF |

## Output Node Estimate

| Node | Connected capacitor count | Sum connected capacitance |
| --- | ---: | ---: |
| `vout` | 6 | 2.20939 fF |

## Largest 10 Capacitors

| Cap | Node 1 | Node 2 | Value |
| --- | --- | --- | --- |
| `C31` | `vdda` | `gnda` | 35.8705 fF |
| `C1` | `ibias` | `vdda` | 6.97853 fF |
| `C33` | `a_2100_n30#` | `gnda` | 6.57175 fF |
| `C19` | `vip` | `vdda` | 3.90033 fF |
| `C13` | `vin` | `vdda` | 3.37202 fF |
| `C34` | `a_20_494#` | `gnda` | 3.04694 fF |
| `C0` | `a_2100_n30#` | `vdda` | 2.63138 fF |
| `C30` | `ibias` | `gnda` | 1.98759 fF |
| `C6` | `vout` | `a_20_494#` | 0.96845 fF |
| `C11` | `vin` | `a_4024_586#` | 0.91307 fF |

## Note

This is a PEX summary only. The connectivity LVS netlists intentionally remove
these capacitors, while the raw extracted netlist keeps them for later analysis.
