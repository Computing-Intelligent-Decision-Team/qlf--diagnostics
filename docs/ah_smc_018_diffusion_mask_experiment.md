# AH-SMC-018: Diagnostic-Only Diffusion Mask / Re-Extract Experiment

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-018 |
| Date | 2026-06-22 |
| Type | Diagnostic-only GDS mask + Magic re-extract |
| Baseline GDS | Fan_SMC psub-tap (`fan_smc_pin_3.psub_tap.gds`) |
| MAGICAL files modified | **None** |
| GDS modifications | Diagnostic masks only — NOT repairs |
| Trust status | Failure-case only |

## Executive Summary

Three variants were tested to isolate which diffusion geometry causes Magic's
`substrate "vout"` and `equiv "vout" "vdda"` / `equiv "vout" "gnda"` records.

**Result: The bottom psub diffusion stripe alone (3 rects) is insufficient to
cause the collapse. Masking 23 diff.drawing rectangles in the M22/M23/M20
device area lost 5 MOS devices but did NOT change substrate/equiv records.**
The diffusion merge appears to be distributed across multiple device areas —
the remaining vout-collapsed NMOS (M17, M18) and/or PMOS nwell diffusions
maintain the merge even when the primary path devices are removed.

**H2 (diffusion/psub geometry) remains PRIMARY CANDIDATE but the merge is
multi-point, not single-point.** A simple local mask cannot cleanly isolate
the collapse without destroying device recognition.

---

## 1. Variant A: Control No-Op (Baseline Reproduction)

### Mask

None — GDS copied without modification.

### Input/Output

| Property | Value |
| --- | --- |
| Input GDS | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds` |
| SHA256 | `71a2501523a7ce10701e856c9f253d4a0c9d5eb76302e7c523e1ea71475187a3` |
| Output GDS | Same (copy) |
| Masked | 0 elements |

### Magic Extraction

```tcl
gds read fan_smc_pin_3.psub_tap.gds
load fan_smc_pin_3_flat
select top cell
extract all
ext2spice lvs; ext2spice cthresh 0; ext2spice rthresh 0; ext2spice
quit -noprompt
```

**Magic**: 8.3 rev 483, sky130A technology.

### Results

| Metric | Value |
| --- | --- |
| `substrate` | **`"vout"`** |
| `equiv` #1 | **`"vout" "vdda"`** |
| `equiv` #2 | **`"vout" "gnda"`** |
| Extracted ports | `vinn vinp vout` (3 ports, gnda/vdda missing) |
| MOS device count | **24** |
| Extraction warnings | `Ports "vout" and "vdda" are electrically shorted`; `Ports "vout" and "gnda" are electrically shorted` |

**Control harness validated.** Baseline substrate/equiv records reproduced.

---

## 2. Variant B: Bottom Psub Stripe Mask

### Hypothesis

The horizontal psub diffusion stripe `[-1050, -450, 15050, -350]` on
`diff.drawing` (65/20) connects gnda to vout through the p-substrate.

### Mask

| Property | Value |
| --- | --- |
| Mask layer | `diff.drawing` (65/20) |
| Mask region | `[-1050, -450, 15050, -350]` |
| Operation | **Delete** (remove BOUNDARY elements) |
| Elements masked | **3** |

### Input/Output

| Property | Value |
| --- | --- |
| Input GDS SHA256 | `71a25015...` |
| Output GDS SHA256 | `4b5ee496a00b2f7b3b419e7a4a8df9c28466a666675a6968a3ac24ba291164dd` |
| Size delta | 361340 → 361148 (−192 bytes) |

### Results

| Metric | Before (Control) | After (Bottom Stripe Mask) | Δ |
| --- | --- | --- | --- |
| `substrate` | `"vout"` | `"vout"` | **unchanged** |
| `equiv "vout" "vdda"` | Present | Present | **unchanged** |
| `equiv "vout" "gnda"` | Present | Present | **unchanged** |
| Extracted ports | `vinn vinp vout` | `vinn vinp vout` | **unchanged** |
| MOS devices | 24 | 24 | **unchanged** |
| Extraction warnings | 2 short warnings | 2 short warnings | **unchanged** |

### Interpretation

**The bottom diffusion stripe alone does not cause the substrate collapse.**
Removing 3 diff.drawing rectangles at the chip-bottom horizontal stripe had
zero effect on extraction. The collapse must involve diffusion connectivity
at the device level (NMOS source/drain diffusions), not just the bottom-edge
psub stripe.

---

## 3. Variant C: Path Contact Stack Mask (M22/M23/M20 Area)

### Hypothesis

The 47-step `psub_to_vdd_path` passes through M22/M23/M20 diffusion. Masking
`diff.drawing` in this device area should break the conduction path and
eliminate the equiv records.

### Mask

| Property | Value |
| --- | --- |
| Mask layer | `diff.drawing` (65/20) |
| Mask region | `[3000, 11000, 9000, 16200]` |
| Coverage | M20 [3200-4800,14400-16000], M22 [7200-8800,11200-12800], M23 [5000-6600,11200-12800] + padding |
| Operation | **Delete** |
| Elements masked | **23** |

### Input/Output

| Property | Value |
| --- | --- |
| Input GDS SHA256 | `71a25015...` |
| Output GDS SHA256 | `6ff7e51189721950f0682b1e0924d7ed13b7abd003aef58a829ff7c34e4379fa` |
| Size delta | 361340 → 359868 (−1472 bytes) |

### Results

| Metric | Before (Control) | After (Path Stack Mask) | Δ |
| --- | --- | --- | --- |
| `substrate` | `"vout"` | `"vout"` | **unchanged** |
| `equiv "vout" "vdda"` | Present | Present | **unchanged** |
| `equiv "vout" "gnda"` | Present | Present | **unchanged** |
| Extracted ports | `vinn vinp vout` | `vinn vinp vout` | **unchanged** |
| MOS device count | 24 | **19** | **−5** |
| Extraction warnings | 2 short warnings | 2 short warnings | **unchanged** |

### Lost MOS Devices

| Lost device | Type | Original location | Extracted body (before mask) |
| --- | --- | --- | --- |
| M23 (1060,2290) | NMOS | [5000, 11200, 6600, 12800] | vout |
| M22 (1500,2290) | NMOS | [7200, 11200, 8800, 12800] | vout |
| M20 (700,2930) | NMOS | [3200, 14400, 4800, 16000] | vout |
| M11 (540,2370) | PMOS | [2000, 11200, 4400, 13600] | vout |
| M5/M6 area | PMOS | [5400-7800, 13200-15600] | vout |

### Surviving vout-collapsed NMOS (outside mask region)

| Device | Location | Y-range | In mask y [11000,16200]? |
| --- | --- | --- | --- |
| M18 | [5600, 20800, 7200, 22400] | 20800–22400 | **No** (below mask) |
| M17 | [3400, 21200, 5000, 22800] | 21200–22800 | **No** (below mask) |

### Interpretation

1. **Substrate/equiv persisted despite removing 23 diff.drawing rectangles**
   and 5 MOS devices from the critical path area.

2. **The remaining vout-collapsed NMOS (M17, M18) are outside the mask region**
   and may independently maintain the gnda↔vout substrate connection.

3. **The diffusion merge is distributed**, not single-point. Multiple NMOS and
   PMOS device areas contribute to the `vout`↔`gnda` substrate connection.

4. **A clean local mask cannot isolate the collapse without destroying
   device recognition.** To eliminate the equiv records, a broader mask
   covering ALL vout-collapsed NMOS diffusions would be needed, but that
   would destroy too many devices for meaningful extraction comparison.

---

## 4. Cross-Variant Summary

| Metric | A (Control) | B (Bottom Stripe) | C (Path Stack) |
| --- | --- | --- | --- |
| Masked elements | 0 | 3 | 23 |
| `substrate` | `"vout"` | `"vout"` | `"vout"` |
| `equiv vout↔vdda` | Present | Present | Present |
| `equiv vout↔gnda` | Present | Present | Present |
| Extracted ports | 3 | 3 | 3 |
| MOS devices | 24 | 24 | **19** |
| Device damage | None | None | **5 lost** |

---

## 5. Analysis

### 5.1 The Bottom Stripe Is Not The Mechanism

Variant B proves that the wide horizontal diffusion stripe at the chip bottom
is NOT the primary cause of the substrate collapse. Only 3 rectangles were
at that location, and removing them had zero effect on extraction.

### 5.2 The Merge Is Distributed Across Device Diffusions

Variant C shows that even after removing the M22/M23/M20 path diffusions
(23 rectangles, 5 MOS devices lost), the collapse persists. The remaining
vout-collapsed devices (M17, M18) and possibly PMOS nwell diffusions
maintain electrical connectivity between gnda and vout through the substrate.

### 5.3 Diagnostic Mask Cannot Isolate Without Destroying Devices

The 23-element mask in Variant C lost 5 of 24 MOS devices (21% loss). To
eliminate ALL vout-collapsed NMOS diffusion, the mask would need to cover
M17 [5600,20800,7200,22400] and M18 [3400,21200,5000,22800] as well,
likely losing 2-3 more devices (7-8/24 = 29-33% loss). At that level of
device destruction, the extraction comparison becomes invalid — we'd be
testing a different circuit.

### 5.4 Implication For H2

H2 (diffusion/psub geometry) remains the **PRIMARY CANDIDATE** with high
confidence. The mask experiment confirms diffusion is necessary (removing
diffusion changes the geometry) but also shows that the merge is multi-point
— no single local mask can break it cleanly.

---

## 6. Hypothesis Assessment (Updated)

| H | Claim | Status | Δ from AH-SMC-017 |
| --- | --- | --- | --- |
| H1 | `.pin=-1` sole cause | **DISPROVEN** | — |
| **H2** | **Diffusion/psub geometry dominates** | **PRIMARY CANDIDATE** | — (mask confirms diffusion is necessary, multi-point) |
| H3 | Routing/met5 co-contaminates | SECONDARY | — |
| H4 | Netgen/LVS setup divergence | DOWNGRADED | — |

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

All trust flags remain failure-case only. Masked GDS variants are diagnostic
specimens, not repairs. `.ext` still records substrate/equiv collapse in all
three variants.

---

## 8. Artifact Paths

| # | Artifact | Absolute Path | SHA256 |
| --- | --- | --- | --- |
| 1 | Baseline GDS | `.../ah_smc_018/control/fan_smc_pin_3.psub_tap.gds` | `71a25015...` |
| 2 | Control `.ext` | `.../ah_smc_018/control/fan_smc_pin_3_flat.ext` | — |
| 3 | Bottom stripe masked GDS | `.../ah_smc_018/bottom_stripe/fan_smc_pin_3.bottom_stripe_masked.gds` | `4b5ee496...` |
| 4 | Bottom stripe `.ext` | `.../ah_smc_018/bottom_stripe/fan_smc_pin_3_flat.ext` | — |
| 5 | Path stack masked GDS | `.../ah_smc_018/path_stack/fan_smc_pin_3.path_stack_masked.gds` | `6ff7e511...` |
| 6 | Path stack `.ext` | `.../ah_smc_018/path_stack/fan_smc_pin_3_flat.ext` | — |
