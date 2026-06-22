# AH-SMC-021: `useDeviceSubGuardRing` Config-Level Diagnostic Probe

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-021 |
| Date | 2026-06-22 |
| Type | Config-level A/B diagnostic experiment |
| MAGICAL files modified | **None** |
| Parameter changed | `useDeviceSubGuardRing: false → true` in `fan_smc_pin_3.json` |
| Trust status | Failure-case only |

## Executive Summary

**Enabling `useDeviceSubGuardRing: true` changed MAGICAL's routing, Magic
extraction, and the substrate collapse center — but did NOT resolve the
fundamental vout/vdda/gnda equivalence.**

With guard rings enabled, the substrate shifted from `"net31"` to `"net050"`,
the equivalence count reduced from 4 to 3, and parasitic capacitance count
dropped from 95 to 92. However, `equiv "net050" "vdda"` and `equiv "net050"
"gnda"` persisted, and gnda/vdda remained absent from the extracted subcircuit
ports. **Both variants fail LVS with "Netlists do not match."**

The guard ring configuration affects how Magic resolves the dominant
substrate net but does not prevent the p-substrate merge — device-level
diffusions still connect vout/vdda/gnda through the shared substrate.

---

## 1. Config Delta

### JSON Diff

The only semantic difference between the two configs:

```diff
+    "useDeviceSubGuardRing": true
```

(Inline-to-multiline formatting difference is a `json.dump` artifact.)

| File | SHA256 |
| --- | --- |
| Baseline JSON | `16aaf53f94dc34adbad94e4d9c18c03d01d7e5e2f36ae523bdbf0c06d14e1cdb` |
| Guardring JSON | `003f91eb832c7376552bcedd252506e010b9fdb62d2371adf1b50f063291e97` |

---

## 2. MAGICAL P&R Output Comparison

| Metric | Baseline | Guardring True | Δ |
| --- | --- | --- | --- |
| `place.gds` size | 335,088 bytes | **428,336 bytes** | **+27.8%** |
| `route.gds` size | 359,924 bytes | **452,404 bytes** | **+25.7%** |
| `init.gds` size | 1,590,198 bytes | **1,669,814 bytes** | **+5.0%** |
| `ioPin` size | 564 bytes | 561 bytes | −3 bytes |
| GDS differ? | — | **Yes (all SHA256 differ)** | |

The substantial size increases confirm that MAGICAL generated additional
geometry (device-level guard rings) that cascaded through placement and
routing.

---

## 3. Magic Extraction Comparison

### 3.1 Substrate Identity

| Variant | Substrate | Anchor |
| --- | --- | --- |
| Baseline | `"net31"` | `0 0 1150 2950 m5` |
| Guardring True | **`"net050"`** | `0 0 310 -10 m1` |

### 3.2 Equivalence Records

| Variant | Count | Records |
| --- | --- | --- |
| Baseline | 4 | `net31↔net050`, `net31↔vout`, `net31↔vdda`, `net31↔gnda` |
| Guardring True | **3** | `net050↔vout`, `net050↔vdda`, `net050↔gnda` |

**net31 dropped from the equivalence set** when guard rings are enabled.
The collapse center shifted from net31 (PMOS input-pair body net) to net050
(C0 compensation capacitor bottom plate).

### 3.3 Port Short Warnings

| Variant | Short warnings |
| --- | --- |
| Baseline | `net31↔net050`, `net31↔vout`, `net31↔vdda`, `net31↔gnda` (4 pairs) |
| Guardring True | `net050↔vout`, `net050↔vdda`, `net050↔gnda` (3 pairs) |

### 3.4 Extracted Subcircuit Ports

| Variant | Port count | gnda/vdda present? |
| --- | --- | --- |
| Baseline | 15 (net31-centric) | **No** |
| Guardring True | 14 (net050-centric) | **No** |

Both variants drop gnda and vdda from the subcircuit because they are equated
to the dominant substrate net through the p-substrate.

### 3.5 MOS Device Count

| Variant | MOS count |
| --- | --- |
| Baseline | 24 |
| Guardring True | 24 |

Device recognition is preserved — no MOS devices were lost.

### 3.6 NMOS Body Terminal Sample

| Variant | Sample body nets |
| --- | --- |
| Baseline | `net31`, `net31`, `net31` |
| Guardring True | `net050`, `net050`, `net050` |

All NMOS bodies follow the dominant substrate net.

---

## 4. Netgen LVS Comparison

| Metric | Baseline | Guardring True |
| --- | --- | --- |
| LVS result | **Netlists do not match** | **Netlists do not match** |
| Parasitic caps | 95 | **92** |
| Source ports | `gnda vdda vinn vinp vout` (5) | `gnda vdda vinn vinp vout` (5) |
| Extracted ports | 15 (no gnda/vdda) | 14 (no gnda/vdda) |
| Port mismatch | 5 source vs 15/14 extracted | 5 source vs 14 extracted |

---

## 5. Analysis

### 5.1 Guard Rings DO Affect Extraction

Enabling `useDeviceSubGuardRing` produced measurable changes:
- MAGICAL P&R output size +25–28% (more geometry)
- Substrate shifted from net31 → net050
- Equiv count reduced 4 → 3
- Parasitic caps reduced 95 → 92

This confirms the parameter is functional and the code path is active.

### 5.2 Guard Rings Do NOT Prevent Substrate Collapse

However, `equiv net050↔vdda` and `equiv net050↔gnda` persisted. The
device-level guard rings add p+ tap geometry near each NMOS/PMOS, but
these taps sit on `diff.drawing` (65/20) which is the same layer as device
active diffusion. Magic treats all `diff.drawing` as connected through the
shared p-substrate, so adding more diff shapes (guard rings) does not break
the connectivity — it may even strengthen it.

### 5.3 Why net31 Dropped Out

net31 is the body net for the PMOS input pair (M8, M9). When individual
device guard rings are enabled, each PMOS gets its own NWELL guard ring
with a dedicated contact to vdda. This breaks the net31 body domain by
providing a direct vdda connection at each device, causing the substrate
to resolve to net050 (C0 bottom plate) instead of net31.

### 5.4 Why net050 Persists

net050 is C0's bottom plate terminal — a massive met5 structure spanning
the entire chip (`[1550, -50, 14650, 160]`). In the source netlist, C0
connects net050 to vout (compensation capacitor). When the substrate is
dominated by the largest connected diffusion area, the C0 bottom plate's
diffusion contact to the substrate causes Magic to name the substrate
`net050` and equate it to the electrically connected vout port.

### 5.5 The Root Cause Is Deeper Than Guard Rings

The fundamental problem is that in Sky130 Magic extraction:
1. `diff.drawing` (65/20) = active diffusion in p-substrate
2. NMOS source/drain are n+ in p-substrate
3. PMOS NWELL has n+ guard ring in p-substrate
4. The psub tap (p+ diffusion) connects to ground

When MAGICAL generates a layout with NMOS drains connected to vout and
PMOS NWELL guard rings connected to vdda, ALL of these diffusions are
in the same p-substrate domain. Magic correctly identifies them as
electrically connected. **The extraction is physically correct — the
substrate does connect these nets.** The fix requires either:
- Substrate isolation (triple-well, deep nwell) — not available in
  this Sky130 flow
- A different extraction approach that separates substrate connectivity
  from metal connectivity
- A Magic substrate model modification

---

## 6. Hypothesis Assessment

| H | Claim | Status | Δ |
| --- | --- | --- | --- |
| H1 | `.pin=-1` sole cause | DISPROVEN | — |
| H2 | Diffusion/psub geometry dominates | **PRIMARY CANDIDATE** | — |
| H2a | Remap aliasing | WEAKENED | — |
| H3 | Routing/met5 co-contaminates | SECONDARY | — |
| H4 | Setup divergence | DOWNGRADED | — |
| **H5** | **`useDeviceSubGuardRing` changes extraction but does not resolve collapse** | **CONFIRMED** | **NEW** |

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

---

## 8. Artifacts

| # | Artifact | Baseline path | Guardring path |
| --- | --- | --- | --- |
| 1 | JSON config | `.../baseline_control/case/fan_smc_pin_3.json` | `.../guardring_true/case/fan_smc_pin_3.json` |
| 2 | Route GDS | `.../baseline_control/case/fan_smc_pin_3.route.gds` | `.../guardring_true/case/fan_smc_pin_3.route.gds` |
| 3 | `.ext` | `.../baseline_control/case/fan_smc_pin_3_flat.ext` | `.../guardring_true/case/fan_smc_pin_3_flat.ext` |
| 4 | `.spice` | `.../baseline_control/case/fan_smc_pin_3_flat.spice` | `.../guardring_true/case/fan_smc_pin_3_flat.spice` |
| 5 | LVS report | `.../baseline_control/case/lvs_prepared/netgen_lvs.log` | `.../guardring_true/case/lvs_prepared/netgen_lvs.log` |
| 6 | JSON diff | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_021/json.diff` | — |
