# DFCFC2/Fan_SMC Closure Campaign Status

This document is maintained by Codex as the authoritative campaign dashboard.
Claude Code records task execution in `docs/claude_code_run_report.md` and does
not promote task status without Codex review.

## Campaign Objective

1. Close the original Fan_SMC/Fan_SMC_Pin_3 circuit first.
2. Reuse the verified diagnostics path to close DFCFC2.
3. Keep diagnostics observation-only until a separate controller/reward review.

Full closure for either circuit requires auditable DRC, explicit Netgen LVS
match, topology-trusted PEX, valid post-layout simulation, valid PVT evidence,
an explicit passive scope, and a reviewed five-field trust decision.

## Current Phase

| Field | Value |
| --- | --- |
| Phase | Phase 2: original Fan_SMC topology closure |
| Active task | `AH-SMC-016` pending user approval |
| Active circuit | Fan_SMC bounded-C0 diagnostic path; original Fan_SMC closure remains the formal target |
| Formal closure priority | Original Fan_SMC, then DFCFC2 |
| Controller/reward integration | Not allowed |
| Campaign status | `AH-SMC-015R2` accepted as patch authorization package; AH-SMC-016 requires explicit user approval before MAGICAL- modification |
| Codex focused diagnostics baseline | 22/22 passed on 2026-06-20 |

## Reviewed Baselines

### Positive Baseline

- Candidate: `smcnr_se_2st_amp/cand_0031`
- Evidence class: curated reproducibility package with backfilled passive proof
- Review: `docs/smcnr_cand0031_evidence_audit.md`
- Governing contract: `docs/smcnr_positive_baseline_contract.md`

### Fan_SMC Diagnostic Baseline

- Evidence class: local artifact
- Run: `smc09_no_c0/sky130_pipeline/extract_b1`
- Direct Netgen result: 24 vs 24 devices, 18 vs 39 nets, mismatch
- PEX: present
- Limitation: C0 was removed; this is not the original AnalogGym circuit
- Trust status: failure-case only

### DFCFC2 Diagnostic Baseline

- Evidence class: local artifact
- Run: `mim_proxy_full_pipeline_with_lvs_diagnosis`
- Observed Magic DRC count: 0 in a partially remapped run
- PEX: present
- LVS: device and net mismatch
- Trust status: failure-case only

## Task Queue

| Task | Status | Owner | Acceptance gate |
| --- | --- | --- | --- |
| `AH-DIAG-001` Fan_SMC Netgen-to-trust fixture | Accepted | Codex fallback execution/review | RED-GREEN verified; focused 22/22; full 71/73 with two known failures |
| `AH-SMC-001` original Fan_SMC reproducible baseline | Accepted | Codex fallback execution/review | Exact evidence gaps, C0 trace, trust decision, and replay blocker recorded |
| `AH-SMC-002` original-C0 B1 local-met5 experiment | Rejected by static A/B | Codex review | Both vout-supply paths unchanged after mask |
| `AH-SMC-003` bounded C0 layout-proxy P&R | Accepted as scale diagnostic | Codex fallback execution/review | P&R completed; layout tractable; extraction still shorts vout to both supplies |
| `AH-SMC-004` bounded-proxy B1 extraction/LVS | Rejected as repair | Codex fallback execution/review | 24 vs 24 devices, 18 vs 37 nets, gnda/vdda disconnected |
| `AH-SMC-005` label-only extraction | Rejected | Codex fallback execution/review | No top ports; supply naming collapses to gnda |
| `AH-SMC-006` center-pin extraction | Rejected as root cause | Codex fallback execution/review | Center markers retain vout-vdda/gnda shorts |
| `AH-SMC-007` psub/body/tap provenance audit | Codex review complete | Claude/Codex review | First divergence: NMOS body pin/tap absent from physical contract |
| `AH-SMC-007R` Claude report correction | Superseded by later reviewed runs | Claude/Codex review | Correct router-layer semantics and reject label-only body proposal |
| `AH-SMC-008` existing tap-split A/B | Rejected as repair | Codex fallback execution/review | 104 OD records rewritten; Magic substrate/equivalence unchanged |
| `AH-SMC-009` explicit p+ substrate-tap design | Reviewed; rejected as repair, accepted as diagnostic | Codex review | Added tap present; DRC 0; Magic still equates vout/vdda/gnda; trust remains failure-case only |
| `AH-SMC-010` primitive/body/substrate minimization | Accepted localization | Codex review | First auditable divergence localized to NMOS `.pin` fourth-pin `-1`; not a closure proof |
| `AH-SMC-011` M23 body-contact GDS probe | Reviewed; accepted as negative diagnostic with scope caveat | Claude, then Codex review | Direct GDS body-contact injection did not change extraction; not a clean `.pin` contract disproof |
| `AH-SMC-012` met5 contamination audit | Reviewed; accepted contamination audit | Claude, then Codex review | AH-SMC-011 connector bridged gnda to a previously separate unknown right-side met5 tree; AH-SMC-011 invalidated as clean experiment |
| `AH-SMC-013` M23 `.pin` repair feasibility | Rejected pending artifact correction | Claude, then Codex review | Preserved `.pin` artifact is byte-identical to baseline; claimed M23 pin change is not auditable |
| `AH-SMC-013R` M23 `.pin` artifact correction | Accepted blocker | Claude, then Codex review | Pin delta auditable; final `.pin` overwritten to baseline; external `.pin` editing blocked |
| `AH-SMC-014` MAGICAL `.pin` provenance audit | Accepted provenance audit | Claude, then Codex review | Verified `.pin` regeneration path, `ioLayer > 10 -> -1`, NMOS PSUB / PMOS NWELL classification; primitive geometry partly inferred because submodule is unavailable |
| `AH-SMC-015` MAGICAL NMOS body-pin patch authorization package | Rejected pending correction | Claude, then Codex review | Mixed Sky130 GDS layer numbers with MAGICAL internal `ioLayer`; `ioLayer=67` would still trigger `layer > 10 -> -1` |
| `AH-SMC-015R` Correct MAGICAL body-pin patch authorization | Rejected pending correction | Claude, then Codex review | Fixed layer semantics and `setIoShape` order, but Option B injection remained inside the generated-pin loop and may not execute when NMOS B pin is omitted |
| `AH-SMC-015R2` Correct Option B missing-pin control flow | Accepted patch authorization package | Claude, then Codex review | Corrected layer semantics, `setIoShape` order, and missing-pin control flow; no MAGICAL- writes |
| `AH-SMC-016` MAGICAL Option B NMOS body-pin diagnostic patch | Pending user approval | Claude, then Codex review | Requires explicit approval to modify MAGICAL-; patch only `Device_generator.writeDB()` and preserve pre-patch dirty-state evidence |
| `AH-SMC-*` subsequent single-variable experiments | Pending | Claude/Codex review | One hypothesis and one changed variable per run |
| Fan_SMC post-layout/PVT closure | Pending | Claude/Codex review | Only after credible DRC/LVS/PEX |
| `AH-DFCFC2-*` closure campaign | Pending | Claude/Codex review | Begins after Fan_SMC diagnostics path is validated |

## Trust Boundary

No DFCFC2 or Fan_SMC artifact is currently accepted as reward-safe,
post-simulation-safe, or training-safe. PEX from an LVS-failing topology is
eligible only for diagnostic parasitic analysis under the current contract.

## Latest Codex Decision

The bounded C0 proxy completed P&R and removed the original pathological scale,
but Magic still shorts vout to both supplies. B1 removes the explicit short at
the cost of disconnecting gnda/vdda and producing a 24-device, 18-vs-37-net
LVS mismatch. Label-only and center-pin A/B experiments reject pin-marker width
as the primary cause. Device mapping and substrate diagnostics now localize the
next investigation to psub/body/tap semantics. See
`docs/codex_ah_smc_003_006_review.md`. No circuit closure claim has been made.

Codex's independent AH-SMC-007 audit identifies the first evidenced semantic
gap at the NMOS primitive/pin contract: source body terminals are `gnda`, while
generated NMOS fourth pins are `-1` and the physical substrate-contact contract
is not proven. AH-SMC-008 confirms that reclassifying existing OD as tap is
insufficient. AH-SMC-009 confirms that adding one top-level p+ substrate tap
tied to the existing `gnda` rail is also insufficient: Magic still records
`substrate "vout"`, `equiv "vout" "vdda"`, and `equiv "vout" "gnda"`.
See `docs/codex_ah_smc_007_008_review.md` and
`docs/codex_ah_smc_009_review.md`.

AH-SMC-010 is accepted as localization evidence, not as closure. It identifies
the first auditable semantic divergence at the NMOS `.pin` contract: source
netlist bodies require `gnda`, while generated NMOS fourth pins are `-1`, and
no extracted NMOS body is `gnda`.

AH-SMC-011 is accepted as a negative GDS-level diagnostic with a scope caveat.
Directly painting an M23 body-contact stack and horizontal met5 connection to
gnda did not change Magic extraction: substrate and M23 body remained `vout`,
and `vout` stayed equivalent to `vdda` and `gnda`. This does not cleanly
disprove the broader NMOS `.pin` contract hypothesis because the `.pin` file was
not modified and the horizontal met5 connector may have crossed existing
vout-associated routing.

AH-SMC-012 is accepted as a contamination audit. It confirms that AH-SMC-011's
manual horizontal met5 connector bridged a gnda-confirmed left tree to a
previously separate right-side unknown tree. AH-SMC-011 is therefore invalidated
as a clean test of the NMOS body-contact or `.pin` contract hypothesis. The
right-side tree remains suspicious but not proven `vout`.

AH-SMC-013 is rejected pending artifact correction. It produced a materially
different extraction, but the preserved `.pin` file still has M23 fourth pin
`-1` and is byte-identical to the baseline `.pin`. The claimed `.pin` change
therefore cannot be used to explain the extraction delta.

AH-SMC-013R is accepted as a blocker. It preserves an auditable one-line M23
`.pin` delta, but the current MAGICAL P&R entry point overwrites the final
`.pin` back to baseline. External `.pin` editing is therefore blocked as a
stable single-variable experiment path.

AH-SMC-014 is accepted as a read-only provenance audit. It verifies that
`Placer.placeParsePin()` regenerates `.pin` from the internal database and
writes `-1` for `ioLayer > 10`; that `DesignDB.connect_children()` classifies
NMOS pin 3 as `PSUB` and PMOS pin 3 as `NWELL`; and that
`Device_generator.writeDB()` copies primitive pin-shape layer data into
`net.ioLayer`. The exact `device_generation.Mosfet.pin()` primitive geometry is
still partially inferred because the external submodule is not initialized
locally.

AH-SMC-015 is rejected pending correction. Its Option B recommendation is a
reasonable diagnostic direction in principle, but the authorization package uses
Sky130 GDS layer numbers such as `67` as MAGICAL internal `ioLayer` values.
That contradicts `Placer.placeParsePin()`, where `ioLayer > 10` writes `-1`.

AH-SMC-015R2 is accepted as the final patch authorization package. It keeps
MAGICAL internal `ioLayer = 6`, uses `setIoShape(xLo,yLo,xHi,yHi)`, and moves
the missing NMOS body-pin injection after the generated-pin loop so it can run
when `self.cell.pin()` returns only D/G/S.

The next task is AH-SMC-016, but it is pending explicit user approval because
it modifies `/home/qlf/IOT/references/MAGICAL-/flow/python/Device_generator.py`.
The local MAGICAL- checkout is already dirty, so AH-SMC-016 must preserve
pre-patch `git status`, `git diff -- flow/python/Device_generator.py`, and
file SHA evidence before applying the diagnostic patch.

`SMCNR_SE_2st_AMP/cand_0031` is the sole positive circuit baseline. It defines
the Harness evidence shape and stage gates, including the provenance of
backfilled full-passive evidence. It does not transfer pass status to
`Fan_SMC_Pin_3` or DFCFC2. See `docs/smcnr_positive_baseline_contract.md`.
