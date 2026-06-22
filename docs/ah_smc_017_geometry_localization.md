# AH-SMC-017: Fan_SMC Geometry-Level Substrate Collapse Localization

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-017 |
| Date | 2026-06-22 |
| Type | Read-only geometry localization audit |
| MAGICAL files modified | **None** |
| Trust status | Failure-case only |

## Executive Summary

**The Fan_SMC substrate collapse is caused by diffusion-layer connectivity, not
metal routing.** The psub route (a horizontal diffusion stripe implemented by
MAGICAL's internal "gnda route" on layer 6/OD) physically connects through the
p-substrate to NMOS source/drain diffusions, creating a continuous electrical
path: gnda → psub diffusion → NMOS drain diffusions → vout.

When `diff.drawing` is excluded from the psub component graph, the merge of
gnda/vdda/vout disappears — only `gnda` remains connected to the psub route.
This proves **diffusion is the dominant mechanism**, not metal routing.

The 47-step `psub_to_vdd_path` confirms the complete conduction chain passes
through 3 NMOS devices (M20, M22, M23 — all body→vout) via diffusion-to-metal
contact stacks.

---

## 1. Hard Blocker: `.ext` Substrate/Equiv Records

From `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext`:

```text
line 32: substrate "vout" 0 0 310 2088 m1 ...
line 33: equiv "vout" "vdda"
line 34: equiv "vout" "gnda"
```

The substrate is named after `vout` (anchored at the vout port on met1 at
[310, 2088]—[2930, 2130]). Magic has geometrically proven that `vdda` and
`gnda` are electrically connected to `vout` through the substrate.

**Until these records change, no Netgen setup, `.pin` contract fix, or
routing change can produce an honest LVS pass.**

---

## 2. Diffusion vs Metal: Decisive Evidence

### 2.1 With Diffusion (baseline)

| Metric | Value |
| --- | --- |
| `psub_component_pin_overlaps` | **`["gnda", "vdda", "vout"]`** |
| `psub_connected_to_vdd_pin` | **true** |
| `psub_connected_to_vss_pin` | true |
| `psub_active_dependent_vdd_path` | true |
| `diff.drawing` count | 128 rectangles |
| psub→vdd path length | 47 steps |

### 2.2 Without Diffusion (diagnostic variant)

| Metric | Value |
| --- | --- |
| `psub_component_pin_overlaps_no_diff` | **`["gnda"]`** |
| `psub_connected_to_vdd_pin_no_diff` | **false** |
| `psub_connected_to_vss_pin_no_diff` | true |

### 2.3 Conclusion

**Removing the 128 `diff.drawing` rectangles eliminates the vout/vdda/gnda
merge.** Without diffusion, only `gnda` remains connected to the psub route.
This is a one-shot diagnostic proof that diffusion is the dominant mechanism.

Source: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/psub_substrate_geometry.json`

---

## 3. The Psub Route: A Diffusion Stripe, Not Metal

MAGICAL's P&R implements the gnda substrate connection as a **horizontal
diffusion stripe** across the entire chip bottom:

| Property | Value |
| --- | --- |
| Net | gnda |
| Layer | MAGICAL internal 6 → `diff.drawing` (65/20) |
| BBox | `[-1050, -450, 15050, -350]` (GDS coordinates) |
| Width | 16,100 units |
| Height | 100 units |

This stripe runs the full width of the chip at y = -450 to -350. It is a
**diffusion** layer, not a metal layer — MAGICAL uses it as the substrate
tap (psub route). In Sky130, `diff.drawing` (65/20) is the active diffusion
layer used for both NMOS source/drain AND p+ substrate taps.

**Why this matters**: When a diffusion stripe labeled "gnda" spans the entire
chip bottom, ALL diffusions in the layout are electrically connected through
the shared p-substrate. NMOS drain diffusions (connected to vout) and PMOS
drain diffusions (connected to vdda through nwell) become part of the same
substrate domain.

---

## 4. The 47-Step Conduction Path: gnda → vdda

The `psub_to_vdd_path` traces a continuous geometric chain from the gnda met5
rail to the vdda met5 pin, passing through diffusion and the metal stack:

| Step Range | Layer(s) | What happens |
| --- | --- | --- |
| 1–2 | met5 | Start at gnda vertical rail (x=950, y=-2050 to 11250) |
| 3–7 | via4→met4→via4→met5→via4→met4 | Cross from left gnda rail toward device area |
| 8–24 | met3→via2→met2→via→met1→mcon→li1→licon1→**diff** | Descend metal stack into **diffusion** at M22 location |
| 25–32 | licon1→li1→mcon→met1→via→met2→via2→met3→via3→met4 | Ascend back up through metal stack |
| 33–47 | via4→met5→...→met5.pin | Route through M7/M0 PMOS area to vdda pin |

**The critical segment is steps 8–24**: from met5 down through the full
contact+metal stack into `diff.drawing` at M22's location, then back up to
met4. This is where the diffusion layer bridges the gnda metal domain to the
vdda metal domain.

### Devices on the Path

| Device | Type | Role | Body collapse? |
| --- | --- | --- | --- |
| M22 | NMOS | Drain/Source diff provide psub contact | body→**vout** |
| M23 | NMOS | Drain/Source diff provide psub contact | body→**vout** |
| M20 | NMOS | Drain/Source diff provide psub contact | body→**vout** |
| M11 | PMOS | Nwell guard ring at diffusion level | body→vout (collapsed) |
| M7 | PMOS | Nwell guard ring at diffusion level | body→vout (collapsed) |
| M0 | PMOS | Nwell guard ring at diffusion level | body→a_25_4050# |
| M4 | PMOS | Nwell guard ring at diffusion level | body→vout (collapsed) |

---

## 5. Vout-Collapsed vs Internal-Collapsed NMOS: Spatial Analysis

### Body→vout NMOS (5 devices)

| Device | Layout box | Position | In psub→vdd path? |
| --- | --- | --- | --- |
| M23 | [5000, 11200, 6600, 12800] | Left-center | **Yes** |
| M22 | [7200, 11200, 8800, 12800] | Center | **Yes** |
| M20 | [3200, 14400, 4800, 16000] | Left | **Yes** |
| M18 | [5600, 20800, 7200, 22400] | Center | No |
| M17 | [3400, 21200, 5000, 22800] | Left | No |

### Body→internal NMOS (7 devices)

| Device | Layout box | Position |
| --- | --- | --- |
| M21 | [9400, 11200, 11000, 12800] | Right |
| M19 | [11600, 14400, 13200, 16000] | Far right |
| M16 | [8600, 16000, 10200, 17600] | Right-center |
| M15 | [6200, 16000, 7800, 17600] | Center |
| M14 | [11600, 19200, 13200, 20800] | Far right |
| M13 | [3200, 19200, 4800, 20800] | Left |
| M12 | [4600, 23200, 6200, 24800] | Left-center |

### Pattern

| Region | NMOS | Body→vout count | Body→internal count |
| --- | --- | --- | --- |
| Left (x=3200–5000) | M20, M17, M13 | 2 | 1 |
| Left-center (x=4600–6600) | M23, M12, M15 | 1 | 2 |
| Center-right (x=7200–10200) | M22, M16, M18 | 2 | 1 |
| Far right (x=9400–13200) | M21, M19, M14 | 0 | 3 |

The far-right NMOS (M21, M19, M14) are farthest from the gnda→vdda conduction
path and all collapse to internal nets rather than `vout`. This suggests the
vout collapse is strongest where the NMOS diffusion is closest to the
gnda→vdda path (left and center regions).

---

## 6. Candidate Collapse Mechanisms

### 6.1 Diffusion/Psub Overreach — PRIMARY CANDIDATE ✓

**Evidence**: The 128 `diff.drawing` rectangles form a continuous electrical
path through the p-substrate connecting gnda to vout and vdda. When diffusion
is excluded from connectivity analysis, only gnda remains connected to the
psub route.

**Mechanism**: In Sky130, NMOS source/drain are n+ diffusions in p-substrate.
The psub tap (p+ diffusion) at the chip bottom is also in the p-substrate.
Magic's extractor models the p-substrate as a single electrical node. Any
diffusion touching the p-substrate is connected to that node. The largest
connected net through the substrate becomes the substrate name — in Fan_SMC,
this is `vout` (due to large output-stage NMOS diffusions).

**SMCNR contrast**: SMCNR has only 3 NMOS with small diffusions, physically
separated from the vout-connected diffusions. The substrate remains `gnda`.

### 6.2 Met5 Routing Contamination — SECONDARY ✓

**Evidence (AH-SMC-012)**: Two separate met5 trees (gnda-left, unknown-right)
with a 300-unit gap at x=1850–2150. The met5 routing does not directly short
gnda to vout — the merge happens at the diffusion level below the metal stack.

**Role**: Met5 routing contributes to the problem by providing the metal
pathway that carries the merged signal from diffusion up to the port level,
but the actual **merge** occurs in the diffusion/substrate domain.

### 6.3 Pin Label/Shape Contamination — REJECTED ✗

**Evidence**: The psub_tap_injection.json from AH-SMC-009 confirms the
injected p+ tap was physically present, DRC-clean, and connected to the gnda
met5 rail. It did NOT change extraction. Pin labels and shapes are not the
primary mechanism.

### 6.4 Psub Tap / Local Power Geometry — REJECTED as sole cause ✗

**Evidence**: AH-SMC-009's top-level p+ substrate tap (one additional p+ tap
stack tied to gnda met5) had zero effect on extraction. A single tap cannot
override the dominant diffusion connectivity.

---

## 7. Candidate Geometry Mechanisms

| # | Mechanism | Evidence | Classification |
| --- | --- | --- | --- |
| C1 | 128 diff.drawing rectangles merge gnda/vdda/vout through p-substrate | psub_substrate_geometry.json: without-diff → only gnda | **PRIMARY** |
| C2 | MAGICAL "gnda route" as diffusion stripe spans entire chip bottom | psub_route_shape=[-1050,-450,15050,-350] on layer 6 | **PRIMARY** |
| C3 | 47-step conduction chain through M22/M23/M20 diffusion | psub_to_vdd_path passes through 3 NMOS | **PRIMARY** |
| C4 | Met5 routing gap between left/right trees | AH-SMC-012 met5 audit | **SECONDARY** |
| C5 | Nondeterministic MAGICAL routing | 3 runs, 3 different route.gds (AH-SMC-013R) | **SECONDARY** |

---

## 8. Minimal Diagnostic Proposal (NOT IMPLEMENTED)

### Proposal D1: Diffusion-isolation diagnostic

**Hypothesis**: If the 128 `diff.drawing` rectangles that merge gnda/vdda/vout
are masked (B1-style layer removal) in a diagnostic GDS copy, Magic extraction
should no longer produce `equiv "vout" "gnda"` or `equiv "vout" "vdda"`.

**Method**:
1. Copy the psub-tap GDS to an isolated AH-SMC-017 directory.
2. Use `mask_gds_layers_in_region.py` (existing tool at MAGICAL-/tools/sky130_adapter/)
   to mask `diff.drawing` (65/20) in a controlled rectangular region.
3. The mask should target only the horizontal psub stripe at y=[-450, -350]
   and the NMOS drain diffusions that bridge to vout.
4. Re-run Magic extraction and compare `.ext` substrate/equiv records.

**Expected result if H2 is correct**: `substrate` changes, `equiv` records
disappear, and gnda/vdda ports reappear in extracted SPICE.

**Risk**: Removing diff.drawing may break device recognition (NMOS/PMOS need
diffusion for terminal identification). This is a **diagnostic-only** mask —
NOT a repair.

**Status**: Proposal only. Requires Codex approval before GDS modification.

### Proposal D2: SMCNR-style geometry comparison

**Hypothesis**: SMCNR passes because its NMOS diffusions are physically
separated from vout-connected diffusions, avoiding the diffusion merge.

**Method**: Obtain or regenerate SMCNR GDS and `.ext`. Run the same
`psub_substrate_geometry` diagnostic on SMCNR. Compare:
- `psub_component_pin_overlaps` (with and without diff)
- `psub_active_dependent_vdd_path`
- `substrate` and `equiv` records

**Expected result**: SMCNR should show `psub_component_pin_overlaps: ["gnda"]`
even WITH diffusion, or at minimum should NOT show the three-way merge.

**Status**: Requires SMCNR GDS/.ext regeneration. Blocked by missing artifacts.

---

## 9. Hypothesis Assessment (Final)

| H | Claim | Status | Confidence | Evidence |
| --- | --- | --- | --- | --- |
| H1 | `.pin=-1` sole root cause | **DISPROVEN** | High | SMCNR also has pin=-1 but passes LVS |
| **H2** | **Diffusion/psub geometry dominates** | **PRIMARY CANDIDATE** | **High** | `psub_substrate_geometry.json` proves diffusion merges gnda/vdda/vout |
| H3 | Routing/met5 co-contaminates | **SECONDARY** | Medium | AH-SMC-012 met5 gap; not the merge mechanism |
| H4 | Netgen/LVS setup divergence | **DOWNGRADED** | N/A | Renames impossible under collapse topology |

---

## 10. Trust Boundary

```json
{
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true
}
```

All trust flags remain failure-case only. `.ext` contains `substrate "vout"`
and `equiv "vout" "vdda"` / `equiv "vout" "gnda"` — geometry-level diagnosis
required before any repair attempt.

---

## 11. Artifact Paths

| # | Artifact | Absolute Path |
| --- | --- | --- |
| 1 | psub_substrate_geometry.json | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/psub_substrate_geometry.json` |
| 2 | psub-tap `.ext` | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext` |
| 3 | device_mapping.json | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/device_mapping.json` |
| 4 | mask_gds_layers_in_region.py | `/home/qlf/IOT/references/MAGICAL-/tools/sky130_adapter/mask_gds_layers_in_region.py` |
| 5 | AH-SMC-012 met5 audit | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_012/ah_smc_012_summary.md` |
