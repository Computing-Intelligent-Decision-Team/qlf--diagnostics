# Sky130 Case Pipeline Summary

| Field | Value |
| --- | --- |
| CASE_NAME | smcnr_se_2st_amp_cand_0031 |
| TOP_CELL | SMCNR_SE_2st_AMP |
| VDD_NET | vdda |
| VSS_NET | gnda |
| SKY130A | /root/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A |
| STATUS | FAIL |
| FAILED_STAGE | connectivity_lvs |
| MESSAGE | Connectivity LVS did not pass; see /mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/lvs_result_summary.md |
| MAGICAL_RESULT | pass |
| LAYOUT_INPUT_MODE | source |
| LAYOUT_PROJECTION_DROPPED_PASSIVES | 0 |
| MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER | 0 |
| MAGICAL_SKIP_ROUTER_PARSE_GDS | 0 |
| MAGICAL_SKIP_TOP_POWER_ROUTE | 0 |
| MAGICAL_POWER_STRIPE_EXTRA_GRID | 0 |
| MAGICAL_POWER_STRIPE_EXTRA_DBU | 0 |
| MAGICAL_DISABLE_POWER_STRIPE | 0 |
| MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES | 0 |
| MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU | 400 |
| MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS | 35,36 |
| MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU | 400 |
| MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_LAYERS | 35,36 |
| MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_BOX_DBU | 1900,13200,32900,13400 |
| MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_MARGIN_DBU | 100 |
| MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU | 40000 |
| MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU | 0 |
| MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES | 1 |
| MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU | 200 |
| MAGICAL_LOCAL_VDD_STRIPE_Y_DBU | 13200 |
| MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU | 0 |
| MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU | 3000:3450,6400:8150,9950:11250,12100:12300,12900:13650,15150:16450,18350:19650,20350:21650 |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE | 0 |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_BOX_DBU | none |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU | none |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE | 1 |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE_MARGIN_DBU | 100 |
| GDS_REMAP_RESULT | pass |
| EXPERIMENTAL_PASSIVE_REMAP | yes |
| PIN_LABEL_RESULT | pass |
| PIN_SHAPE_RESULT | pass |
| DRC_COUNT | 0 |
| LVS_MODE | full_extraction |
| RAW_SUBCKT_PORTS | vdda gnda vin vip ibias vout |
| ANONYMOUS_NODES | a_10945_2960#,a_10945_3220#,a_10945_3480#,a_10945_3740#,a_10945_4000#,a_10945_4260#,a_10945_4520#,a_10945_4780#,a_10945_5040#,a_10945_5300#,a_10945_5560#,a_10945_5820#,a_10945_6080#,a_10945_6340#,a_10945_6600#,a_11789_2830#,a_11789_3090#,a_11789_3350#,a_11789_3610#,a_11789_3870#,a_11789_4130#,a_11789_4390#,a_11789_4650#,a_11789_4910#,a_11789_5170#,a_11789_5430#,a_11789_5690#,a_11789_5950#,a_11789_6210#,a_11789_6470#,a_11789_6730#,a_1340_n30#,a_3264_586#,a_3585_n10#,a_660_2774#,a_n15_2446# |
| CONNECTIVITY_LVS_MATCH | no |
| NETGEN_EXIT_STATUS | 0 |
| NET_RENAMES_USED | no |
| PEX_CAPS | 350 |
| PEX_TOTAL_CAP_FF | 677.247 fF |
| PEX_OUTPUT_NODE | vout |

## KEY_OUTPUTS

- Case directory: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/case`
- Source/MAGICAL netlist: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/case/SMCNR_SE_2st_AMP_cand_0031.sp`
- Config: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/case/smcnr_se_2st_amp_cand_0031_passive_probe.json`
- Layout projection case directory: ``
- Layout projection netlist: ``
- Layout projection config: ``
- MAGICAL log: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/magical_place_route.log`
- MAGICAL run log: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/run_SMCNR_SE_2st_AMP_trial.log`
- ioPin: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/SMCNR_SE_2st_AMP.ioPin`
- Route GDS: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/SMCNR_SE_2st_AMP.route.gds`
- Sky130 remapped GDS: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/SMCNR_SE_2st_AMP.sky130.gds`
- Pinned-shapes GDS: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds`
- Generated GDS directory: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/gds`
- DRC log: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/magic_drc.log`
- Raw extracted netlist: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/SMCNR_SE_2st_AMP_extracted.spice`
- Raw extracted netlist copy: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/SMCNR_SE_2st_AMP_extracted.raw.spice`
- Connectivity source netlist: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/SMCNR_SE_2st_AMP_source.connectivity.spice`
- Connectivity extracted netlist: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/SMCNR_SE_2st_AMP_extracted.connectivity.spice`
- LVS preparation report: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/lvs_preparation_report.md`
- Netgen connectivity LVS report: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/netgen_lvs_report.out`
- LVS result summary: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/lvs_result_summary.md`
- PEX summary: `/mnt/e/codex-magical-sky130-harness/magical-sky130-harness/generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware/pex_summary.md`
