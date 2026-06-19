# Sky130 Native Passive Capability Probe

- Source netlist: `examples\smcnr_se_2st_amp_sky130_try\SMCNR_SE_2st_AMP_layout_physical_hspice.sp`
- Sky130A: `/root/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A`
- Source passive models: `['cfmom_2t', 'rppolywo_m']`
- Source model native status: `fail`
- Direct source model support: `False`
- Unsupported source models: `['cfmom_2t', 'rppolywo_m']`
- Native retarget available: `True`
- Requires source model change: `True`
- Requires geometry replacement: `True`
- Layer remap alone sufficient: `False`
- Recommended action: `retarget source models and generated passive geometry to supported Sky130 primitives`

## Source Passives

| Instance | Model | Kind | Direct Native Support | Retarget Candidates |
| --- | --- | --- | --- | --- |
| xr0 | rppolywo_m | resistor | False | sky130_fd_pr__res_xhigh_po, sky130_fd_pr__res_xhigh_po_0p35, sky130_fd_pr__res_xhigh_po_0p69, sky130_fd_pr__res_xhigh_po_1p41, sky130_fd_pr__res_xhigh_po_2p85, sky130_fd_pr__res_xhigh_po_5p73, sky130_fd_pr__res_generic_po, sky130_fd_pr__res_generic_l1, sky130_fd_pr__res_generic_m1, sky130_fd_pr__res_generic_m2, sky130_fd_pr__res_generic_m3, sky130_fd_pr__res_generic_m4, sky130_fd_pr__res_generic_m5, sky130_fd_pr__res_generic_nd, sky130_fd_pr__res_generic_nd__hv, sky130_fd_pr__res_generic_pd, sky130_fd_pr__res_generic_pd__hv, sky130_fd_pr__res_high_po, sky130_fd_pr__res_high_po_0p35, sky130_fd_pr__res_high_po_0p69, sky130_fd_pr__res_high_po_1p41, sky130_fd_pr__res_high_po_2p85, sky130_fd_pr__res_high_po_5p73, sky130_fd_pr__res_iso_pw |
| xc0 | cfmom_2t | capacitor | False | sky130_fd_pr__cap_mim_m3_1, sky130_fd_pr__cap_mim_m3_2, sky130_fd_pr__cap_var, sky130_fd_pr__cap_var_hvt, sky130_fd_pr__cap_var_lvt |

## Native Primitive Support

- Magic supported passive models: `29`
- Netgen supported passive models: `45`
- Intersection used for retargeting: `['sky130_fd_pr__cap_mim_m3_1', 'sky130_fd_pr__cap_mim_m3_2', 'sky130_fd_pr__cap_var', 'sky130_fd_pr__cap_var_hvt', 'sky130_fd_pr__cap_var_lvt', 'sky130_fd_pr__res_generic_l1', 'sky130_fd_pr__res_generic_m1', 'sky130_fd_pr__res_generic_m2', 'sky130_fd_pr__res_generic_m3', 'sky130_fd_pr__res_generic_m4', 'sky130_fd_pr__res_generic_m5', 'sky130_fd_pr__res_generic_nd', 'sky130_fd_pr__res_generic_nd__hv', 'sky130_fd_pr__res_generic_pd', 'sky130_fd_pr__res_generic_pd__hv', 'sky130_fd_pr__res_generic_po', 'sky130_fd_pr__res_high_po', 'sky130_fd_pr__res_high_po_0p35', 'sky130_fd_pr__res_high_po_0p69', 'sky130_fd_pr__res_high_po_1p41', 'sky130_fd_pr__res_high_po_2p85', 'sky130_fd_pr__res_high_po_5p73', 'sky130_fd_pr__res_iso_pw', 'sky130_fd_pr__res_xhigh_po', 'sky130_fd_pr__res_xhigh_po_0p35', 'sky130_fd_pr__res_xhigh_po_0p69', 'sky130_fd_pr__res_xhigh_po_1p41', 'sky130_fd_pr__res_xhigh_po_2p85', 'sky130_fd_pr__res_xhigh_po_5p73']`

## Generator Source Check

- Status: `{'checked': True, 'can_patch_current_generator_source': True, 'missing_files': [], 'recognized_layout_generator_files': ['device_generation\\device_generation\\Resistor.py', 'device_generation\\device_generation\\Capacitor.py']}`
