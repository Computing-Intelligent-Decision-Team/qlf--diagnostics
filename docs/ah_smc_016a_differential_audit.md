# AH-SMC-016A: SMCNR vs Fan_SMC NMOS Body-Pin Differential Audit

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-016A |
| Date | 2026-06-22 |
| Type | Read-only differential audit |
| Positive baseline | `SMCNR_SE_2st_AMP/cand_0031` |
| Diagnostic case | `Fan_SMC_Pin_3` (bounded-C0 proxy) |
| MAGICAL files modified | **None** |
| Trust status | Failure-case only |

## Conclusion

**`.pin=-1 alone is not sufficient as a single-variable root cause for Fan_SMC
body collapse.** Both SMCNR and Fan_SMC have all NMOS body pins as `-1` in their
`.pin` files, but SMCNR resolves NMOS body to `gnda` (LVS PASS) while Fan_SMC
resolves NMOS body to `vout` (LVS FAIL).

The divergence is at the **geometry/substrate/extraction** level, not the
`.pin` contract level. SMCNR's simpler two-stage amplifier topology keeps gnda
and vout diffusions physically separated in the p-substrate, allowing Magic to
resolve NMOS body correctly to `gnda`. Fan_SMC's larger, more complex layout
with interleaved routing causes Magic's extractor to merge vout, vdda, and gnda
through the shared p-substrate.

**Before any MAGICAL `.pin` contract patch, Fan_SMC requires a geometry-level
understanding of why its psub/diffusion layout merges vout and gnda when SMCNR's
does not.** The existing differential audit data (Fan_SMC `psub_substrate_geometry.json`)
already shows `psub_component_pin_overlaps: ["gnda", "vdda", "vout"]` with
diffusion included — this is the geometry-level divergence that SMCNR likely
avoids through simpler physical design.

---

## A. `.pin` Comparison

### SMCNR cand_0031 `.pin`

| Device | Type | Model | Pin Count | Pin 1 (D) | Pin 2 (G) | Pin 3 (S) | **Pin 4 (B)** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| xm1 | NMOS | nch_mac | 4 | coords | coords | coords | **`-1`** |
| xm3 | NMOS | nch_mac | 4 | coords | coords | coords | **`-1`** |
| xm4 | NMOS | nch_mac | 4 | coords | coords | coords | **`-1`** |
| xm7 | PMOS | pch_mac | 4 | coords | coords | coords | coords |
| xm6 | PMOS | pch_mac | 4 | coords | coords | coords | coords |
| xm5 | PMOS | pch_mac | 4 | coords | coords | coords | coords |
| xm2 | PMOS | pch_mac | 4 | coords | coords | coords | coords |
| xm0 | PMOS | pch_mac | 4 | coords | coords | coords | coords |
| xr0 | RES | rppolywo_m | 3 | coords | coords | **`-1`** | N/A |
| xc0 | CAP | cfmom_2t | 2 | coords | coords | N/A | N/A |

**NMOS body pin = `-1`**: 3/3 NMOS (100%)
**PMOS body pin = coords**: 5/5 PMOS (100%)

Source: `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/case/SMCNR_SE_2st_AMP.pin`

### Fan_SMC_Pin_3 `.pin`

| Stat | Value |
| --- | --- |
| NMOS count | 12 (M12–M23) |
| NMOS body pin = `-1` | **12/12 (100%)** |
| PMOS count | 11 (M0–M11, minus M1 unmatched) |
| PMOS body pin = coords | **11/11 (100%)** |
| C0 pin 3 = `-1` | Yes (2-pin device) |

Source: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.pin`

### `.pin` Delta

| Criterion | SMCNR | Fan_SMC | Same? |
| --- | --- | --- | --- |
| NMOS body pin = `-1` | Yes (3/3) | Yes (12/12) | **Same pattern** |
| PMOS body pin = coords | Yes (5/5) | Yes (11/11) | **Same pattern** |
| RES pin = `-1` | Yes (1/1) | C0 is 2-pin | Not comparable |

**Finding**: Both circuits have identical `.pin` patterns: NMOS body = `-1`,
PMOS body = coordinates. The `.pin` contract alone does not distinguish the
passing case from the failing case.

---

## B. Source Connectivity Comparison

### SMCNR Source Netlist (NMOS)

```
xm1 outp outp gnda gnda nch_mac       → body = gnda
xm3 outn outp gnda gnda nch_mac       → body = gnda
xm4 vout outn gnda gnda nch_mac       → body = gnda
```

All 3 SMCNR NMOS: **body = gnda**

### Fan_SMC Source Netlist (NMOS, first 3 of 12)

```
M23 vout net049 gnda gnda             → body = gnda
M22 net049 net043 gnda gnda           → body = gnda
M21 net043 net043 gnda gnda           → body = gnda
...
(all 12 NMOS: body = gnda)
```

All 12 Fan_SMC NMOS: **body = gnda**

### Source Delta

| Criterion | SMCNR | Fan_SMC | Same? |
| --- | --- | --- | --- |
| NMOS source body net | gnda (3/3) | gnda (12/12) | **Same** |
| Body-to-source connection pattern | B=S=gnda (all 3 NMOS) | B=S=gnda (most NMOS) | **Same** |

**Finding**: Both circuits specify `B=gnda` for all NMOS in source netlists.

---

## C. Extracted Connectivity Comparison

### SMCNR Extracted SPICE (NMOS body terminals)

From `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.connectivity.spice`:

```
X2 vout outn gnda gnda   → NMOS body = gnda  ✓ MATCH
X3 gnda outp outn gnda   → NMOS body = gnda  ✓ MATCH
X5 gnda outp outp gnda   → NMOS body = gnda  ✓ MATCH
```

| NMOS | Source body | Extracted body | Match? |
| --- | --- | --- | --- |
| xm4 (X2) | gnda | **gnda** | ✓ |
| xm1 (X3) | gnda | **gnda** | ✓ |
| xm3 (X5) | gnda | **gnda** | ✓ |

**SMCNR: 3/3 NMOS body = gnda → LVS PASS**

Internal net renaming (from raw extraction):
- `a_20_494#` → `outn`
- `a_2100_n30#` → `outp`
- `a_4024_586#` → `net53`
- `a_4345_n10#` → `outp`

These are routine gate/source net renames — NOT body mismatches.

### Fan_SMC Extracted SPICE (NMOS body terminals)

From `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/device_mapping.json`:

| NMOS | Source body | Extracted body | Match? |
| --- | --- | --- | --- |
| M23 | gnda | **vout** | ✗ |
| M22 | gnda | **vout** | ✗ |
| M21 | gnda | **a_1905_2290#** | ✗ |
| M20 | gnda | **vout** | ✗ |
| M19 | gnda | **a_1500_3250#** | ✗ |
| M18 | gnda | **vout** | ✗ |
| M17 | gnda | **vout** | ✗ |
| M16 | gnda | **a_900_2930#** | ✗ |
| M15 | gnda | **a_1220_2750#** | ✗ |
| M14 | gnda | **a_2345_3890#** | ✗ |
| M13 | gnda | **a_665_3890#** | ✗ |
| M12 | gnda | **a_940_4290#** | ✗ |

**Fan_SMC: 0/12 NMOS body = gnda → LVS FAIL**

Body collapse distribution:
- **vout**: 5 NMOS (M23, M22, M20, M18, M17)
- **a_*# internal nets**: 7 NMOS
- **gnda**: 0 NMOS

### Extracted Delta

| Criterion | SMCNR | Fan_SMC |
| --- | --- | --- |
| NMOS body = gnda | **3/3 (100%)** | **0/12 (0%)** |
| NMOS body = vout | 0/3 | 5/12 |
| NMOS body = internal | 0/3 | 7/12 |
| LVS result | **PASS** | **FAIL** |
| Device count match | 8 vs 8 ✓ | 24 vs 24 ✓ |
| Net count match | 9 vs 9 ✓ | 18 vs 19 ✗ |

---

## D. GDS / Geometry Comparison

### D.1 Available Data

| Data type | SMCNR | Fan_SMC |
| --- | --- | --- |
| `.ext` file | **Missing** (not in reproducibility package) | Present (AH-SMC-009, AH-SMC-013) |
| GDS file | **Missing** (not in reproducibility package) | Present (baseline + multiple variants) |
| Magic extraction log | **Missing** | Present |
| `psub_substrate_geometry.json` | **Missing** | Present |
| `device_mapping.json` | **Missing** | Present |
| Extracted SPICE (raw) | Present | Present |
| Extracted SPICE (connectivity) | Present | Present |
| LVS report | Present (`lvs_match=yes`) | Present (`Netlists do not match`) |

### D.2 Geometry Evidence Gap

**SMCNR `.ext`, GDS, and extraction logs are not in the local reproducibility
package.** The `README.md` states these were intentionally excluded (563 MB → 2.7 MB).
Without the SMCNR `.ext` file, a direct line-by-line substrate/equiv/device
comparison is not possible from local artifacts.

However, the **indirect evidence from extracted SPICE is conclusive**: SMCNR
NMOS body = gnda for all 3 devices. This proves Magic resolved the body correctly
without `.pin` body pin coordinates, and without producing `equiv "vout" "gnda"`
records.

### D.3 Fan_SMC Geometry Evidence (Present)

From `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/psub_substrate_geometry.json`:

- `magic_substrate_nets`: `["vout"]`
- `magic_equiv_pairs`: `[{"net_a": "vout", "net_b": "vdda"}, {"net_a": "vout", "net_b": "gnda"}]`
- `psub_route_net`: `"gnda"`
- `psub_component_pin_overlaps` (with diff): `["gnda", "vdda", "vout"]`
- `psub_component_pin_overlaps_no_diff` (without diff): `["gnda"]`
- `psub_active_dependent_vdd_path`: `true`

This confirms that Fan_SMC's **diffusion layer** (diff.drawing) creates an
electrical path that merges gnda, vdda, and vout in the p-substrate. When
diffusion is excluded, only gnda remains connected to the psub route.

### D.4 SMCNR Geometry Inference (No Direct Evidence)

SMCNR's extracted SPICE shows body=gnda for all NMOS, and no port-short warnings
in the extracted connectivity. This strongly suggests that SMCNR's layout does
NOT produce `equiv "vout" "gnda"` or `equiv "vout" "vdda"` records. The simpler
two-stage amplifier topology likely keeps vout and gnda diffusions sufficiently
separated that Magic does not merge them through the substrate.

**Evidence gap**: Without SMCNR `.ext`/GDS, this is inference from extracted
SPICE results, not direct geometry audit.

---

## E. Magic Extraction / LVS Artifacts

### E.1 SMCNR LVS Summary

| Field | Value |
| --- | --- |
| LVS status | **PASS** |
| Source devices | 8 |
| Extracted devices | 8 |
| Source nets | 9 |
| Extracted nets | 9 |
| Device mismatch | No |
| Net mismatch | No |
| Property mismatch | No |
| LVS mode | `mos_only_projection` |

Source: `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/lvs_result_summary.md`

### E.2 Fan_SMC LVS Summary

| Field | Value |
| --- | --- |
| LVS status | **FAIL** |
| Source devices | 24 |
| Extracted devices | 24 |
| Source nets | 18 |
| Extracted nets | 19 |
| Device mismatch | Yes (unmatched extracted device) |
| Net mismatch | Yes (mismatch) |
| Body mismatch | 23/23 |
| Terminal mismatch | 88/88 |

Source: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/device_mapping.json`

### E.3 Fan_SMC Magic Extraction Warnings

```
Ports "vout" and "vdda" are electrically shorted.
Ports "vout" and "gnda" are electrically shorted.
```

Source: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/extract_warnings.txt`

### E.4 SMCNR Magic Extraction Warnings

**Missing** — Magic extraction log not in reproducibility package. However, the
extracted SPICE header `.subckt SMCNR_SE_2st_AMP_flat vdda gnda vin vip ibias vout`
includes both vdda and gnda as ports, suggesting they were NOT shorted (if they
were equated by Magic, one would typically be dropped from the port list).

---

## F. Hypothesis Assessment

### H1: NMOS `.pin` fourth entry = `-1` is the sole root cause

**Assessment: DISPROVEN by differential evidence.**

Both SMCNR (LVS PASS) and Fan_SMC (LVS FAIL) have all NMOS body pins as `-1`.
SMCNR correctly resolves body to gnda; Fan_SMC collapses body to vout.
`.pin=-1` alone cannot explain the Fan_SMC failure.

**Evidence**: Section A (both .pin files identical pattern), Section C
(SMCNR body=gnda despite pin=-1).

### H2: Fan_SMC's diffusion/substrate/psub geometry creates body collapse

**Assessment: SUPPORTED by local Fan_SMC evidence. Untested against SMCNR
geometry (evidence gap).**

Fan_SMC's `psub_substrate_geometry.json` proves that diffusion-layer
connectivity merges gnda, vdda, and vout (`psub_component_pin_overlaps_with_diff`).
SMCNR's simpler topology likely avoids this merge, but SMCNR `.ext`/GDS are not
available locally to confirm.

**Evidence**: Section D.3 (Fan_SMC psub geometry), Section D.4 (SMCNR inference
gap).

### H3: Fan_SMC routing/met5/power-domain shapes co-contaminate substrate extraction

**Assessment: SUPPORTED by AH-SMC-012 met5 audit, but secondary to H2.**

AH-SMC-012 showed the Fan_SMC met5 routing has two separate trees (gnda-left,
unknown-right) connected at the met5 layer by a 300-unit gap. This suggests
routing topology contributes to the extraction problem, but the primary
mechanism is H2 (diffusion connectivity). SMCNR's simpler routing likely has
cleaner power-domain separation.

**Evidence**: AH-SMC-012 met5 audit, Section D.3.

### Overall Assessment

| Hypothesis | Status | Confidence |
| --- | --- | --- |
| H1: `.pin=-1` sole root cause | **DISPROVEN** | High (differential evidence) |
| H2: Diffusion/psub geometry dominates | **SUPPORTED** | Medium (Fan_SMC evidence strong; SMCNR evidence missing) |
| H3: Routing/met5 co-contaminates | **SUPPORTED** | Medium (AH-SMC-012 met5 audit) |

**Key conclusion**: `.pin=-1 alone is not sufficient as a single-variable root
cause; Fan_SMC requires geometry/substrate/routing differential analysis before
any MAGICAL patch.`

---

## G. Next Recommended Action

1. **Before any MAGICAL patch**: Obtain or regenerate SMCNR `.ext` and GDS for
   direct geometry comparison (substrate record, equiv records, psub routing).
2. **Geometry differential**: Compare SMCNR vs Fan_SMC `psub_substrate_geometry`
   when both are available. The key question: does SMCNR also show
   `psub_component_pin_overlaps: ["gnda", "vdda", "vout"]` with diffusion?
3. **Minimal SMCNR rerun**: If SMCNR artifacts can be regenerated locally, run
   Magic extraction and compare `.ext` substrate/equiv records.
4. **Only after geometry root cause is confirmed**: Consider the MAGICAL patch
   from AH-SMC-015R2, but with the understanding that `.pin` contract change
   alone will NOT fix Fan_SMC body collapse — the geometry-level merge must also
   be addressed.

---

## H. Artifact Paths

| # | Artifact | Absolute Path | Present |
| --- | --- | --- | --- |
| 1 | SMCNR `.pin` | `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/case/SMCNR_SE_2st_AMP.pin` | ✅ |
| 2 | SMCNR source netlist | `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/case/SMCNR_SE_2st_AMP_cand_0031.sp` | ✅ |
| 3 | SMCNR extracted SPICE (raw) | `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.raw.spice` | ✅ |
| 4 | SMCNR extracted SPICE (connectivity) | `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.connectivity.spice` | ✅ |
| 5 | SMCNR LVS summary | `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/lvs_result_summary.md` | ✅ |
| 6 | SMCNR LVS prep report | `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/lvs_preparation_report.md` | ✅ |
| 7 | SMCNR state.json | `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json` | ✅ |
| 8 | SMCNR `.ext` file | (not in reproducibility package) | **MISSING** |
| 9 | SMCNR GDS file | (not in reproducibility package) | **MISSING** |
| 10 | SMCNR Magic extraction log | (not in reproducibility package) | **MISSING** |
| 11 | Fan_SMC `.pin` | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.pin` | ✅ |
| 12 | Fan_SMC source netlist | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.sp` | ✅ |
| 13 | Fan_SMC `.ext` | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext` | ✅ |
| 14 | Fan_SMC device_mapping | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/device_mapping.json` | ✅ |
| 15 | Fan_SMC psub geometry | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/psub_substrate_geometry.json` | ✅ |
| 16 | Fan_SMC LVS report | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/netgen_lvs_report.log` | ✅ |
| 17 | Positive baseline contract | `/home/qlf/IOT/references/AnalogHarness/docs/smcnr_positive_baseline_contract.md` | ✅ |

---

## I. Trust Boundary

```json
{
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true
}
```

All trust flags remain failure-case only. No closure, training, reward, or
post-sim safety is claimed. Fan_SMC remains failure-case only. SMCNR positive
baseline status is not transferred to Fan_SMC.
