# Native Sky130 Passive Retarget LVS Trial

- Status: `native_passive_retarget_incomplete`
- Native resistor chain status: `pass`
- Native resistor chain device count: `31`
- Native capacitor device recognition status: `fail`
- Missing native source passive instances: `['xc0']`
- Full native passive LVS ready: `False`
- Full native passive LVS proven: `False`

## Artifacts

- Source native passive netlist: `generated\analog_harness\smcnr_se_2st_amp\cand_0031\layout_passive_existing_gds\resistor_remap_variants\native_passive_retarget_trial\SMCNR_SE_2st_AMP_source_native_passive.spice`
- Candidate native passive netlist: `generated\analog_harness\smcnr_se_2st_amp\cand_0031\layout_passive_existing_gds\resistor_remap_variants\native_passive_retarget_trial\SMCNR_SE_2st_AMP_candidate_native_passive.spice`

## Resistor Chain Netgen

- Status: `pass`
- Report: `generated\analog_harness\smcnr_se_2st_amp\cand_0031\layout_passive_existing_gds\resistor_remap_variants\native_passive_retarget_trial\SMCNR_SE_2st_AMP_native_resistor_chain_netgen.out`
- Log: `generated\analog_harness\smcnr_se_2st_amp\cand_0031\layout_passive_existing_gds\resistor_remap_variants\native_passive_retarget_trial\SMCNR_SE_2st_AMP_native_resistor_chain_netgen.log`

## Native Capacitor Blocker

The candidate extraction did not contain a Sky130 native capacitor device such as `sky130_fd_pr__cap_mim_m3_1` or `sky130_fd_pr__cap_mim_m3_2` for the source capacitor. Existing evidence remains plate-coupling PEX, not native LVS device recognition.
