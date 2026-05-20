# Sky130 Power-Net Config Default

## 1. Background

MAGICAL's generic examples normally rely on default power names such as `VDD`
and `GND`. The Sky130 inverter uses Sky130-style names instead:

```spice
M0 (Y A VGND VGND) sky130_fd_pr__nfet_01v8 ...
M1 (Y A VPWR VPWR) sky130_fd_pr__pfet_01v8 ...
```

Without explicit Sky130 power-net configuration, the layout can route and label
cell ports, but Magic raw extraction may leave the NMOS source on an anonymous
node such as `a_n15_90#`.

## 2. Why Not Change MAGICAL Global Defaults

The fix is specific to the Sky130 adapter flow. Changing MAGICAL's global
default power names would affect existing mockPDK and other PDK examples that
still use `VDD` and `GND`. The current approach keeps the generic flow unchanged
and adds VPWR/VGND only in the Sky130 inverter configuration path.

## 3. Default Location

The maintained baseline config is:

```text
examples/inverter_sky130_try/inverter.json
```

It now declares:

```json
"vddNetNames" : ["VPWR"],
"vssNetNames" : ["VGND"]
```

The Docker trial wrapper also emits the same fields into its temporary
`inverter_trial.json`:

```text
examples/inverter_sky130_try/run_with_trial_sky130PDK.sh
```

The adapter utility:

```text
tools/sky130_adapter/ensure_sky130_inverter_powernets.py
```

checks and, if needed, updates `inverter.json` before the enhanced Sky130
inverter pipeline runs. It writes a report to:

```text
generated/sky130_powernet_pipeline/inverter/powernet_config_check.md
```

## 4. Pipeline Integration

The enhanced pipeline:

```bash
tools/sky130_adapter/run_inverter_sky130_powernet_pipeline.sh
```

runs the power-net config check before MAGICAL placement/routing. This makes the
Sky130 inverter baseline self-checking without changing MAGICAL's global
defaults.

## 5. Raw Extraction Result

Before the power-net fix, raw Magic extraction could contain:

```spice
X0 Y A a_n15_90# VGND sky130_fd_pr__nfet_01v8 ...
```

After the fix, raw Magic extraction is clean:

```spice
.subckt inverter_core_flat A Y VPWR VGND
X0 Y A VPWR VPWR sky130_fd_pr__pfet_01v8 ...
X1 Y A VGND VGND sky130_fd_pr__nfet_01v8 ...
```

The anonymous NMOS source node is gone.

## 6. DRC and LVS

The latest enhanced pipeline result is summarized in:

```text
generated/sky130_powernet_pipeline/inverter/summary.md
```

Observed checks:

| Check | Result |
| --- | --- |
| VPWR recognized as VDD | yes |
| VGND recognized as VSS | yes |
| Raw NMOS | `X1 Y A VGND VGND ...nfet...` |
| Anonymous extracted nodes | none |
| Magic DRC error count | 0 |
| Netgen LVS match after normalization | yes |

## 7. Normalization Status

Keep:

```text
tools/sky130_adapter/normalize_lvs_netlists_inverter.py
```

Raw net naming is now clean for the power-net-fixed baseline, so the
`a_n15_90# -> VGND` rename is not expected to be needed for this case. The
normalization step is still used for connectivity LVS because Magic extraction
adds parasitic capacitors and layout-derived MOS properties such as `ad`, `as`,
`pd`, and `ps`.

PEX-oriented flows should keep those parasitics and layout-derived properties;
the current normalization is only a temporary connectivity-LVS helper.

## 8. Next Step

When Sky130 adapter support expands beyond this inverter, propagate the same
PDK-specific default power-net policy to generated configs for additional
Sky130 examples such as diff-pair and OTA cases. Keep the behavior local to the
Sky130 adapter layer unless there is a separate, explicit decision to change
MAGICAL global defaults.
