# Fan_SMC Diagnostic Psubstrate Tap Design

## Status

Approved direction: add one diagnostic p+ substrate tap stack to a new
Fan_SMC candidate. This specification does not authorize controller, reward,
GRPO, closure-level, or historical-artifact changes.

## Purpose

Test one hypothesis:

> The bounded-C0 Fan_SMC extraction collapses substrate and supply identities
> because the generated physical layout has no explicit p+ substrate contact
> tied to the existing `gnda` route.

This is a diagnostic A/B, not the final NMOS primitive architecture and not a
claim that the C0 layout surrogate is electrically equivalent to 5 pF.

## Baseline

Input GDS:

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/
fan_smc_c0_proxy_94x10/fan_smc_pin_3.pinned_shapes.gds
```

The baseline has:

- 24 extracted MOS devices;
- Magic substrate named `vout`;
- explicit `vout=vdda` and `vout=gnda` equivalences;
- only `vinn vinp vout` surviving as extracted top ports;
- no explicit NMOS body pin or p+ substrate tap;
- an existing gnda met5 vertical rail covering approximately
  `x=150..650`, `y=-2050..11650` database units.

## Alternatives Considered

### Selected: One top-level diagnostic p+ tap stack

Insert one physical p+ substrate contact in empty space and connect it through
a vertical contact/metal stack to the existing gnda met5 rail.

Advantages:

- one bounded conceptual variable;
- no P&R rerun;
- preserves every existing device, route, port and passive;
- directly tests substrate naming and equivalence behavior;
- fully reversible because output is a new generated GDS.

Limitation: this does not establish the final per-device body-aware primitive.

### Deferred: Modify every NMOS primitive

Add a physical fourth pin and local p+ tap to each NMOS primitive, then rerun
P&R. This is architecturally stronger but changes primitive geometry,
placement bounds and routing contracts simultaneously.

### Rejected For First A/B: Insert a complete native standard-cell tap

Sky130 `tapvgnd`/`tapvpwrvgnd` cells also introduce pwell, nwell, p+ tap, n+
tap and both power rails. That changes several physical variables and does not
fit the first root-cause experiment.

## New Tool

Add:

```text
tools/sky130_adapter/add_diagnostic_psub_tap_stack.py
tools/sky130_adapter/test_add_diagnostic_psub_tap_stack.py
```

Command interface:

```text
--input-gds PATH
--output-gds PATH
--report PATH
--summary-json PATH
--cell fan_smc_pin_3_flat
--anchor-x 400
--anchor-y -1000
--expected-gnda-met5-box 150,-2050,650,11650
```

The tool must fail without writing output when:

- the requested top cell is absent;
- the anchor is outside the expected gnda met5 geometry;
- the proposed stack overlaps poly, nwell or existing active diffusion;
- output would overwrite the input;
- the input cannot be parsed as GDS.

## Added Physical Stack

The stack is one logical object. Its layer purposes are:

| Purpose | Sky130 GDS |
| --- | --- |
| psubstrate contact diffusion | `tap.drawing` 65/44 |
| p+ implant | `psdm.drawing` 94/20 |
| local diffusion contact | `licon1.drawing` 66/44 |
| local interconnect | `li1.drawing` 67/20 |
| LI-to-met1 contact | `mcon.drawing` 67/44 |
| routing patches | met1 through met5 drawing layers |
| routing vias | via through via4 drawing layers |

No TEXT or pin-purpose shape is added. Net identity must come only from
physical overlap with the existing labeled gnda met5 component.

The default anchor is `(400, -1000)`, within the existing gnda vertical met5
rail and below placed devices. Rectangles are fixed relative to the anchor:

| Element | Relative bbox `(x1,y1,x2,y2)` |
| --- | --- |
| tap.drawing | `(-150,-150,150,150)` |
| psdm.drawing | `(-250,-250,250,250)` |
| licon1.drawing | `(-25,-25,25,25)` |
| li1.drawing | `(-150,-150,150,150)` |
| mcon.drawing | `(-50,-50,50,50)` |
| met1.drawing | `(-150,-150,150,150)` |
| via.drawing | `(-25,-25,25,25)` |
| met2.drawing | `(-150,-150,150,150)` |
| via2.drawing | `(-25,-25,25,25)` |
| met3.drawing | `(-150,-150,150,150)` |
| via3.drawing | `(-25,-25,25,25)` |
| met4.drawing | `(-150,-150,150,150)` |
| via4.drawing | `(-50,-50,50,50)` |
| met5.drawing | `(-150,-150,150,150)` |

These dimensions match contact scales already present in the candidate and
are diagnostic, not a waiver of Sky130 DRC. The JSON report records every
absolute rectangle. Implant and conductor enclosures are explicit rather than
inferred.

## Preservation Invariants

The tool must prove in its summary that:

- all original GDS records remain byte-identical and in the same order;
- only new BOUNDARY elements are inserted before the selected cell's ENDSTR;
- no existing layer/datatype, TEXT, SREF, cell name or bbox is rewritten;
- the source netlist and MAGICAL route artifacts are untouched;
- exactly one diagnostic stack is added.

## TDD Plan

Use synthetic in-memory GDS fixtures.

1. RED: a valid fixture receives exactly the expected stack layers and record
   counts while preserving all original records.
2. RED: insertion is rejected when no existing met5 anchor overlaps the stack.
3. RED: insertion is rejected when the tap region overlaps poly, nwell or
   active diffusion.
4. RED: input/output path equality is rejected.
5. GREEN: implement only the parser, overlap gate, record insertion and
   structured reports needed by those tests.
6. Run the complete new test module and relevant Sky130 adapter tests.

## Experiment Flow

```text
baseline pinned_shapes GDS
-> add one p+ substrate tap stack
-> structural GDS audit
-> Magic DRC
-> Magic extraction
-> direct .ext/substrate/equiv inspection
-> MOS-only LVS preparation
-> Netgen only if extraction preserves useful ports/devices
-> diagnostics/trust decision
```

Every output goes under:

```text
generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/
```

## Acceptance And Stop Gates

### Structural gate

- Input GDS unchanged.
- Added stack has the expected layers and no forbidden overlap.
- GDS remains parseable.

### DRC gate

- Preserve the raw Magic DRC log and count.
- A DRC failure does not invalidate the diagnostic, but forbids any closure or
  trust upgrade.

### Extraction gate

Record all of:

- extracted top ports;
- MOS count;
- substrate record;
- equivalence records;
- M11 and M23 extracted terminals;
- unknown layer/datatype warnings.

The hypothesis receives support only if substrate identity moves from `vout`
toward `gnda` and the existing vout-to-supply equivalences improve without
deleting devices or ports.

### LVS gate

Run Netgen only after a usable extracted netlist exists. A pass requires the
direct report to state a unique match. Equal device counts alone are not a
pass.

### Stop gate

Stop after this one A/B and Codex review. Do not add more taps, edit NMOS
primitives, change C0, run post-layout simulation/PVT, or modify Harness reward
logic in the same task.

## Trust Policy

Until independent DRC/LVS/PEX evidence succeeds:

```text
usable_for_reward=false
usable_for_post_sim=false
usable_for_training=false
usable_for_parasitic_modeling=false
usable_only_as_failure_case=true
```

Even a successful substrate experiment remains diagnostic because the bounded
C0 proxy is not yet proven electrically equivalent to the original 5 pF
capacitor.
