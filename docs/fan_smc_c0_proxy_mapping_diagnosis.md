# Fan_SMC C0 Proxy Mapping Diagnosis

## Finding

The original 5 pF behavioral capacitor is mapped by the prior converter to:

```text
C0 (net050 vout) cfmom_2t nr=1000 lr=500u ...
```

The generated flattened C0 GDS contains 17,018 boundaries and spans roughly
140 um by 500.7 um. It dominates the full layout height and places M11 and the
vout interface at its upper edge.

## Root-Cause Trace

The converter computes both geometry axes linearly from capacitance:

```text
nr = cap_fF / 5
lr_um = cap_fF / 10
```

For 5 pF (`5000 fF`), this yields `nr=1000`, `lr=500 um`. Scaling both axes
linearly makes proxy area grow approximately quadratically with target
capacitance. The conversion report already classifies this as
`value_to_geometry_estimate`, `needs_validation`, and not final-flow-safe.

This mapping also does not preserve the AnalogHarness simulation projection,
which estimates a cfmom macro primarily from `nr`. The current proxy therefore
is neither a validated electrical mapping nor a layout-safe abstraction.

## Differential Evidence

- Original proxy layout: M11 S/G/B/D all extract as vout; vout shorts to both
  supplies.
- no-C0/B1 layout: M11 drain remains vout while gate and source/body remain
  distinct anonymous nets. This removes the total M11 collapse, although LVS
  still fails and the original capacitor is absent.
- Local met5 B1 masking on the original proxy does not change either static
  vout-supply path.

These observations support the oversized C0 layout proxy as the next root-cause
variable. They do not prove that a smaller proxy preserves 5 pF electrically.

## AH-SMC-003 Candidate

Use the reviewed SMCNR positive-baseline layout parameters `nr=94`, `lr=10 um`
as a bounded layout surrogate while retaining the original source target of
5 pF in a separate manifest.

Prepared candidate:

```text
generated/diagnostics/fan_smc_c0_proxy_94x10/
```

This candidate is diagnostic-only. Its manifest explicitly records
`electrically_equivalent_to_source_5pf=false`. If it repairs layout topology,
the eventual passive path must use formal/native replacement evidence rather
than pretending that the surrogate is the final capacitor.

## Reviewed Result

The candidate completed MAGICAL P&R and reduced C0 to 1,606 boundaries with an
approximately 13.1 um by 10.7 um box. This removes the pathological layout
scale, but Magic still reports vout shorted to both supplies.

A bounded B1 variant removes those explicit warnings but also disconnects
`gnda` and `vdda`; direct Netgen reports 24 vs 24 devices and 18 vs 37 nets.
Label-only and 200-by-200 center-pin experiments reject full-width pin-purpose
geometry as the primary cause.

Current diagnostics instead point to psub/body/tap semantics. Magic records
substrate `vout` and equivalences from vout to both supplies; the psub diagnosis
fails while the PMOS nwell-domain diagnosis passes. Detailed review:
`docs/codex_ah_smc_003_006_review.md`.
