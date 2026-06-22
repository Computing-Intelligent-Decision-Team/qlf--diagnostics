# Codex Review: AH-SMC-003 Through AH-SMC-006

## Decision

The bounded C0 proxy makes the Fan_SMC layout tractable, but no reviewed
candidate closes LVS.  The current primary blocker is substrate/body-domain
semantics, not P&R scale or pin-marker width.

## AH-SMC-003: Bounded C0 Proxy

- Evidence class: local generated artifact.
- Only logical netlist change: C0 layout surrogate from `nr=1000, lr=500u` to
  `nr=94, lr=10u`.
- This surrogate is not electrically equivalent to the source 5 pF target.
- MAGICAL P&R completed and produced final route artifacts.
- C0 shrank from 17,018 boundaries and about 140 um by 500.7 um to 1,606
  boundaries and about 13.1 um by 10.7 um.
- Route analysis classified the final run as completed cleanly, despite
  intermediate retries.
- Magic extraction still reported `vout` shorted to both `vdda` and `gnda`.
- Extracted MOS count: 24.  Extracted passive identity for C0/net050: absent.

## AH-SMC-004: B1 On The Bounded Proxy

- Evidence class: local generated artifact.
- Single geometry change: remove 352 bounded `met5.drawing` polygons using the
  established B1 region.
- Magic no longer printed the explicit vout-to-supply short warnings and
  recovered ports `gnda vdda vinn vinp vout`.
- The edit also disconnected the supply domains and fragmented internal nets.
- Direct Netgen result: 24 vs 24 devices, 18 vs 37 nets, two disconnected pins
  (`gnda`, `vdda`), and `Netlists do not match`.
- MOS connectivity diagnosis: `supply_or_internal_net_mismatch`.
- Therefore B1 is not an LVS repair; it removes necessary power connectivity
  along with the observed short.

## Parenthesized Passive Parser Fix

`source_to_connectivity` previously dropped known passive models only in the
`X*` path, so `C0 (net050 vout) cfmom_2t ...` leaked into a MOS-only source
netlist.

- A focused regression test first failed because `cfmom_2t` remained.
- The minimal fix recognizes known passive aliases on `X`, `C`, and `R`
  instance lines before MOS normalization.
- Focused regression: 1/1 passed.
- `test_prepare_lvs_netlists.py`: 5/5 passed.
- diagnostics/trust-gate suite: 22/22 passed.
- Regenerated report records one dropped `cfmom_2t`; the connectivity source
  contains no C0 instance.

## AH-SMC-005 And AH-SMC-006: Pin Geometry A/B

AH-SMC-005 used the label-only GDS.  It removed explicit short warnings but
created no top ports and collapsed supply naming to `gnda`; it is rejected.

AH-SMC-006 replaced full ioPin rectangles with 200 by 200 center pin markers
for only the five top ports.  Magic still reported `vout` shorted to `vdda`
and `gnda`, and the extracted top ports remained only `vinn vinp vout`.
Therefore full-width pin-purpose geometry is not the primary short cause.

## Root-Cause Evidence

- Extracted-device mapping: 23 mapped devices, one unmatched extracted
  device, 23 body mismatches, and 88 terminal mismatches.
- M11 expected `(vout, net050, vdda, vdda)` but extracted all four terminals
  as `vout`.
- M23 expected `(vout, net049, gnda, gnda)` but extracted source/body/drain in
  the `vout` domain.
- PMOS nwell/body-domain static diagnosis: pass.
- Psub diagnosis: fail with
  `magic_substrate_on_signal`, `magic_equates_signal_to_power`, and
  `psub_active_dependent_signal_path_with_magic_conflict`.
- Magic `.ext` explicitly records substrate `vout` and equivalences
  `vout=vdda` and `vout=gnda`.

The next investigation must follow psub/body/tap semantics from the MAGICAL
primitive and route contract through GDS remapping into Magic extraction.

## Trust Decision

| Field | Decision |
| --- | --- |
| `usable_for_reward` | false |
| `usable_for_post_sim` | false |
| `usable_for_training` | false |
| `usable_for_parasitic_modeling` | false for topology-faithful modeling |
| `usable_only_as_failure_case` | true |

No post-layout simulation or PVT work is authorized for these candidates.
