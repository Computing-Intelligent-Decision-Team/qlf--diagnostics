# Native Sky130 TODO

## Must Complete

1. Keep `examples/mockPDK` and `examples/sky130PDK` untouched while native trials
   are developed under `generated/sky130PDK_native_trial`.
2. Define a native export map that separates MAGICAL internal layer IDs from
   Sky130 GDS layer/datatype/purpose.
3. Add an opt-in native export path for final `*.route.gds`, likely starting in
   `anaroute/src/writer/wrLayout.cpp`.
4. Preserve existing mockPDK/bridge behavior when native export is disabled.
5. Move route drawing layer/datatype remap from `remap_gds_to_sky130.py` into
   native GDS export.
6. Move top-port filtering into native pin export. The authoritative allowed pin
   set must be the source top subckt port list, not all `.ioPin` entries.
7. Emit Sky130 label-purpose TEXT for top ports only.
8. Emit Sky130 pin-purpose BOUNDARY geometry for top ports only.
9. Keep power-net names explicit in JSON/case config; do not hardcode Sky130
   global power names into MAGICAL defaults.
10. Validate native output against the current regression cases:
    `inverter_core`, `ota_core`, and `current_mirror_core`.

## Should Complete

1. Generate a Sky130-native trial LEF from Sky130 tech LEF routing/cut rules,
   constrained to what Anaroute can parse.
2. Decide and document the routing stack policy:
   - MAGICAL `M1` -> Sky130 `li1`; or
   - MAGICAL `M1` -> Sky130 `met1`.
3. Audit device generation layer dictionaries against the selected routing stack.
4. Add native export reports showing every emitted MAGICAL layer and resulting
   Sky130 layer/datatype/purpose.
5. Add regression checks that fail if internal routed nets are present in raw
   Magic `.subckt` ports.
6. Keep raw PEX extraction and connectivity LVS split in the case pipeline.
7. Document all unsupported/TBD layers in the native export map.

## Later Optimization

1. Replace bridge postprocess scripts in the case pipeline with no-op validation
   once native export is stable.
2. Support richer Sky130 device variants and marker layers, such as threshold
   options and resistor layers.
3. Add parasitic-aware LVS or structured PEX comparison after native connectivity
   output is stable.
4. Expand regression with diff pair, current mirror variants, comparator/preamp
   slices, and resistor/capacitor cases.
5. Add automated comparison between bridge output and native output for the same
   case during transition.
