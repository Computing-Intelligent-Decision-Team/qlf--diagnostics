# MAGICAL NMOS Terminal Assignment Analysis

## 1. Scope

This report analyzes why the Sky130 inverter source netlist

```spice
M0 (Y A VGND VGND) sky130_fd_pr__nfet_01v8 l=150n w=1u multi=1 nf=1
```

still extracts from Magic as:

```spice
X0 Y A a_n15_90# VGND sky130_fd_pr__nfet_01v8 ...
```

The analysis is read-only. It does not modify MAGICAL source, mockPDK,
sky130PDK, baseline GDS files, or the inverter LVS normalization script.

## 2. Input Netlist Pin Order

Input file: `examples/inverter_sky130_try/inverter_sky130_name_test.sp`

| instance | input line | interpreted order |
| --- | --- | --- |
| M0 | `M0 (Y A VGND VGND) sky130_fd_pr__nfet_01v8 ...` | D=`Y`, G=`A`, S=`VGND`, B=`VGND` |
| M1 | `M1 (Y A VPWR VPWR) sky130_fd_pr__pfet_01v8 ...` | D=`Y`, G=`A`, S=`VPWR`, B=`VPWR` |

The parser grammar in `flow/python/DesignDB.py` reads the parenthesized net
list as an ordered list. The `mosfet.connect()` method explicitly treats the
four positions as drain, gate, source, and bulk.

Evidence:

- `flow/python/DesignDB.py:151-161`: creates `drain`, `gate`, `source`, `bulk`
  pins and connects them in `connect(drain, gate, source, bulk)`.
- `flow/python/DesignDB.py:464-466`: leaf MOS subckt nets are named by index,
  with the source comment saying `0:drain, 1:gate, etc...`.

## 3. Sky130 Device Name Mapping

`sky130_fd_pr__nfet_01v8` is in the NMOS recognition set and is handled through
the same `mosfet` logic as existing `nch_lvt_mac` devices.

Evidence:

- `flow/python/DesignDB.py:12`: `sky130_fd_pr__nfet_01v8` is in `nmos_set`.
- `flow/python/DesignDB.py:208-211`: the Sky130 NFET class subclasses
  `mosfet` without custom terminal logic.
- `flow/python/DesignDB.py:497-509`: any `nmos_set` reference allocates an
  `Nch` physical property and sets `ImplTypePCELL_Nch`.

This means the Sky130 name support currently does not introduce a separate
Sky130 pin-order mapping. It reuses MAGICAL's legacy MOS pin order:

| internal net index | meaning |
| ---: | --- |
| 0 | drain |
| 1 | gate |
| 2 | source |
| 3 | bulk / psub |

## 4. Device Generator Terminal Geometry

The MOS generator creates pins in the order `[drain, gate, source]` for NMOS.
For a single-finger device, it places:

| generator pin | geometry side | source evidence |
| --- | --- | --- |
| source | left vertical M1 stripe | `device_generation/device_generation/Mosfet.py:293-295` |
| drain | right vertical M1 stripe | `device_generation/device_generation/Mosfet.py:293-295` |
| gate | top M1 gate shape | `device_generation/device_generation/Mosfet.py:88-93`, `286-291` |

The writeback code maps `self.cell.pin()` back to DB net indices by order.

Evidence:

- `device_generation/device_generation/Mosfet.py:51-54`: creates D/G/S/B pin
  objects.
- `device_generation/device_generation/Mosfet.py:88-93`: NMOS `pin()` returns
  `[drain, gate, source]`.
- `flow/python/Device_generator.py:62-80`: walks those pins in order and maps
  them to integer net names `0`, `1`, `2`, ...

For this inverter run, `examples/inverter_sky130_try/inverter_core.pin`
confirms the generated M0 local pin boxes:

| M0 local pin index | expected meaning | local box |
| ---: | --- | --- |
| 0 | drain | `(350, -50) - (450, 1050)` |
| 1 | gate | `(-50, 1150) - (450, 1250)` |
| 2 | source | `(-50, -50) - (50, 1050)` |
| 3 | bulk | `-1` |

So MAGICAL's device generator assigns M0 source to the left diffusion terminal
and M0 drain to the right diffusion terminal.

## 5. Router Pin Assignment Evidence

Router debug file: `examples/inverter_sky130_try/inverter_core.gr`

After placement, the router sees these relevant pins:

| net | router pin id | io layer | placed box | interpretation |
| --- | ---: | ---: | --- | --- |
| Y | 2 | 1 | `(350, 350) - (450, 1450)` | M0 right drain terminal |
| VGND | 5 | 1 | `(-50, 350) - (50, 1450)` | M0 left source terminal |
| VGND | 6 | 6 | `(-650, -1050) - (3250, -950)` | psub / guard-ring rail |

The routing log confirms those router pins are assigned to the expected nets:

| log line | meaning |
| --- | --- |
| `addShape2Pin 2 0 700 700 900 2900` | Y pin on M0 right terminal, after router 2x scale |
| `addShape2Pin 5 0 -100 700 100 2900` | VGND pin on M0 left source terminal, after router 2x scale |
| `addShape2Pin psub shape 5 -1300 -2100 6500 -1900` | VGND psub/power-layer rail |
| `addPin2Net  2 1` | Y pin attached to router net Y |
| `addPin2Net  5 3` | M0 source pin attached to router net VGND |
| `addPin2Net pubs ver 6 3` | psub rail attached to router net VGND |

This is the strongest evidence that parser order and router input assignment
are not swapped: MAGICAL gives the router `Y -> right terminal` and
`VGND -> left terminal`.

## 6. Comparison With Magic Raw Extraction

Raw extracted file:
`generated/sky130_lvs_pinned_shapes/inverter_core_extracted_pinned_shapes.spice`

```spice
.subckt inverter_core_flat A Y VPWR VGND
X0 Y A a_n15_90# VGND sky130_fd_pr__nfet_01v8 ...
```

Previous geometric terminal diagnosis:
`docs/sky130_adapter/nmos_terminal_mapping_diagnosis.md`

| physical terminal | bbox | Magic / connectivity result |
| --- | --- | --- |
| NMOS left terminal | `(-75, 450) - (125, 1450)` | associated with `a_n15_90#`; no VGND pin-purpose overlap |
| NMOS right terminal | `(275, 450) - (475, 1450)` | connected to `Y` |
| VGND rail | `(-650, -1050) - (3250, -950)` | valid port/rail, but separate from left source terminal |

This aligns with MAGICAL's right terminal assignment for `Y`, but not with the
intended left terminal assignment for `VGND`.

## 7. Power-Net Naming Observation

Current `examples/inverter_sky130_try/inverter_trial.json` does not override
`vddNetNames` or `vssNetNames`. The defaults in `flow/python/Params.py` include
`VDD/GND` variants but not `VPWR/VGND`.

The routing log shows all four inverter nets are passed to Anaroute with
`isPower False`, including `VPWR` and `VGND`.

This is a real Sky130 adapter issue, but it does not fully explain the present
source disconnect by itself, because `.gr` still shows both the M0 source pin
and the psub rail assigned to the same `VGND` router net. It may affect routing
priority, width/via choices, and power-stripe treatment, so it should be fixed
or tested separately.

## 8. Current Classification

| possible cause | current evidence | verdict |
| --- | --- | --- |
| netlist pin order mismatch | M0 input order is D/G/S/B; DesignDB uses D/G/S/B; `.gr` maps Y to drain and VGND to source | unlikely |
| Sky130 device-name mapping mismatch | Sky130 NFET reuses legacy MOS logic, no alternate pin order | unlikely |
| device generator left/right naming mismatch | single-finger source is left, drain is right; `.gr` uses VGND left and Y right | unlikely as a naming-only bug |
| router assignment mismatch | router input assignment is correct in `.gr` | unlikely at input boundary |
| source/drain symmetry handling mismatch | Magic agrees right terminal is Y; left terminal remains internal, not swapped to VGND | not the main symptom |
| body/source tap confusion | body/tap is VGND, source remains internal; this is visible in Magic raw extraction | possible symptom, not root cause |
| routed geometry connectivity issue | router says both source pin and psub rail are VGND, but final GDS/Magic sees them disconnected | most likely |

The most likely root cause is downstream of router pin assignment: Anaroute or
post-routing GDS output produced disconnected geometry for the VGND net, or the
route for the source-side VGND component did not physically merge with the
VGND rail/port component under Magic's Sky130 extraction rules.

## 9. Recommended Next Minimum Experiments

1. Run a terminal-swap netlist experiment without overwriting the baseline:
   create a separate `examples/inverter_sky130_try_terminal_swap/` using
   `M0 (VGND A Y VGND) ...`. If Magic then extracts `X0 VGND A ...`, it confirms
   parser/device pin order sensitivity; if the same side remains floating, it
   confirms a routing/connectivity issue.

2. Add `VPWR` to `vddNetNames` and `VGND` to `vssNetNames` in an experiment-only
   JSON, then rerun the trial PDK flow. The current log shows both are not
   treated as power nets. This may change power routing behavior.

3. Inspect Anaroute's final routed geometry per net, or add a non-invasive dump
   around routed wires for net `VGND`. The key question is whether router net
   `VGND` has one connected component or multiple disconnected components before
   GDS writing.

4. If Anaroute internally believes VGND is connected but Magic does not, compare
   the exact via/contact stack from M0 source to the psub rail after remap. If
   Anaroute also has multiple components, the fix belongs in routing completion
   or net handling.

## 10. Patch Direction, Not Applied

No source patch is applied in this step.

Likely future patch candidates, in order of least invasive:

1. Add Sky130 power-net names through experiment JSON:
   `vddNetNames: ["VDD", "vdd", "vdda", "vddd", "VPWR"]`,
   `vssNetNames: ["VSS", "GND", "vss", "gnd", "vssa", "vssd", "VGND"]`.
2. Add a router connectivity report/check for each routed net before writing
   GDS, especially for nets with both device pins and psub/nwell pins.
3. If a terminal-swap experiment proves orientation sensitivity, add an explicit
   Sky130 MOS D/S mapping layer rather than changing global legacy MOS behavior.

`normalize_lvs_netlists_inverter.py` must remain for now because raw Magic
extraction still contains `a_n15_90#`.
