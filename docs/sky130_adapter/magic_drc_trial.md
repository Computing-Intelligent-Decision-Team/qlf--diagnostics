# Magic DRC Trial

## Current Goal

Run a first automated Magic DRC trial on the Sky130-remapped inverter GDS. This
checks whether Magic can load the Sky130 technology, read the remapped GDS, load
the expected top cell, and execute `drc check` / `drc count`.

This is not a DRC-clean signoff step.

## Run Command

From the MAGICAL repository root:

```bash
tools/sky130_adapter/run_magic_drc_inverter.sh
```

If a different Sky130A PDK root is needed:

```bash
SKY130A=/path/to/sky130A tools/sky130_adapter/run_magic_drc_inverter.sh
```

## Input GDS

```text
examples/inverter_sky130_try/inverter_core.sky130.gds
```

## Magic RC File

Default path:

```text
/home/to/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A/libs.tech/magic/sky130A.magicrc
```

The script uses `$SKY130A/libs.tech/magic/sky130A.magicrc`. If `SKY130A` is not
set, it uses the default Sky130A path above.

## Generated Files

```text
generated/sky130_drc/inverter_magic_drc.tcl
generated/sky130_drc/inverter_magic_drc.log
```

The generated TCL performs:

```tcl
gds read examples/inverter_sky130_try/inverter_core.sky130.gds
load inverter_core_flat
drc check
drc count
quit -noprompt
```

## Success Criteria

- Magic starts in batch mode.
- `sky130A.magicrc` loads.
- The GDS is read.
- The top cell `inverter_core_flat` can be loaded.
- `drc check` and `drc count` execute.
- A log is written to `generated/sky130_drc/inverter_magic_drc.log`.

If `load inverter_core_flat` fails, inspect the log and check the actual GDS
top-level cell name.

## Current Limitations

- DRC failure is expected at this stage.
- The current GDS is only a layer/datatype-remapped MAGICAL output.
- Sky130 geometry rules are not guaranteed yet.
- Contact enclosure, well/tap, implant, local interconnect, and related device
  rules have not been fully adapted.
