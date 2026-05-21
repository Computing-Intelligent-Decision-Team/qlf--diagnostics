# Native Sky130 PDK Integration Plan

## Scope

This document starts native Sky130 PDK integration planning from the existing
bridge/remap flow. It is an audit and design note only. It does not modify
MAGICAL core source, Anaroute, device generation, `examples/mockPDK`,
`examples/sky130PDK`, regression case inputs, or generated regression outputs.

Current bridge regression cases:

- `inverter_core`
- `ota_core`
- `current_mirror_core`

These cases prove the bridge flow, not a completed native Sky130 adaptation.

## Current Bridge Flow

Current data path:

```text
MAGICAL internal PDK / mock-compatible trial PDK
  -> MAGICAL placement GDS
  -> Anaroute route.gds using MAGICAL internal layer numbers
  -> remap_gds_to_sky130.py
  -> add_sky130_pin_labels_from_iopin.py
  -> add_sky130_pin_shapes_from_iopin.py
  -> Magic DRC / extraction
  -> Netgen connectivity LVS
  -> PEX summary from raw Magic extraction
```

The route GDS is still written by MAGICAL/Anaroute in internal layer space.
Sky130 layer/datatype semantics are added after export.

## Target Native Flow

Target data path:

```text
Sky130-native MAGICAL PDK
  -> MAGICAL native GDS export with Sky130 layer/datatype/purpose
  -> Magic DRC / extraction
  -> Netgen LVS
```

The target removes the external remap and pin postprocess steps. The case
pipeline may still run DRC/LVS/PEX, but it should no longer repair GDS layer or
pin-purpose data.

## Relevant MAGICAL Data Flow

### JSON and Power Nets

`flow/python/Params.py` reads:

- `spectre_netlist`
- `simple_tech_file`
- `techfile`
- `lef`
- `vddNetNames`
- `vssNetNames`

`flow/python/MagicalDB.py` calls `markPowerNets()`, which marks nets matching
the JSON-provided `vddNetNames` and `vssNetNames`.

Power-net names should remain case/config inputs. They should not become a
global Sky130 default hardcoded in MAGICAL.

### TechDB and Simple Techfile

`flow/python/MagicalDB.py` calls:

```python
magicalFlow.parseSimpleTechFile(params, self.techDB)
```

The C++ side is:

- `flow/cpp/magical_flow/src/db/TechDB.h`
- `flow/cpp/magical_flow/src/db/TechDB.cpp`
- `flow/cpp/magical_flow/src/parser/ParseSimpleTech.cpp`

`TechDB::addNewLayer()` requires new layer IDs to be added in increasing order.
This is the core reason not to directly replace MAGICAL internal layer IDs with
Sky130 GDS numbers in the internal techfile.

### LEF and Anaroute Techfile

`flow/python/PnR.py` calls:

```python
router.parseLef(self.params.lef)
router.parseTechfile(self.params.techfile)
```

The Anaroute side is:

- `anaroute/src/parser/parLef.cpp`
- `anaroute/src/db/dbLef.hpp`
- `anaroute/src/db/dbLef.cpp`
- `anaroute/src/parser/parTech.cpp`
- `anaroute/src/db/dbTechfile.hpp`

The LEF parser builds routing/cut layer rule data. The techfile maps layer names
to mask/layer indices through `TechfileDB`.

### Route GDS Export

`flow/python/PnR.py` writes route GDS through:

```python
router.writeLayoutGds(placeFile, dirname + ckt.name + ".route.gds", True)
```

The Anaroute export path is:

- `anaroute/src/writer/writer.cpp`
- `anaroute/src/writer/wrLayout.cpp`
- `anaroute/src/writer/wrGds.cpp`

`wrLayout.cpp` reads the placement GDS, adds routing geometry, flattens the top
cell, and writes `*.route.gds`.

Current route geometry behavior:

- routing boxes use `maskIdx = _cir.layerIdx2MaskIdx(layerIdx)`;
- datatype is `0` for most layers;
- datatype is `40` for layers above the sixth routing layer;
- IO text is emitted on `100 + maskIdx`;
- text currently does not encode Sky130 label purpose/texttype.

This is the most likely first native export hook.

### Device/Placement GDS Export

Device/placement GDS is written before Anaroute merges routing:

- `flow/cpp/magical_flow/src/writer/GdsWriter.h`
- `flow/python/Flow.py`
- `flow/python/PnR.py`
- `device_generation/device_generation/*.py`

`GdsWriter.h` maps internal DB layer to PDK layer through
`TechDB::dbLayerToPdk()` and preserves rectangle datatype from layout data.

Device generation also uses gdspy directly and local layer dictionaries. Native
Sky130 device GDS will eventually need its own layer/purpose treatment, but that
should be separated from the first route export hook.

### ioPin and Pin Text

`flow/python/PnR.py` writes an intermediate debug-style pin file before routing:

```python
self.writeiopifile(cktIdx, iopinfile)
```

Anaroute writes the final `.ioPin` via:

```python
router.writeDumb(placeFile, dirname + ckt.name + ".ioPin")
```

The relevant source is:

- `anaroute/src/writer/wrDumb.cpp`
- `anaroute/src/parser/parIOPin.cpp`

`wrDumb.cpp` emits one selected layer/box per net, including routed internal
nets. It does not know the top subckt port list. That is why the bridge
postprocess needs a top-port filter.

## Current Bridge Responsibilities

### `remap_gds_to_sky130.py`

Current responsibilities:

- drawing layer remap;
- contact/via layer remap;
- datatype rewrite;
- TEXT layer/TEXTTYPE handling when layer records are present;
- preserving unmapped/TBD layers.

This script consumes:

```text
generated/sky130PDK_trial/sky130_gds_export_map.yaml
```

### Pin Label Postprocess

`add_sky130_pin_labels_from_iopin.py` currently handles:

- parsing `ioPin`;
- parsing the source top subckt port list;
- filtering internal routed nets;
- choosing Sky130 label layers:
  - `li1.label` 67/5;
  - `met1.label` 68/5;
  - `met5.label` 72/5;
- inserting GDS TEXT records.

### Pin Shape Postprocess

`add_sky130_pin_shapes_from_iopin.py` currently handles:

- parsing `ioPin`;
- applying the same top-port filter;
- choosing Sky130 pin-purpose layers:
  - `li1.pin` 67/16;
  - `met1.pin` 68/16;
  - `met5.pin` 72/16;
- inserting pin-purpose BOUNDARY geometry.

## Where Responsibilities Should Move

| Responsibility | Native destination | Notes |
| --- | --- | --- |
| Internal layer ordering | PDK generator / simple techfile | Preserve MAGICAL internal increasing IDs. Do not force Sky130 GDS numbers into internal IDs. |
| Sky130 drawing layer/datatype map | PDK generator plus GDS export layer | Keep mapping data generated, but consume it in native export instead of postprocess. |
| Routing/cut rule stack | LEF generator | Generate an Anaroute-readable LEF from Sky130 routing/cut rules. |
| Route shape GDS layer/datatype | Anaroute `wrLayout.cpp` export layer | First recommended native hook for route polygons and route TEXT. |
| Device/placement GDS layer/datatype | Device generator and/or MAGICAL `GdsWriter.h` | Needed after route export hook; device geometry may use gdspy and separate layer dictionaries. |
| Top-port determination | MAGICAL/PnR case context or export metadata | Must come from source top subckt ports, not `.ioPin` alone. |
| Sky130 label TEXT export | GDS export layer, likely `wrLayout.cpp` for top-level route IO text | Needs layer-specific label map and TEXTTYPE support. |
| Sky130 pin-purpose geometry | GDS export layer, likely alongside route IO text/pin geometry | Emit only for top ports, using layer-specific pin-purpose map. |
| `.ioPin` debug output | Keep as debug/report artifact | It should not be the authoritative native pin source. |
| DRC/LVS/PEX orchestration | case pipeline | Pipeline should verify native output, not repair it. |

## Recommended Native Implementation Phases

### Phase A: Native Export Audit

Complete source audit and document exact modification points. This document and
`native_sky130_export_flow_audit.md` are Phase A artifacts.

### Phase B: `generated/sky130PDK_native_trial`

Generate a native-trial PDK directory under `generated/`, not
`examples/sky130PDK`. Keep internal MAGICAL layer IDs stable while adding an
explicit export map for Sky130 GDS layer/datatype/purpose.

### Phase C: Native GDS Layer Export

Teach the GDS export path to consume the export map directly. The first
candidate is Anaroute `wrLayout.cpp`, because it writes final `*.route.gds`.
This should replace `remap_gds_to_sky130.py` for routing layers first.

### Phase D: Native Top-Port Pin Export

Move top-port pin label and pin-purpose generation into native export. The
exporter must filter to true top ports and skip internal routed nets such as
`net1`, `net2`, and `NREF`.

### Phase E: Native Regression

Run native output through the same regression cases:

- `inverter_core`
- `ota_core`
- `current_mirror_core`

The bridge/remap regression should stay available until native output matches
or exceeds it.

## Risks

- `TechDB::addNewLayer()` requires increasing internal layer IDs.
- Sky130 layer/datatype/purpose is not one-to-one with MAGICAL routing layer IDs.
- Sky130 label and pin purposes are layer-specific.
- `.ioPin` can include internal routed nets; internal nets must not become top ports.
- Power-net names must remain explicit case/config data.
- Native export must not break mockPDK or bridge regression flows.
- The current Anaroute route export uses mask index and ad hoc datatype rules;
  replacing those must be staged and regression-tested.
- `M1` as Sky130 `li1` versus `met1` remains a stack policy decision with device
  generation consequences.

## First Recommended Modification Point

The first native code change should be in the final route GDS export layer,
behind an opt-in native Sky130 export map:

```text
anaroute/src/writer/wrLayout.cpp
```

Reason:

- it writes the final flattened `*.route.gds`;
- it already sees route wires and IO text;
- it is where the current external remap has the closest native equivalent;
- it can be gated so mockPDK and existing bridge flows continue unchanged.

Do not start by changing `TechDB` layer IDs or global power-net defaults.
