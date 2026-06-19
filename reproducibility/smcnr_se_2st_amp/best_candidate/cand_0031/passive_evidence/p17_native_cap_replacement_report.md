# Sky130 Native Capacitor Replacement Candidate

- Status: `replacement_candidate_prepared`
- Source instance: `xc0`
- Source model: `cfmom_2t`
- Replacement cell: `SMCNR_SE_2st_AMP_xc0`
- Native cap extraction: `pass`
- Replacement GDS: `generated\analog_harness\smcnr_se_2st_amp\cand_0031\layout_passive_existing_gds\resistor_remap_variants\native_cap_replacement_candidate\SMCNR_SE_2st_AMP_xc0.gds`
- Replacement SPICE: `generated\analog_harness\smcnr_se_2st_amp\cand_0031\layout_passive_existing_gds\resistor_remap_variants\native_cap_replacement_candidate\SMCNR_SE_2st_AMP_xc0.spice`
- Terminal bridge status: `not_implemented`
- Top GDS merge status: `not_implemented`
- Full native capacitor LVS ready: `False`

## Remaining Gates

- connect original MAGICAL xc0 route-pin boxes to generated MIM C1/C2 terminals
- replace xc0 cell in the full routed Sky130 GDS without disturbing MOS/resistor routing
- rerun Magic extraction and prove xc0 appears as sky130_fd_pr__cap_* in the full top netlist
