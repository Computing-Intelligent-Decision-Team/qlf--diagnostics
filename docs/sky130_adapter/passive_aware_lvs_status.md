# Passive-Aware LVS/PEX Status

## Current State

The SMC analog harness can run the full MOS-only projection loop through:

- GRPO/front-end sizing proposal
- pre-layout ngspice simulation
- MAGICAL/Sky130 layout
- DRC
- MOS-only connectivity LVS
- Magic extraction and PEX summary
- post-layout ngspice simulation
- post-layout PVT sweep

The current best SMC candidate reaches `L6_post_layout_pvt`. As of the latest
repair pass, the passive evidence also includes a DRC-clean full-GDS native
passive trial for `cand_0031`:

- `best_passive_aware_scope=full_passive_inclusive_gds_lvs`
- `best_full_passive_inclusive_gds_lvs_proven=true`
- `best_native_passive_device_recognition_status=pass`
- `best_native_passive_retarget_full_native_passive_lvs_proven=true`
- `best_native_cap_replacement_terminal_bridge_status=m4_outside_stacks_inserted`
- `best_native_cap_replacement_drc_count=0`
- `best_native_cap_replacement_native_passive_netgen_status=pass`

The top-level config still carries the original default
`verification_scope=mos_only_projection`, but the best passive evidence packet
is now scoped as `full_passive_inclusive_gds_lvs`.

## 2026-06-19 Native Full-GDS Passive Repair

The native passive blockers for the SMC candidate have been repaired through a
controlled replacement/bridge trial:

1. Start from the DRC-clean route-bridge GDS:
   `resistor_remap_variants/xhigh_rb/rb.gds`.
2. Keep the formal/native resistor retarget result: 31
   `sky130_fd_pr__res_xhigh_po` segments for `xr0`, with Netgen pass.
3. Generate a same-cell native Sky130 MIM cap replacement for
   `SMCNR_SE_2st_AMP_xc0` using `sky130_fd_pr__cap_mim_m3_1`.
4. Replace the flattened `xc0` MOM region in the full routed GDS, preserving
   original route pin boxes.
5. Bridge the replacement cap terminals with `m4_outside_stacks`: M1-M4 stacks
   are placed outside the M3 plate bbox, and short M4 straps connect to the
   generated MIM plates.
6. Rerun Magic extraction, DRC, and native passive retarget Netgen.

Canonical evidence is stored at:

`generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_existing_gds/resistor_remap_variants/native_cap_full_gds_trial/native_cap_full_gds_trial_summary.json`

That summary reports:

- `status=pass`
- `drc_status=pass`
- `drc_count=0`
- `native_capacitor_device_recognition_status=pass`
- extracted native capacitor:
  `X30 outn net027 sky130_fd_pr__cap_mim_m3_1 l=10.3 w=10.95`
- `native_resistor_chain_status=pass`
- `native_resistor_chain_device_count=31`
- `native_passive_netgen_status=pass`
- `full_native_passive_lvs_proven=true`
- `verification_scope=full_passive_inclusive_gds_lvs`

Historical sections below are retained because they explain how the failure was
localized. Their older statements that `xc0` was only plate-coupling evidence
or that full passive-inclusive GDS LVS was unproven are superseded by this
native full-GDS trial.

## 2026-06-19 Native Passive Capability Gate

A new static capability probe is now part of the passive evidence path:

`generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_existing_gds/resistor_remap_variants/native_passive_capability/native_passive_capability_summary.json`

The probe scans the source netlist plus the local Sky130 Magic tech and Netgen
setup files. For current `SMCNR_SE_2st_AMP` it reports:

- `source_model_native_status=fail`
- `direct_source_model_support=false`
- unsupported source models: `rppolywo_m`, `cfmom_2t`
- `native_retarget_available=true`
- resistor retarget candidates include `sky130_fd_pr__res_xhigh_po`
- capacitor retarget candidates include `sky130_fd_pr__cap_mim_m3_1` and
  `sky130_fd_pr__cap_mim_m3_2`
- `native_retarget_requires_geometry_replacement=true`
- `can_fix_current_gds_by_layer_remap_only=false`

This is the key distinction for the remaining native LVS work. The current
formal abstraction flow is valid as a source-equivalent R/C LVS abstraction,
but it is not native Magic/Netgen recognition of the existing MAGICAL
`rppolywo_m` and `cfmom_2t` GDS. Native LVS requires retargeting both the source
models and generated passive geometry to Sky130 PDK primitives.

The same probe also checks whether this repo contains the MAGICAL passive
generator source files required to implement that retarget in-place. The
`device_generation` submodule is now initialized and the probe sees
`device_generation/device_generation/Resistor.py` and
`device_generation/device_generation/Capacitor.py`. The final repair for
`cand_0031` did not patch the generator in-place; it uses a controlled
post-generation native passive replacement and terminal bridge trial, recorded
above as `native_cap_full_gds_trial`.

As of the latest diagnostic run, the WSL tool issue is fixed: the pipeline can
use `/usr/bin/netgen-lvs` from `Ubuntu-24.04`, with Magic available at
`/usr/local/bin/magic`. The case pipeline now also auto-discovers the local
AnalogGym Sky130 PDK at
`../Analoggym_opt_moo_Mahalanobis_paper/mosfet_model/sky130_pdk` when the
legacy `/home/to/.ciel/.../sky130A` path is absent. The earlier remaining
blocker was full passive-inclusive GDS connectivity; the native full-GDS trial
above resolves that blocker for `cand_0031`.

The source-equivalent passive abstraction packet is ready for use as a formal
abstraction artifact:

`generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_existing_gds/resistor_remap_variants/xhigh_po_second_stage_abstraction_packet_verification_summary.json`

That summary records `formal_lvs_abstraction_ready=true`,
`all_source_passives_have_candidate=true`, and no unresolved abstraction-packet
blockers. This means the segmented resistor chain and MOM capacitor are covered
by source-equivalent candidates. That formal packet alone is not the native
full-GDS proof; the native full-GDS proof is the separate
`native_cap_full_gds_trial` evidence recorded above.

## Historical Native Retarget Progress

This section records the intermediate state before the native full-GDS repair.
It is retained to explain the path to the final fix; current status is the
`native_cap_full_gds_trial` pass described above.

The harness records native retarget evidence separately from formal R/C
abstraction:

- `xr0` native resistor-chain retarget is proven at the Netgen level. The
  native trial keeps `sky130_fd_pr__res_xhigh_po` devices, generates a
  31-segment resistor chain, and Netgen reports a unique match after series
  merging.
- At this intermediate point, `xc0` was not yet a native LVS-recognized
  capacitor in the full candidate extraction. That limitation is now superseded:
  the final full-GDS trial extracts `xc0` as
  `sky130_fd_pr__cap_mim_m3_1`.
- A new Sky130 native capacitor gencell probe proves that the local PDK and
  Magic can generate and extract `sky130_fd_pr__cap_mim_m3_1`; the extracted
  standalone netlist contains a native `sky130_fd_pr__cap_mim_m3_1` device.
- A replacement candidate for `SMCNR_SE_2st_AMP_xc0` is generated as a same-name
  Sky130 MIM capacitor cell, sized from the original `xc0` bbox. The final
  repair merged this candidate into the routed top GDS, inserted
  `m4_outside_stacks` terminal bridges, reran extraction/DRC, and proved `xc0`
  appears as a native `sky130_fd_pr__cap_mim_m3_1` device.

This historical section previously kept
`best_full_passive_inclusive_gds_lvs_proven=false` and
`best_native_capacitor_device_recognition_status=fail`. Those values are now
superseded by the current top-level summary, which reports both as pass/true
through the full-GDS native passive trial.

## What The Passive Probe Proves

The separate `passive_aware_lvs` probe now emits a
`passive_integrity_report.md` for each full-extraction attempt. For the current
SMC case it shows:

- Source netlist contains two intentional passives: `xr0` (`rppolywo_m`) and
  `xc0` (`cfmom_2t`).
- MAGICAL generates both passive device GDS files:
  `SMCNR_SE_2st_AMP_xr0.gds` and `SMCNR_SE_2st_AMP_xc0.gds`.
- The original non-experimental remap did not preserve intentional passives in
  the extracted raw netlist.
- LVS preparation drops two source passive devices because full passive
  connectivity matching is not implemented.
- A follow-up experimental remap probe on the existing `cand_0031` pinned GDS
  remapped the passive datatype-specific layers and removed the previous Magic
  unknown-layer messages.
- That experimental extraction produced eight physical generic resistor devices
  (`sky130_fd_pr__res_generic_m1..m4`) but still did not preserve the two source
  passive instances (`xr0`, `xc0`) as LVS-matchable devices.
- A GDS structure diagnostic now shows why this is not enough for LVS:
  the remapped top GDS is already flattened (`SREF/AREF count = 0`), contains no
  `xr0` or `xc0` strings, and preserves only two of the four source passive
  terminal names (`gnda`, `vout`; not `net027` or `outn`). The generated passive
  GDS files exist, but neither contains text labels.
- A placement/routing identity reconstruction diagnostic now recovers the source
  passive pin identity from MAGICAL intermediates:
  `xr0/net027`, `xr0/vout`, `xc0/outn`, and `xc0/net027` all have exact matches
  between placed `.pin` boxes and source-net `.gr` route rectangles. The only
  source passive terminal without a pin box is `xr0/gnda`, which is also absent
  in MAGICAL's `.pin` geometry for that device.
- The same report emits four experimental Magic label-injection candidates:
  `net027` and `vout` on `li1`, plus `outn` and `net027` on `met1`. These are
  derived from route-layer identity (`M1 -> li1`, `M2 -> met1`), not from a
  proven extraction run yet.
- A follow-up label-injection extraction experiment now proves partial terminal
  recovery. The harness fallback probe now runs this automatically after
  identity reconstruction: it injects the four reconstructed labels and
  pin-purpose boxes into the experimental passive GDS, reruns Magic extraction,
  reruns GDS/LVS-preparation diagnostics, and writes a terminal recovery report.
  Magic extraction emits source terminal names on physical passive devices for
  `net027` and `outn`. It still does not recover `vout` or `gnda` on extracted
  physical passive devices, so the result is
  `physical_passives_partially_recover_source_terminals`, not full passive-aware
  LVS.

This means the passive devices are not missing from MAGICAL output; they are
now partially recovered at the Sky130 extraction boundary. Source-instance
preservation is still not native in Magic extraction, but formal LVS
abstraction is now available through the packet-based R/C rewrite described
below.

## Latest Experimental Probe

The current passive-only remap probe is stored at:

`generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_remap_probe`

The same flow is now also available through the harness fallback probe at:

`generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_existing_gds`

It reuses the existing `cand_0031` pinned GDS rather than rerunning MAGICAL
routing, applies `--allow-experimental`, and then runs Magic extraction. The
important evidence is:

- `experimental_passive_remap_report.md`: `RPDMY 115/1`, `RH 117/0`,
  `MRDMY 150/2..5`, `TSV_PPI 155/2,3,4,5,27,100`, and `LVS_DUMMY 208/1`
  are remapped to experimental Sky130 target layers.
- `magic_extract_experimental_passive.log`: no passive-related unknown
  layer/datatype messages are reported.
- `SMCNR_SE_2st_AMP_experimental_passive_extracted.spice`: Magic emits generic
  resistor devices on metal resistor layers.
- `passive_integrity_experimental_remap_report.md`: the probe is still marked
  not proven because extracted physical passives are not mapped back to source
  instances and LVS preparation has not preserved the source passives.
- `layout_passive_existing_gds/passive_integrity_report.md`: harness-generated
  fallback evidence with the same conclusion, using
  `passive_probe_mode=existing_pinned_gds_extraction`.
- `layout_passive_existing_gds/passive_lvs_preparation_diagnostic.md`: explains
  that physical passive devices were extracted but source passive terminals were
  not recovered.
- `layout_passive_existing_gds/passive_gds_structure_diagnostic.md`: explains
  that the flattened top GDS no longer carries source passive instance names or
  internal passive-terminal labels.
- `layout_passive_existing_gds/passive_identity_reconstruction_report.md`:
  proves that source passive pin identity can still be reconstructed from
  `.pin`, `.gr`, and `run_SMCNR_SE_2st_AMP_trial.log`, even though Magic's
  extracted passive devices do not carry those source terminal names.
- `layout_passive_existing_gds/passive_identity_label_injection_report.md`:
  records the four injected labels/pin-purpose boxes.
- `layout_passive_existing_gds/SMCNR_SE_2st_AMP_identity_labels_extracted.spice`:
  Magic extraction after label injection. This netlist includes `R1 net027_uq0
  net027 ...` and `R5 outn vdda ...`, showing partial source-terminal recovery.
- `layout_passive_existing_gds/passive_identity_label_lvs_preparation_diagnostic.md`:
  classifies the label-injected extraction as partial recovery, with covered
  terminals `net027`, `outn` and missing terminals `gnda`, `vout`.
- `layout_passive_existing_gds/passive_identity_label_terminal_recovery_report.md`:
  harness-generated structured evidence for the same labelled extraction. It
  records covered terminals `net027`, `outn`, missing terminals `gnda`, `vout`,
  the `net027/net027_uq0` split candidate, and the Magic `gnda/vdda` port short.
- `layout_passive_existing_gds/passive_identity_label_abstraction_readiness_report.md`:
  harness-generated abstraction-readiness evidence. It classifies the current
  label-injected extraction as `partial_passive_abstraction_readiness`, with
  zero source passives ready for abstraction, two source passives with partial
  terminal recovery, and seven concrete blockers after coordinate ownership is
  enabled. The `.ext` coordinate parser finds eight `devres` devices and all
  eight map to the `xc0` passive pin boxes; none map to `xr0`. For `xr0`, `vout`
  appears only through non-resistor parasitic capacitance and is still missing
  from expected resistor devices; `gnda` also has no MAGICAL passive pin
  geometry, and there is no coordinate-matched extracted resistor for the source
  resistor instance. For `xc0`, both terminal names appear and all coordinate
  matched `devres` markers sit in the MOM capacitor region, but there is no
  direct extracted capacitor between `outn` and `net027`; the recovered source
  terminals touch resistor-marker fragments rather than a recognized MOM
  capacitor device.
- The abstraction analyzer now also reconstructs conservative MOM capacitor
  plate-coupling evidence from `.ext devres` ownership and extracted parasitic
  capacitors. For `xc0`, the current label-injected extraction finds four
  cross-plate capacitors between the `outn` and `net027` plate-node sets,
  totaling about `539.84 fF`. It exports a diagnostic source-equivalent
  candidate `xc0 outn net027 cfmom_2t`, marked
  `candidate_requires_review` because this is a PEX coupling abstraction, not a
  recognized `cfmom_2t` LVS device.

## Second-Stage Resistor Remap Experiment

The resistor remap variants are stored under:

`generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_existing_gds/resistor_remap_variants`

The harness fallback probe now runs these variants automatically when
`verification.passive_aware.run_resistor_remap_variant_probe` is enabled. The
experiments start from the already Sky130-remapped experimental passive pinned
GDS and rewrite only the ambiguous resistor-marker layers:

- `xhigh_po_second_stage`: preserves `URPM 79/20` and rewrites `RPM 86/20` to
  `NPC 95/20`. Magic extracts 31 `sky130_fd_pr__res_xhigh_po` `rsubckt`
  fragments. The updated abstraction analyzer maps 28 passive `rsubckt`
  fragments back to `xr0` and 3 to `xc0`. It also proves a 31-segment
  resistor-chain path from `net027` to `vout`. `xr0` now covers `gnda`,
  `net027`, and `vout` on expected-kind resistor evidence, but remains blocked
  by `body_or_substrate_pin_has_no_magical_geometry:gnda` and
  `source_resistor_requires_segmented_chain_abstraction`. The analyzer exports
  a diagnostic candidate fragment at
  `xhigh_po_second_stage_abstraction_candidates.spice` containing the
  source-equivalent line `xr0 net027 vout gnda rppolywo_m`, marked
  `candidate_requires_review`.
- `generic_po_second_stage`: rewrites both `URPM 79/20` and `RPM 86/20` to
  `NPC 95/20`. Magic extracts 31 `sky130_fd_pr__res_generic_po` `rsubckt`
  fragments. The analyzer maps 27 passive `rsubckt` fragments back to `xr0`
  and 4 to `xc0`, and proves the same 31-segment `net027` to `vout` resistor
  chain. It exports the same source-equivalent diagnostic candidate in
  `generic_po_second_stage_abstraction_candidates.spice`, with the same
  remaining `xr0` blockers as the `xhigh` variant.
- `high_po_second_stage`: preserves `RPM 86/20` and rewrites `URPM 79/20` to
  `NPC 95/20`. Magic does not extract `sky130_fd_pr__res_high_po`; the result
  falls back to the previous metal-resistor marker evidence and keeps the
  `no_coordinate_matched_extracted_resistor_for_source_instance` blocker.

For current `cand_0031`, the automatic variant summary chooses
`xhigh_po_second_stage` as the best variant:

- Variant probe status: `pass`
- Variants attempted: 3
- Successful variants: 3
- Best source-level abstraction candidates: 2
- Best segmented resistor-chain count: 1
- Best capacitor plate-coupling count: 1
- Best passive `rsubckt` count: 31
- Best passive `rsubckt` ownership: `xr0: 28`, `xc0: 3`
- Best blocker count: 5
- Best abstraction packet:
  `xhigh_po_second_stage_abstraction_packet.json`
- Best abstraction packet coverage: all source passives have source-equivalent
  candidates (`xr0`, `xc0`), with no missing source passive instances.
- Best abstraction packet proof status: `candidate_requires_review`, not full
  LVS proof. The source-equivalent lines are
  `xr0 net027 vout gnda rppolywo_m` and `xc0 outn net027 cfmom_2t`.

This narrows the likely resistor mapping to either `xhigh_po` or `generic_po`,
with `xhigh_po` currently the closer Sky130 primitive because it emits
`sky130_fd_pr__res_xhigh_po`. The formal abstraction verifier now collapses the
segmented `xr0` chain into a source-equivalent LVS resistor and collapses the
`xc0` plate-coupling evidence into a source-equivalent LVS capacitor. The
passive-only abstraction trial and the hybrid MOS-only-reference plus passive
abstraction trial pass Netgen, so harness evidence can report
`passive_aware_status=formal_abstraction_pass`. A fresh rerun using the
current WSL `netgen-lvs` and the AnalogGym PDK setup is stored at
`generated/analog_harness/smcnr_se_2st_amp/cand_0031/netgen_env_check/formal_hybrid_rerun`;
it reports 10 devices vs. 10 devices, including `r (1)` and `c (1)`, with
`Circuits match uniquely` and `Netlists match uniquely`. This is still not
native Magic/Netgen recognition of `rppolywo_m` or `cfmom_2t`, and it is not
full passive-inclusive GDS signoff.

## Latest Full-GDS Connectivity Blocker

Recent full-GDS experiments added several controlled knobs:

- `MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES`,
  `MAGICAL_LOCAL_VDD_STRIPE_Y_DBU`,
  `MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU`, and
  `MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU` for local VDD stripe placement.
- `MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_*` for router-only blockage around that
  local stripe.
- `MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_*` and
  `tools/sky130_adapter/add_local_power_stripe_to_gds.py` for post-route
  diagnostic stripe injection.

The best local-stripe attempts remove the previous `gnda/vdda` Magic port
short and keep top-level ports complete, but the extracted MOS network still
does not match the MOS-only reference. The persistent symptom is internal
MOS signal/supply corruption: `X5`, `X6`, and `X7` terminals that should remain
on internal nets are extracted on `vdda` in the full passive-remapped GDS.

The latest localization probes identify the upper-metal failure mode more
precisely. Five `met5` verticals overlap the top `vdda` stripe. Clipping all of
them removes the `outn`-to-`vdda` symptom but also cuts true pMOS supply/well
connections. Clipping only the two most suspicious signal trunks (`s0/s1`)
changes the extracted net from `vdda` to an internal `w_n115_2325#`, but that
internal net still contains local pMOS bulk/source roles, so it is not a valid
repair. Splitting only the top `vdda` drawing stripe has no effect because the
matching `met5` port-purpose boundary (`72/16`) also labels the stripe.
Splitting both `72/20` and `72/16` reproduces the same isolated mixed internal
net. Therefore the current full passive-inclusive GDS is not closed: the
problem is a route/port/well connectivity interaction, not just a stale label
or a missing LVS rule.

The latest native debug probe
`generated/analog_harness/smcnr_se_2st_amp/cand_0031/native_debug/remove_gnda_stack`
removed the suspicious `gnda` LI/metal/via stack at the `xm4` gate edge
without touching active/poly/implant geometry. Magic extraction still reports
MOS supply-role corruption: `xm4` gate remains on `vdda` and `xm3/x7` still
has an internal/source terminal on `vdda`. This rules out a single local
`gnda` stack as the whole root cause. A layer-strip sweep also shows that
removing individual experimental passive marker layers, or all of them
together, does not restore MOS connectivity. The remaining blocker is upstream
passive-inclusive routing/device geometry, not Netgen availability and not a
single remap-marker artifact.

The next real fix is a net-aware local supply/tap strategy in MAGICAL routing
or device generation, not another evidence relabel. Until that is implemented,
reports must label the passive probe as
`formal_passive_abstraction_with_gds_mos_bridge` only when the route-bridge DRC,
MOS-connectivity, and formal passive LVS gates pass. Candidate closure still
stays limited to the MOS-only projection/post-layout evidence, not native
full passive-aware LVS.

## Layer Findings

Per-device GDS remap debugging shows the passive-specific layers are split by
device:

- `xr0` resistor uses `RPDMY 115/1` and `RH 117/0` in addition to already
  mapped resistor/MOS/contact layers.
- `xc0` MOM capacitor uses `MRDMY 150/2..5` and `TSV_PPI 155/2..5,27,100` in
  addition to already mapped metal/via layers.

The Sky130 PDK contains relevant real layers such as:

- `RPM 86/20`
- `URPM 79/20`
- `POLYRES 66/13`
- `CAPID 82/64`
- `CAPM 89/44`
- `CAPM2 97/44`
- metal resistor marker layers such as `MET1RES 68/13` through `MET5RES 72/13`
- `RDL 74/20` and related RDL purposes

These are candidates only. They are not yet confirmed one-to-one mappings for
MAGICAL `RPDMY`, `RH`, `MRDMY`, `TSV_PPI`, or `LVS_DUMMY`.

## Tooling Added For The Next Step

`tools/sky130_adapter/remap_gds_to_sky130.py` now supports datatype-specific
mapping overrides. This is required because some MAGICAL passive layers use the
same internal layer number with multiple datatypes, for example:

- `MRDMY 150/2`
- `MRDMY 150/3`
- `MRDMY 150/4`
- `MRDMY 150/5`

The old remapper keyed only on the internal layer number, so it could not map
those cases to different Sky130 targets. The new support keeps default behavior
unchanged and only enables experimental entries when called with:

```bash
python tools/sky130_adapter/remap_gds_to_sky130.py \
  --input-gds path/to/input.gds \
  --output-gds path/to/output.gds \
  --export-map path/to/experimental_map.yaml \
  --report path/to/report.md \
  --allow-experimental
```

An export-map entry can use `datatype_overrides` with `status: experimental`.
Entries marked experimental are ignored unless `--allow-experimental` is set.

`tools/sky130_adapter/inspect_gds_structure.py` now generates a Markdown report
and JSON summary for top-GDS/passive-GDS structure. The harness fallback probe
uses it automatically and records fields such as:

- `passive_gds_top_ref_count`
- `passive_gds_top_text_count`
- `passive_gds_source_instance_names_present_count`
- `passive_gds_source_terminal_names_present_count`
- `passive_gds_generated_passive_gds_present_count`

`tools/sky130_adapter/reconstruct_passive_identity.py` now generates a
placement-aware passive identity manifest from MAGICAL intermediates. The
harness fallback probe records fields such as:

- `passive_identity_status`
- `passive_identity_exact_route_matches`
- `passive_identity_missing_route_matches`
- `passive_identity_pins_with_geometry`
- `passive_identity_pins_without_geometry`

For `cand_0031`, this status is
`source_passive_pin_identity_reconstructed_from_magical_intermediates`, with
four exact source-net route matches and four label-injection candidates.

`tools/sky130_adapter/add_passive_identity_labels_to_gds.py` now applies those
label-injection candidates to a GDS by inserting Sky130 label TEXT and
pin-purpose BOUNDARY records. This is currently an experimental probe: it
improves extraction naming but does not complete source-instance LVS.

`tools/sky130_adapter/analyze_passive_abstraction.py` now checks whether the
label-injected extracted netlist has enough source-terminal and expected
device-kind evidence to justify an LVS abstraction rule. It distinguishes
terminal names that appear only on unrelated parasitic capacitors from terminals
that appear on the expected extracted device kind. When a Magic `.ext` file and
passive identity manifest are provided, it maps both `device devres`
coordinates and passive `device rsubckt` coordinates back to reconstructed
source passive pin boxes. For current default `cand_0031`, this coordinate
ownership proves all eight extracted `devres` devices belong to `xc0`. In the
second-stage resistor-remap experiment, the same analyzer also maps recovered
poly-resistor `rsubckt` fragments back to `xr0`. It can also write a diagnostic
SPICE fragment with `--candidate-netlist`; this records source-level passive
abstraction candidates such as the segmented `xr0` chain, but deliberately
labels them as diagnostic artifacts rather than LVS pass evidence. For MOM
capacitors, it derives plate-node sets from coordinate-matched `.ext devres`
records, sums extracted parasitic capacitors that cross those plate-node sets,
and records this as PEX coupling evidence rather than a recognized capacitor
device.

The same analyzer can also write a structured abstraction packet with
`--packet-json`. This packet records `proof_status`,
`full_passive_aware_lvs_proven=false`, source-equivalent candidate netlist
lines, unresolved blockers, and source-instance coverage. For the current best
variant, the packet proves that both source passive instances have diagnostic
candidates, but the packet remains `candidate_requires_review` because the
resistor requires segmented-chain abstraction and the capacitor is still a
plate-coupling PEX abstraction rather than a recognized `cfmom_2t` LVS device.

`tools/sky130_adapter/verify_passive_abstraction_packet.py` now provides a
separate verification gate for these packets. It rereads the source netlist and
checks that each source passive has a matching source-equivalent candidate, that
the source-equivalent line matches the original source passive terminals/model,
and that each candidate has structural support evidence. For current
`xhigh_po_second_stage`, this verifier reports `candidate_requires_review`,
with all source passives covered and all candidate support verified. The
default label-injected packet fails this verifier because it covers `xc0` but
not `xr0`.

The verifier also emits passive-only source/candidate abstraction netlists for a
diagnostic Netgen trial. For current `xhigh_po_second_stage`, the harness now
runs this abstract comparison automatically; Netgen reports `PASS` on the two
R/C abstraction netlists. This proves that the source-equivalent abstraction
candidate is internally consistent under Netgen, but it is deliberately scoped
as `passive_abs_netgen_status=pass`, not as full layout-extracted passive-aware
LVS.

`tools/sky130_adapter/prepare_passive_aware_lvs_netlists.py` now prepares a
stronger diagnostic trial: MOS devices plus packet-derived passive
abstractions. It preserves source passives as simple R/C primitives, removes
extracted passive fragments and parasitic capacitors from the Magic extraction,
then injects the packet-derived source-equivalent passive candidates into the
extracted netlist. For current `xhigh_po_second_stage`, this preparation
succeeds with `ready_for_netgen_trial`; Netgen then runs and reports `FAIL`.
The failure is now narrower: both sides have 10 devices with matching classes
(`nfet=3`, `pfet=5`, `r=1`, `c=1`), but the netlists still have a network
mismatch (`10` source nets vs `11` extracted nets). The report also shows the
extracted `gnda` top node is disconnected and that several MOS/internal nets
still need the same terminal/net-abstraction work before a full passive-aware
LVS pass can be claimed.

`tools/sky130_adapter/compare_mos_connectivity.py` now records this remaining
failure as an explicit MOS-network diagnostic instead of leaving it only inside
the Netgen report. The harness compares the full passive-remapped extraction
against the already-passing MOS-only projection reference and records:

- `passive_resistor_variant_best_passive_aware_mos_connectivity_status`
- `passive_resistor_variant_best_passive_aware_mos_connectivity_reason`
- `passive_resistor_variant_best_passive_aware_mos_connectivity_summary_json`
- `passive_resistor_variant_best_passive_aware_mos_connectivity_report`

For current `cand_0031` and best variant `xhigh_po_second_stage`, the diagnostic
status is `supply_or_internal_net_mismatch`. The structured summary reports
that the candidate `gnda` net has no MOS terminal roles, three nFET bulks and
two nFET sources are tied to `vdda`, Netgen reports `gnda` as disconnected, and
Netgen reports a net-count mismatch of `10` source nets vs `11` extracted nets.
This is now the strongest localized blocker for full passive-aware LVS.

The MOS connectivity comparator now also writes
`role_signature_match_suggestions`. This does not relax the pass/fail gate; it
lists the closest candidate net-role signatures for each missing reference net
so the next physical repair can target concrete corrupted nets instead of
guessing from raw SPICE text.

The latest supply-short localization narrows this further. Magic reports
`Ports "gnda" and "vdda" are electrically shorted` before Netgen sees the full
passive-remapped extraction. The harness now records this as:

- `magic_port_short_count`
- `magic_supply_short_present`
- `passive_resistor_variant_best_magic_port_short_count`
- `passive_resistor_variant_best_magic_supply_short_present`
- `passive_resistor_variant_best_magic_port_shorts`

For current `cand_0031`, both the base existing-pinned-GDS passive probe and
the best `xhigh_po_second_stage` variant report one supply short:
`gnda` shorted to `vdda`.

`tools/sky130_adapter/remap_gds_to_sky130.py` now supports
`--exclude-input-pair LAYER:DATATYPE`, which allows controlled leave-one-out
remap experiments without editing the export-map YAML. Using that option, the
current generated exclusion probes show:

- excluding any single experimental passive pair does not remove the
  `gnda/vdda` short;
- excluding whole passive marker families (`RPDMY/RH`, `MRDMY`, `TSV_PPI`,
  `LVS_DUMMY`) does not remove the short;
- excluding all currently experimental passive pairs does not remove the short;
- direct Magic extraction of
  `case/SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds` already reports the same
  `gnda/vdda` short;
- confirmed-only remap of that full candidate GDS also reports the same short.

The generated probe artifacts are:

- `layout_passive_existing_gds/passive_remap_exclusion_probe/passive_remap_exclusion_probe_summary.json`
- `layout_passive_existing_gds/passive_remap_exclusion_probe/passive_remap_exclusion_group_probe_summary.json`
- `layout_passive_existing_gds/passive_remap_exclusion_probe/passive_remap_baseline_probe_summary.json`

This means the remaining blocker is earlier than Netgen and earlier than the
second-stage passive marker remap variants. The full candidate pinned GDS has a
physical supply short when Magic extracts it. The most likely next repair path
is to fix passive device geometry/pin integration or regenerate the full-passive
layout so `xr0/xc0` conductor geometry does not bridge the global supplies.

`tools/sky130_adapter/strip_passive_geometry_from_gds.py` now provides a more
targeted geometry localization diagnostic. It computes placed passive-instance
bboxes from the MAGICAL placement log and generated passive GDS files, then
writes stripped diagnostic GDS files using five modes:

- `contains`: remove elements fully contained inside the passive placement bbox;
- `intersects`: remove elements touching the passive placement bbox;
- `crossing`: remove only elements that touch the passive placement bbox but
  are not fully contained by it.
- `clip-crossing`: remove only the overlap between a crossing rectangle and the
  passive placement bbox, preserving outside fragments.
- `crop-crossing`: keep only the overlap between a crossing rectangle and the
  passive placement bbox, deleting outside fragments.

The same tool also accepts `--strip-box-json`, so a diagnostic can cut against a
specific non-passive bbox such as the top VDD power stripe while still limiting
the edit to selected crossing elements.

For current `cand_0031`, the `contains_margin_0` strip removes 1604 elements
but Magic still reports `gnda/vdda` short. The `intersects_margin_0` strip
removes 1611 elements and the short disappears. The difference is exactly seven
crossing elements:

- four `72/20/BOUNDARY` met5 drawing vertical elements;
- one `67/20/BOUNDARY` li1 drawing element;
- two `68/20/BOUNDARY` met1 drawing elements.

The strongest current diagnostic is `crossing_margin_0`: it removes only those
seven crossing elements, keeps the passive-internal geometry, and Magic no
longer reports a `gnda/vdda` short. However, the crossing-stripped extraction
still fails MOS/internal-net LVS (`mos_internal_net_mismatch`), and the
MOS+packet-passive Netgen trial still fails. This proves that the supply short
is localized to crossing route/power geometry around `xr0/xc0`, but it does not
prove full passive-aware LVS.

The generated strip artifacts are:

- `layout_passive_existing_gds/passive_geometry_strip_probe/passive_geometry_strip_margin_probe_summary.json`
- `layout_passive_existing_gds/passive_geometry_strip_probe/passive_geometry_crossing_repair_probe_summary.json`
- `layout_passive_existing_gds/passive_geometry_strip_probe/crossing_margin_0/crossing_margin_0_strip_summary.json`

The harness also records a hybrid MOS+passive abstraction trial. This uses the
already-passing MOS-only projection extracted netlist as the MOS side, then
injects the same `xhigh_po_second_stage` passive abstraction packet. For current
`cand_0031`, this hybrid trial reports Netgen `PASS` with 10 source devices,
10 extracted devices, 10 source nets, and 10 extracted nets. This is important
positive evidence: the passive abstraction can compose with a proven MOS LVS
network. It is still not full passive-aware LVS, because the MOS network comes
from the MOS-only projection extraction rather than the full passive-remapped
extraction.

The harness fallback path in `tools/analog_harness/layout.py` now calls this
label-injection probe automatically when
`verification.passive_aware.run_passive_identity_label_probe` is enabled. The
generated evidence fields include:

- `passive_identity_label_probe_status`
- `passive_identity_label_recovery_status`
- `passive_identity_label_covered_source_terminal_count`
- `passive_identity_label_missing_source_terminal_count`
- `passive_identity_label_split_net_count`
- `passive_identity_label_magic_port_short_count`
- `passive_identity_label_abstraction_status`
- `passive_identity_label_abstraction_readiness_status`
- `passive_identity_label_source_passives_candidate_for_abstraction`
- `passive_identity_label_source_passives_with_partial_terminal_recovery`
- `passive_identity_label_source_resistors_with_segmented_chain`
- `passive_identity_label_source_capacitors_with_plate_coupling_evidence`
- `passive_identity_label_source_level_abstraction_candidate_count`
- `passive_identity_label_abstraction_packet_proof_status`
- `passive_identity_label_full_passive_aware_lvs_proven`
- `passive_identity_label_abstraction_packet_unresolved_blocker_count`
- `passive_identity_label_abstraction_packet_verification_status`
- `passive_identity_label_abstraction_packet_all_source_passives_have_candidate`
- `passive_identity_label_abstraction_packet_all_candidate_support_verified`
- `passive_identity_label_abstraction_blocker_count`
- `passive_identity_label_ext_devres_count`
- `passive_identity_label_ext_devres_by_source_instance`
- `passive_identity_label_ext_passive_rsubckt_count`
- `passive_identity_label_ext_passive_rsubckt_by_source_instance`
- `magic_port_short_count`
- `magic_supply_short_present`
- `passive_geometry_strip_supply_short_removed_by_count`
- `passive_geometry_crossing_strip_element_count`
- `passive_geometry_crossing_strip_supply_short_present_after`
- `passive_geometry_crossing_strip_mos_connectivity_status_after`
- `passive_resistor_variant_probe_status`
- `passive_resistor_variant_best_variant`
- `passive_resistor_variant_best_magic_port_short_count`
- `passive_resistor_variant_best_magic_supply_short_present`
- `passive_resistor_variant_best_magic_port_shorts`
- `passive_resistor_variant_best_source_level_abstraction_candidate_count`
- `passive_resistor_variant_best_source_resistors_with_segmented_chain`
- `passive_resistor_variant_best_source_capacitors_with_plate_coupling_evidence`
- `passive_resistor_variant_best_ext_passive_rsubckt_count`
- `passive_resistor_variant_best_ext_passive_rsubckt_by_source_instance`
- `passive_resistor_variant_best_abstraction_packet_json`
- `passive_resistor_variant_best_abstraction_candidates`
- `passive_resistor_variant_best_abstraction_packet_verification_status`
- `passive_resistor_variant_best_abstraction_packet_verification_json`
- `passive_resistor_variant_best_abstraction_source_passive_abs_netlist`
- `passive_resistor_variant_best_abstraction_candidate_passive_abs_netlist`
- `passive_resistor_variant_best_passive_abs_netgen_status`
- `passive_resistor_variant_best_passive_abs_lvs_result_summary`
- `passive_resistor_variant_best_passive_abs_netgen_report`
- `passive_resistor_variant_best_passive_aware_lvs_trial_prepare_status`
- `passive_resistor_variant_best_passive_aware_lvs_trial_netgen_status`
- `passive_resistor_variant_best_passive_aware_lvs_trial_result_summary`
- `passive_resistor_variant_best_passive_aware_mos_connectivity_status`
- `passive_resistor_variant_best_passive_aware_mos_connectivity_reason`
- `passive_resistor_variant_best_passive_aware_mos_connectivity_summary_json`
- `passive_resistor_variant_best_passive_aware_mos_connectivity_report`
- `passive_resistor_variant_best_hybrid_mos_passive_lvs_trial_prepare_status`
- `passive_resistor_variant_best_hybrid_mos_passive_lvs_trial_netgen_status`
- `passive_resistor_variant_best_hybrid_mos_passive_lvs_trial_result_summary`
- `passive_resistor_variant_best_all_source_passives_have_candidate`
- `passive_resistor_variant_best_missing_source_passive_instances`
- `passive_netgen_available`
- `passive_netgen_lvs_available`

The corresponding artifact path is recorded as
`passive_identity_label_abstraction_candidates`; the structured packet is
recorded as `passive_identity_label_abstraction_packet_json`. The automatic
resistor-variant summary is recorded as
`passive_resistor_variant_probe_summary_json`, and the best variant packet is
recorded as `passive_resistor_variant_best_abstraction_packet_json`. The best
variant packet verification is recorded as
`passive_resistor_variant_best_abstraction_packet_verification_json`. The
passive-only abstract Netgen trial is recorded as
`passive_resistor_variant_best_passive_abs_lvs_result_summary` and
`passive_resistor_variant_best_passive_abs_netgen_report`. The stronger
MOS+passive diagnostic trial is recorded as
`passive_resistor_variant_best_passive_aware_lvs_trial_result_summary`. The
MOS-network comparison for that full passive-remapped trial is recorded as
`passive_resistor_variant_best_passive_aware_mos_connectivity_summary_json` and
`passive_resistor_variant_best_passive_aware_mos_connectivity_report`. The hybrid
MOS-only-projection plus passive-abstraction trial is recorded as
`passive_resistor_variant_best_hybrid_mos_passive_lvs_trial_result_summary`.

## Formal Passive Abstraction Update

`netgen-lvs` is now installed in the `Ubuntu-24.04` WSL environment and the
pipeline scripts prefer `netgen-lvs` over the plain `netgen` binary. This matters
because Ubuntu's `netgen` package is the unrelated 3D meshing tool; IC LVS must
use `netgen-lvs`. Netgen invocation now uses a generated Tcl file
(`netgen-lvs -batch source <script.tcl>`) so the Debian `netgen-lvs` argument
expansion does not split `{file topcell}` pairs. The harness and GDS-subset
diagnostic scripts now also resolve WSL distro selection explicitly: configured
`layout.wsl_distro`, `MAGICAL_WSL_DISTRO`/`SKY130_WSL_DISTRO`, or the first
non-`docker-desktop` distro from `wsl -l -q`. This fixes the failure mode where
Windows defaulted to `docker-desktop`, making `magic`/`netgen-lvs` look
unavailable even though they exist in `Ubuntu-24.04`.

The best `xhigh_po_second_stage` packet now verifies as
`formal_lvs_abstraction_verified`:

- `xr0`: the 31-device `sky130_fd_pr__res_xhigh_po` segmented resistor chain is
  formally collapsed to `R_xr0 net027 vout 1` for LVS.
- `xc0`: the `cfmom_2t` plate-coupling evidence is formally collapsed to
  `C_xc0 outn net027 1f` for LVS.
- The formal verifier reports `remaining_unresolved_blockers=[]`.

The passive-only formal abstraction Netgen trial passes uniquely:

- `layout_passive_existing_gds/resistor_remap_variants/formal_passive_abs_netgen/netgen_lvs.out`
- `layout_passive_existing_gds/resistor_remap_variants/formal_passive_abs_netgen/lvs_result_summary.md`

This fixes the earlier "segmented resistor chain is only diagnostic" and
"cfmom_2t is only plate-coupling PEX evidence" issues at the formal abstraction
layer. It still does not claim native Magic/Netgen recognition of the original
source passive devices.

## Clip-Crossing and Hybrid Update

`tools/sky130_adapter/strip_passive_geometry_from_gds.py` now supports
`--mode clip-crossing`. Unlike the earlier `crossing` repair, this mode cuts only
the rectangle area overlapping a passive placement bbox and preserves the
outside fragments of the same route/power element. The `cand_0031`
`clip_crossing_margin_0` probe clipped the same seven crossing elements into
eleven retained fragments:

- clipped layers: `67/20/BOUNDARY`, `68/20/BOUNDARY`, `72/20/BOUNDARY`;
- stripped elements: `0`;
- Magic extraction completed without a `gnda`/`vdda` electrically-shorted port
  warning.

The clipped full-GDS formal passive-aware trial still does not pass Netgen:

- devices: source `10`, extracted `10`;
- nets: source `10`, extracted `13`;
- LVS status: `FAIL`;
- MOS connectivity status: `mos_internal_net_mismatch`.

The remaining physical mismatch is dominated by pFET source/bulk connectivity in
the passive-inclusive full GDS. In the clipped extraction, only one pFET bulk is
on `vdda`; several pFET source/bulk terminals are on `gnda` or anonymous
internal well nets. This is not a passive R/C abstraction failure.

The `xhigh_po_second_stage` hybrid trial was regenerated after the formal packet
verifier update. It uses the MOS-only projection extraction plus the formal
source-equivalent passive R/C abstraction and passes Netgen uniquely:

- prepare status: `ready_for_netgen_trial`;
- `formal_lvs_abstraction_ready=true`;
- `abstraction_scope=source_equivalent_passive_lvs_abstraction`;
- hybrid LVS status: `PASS`, devices `10` vs `10`, nets `10` vs `10`.

This hybrid PASS is useful evidence for the abstraction layer, but it is not a
full passive-inclusive GDS signoff because the MOS network comes from a
separately regenerated MOS-only projection layout.

## Actual Full-Probe Update

The actual `layout_passive_aware` run now reaches `connectivity_lvs` rather than
stopping at MAGICAL placement/routing:

- DRC: `0`
- failed stage: `connectivity_lvs`
- full-extraction raw ports before repair: `vdda vin vip ibias vout`
- Magic extraction warning: `gnda` and `vdda` are electrically shorted
- source/extracted MOS device count: `8` vs `8` in plain connectivity LVS

The harness now removes stale MOS-only `lvsNetRenames` from the passive probe
config. It also enters the existing-pinned/formal diagnostic fallback when this
actual full probe fails at `connectivity_lvs`, not only when MAGICAL placement
fails. This means future runs automatically produce the formal abstraction
packet, passive-only Netgen trial, full MOS+passive diagnostic trial, hybrid
trial, and MOS-connectivity comparison evidence.

Running `prepare_passive_aware_lvs_netlists.py` directly on the actual
`layout_passive_aware/SMCNR_SE_2st_AMP_extracted.raw.spice` with no stale
renames proves that passive abstraction itself is ready:

- `formal_lvs_abstraction_ready=true`
- `abstraction_scope=source_equivalent_passive_lvs_abstraction`
- source/extracted device count in Netgen: `10` vs `10`
- Netgen still fails on network mismatch: source nets `10`, extracted nets `11`
- Netgen reports `gnda` as a disconnected extracted node

So the remaining failure is the full passive-inclusive GDS MOS/supply network,
not the formal `xr0`/`xc0` passive abstraction.

The actual full-GDS `clip-crossing` subset search also matches the earlier
existing-pinned diagnosis. Out of seven crossing elements, the only size-3
short-free subset is:

- `e00`: `72/20/BOUNDARY`, `[10950, 2150, 11450, 35850]`, `xc0`
- `e01`: `72/20/BOUNDARY`, `[4150, 11550, 4650, 35850]`, `xc0`
- `e03`: `72/20/BOUNDARY`, `[9350, 16150, 9850, 35850]`, `xc0`

This subset removes the Magic `gnda/vdda` supply-short warning, but MOS
connectivity remains `mos_internal_net_mismatch`. No tested subset of size 1,
2, or 3 produced both a short-free extraction and a MOS-connectivity pass.

Additional actual-GDS subset probes now cover the other crossing edit modes
with the corrected `Ubuntu-24.04` WSL/PDK environment:

- `crop-crossing`, all size `1..3`: 22/63 combinations remove the supply short,
  but 0/63 produce MOS connectivity `match`.
- `crossing`, all size `1..3`: 22/63 combinations remove the supply short, but
  0/63 produce MOS connectivity `match`.
- `crossing --run-all-elements`: deleting all seven crossing elements removes
  the supply short, but MOS connectivity remains `mos_internal_net_mismatch`.

These results rule out a simple geometric delete/crop/clip repair as a signoff
path. The full passive-inclusive GDS still corrupts pFET source/bulk or well
connectivity after the supply short is removed.

A narrower VDD-overlap trim was also tested. Instead of deleting or cropping the
passive crossing elements against the passive bbox, this probe uses
`--strip-box-json` with the top VDD stripe bbox `[1900, 35450, 32900, 37350]`
and only selected `cfmom` met5 crossing elements `e00`, `e01`, and `e03`. The
three affected rectangles are truncated just below the top VDD stripe:

- `[10950, 2150, 11450, 35850] -> [10950, 2150, 11450, 35450]`
- `[4150, 11550, 4650, 35850] -> [4150, 11550, 4650, 35450]`
- `[9350, 16150, 9850, 35850] -> [9350, 16150, 9850, 35450]`

Artifacts:

- `layout_passive_aware/vdd_overlap_trim_probe/vdd_overlap_trim_clear100_strip_summary.json`
- `layout_passive_aware/vdd_overlap_trim_probe/vdd_overlap_trim_clear100_extracted.spice`
- `layout_passive_aware/vdd_overlap_trim_probe/vdd_overlap_trim_clear100_mos_connectivity_report.md`
- `layout_passive_aware/vdd_overlap_trim_probe/formal_lvs_clear100/clear100_lvs_result_summary.md`
- `layout_passive_aware/vdd_overlap_trim_probe/formal_lvs_clear100_mos_restored/prepare_summary.json`
- `layout_passive_aware/vdd_overlap_trim_probe/formal_lvs_clear100_mos_restored/clear100_mos_restored_lvs_result_summary.md`

This removes the Magic `gnda/vdda` electrically-shorted port warning while
keeping MOS device count at 8 and formal MOS+passive device count at 10 vs 10.
However, MOS connectivity remains `mos_internal_net_mismatch`, and Netgen still
fails the formal MOS+passive trial on net mismatch (`10` source nets vs `12`
extracted nets). The closest-role diagnostic shows the candidate `gnda` net is
polluted with pFET source/bulk/drain roles that should belong to `vdda`, `outn`,
or related internal nodes. Therefore the remaining repair is not just top VDD
stripe overlap; it requires fixing pFET/nwell/source connectivity in the
passive-inclusive layout.

The same clear100 artifact was then run through a new explicit
`--mos-reference` preparation mode. In this diagnostic, the extracted-side MOS
network is restored from the already-passing MOS-only projection extraction and
the same `xhigh_po_second_stage` passive R/C abstractions are injected. Netgen
reports `PASS`, with devices `10` vs `10` and nets `10` vs `10`. This does not
prove full passive-inclusive GDS signoff because
`mos_connectivity_source=mos_reference`; it proves the opposite boundary more
sharply: once MOS connectivity is correct, the formal `xr0`/`xc0` passive
abstraction composes cleanly under Netgen. The remaining failing component is
the MOS/nwell network extracted from the full passive-inclusive GDS.

Power-stripe environment experiments were also added and tested:

- `MAGICAL_POWER_STRIPE_EXTRA_GRID`
- `MAGICAL_POWER_STRIPE_EXTRA_DBU`

These variables are default-off and are passed through the Sky130 pipeline and
analog harness only when explicitly configured. For this SMC candidate, moving
the power stripes by 2 or 20 grid steps caused Anaroute `parseGds` failures, so
power-stripe margin is not currently a signoff repair. The router environment
switches were also tested:

- `MAGICAL_SKIP_TOP_POWER_ROUTE=1`: avoids full routing of top power nets but
  fails at Anaroute `parseGds`.
- `MAGICAL_SKIP_TOP_POWER_ROUTE=1` plus
  `MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER=1`: still fails at `parseGds`.
- `MAGICAL_SKIP_ROUTER_PARSE_GDS=1`: bypasses `parseGds`, but then routing the
  power net fails.

These are recorded as engineering diagnostics, not enabled defaults.

## PDK/Anaroute Setup Hardening

Anaroute was also failing for an environment/tooling reason unrelated to LVS
semantics: its `parTech.cpp` parser compares some header lines literally, so
CRLF line endings in `sky130.techfile`/`sky130.lef` can leave the router tech
database incomplete and later crash `parseGds` with `_Map_base::at`.

This is now fixed and guarded:

- `tools/sky130_adapter/generate_magical_sky130_pdk.py` writes
  `sky130.techfile.simple`, `sky130.techfile`, `sky130.lef`, and
  `sky130_gds_export_map.yaml` with LF line endings.
- The generator keeps router-facing `sky130.techfile` and `sky130.lef`
  routing-only; passive-only abstraction/remap data stays in the simple tech
  file and export map rather than being injected into Anaroute's routing tech.
- `tools/sky130_adapter/run_sky130_case_pipeline.sh` now validates the configured
  `techfile`, `simple_tech_file`, and `lef` before entering Docker. Missing
  files or CRLF line endings fail in the setup stage with a report at
  `pdk_line_endings.txt`.
- Direct parser probes against the existing SMC placed GDS now pass for both
  `examples/sky130PDK` and `generated/sky130PDK_trial` after LF regeneration.

The MOS-only pipeline was rerun after this fix and passes DRC/LVS/PEX. The full
passive-inclusive pipeline also reaches Magic extraction and Netgen analysis
instead of crashing in placement/routing, but it still fails connectivity LVS
because of the physical MOS/supply/well mismatch described above.

## PnR Substrate Net Fix

`flow/python/PnR.py` had a generic substrate-pin binding bug: PSUB pins were
registered with the original circuit net index instead of the router net index
returned by `router.addNet(...)`. This is fixed by binding the PSUB pin to
`routerNetIdx`, matching the normal pin path.

For this SMC candidate, that bug is not the root cause of the remaining full
passive-inclusive failure because the `gnda` circuit net index and router net
index already coincided in the observed run. The fix still removes a real
indexing hazard for future cases where filtered/rerouted net indices diverge.

## Power-Stripe Repair Experiments

The latest repair attempt targeted the physical source of the full-passive
`gnda/vdda` short: top-level power routing through the `xr0`/`xc0` passive
placement bboxes.

The following diagnostic controls are now wired through the Sky130 pipeline and
recorded in `summary.md`:

- `MAGICAL_POWER_STRIPE_EXTRA_GRID`
- `MAGICAL_POWER_STRIPE_EXTRA_DBU`
- `MAGICAL_DISABLE_POWER_STRIPE`
- `MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES`
- `MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU`

`MAGICAL_POWER_STRIPE_EXTRA_DBU=1000` moved the top VDD stripe upward and the
bottom VSS stripe downward. The run completed through Magic/Netgen with DRC `0`
and experimental passive remap enabled, but Magic still reported `gnda/vdda`
short. The router simply extended the VDD met5 access routes farther upward; the
new crossing probe still found six route elements crossing passive bboxes:
three `72/20`, one `67/20`, and two `68/20` elements.

`MAGICAL_DISABLE_POWER_STRIPE=1` is not a valid repair path for this router. It
fails during detailed routing with Anaroute's
`constructSelfSymPowerRoutables` assertion because self-symmetric power nets
expect at least one power stripe.

`MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES=1` keeps a VDD stripe segment only
outside the passive x-intervals. This run now completes MAGICAL, remap, DRC,
Magic extraction, PEX summary, and Netgen invocation, and the pipeline summary
preserves the full failure evidence instead of overwriting it at the end:

- artifact: `generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware_split_stripe/summary.md`
- DRC: `0`
- experimental passive remap: `yes`
- raw ports: `vdda vin vip ibias vout` (`gnda` still absent)
- connectivity LVS: `no`
- PEX caps: `314`
- total listed capacitance: `618.367 fF`

The split-stripe crossing probe reduced the passive crossing count to five:
two `72/20`, one `67/20`, and two `68/20` elements. The supply short still
remains. This proves that a VDD stripe x-gap alone is insufficient; Anaroute can
still choose power-access routes that enter the passive bbox from lower VDD pins
and then climb to the stripe segment.

The next attempt added router-only passive obstructions. The implementation
generates a temporary `SMCNR_SE_2st_AMP.place.router_obstructed.gds` for
Anaroute `parseGds`, but writes the final route GDS against the original
placement GDS so the artificial obstruction rectangles are not emitted into the
layout under test. The new environment controls are:

- `MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS`
- `MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU`

This obstruction path is functionally active:

- obstructing internal layer `36` (`M6`, Sky130 `72/20`) completes routing and
  moves the remaining high-level passive crossings down to internal layer `35`
  (`M5`, Sky130 `71/20`);
- obstructing layers `35,36` also completes routing and reduces the passive
  crossing set to three lower-layer elements (`67/20` and `68/20`);
- obstructing `31,32,35,36` is too strong and makes Anaroute fail routing;
- obstructing `32,35,36` also makes routing fail, so low-level passive/signal
  access still depends on those layers.

The best obstruction run so far is:

- artifact:
  `generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware_router_obs_m5_m6/summary.md`
- obstruction layers: `35,36`
- DRC: `0`
- experimental passive remap: `yes`
- connectivity LVS: `no`
- passive crossing count after route: `3`

Deleting those final three crossings in a localization probe does **not** remove
the Magic `gnda/vdda` port short. This is a stronger negative result than the
earlier stripe experiments: after high-metal power crossing is rerouted, the
remaining short is no longer explained by the simple passive-bbox crossing
element set.

A placement keepout experiment was also added:

- `MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU`
- `MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU`

Moving both passives right by `40000` DBU completes routing and extraction, but
Magic still reports `gnda/vdda` short. This means a simple global passive offset
is not a sufficient repair either.

The practical next repair is therefore not another global stripe offset. It is
one of:

- add net-specific routing control so only VDD/GND power access avoids passive
  bboxes while signal/passive pins can still use low layers;
- fix the passive pcell pin/guard-ring substrate semantics so rerouted power
  geometry no longer pollutes the MOS bulk/source network;
- add a true placement constraint that changes the floorplan before power
  routing, not just a global post-placement translation.

## Remaining Work

## 2026-06-19 evidence schema hardening

The formal passive evidence now records explicit LVS primitive abstraction
records instead of only reporting candidate counts:

- `xc0`: `cfmom_2t` plate-coupling evidence is collapsed to LVS primitive
  `C_xc0 outn net027 1f` under
  `collapse_plate_coupling_evidence_to_lvs_capacitor`.
- `xr0`: the segmented `rppolywo_m` resistor chain is collapsed to LVS
  primitive `R_xr0 net027 vout 1` under
  `collapse_segmented_resistor_chain_to_lvs_resistor`.

These records are emitted by the packet verifier, the passive LVS evidence
verifier, the candidate state backfill path, and the top-level analog harness
summary. This closes the ambiguity that `cfmom_2t` was only PEX plate-coupling
evidence: in the formal abstraction scope it is now an LVS primitive capacitor.
It still does not claim native Magic extraction of a `cfmom_2t` device.

The non-primary Sky130 LVS helper scripts now share the same `netgen-lvs`
hardening as the main pipeline: they prefer `netgen-lvs` and only accept a
plain `netgen` command if its version output identifies IC Netgen 1.x. This
prevents the current WSL meshing `NETGEN-6.x` binary from being used as an LVS
tool.

## 2026-06-19 follow-up repairs

Three harness-side gaps were closed in this pass:

- `netgen-lvs` is available in `Ubuntu-24.04` and the harness/pipeline prefers
  `/usr/bin/netgen-lvs`.
- Formal passive LVS evidence now has an explicit verifier:
  `tools/sky130_adapter/verify_passive_lvs_evidence.py`. It requires packet
  formal readiness, source/candidate primitive R/C counts, passive-only Netgen
  pass, and hybrid MOS-reference plus passive-abstraction Netgen pass before
  reporting `formal_passive_lvs_evidence_pass`.
- MAGICAL `ioPin` layers `3`, `4`, and `5` are now mapped to Sky130
  `met2/met3/met4` label and pin-purpose layers. This fixes the native offset
  experiment that previously failed at `pin_labels` with
  `No Sky130 label mapping for ioPin layer 3`.

The latest full-GDS native experiment is:

- artifact:
  `generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware_offset_x40000_local_vdd_leftbox`
- passive placement offset: `MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU=40000`
- local VDD repair: enabled at `y=13200`, height `200`
- raw ports: `vdda gnda vin vip ibias vout`
- DRC: `0`
- native full-GDS LVS: `no`
- MOS comparator status: `mos_internal_net_mismatch`

This is progress over earlier `supply_or_internal_net_mismatch` runs: the
supply-role corruption is removed, but Magic still splits internal MOS nets.
The comparator now records machine-readable split hints:

- `ibias` is split into `ibias` + `a_n15_2446#`
- `outp` is split into `a_1340_n30#` + `a_3585_n10#`
- `a_660_2774#` has the exact MOS role signature of source `outn`
- `a_3264_586#` has the exact MOS role signature of source `net53`

A diagnostic, non-signoff trial then rewrote the passives through the formal
R/C abstraction and applied only those internal-net repairs. That Netgen run
passes:

- artifact:
  `generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_aware_offset_x40000_local_vdd_leftbox/formal_passive_split_repair_lvs2`
- result summary: `lvs_result_summary.md`
- status: `PASS`

This pass is intentionally not classified as native full-GDS passive-aware LVS,
because the net repairs are derived from MOS-only/reference role signatures
rather than from Magic physically recovering the internal nets from the full GDS.
It does prove that the remaining native failure is now localized to Magic's
internal net recovery/physical extraction for the passive-inclusive full GDS,
not to Netgen availability, formal R/C abstraction, or GRPO/harness integration.

The harness now automates this diagnostic step for future passive probes. After
`compare_mos_connectivity.py` emits split-net and exact-role hints, the analog
harness derives a `mos_connectivity_repair_plan.v1` and runs a
`formal_passive_mos_repair_lvs_trial`. The repair plan is explicitly marked
`signoff_eligible=false` and `requires_reference_role_signatures=true`, so a
pass in this trial is recorded as localization evidence only. It must not be
used to set `verification_scope=full_passive_inclusive_gds_lvs`.

A route-net label recovery probe was added as
`tools/sky130_adapter/add_net_labels_from_gr_to_gds.py`. It injects Sky130 TEXT
labels from MAGICAL `.gr` route rectangles without changing drawing geometry by
default. On the same offset/local-VDD full-GDS result, labeling
`ibias/outp/outn/net53/net027` directly from `.gr` recovers most internal names:

- `X5/X6/X7` now use `outn`
- `X3/X4` now use `net53`
- the main `outp` and `ibias` label islands are recovered

A companion physical bridge probe was then added as
`tools/sky130_adapter/add_mos_route_bridges_to_gds.py`. It consumes the MOS
split-net summary, `.pin`, `.gr`, and placement log, then inserts only short
same-layer bridge candidates between unmatched MOS pin boxes and their nearest
same-net route rectangles. On the current SMC offset/local-VDD result it derives
exactly two LI1 bridges:

- `ibias`: `SMCNR_SE_2st_AMP_xm7` pin 0 to the nearest `ibias` route, bridge
  box `[-50, 12450, 50, 12550]`.
- `outp`: `SMCNR_SE_2st_AMP_xm1` pin 0 to the nearest `outp` route, bridge box
  `[17950, 1450, 18050, 1550]`.

The integrated harness route-bridge trial is stored at:

`generated/analog_harness/smcnr_se_2st_amp/cand_0031/layout_passive_existing_gds/resistor_remap_variants/xhigh_rb/rb_trial.json`

It reports:

- route label injection: `pass`
- route-label-only MOS connectivity: `mos_internal_net_mismatch`
- bridge insertion: `bridges_inserted`
- bridge count: `2`
- bridge GDS DRC: `0`
- bridge GDS MOS connectivity: `pass`
- formal passive LVS preparation: `ready_for_netgen_trial`
- formal passive Netgen LVS: `pass`

This is stronger than the earlier rename-only diagnostic because the matching
MOS network is extracted from a physically bridged GDS and passes DRC. It is
still not native passive device recognition: `xr0` and `xc0` are matched through
the formal source-equivalent R/C abstraction packet, and the evidence is
classified as `formal_abstraction_with_gds_mos_bridge_pass`, not
`full_passive_inclusive_gds_lvs`.

Full passive-aware LVS/PEX still needs these engineering steps:

1. Confirm real Sky130 target layers for each MAGICAL passive layer/datatype.
2. Decide whether the experimental remap should be promoted, refined, or split
   into resistor-only and capacitor-only mappings.
3. Keep the route-label/MOS-bridge trial in the passive probe path. It now fixes
   the remaining SMC MOS split-net extraction in a DRC-clean physical GDS
   candidate, while still using formal passive R/C abstraction for `xr0`/`xc0`.
4. Continue from the `xhigh_po_second_stage` formal abstraction result. The
   segmented `xr0` chain and `xc0` plate-coupling macro now have formal R/C LVS
   rewrites, so the remaining passive-related work is native device recognition
   and tighter physical extraction, not source-equivalent abstraction.
5. Decide whether future signoff requires native `cfmom_2t`/`rppolywo_m`
   recognition. The current fixed path verifies them as formal source-equivalent
   LVS primitive abstractions, not as native extracted devices.
6. Promote the existing-GDS label probe from diagnostic evidence to an LVS
   abstraction rule only after all source passive terminals and source instance
   semantics are recovered.
7. Preserve the current `netgen-lvs` setup. The environment now has LVS
   `netgen-lvs` available and the harness scripts prefer it over the unrelated
   meshing `netgen`. The best `xhigh_po_second_stage` formal passive
   abstraction passes passive-only Netgen, the hybrid MOS-only-projection plus
   passive-abstraction trial, and the new DRC-clean route-bridge GDS MOS plus
   formal passive LVS trial.
8. Fix the earlier physical supply short in the full candidate pinned GDS. The
   latest exclusion probes show that this is not removed by excluding individual
   experimental passive marker mappings or by excluding all experimental passive
   mappings. Direct extraction of the full candidate pinned GDS and confirmed-
   only remap both short `gnda` to `vdda`; MOS-only projection avoids this only
   because it regenerates a MOS-only layout without the flattened passive
   conductor geometry.
9. Repair the passive-inclusive full GDS route/well connectivity. The
   `clip-crossing` probe proves the seven crossing route/power elements can be
   cut without deleting their outside fragments and without the Magic supply
   short returning, but the resulting extraction still corrupts pFET source/bulk
   connectivity. A real fix must reroute, re-place, or add correct well/tap
   connectivity instead of treating geometry clipping as signoff.

Until native passive device recognition is also available, candidate closure
must remain limited to the MOS-only projection/post-layout evidence. The passive
probe may report
`verification_scope=formal_passive_abstraction_with_gds_mos_bridge` when the
route bridge, MOS connectivity, DRC, and formal passive Netgen checks pass, but
it must not claim `verification_scope=full_passive_inclusive_gds_lvs` or full
passive-aware closure.

## 2026-06-19 native-recognition gate

The harness now reports native passive device recognition separately from the
formal passive LVS abstraction. The native-recognition gate requires each source
passive to appear in the Magic-extracted netlist as a direct expected passive
device. Segmented resistor chains and plate-coupling evidence are explicitly
classified as formal abstraction evidence, not native extraction.

Current SMC summary:

- `best_native_passive_device_recognition_status`: `fail`
- `best_native_passive_device_recognition_claimed`: `false`
- `best_native_passive_device_recognition_missing_instances`: `xr0`, `xc0`
- `xr0` blockers:
  `body_or_substrate_pin_has_no_magical_geometry:gnda`,
  `source_resistor_requires_segmented_chain_abstraction`
- `xc0` blockers:
  `source_capacitor_requires_plate_coupling_abstraction`,
  `coordinate_matched_devices_are_resistor_markers_not_capacitor`,
  `source_capacitor_touches_extracted_resistor_markers_not_a_capacitor_device`

This gate is also included in
`generated/analog_harness/smcnr_se_2st_amp/summary.json` and in the passive LVS
evidence packet. The full passive-inclusive LVS flag remains false:

- `best_passive_aware_scope`: `formal_passive_abstraction_with_gds_mos_bridge`
- `best_full_passive_inclusive_gds_lvs_proven`: `false`

The configured Sky130 PDK path exists at
`/root/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A`.
A direct grep over its Magic/Netgen tech files finds Magic extraction rules for
`sky130_fd_pr__res_xhigh_po` and `sky130_fd_pr__res_generic_*`, but no direct
`cfmom` or `rppoly` references. This matches the observed extraction: the
resistor appears as many `sky130_fd_pr__res_xhigh_po` segments and the MOM
capacitor appears as plate-coupling/parasitic evidence, not as native
`rppolywo_m` or `cfmom_2t` devices.

Full native passive-aware closure therefore requires either:

1. generating real Sky130 PDK passive pcells that Magic/Netgen recognize, or
2. adding and validating explicit Magic/Netgen extraction/setup support for the
   MAGICAL passive geometry.

Until then, the fixed flow is the formal source-equivalent R/C abstraction plus
DRC-clean route-bridge MOS connectivity path, not native passive LVS signoff.
