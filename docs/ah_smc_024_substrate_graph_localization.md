# AH-SMC-024: Fan_SMC Substrate/Equiv Graph Localization

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-024 |
| Date | 2026-06-22 |
| Type | Read-only substrate graph trace from `.ext` records |
| MAGICAL files modified | **None** |
| Trust status | Failure-case only |

## Executive Summary

**The Fan_SMC substrate collapse is a port-level phenomenon.** Magic's `.ext`
file records `equiv "vout" "vdda"` and `equiv "vout" "gnda"`, merging exactly
three top-level ports into a single electrical domain. All 24 MOS devices
have at least one terminal in this equivalence class, and 5 of 12 NMOS have
body directly assigned to `vout`.

SMCNR, by contrast, records `substrate "gnda"` with **zero** equiv records and
preserves all 6 ports. The substrate equivalence class contains only `{gnda}`
— a single net, not a merged domain.

**The collapse mechanism**: Fan_SMC's 128 `diff.drawing` shapes create a
continuous p-substrate domain that electrically connects vout-associated
NMOS drain diffusions to gnda-associated NMOS source diffusions and vdda-
associated PMOS NWELL contacts. Magic detects this geometric connectivity
and records the equivalence. No single device or local region is responsible
— the merge is a global layout property.

---

## 1. Substrate Graph: Side-by-Side

### SMCNR (LVS PASS)

| Field | Value |
| --- | --- |
| `substrate` | **`"gnda"`** |
| `equiv` records | **0** (none) |
| Equiv class | `{gnda}` (1 net) |
| Ports | `vdda gnda vin vip ibias vout` (6) |
| Ports in equiv class | Only `gnda` |
| Devices touching equiv | NMOS sources (3) — correct body connection |

Source: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_023/SMCNR_SE_2st_AMP_flat.ext`

### Fan_SMC (LVS FAIL)

| Field | Value |
| --- | --- |
| `substrate` | **`"vout"`** |
| `equiv` records | **2** (`vout↔vdda`, `vout↔gnda`) |
| Equiv class | `{vout, vdda, gnda}` (3 nets) |
| Ports | `vinn vinp vout vdda gnda` (5) |
| Ports in equiv class | `vout, vdda, gnda` (3 of 5) |
| Devices touching equiv | **24/24 (100%)** |

Source: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext`

---

## 2. Fan_SMC Collapse Structure

### 2.1 Equivalence Class Composition

```
{vout, vdda, gnda}
```

Only three top-level ports are in the equivalence class. No internal `a_*#`
nodes are directly equated. This means Magic's `equiv` records are about
port-level merging, not internal node merging.

### 2.2 Device Participation

| Category | Count | Detail |
| --- | --- | --- |
| NMOS affected | 12/12 | All have terminals touching equiv class |
| PMOS affected | 12/12 | All have terminals touching equiv class |
| NMOS body = `vout` | 5 | M23, M22, M20, M18, M17 |
| NMOS body = internal `a_*#` | 7 | Routed through internal nets connected to equiv class |
| PMOS body = `vout` | 4 | Direct substrate collapse |
| PMOS body = internal `a_*#` | 8 | Routed through internal nets |

### 2.3 Internal Net Bridge Analysis

The 7 NMOS bodies assigned to `a_*#` internal nets are NOT directly equated
to vout, but their device terminals (drain, source, or gate) ARE connected
to the equivalence class through the device channels:

```
vout (port, in equiv class)
  → NMOS drain (device terminal)
    → NMOS channel
      → NMOS source = a_*# (internal net)
        → connects to other devices
          → eventually reaches gnda or vdda through more device channels
```

This is the **device-channel bridge**: Magic's extractor models the MOSFET
channel as a conductive path between drain and source. When drain is vout
(in equiv class) and source connects through internal nets to gnda, the
entire chain becomes electrically equivalent.

### 2.4 Key Bridge Devices

The devices that directly bridge vout to the equiv class:

| Device | Drain | Source | Body | Bridge type |
| --- | --- | --- | --- | --- |
| M23 (NMOS) | vout | vout | vout | **D/B/S all vout — fully collapsed** |
| M22 (NMOS) | vout | vout | vout | D/B/S all vout |
| M11 (PMOS) | a_1500_2270# | vout | vout | S/B = vout |
| M10 (PMOS) | vout | vout | vout | **All 4 terminals vout** |

**All 24 devices serve as bridges** — each has at least drain or source
connected to the equiv class through its device channel.

---

## 3. Diffusion Node Analysis

### 3.1 SMCNR Diffusion Nodes

58 nodes total, including device-internal diffusion contacts. The compact
layout keeps `ndif` (NMOS) and `pdif` (PMOS) nodes physically separated.

### 3.2 Fan_SMC Diffusion Nodes

18 nodes total (fewer, larger nodes due to multi-finger devices):
- 7 `ndif` (NMOS diffusion) nodes
- 5 `pdif` (PMOS diffusion) nodes
- 4 `p` (poly gate) nodes
- 2 `li` (local interconnect) nodes

The 7 `ndif` nodes represent large merged NMOS diffusion regions (multi-finger
devices share diffusion), while the 5 `pdif` nodes represent PMOS diffusions.
Both types connect through the p-substrate.

---

## 4. Collapse Mechanism Diagram

```
                    Magic p-substrate model
                    ═══════════════════════
                    
    ┌──────────┐    substrate "vout"    ┌──────────┐
    │  vout    │◄──────────────────────►│  gnda    │
    │  (port)  │    equiv "vout" "gnda" │  (port)  │
    └────┬─────┘                        └────┬─────┘
         │                                   │
    ┌────▼─────┐                        ┌────▼─────┐
    │ NMOS     │    device channel      │ NMOS     │
    │ drain    │◄──────────────────────►│ source   │
    │ (ndif)   │    through p-sub       │ (ndif)   │
    └──────────┘                        └──────────┘
         │                                   │
    ┌────▼─────┐                        ┌────▼─────┐
    │  equiv   │◄───── "vdda" ─────────►│  vdda    │
    │  class   │    equiv "vout" "vdda" │  (port)  │
    └──────────┘                        └──────────┘
    
    128 diff.drawing shapes provide the physical connectivity
    through the shared p-substrate in Magic's extraction model
```

---

## 5. Comparison With SMCNR

### Why SMCNR Avoids This

1. **Substrate correctly named `gnda`** — the ground-connected NMOS source
   diffusions dominate the p-substrate domain, not vout.

2. **No equiv records** — Magic finds no geometric path connecting vout
   to gnda through the substrate. The 56 diff.drawing shapes are physically
   separated into distinct domains.

3. **All 6 ports preserved** — `ext2spice` sees no port equivalence, so
   all ports appear in the subcircuit declaration.

### Why Fan_SMC Triggers This

1. **Substrate named `vout`** — the vout-connected NMOS drain diffusions
   (large multi-finger devices) dominate the p-substrate domain.

2. **equiv vout↔vdda, vout↔gnda** — Magic finds geometric paths through
   the 128 diff.drawing shapes connecting all three ports.

3. **Port collapse** — `ext2spice` drops gnda and vdda from the subcircuit
   because Magic has declared them equivalent to vout.

---

## 6. What This Means For Repair

### The Problem Is Global, Not Local

AH-SMC-018 and AH-SMC-020 proved that local diffusion masks cannot break
the collapse. This graph analysis explains why: **all 24 devices participate
in the equivalence class through their device channels.** Removing a few
diffusion shapes doesn't break the global connectivity — there are always
alternative paths through other devices.

### Possible Repair Directions

| Direction | Mechanism | Feasibility |
| --- | --- | --- |
| Substrate model change | Tell Magic to treat PSUB/NWELL as separate domains | Requires Magic source modification |
| Physical isolation | Add deep-nwell or triple-well to isolate vout from gnda | Not available in this Sky130 flow |
| Diffusion domain separation | Modify MAGICAL placement to physically separate NMOS source/drain diffusions | Requires MAGICAL placement constraint changes |
| Post-extraction fix | Strip equiv records from `.ext` before ext2spice | Diagnostic only; not a real repair |

---

## 7. Hypothesis Assessment

| H | Claim | Status |
| --- | --- | --- |
| H1 | `.pin=-1` sole cause | DISPROVEN |
| **H2** | **Diffusion/psub geometry dominates** | **PRIMARY CANDIDATE** |
| **H6** | **Layout complexity is root differentiator** | **CANDIDATE_STRONG** |
| **H7** | **Collapse is port-level, device-global** | **SUPPORTED** |

### H7 (New)

The collapse is a **port-level, device-global phenomenon**: exactly three
ports (vout, vdda, gnda) are merged into a single equivalence class through
device-channel connectivity across all 24 MOS devices. No single device or
local region is responsible — the merge is a global layout property.

---

## 8. Trust Boundary

```json
{
  "usable_for_reward": false, "usable_for_post_sim": false,
  "usable_for_training": false, "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true
}
```

---

## 9. Artifacts

| # | Artifact | Path |
| --- | --- | --- |
| 1 | Fan_SMC `.ext` | `.../fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext` |
| 2 | SMCNR `.ext` (regenerated) | `.../ah_smc_023/SMCNR_SE_2st_AMP_flat.ext` |
| 3 | Substrate graph trace script | `.../ah_smc_024/trace_substrate_graph.py` |
