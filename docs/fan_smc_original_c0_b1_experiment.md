# Fan_SMC Original-C0 B1 Experiment

## Task

`AH-SMC-002`

## Hypothesis

The local met5 drawing geometry removed by the no-C0 B1 control contributes to
the vout-vdda/gnda collapse independently of C0 removal.

## Single Changed Variable

Delete `72/20` boundaries within `(-50000, -50000) - (200000, 200000)` from
the original-C0 remapped GDS. Source netlist, C0, remap, top-port labels,
pin-shape generation, extraction Tcl, PDK, and extraction settings remain the
same as the audited baseline.

## Prepared Local Artifacts

All outputs are under:

```text
/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/
fan_smc_original_c0_b1/
```

| Artifact | Status |
| --- | --- |
| `b1_report.json` | present; 1520 met5 boundaries deleted |
| `fan_smc_pin_3.original_c0.b1.gds` | present |
| `fan_smc_pin_3.original_c0.b1.pinned.gds` | present; five top labels added |
| `fan_smc_pin_3.original_c0.b1.pinned_shapes.gds` | present; five top pin shapes added |
| `gds_structure.json` | present; source C0 token retained, flattened top has no SREF identity |
| `magic_extract.tcl` | present |
| `fan_smc_pin_3_flat.ext` | not generated |
| `fan_smc_pin_3_flat.spice` | not generated |
| `magic_extract.log` | not generated |

The same coordinate region deleted 118 boundaries in the no-C0 GDS but 1520
in the original-C0 GDS. This difference is evidence that C0 materially changes
the geometry inside that region; it does not invalidate the single-variable
comparison against the original-C0 baseline.

## Execution Status

The geometry preparation completed, but the hypothesis was rejected before
Magic extraction. The repository GDS tracer reports that both the baseline and
B1 variants remain geometrically connected for `vout-vdda` and `vout-gnda`.
Path lengths and layer sequences are unchanged: 27 elements for vout-vdda and
33 elements for vout-gnda.

The current Codex sandbox could not run the Magic Docker wrapper, and host
Magic 8.3.105 is incompatible with the installed Sky130 techfile. Container
extraction was not pursued further because the bounded met5 mask did not alter
either target static path.

## Static A/B Result

| Pair | Baseline | B1 | Decision |
| --- | --- | --- | --- |
| vout-vdda | connected, path length 27 | connected, path length 27 | unchanged |
| vout-gnda | connected, path length 33 | connected, path length 33 | unchanged |

Artifacts are under `static_connectivity/` in the experiment directory. The
annotated baseline path associates vout-vdda with M11, whose source terminals
are `(vout, net050, vdda, vdda)` but whose extracted S/G/B/D terminals all
collapse to `vout` in the historical Magic artifact.

## Acceptance Measurements

After container extraction, compare against original `extract_v2`:

- whether vout-vdda and vout-gnda short warnings remain;
- extracted top-level port list;
- extracted MOS count;
- extracted capacitor count/total;
- whether source C0 terminal identity is recognized;
- whether power/body terminals still collapse onto vout.

No pass, LVS, DRC, PEX-trust, post-simulation, or training claim is made. The
local-met5 B1 hypothesis is rejected and should not be layered with more masks.
