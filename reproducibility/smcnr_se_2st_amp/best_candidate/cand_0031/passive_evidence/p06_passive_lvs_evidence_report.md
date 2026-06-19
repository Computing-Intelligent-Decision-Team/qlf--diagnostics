# Passive LVS Evidence Verification

## Summary

- Input summary: `generated\analog_harness\smcnr_se_2st_amp\cand_0031\layout_passive_existing_gds\resistor_remap_variants\resistor_remap_variant_probe_summary.json`
- Status: `formal_passive_lvs_evidence_pass`
- Verification scope: `formal_passive_abstraction_with_gds_mos_bridge`
- Formal passive LVS evidence pass: `True`
- Full-GDS formal passive LVS evidence pass: `False`
- Route-bridge formal passive LVS evidence pass: `True`
- Full passive-inclusive GDS LVS proven: `False`
- Native passive device recognition status: `fail`
- Native passive device recognition claimed: `False`
- Native passive missing instances: `['xr0', 'xc0']`
- Failed requirements: `none`

## Requirements

| Requirement | Pass |
| --- | --- |
| `all_source_passives_have_candidate` | `True` |
| `cfmom_plate_coupling_formalized` | `True` |
| `hybrid_mos_reference_passive_netgen_lvs_pass` | `True` |
| `packet_formal_lvs_abstraction_ready` | `True` |
| `passive_only_netgen_lvs_pass` | `True` |
| `primitive_counts_match` | `True` |
| `primitive_netlists_present` | `True` |
| `segmented_resistor_chain_formalized` | `True` |

## Route Bridge Gates

| Gate | Pass |
| --- | --- |
| `route_bridge_drc_clean` | `True` |
| `route_bridge_formal_passive_lvs_pass` | `True` |
| `route_bridge_inserted` | `True` |
| `route_bridge_mos_connectivity_pass` | `True` |

## Primitive Counts

- Source abstraction: `{'resistor': 1, 'capacitor': 1, 'total': 2}`
- Candidate abstraction: `{'resistor': 1, 'capacitor': 1, 'total': 2}`
- Primitive abstraction records: `[{'source_instance': 'xc0', 'candidate_type': 'plate_coupling_capacitor_source_equivalent', 'abstraction_rule': 'collapse_plate_coupling_evidence_to_lvs_capacitor', 'support_type': 'plate_coupling_capacitance', 'lvs_primitive_device_class': 'c', 'lvs_primitive_kind': 'capacitor', 'lvs_primitive_spice': 'C_xc0 outn net027 1f', 'electrical_terminals': ['outn', 'net027']}, {'source_instance': 'xr0', 'candidate_type': 'segmented_resistor_chain_source_equivalent', 'abstraction_rule': 'collapse_segmented_resistor_chain_to_lvs_resistor', 'support_type': 'segmented_resistor_chain', 'lvs_primitive_device_class': 'r', 'lvs_primitive_kind': 'resistor', 'lvs_primitive_spice': 'R_xr0 net027 vout 1', 'electrical_terminals': ['net027', 'vout']}]`

## Interpretation

A formal pass means segmented resistor chains and cfmom plate-coupling evidence have been promoted into primitive LVS R/C devices and have passed Netgen in both passive-only and MOS-reference hybrid trials.

This is still distinct from native full-GDS passive-aware LVS. Native proof is reported only when `native_passive_device_recognition_claimed=true`.
