# Original Fan_SMC Baseline Audit

## Identity

| Field | Value |
| --- | --- |
| Task | `AH-SMC-001` |
| Circuit | Original Fan_SMC/Fan_SMC_Pin_3 with C0 present |
| Evidence root | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3` |
| Audited extraction | `magical_case/sky130_pipeline/extract_v2` |
| Evidence class | Local artifacts plus generated local diagnostics |
| Evidence scope | Unknown; no direct original-C0 LVS report |

The `smc09_no_c0` branch is excluded from baseline status. It is used only as
a differential diagnostic control.

## Artifact Table

| Stage | Absolute path | Class | Audited result |
| --- | --- | --- | --- |
| Raw source | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/fan_smc_pin_3_raw.spice` | local artifact | C0 connects `net050` to `VOUT` through the raw capacitor variable. |
| Converted source | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/fan_smc_pin_3_magical.sp` | local artifact | C0 is a `cfmom_2t` instance between `net050` and `VOUT`. |
| MAGICAL case source | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/fan_smc_pin_3.sp` | local artifact | C0 remains `cfmom_2t(net050, vout)`. |
| Case config | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/fan_smc_pin_3.json` | local artifact | Power names are `vdda`/`gnda`; `net31` and M4 symmetry exclusions are recorded. |
| Original route GDS | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/fan_smc_pin_3.route.gds` | local artifact | Flattened top cell; raw C0 token present, no SREF identity, `net050` token absent. |
| Remapped GDS | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/fan_smc_pin_3.sky130.gds` | local artifact | 17 layer pairs remapped, 12 TBD pairs preserved; all original text dropped. |
| Pinned-shapes GDS | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/fan_smc_pin_3.pinned_shapes.gds` | local artifact | Five top labels/shapes restored; raw C0 token present but `net050` identity absent. |
| Extraction Tcl | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract_v2/magic_extract.tcl` | local artifact | Reads the pinned-shapes GDS and runs `extract all`/`ext2spice`. |
| Extraction log | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract_v2/magic_extract.log` | local artifact | Magic 8.3.483; 12 unknown layer/datatype errors; vout shorted to vdda and gnda. |
| Extracted SPICE | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/extract_v2/fan_smc_pin_3_flat.spice` | local artifact | Top ports are only `vinn vinp vout`; 24 MOS and 61 capacitors; no extracted `cfmom_2t`. |
| Device mapping | `/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/fan_smc_pin_3/magical_case/sky130_pipeline/smc_extracted_device_mapping.json` | local artifact | 24 source/24 extracted devices, but 23 body mismatches and 88 terminal mismatches; extracted body domains include vout. |
| Route GDS diagnostic | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_original_baseline/route_gds_structure.json` | generated local diagnostic | One source passive parsed; C0 token present, `net050` absent, flattened with zero references. |
| Remap GDS diagnostic | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_original_baseline/sky130_gds_structure.json` | generated local diagnostic | C0 token survives, but neither source passive terminal name is present. |
| Pinned GDS diagnostic | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_original_baseline/pinned_shapes_gds_structure.json` | generated local diagnostic | vout text restored; net050 remains absent. |

## C0 Trace

1. **Source:** C0 is explicitly present between `net050` and `vout` as a
   `cfmom_2t` proxy.
2. **Generated primitive:** `magical_case/gds/fan_smc_pin_3_C0.gds` exists.
3. **Flattened GDS:** the byte token `C0` remains, but there is no SREF and no
   `net050` text identity. Token presence is not passive connectivity proof.
4. **Magic extraction:** no `cfmom_2t` device is emitted. The line named `C0`
   in the extracted SPICE is an automatically numbered `1.31e-19 F` parasitic
   between `vinn` and an anonymous node, not the source capacitor.

Therefore the original source capacitor is not proven to survive as a
passive-aware extracted device or equivalent terminal pair.

## Verification Status

| Gate | Status | Evidence |
| --- | --- | --- |
| MAGICAL route | present with warnings | Route GDS and run log exist; the log records an earlier horizontal legalization infeasibility before continuing. |
| Magic DRC | unknown | No direct DRC log/count was found for this exact original-C0 stage. |
| Magic extraction | fail/diagnostic | Direct port-short warnings and missing power ports in extracted top-level subckt. |
| Netgen LVS | unknown | No direct Netgen report exists for this exact original-C0 stage. Magic port shorts are not relabeled as a Netgen LVS result. |
| PEX availability | present but topology-untrusted | Derived from raw extracted SPICE: 61 capacitors, 25.31421542 fF total. |
| Post-layout simulation | missing | No direct artifact found. |
| PVT | missing | No direct artifact found. |
| Passive-aware scope | unknown | Source C0 terminal/device identity is not proven in extracted output. |

## Replay Recipe And Environment Result

The intended replay is:

```bash
source /home/qlf/IOT/scripts/env/magical_sky130_env.sh
mkdir -p <new-output-directory>
cp <extract_v2>/magic_extract.tcl <new-output-directory>/
cd <new-output-directory>
magic -dnull -noconsole \
  -rcfile "$SKY130A/libs.tech/magic/sky130A.magicrc" \
  magic_extract.tcl > magic_extract.log 2>&1
```

Fresh replay was not completed in the current restricted execution context:

- The environment `magic` wrapper requires Docker socket access, which was
  denied by the sandbox before Magic started.
- Explicit `/usr/bin/magic` is version 8.3.105, while the installed Sky130
  techfile requires at least 8.3.411. It reported incompatible tech syntax and
  then segfaulted.
- The historical extraction artifact was produced by Magic 8.3.483.

These are environment replay blockers, not evidence that the circuit itself
passed or failed a new run.

## Existing Differential Evidence

- Removing all met5 drawing geometry eliminates the explicit port-short
  warning, but also eliminates every top-level port from the extracted subckt.
  It is not a valid repair or LVS improvement.
- Removing nwell or tap geometry similarly changes port extraction and cannot
  establish a root cause by itself.
- The no-C0 B1 control deletes 118 `72/20` polygons in a bounded local region
  and preserves top ports, but also removes C0. It cannot distinguish the B1
  effect from the no-C0 effect on the original circuit.

## Provisional Trust Decision

| Field | Value |
| --- | --- |
| `usable_for_reward` | false |
| `usable_for_post_sim` | false |
| `usable_for_training` | false |
| `usable_for_parasitic_modeling` | false |
| `usable_only_as_failure_case` | true |

The PEX is parseable but topology-untrusted, DRC and Netgen LVS are unknown,
and post/PVT/passive evidence is missing. Unknown LVS is not claimed as a
direct Netgen mismatch.

## Ranked Root-Cause Hypotheses

1. **Power/topology collapse in translated layout:** strongest direct evidence.
   Magic shorts vout to both supplies, power ports disappear, and extracted MOS
   terminal/body mappings collapse heavily onto vout.
2. **Local met5 geometry contributes to the collapse:** medium evidence. Full
   met5 deletion removes the warnings but also destroys the port interface.
3. **C0 identity/terminal mapping is lost during flattened remap/extraction:**
   strong passive-specific evidence, but not yet proven to cause the supply
   collapse.
4. **Twelve preserved TBD layer pairs affect extraction semantics:** observed
   read errors, but no causal A/B evidence yet.

## First Single-Variable A/B Experiment

Apply the exact no-C0 B1 local `72/20` mask region to the original
`fan_smc_pin_3.sky130.gds` while keeping C0 and every other input unchanged.
Then run the same label, pin-shape, and extraction stages into a new output
directory.

The single changed variable is the bounded met5 drawing mask. Compare:

- vout-vdda/gnda short warnings;
- extracted top ports;
- 24 MOS preservation;
- source C0/passive terminal evidence;
- extracted net count and PEX count.

This experiment diagnoses whether B1 containment helps independently of C0
removal. It is not an architecture fix and cannot be promoted as closure.

## Do Not Claim

- Do not claim original Fan_SMC has a direct Netgen LVS failure artifact.
- Do not claim DRC clean; no direct DRC artifact was found.
- Do not identify the extracted parasitic named C0 as the source cfmom device.
- Do not treat full-M5 deletion or no-C0 as a valid original-circuit repair.
- Do not call the current PEX topology-trusted, post-simulation-safe, or
  training-safe.
