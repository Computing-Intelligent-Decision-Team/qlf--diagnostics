# AH-SMC-020: Diagnostic Non-Device OD Mask / Re-Extract Experiment

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-020 |
| Date | 2026-06-22 |
| Type | Diagnostic mask experiment — non-device OD shapes |
| Baseline GDS | Fan_SMC psub-tap (`fan_smc_pin_3.psub_tap.gds`) |
| MAGICAL files modified | **None** |
| GDS modifications | Diagnostic only — NOT repairs |
| Trust status | Failure-case only |

## Executive Summary

**Removing or remapping the 17 non-device `diff.drawing` shapes had no effect
on Magic's substrate/equiv records.** All three variants produced identical
extraction state: `substrate "vout"`, `equiv "vout" "vdda"`, `equiv "vout"
"gnda"`, and 3-port extracted subcircuit (`vinn vinp vout`).

**H2a (remap aliasing of non-device OD) is WEAKENED.** The 17 outside-device
shapes (guard-ring candidates, edge stripes, bottom-right ring) are
NOT the primary cause of the substrate collapse. The collapse must originate
from the 111 device-active diff shapes or from a more fundamental layer
semantics issue.

---

## 1. Variant A: Control No-Op

| Metric | Value |
| --- | --- |
| GDS SHA256 | `71a25015...` (baseline) |
| Masked elements | 0 |
| `substrate` | `"vout"` |
| `equiv` | `"vout" "vdda"`, `"vout" "gnda"` |
| Extracted ports | `vinn vinp vout` (3) |
| MOS devices | **24** |
| Harness validated | ✓ |

---

## 2. Variant B: Delete 17 Non-Device Diff Shapes

| Property | Value |
| --- | --- |
| Mask operation | **Delete** `diff.drawing` (65/20) |
| Target shapes | 17 outside-device shapes (Groups A, B, C from AH-SMC-019) |
| Elements masked | 17 |
| GDS SHA256 | `6e79ab93...` |

### Extraction Results

| Metric | Before | After | Δ |
| --- | --- | --- | --- |
| `substrate` | `"vout"` | `"vout"` | **unchanged** |
| `equiv vout↔vdda` | Present | Present | **unchanged** |
| `equiv vout↔gnda` | Present | Present | **unchanged** |
| Extracted ports | 3 | 3 | **unchanged** |
| MOS devices | 24 | **23** | **−1** |

**One MOS device was lost** because at least one of the masked shapes
overlapped a device's active diffusion area. The 17 "outside-device" shapes
were identified by device `layout_box` overlap, but the `layout_box` is
an approximate bounding box — a shape may be classified as "outside" if
it lies outside the box even if it's functionally part of the device's
diffusion geometry.

---

## 3. Variant C: Remap 17 Shapes to `tap.drawing` (65/44)

| Property | Value |
| --- | --- |
| Mask operation | **Rewrite** 65/20 → 65/44 |
| Target shapes | Same 17 shapes as Variant B |
| Elements remapped | 17 |
| GDS SHA256 | `8727d64b...` |

### Extraction Results

| Metric | Before | After | Δ |
| --- | --- | --- | --- |
| `substrate` | `"vout"` | `"vout"` | **unchanged** |
| `equiv vout↔vdda` | Present | Present | **unchanged** |
| `equiv vout↔gnda` | Present | Present | **unchanged** |
| Extracted ports | 3 | 3 | **unchanged** |
| MOS devices | 24 | **23** | **−1** |

**Remapping to `tap.drawing` also had no effect.** Even with the 17 shapes
reclassified to a different substrate layer, Magic's extractor still produces
the same substrate/equiv records. `tap.drawing` (65/44) is also a p-substrate
layer in Sky130, so shapes on this layer are still connected through the
shared p-substrate domain.

---

## 4. Cross-Variant Summary

| Metric | A (Control) | B (Delete) | C (Remap→Tap) |
| --- | --- | --- | --- |
| Masked/changed | 0 | 17 | 17 |
| `substrate` | `"vout"` | `"vout"` | `"vout"` |
| `equiv` records | 2 | 2 | 2 |
| Ports | 3 | 3 | 3 |
| MOS devices | 24 | **23** | **23** |
| Device damage | None | −1 | −1 |

---

## 5. Analysis

### 5.1 Non-Device OD Is NOT The Primary Mechanism

The 17 shapes identified in AH-SMC-019 (edge guard ring candidates, horizontal
edge stripes, bottom-right ring structure) are NOT the primary cause of the
substrate collapse. Removing them entirely (Variant B) or remapping them to
`tap.drawing` (Variant C) did not change Magic's extraction.

### 5.2 H2a Is Weakened

The remap aliasing hypothesis (H2a from AH-SMC-019) is weakened by this
experiment. If uniform OD→diff.drawing mapping were the root cause, removing
the aliased non-device shapes should have had some effect. It did not.

### 5.3 The Collapse Must Originate From Device-Active Diffusion

Since removing outside-device shapes did nothing, and AH-SMC-018 showed that
even masking device-area diffusion (23 shapes, M22/M23/M20) didn't break the
collapse, the mechanism must involve the **111 device-active diff shapes**
across a broader set of devices — possibly ALL NMOS source/drain diffusions
are interconnected through the shared p-substrate in a way that local masks
cannot break.

### 5.4 `tap.drawing` Also Enters Substrate Semantics

Variant C (remap to tap) confirms that `tap.drawing` (65/44) is also treated
as part of the p-substrate domain by Magic. So remapping diff→tap does not
escape the substrate connectivity — both layers share the same p-substrate
electrical node.

---

## 6. Cumulative Mask Experiment Results

| Experiment | Task | Shapes changed | Substrate Δ | Equiv Δ | MOS Δ |
| --- | --- | --- | --- | --- | --- |
| Bottom stripe delete | AH-SMC-018-B | 3 | None | None | 0 |
| Path stack delete | AH-SMC-018-C | 23 | None | None | −5 |
| Non-device delete | AH-SMC-020-B | 17 | None | None | −1 |
| Non-device remap→tap | AH-SMC-020-C | 17 | None | None | −1 |

**Across 4 mask experiments (60 total shapes modified), substrate/equiv
records never changed.** The collapse is robust against local diffusion
manipulation.

---

## 7. Hypothesis Assessment (Updated)

| H | Claim | Status | Confidence | Δ |
| --- | --- | --- | --- | --- |
| H1 | `.pin=-1` sole cause | DISPROVEN | High | — |
| H2 | Diffusion/psub geometry dominates | PRIMARY CANDIDATE | High | — |
| H2a | Remap aliasing of non-device OD | **WEAKENED** | Low | ↓ |
| H3 | Routing/met5 co-contaminates | SECONDARY | Medium | — |
| H4 | Setup divergence | DOWNGRADED | N/A | — |

---

## 8. Trust Boundary

```json
{
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true
}
```

---

## 9. Artifact Paths

| Variant | GDS | SHA256 | MOS |
| --- | --- | --- | --- |
| A (Control) | `.../ah_smc_020/control/fan_smc_pin_3.psub_tap.gds` | `71a25015...` | 24 |
| B (Delete) | `.../ah_smc_020/delete_nondev/fan_smc_pin_3.delete_nondev.gds` | `6e79ab93...` | 23 |
| C (Remap) | `.../ah_smc_020/remap_to_tap/fan_smc_pin_3.remap_to_tap.gds` | `8727d64b...` | 23 |
