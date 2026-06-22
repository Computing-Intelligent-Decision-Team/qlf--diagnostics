# AH-SMC-019: Fan_SMC Diffusion Semantics / Provenance Audit

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-019 |
| Date | 2026-06-22 |
| Type | Read-only diffusion provenance audit |
| MAGICAL files modified | **None** |
| Trust status | Failure-case only |

## Executive Summary

**All 128 Fan_SMC `diff.drawing` shapes originate from MAGICAL internal
layer 6/0 (OD), remapped 1:1 to Sky130 layer 65/20 with no semantic
distinction between device active diffusion, guard rings, edge stripes, and
psub route.**

17 of 128 shapes (13.3%) are **outside all MOS device layout boxes** and
represent non-device diffusion: chip-edge guard rings (left/right vertical
strips, 150×28,250 each), horizontal edge stripes (top/bottom, 15,850 wide),
and a bottom-right structure resembling a guard ring or test artifact. These
shapes are invisible to the per-device fanout analysis but are physically
present in the GDS and electrically connected through Magic's p-substrate
model.

**This is a remap-level semantic aliasing problem**: MAGICAL's OD layer
serves multiple purposes (device active, guard ring, substrate route), but
the Sky130 remap exports all of them uniformly as `diff.drawing`. Magic
interprets ALL `diff.drawing` shapes as active diffusion connected through
the shared p-substrate, merging vout/vdda/gnda.

---

## 1. Layer Provenance Chain

```
MAGICAL P&R (internal)          Sky130 remap            Magic extraction
─────────────────────          ────────────            ─────────────────
layer 6/0 (OD, 128 shapes)  →  65/20 diff.drawing  →  p-substrate domain
                                65/44 tap.drawing       (1 tap from AH-SMC-009)
```

### Verified 1:1 Correspondence

| Source | Layer | Count | BBoxes identical? |
| --- | --- | --- | --- |
| MAGICAL route GDS | 6/0 (OD) | 128 | — |
| Sky130 remapped GDS | 65/20 (diff.drawing) | 128 | **Yes** (all 128 match 1:1) |

**Source files**:
- MAGICAL route GDS: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.route.gds`
- Sky130 remapped GDS: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds`

---

## 2. Diff Shape Classification

### 2.1 By Device Proximity

| Classification | Count | % | Area (total) |
| --- | --- | --- | --- |
| **Inside MOS device boxes** | 111 | 86.7% | ~95% of diff area |
| **Outside all device boxes** | 17 | 13.3% | ~5% of diff area |
| Overlapping multiple devices | 0 | 0% | — |
| Touching psub route | 3 | 2.3% | Bottom edge stripe |

### 2.2 Outside-Device Shapes — Detailed Breakdown

#### Group A: Chip-Edge Vertical Guard Rings (2 shapes)

| Shape | BBox | Size | Area | Likely function |
| --- | --- | --- | --- | --- |
| Left edge | `[-1075, -325, -925, 27925]` | 150×28,250 | 4,237,500 | Left chip-edge nwell/OD guard |
| Right edge | `[14925, -325, 15075, 27925]` | 150×28,250 | 4,237,500 | Right chip-edge nwell/OD guard |

**Interpretation**: These are full-height vertical diffusion stripes at the
chip left and right edges. In Sky130, they become `diff.drawing` and are
treated as part of the active p-substrate domain. They directly connect the
chip-edge psub to all internal diffusions.

#### Group B: Horizontal Edge Stripes (4 shapes + 3 corner squares)

| Shape | BBox | Size | Area | Function |
| --- | --- | --- | --- | --- |
| Bottom psub stripe | `[-925, -475, 14925, -325]` | 15,850×150 | 2,377,500 | Psub route / gnda tap |
| Top edge stripe | `[-925, 27925, 14925, 28075]` | 15,850×150 | 2,377,500 | Top edge OD |
| Bottom-left corner | `[-1075, -475, -925, -325]` | 150×150 | 22,500 | Corner fill |
| Bottom-right corner | `[14925, -475, 15075, -325]` | 150×150 | 22,500 | Corner fill |
| Top-left corner | `[-1075, 27925, -925, 28075]` | 150×150 | 22,500 | Corner fill |
| Top-right corner | `[14925, 27925, 15075, 28075]` | 150×150 | 22,500 | Corner fill |

**Interpretation**: The bottom stripe is MAGICAL's gnda psub route. The top
stripe and edge guard rings form a complete perimeter frame of `diff.drawing`
around the chip. In Magic, this creates a continuous p-substrate domain that
touches ALL internal diffusions.

#### Group C: Bottom-Right Guard Ring Structure (9 shapes)

| Shape | BBox | Size | Area |
| --- | --- | --- | --- |
| Main block | `[925, 23050, 2275, 24050]` | 1,350×1,000 | 1,350,000 |
| Left vertical | `[525, 22675, 675, 24525]` | 150×1,850 | 277,500 |
| Right vertical | `[2525, 22675, 2675, 24525]` | 150×1,850 | 277,500 |
| Bottom horizontal | `[675, 22525, 2525, 22675]` | 1,850×150 | 277,500 |
| Top horizontal | `[675, 24525, 2525, 24675]` | 1,850×150 | 277,500 |
| 4 corner squares | various | 150×150 each | 22,500 each |

**Total Group C**: 9 shapes, ~2.7M area units.

**Interpretation**: A rectangular ring structure at the bottom-right of the
chip (x=525-2675, y=22525-24675). This resembles an NWELL guard ring or an
isolated OD structure. It is NOT associated with any MOS device (no instance
layout_box overlaps it). It may be a MAGICAL-generated guard ring for the
resistor (xr0 / C0 area) or a route artifact.

---

## 3. Remap Semantics Analysis

### 3.1 MAGICAL Internal Layer 6 ↔ Sky130 65/20 Mapping

The remap configuration (`sky130_gds_export_map.yaml`) maps:

```
MAGICAL internal layer 6/0 → Sky130 65/20 (diff.drawing)
```

This is a **uniform, non-contextual mapping**: ALL shapes on MAGICAL layer 6
are exported as Sky130 `diff.drawing`, regardless of their function.

### 3.2 Semantic Aliasing

MAGICAL layer 6 (OD) serves at least FOUR distinct purposes:

| Purpose | Expected Sky130 layer | Actual Sky130 layer | Aliased? |
| --- | --- | --- | --- |
| MOS active (source/drain) | `diff.drawing` (65/20) | `diff.drawing` (65/20) | ✓ Correct |
| NWELL guard ring | `nwell.drawing` (64/20) or `tap.drawing` (65/44) | `diff.drawing` (65/20) | **✗ Aliased** |
| Psub route / substrate tap | `tap.drawing` (65/44) | `diff.drawing` (65/20) | **✗ Aliased** |
| Chip-edge OD stripes | `diff.drawing` (65/20) or omitted | `diff.drawing` (65/20) | **✗ Questionable** |

### 3.3 Existing Tap Split (Insufficient)

The `split_sky130_tap_from_diff.py` step in the pipeline only reclassifies
shapes that overlap with pin labels — it does NOT address the guard ring or
edge stripe aliasing. AH-SMC-008 confirmed this split changed 104 OD records
but did not change Magic extraction.

### 3.4 Impact on Magic Extraction

In Sky130 Magic extraction:
1. `diff.drawing` (65/20) = active diffusion in p-substrate
2. `tap.drawing` (65/44) = p+ substrate tap in p-substrate
3. BOTH are electrically connected through the shared p-substrate

When guard rings, edge stripes, and the psub route are all mapped to
`diff.drawing`, Magic sees them as additional active diffusion regions
connected to the same p-substrate domain. This merges what should be
separate electrical domains (vout, vdda, gnda) into a single substrate node.

---

## 4. SMCNR Comparison (Evidence Gap)

**SMCNR's `diff.drawing` classification is not available** because SMCNR's
GDS contains the remapped Sky130 shapes but the per-instance layout boxes
and device_mapping are not in the local reproducibility package.

However, SMCNR's extracted SPICE shows body=gnda for all NMOS, suggesting
SMCNR either:
- Has fewer outside-device diff shapes (simpler topology)
- Has guard rings on different layers (correctly mapped)
- Has a different OD-to-Sky130 remap configuration

Without SMCNR's GDS and remap configuration, this cannot be confirmed.

---

## 5. Proposed Non-Device-Diff Mask Plan (NOT IMPLEMENTED)

### Hypothesis

If non-device `diff.drawing` shapes (Groups A, B, C) are remapped to a
different layer (e.g., `tap.drawing` 65/44) or removed, Magic would no
longer merge the vout/vdda/gnda substrate domain.

### Candidate Mask Shapes

| Group | Shapes | Count | Proposed Action | Risk |
| --- | --- | --- | --- | --- |
| A: Edge guard rings | Left/right vertical strips | 2 | Remap to 65/44 (tap.drawing) | May break NWELL biasing |
| B: Horizontal edge stripes | Top/bottom + corners | 7 | Remap to 65/44 | Bottom stripe IS the gnda tap — keep as-is? |
| C: Bottom-right guard ring | 9 shapes | 9 | Remap to 65/44 or remove | May be R0/C0 guard ring — needed for LVS? |
| **Total** | | **18** | | |

Note: The bottom stripe (Group B, 3 shapes) is the only diffusion touching
the psub route directly. AH-SMC-018 Variant B showed masking these 3 shapes
had zero effect. Therefore the edge guard rings and bottom-right structure
are more likely candidates for the substrate merge.

### Risk Assessment

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Remapping guard rings may break PMOS NWELL contacts | High | PMOS devices need NWELL connection |
| Removing Group C may break xr0 or C0 recognition | Medium | Test extraction after mask |
| Edge stripes may be needed for DRC | Low | DRC is 0 even with modified shapes |

### Status: Proposal Only

Requires Codex approval before any GDS modification.

---

## 6. Hypothesis Assessment (Updated)

| H | Claim | Status | Confidence |
| --- | --- | --- | --- |
| H1 | `.pin=-1` sole cause | **DISPROVEN** | High |
| **H2** | **Diffusion/psub geometry dominates** | **PRIMARY CANDIDATE** | **High** |
| H2a | Remap aliasing (OD→diff.drawing uniform) is a contributing mechanism | **NEW CANDIDATE** | Medium |
| H3 | Routing/met5 co-contaminates | SECONDARY | Medium |
| H4 | Netgen/LVS setup divergence | DOWNGRADED | N/A |

### New Finding: H2a (Remap Aliasing)

The uniform mapping of MAGICAL layer 6/0 → Sky130 65/20 merges device
diffusion, guard rings, edge stripes, and psub route into a single Magic
layer. This is a **semantic aliasing** problem at the remap level that
may be the root mechanism behind H2.

---

## 7. Trust Boundary

```json
{
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true
}
```

All trust flags remain failure-case only.

---

## 8. Artifact Paths

| # | Artifact | Absolute Path |
| --- | --- | --- |
| 1 | MAGICAL route GDS | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.route.gds` |
| 2 | Sky130 remapped GDS | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds` |
| 3 | Device mapping | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/device_mapping.json` |
| 4 | remap_gds_to_sky130.py | `/home/qlf/IOT/references/MAGICAL-/tools/sky130_adapter/remap_gds_to_sky130.py` |
| 5 | split_sky130_tap_from_diff.py | `/home/qlf/IOT/references/MAGICAL-/tools/sky130_adapter/split_sky130_tap_from_diff.py` |
