# Analog Harness

This package connects the local AnalogGym GRPO optimizer to the existing
MAGICAL/Sky130 layout verification flow.

The first supported design is `SMCNR_SE_2st_AMP`. Version 1 records the
current SMC layout verification scope as `mos_only_projection`; this is not a
passive-aware LVS/PEX closure claim.

The controller first checks configured front-end sizing results. If a reusable
front-end candidate exists, it evaluates that candidate through the harness
before asking GRPO for a new sizing. If evidence shows a sizing repair is
needed, the next candidate is forced through the GRPO sizing adapter. Good
GRPO/harness candidates are saved into `knowledge_transfer/warm_start_bank.json`
and `knowledge_transfer/proxy_feedback_dataset.jsonl` so later runs can
warm-start from proven sizing/evidence pairs.

Closure levels are evidence-based. `post_sim=proxy_fallback` does not count as
L5; a candidate with passing DRC/LVS/PEX but proxy post-sim remains
`L4_layout_verified_mos_only`. `post_sim=pass` promotes to
`L5_post_layout_nominal`; `pvt_sim=pass` promotes to `L6_post_layout_pvt`.
The summary command recomputes closure/reward from stored evidence so older
state files cannot overstate closure.

When post-layout ngspice reports a Sky130 binned-model mismatch, the controller
records `post_sim:sky130_model_bin_mismatch` as a sizing redesign request. The
GRPO adapter then proposes a `model_safe_sizing_repair` seed from the configured
`optimizer.model_safe_repair_values`. If that repaired sizing breaks layout
LVS, the regular layout-safe sizing repair path takes over on the next round.

For PEX post-layout simulation, Magic-extracted Sky130 MOS dimensions are
normalized for ngspice and projected onto nearest supported Sky130 model bins.
The generated post-layout netlist records `simulation_model_projection`; mixed
metric packets also record which fields came from ngspice and which fields were
filled by the deterministic proxy.

The simulator now writes full AC sweep, OP power, and transient waveform data.
It derives `dcgain`, `GBW` or `GBW_lower_bound`, `phase_margin`, `Power`,
`settlingTime`, `FOML`, and `FOMS` from ngspice outputs where available.
Pre-layout MAGICAL macro devices (`nch_mac`, `pch_mac`, `rppolywo_m`,
`cfmom_2t`) are projected into approximate Sky130 MOS/resistor/capacitor
primitives for ngspice; the evidence records
`prelayout_projection_scope=macro_to_sky130_approximation`.

Post-layout PVT is enabled in the SMC config with three corners:
`tt_1v8_27C`, `ss_1v62_125C`, and `ff_1v98_-25C`. The aggregate `pvt_sim`
packet records per-corner status and worst-case metrics.

Passive-aware LVS/PEX is probed separately as `passive_aware_lvs`. The current
adapter now has a formal source-equivalent abstraction for the SMC resistor and
MOM capacitor (`xr0` as a segmented-chain resistor and `xc0` as a plate-coupling
capacitor). The dedicated passive LVS evidence verifier requires primitive R/C
netlists plus passive-only and hybrid Netgen passes before reporting a formal
pass. Passive-only Netgen, the hybrid MOS-only-projection plus passive
abstraction trial, and the DRC-clean route-bridge GDS MOS plus formal passive
trial pass. The `passive_aware_lvs` packet is classified as
`formal_abstraction_with_gds_mos_bridge_pass` with
`verification_scope=formal_passive_abstraction_with_gds_mos_bridge`; it is not a
native passive-device full-GDS pass and does not promote candidate closure
beyond the MOS-only layout/post-layout levels. On Windows, the
adapter now resolves WSL distro selection explicitly and avoids the default
`docker-desktop` distro, so `magic` and IC LVS `netgen-lvs` are checked and run
from the configured `Ubuntu-24.04` environment. The Sky130 case pipeline also
auto-discovers the AnalogGym-local Sky130 PDK
(`../Analoggym_opt_moo_Mahalanobis_paper/mosfet_model/sky130_pdk`) when the
legacy ciel PDK path is absent.

The Sky130 PDK generator and case pipeline also guard against CRLF line endings
in MAGICAL tech/LEF files. CRLF can break Anaroute's tech parser and surface
later as `parseGds` crashes; the generated trial PDK is now written as LF and
the pipeline fails early if a configured PDK file regresses.

The latest full-GDS diagnostic with a passive X offset plus local VDD repair
keeps the top-level ports complete and removes the supply-role corruption. The
remaining `mos_internal_net_mismatch` is now repairable by a physical
route-label bridge probe: the adapter injects route labels from MAGICAL `.gr`,
derives two small LI1 bridges from MOS split-net evidence, reruns Magic DRC and
extraction, and then runs formal passive R/C LVS. The integrated probe records
`route_bridge_count=2`, `route_bridge_drc_count=0`,
`route_bridge_mos_connectivity_status=pass`, and
`formal_passive_lvs_netgen_status=pass`. This is stronger than a rename-only
diagnostic because the repaired MOS network comes from the bridged GDS
extraction, but it still does not claim native passive device recognition:
`xr0` and `xc0` are matched through the formal R/C abstraction packet.

Future passive probes automatically derive a diagnostic
`mos_connectivity_repair_plan.v1` from those comparator hints and run a
`formal_passive_mos_repair_lvs_trial`. That repair trial is always marked
`signoff_eligible=false`; it helps prove whether the remaining mismatch is only
internal-net recovery, but it does not change the candidate closure level or the
native full-GDS claim.

The Sky130 adapter also has a route-net label probe
(`add_net_labels_from_gr_to_gds.py`) that injects labels from MAGICAL `.gr`
rectangles. On the current SMC full-GDS case it recovers most internal signal
names. The companion `add_mos_route_bridges_to_gds.py` tool now turns the two
remaining source-pin opens into physical bridge candidates using `.pin`, `.gr`,
placement-log, and MOS split-net evidence. The harness classifies the passing
result as `formal_abstraction_with_gds_mos_bridge_pass`, not as native
full-GDS passive-aware LVS.

Power-stripe diagnostics are now wired through the layout pipeline. Moving the
stripe, disabling it, splitting the VDD stripe around passive bboxes, and
splitting the top `met5` VDD drawing/port boundaries around the suspicious
`s0/s1` trunks were tested. Disabling the stripe is not accepted by Anaroute;
the split experiments either leave the signal/supply short unchanged or isolate
a mixed internal net that still contains pMOS bulk/source roles. Full
passive-inclusive signoff now requires a real net-aware routing/tap repair,
not a label-only or stripe-only post-process.

The case pipeline also exposes diagnostic local-stripe knobs:
`MAGICAL_LOCAL_VDD_STRIPE_*`, `MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_*`, and
`MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_*`. These are evidence tools, not a
closure claim. Pre-route local VDD can separate `gnda/vdda` but currently
corrupts `X7`; post-route injection avoids router interaction but does not
repair pFET well/VDD extraction.

For diagnosis, `prepare_passive_aware_lvs_netlists.py --mos-reference` can
restore the extracted-side MOS network from the already-passing MOS-only
projection and inject the same passive abstractions. That restored trial passes
Netgen, but it is explicitly marked `mos_connectivity_source=mos_reference` and
is not full passive-inclusive GDS signoff.

The full-extraction passive probe writes `passive_integrity_report.md` under
each candidate's `layout_passive_aware` directory. On full-probe
`connectivity_lvs` failure it also runs the existing-pinned/formal diagnostic
fallback, so the abstraction packet, Netgen trials, and MOS-connectivity
comparison are recorded automatically. The current root cause and next
engineering steps are tracked in
`docs/sky130_adapter/passive_aware_lvs_status.md`.

`summarize` also backfills stronger passive evidence from existing
`layout_passive_existing_gds/resistor_remap_variants` artifacts when an older
candidate state still contains an `unsupported` passive packet. The GRPO
feedback flattener exposes both `verification_mask` and
`verification_native_pass_mask`: scoped formal passive evidence sets `E2P` in
`verification_mask`, while `verification_native_pass_mask["E2P"]` remains
`false` unless native full-GDS passive LVS actually passes.

The passive evidence packet now includes explicit
`passive_lvs_primitive_abstractions` records. For the current SMC candidate,
`xc0` is mapped to `C_xc0 outn net027 1f` with rule
`collapse_plate_coupling_evidence_to_lvs_capacitor`, and `xr0` is mapped to
`R_xr0 net027 vout 1` with rule
`collapse_segmented_resistor_chain_to_lvs_resistor`.

## Smoke run

```bash
python -m tools.analog_harness.cli run \
  --config tools/analog_harness/configs/smcnr_se_2st_amp.yaml \
  --max-candidates 1 \
  --layout-budget 0 \
  --skip-layout \
  --skip-sim
```

## Full run entrypoint

```bash
python -m tools.analog_harness.cli run \
  --config tools/analog_harness/configs/smcnr_se_2st_amp.yaml \
  --max-candidates 1 \
  --layout-budget 1
```

The full run requires the same Docker, Magic, netgen, Sky130A, and ngspice
environment used by `tools/sky130_adapter/run_sky130_case_pipeline.py`.

Use `--force-sizing` to skip front-end reuse and call GRPO first. Use
`--no-frontend-results` to disable front-end result discovery, and
`--no-knowledge-archive` to avoid updating the warm-start archive.

## GRPO warm-start training interface

```bash
python -m tools.analog_harness.cli train-grpo \
  --config tools/analog_harness/configs/smcnr_se_2st_amp.yaml \
  --steps 300
```

This command does not run long training. It writes
`knowledge_transfer/grpo_warm_start_training_manifest.json` plus PowerShell and
Bash launch scripts that point AnalogGym at the harness warm-start bank and
proxy feedback dataset.
