# AH-SMC-016C: Setup-Normalized Fan_SMC Rerun

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-016C |
| Date | 2026-06-22 |
| Type | Setup-normalized diagnostic rerun |
| Baseline | Fan_SMC psub-tap LVS artifacts |
| MAGICAL files modified | **None** |
| Trust status | Failure-case only |

## Executive Summary

AH-SMC-016C tested whether SMCNR-style net renames could improve Fan_SMC LVS
results. The answer is **no**: the body/substrate collapse has fundamentally
restructured the extracted connectivity, making unambiguous net renames
**impossible**.

Only 3 of 18 source nets survive extraction intact (`vinn`, `vinp`, `vout`).
All 15 other source nets have no extracted counterpart. The substrate merge
(`equiv "vout" "vdda"`, `equiv "vout" "gnda"`) has merged multiple source
nets into single internal nodes — a rename cannot undo this merge.

**H4 (net rename setup gap) is DOWNGRADED: renames are not a contributing
factor because they are impossible under the current extraction topology.**
The SMCNR-vs-Fan_SMC rename difference is a **symptom** of the geometry
difference (SMCNR extraction preserved net identity; Fan_SMC collapsed it),
not an independent setup gap.

---

## 1. Baseline Netgen LVS (No Renames)

### Command

```bash
SKY130A=/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A
/usr/lib/netgen/bin/netgen -batch source run_lvs_baseline.tcl
```

Netgen version: 1.5.133

### Result

```
Result: Netlists do not match.
```

| Metric | Source | Extracted |
| --- | --- | --- |
| Devices | 24 | 24 |
| Nets | 18 | **19** |
| PFET | 12 | 12 |
| NFET | 12 | 12 |

**Baseline reproduced.** Confirms the existing AH-SMC-009 LVS result.

---

## 2. Net Rename Feasibility Analysis

### 2.1 Shared Nets

Only **3 nets** appear in both source and extracted connectivity:

| Net | Source fanout | Extracted fanout | Rename needed? |
| --- | --- | --- | --- |
| `vinn` | 1 (M8 gate) | 1 (X1 gate) | No (already shared) |
| `vinp` | 1 (M9 gate) | 1 (X17 gate) | No (already shared) |
| `vout` | 4 (M11 D, M23 D) | 5+ (multiple devices) | No (already shared) |

### 2.2 Source-Only Nets (15 — no extracted counterpart)

| Source net | Fanout | Example device terminals | Missing from extraction because |
| --- | --- | --- | --- |
| `gnda` | 12 NMOS B + 8 NMOS S | M23 B/gnda, M22 B/gnda | Collapsed into vout (substrate) |
| `vdda` | 10 PMOS B + 10 PMOS S | M11 B/vdda, M0 B/vdda | Collapsed into vout (substrate) |
| `net013` | 6 PMOS G | M0 G, M1 G, M2 G | Merged into `a_20_2910#` (fanout 6) |
| `vb3` | 5 NMOS G + 1 PMOS D | M14 G, M15 G | Merged into `a_700_3870#` (fanout 6) |
| `vb4` | 4 NMOS G + 1 PMOS D | M12 G, M17 G | Merged into `a_420_4610#` (fanout 6) |
| `net049` | 2 NMOS G + 1 PMOS D | M22 G, M23 G | Merged into internal nodes |
| `net043` | 2 NMOS G + 1 NMOS D | M21 G, M22 D | Merged into `a_1500_2270#` (fanout 3) |
| `net050` | 2 PMOS G + 1 NMOS D | M11 G, M16 D | Collapsed into vout |
| `net063` | 1 PMOS D + 1 NMOS D | M9 D, M20 D | Merged into `a_900_2930#` (fanout 3) |
| `net31` | 2 PMOS B/S | M8 B, M9 B | Merged into vout |
| `dm_1` | 1 PMOS D + 1 NMOS D | M2 D, M13 D | Merged into `a_665_3890#` (fanout 2) |
| `dm_2` | 1 PMOS D + 1 NMOS D | M8 D, M19 D | Merged into `a_1500_3250#` (fanout 3) |
| `voutn` | 2 PMOS G + 1 NMOS D | M5 G, M6 G, M15 D | Merged into `a_1220_2750#` (fanout 3) |
| `net54` | 1 NMOS D + 1 NMOS S | M12 S, M17 D | Merged into `a_940_4290#` (fanout 2) |
| `net56` | 1 NMOS D + 1 NMOS S | M13 S, M18 D | Merged into `a_900_3890#` (fanout 2) |

### 2.3 Extracted-Only Internal Nets (16 — no source counterpart)

Each internal `a_*#` node represents a merged electrical node combining
multiple source nets due to substrate shorts:

| Internal net | Fanout | Likely merged from |
| --- | --- | --- |
| `a_20_2910#` | 6 | net013 (6 PMOS gates) |
| `a_700_3870#` | 6 | vb3 (5 NMOS gates + 1 PMOS drain) |
| `a_420_4610#` | 6 | vb4 (4 NMOS gates + 1 PMOS drain) + extra connections |
| `a_1500_2270#` | 3 | net043 (2 NMOS gates + 1 NMOS drain) |
| `a_220_2930#` | 3 | net049 (2 NMOS gates + 1 PMOS D) |
| `a_900_2930#` | 3 | net063 (1 PMOS D + 1 NMOS D) + extra |
| `a_1220_2750#` | 3 | voutn (2 PMOS gates + 1 NMOS D) |
| `a_1500_3250#` | 3 | dm_2 (1 PMOS D + 1 NMOS D) + extra |
| `a_900_3890#` | 2 | net56-related |
| `a_665_3890#` | 2 | dm_1-related |
| `a_940_4290#` | 2 | net54-related |
| `a_2345_3890#` | 1 | Isolated internal |
| `a_220_3490#` | 1 | Isolated internal |
| `a_1420_2770#` | 1 | Isolated internal |
| `a_1905_2290#` | 1 | Isolated internal |
| `a_25_4050#` | 1 | Isolated internal |

### 2.4 Why Renames Are Impossible

SMCNR's net renames worked because SMCNR extraction preserved the same
electrical topology as the source — internal nodes were clean 1:1 aliases
for source nets (`a_20_494#` → `outn`).

Fan_SMC extraction has **fundamentally restructured** the topology:

1. **Merge-to-one**: `gnda` and `vdda` were merged into `vout` through the
   substrate, so there is no extracted net that uniquely represents `gnda`
   or `vdda`.

2. **Fanout mismatch**: Internal nodes have different fanout counts from
   their likely source counterparts (e.g., `a_420_4610#` fanout=6 vs source
   `vb4` fanout=5), indicating additional electrical connections through
   the substrate.

3. **Port collapse**: The extracted subcircuit has only 3 ports vs 5 source
   ports. Netgen cannot match netlists with different port counts even if
   internal nets are renamed.

**Any rename from `a_*#` to a source net name would be incorrect** because
it would claim an identity that doesn't exist in the extracted topology.

---

## 3. Candidate Renames Variant

### Candidate `lvs_renames.txt`

**Empty file** — no unambiguous renames are possible.

Path: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016c/candidate_lvs_renames.txt`

### Netgen with Candidate Renames

The candidate renames variant produces the same Netgen result as the baseline
(no renames = empty renames). Result: **Netlists do not match.**

---

## 4. Port Count Mismatch: Guaranteed LVS Failure

Even if internal net renames were possible, the **port count mismatch**
guarantees LVS failure:

| | Ports | Count |
| --- | --- | --- |
| Source `.subckt` | `gnda vdda vinn vinp vout` | 5 |
| Extracted `.subckt` | `vinn vinp vout` | **3** |

Netgen compares subcircuit interface ports first. `gnda` and `vdda` are
declared as source ports but absent from extracted ports. Netgen cannot
resolve this mismatch through internal net renames — the port lists must
match for a clean LVS pass.

This port mismatch is a **direct consequence** of Magic extraction writing
`equiv "vout" "vdda"` and `equiv "vout" "gnda"` in the `.ext` file. When
these equivalences exist, `ext2spice` folds the equated ports into the
dominant net (`vout`) and drops them from the subcircuit declaration.

**Source**: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext` lines 32-34.

---

## 5. `.ext` Substrate/Equiv Records (Unchanged)

The psub-tap Fan_SMC `.ext` file still contains:

```text
substrate "vout"
equiv "vout" "vdda"
equiv "vout" "gnda"
```

**These records are the primary hard blocker.** No Netgen setup (renames,
model aliases, property removal) can fix extraction records that declare
vout ≡ vdda ≡ gnda at the layout level.

---

## 6. Body Terminal Collapse (Unchanged)

All 12 NMOS extracted body terminals remain non-`gnda`:

| Destination | Count | NMOS instances |
| --- | --- | --- |
| `vout` | 5 | M23, M22, M20, M18, M17 |
| Internal `a_*#` | 7 | M21, M19, M16, M15, M14, M13, M12 |
| `gnda` | **0** | — |

Zero of 12 NMOS body terminals resolve to the source-specified `gnda`.

---

## 7. Comparison: Baseline vs Candidate Renames

| Metric | Baseline (no renames) | Candidate (empty renames) | Delta |
| --- | --- | --- | --- |
| Devices | 24 vs 24 | 24 vs 24 | Same |
| Nets | 18 vs 19 | 18 vs 19 | Same |
| Netlist match | No | No | Same |
| Result | **Netlists do not match** | **Netlists do not match** | **Same** |

The candidate renames variant is identical to baseline because no unambiguous
renames are possible.

---

## 8. Hypothesis Assessment (Updated)

| H | Claim | AH-SMC-016B Status | AH-SMC-016C Status | Δ |
| --- | --- | --- | --- | --- |
| H1 | `.pin=-1` sole root cause | DISPROVEN | **DISPROVEN** | — |
| H2 | Diffusion/psub geometry dominates | SUPPORTED_BY_FAN_ONLY | **SUPPORTED_BY_FAN_ONLY** | — |
| H3 | Routing/met5 co-contaminates | CANDIDATE | **CANDIDATE** | — |
| **H4** | **Netgen/LVS setup divergence** | **SUPPORTED** | **DOWNGRADED** | **↓** |

### H4 Downgrade Rationale

AH-SMC-016B identified missing net renames as a "supported" setup gap. AH-SMC-016C
demonstrates that net renames are **impossible under the current extraction
topology** — the body collapse has fundamentally restructured connectivity.

The SMCNR-vs-Fan_SMC rename difference is a **symptom** of the geometry
difference (SMCNR extraction preserved net identity; Fan_SMC collapsed it),
not an independent setup gap. Renames cannot help because:

1. No 1:1 mapping exists between source nets and extracted internal nodes
2. Internal nodes are merged (fanout mismatch)
3. Port lists differ (5 source vs 3 extracted)
4. The `.ext` equiv records guarantee port collapse regardless of renames

**H4 is not an independent contributing factor.** The setup divergence is a
consequence of the geometry problem, not a separate root cause.

---

## 9. Conclusion

**Net renames cannot improve Fan_SMC LVS results.** The geometry-level substrate
collapse (H2) has fundamentally restructured the extracted connectivity,
making:

1. Net renames **impossible** (no 1:1 internal↔source mapping)
2. Port matching **impossible** (5 source vs 3 extracted ports)
3. Body terminal recovery **impossible** (0/12 NMOS body = gnda)

**.pin=-1 alone is not sufficient as a single-variable root cause.**
The primary blocker remains the diffusion/psub geometry merge that causes
Magic to equate vout, vdda, and gnda.

**Next diagnostic must address the geometry level** — either by fixing the
layout diffusion connectivity (H2) or by isolating the routing contamination
(H3). Setup normalization alone cannot resolve this class of failure.

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
and `equiv "vout" "vdda"` / `equiv "vout" "gnda"` — no Netgen setup can
honestly pass LVS with these records present.

---

## 11. Artifacts

| # | Artifact | Absolute Path |
| --- | --- | --- |
| 1 | Source connectivity | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016c/fan_smc_pin_3_source.connectivity.spice` |
| 2 | Extracted connectivity | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016c/fan_smc_pin_3_extracted.connectivity.spice` |
| 3 | Baseline LVS report | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016c/netgen_lvs_baseline.log` |
| 4 | Baseline LVS Tcl | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016c/run_lvs_baseline.tcl` |
| 5 | Candidate lvs_renames.txt | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016c/candidate_lvs_renames.txt` |
| 6 | psub-tap `.ext` | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext` |
| 7 | Netgen binary | `/usr/lib/netgen/bin/netgen` (1.5.133) |
| 8 | sky130A_setup.tcl | `/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A/libs.tech/netgen/sky130A_setup.tcl` |
