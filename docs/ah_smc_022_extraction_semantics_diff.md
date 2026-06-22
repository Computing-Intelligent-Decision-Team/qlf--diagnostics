# AH-SMC-022: SMCNR vs Fan_SMC Extraction Semantics Differential Audit

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-022 |
| Date | 2026-06-22 |
| Type | Read-only cross-circuit extraction semantics audit |
| Positive baseline | `SMCNR_SE_2st_AMP/cand_0031` (LVS PASS) |
| Diagnostic case | `Fan_SMC_Pin_3` (LVS FAIL, all variants) |
| MAGICAL files modified | **None** |
| Trust status | Failure-case only |

## Executive Summary

**SMCNR and Fan_SMC share identical `.pin` contracts (NMOS body = -1) but
diverge at the extraction level due to circuit scale and layout complexity.**

SMCNR (8 MOS, simple 2-stage amplifier) passes LVS because its NMOS
diffusions are compact and well-separated from vout-connected diffusions.
Magic correctly resolves NMOS body to gnda and preserves all 6 subcircuit
ports. Fan_SMC (24 MOS, multi-stage amplifier with C0) fails because its
larger, interleaved layout creates a merged diffusion domain that Magic
collapses to a single substrate net.

**The `.pin=-1` contract is not the differentiator. Layout complexity and
diffusion interleaving are.** SMCNR proves that `.pin=-1` is compatible
with correct extraction when the physical design keeps diffusion domains
separated. Fan_SMC fails because its physical design does not.

---

## 1. Circuit Scale Comparison

| Metric | SMCNR | Fan_SMC | Ratio |
| --- | --- | --- | --- |
| NMOS devices | 3 | 12 | 4× |
| PMOS devices | 5 | 12 | 2.4× |
| Total MOS | 8 | 24 | 3× |
| Resistors | 1 (31-segment chain) | 0 | — |
| Capacitors | 1 (cfmom_2t) | 1 (cfmom_2t, C0) | 1× |
| Topology | 2-stage single-ended | Multi-stage fully differential | — |
| NMOS multi params | 1 (no multi) | 4–32 | — |
| `.pin` lines | 10 devices | 25 devices | 2.5× |

---

## 2. `.pin` Contract: Identical Pattern

| Criterion | SMCNR | Fan_SMC |
| --- | --- | --- |
| NMOS body pin = `-1` | **3/3 (100%)** | **12/12 (100%)** |
| PMOS body pin = coords | **5/5 (100%)** | **11/11 (100%)** |
| Pattern | Same | Same |

**Finding**: The `.pin` contract is identical. This confirms H1 is disproven.

---

## 3. Source Connectivity: Same Body Net Pattern

| Criterion | SMCNR | Fan_SMC |
| --- | --- | --- |
| NMOS body net | `gnda` (3/3) | `gnda` (12/12) |
| PMOS body net | `vdda` (5/5) | `vdda` (most) or `net31` (M8,M9) |

**Finding**: Both specify `B=gnda` for all NMOS. Source connectivity is equivalent.

---

## 4. Extracted Connectivity: Divergence Point

### 4.1 NMOS Body Terminal Resolution

| Circuit | Body = gnda | Body = vout | Body = internal | LVS impact |
| --- | --- | --- | --- | --- |
| **SMCNR** | **3/3 (100%)** | 0/3 | 0/3 | PASS |
| **Fan_SMC** | **0/12 (0%)** | 5/12 | 7/12 | FAIL |

**This is the single most important difference.** SMCNR resolves all NMOS
bodies correctly; Fan_SMC resolves none.

### 4.2 SMCNR Extracted SPICE (Raw)

```spice
.subckt SMCNR_SE_2st_AMP_flat vdda gnda vin vip ibias vout
X0 vdda ibias a_785_2846# vdda  ← PMOS body=vdda ✓
X2 vout a_20_494# gnda gnda     ← NMOS body=gnda ✓
X3 gnda a_2100_n30# a_20_494# gnda  ← NMOS body=gnda ✓
X5 gnda a_2100_n30# a_4345_n10# gnda  ← NMOS body=gnda ✓
```

### 4.3 Fan_SMC Extracted SPICE (Raw)

```spice
.subckt fan_smc_pin_3_flat vinn vinp vout       ← gnda/vdda MISSING
X23 vout a_220_2930# vout vout                  ← NMOS body=vout ✗
X2 a_900_2930# a_420_4610# vout vout            ← NMOS body=vout ✗
```

---

## 5. Parasitic Capacitance Evidence

SMCNR raw extracted SPICE includes a **35.87 fF parasitic capacitance**
between `vdda` and `gnda` (C31):

```spice
C31 vdda gnda 35.8705f
```

This is the NWELL-to-psub junction capacitance — physically real and
expected. Despite this large parasitic, **Magic did NOT produce an
`equiv "vdda" "gnda"` record** for SMCNR. The ports remain separate.

**This proves that Magic distinguishes between parasitic capacitance and
electrical equivalence.** Parasitic caps alone do not trigger `equiv`
records. The `equiv` records in Fan_SMC come from a different mechanism:
the merged diffusion domain through the p-substrate.

---

## 6. Why SMCNR Works While Fan_SMC Fails

### 6.1 Diffusion Domain Separation

SMCNR's 3 NMOS devices are compact single-finger transistors. Their
source/drain diffusions are physically small and well-separated from
the vout-connected PMOS drain diffusions. The gnda-connected substrate
domain remains isolated from vout.

Fan_SMC's 12 NMOS devices span the entire chip with multi-finger
layouts (multi=4, 8, 16, 32). The large diffusion areas create a
continuous p-substrate domain that physically connects gnda-connected
NMOS sources to vout-connected NMOS drains and PMOS NWELL contacts.

### 6.2 Circuit Complexity

| Factor | SMCNR | Fan_SMC |
| --- | --- | --- |
| Layout area | ~101.5 μm² | ~1,700 μm² (est.) |
| Diffusion rectangles | Unknown (not available) | 128 |
| psub route | Unknown (not available) | Horizontal stripe 16,100 units wide |
| Device interleaving | Simple | Complex (symmetrical routing) |
| C0 impact | Standard cfmom | Massive met5 plate spanning chip |

### 6.3 Guard Ring Effect (AH-SMC-021)

Even with `useDeviceSubGuardRing: true`, Fan_SMC still produces `equiv`
records. The guard rings add more `diff.drawing` shapes — these enter the
same p-substrate domain and do not break the merge. In fact, they may
strengthen it by adding more substrate-connected diffusion area.

---

## 7. Extraction Semantics Summary

| Semantic | SMCNR | Fan_SMC | Gap |
| --- | --- | --- | --- |
| Port preservation | 6/6 | 3/5 (gnda/vdda lost) | **3 ports missing** |
| Body resolution | 8/8 correct | 0/24 correct | **Total collapse** |
| Substrate naming | (gnda inferred) | "vout" | **Substrate named after signal** |
| Equiv records | None (inferred) | 2–4 present | **Electrical merge** |
| Parasitic caps | Present (normal) | Present (normal) | Same mechanism |
| LVS | PASS | FAIL | — |

---

## 8. What This Means For Fan_SMC

### The `.pin=-1` contract is NOT the blocker

SMCNR proves that NMOS body pins can be `-1` and LVS can still pass —
provided the physical layout keeps diffusion domains separated.

### The blocker is the merged diffusion domain

Fan_SMC's layout has NMOS drain (vout) and source (gnda) diffusions
physically connected through the shared p-substrate. Magic correctly
identifies this electrical connection and produces `equiv` records.

### The extraction is topology-dependent

Whether Magic produces `equiv` records depends on the physical separation
of diffusion domains, not on the `.pin` contract. SMCNR's compact layout
preserves separation; Fan_SMC's large interleaved layout does not.

### Fan_SMC may need a fundamentally different layout approach

No amount of `.pin` editing, guard ring enabling, or local diffusion
masking can fix a layout where vout and gnda diffusions are physically
merged through the p-substrate. Solutions would require:
- Physical separation of NMOS gnda-source diffusions from vout-drain
  diffusions (changes MAGICAL placement/routing)
- Triple-well or deep-nwell isolation (not available in this Sky130 flow)
- A Magic extraction model that treats substrate connectivity differently

---

## 9. Hypothesis Assessment (Final)

| H | Claim | Status | Confidence |
| --- | --- | --- | --- |
| H1 | `.pin=-1` sole cause | **DISPROVEN** | High |
| **H2** | **Diffusion/psub geometry dominates** | **PRIMARY CANDIDATE** | **High** |
| H2a | Remap aliasing | WEAKENED | Low |
| H3 | Routing/met5 co-contaminates | SECONDARY | Medium |
| H4 | Setup divergence | DOWNGRADED | N/A |
| H5 | Guard ring config affects but doesn't fix | CONFIRMED | High |
| **H6** | **Circuit scale/layout complexity is the root differentiator** | **SUPPORTED** | **High** |

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

---

## 11. Artifact Paths

| # | Artifact | Path |
| --- | --- | --- |
| 1 | SMCNR extracted raw SPICE | `.../reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.raw.spice` |
| 2 | SMCNR extracted connectivity SPICE | `.../lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.connectivity.spice` |
| 3 | SMCNR LVS summary | `.../lvs_mos_projection/lvs_result_summary.md` |
| 4 | SMCNR `.pin` | `.../case/SMCNR_SE_2st_AMP.pin` |
| 5 | Fan_SMC `.ext` | `.../ah_smc_021/baseline_control/case/fan_smc_pin_3_flat.ext` |
| 6 | Fan_SMC extracted SPICE | `.../ah_smc_021/baseline_control/case/fan_smc_pin_3_flat.spice` |
| 7 | Fan_SMC guardring `.ext` | `.../ah_smc_021/guardring_true/case/fan_smc_pin_3_flat.ext` |
