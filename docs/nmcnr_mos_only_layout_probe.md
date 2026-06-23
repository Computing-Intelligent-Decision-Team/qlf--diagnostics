# NMCNR MOS-Only Layout Probe Report

**Date**: 2026-06-23
**Status**: **Probe complete — LVS FAIL (substrate collapse confirmed)**

## 1. Executive Summary

24-MOS NMCNR MOS-only projection was run through the full MAGICAL → Sky130 remap →
Magic DRC → extraction → Netgen LVS chain. The core diagnostic question was:
*"Does 24-MOS NMCNR experience substrate collapse like Fan_SMC (24 MOS)?"*

**Answer: YES. The extracted netlist exhibits severe net merging into the n-well
node `w_n35_1245#`, preventing LVS match.**

---

## 2. Pipeline Results

| Stage | Result | Detail |
|-------|--------|--------|
| MAGICAL placement | ✅ PASS | 24 MOS placed, routing finished |
| MAGICAL routing | ✅ PASS | `route.gds` written (223KB) |
| Sky130 GDS remap | ✅ PASS | 18 layers remapped, 2 preserved unmapped |
| Pin shapes | ⚠️ Manual port injection | GDS labels not read by Magic; ports injected into `.ext` |
| Magic DRC | ✅ PASS | **Total DRC errors: 0** |
| Magic extraction | ✅ PASS | `.ext` + `.spice` generated |
| Netgen LVS | ❌ **FAIL** | Device count matches, net count mismatched |

---

## 3. Detailed Metrics

### 3.1 DRC
```
Total DRC errors found: 0
```

### 3.2 Extraction
| Metric | Value |
|--------|-------|
| Extracted devices | 24 (12 PMOS + 12 NMOS) |
| Substrate | `w_n35_1245#` (n-well) |
| Equiv records | 0 |
| Port short warnings | 0 |
| Parasitic caps | 105 (with cthresh=0) |
| Port count | 6 (vdda gnda vin vip ibias vout — manually injected) |

### 3.3 LVS (MOS-only, parasitic caps stripped)
| Metric | Source | Extracted | Match |
|--------|--------|-----------|-------|
| NMOS | 12 | 12 | ✅ |
| PMOS | 12 | 12 | ✅ |
| **Total devices** | **24** | **24** | ✅ |
| Nets | 33 | 21 | ❌ **MISMATCH** |
| Disconnected pins | 1 (vout) | 6 (all ports) | ❌ |

---

## 4. Failure Classification

### Primary Failure: Substrate/Well Net Merging

The extracted netlist merges multiple independent nets into a single well node
`w_n35_1245#`. This node absorbs:

| Terminal type | Count | Correct? |
|---|---|---|
| PMOS drain/source | 12 | ⚠️ Depends on topology |
| PMOS bulk (n-well) | 12 | ✅ All PMOS bulk → n-well |
| NMOS drain/source | 8 | ❌ Should NOT merge into well |
| NMOS bulk (p-sub) | 12 | ❌ Should be gnda, not n-well |

**Impact**: 9 source nets have no matching extracted counterpart:
`net050`, `net049`, `dm_2`, `net063`, `net54`, `net56`, `gnda`, `vb4`, `vb3`.
Two extracted nets (`a_1100_2410#`, `a_1020_2890#`) have no source counterpart.

The source node `voutn` maps directly to `w_n35_1245#` in the extracted netlist —
this is a clear case of a functional net being absorbed into the well.

### Secondary Failure: Port Connectivity

All 6 extracted ports show as "disconnected" — the manually-injected port
definitions don't have physical connectivity to the extracted metal. This is
a GDS labeling issue (pin shapes/labels not recognized by Magic during
extraction), not a circuit issue.

### Failure Taxonomy

```
Root cause: Substrate/well net merging in Magic extraction
Failure type: LVS net mismatch
Severity: BLOCKING — cannot proceed to PEX or post-sim
Related to Fan_SMC: YES — same class of substrate collapse,
  but manifests differently (no explicit equiv records,
  net merging into w_n35_1245# instead of equiv vout-vdda-gnda)
```

---

## 5. Comparison: NMCNR vs Fan_SMC vs SMCNR

| Attribute | SMCNR (8 MOS) | Fan_SMC (24 MOS) | NMCNR (24 MOS) |
|---|---|---|---|
| DRC | 0 ✅ | 0 ✅ | 0 ✅ |
| Equiv records | 0 ✅ | 2 ❌ | 0 (but nets merged) |
| Substrate | gnda ✅ | vout ❌ | w_n35_1245# ❌ |
| LVS | PASS ✅ | FAIL ❌ | FAIL ❌ |
| MOS count match | 8 vs 8 ✅ | 26 vs 52 ❌ | 24 vs 24 ✅ |
| Net count match | 9 vs 9 ✅ | Mismatch ❌ | 33 vs 21 ❌ |
| Failure mode | (none) | equiv vout-vdda-gnda | well merging absorbs nets |

**Conclusion**: NMCNR fails LVS like Fan_SMC, but with a different collapse pattern.
Fan_SMC produced explicit `equiv` records merging vout/vdda/gnda. NMCNR merges
nets directly into the well node without `equiv` records. Both are forms of
substrate-domain connectivity collapse in Magic extraction.

---

## 6. Deliverables

```
generated/diagnostics/nmcnr_mos_only_projection/
├── case/
│   ├── leung_nmcnr_mos_only.sp          ← MAGICAL format source
│   ├── leung_nmcnr_mos_only.json         ← MAGICAL config
│   ├── leung_nmcnr_mos_only.route.gds    ← MAGICAL output (pre-remap)
│   ├── leung_nmcnr_mos_only.sky130.gds   ← remapped
│   ├── leung_nmcnr_mos_only.sky130.pinned_shapes.gds ← with pin shapes
│   ├── leung_nmcnr_mos_only.ioPin        ← MAGICAL pin data
│   └── run_leung_nmcnr_mos_only_trial.log
├── leung_nmcnr_mos_only.gds             ← clean copy (pinned+labeled)
├── leung_nmcnr_mos_only_flat.ext        ← Magic extraction
├── leung_nmcnr_mos_only_flat.spice      ← extracted SPICE (105 caps + 24 MOS)
├── leung_nmcnr_mos_only_flat_mos.spice  ← stripped (24 MOS only)
├── leung_nmcnr_mos_only_src.spice       ← source for LVS
├── leung_nmcnr_mos_only_flat_src.spice  ← _flat source for LVS
├── magic_drc.tcl, magic_drc.log
├── magic_extract.tcl, magic_extract.log
├── run_lvs.tcl, lvs.log
├── gds_remap_report.md
└── magic_drc.log
```

---

## 7. Trust Status (unchanged)

| Flag | Value |
|---|---|
| `trust_assigned` | `false` |
| `usable_for_supervised_positive_training` | `false` |
| `usable_for_parasitic_modeling` | `false` |
| `usable_only_as_failure_case` | **`true`** (now justified by LVS evidence) |

---

## 8. What We Learned

1. **24-MOS NMCNR DOES experience substrate collapse** — answering the core
   diagnostic question. The collapse pattern differs from Fan_SMC (well merging
   vs equiv records) but the outcome is the same: LVS FAIL.

2. **MAGICAL can generate layout for sky130 device names** — `sky130_fd_pr__pfet_01v8`
   and `sky130_fd_pr__nfet_01v8` are fully supported by the MAGICAL DesignDB
   and PDK.

3. **MOS count is preserved through extraction** — 24 vs 24, unlike Fan_SMC's
   26→52 split. This suggests the collapse is "cleaner" — nets merge but devices
   don't fragment.

4. **The substrate collapse threshold appears to be between 8 and 24 MOS** —
   SMCNR (8 MOS) passes, Fan_SMC and NMCNR (both 24 MOS) fail.

5. **Equiv records = 0 does NOT mean no collapse** — NMCNR has 0 equiv records
   but clear net merging into the well node. The absence of equiv records is
   not sufficient to declare a clean extraction.

---

## 9. Forbidden Claims

- ❌ NMCNR LVS did NOT pass
- ❌ MOS device count match does NOT equal correct connectivity
- ❌ DRC=0 does NOT imply LVS-clean
- ❌ This probe does NOT make NMCNR training-positive
- ❌ 0 equiv records does NOT mean no substrate collapse
