# Codex Review: AH-SMC-007 And AH-SMC-008

## Decision

The first evidenced body-semantic divergence occurs in the MAGICAL NMOS
primitive/pin contract. The source has four-terminal NMOS devices whose bodies
are tied to `gnda`, while the generated NMOS physical contract has no body pin
geometry and no p+ substrate tap. Reclassifying existing standalone OD as tap
does not repair the extraction.

## Source And Pin Contract

- Source M23 is `(vout, net049, gnda, gnda)` in
  `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.sp`, line 14.
- M23's generated fourth pin is `-1` in
  `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.pin`, lines 62-66.
- The same absent fourth pin is present for the other NMOS devices.
- M11, by contrast, has a physical fourth-pin rectangle in the same pin file,
  lines 2-6.

## Primitive And Remap Evidence

- M23 primitive GDS contains one OD, one NP, two poly boundaries and contact/
  routing geometry. It has no standalone p+ tap region.
- M11 contains separate nwell/implant/OD structures and has a physical body-pin
  contract; the nwell-domain diagnostic passes.
- Route-to-Sky130 mapping reports `od_maps_to_diff_before_tap_semantics` for
  M23. It does not create missing body geometry.
- Tap/body diagnosis finds no local tap geometry in the NMOS instance boxes.
- The synthetic psub route is assigned to `gnda` on the router side, but is a
  met5 rail without a physical stack down to a p+ substrate tap.

## Direct Magic Evidence

Static connectivity through active diffusion is treated only as an
over-approximation. The decisive evidence is Magic's `.ext` output:

- substrate is named `vout`;
- `vout` is equivalent to `vdda`;
- `vout` is equivalent to `gnda`;
- M23 source/body/drain extract in the vout domain.

This is consistent with an unrepresented substrate-body connection, not proof
that every static active-diffusion path is a real metal short.

## AH-SMC-008 Tap-Split A/B

The existing adapter tap-split was applied as the only changed variable:

- 104 standalone `diff.drawing` rectangles became `tap.drawing`;
- pin labels, pin shapes, route geometry and source netlist were unchanged;
- Magic output remained unchanged;
- substrate remained `vout` and both supply equivalences remained.

Decision: reject tap-split as a repair. It can classify existing OD, but cannot
create the missing NMOS p+ substrate tap/body connection.

## Trust Decision

| Field | Decision |
| --- | --- |
| `usable_for_reward` | false |
| `usable_for_post_sim` | false |
| `usable_for_training` | false |
| `usable_for_parasitic_modeling` | false for topology-faithful modeling |
| `usable_only_as_failure_case` | true |

## Next Design Gate

The next A/B must introduce one explicit p+ substrate tap tied to the existing
gnda rail, or replace the NMOS primitive with a body-aware equivalent. This is
a physical-adapter design decision and requires review before implementation.
