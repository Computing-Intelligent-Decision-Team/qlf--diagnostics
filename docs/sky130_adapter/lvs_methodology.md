# Sky130 LVS Methodology

## 1. Current Goal

The current Sky130 inverter flow uses Magic extraction and Netgen to verify
connectivity. The power-net-fixed baseline now has clean raw port names:

```spice
.subckt inverter_core_flat A Y VPWR VGND
X0 Y A VPWR VPWR sky130_fd_pr__pfet_01v8 ...
X1 Y A VGND VGND sky130_fd_pr__nfet_01v8 ...
```

The remaining LVS work is to separate raw extraction, connectivity LVS, and
parasitic summary artifacts so the flow is explicit about what is compared.

## 2. Why Raw Magic Extraction Contains Parasitics

Magic extraction emits layout-derived parasitic capacitors and MOS geometry
properties. A raw extracted inverter netlist can contain capacitor lines such
as:

```spice
C0 A Y 0.24578f
```

It can also attach MOS properties such as `ad`, `as`, `pd`, and `ps`. These are
valuable layout-derived data, but the hand-written source netlist used for this
trial does not contain matching parasitics or area/perimeter properties.

## 3. Connectivity LVS Netlists

The current Netgen check is connectivity LVS. The pipeline prepares:

- `inverter_core_extracted.raw.spice`: exact copy of Magic raw extraction;
- `inverter_core_extracted.connectivity.spice`: extracted netlist with
  parasitic capacitor lines removed and `ad/as/pd/ps` stripped from MOS lines;
- `inverter_source.connectivity.spice`: source netlist converted to X-instance
  form with matching model names and `w/l` properties.

The connectivity extracted netlist keeps device model names and `w/l`; it does
not keep parasitic capacitors or layout-only MOS properties.

## 4. Why Removing Parasitics Is Not Data Loss

The flow does not discard Magic parasitics. It preserves the raw extracted
netlist and generates a separate PEX summary. Connectivity LVS simply compares
the transistor-level topology without asking the source schematic to include
layout parasitics that were never present there.

The PEX summary is generated from the raw netlist and reports:

- parasitic capacitor count;
- total listed capacitance;
- per-node capacitor count and capacitance sum;
- largest extracted capacitors.

## 5. Property-Only Mismatch

`ad`, `as`, `pd`, and `ps` are layout-derived MOS geometry properties. If the
source netlist lacks these properties, Netgen may report property-only mismatch
even when device connectivity is correct. The current connectivity LVS removes
these properties from the extracted comparison netlist while preserving `w/l`.

This is not suitable for final PEX or property-aware verification. It is a
temporary connectivity-LVS policy for the Sky130 adapter bring-up.

## 6. LVS Flow Layers

The enhanced inverter pipeline now reports these stages separately:

1. Raw Magic extraction.
2. Connectivity LVS preparation.
3. Netgen connectivity LVS.
4. LVS result analysis.
5. PEX summary.

The top-level summary must describe the check as connectivity LVS, not complete
parasitic-aware LVS.

## 7. Current Limits

This is not full parasitic-aware LVS. It does not compare extracted capacitors
against source parasitics, and it does not validate all layout-derived MOS
properties. It verifies that the source and extracted transistor connectivity
match after intentional connectivity-only normalization.

The older inverter-specific script remains in the tree:

```text
tools/sky130_adapter/normalize_lvs_netlists_inverter.py
```

It should not be deleted yet, but the newer layered flow uses:

```text
tools/sky130_adapter/prepare_lvs_netlists.py
tools/sky130_adapter/analyze_lvs_result.py
tools/sky130_adapter/summarize_magic_pex.py
```

## 8. Upgrade Path

Future work should:

- keep raw extracted parasitics for post-layout simulation;
- align source and extracted MOS properties where property-aware checks are
  required;
- introduce tolerance-based property comparison if needed;
- run the same layered flow on more Sky130 examples such as diff-pair and OTA
  regressions.
