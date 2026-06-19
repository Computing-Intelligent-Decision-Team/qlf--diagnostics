# Analog Harness Summary

| Field | Value |
| --- | --- |
| design_id | smcnr_se_2st_amp |
| top_cell | SMCNR_SE_2st_AMP |
| run_dir | E:\codex-magical-sky130-harness\magical-sky130-harness\generated\analog_harness\smcnr_se_2st_amp |
| verification_scope | mos_only_projection |
| candidate_count | 38 |
| best_candidate | cand_0031 |
| best_reward | 0.6000000000000001 |
| best_closure_level | L6_post_layout_pvt |
| best_passive_aware_status | pass |
| best_passive_aware_scope | full_passive_inclusive_gds_lvs |
| best_passive_lvs_evidence_scope | formal_passive_abstraction_with_gds_mos_bridge |
| best_segmented_resistor_chain_formalized | True |
| best_cfmom_plate_coupling_formalized | True |
| best_passive_lvs_primitive_abstractions | [{'abstraction_rule': 'collapse_plate_coupling_evidence_to_lvs_capacitor', 'candidate_type': 'plate_coupling_capacitor_source_equivalent', 'electrical_terminals': ['outn', 'net027'], 'lvs_primitive_device_class': 'c', 'lvs_primitive_kind': 'capacitor', 'lvs_primitive_spice': 'C_xc0 outn net027 1f', 'source_instance': 'xc0', 'support_type': 'plate_coupling_capacitance'}, {'abstraction_rule': 'collapse_segmented_resistor_chain_to_lvs_resistor', 'candidate_type': 'segmented_resistor_chain_source_equivalent', 'electrical_terminals': ['net027', 'vout'], 'lvs_primitive_device_class': 'r', 'lvs_primitive_kind': 'resistor', 'lvs_primitive_spice': 'R_xr0 net027 vout 1', 'source_instance': 'xr0', 'support_type': 'segmented_resistor_chain'}] |
| best_route_bridge_trial_status | pass |
| best_route_bridge_drc_count | 0 |
| best_route_bridge_mos_connectivity_status | pass |
| best_route_bridge_formal_passive_lvs_netgen_status | pass |
| best_full_passive_inclusive_gds_lvs_proven | True |
| best_native_passive_device_recognition_status | pass |
| best_native_passive_device_recognition_claimed | True |
| best_native_passive_device_recognition_missing_instances | [] |
| best_native_passive_device_recognition_blockers | {} |
| best_native_passive_capability_source_model_native_status | fail |
| best_native_passive_capability_direct_source_model_support | False |
| best_native_passive_capability_unsupported_source_models | ['cfmom_2t', 'rppolywo_m'] |
| best_native_passive_capability_retarget_available | True |
| best_native_passive_capability_retarget_map | {'cfmom_2t': ['sky130_fd_pr__cap_mim_m3_1', 'sky130_fd_pr__cap_mim_m3_2', 'sky130_fd_pr__cap_var', 'sky130_fd_pr__cap_var_hvt', 'sky130_fd_pr__cap_var_lvt'], 'rppolywo_m': ['sky130_fd_pr__res_xhigh_po', 'sky130_fd_pr__res_xhigh_po_0p35', 'sky130_fd_pr__res_xhigh_po_0p69', 'sky130_fd_pr__res_xhigh_po_1p41', 'sky130_fd_pr__res_xhigh_po_2p85', 'sky130_fd_pr__res_xhigh_po_5p73', 'sky130_fd_pr__res_generic_po', 'sky130_fd_pr__res_generic_l1', 'sky130_fd_pr__res_generic_m1', 'sky130_fd_pr__res_generic_m2', 'sky130_fd_pr__res_generic_m3', 'sky130_fd_pr__res_generic_m4', 'sky130_fd_pr__res_generic_m5', 'sky130_fd_pr__res_generic_nd', 'sky130_fd_pr__res_generic_nd__hv', 'sky130_fd_pr__res_generic_pd', 'sky130_fd_pr__res_generic_pd__hv', 'sky130_fd_pr__res_high_po', 'sky130_fd_pr__res_high_po_0p35', 'sky130_fd_pr__res_high_po_0p69', 'sky130_fd_pr__res_high_po_1p41', 'sky130_fd_pr__res_high_po_2p85', 'sky130_fd_pr__res_high_po_5p73', 'sky130_fd_pr__res_iso_pw']} |
| best_native_passive_capability_requires_geometry_replacement | True |
| best_native_passive_capability_can_fix_current_gds_by_layer_remap_only | False |
| best_native_passive_capability_device_generation_source_status | {'can_patch_current_generator_source': True, 'checked': True, 'missing_files': [], 'recognized_layout_generator_files': ['device_generation\\device_generation\\Resistor.py', 'device_generation\\device_generation\\Capacitor.py']} |
| best_native_passive_retarget_trial_status | native_passive_retarget_ready |
| best_native_resistor_chain_status | pass |
| best_native_resistor_chain_netgen_status | pass |
| best_native_resistor_chain_device_count | 31 |
| best_native_resistor_chain_model | ['sky130_fd_pr__res_xhigh_po'] |
| best_native_capacitor_device_recognition_status | pass |
| best_native_passive_retarget_missing_native_source_passive_instances | [] |
| best_native_passive_retarget_full_native_passive_lvs_ready | True |
| best_native_passive_retarget_full_native_passive_lvs_proven | True |
| best_native_cap_gencell_extraction_status | pass |
| best_native_cap_gencell_model | sky130_fd_pr__cap_mim_m3_1 |
| best_native_cap_gencell_recognized_device_count | 1 |
| best_native_cap_replacement_status | replacement_candidate_prepared |
| best_native_cap_replacement_cell_name | SMCNR_SE_2st_AMP_xc0 |
| best_native_cap_replacement_terminal_bridge_status | m4_outside_stacks_inserted |
| best_native_cap_replacement_top_gds_merge_status | merged_replacement_candidate |
| best_native_cap_replacement_bridge_mode | m4_outside_stacks |
| best_native_cap_replacement_full_gds | generated\analog_harness\smcnr_se_2st_amp\cand_0031\layout_passive_existing_gds\resistor_remap_variants\native_cap_full_gds_trial\native_cap_replaced.gds |
| best_native_cap_replacement_extract_status | pass |
| best_native_cap_replacement_drc_status | pass |
| best_native_cap_replacement_drc_count | 0 |
| best_native_cap_replacement_native_passive_netgen_status | pass |
| best_native_cap_replacement_native_capacitor_device_count | 1 |
| best_native_cap_full_gds_trial_status | pass |
| best_native_cap_full_gds_trial_summary_json | E:\codex-magical-sky130-harness\magical-sky130-harness\generated\analog_harness\smcnr_se_2st_amp\cand_0031\layout_passive_existing_gds\resistor_remap_variants\native_cap_full_gds_trial\native_cap_full_gds_trial_summary.json |
| best_native_cap_replacement_full_native_capacitor_lvs_ready | True |
| best_native_cap_replacement_remaining_gates | [] |
| best_passive_evidence_backfilled_from_artifacts | True |
| knowledge_transfer_archive | E:\codex-magical-sky130-harness\magical-sky130-harness\generated\analog_harness\smcnr_se_2st_amp\knowledge_transfer |

## Candidates

| Candidate | Reward | Closure | Scope |
| --- | ---: | --- | --- |
| cand_0001 | -0.11390024867156133 | L1_pre_layout_nominal | mos_only_projection |
| cand_0002 | -0.11390024867156133 | L1_pre_layout_nominal | mos_only_projection |
| cand_0003 | -0.11390024867156133 | L1_pre_layout_nominal | mos_only_projection |
| cand_0004 | -0.11390024867156133 | L1_pre_layout_nominal | mos_only_projection |
| cand_0005 | -0.039845910155576196 | L1_pre_layout_nominal | mos_only_projection |
| cand_0006 | -0.039845910155576196 | L1_pre_layout_nominal | mos_only_projection |
| cand_0007 | -0.11390024867156133 | L1_pre_layout_nominal | mos_only_projection |
| cand_0008 | -0.1142121463911572 | L1_pre_layout_nominal | mos_only_projection |
| cand_0009 | -0.1142121463911572 | L1_pre_layout_nominal | mos_only_projection |
| cand_0010 | -0.1142121463911572 | L1_pre_layout_nominal | mos_only_projection |
| cand_0011 | -0.1142121463911572 | L1_pre_layout_nominal | mos_only_projection |
| cand_0012 | -0.039845910155576196 | L1_pre_layout_nominal | mos_only_projection |
| cand_0013 | -0.039845910155576196 | L1_pre_layout_nominal | mos_only_projection |
| cand_0014 | 0.1357878536088428 | L4_layout_verified_mos_only | mos_only_projection |
| cand_0015 | 0.1357878536088428 | L4_layout_verified_mos_only | mos_only_projection |
| cand_0016 | 0.1357878536088428 | L4_layout_verified_mos_only | mos_only_projection |
| cand_0017 | 0.1357878536088428 | L4_layout_verified_mos_only | mos_only_projection |
| cand_0018 | -0.11532673588472588 | L1_pre_layout_nominal | mos_only_projection |
| cand_0019 | 0.1357878536088428 | L4_layout_verified_mos_only | mos_only_projection |
| cand_0020 | -0.11532673588472588 | L1_pre_layout_nominal | mos_only_projection |
| cand_0021 | 0.1357878536088428 | L4_layout_verified_mos_only | mos_only_projection |
| cand_0022 | -0.11532673588472588 | L1_pre_layout_nominal | mos_only_projection |
| cand_0023 | 0.1357878536088428 | L4_layout_verified_mos_only | mos_only_projection |
| cand_0024 | 0.1357878536088428 | L4_layout_verified_mos_only | mos_only_projection |
| cand_0025 | 0.28898759026137577 | L5_post_layout_nominal | mos_only_projection |
| cand_0026 | 0.5296713513860634 | L6_post_layout_pvt | mos_only_projection |
| cand_0027 | 0.47500114565925994 | L6_post_layout_pvt | mos_only_projection |
| cand_0028 | 0.6000000000000001 | L6_post_layout_pvt | mos_only_projection |
| cand_0029 | 0.6000000000000001 | L6_post_layout_pvt | mos_only_projection |
| cand_0030 | 0.6000000000000001 | L6_post_layout_pvt | mos_only_projection |
| cand_0031 | 0.6000000000000001 | L6_post_layout_pvt | mos_only_projection |
| cand_0032 | -0.18471423696282185 | L1_pre_layout_nominal | mos_only_projection |
| cand_0033 | -0.18471423696282185 | L1_pre_layout_nominal | mos_only_projection |
| cand_0034 | -0.18471423696282185 | L1_pre_layout_nominal | mos_only_projection |
| cand_0035 | -0.18471423696282185 | L1_pre_layout_nominal | mos_only_projection |
| cand_0036 | -0.18471423696282185 | L1_pre_layout_nominal | mos_only_projection |
| cand_0037 | -0.1142121463911572 | L1_pre_layout_nominal | mos_only_projection |
| cand_0038 | -0.18471423696282185 | L1_pre_layout_nominal | mos_only_projection |
