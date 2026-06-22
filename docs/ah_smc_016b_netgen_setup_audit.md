# AH-SMC-016B: SMCNR vs Fan_SMC Netgen/LVS Setup Provenance Audit

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-016B |
| Date | 2026-06-22 |
| Type | Read-only setup provenance audit |
| Positive baseline | `SMCNR_SE_2st_AMP/cand_0031` (LVS PASS) |
| Diagnostic case | `Fan_SMC_Pin_3` (LVS FAIL) |
| MAGICAL files modified | **None** |
| Trust status | Failure-case only |

## Conclusion

**Fan_SMC LVS failure has at least three contributing factors beyond NMOS
`.pin=-1`, two of which are setup/config divergences from the SMCNR workflow:**

1. **Magic extraction collapse** (geometry-level): Fan_SMC Magic extraction drops
   `gnda` and `vdda` from the subcircuit port list because they are electrically
   shorted to `vout` through the p-substrate. SMCNR does not have this problem.

2. **Missing net renames** (setup-level): SMCNR used 5 explicit internal-→source
   net renames to map `a_*#` nodes to source net names. Fan_SMC's LVS preparation
   had "Net rename enabled: no". Without renames, ALL internal nodes are compared
   as-is against source nets, guaranteeing mismatches.

3. **Port count mismatch** (consequence of #1): Fan_SMC source has 5 ports
   (`gnda vdda vinn vinp vout`) but extracted has only 3 ports
   (`vinn vinp vout`). Netgen cannot match these netlists regardless of device
   connectivity.

**Before any MAGICAL `.pin` contract patch, the next diagnostic should be a
setup-normalized Fan_SMC rerun that applies SMCNR-style net renames and
documents the port count mismatch explicitly.**

---

## 1. Magic Extraction Tcl Comparison

### SMCNR

```tcl
gds read .../SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds
load SMCNR_SE_2st_AMP_flat
select top cell
extract all
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice
quit -noprompt
```

Source: `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/magic_extract.tcl`

### Fan_SMC

```tcl
gds read fan_smc_pin_3.psub_tap.gds
load fan_smc_pin_3_flat
select top cell
extract all
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice
quit -noprompt
```

Source: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/magic_extract.tcl`

### Delta: **Identical.**

Both use the same sequence: `extract all` → `ext2spice lvs` →
`ext2spice cthresh 0` → `ext2spice rthresh 0` → `ext2spice`.

The `lvs` flag instructs `ext2spice` to ignore parasitic capacitors and produce
a connectivity-only SPICE netlist. `cthresh 0` and `rthresh 0` include all
parasitic capacitors and resistors.

**The Fan_SMC extraction warnings (`Ports "vout" and "vdda/gnda" are
electrically shorted`) are a GEOMETRY phenomenon, not a Tcl configuration
difference.**

---

## 2. Extracted SPICE Port Comparison

This is the most critical setup difference:

| Circuit | Extracted `.subckt` ports | Count | gnda/vdda present? |
| --- | --- | --- | --- |
| **SMCNR** | `vdda gnda vin vip ibias vout` | 6 | **YES** |
| **Fan_SMC** | `vinn vinp vout` | **3** | **NO** |

### SMCNR raw extracted SPICE

```spice
.subckt SMCNR_SE_2st_AMP_flat vdda gnda vin vip ibias vout
X0 vdda ibias a_785_2846# vdda sky130_fd_pr__pfet_01v8 ...
X2 vout a_20_494# gnda gnda sky130_fd_pr__nfet_01v8 ...
X3 gnda a_2100_n30# a_20_494# gnda sky130_fd_pr__nfet_01v8 ...
```

All NMOS body = `gnda` (correct). All PMOS body = `vdda` (correct).
All 6 ports present.

### Fan_SMC raw extracted SPICE

```spice
.subckt fan_smc_pin_3_flat vinn vinp vout
X23 vout a_220_2930# vout vout sky130_fd_pr__nfet_01v8 ...
```

All NMOS body = `vout` (collapsed). gnda/vdda **absent** from ports.
Only 3 ports.

### Impact on LVS

Fan_SMC source netlist:
```spice
.subckt fan_smc_pin_3 gnda vdda vinn vinp vout   ← 5 ports
```

Fan_SMC extracted netlist:
```spice
.subckt fan_smc_pin_3_flat vinn vinp vout          ← 3 ports
```

**Netgen cannot match these netlists.** The source declares 5 ports
(`gnda vdda vinn vinp vout`) while the extracted declares only 3
(`vinn vinp vout`). The port list mismatch alone guarantees LVS failure,
regardless of internal connectivity.

### Root cause

This is NOT a Netgen configuration issue. Magic's `ext2spice` automatically
determines subcircuit ports from the extracted connectivity. When Magic
determines that `gnda` and `vdda` are electrically shorted to `vout` (via
`equiv` records in `.ext`), it folds them into `vout` and drops them from the
port list. This is a **geometry-level** problem — Magic's extractor sees
gnda=vdda=vout in the p-substrate.

---

## 3. Net Renames Comparison

### SMCNR

SMCNR used **5 explicit net renames** stored in `lvs_renames.txt`:

```
a_785_2846#=ibias
a_4024_586#=net53
a_20_494#=outn
a_2100_n30#=outp
a_4345_n10#=outp
```

These map Magic-generated internal node names (`a_*#`) to source netlist net
names. The `prepare_lvs_netlists.py` script applies these renames when
generating the connectivity netlist.

Source: `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/lvs_renames.txt`

### Fan_SMC

LVS preparation report explicitly states:

> Net rename enabled: no

No `lvs_renames.txt` file exists in the Fan_SMC LVS prepared directory. All
internal nodes (`a_220_2930#`, `a_1500_3250#`, etc.) are passed through
unchanged to the connectivity netlist.

Source: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/lvs_preparation_report.md`

### Impact on LVS

Without net renames, ALL internal `a_*#` nodes in the extracted netlist are
compared against source net names. Since source net names (`net049`, `vb3`,
`dm_1`, etc.) don't match internal nodes (`a_220_2930#`, `a_700_3870#`, etc.),
this guarantees net mismatches.

Even if the body collapse were fixed (#1 above), the LVS would still fail
because internal node names don't match source net names. SMCNR avoided this
by explicitly mapping internal nodes to source names.

---

## 4. Source Connectivity Normalization

### Model Aliases

| Circuit | Source model | Extracted model | Alias applied |
| --- | --- | --- | --- |
| SMCNR | `nch_mac` | `sky130_fd_pr__nfet_01v8` | **Yes** (3 instances) |
| SMCNR | `pch_mac` | `sky130_fd_pr__pfet_01v8` | **Yes** (5 instances) |
| Fan_SMC | `sky130_fd_pr__nfet_01v8` | `sky130_fd_pr__nfet_01v8` | Not needed (already matching) |
| Fan_SMC | `sky130_fd_pr__pfet_01v8` | `sky130_fd_pr__pfet_01v8` | Not needed (already matching) |

SMCNR source uses foundry model names (`nch_mac`, `pch_mac`) which are aliased
to Sky130 models. Fan_SMC source already uses Sky130 model names directly.
Both are correctly normalized.

### Property Removal

Both circuits remove the same MOS properties: `ad`, `as`, `pd`, `ps`.
This is standard LVS property normalization.

### Passive Device Handling

| Circuit | Source passives | Dropped | Reason |
| --- | --- | --- | --- |
| SMCNR | 2 (`xc0` cfmom_2t, `xr0` rppolywo_m) | **0** (excluded from source connectivity netlist) | `mos_only_projection`: passives not in LVS scope |
| Fan_SMC | 1 (`C0` cfmom_2t) | **1** | `cfmom_2t` unsupported; dropped from connectivity |

SMCNR explicitly excluded passives from the LVS source netlist (only 8 MOS
devices in connectivity source). Fan_SMC had C0 in the source netlist, which
was dropped as unsupported. This is consistent — neither circuit attempts
passive-aware LVS in the connectivity mode.

---

## 5. Netgen Setup Comparison

### Fan_SMC

```tcl
set setup [file join $::env(SKY130A) libs.tech netgen sky130A_setup.tcl]
lvs {source.connectivity.spice fan_smc_pin_3} \
    {extracted.connectivity.spice fan_smc_pin_3_flat} \
    $setup {netgen_lvs_report.log}
```

The `$SKY130A` environment variable resolves on the machine where Netgen ran.
From the Netgen stdout log:
```
Reading setup file /mnt/d/IOT/PreviousProjects/XinTuZhiLian/pdks/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A/libs.tech/netgen/sky130A_setup.tcl
```

PDK version: **bdc9412b**

### SMCNR

SMCNR's Netgen command and setup file path are not preserved in the local
reproducibility package. The LVS result summary only records the outcome
(`lvs_match=yes`, `netgen_exit_status=0`). The run was on a Windows machine
(`E:\codex-magical-sky130-harness\...`).

**Missing artifact**: SMCNR Netgen Tcl wrapper and stdout log.

### Local PDK Reference

```text
/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A/libs.tech/netgen/sky130A_setup.tcl
SHA256: 7a33f3f54fab57a9d9b0887ac7b7b64ce6c454110e8b7f01f3cfb90a1282dc94
```

PDK version: **7b70722e**

### Model Equivalence

Both Netgen runs apply the same sky130A model equivalence (from the PDK setup):
```
Model sky130_fd_pr__nfet_01v8 pin 1 == 3    (D/S permutable)
Model sky130_fd_pr__pfet_01v8 pin 1 == 3    (D/S permutable)
```

This is standard for the Sky130 PDK and does not differ between the two setups.

### Delta Summary

| Criterion | SMCNR | Fan_SMC | Same? |
| --- | --- | --- | --- |
| Netgen binary/version | (unknown) | 1.5.133 | Unknown |
| Setup Tcl source | sky130A PDK (unknown version) | sky130A PDK (bdc9412b) | Different PDK versions |
| Local PDK version | N/A | 7b70722e | Different |
| Model D/S equivalence | Standard sky130A | Standard sky130A | **Same** |
| Netgen command format | (unknown) | `lvs {src} {ext} $setup {out}` | Likely same |

**No critical Netgen configuration divergence was found** that would explain
the LVS pass/fail difference. The primary divergences are at the Magic
extraction level (port collapse) and the LVS preparation level (missing net
renames).

---

## 6. LVS Preparation Pipeline Comparison

### Preparation Script

Both circuits use the same `prepare_lvs_netlists.py`:
`/home/qlf/IOT/references/MAGICAL-/tools/sky130_adapter/prepare_lvs_netlists.py`

The script:
1. Drops specified MOS properties (`ad`, `as`, `pd`, `ps`)
2. Applies model aliases (for SMCNR: `nch_mac`→Sky130)
3. Drops unsupported passive devices
4. Applies explicit net renames if provided via `--rename` flags
5. Strips parasitic capacitors for connectivity netlist

### SMCNR Pipeline

```
source netlist (mac models) + extracted SPICE
  → model aliases (nch_mac→sky130, pch_mac→sky130)
  → external renames (a_*# → source net names)
  → property removal (ad/as/pd/ps)
  → passive exclusion (mos_only_projection)
  → connectivity source + connectivity extracted
  → Netgen LVS → PASS
```

### Fan_SMC Pipeline

```
source netlist (sky130 models) + extracted SPICE
  → (no model aliases needed)
  → (no net renames configured)
  → property removal (ad/as/pd/ps)
  → drop C0 (unsupported cfmom_2t)
  → connectivity source + connectivity extracted
  → Netgen LVS → FAIL
```

### Key Pipeline Divergences

| Step | SMCNR | Fan_SMC |
| --- | --- | --- |
| Model aliases | `nch_mac→sky130`, `pch_mac→sky130` | None needed |
| Net renames | **5 explicit renames** | **None** |
| Property removal | Standard (ad/as/pd/ps) | Standard (ad/as/pd/ps) |
| Passive handling | Excluded from source | C0 dropped as unsupported |
| Extracted ports | 6 (all present) | **3 (gnda/vdda missing)** |

---

## 7. Risk Assessment

### H4: Netgen/LVS/Harness Setup Divergence

**Assessment: SUPPORTED as contributing factor.**

The setup divergence is real:
1. SMCNR applied net renames; Fan_SMC did not — **setup gap**.
2. Fan_SMC's Magic extraction dropped gnda/vdda from ports — **geometry
   consequence**, not setup issue.
3. The missing net renames alone would cause LVS failure even if the body
   collapse were fixed.
4. The port count mismatch (5 vs 3) guarantees LVS failure regardless of
   internal connectivity.

**However, the setup divergence is SECONDARY to the geometry problem.** Fixing
net renames and port normalization would change the LVS symptoms but would not
fix the underlying `equiv "vout" "gnda"` / `equiv "vout" "vdda"` records in
Magic's `.ext` file. Those are geometry-level, not setup-level.

### Fan_SMC Failure Catalog

| # | Factor | Level | Fixable without MAGICAL patch? |
| --- | --- | --- | --- |
| 1 | Magic extraction: `substrate "vout"`, `equiv vout↔vdda/gnda` | **Geometry** | No — requires layout change |
| 2 | Extracted ports lost gnda/vdda | **Consequence of #1** | No — symptom of #1 |
| 3 | No net renames configured | **Setup** | **Yes** — add lvs_renames.txt |
| 4 | C0 cfmom_2t dropped | **Setup** | **Yes** — consistent with mos_only_projection |
| 5 | MAGICAL nondeterministic routing | **Tooling** | Partially — seeded random or multiple-run averaging |
| 6 | NMOS .pin = -1 | **Primitive contract** | No — requires MAGICAL code change |

**Items 1 and 2 are the primary blockers.** Items 3-4 are setup gaps that make
the LVS failure appear worse than it is but are not root causes. Item 5 makes
any single-run diagnosis unreliable.

---

## 8. Recommendation

### Primary: Setup-Normalized Fan_SMC Rerun

Before any MAGICAL `.pin` contract patch, execute a **setup-normalized Fan_SMC
rerun** that:

1. Applies SMCNR-style explicit net renames (map all `a_*#` nodes in the
   extracted netlist to their corresponding source net names)
2. Runs in `mos_only_projection` mode (consistent with SMCNR)
3. Documents the port count mismatch explicitly
4. Records the Netgen report with and without renames

This would isolate whether the LVS failure is caused by:
- (a) Missing net renames → LVS should partially improve
- (b) Body collapse to vout → LVS still fails on net assignments
- (c) Both → LVS status provides diagnostic insight

### Secondary: Only after setup normalization confirms geometry root cause

If the setup-normalized rerun still shows body=vout for NMOS devices (despite
correct net renames), the geometry root cause (H2 from AH-SMC-016A) is
confirmed. At that point, the MAGICAL patch from AH-SMC-015R2 can be considered
with the understanding that it addresses the `.pin` contract but may not resolve
the diffusion/psub merge.

---

## 9. Hypothesis Assessment (Updated)

| H | Claim | Status | Confidence | Changed? |
| --- | --- | --- | --- | --- |
| H1 | `.pin=-1` sole root cause | **DISPROVEN** | High | No — confirmed by AH-SMC-016A |
| H2 | Diffusion/psub geometry dominates | **SUPPORTED_BY_FAN_ONLY** | Medium | No — SMCNR .ext/GDS still missing |
| H3 | Routing/met5 co-contaminates | **CANDIDATE** | Medium | No — AH-SMC-012 met5 audit |
| **H4** | **Netgen/LVS setup divergence contributes** | **SUPPORTED** | **High** | **NEW** — missing net renames + port mismatch |

---

## 10. Artifact Paths

| # | Artifact | Absolute Path |
| --- | --- | --- |
| 1 | SMCNR magic_extract.tcl | `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/magic_extract.tcl` |
| 2 | Fan_SMC magic_extract.tcl | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/magic_extract.tcl` |
| 3 | SMCNR extracted SPICE | `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.connectivity.spice` |
| 4 | Fan_SMC extracted SPICE | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/fan_smc_pin_3_extracted.connectivity.spice` |
| 5 | Fan_SMC source connectivity | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/fan_smc_pin_3_source.connectivity.spice` |
| 6 | Fan_SMC lvs_preparation_report | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/lvs_preparation_report.md` |
| 7 | SMCNR lvs_preparation_report | `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/lvs_preparation_report.md` |
| 8 | Fan_SMC Netgen run_lvs.tcl | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/run_lvs.tcl` |
| 9 | Fan_SMC Netgen stdout log | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/netgen_stdout.log` |
| 10 | SMCNR lvs_renames.txt | `/home/qlf/IOT/references/AnalogHarness/reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/layout/lvs_mos_projection/lvs_renames.txt` |
| 11 | prepare_lvs_netlists.py | `/home/qlf/IOT/references/MAGICAL-/tools/sky130_adapter/prepare_lvs_netlists.py` |
| 12 | Local sky130A_setup.tcl | `/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A/libs.tech/netgen/sky130A_setup.tcl` |
| 13 | Fan_SMC Netgen setup path (from log) | `/mnt/d/IOT/PreviousProjects/XinTuZhiLian/pdks/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A/libs.tech/netgen/sky130A_setup.tcl` |
| 14 | SMCNR Netgen setup path | **MISSING** (not in reproducibility package) |
| 15 | SMCNR Netgen stdout log | **MISSING** (not in reproducibility package) |

---

## 11. Trust Boundary

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
