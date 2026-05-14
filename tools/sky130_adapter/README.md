# Sky130 Adapter PDK Generator

This directory contains helper scripts for building trial MAGICAL PDK files from
the layer mapping draft in `docs/sky130_adapter/sky130_layer_map.yaml`.

The generated PDK is a trial artifact. It is not a completed Sky130 PDK
adaptation and is not expected to be Sky130 DRC-clean yet.

## Dry Run

From the MAGICAL repository root:

```bash
python3 tools/sky130_adapter/generate_magical_sky130_pdk.py --dry-run
```

The dry run prints which MAGICAL layers would be remapped to Sky130 GDS layer
numbers in the separate export map, and which layers still have `TBD`
mappings.

## Generate Trial PDK

From the MAGICAL repository root:

```bash
python3 tools/sky130_adapter/generate_magical_sky130_pdk.py
```

This writes:

```text
generated/sky130PDK_trial/sky130.techfile
generated/sky130PDK_trial/sky130.techfile.simple
generated/sky130PDK_trial/sky130.lef
generated/sky130PDK_trial/sky130_gds_export_map.yaml
```

The script does not overwrite `examples/sky130PDK` and does not modify
`examples/mockPDK`.

The generated trial PDK is MAGICAL-internal-layer-compatible. That means
`sky130.techfile` and `sky130.techfile.simple` keep the original mockPDK
internal layer numbers and ordering so `TechDB::addNewLayer` can parse them.
Real Sky130 GDS layer/datatype information is recorded separately in
`sky130_gds_export_map.yaml`.

## Point Inverter Test To The Trial PDK

For a temporary local test, edit `examples/inverter_sky130_try/inverter.json`
so the PDK paths point two directories up to `generated/sky130PDK_trial`:

```json
{
  "spectre_netlist": "inverter_sky130_name_test.sp",
  "simple_tech_file": "../../generated/sky130PDK_trial/sky130.techfile.simple",
  "techfile": "../../generated/sky130PDK_trial/sky130.techfile",
  "lef": "../../generated/sky130PDK_trial/sky130.lef"
}
```

Then run the existing inverter flow from `examples/inverter_sky130_try`.

## Current Limitations

- MAGICAL layer names are preserved (`OD`, `PO`, `CO`, `M1`, `VIA1`, etc.) so
  existing parsers can still recognize them.
- MAGICAL internal layer IDs are preserved in `sky130.techfile` and
  `sky130.techfile.simple`. They are not real Sky130 GDS layer numbers.
- Real Sky130 layer/datatype mappings are stored in
  `sky130_gds_export_map.yaml` for a future GDS export remap or post-processing
  step.
- `sky130.lef` still keeps the mock-style width, spacing, pitch, area, and via
  geometry in this draft. A later generator should derive these rules from the
  real Sky130 tech LEF.
- Sky130 has a `li1/mcon/met1` stack, while MAGICAL currently has a simpler
  mock routing stack. The generated trial PDK is for interface experiments, not
  final DRC-clean layout.
- The next engineering step is to implement GDS export remapping, or a
  post-processing script, so final GDS output can use real Sky130
  layer/datatype pairs without breaking MAGICAL's internal TechDB ordering.
- Magic/KLayout DRC and LVS validation still need to be added after the layer
  mapping and rule generation become more complete.
