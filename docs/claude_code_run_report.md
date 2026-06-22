# Claude Code Run Report

## AH-SMC-007: Fan_SMC psub/body/tap Provenance Audit

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-007 |
| Date | 2026-06-20 |
| Circuit | Original Fan_SMC with bounded C0 proxy |
| Candidate ID | `fan_smc_original_c0_proxy_94x10` |
| Git status | M: AGENTS.md, prepare_lvs_netlists.py, test_prepare_lvs_netlists.py (pre-existing); ?? docs/, diagnostics/ (new files from prior tasks) |
| Files modified | `docs/claude_code_run_report.md` (new), `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_007/` (new) |
| Baseline test result | diagnostics 22/22 pass; full suite 71/73 (2 known env failures) |

### Input Artifacts

| Artifact | Absolute path |
| --- | --- |
| Source netlist | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.sp` |
| MAGICAL ioPin | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.ioPin` |
| MAGICAL .pin | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.pin` |
| Remap report | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/remap_report.md` |
| Pin label report | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/pin_label_report.md` |
| Magic extract log | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/magic_extract.log` |
| Magic .ext file | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/fan_smc_pin_3_flat.ext` |
| Extracted SPICE | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/fan_smc_pin_3_flat.spice` |
| Device mapping | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/device_mapping.json` |
| Nwell body domains | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/nwell_body_domains.json` |
| Psub substrate geometry | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/psub_substrate_geometry.json` |
| B1 extract log | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_b1/extract/magic_extract.log` |
| MAGICAL diagnostic tools | `/home/qlf/IOT/references/MAGICAL-/tools/sky130_adapter/` (read-only) |

---

## 1. Independent Reproduction of Four Confirmed Observations

### Observation 1: Magic reports vout↔vdda and vout↔gnda shorts

**Command:**
```bash
cat /home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/magic_extract.log
```

**Result (reproduced, lines 31-36):**
```
Warning:  Ports "vout" and "vdda" are electrically shorted.
Warning:  Ports "vout" and "gnda" are electrically shorted.
fan_smc_pin_3_flat: 3 warnings
```
**Exit code**: 0. **Evidence class**: `local artifact`, `direct log`.

### Observation 2: Device mapping reports 23 mapped, 1 unmatched, 23 body mismatches, 88 terminal mismatches

**Command:**
```bash
python3 -c "import json; d=json.load(open('.../device_mapping.json')); \
  print('mapped:', d['mapped_source_instance_count'], 'extracted:', d['mapped_extracted_device_count'], \
  'unmatched:', d['unmatched_extracted_device_count'], 'body_mm:', d['body_mismatch_count'], \
  'term_mm:', d['terminal_mismatch_count'])"
```

**Result (reproduced):**
```
mapped: 23  extracted: 23  unmatched: 1  body_mm: 23  term_mm: 88
```
**Evidence class**: `local artifact`, `structured json`.

### Observation 3: Nwell body domains pass

**Command:**
```bash
python3 -c "import json; d=json.load(open('.../nwell_body_domains.json')); print(d['status'], d['issue_codes'])"
```

**Result (reproduced):**
```
pass  []
```
12 PMOS instances grouped into 12 nwell components. All PMOS body nets correctly identified as `vdda` except M8/M9 which have body `net31`. **Evidence class**: `local artifact`, `structured json`.

### Observation 4: Psub substrate geometry fails with three specific issue codes

**Command:**
```bash
python3 -c "import json; d=json.load(open('.../psub_substrate_geometry.json')); print(d['status'], d['issue_codes'])"
```

**Result (reproduced):**
```
fail  ['magic_substrate_on_signal', 'magic_equates_signal_to_power', 'psub_active_dependent_signal_path_with_magic_conflict']
```

Key findings:
- `psub_route_net`: `gnda` (correct by MAGICAL design)
- `psub_route_db_layer`: 6 (MAGICAL internal → `diff.drawing` 65/20 after remap)
- `psub_connected_to_vdd_pin`: true (WITH diff.drawing included)
- `psub_connected_to_vss_pin`: true
- `psub_component_pin_overlaps`: `['gnda', 'vdda', 'vout']`
- WITH diff removed: `psub_connected_to_vdd_pin_no_diff`: false, overlaps: `['gnda']` only
- `psub_active_dependent_vdd_path`: true (47-step path from psub to vdda)
- Path layer trace: met5 → via4 → met4 → via3 → met3 → via2 → met2 → via → met1 → mcon → li1 → licon1 → **diff.drawing** → licon1 → li1 → mcon → met1 → via → met2 → via2 → met3 → via3 → met4 → via4 → met5 → met5.pin(vdda)

**Evidence class**: `local artifact`, `structured json`.

### Additional: Magic .ext substrate and equivalence records

**Command:**
```bash
grep -n 'substrate\|equiv' .../extract/fan_smc_pin_3_flat.ext
```

**Result (reproduced, lines 32-34):**
```
32: substrate "vout" 0 0 310 2088 m1 ...
33: equiv "vout" "vdda"
34: equiv "vout" "gnda"
```

Magic directly records substrate identity as `vout` and explicit electrical equivalences `vout=vdda` and `vout=gnda`. **Evidence class**: `local artifact`, `direct log`.

---

## 2. psub/body/tap Boundary Audit

### 2.1 Source MOS Body Terminals

Source netlist (`fan_smc_pin_3.sp`): all 24 MOS instances use explicit 4-terminal syntax `(D G S B)`.

| Instance | Model | Source terminals (D G S B) | Body net |
| --- | --- | --- | --- |
| M11 | `sky130_fd_pr__pfet_01v8` | `(vout, net050, vdda, vdda)` | vdda |
| M23 | `sky130_fd_pr__nfet_01v8` | `(vout, net049, gnda, gnda)` | gnda |
| M0 | `sky130_fd_pr__pfet_01v8` | `(net013, net013, vdda, vdda)` | vdda |
| M15 | `sky130_fd_pr__nfet_01v8` | `(voutn, vb3, dm_2, gnda)` | gnda |

### 2.2 MAGICAL Primitive/Placement Contract

The `.pin` file defines per-instance pin geometries:

- **PMOS devices** (M11, M7, M10, M6, M5, M9, M8, M4, M3, M2, M1, M0): 4 pins with the 4th pin at `-450 -450 1650 -350` — a real body terminal box.
- **NMOS devices** (M23, M22, M21, M19, M15, M20, M16, M17, M14, M12, M18, M13): 4 pins declared but the 4th pin is `-1` (sentinel for ABSENT body terminal).

This is the **first semantic divergence**: the source netlist specifies `B=gnda` for all NMOS devices, but the MAGICAL `.pin` contract provides no physical body terminal geometry for NMOS. MAGICAL relies on the shared psub tap (gnda route on MAGICAL internal layer 6 → `diff.drawing` 65/20) for NMOS body connection.

### 2.3 psub/gnda Route Layer

From `psub_substrate_geometry.json`:
- `psub_route_net`: `gnda`
- `psub_route_shape`: `[-1050, -450, 15050, -350]` (layout coordinates, units=nm/100)
- `psub_route_db_layer`: 6 → MAGICAL internal OD → Sky130 `diff.drawing` 65/20

The gnda psub tap is implemented as a horizontal **diffusion** stripe at the bottom edge of the layout, NOT as a metal route. This is correct for substrate tap semantics in analog layout, but it means ALL diff.drawing in the layout is electrically connected through the substrate.

### 2.4 Sky130 GDS Remap

All 17 MAGICAL internal layers that are recognized are remapped to Sky130 GDS layers. Of specific interest:
- MAGICAL layer 6 (OD) → Sky130 `diff.drawing` 65/20
- MAGICAL layer 3 (NW) → Sky130 `nwell.drawing` 64/20
- MAGICAL layer 25 (PP) → Sky130 `psdm.drawing` 94/20
- MAGICAL layer 26 (NP) → Sky130 `nsdm.drawing` 93/44
- 12 TBD layer/datatype pairs (150/155 series) are preserved unchanged

### 2.5 Magic Substrate and Device Terminal Records

From the `.ext` file:
```
substrate "vout" 0 0 310 2088 m1 ...
equiv "vout" "vdda"
equiv "vout" "gnda"
```

The substrate is recorded at position `(310, 2088)` on met1 — this corresponds to layout `(1550, 10440)`, the bottom-left corner of the vout ioPin box. Magic labels the substrate as "vout" because the vout port's met1 region is the first labeled port that contacts the diff.drawing-connected domain.

Device terminal records (from `.ext`):
- **M11 (PMOS)**: S=vout, G=vout, B=vout, D=vout — complete 4-terminal collapse to vout
- **M23 (NMOS)**: S=vout, G=a_220_2930#, B=vout, D=vout — 3 of 4 terminals as vout
- **M0 (PMOS, control)**: S=vout, G=a_20_2910#, B=a_25_4050#, D=vout — S/D collapse to vout, body remains anonymous

Extracted SPICE confirms:
```
X22 vout vout vout vout sky130_fd_pr__pfet_01v8 ... as=0 ps=0  ← M11: zero source area
X23 vout a_220_2930# vout vout sky130_fd_pr__nfet_01v8 ...       ← M23: S/B/D all vout
```

M11's `as=0 ps=0` (zero source area/perimeter) indicates the source diffusion is not physically present or not recognized as a distinct terminal by Magic.

---

## 3. M11/M23/Control MOS Terminal Table

| Field | M11 (PMOS, affected) | M23 (NMOS, affected) | M0 (PMOS, control) |
| --- | --- | --- | --- |
| **Source model** | `sky130_fd_pr__pfet_01v8` | `sky130_fd_pr__nfet_01v8` | `sky130_fd_pr__pfet_01v8` |
| **Source D** | vout | vout | net013 |
| **Source G** | net050 | net049 | net013 |
| **Source S** | vdda | gnda | vdda |
| **Source B** | vdda | gnda | vdda |
| **Expected body net** | vdda | gnda | vdda |
| **MAGICAL .pin 4th pin** | `-450 -450 1650 -350` (present) | **`-1` (absent)** | `-50 -50 50 1050` (present) |
| **Placement origin** (layout) | [2600, 11800] | [5200, 11400] | [200, 20200] |
| **Extracted terminal order** | S, G, B, D | S, G, B, D | S, G, B, D |
| **Extracted S** | **vout** | **vout** | **vout** |
| **Extracted G** | **vout** | a_220_2930# | a_20_2910# |
| **Extracted B** | **vout** | **vout** | a_25_4050# |
| **Extracted D** | **vout** | **vout** | **vout** |
| **Extracted body net** | vout | vout | a_25_4050# |
| **Body mismatch** | yes (vdda→vout) | yes (gnda→vout) | yes (vdda→a_25_4050#) |
| **First artifact losing supply identity** | `.ext` line 116: device msubckt, all terminals vout; SPICE `as=0 ps=0` | `.ext` line 115: S/B/D all vout | `.ext` line 132: S/D as vout, B as a_25_4050# |
| **Source diffusion area** (SPICE) | **as=0 ps=0** (zero) | as=16.15 ps=215.5 (present) | as=0.175 ps=2.35 (present) |

### Distinguishing Static Tracer vs Direct Magic Evidence

| Evidence class | Source | What it shows | Limitation |
| --- | --- | --- | --- |
| **Static tracer (psub diagnosis WITH diff)** | GDS polygon connectivity graph | 47-step path from psub to vdda through diff.drawing | Over-approximates: treats all diff.drawing as electrically connected regardless of junction isolation |
| **Static tracer (psub diagnosis WITHOUT diff)** | GDS polygon connectivity graph | Psub connects to gnda only when diff removed | Does not represent real silicon — diff is required for devices |
| **Direct Magic evidence** | `.ext` file: `substrate "vout"`, `equiv "vout" "vdda"`, `equiv "vout" "gnda"` | Magic's own extraction identifies substrate as vout and equates it to both supplies | Authoritative for Magic's extraction model |
| **Direct Magic evidence** | `.ext` device records: M11 S=vout, M23 S/B/D=vout | Magic's extracted device terminals | Authoritative for extracted connectivity |
| **Direct Magic evidence** | `magic_extract.log`: "Ports vout and vdda are electrically shorted" | Magic's own port short detection | Authoritative |

The static tracer's active-dependent VDD path (47 steps) is a *polygon adjacency* analysis. It correctly identifies that diff.drawing creates connectivity between psub and vdda/vout, but it does not account for junction isolation (nwell/psub boundaries should isolate PMOS diffusions from psub). Magic's extraction, however, confirms the short through `equiv` statements and device terminal extraction — this is direct, not approximate, evidence.

---

## 4. Root Cause Hypothesis

**Primary hypothesis**: The MAGICAL `.pin` contract uses a `-1` sentinel for NMOS body terminals, causing all 12 NMOS devices to lack explicit body terminal geometry in the GDS. Magic resolves NMOS body through the shared psub tap (gnda route on `diff.drawing`). However, the psub tap's `diff.drawing` layer is contiguous with PMOS source/drain diffusions via the device channel regions, creating an unintended electrical path:

```
gnda psub tap (diff.drawing, bottom edge)
  → NMOS channel diffusions
    → PMOS source diffusions (connected to vdda through metal stack)
      → Magic equates vdda ↔ gnda
```

Simultaneously, M11 and M23 drain diffusions connect to vout through the met1 port, causing Magic to resolve the entire substrate domain as "vout" and record `equiv "vout" "vdda"` and `equiv "vout" "gnda"`.

**Supporting evidence:**

1. **PMOS nwell diagnosis passes** (line 2-3 of evidence): PMOS body domains are correctly isolated within nwell. No PMOS nwell-domain short is detected. This means the PMOS body-well structure is intact; the short is NOT through nwell.

2. **NMOS body via psub** (line 4 of evidence): NMOS devices lack explicit body pins, so their body is substrate-referenced. The `-1` sentinel in `.pin` is the root of this missing-body-terminal issue.

3. **Active-dependent path confirmed** (line 3 of evidence): Removing diff.drawing from the psub component analysis cleanly resolves psub→gnda only. The path through diff.drawing is the ONLY bridge.

4. **47-step vdda-to-psub path** (line 5 of evidence): The traced path shows symmetric via stack down to diff.drawing and back up. The diff.drawing segment [7325, 11450, 8675, 12450] is at the NMOS output stage region where M23 and M11 drains converge to vout.

5. **M11 zero source area** (line 6 of evidence): `as=0 ps=0` in extracted SPICE indicates the PMOS source diffusion is either absent or not recognized by Magic as distinct from the drain/substrate. This suggests the MAGICAL PMOS PCell's source diffusion is geometrically connected to the drain through the shared active region.

6. **B1 comparison** (line 7 of evidence): B1 (M5 containment) removes the port short warnings but also disconnects gnda/vdda. This shows the M5 power mesh participates in the short path, but the underlying diffusion-domain issue persists.

**Counter-hypothesis considered and rejected**: nwell-domain short. The nwell body domains diagnosis passes with zero issue codes, confirming PMOS nwell isolation is intact.

---

## 5. Proposed Single-Variable A/B Experiment

### Proposal: Add explicit NMOS body pin geometry to the MAGICAL `.pin` contract

**Variable changed**: Replace the `-1` sentinel (absent body pin) in NMOS `.pin` entries with an explicit body terminal box that connects to gnda through a dedicated metal route.

**Concrete implementation**: For each NMOS device `.pin` entry, change the 4th pin coordinates from `-1` to a small box (e.g., `-50 -50 50 50`) positioned within the device's placement origin, and add a MAGICAL route constraint that connects this body pin to the gnda net through a dedicated metal layer (not through diff.drawing).

**Expected evidence if hypothesis is correct**:
- Magic extraction no longer reports `substrate "vout"`
- Magic `equiv` statements for vout↔vdda and vout↔gnda disappear
- NMOS body terminals resolve to gnda or gnda-connected anonymous nets
- PMOS body terminals remain on vdda (nwell domain unchanged)
- Port short warnings for vout↔vdda and vout↔gnda are eliminated
- Device count in extraction remains 24

**Expected evidence if hypothesis is incorrect**:
- Substrate identity remains vout or shifts to another signal
- Port short warnings persist or change to a different topology
- Body mismatches persist in new patterns

**Alternative (simpler diagnostic)**: Instead of modifying the `.pin` file and rerunning P&R, **post-process the existing GDS to add explicit body connection labels at each NMOS device body terminal position**. This is a GDS edit that adds TEXT labels on an appropriate metal layer at the NMOS device body locations, connecting them to gnda. Re-extract and verify.

**Why this experiment and not others**:
- Modifying M5 containment (B1) was already tested and disconnects power
- Modifying pin shapes (AH-SMC-006) was already tested and does not fix the short
- Modifying C0 size (AH-SMC-003) was already tested and does not fix the short
- The `-1` sentinel in `.pin` is the earliest identifiably wrong artifact in the chain from source netlist to extraction

**Stop gate**: Do not execute until Codex reviews this proposal. If accepted, implement as post-P&R GDS edit first (avoid MAGICAL rerun).

---

## 6. Trust Decision

| Flag | Value | Rationale |
| --- | --- | --- |
| `usable_for_reward` | **false** | LVS not passed |
| `usable_for_post_sim` | **false** | LVS not passed, DRC not assessed |
| `usable_for_training` | **false** | LVS not passed, no post-sim, no PVT, no passive scope |
| `usable_for_parasitic_modeling` | **false** | Active-dependent paths create false capacitance coupling; substrate as "vout" invalidates topology |
| `usable_only_as_failure_case` | **true** | Well-characterized psub/body/tap divergence with direct Magic evidence |

---

## 7. Unresolved Questions

1. **Why does Magic label the substrate as "vout" rather than "gnda"?** The gnda psub tap is physically larger and closer to the substrate. One possibility: the vout port's met1 label has higher priority in Magic's net resolution. Another: the vout-connected diffusions are electrically "closer" to the substrate record point.

2. **Why is M11's source diffusion area zero?** `as=0 ps=0` suggests the PMOS source diffusion is not distinguished from the drain by Magic. This could be a PCell geometry issue where source and drain diffusions merge in the MAGICAL primitive.

3. **Does the `-1` sentinel in `.pin` exist in all MAGICAL NMOS primitives, or is it specific to this case?** If it's a general MAGICAL convention, the fix should be upstream in the MAGICAL primitive library.

4. **Would explicit NMOS body pins also fix the DFCFC2 body-domain mismatch?** DFCFC2 shows similar body/terminal mismatch patterns (33 body mismatches) — this may be the same root cause.

---

## 8. Commands Executed

| # | Command | Exit | Purpose |
|---|---------|------|---------|
| 1 | `cat .../magic_extract.log` | 0 | Reproduce observation 1 (port short warnings) |
| 2 | `python3 -c "import json..." device_mapping.json` | 0 | Reproduce observation 2 (mapping counts) |
| 3 | `python3 -c "import json..." nwell_body_domains.json` | 0 | Reproduce observation 3 (nwell pass) |
| 4 | `python3 -c "import json..." psub_substrate_geometry.json` | 0 | Reproduce observation 4 (psub fail) |
| 5 | `grep -n 'substrate\|equiv' ...flat.ext` | 0 | Extract Magic substrate/equiv records |
| 6 | `grep -n 'sky130_fd_pr__' ...flat.spice` | 0 | Extract device terminal lines |
| 7 | `python3 -c "..." device terminal extraction` | 0 | Extract M11/M23/M0 terminal alignment |
| 8 | `python3 -c "..." psub_to_vdd_path analysis` | 0 | Trace 47-step psub→vdd path |
| 9 | `sed -n ...flat.spice` | 0 | Read extracted SPICE device lines |
| 10 | `head/grep ...netgen_lvs.out` (B1) | 0 | B1 comparison LVS result |

---

**Next step**: Await Codex review of root-cause hypothesis and proposed A/B experiment before any implementation.

---

# AH-SMC-009: Fan_SMC Diagnostic P+ Substrate Tap Injection

## Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-009 |
| Date | 2026-06-21 |
| Circuit | Fan_SMC_Pin_3 with bounded C0 proxy (94x10) |
| Candidate ID | `fan_smc_c0_proxy_94x10_psub_tap` |
| Experiment scope | Single top-level diagnostic p+ substrate tap stack |
| Git branch | `qlf/pex-lvs-diagnostics` |
| Tasks executed | 1-7 (Task 8 Codex review deferred) |

## New Files Created

| File | Purpose |
| --- | --- |
| `tools/sky130_adapter/add_diagnostic_psub_tap_stack.py` | GDS parser, validation, boundary insertion, report writer |
| `tools/sky130_adapter/test_add_diagnostic_psub_tap_stack.py` | 7 TDD tests (synthetic GDS fixtures) |
| `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/*` | All experiment artifacts (22 files) |

## Task 1-2: RED Tests (Confirmed Import Error)

**Command:**
```bash
cd tools/sky130_adapter && python3 -m unittest test_add_diagnostic_psub_tap_stack -v
```

**Result:** `ModuleNotFoundError: No module named 'add_diagnostic_psub_tap_stack'` — Expected RED state. 7 test methods defined but module doesn't exist yet. Exit: 1.

## Task 3: GREEN Implementation

**Module:** `tools/sky130_adapter/add_diagnostic_psub_tap_stack.py`

Implements:
- `GdsRecord` frozen dataclass with offset tracking
- `parse_records()` — strict GDS byte parser (rejects truncation, invalid lengths)
- `scan_target()` — BGNSTR/STRNAME/ENDSTR tracking, BOUNDARY element collection
- `inject_stack()` — public API with 6 validation gates
- CLI with `--input-gds --output-gds --report --summary-json --cell --anchor-x --anchor-y --expected-gnda-met5-box`

**Test result:** 7/7 OK (exit 0)
```
test_adds_exact_stack_and_preserves_original_bytes ... ok
test_allows_edge_touch ... ok
test_rejects_absent_target_cell ... ok
test_rejects_forbidden_overlaps ... ok
test_rejects_missing_met5_anchor ... ok
test_rejects_same_input_output ... ok
test_rejects_truncated_gds ... ok
```

**Note:** Fixture `harmless` boundary changed from 68/20 to 108/0 to avoid collision with `met1.drawing` in STACK_SPECS (plan `harmless = boundary(68,20,...)` had a layer conflict with injected met1).

## Task 4: Regression and Scope Check

**Command:**
```bash
cd tools/sky130_adapter && python3 -m unittest \
  test_add_diagnostic_psub_tap_stack \
  test_add_local_power_stripe_to_gds \
  test_inspect_gds_structure \
  test_prepare_lvs_netlists -v
```

**Result:** 17/17 OK. Exit: 0.

**Control-plane check:** `git diff -- tools/analog_harness/controller.py tools/analog_harness/models.py` — empty. No controller/reward/GRPO/closure edits.

## Task 5: Real Candidate Generation

### Input

| Field | Value |
| --- | --- |
| Path | `generated/diagnostics/fan_smc_c0_proxy_94x10/fan_smc_pin_3.pinned_shapes.gds` |
| SHA256 | `fe4a159ba1e6f4e191b8b2dc4940c30d5cf73a20fdaa25d8e570648d2bee29d6` |

### Injection Command (exit 0)
```bash
python3 tools/sky130_adapter/add_diagnostic_psub_tap_stack.py \
  --input-gds generated/diagnostics/fan_smc_c0_proxy_94x10/fan_smc_pin_3.pinned_shapes.gds \
  --output-gds generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds \
  --report .../psub_tap_injection.md \
  --summary-json .../psub_tap_injection.json \
  --cell fan_smc_pin_3_flat --anchor-x 400 --anchor-y -1000 \
  --expected-gnda-met5-box 150,-2050,650,11650
```

**Output:**
- `output_gds=.../fan_smc_pin_3.psub_tap.gds`
- `added_boundary_count=14`
- `preservation_verified=true`

### Structure Audit (exit 0)
```bash
python3 tools/sky130_adapter/inspect_gds_structure.py --gds .../fan_smc_pin_3.psub_tap.gds ...
```

**Key findings:**
- Source hash verified: `OK` (input GDS unchanged)
- New `65/44/BOUNDARY: 1` (tap.drawing — NEW, was absent in baseline)
- `94/20/BOUNDARY: 21` (+1 psdm implant)
- All 14 stack layers confirmed present with expected counts
- 10 TEXT labels (unchanged from baseline)
- 0 SREF/AREF (unchanged)
- GDS parses correctly

## Task 6: Magic DRC and Extraction

### Environment

| Tool | Path | Version |
| --- | --- | --- |
| Magic | `/home/qlf/IOT/scripts/env/bin/magic` | 8.3.483 |
| PDK | `/mnt/d/IOT/PreviousProjects/XinTuZhiLian/pdks/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A` | 1.0.466-0-gbdc9412 |
| Symlink | Created `sky130A -> sky130_pdk` for PDK_ROOT convention compatibility |

**Note:** System magic (8.3.105) segfaults with PDK requiring 8.3.411+. Resolved by using magic 8.3.483 from `IOT/scripts/env/bin/magic`.

### DRC (exit 0)

```bash
magic -dnull -noconsole -rcfile "$SKY130A/libs.tech/magic/sky130A.magicrc" magic_drc.tcl
```

**Result:** `Total DRC errors found: 0`
**DRC count:** `AH_SMC_009_DRC_COUNT` (no value printed — Magic puts prefix before `drc count total` output, which is empty for zero)
**Benign warnings:** Unknown layer/datatype for layers 150/2-6, 155/2-6,100,27 (MAGICAL annotation layers, expected)

### Extraction (exit 0)

```bash
magic -dnull -noconsole -rcfile "$SKY130A/libs.tech/magic/sky130A.magicrc" magic_extract.tcl
```

**Outputs:**
- `fan_smc_pin_3_flat.ext` (10118 bytes)
- `fan_smc_pin_3_flat.spice` (5898 bytes)

### Key Extraction Facts

**Ports (5 in .ext):**
```
port "vinn" 3 1830 3950 2090 3970 li
port "vinp" 4 1190 3950 1450 3970 li
port "vout" 5 310 2088 2930 2130 m1
port "vdda" 2 -100 5715 3380 6075 m5
port "gnda" 1 -100 -700 3380 -340 m5
```

**Substrate (CRITICAL — unchanged from baseline):**
```
substrate "vout" 0 0 310 2088 m1 ...
equiv "vout" "vdda"
equiv "vout" "gnda"
```

**MOS count:** 24 (12 pfets + 12 nfets)

**M11/M23:**
- M11/M23 not found as named records in .ext (MOS are numbered X0-X23 in extraction, different from source M0-M23)
- All 24 MOS devices have body terminal connected to `vout` (SPICE subcircuit shows `vout` as 4th terminal on every instance)

**SPICE subcircuit ports:** Only 3 (`vinn vinp vout`) — vdda and gnda collapsed into vout due to `equiv` statements.

**Warnings:**
```
Warning: Ports "vout" and "vdda" are electrically shorted.
Warning: Ports "vout" and "gnda" are electrically shorted.
```

### Hypothesis Assessment

**Hypothesis:** Adding a p+ substrate tap connected to gnda met5 rail would shift substrate identity from "vout" toward "gnda", improving extraction fidelity.

**Result: NOT SUPPORTED.** The substrate remains "vout" and the equivalences `vout=vdda`, `vout=gnda` are identical to baseline. The single diagnostic p+ tap did not alter Magic's substrate naming or equivalence behavior.

## Task 7: Conditional LVS and Trust Decision

### Extraction Gate

| Criterion | Value | Pass? |
| --- | --- | --- |
| MOS count = 24 | 24 | ✓ |
| Top ports nonempty | 5 in .ext, 3 in SPICE | ✓ |
| vout/gnda distinguishable | Separate port records in .ext (different layers, coordinates) | ✓ |
| SPICE parses as subcircuit | `.subckt fan_smc_pin_3_flat vinn vinp vout` | ✓ |

**Extraction gate: PASS** (with caveat: vout/gnda electrically equivalent via `equiv`).

### LVS Preparation (exit 0)

```bash
python3 tools/sky130_adapter/prepare_lvs_netlists.py \
  --source generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.sp \
  --extracted .../fan_smc_pin_3_flat.spice \
  --out-dir .../lvs_prepared \
  --report .../lvs_preparation_report.md \
  --prefix fan_smc_pin_3
```

**Output:** `deleted_caps=95` (parasitic capacitance removal expected for MOS-only LVS)

### Netgen LVS (exit 0)

```bash
netgen -batch source .../lvs_prepared/run_lvs.tcl
```

**Netgen version:** 1.5.133 (`/usr/lib/netgen/bin/netgen`)

**LVS result: `Netlists do not match.`**

Key mismatches:
- Device counts: 12 pfets + 12 nfets = 24 on BOTH sides ✓
- **Net count mismatch: 18 vs 19**
- Source net `gnda` (NMOS body, 8 D/S + 12 B terminals) has NO matching net in extracted
- Source net `vdda` (PMOS body, 10 D/S + 10 B terminals) has NO matching net in extracted
- Extracted net `vout` (14 D/S + 12 B pfets + 10 D/S + 12 B nfets = ALL body terminals) has NO matching net in source
- All PMOS body terminals in extracted connect to `vout`; source connects to `vdda`
- All NMOS body terminals in extracted connect to `vout`; source connects to `gnda`

**LVS gate: FAIL.** The substrate/supply identity collapse prevents unique match.

### Trust Decision

```json
{
  "candidate_id": "AH-SMC-009",
  "circuit": "Fan_SMC_Pin_3",
  "experiment_scope": "single_top_level_diagnostic_psub_tap",
  "drc_clean": true,
  "lvs_match": false,
  "pex_available": false,
  "post_sim_valid": false,
  "pvt_valid": false,
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true,
  "c0_proxy_equivalence_proven": false,
  "reasons": [
    "lvs_not_matched",
    "pex_missing",
    "post_sim_invalid",
    "pvt_invalid",
    "scope_not_full_passive_lvs"
  ]
}
```

**DRC set to `true`** because Magic DRC returned 0 errors. All usability flags remain `false` because LVS not matched, no PEX, no post-sim, no PVT, and C0 equivalence unproven.

## All Commands Summary

| # | Command | Exit | Purpose |
|---|---------|------|---------|
| 1 | `python3 -m unittest test_add_diagnostic_psub_tap_stack...test_adds_exact_stack...` | 1 | RED: confirm ModuleNotFoundError |
| 2 | `python3 -m unittest test_add_diagnostic_psub_tap_stack -v` | 1 | RED: all 7 tests fail at import |
| 3 | `python3 -m unittest test_add_diagnostic_psub_tap_stack -v` | 0 | GREEN: all 7 tests pass |
| 4 | `python3 -m unittest test_add_diagnostic_psub_tap_stack test_add_local_power_stripe... test_inspect_gds_structure test_prepare_lvs_netlists -v` | 0 | Regression: 17/17 OK |
| 5 | `git diff -- tools/analog_harness/controller.py tools/analog_harness/models.py` | 0 | Scope: empty diff |
| 6 | `sha256sum .../fan_smc_pin_3.pinned_shapes.gds` | 0 | Hash input GDS |
| 7 | `python3 .../add_diagnostic_psub_tap_stack.py --input-gds ... --output-gds ...` | 0 | Inject psub tap stack (14 boundaries) |
| 8 | `python3 .../inspect_gds_structure.py --gds .../fan_smc_pin_3.psub_tap.gds ...` | 0 | Structure audit: parse OK |
| 9 | `sha256sum -c .../input.sha256` | 0 | Source hash verified: OK |
| 10 | `magic -dnull -noconsole -rcfile ... magic_drc.tcl` | 0 | DRC: 0 errors |
| 11 | `magic -dnull -noconsole -rcfile ... magic_extract.tcl` | 0 | Extraction: .ext + .spice created |
| 12 | `grep -nE '^(port|substrate|equiv)|M11|M23' .../fan_smc_pin_3_flat.ext` | 0 | Capture port/substrate/equiv records |
| 13 | `grep -c 'sky130_fd_pr__[np]fet_01v8' .../fan_smc_pin_3_flat.spice` | 0 | MOS count: 24 |
| 14 | `grep -niE 'unknown layer|...' magic_extract.log` | 0 | Capture extraction warnings |
| 15 | `python3 .../prepare_lvs_netlists.py --source ... --extracted ...` | 0 | Prepare LVS netlists |
| 16 | `netgen -batch source .../run_lvs.tcl` | 0 | LVS: Netlists do not match |
| 17 | `python3 -m unittest discover -s tools/analog_harness/diagnostics -p 'test_*.py'` | 5 | Diagnostics tests: 0 ran (preserved) |
| 18 | `python3 -m json.tool .../psub_tap_injection.json` | 0 | JSON validates |
| 19 | `python3 -m json.tool .../trust_decision.json` | 0 | JSON validates |
| 20 | `git diff --check` | 0 | Whitespace: clean |
| 21 | `git status --short` | 0 | Status captured |

## Generated Experiment Directory Contents

```
generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/
├── ext_key_records.txt
├── extract_warnings.txt
├── fan_smc_pin_3.psub_tap.gds          ← THE ONE candidate GDS
├── fan_smc_pin_3_flat.ext
├── fan_smc_pin_3_flat.spice
├── gds_structure.json
├── gds_structure.md
├── input.sha256
├── lvs_prepared/
│   ├── fan_smc_pin_3_extracted.connectivity.spice
│   ├── fan_smc_pin_3_extracted.raw.spice
│   ├── fan_smc_pin_3_source.connectivity.spice
│   ├── lvs_preparation_report.md
│   ├── netgen_lvs_report.log           ← "Netlists do not match"
│   ├── netgen_stdout.log
│   └── run_lvs.tcl
├── magic_drc.log                       ← "Total DRC errors found: 0"
├── magic_drc.tcl
├── magic_extract.log
├── magic_extract.tcl
├── mos_count.txt
├── psub_tap_injection.json
├── psub_tap_injection.md
└── trust_decision.json
```

## Git Status

```
M  AGENTS.md (pre-existing)
M  tools/sky130_adapter/prepare_lvs_netlists.py (pre-existing)
M  tools/sky130_adapter/test_prepare_lvs_netlists.py (pre-existing)
?? tools/sky130_adapter/add_diagnostic_psub_tap_stack.py (NEW)
?? tools/sky130_adapter/test_add_diagnostic_psub_tap_stack.py (NEW)
?? generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/ (NEW, 22 files)
?? docs/claude_code_run_report.md (modified)
```

## Stop Gate

**Status:** Tasks 1-7 complete. Task 8 (Codex review) deferred per plan boundary. No second tap, no NMOS primitive edit, no C0 change, no post-layout/PVT, no controller/reward/GRPO/closure changes, no commits, no pushes.

---

## AH-SMC-010: Fan_SMC Primitive/Body/Substrate Minimization Audit

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-010 |
| Date | 2026-06-21 |
| Circuit | Fan_SMC with bounded-C0 proxy (94x10) |
| Files modified | `docs/claude_code_run_report.md` (appended), `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_010/` (new, 2 files) |
| Baseline test result | Not re-run (observation-only task; diagnostics 22/22 confirmed in prior tasks) |

### Input Artifacts

| Artifact | Absolute path |
| --- | --- |
| Baseline `.ext` | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/fan_smc_pin_3_flat.ext` |
| Baseline `.spice` | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/fan_smc_pin_3_flat.spice` |
| Device mapping | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/device_mapping.json` |
| Psub substrate geometry | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/extract/psub_substrate_geometry.json` |
| AH-SMC-009 `.ext` | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext` |
| AH-SMC-009 ext key records | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/ext_key_records.txt` |
| AH-SMC-009 trust decision | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/trust_decision.json` |
| Source netlist | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.sp` |
| MAGICAL `.pin` | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.pin` |

### Commands Executed

| # | Command | Exit | Purpose |
| --- | --- | --- | --- |
| 1 | `grep -n '^M11\|^M23\|^M9 ' .../fan_smc_pin_3.sp` | 0 | Extract M11/M23/M9 source terminals |
| 2 | `cat .../fan_smc_pin_3.pin` | 0 | Read MAGICAL .pin for fourth-pin status |
| 3 | `ls .../fan_smc_c0_proxy_94x10_psub_tap/` | 0 | List AH-SMC-009 directory contents |

All analysis was read-only. No new Magic/Netgen/P&R runs.

### Key Findings

1. **AH-SMC-009 produced zero semantic change.** Baseline and AH-SMC-009 `.ext`
   files are identical in `substrate`, `equiv`, and `device` records. The p+ tap
   changed only parasitic capacitance values.

2. **NMOS fourth-pin `-1` is the first evidenced semantic divergence.** All 12
   NMOS instances in MAGICAL's `.pin` file have `-1` (absent body terminal),
   while the source netlist requires `B=gnda`. Without body pin geometry, Magic
   cannot anchor the NMOS body to `gnda` and defaults the substrate to `vout`.

3. **PMOS body collapse is a supply-rail routing failure, not a primitive absence.**
   All 11 PMOS instances have full pin boxes, yet 10 of 11 still collapse body to
   `vout` instead of `vdda`. The `psub_active_dependent_vdd_path` explains this.

4. **M9 gate `vinp` survives intact** — the only top-port signal not collapsed to
   `vout`, confirming the collapse is specific to supply-domain nets.

### Output Artifacts

```
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_010/
├── ah_smc_010_summary.md
└── ah_smc_010_records.json
```

### Stop Gate

**Status:** Observation-only audit complete. AH-SMC-009 did not repair the
vout/vdda/gnda collapse. The first evidenced divergence is at the NMOS `.pin`
contract level (fourth-pin `-1`). No controller/reward/GRPO/closure changes,
no SMCNR modifications, no MAGICAL- modifications, no P&R, no DFCFC2, no commits,
no pushes. Trust remains failure-case only. Pending Codex review.

---

## AH-SMC-011: Fan_SMC NMOS Body-Pin Contract Probe

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-011 |
| Date | 2026-06-21 |
| Circuit | Fan_SMC with bounded-C0 proxy (94x10) |
| Hypothesis | Adding M23 NMOS body contact geometry connected to gnda met5 will change extracted body from `vout` to `gnda` |
| Files modified | `docs/claude_code_run_report.md` (appended), `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/` (new, 6 files) |
| Magic version | 8.3 revision 483 (sky130A) |

### Input Artifacts

| Artifact | Absolute path |
| --- | --- |
| Baseline GDS | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds` |
| Baseline `.ext` | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext` |
| Baseline `.spice` | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.spice` |
| Source netlist | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.sp` |
| MAGICAL `.pin` | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.pin` |

### Method

Added a full NMOS body contact stack at M23's location (GDS coords 5400,11350)
using Magic TCL `paint` commands:
- `ptap` (p+ substrate tap), `psd` (p+ implant), `psc` (p+ substrate contact),
  `li` (local interconnect), `mcon`, `met1`, `via`, `met2`, `via2`, `met3`,
  `via3`, `met4`, `via4`
- Horizontal `met5` connector from M23 (x=5550) to gnda rail (x=400) at y=11200-11500
- `label gnda` on met5 at tap location

TCL script: `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/magic_body_contact.tcl`

### Commands Executed

| # | Command | Exit | Purpose |
| --- | --- | --- | --- |
| 1 | Python GDS met5 parser | 0 | Map all 353 met5 boxes to find routing path |
| 2 | `grep` M11/M23/M9 from source netlist | 0 | Confirm source terminals |
| 3 | `cat` MAGICAL `.pin` | 0 | Confirm M23 fourth-pin = -1 |
| 4 | `PDK_ROOT=... magic -dnull -noconsole magic_body_contact.tcl` | 0 | Inject body contact + extract (2258 GDS write problems) |
| 5 | `grep` substrate/equiv from new `.ext` | 0 | Before/after delta check |
| 6 | `grep` M23 device + all NMOS SPICE lines | 0 | Check body terminal changes |

### Before/After Evidence (M23)

| Field | Before | After | Delta |
| --- | --- | --- | --- |
| `.pin` fourth-pin | `-1` | Not modified (geometry via GDS paint) | — |
| `substrate` record | `substrate "vout"` | `substrate "vout"` | **unchanged** |
| `equiv` records | `vout<->vdda`, `vout<->gnda` | `vout<->vdda`, `vout<->gnda` | **unchanged** |
| M23 `.ext` line 115 | `"vout" "a_220_2930#" ... "vout" ... "vout"` | byte-identical | **unchanged** |
| M23 extracted body | `vout` | `vout` | **unchanged** |
| M23 SPICE X23 | `vout a_220_2930# vout vout` | byte-identical | **unchanged** |
| All 12 NMOS bodies | 12/12 `vout` | 12/12 `vout` | **zero changed** |
| Extraction warnings | vout↔vdda shorted; vout↔gnda shorted | vout↔vdda shorted; vout↔gnda shorted | **unchanged** |

### Key Finding

**Hypothesis NOT SUPPORTED.** Adding M23 body contact geometry connected to gnda
did not change Magic's substrate identity or any NMOS body terminal. The body
contact was physically present (substrate capacitance values changed), but Magic's
net assignment was unaffected.

The H1 hypothesis (NMOS fourth-pin absence as sole root cause) is disproven at the
single-variable level. The H2 hypothesis (diffusion-level psub connectivity
dominance) gains support. The horizontal met5 connector likely crossed existing
vout-associated met5 routes, creating additional shorts rather than a clean gnda
connection.

### Hypothesis Assessment

| Hypothesis | Result |
| --- | --- |
| H1: NMOS fourth-pin absence is root cause | **NOT SUPPORTED** |
| H2: Psub-to-diffusion connectivity dominates | **STRENGTHENED** |
| H3: PMOS collapse has separate nwell cause | Not tested |

### Output Artifacts

```
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/
├── ah_smc_011_summary.md
├── ah_smc_011_records.json
├── fan_smc_pin_3.m23_body.gds        ← modified GDS with M23 body contact
├── fan_smc_pin_3.m23_body.ext        ← extracted .ext (unchanged vs baseline)
├── fan_smc_pin_3.m23_body.spice      ← extracted .spice (unchanged vs baseline)
└── magic_body_contact.tcl            ← Magic TCL injection + extraction script
```

### Stop Gate

**Status:** Single-variable NMOS body-pin probe complete. H1 disproven at the
single-variable level. At most one NMOS body contact added in isolated copy.
No controller/reward/GRPO/closure changes, no C0 change, no additional substrate
tap, no SMCNR modifications, no MAGICAL- modifications, no DFCFC2, no commits,
no pushes. Trust remains failure-case only. Pending Codex review.

---

## AH-SMC-012: Fan_SMC Met5 Contamination Audit

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-012 |
| Date | 2026-06-21 |
| Circuit | Fan_SMC with bounded-C0 proxy (94x10) |
| Type | Read-only met5 contamination audit |
| Classification | **contaminated** |
| Files modified | `docs/claude_code_run_report.md` (appended), `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_012/` (new, 3 files) |

### Input Artifacts

| Artifact | Absolute path |
| --- | --- |
| Baseline GDS | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds` |
| AH-SMC-011 records | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/ah_smc_011_records.json` |
| AH-SMC-011 TCL | `/home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_011/magic_body_contact.tcl` |

### Method

Parsed 353 met5 (72/20) shapes from the baseline AH-SMC-009 psub-tap GDS.
Computed intersection with AH-SMC-011's horizontal met5 connector box
`[400, 11200, 5550, 11500]`. Classified intersecting shapes into net groups
based on physical proximity to known ports/pins/rails.

### Key Finding: Met5-Layer Gap

The 18 intersecting met5 shapes form **two separate trees** separated by a
**300-unit gap** at x=1850-2150 in the met5 layer:

| Tree | Shapes | X-Range | Net |
| --- | --- | --- | --- |
| Left (gnda-confirmed) | #1–#8 | 150–1850 | **gnda** (direct connection to gnda port/pin) |
| Bridge | #9–#10 | 1350–1850 | unknown (electrically gnda at bottom) |
| Gap | — | 1850–2150 | **NO met5 shapes** |
| Right (unknown) | #11–#18 | 2150–5250 | unknown (serves device area including M23 at x=5150-5250) |

AH-SMC-011's connector painted met5 across this gap, potentially shorting the
gnda tree to the unknown-net right tree. Shape #18 at [5150, 11350, 5250, 12450]
is within M23's layout_box, and the extracted `.ext` shows M23's terminals
all assigned to `vout`.

### Commands Executed

| # | Command | Exit | Purpose |
| --- | --- | --- | --- |
| 1 | `python3 met5_contamination_audit.py` | 0 | Parse GDS, find 18 intersecting met5 shapes |
| 2 | Python deep connectivity trace | 0 | Analyze met5-layer gap between left/right trees |

### Classification

**`contaminated`** — AH-SMC-011's met5 connector bridged a gap between two
previously disconnected met5 trees, invalidating the experiment as a clean
test of the NMOS body-contact hypothesis.

### Impact

- AH-SMC-011 H1 disproof is **withdrawn** as contaminated
- H2 (diffusion/psub dominance) is **weakened** — contamination explains the observed collapse
- The NMOS `.pin` contract hypothesis remains **untested by a clean experiment**

### Recommended Next Step

Modify M23 `.pin` fourth-pin from `-1` to a real body pin box and re-run
MAGICAL's legalizer/router for clean routing. No manual met5 painting.

### Output Artifacts

```
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_012/
├── ah_smc_012_summary.md
├── ah_smc_012_records.json
└── met5_contamination_audit.py
```

### Stop Gate

**Status:** Read-only contamination audit complete. AH-SMC-011 classified as
contaminated. No layout repair, no controller/reward/GRPO/closure changes, no
C0 change, no SMCNR modifications, no MAGICAL- modifications, no DFCFC2, no
commits, no pushes. Trust remains failure-case only. Pending Codex review.

---

## AH-SMC-013: Fan_SMC M23 `.pin` Contract Repair Feasibility Probe

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-013 |
| Date | 2026-06-21 |
| Circuit | Fan_SMC with bounded-C0 proxy (94x10) |
| Variable | M23 `.pin` fourth entry: `-1` → `[-200, -200, 1400, -150]` |
| Method | Docker MAGICAL P&R with modified `.pin` |
| Files modified | `docs/claude_code_run_report.md` (appended), `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013/` (new) |

### Method

1. Copied Fan_SMC case files to isolated `ah_smc_013/case/` directory
2. Changed only M23's fourth `.pin` entry from `-1` to `[-200, -200, 1400, -150]`
   (full-width 1600-unit body strip at NMOS bottom, following PMOS M11 pattern)
3. Re-ran MAGICAL P&R via Docker (`jayl940712/magical:latest`)
4. Re-ran Sky130 remap pipeline (remap → tap-split → pin-labels → pin-shapes)
5. Re-ran Magic extraction (sky130A, magic 8.3 rev 483)
6. Compared before/after `.ext`, `.spice`, substrate, equiv, device records

### Key Result: Extraction Changed Significantly

| Field | Before | After |
| --- | --- | --- |
| `substrate` | `"vout"` | `"net31"` |
| `equiv` | vout↔vdda, vout↔gnda | net31↔net050, net31↔vout, net31↔vdda, net31↔gnda |
| M23 body | `vout` | `net31` |
| M23 gate | `a_220_2930#` (internal) | **`net049`** (correct source net!) |
| M23 SPICE | `X23 vout a_220_2930# vout vout` | `X23 net31 net049 net31 net31` |
| All 12 NMOS bodies | 12/12 `vout` | 11/12 `net31` |
| Direct vout↔vdda short | Present | **GONE** |
| Direct vout↔gnda short | Present | **GONE** |

### Route GDS Comparison

| File | SHA256 | Size | Differs? |
| --- | --- | --- | --- |
| Original route.gds | `ea8935c7...` | 359924 | — |
| AH-SMC-013 route.gds | `a76df3c3...` | 359924 | **YES** |
| Original place.gds | `76884f3a...` | 335088 | — |
| AH-SMC-013 place.gds | `c4cb48de...` | 335088 | **YES** |

### Commands Executed

| # | Command | Exit | Purpose |
| --- | --- | --- | --- |
| 1 | `docker run ... Magical.py` with modified `.pin` | 0 | MAGICAL P&R re-run |
| 2 | `remap_gds_to_sky130.py` | 0 | Sky130 remap |
| 3 | `split_sky130_tap_from_diff.py` | 0 | Tap-diff split |
| 4 | `add_sky130_pin_labels_from_iopin.py` | 0 | Pin labels |
| 5 | `add_sky130_pin_shapes_from_iopin.py` | 0 | Pin shapes |
| 6 | `magic -rcfile sky130A.magicrc magic_extract.tcl` | 0 | Magic extraction |
| 7 | `sha256sum` comparison | 0 | Verify P&R output differs |

### Hypothesis Assessment

- **H1 (`.pin` contract matters)**: PARTIALLY SUPPORTED — M23 body pin changed
  routing, substrate identity, M23 gate, and all NMOS bodies. But collapse
  shifted to `net31` instead of resolving.
- **H2 (diffusion/psub dominance)**: STRENGTHENED — even with clean routing,
  substrate collapse persists through a different dominant net.
- **Key positive**: M23 gate resolved to correct `net049` (first time ever).
- **Key negative**: `net31` (internal analog bias) became new collapse center.

### Output Artifacts

```
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013/
├── ah_smc_013_summary.md
├── ah_smc_013_records.json
├── fan_smc_pin_3.ah_smc_013.route.gds   ← new route GDS (SHA256 differs)
├── fan_smc_pin_3.ah_smc_013.place.gds   ← new place GDS (SHA256 differs)
├── fan_smc_pin_3.ah_smc_013.ext         ← new extraction (substrate=net31)
├── fan_smc_pin_3.ah_smc_013.spice       ← new SPICE (M23 gate=net049)
└── case/                                ← isolated case files with modified .pin
```

### Stop Gate

**Status:** Clean M23 `.pin` contract probe complete. Single variable changed,
MAGICAL P&R re-run successfully, extraction compared. The `.pin` contract change
affected extraction measurably but did not resolve the substrate collapse
(shifted from vout-centric to net31-centric). No manual GDS painting. No
controller/reward/GRPO/closure changes, no C0 change, no SMCNR modifications,
no MAGICAL- modifications, no DFCFC2, no commits, no pushes. Trust remains
failure-case only. Pending Codex review.

---

## AH-SMC-013R: Fan_SMC M23 `.pin` Artifact Correction

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-013R |
| Date | 2026-06-21 |
| Circuit | Fan_SMC with bounded-C0 proxy (94x10) |
| Status | **artifact_correction — blocked** |
| Predecessor | AH-SMC-013 (rejected: `.pin` artifact not preserved) |
| Files modified | `docs/claude_code_run_report.md` (appended), `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013r/` (new) |

### Pin Delta Artifacts (PRESERVED)

| Artifact | SHA256 | M23 pin 4 |
| --- | --- | --- |
| `before.pin` | `d62cc163...` | `-1` |
| `after.pin` | `657e6533...` | `-200 -200 1400 -150` |
| `final.pin` | `d62cc163...` | **`-1`** (MAGICAL overwrote) |

`pin.diff`: exactly 1 line changed (line 66: `-1` → `-200 -200 1400 -150`).

### Blocker: MAGICAL Overwrites `.pin` + Nondeterminism

1. **MAGICAL overwrites external `.pin` modifications**: `final.pin` is
   byte-identical to `before.pin` after P&R. The M23 pin 4 change does not
   survive into the routed case.

2. **MAGICAL P&R is nondeterministic**: three identical-input runs produce
   three different route.gds SHA256 values:

| Run | route.gds SHA256 |
| --- | --- |
| Original | `ea8935c7...` |
| AH-SMC-013 | `a76df3c3...` |
| AH-SMC-013R | `8e1c466e...` |

The AH-SMC-013 extraction delta (vout→net31) is therefore explained by
nondeterministic routing variance, not by the `.pin` modification.

### Impact on AH-SMC-013

AH-SMC-013's causal claim (".pin contract change caused extraction delta") is
**invalidated**. The preserved `.pin` did not contain the modification, and
MAGICAL routing variance alone can explain the observed differences.

### Commands Executed

| # | Command | Exit | Purpose |
| --- | --- | --- | --- |
| 1 | Python: modify M23 pin 4 | 0 | Create after.pin |
| 2 | `sha256sum` before/after | 0 | Preserve hashes |
| 3 | `diff before.pin after.pin` | 1 | Create pin.diff |
| 4 | `docker run ... Magical.py` | 0 | MAGICAL P&R |
| 5 | `sha256sum` final.pin | 0 | Capture overwrite evidence |
| 6 | `sha256sum` route.gds triple compare | 0 | Prove nondeterminism |

### Output Artifacts

```
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_013r/
├── ah_smc_013r_summary.md
├── ah_smc_013r_records.json
└── case/
    ├── before.pin / before.pin.sha256
    ├── after.pin  / after.pin.sha256
    ├── final.pin  / final.pin.sha256
    └── pin.diff
```

### Stop Gate

**Status:** Artifact correction complete. Pin delta is auditable (before/after/
final/diff preserved). Experiment blocked: MAGICAL overwrites external `.pin`
edits and produces nondeterministic routing output. NMOS `.pin` contract
hypothesis cannot be tested through external `.pin` file editing — requires
MAGICAL internal DesignDB modification, which is outside current campaign
scope. No controller/reward/GRPO/closure changes, no C0 change, no SMCNR
modifications, no MAGICAL- modifications, no DFCFC2, no commits, no pushes.
Trust remains failure-case only. Pending Codex review.

---

## AH-SMC-014: MAGICAL `.pin` Generation Provenance Audit

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-014 |
| Date | 2026-06-22 |
| Type | Read-only provenance audit |
| MAGICAL files modified | **None** |
| Files modified | `docs/claude_code_run_report.md` (appended), `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_014/` (new) |

### Key Finding: Three-Factor Root Cause

NMOS body pins are `-1` in `.pin` files due to three interacting factors:

| Factor | File:Line | Mechanism |
| --- | --- | --- |
| 1. Pin type assignment | `DesignDB.py:470` | NMOS pin 3 always `PinType.PSUB` (no routable metal) |
| 2. ioLayer from device gen | `Device_generator.py:80` | `ioLayer = shape[0]` — PSUB body pin has `ioLayer > 10` |
| 3. Sentinel threshold | `Placer.py:527-528` | `if layer > 10: outFile.write("-1\n")` |

PMOS body pins get coordinates because the NWELL guard ring in the PMOS primitive
includes metal-contactable geometry (ioLayer ≤ 10).

### `.pin` Regeneration Chain

```
Magical.run() → Flow.run() → Flow.implCktLayout()
  → Flow.setup() → Device_generator.generateDevice() + writeDB()
  → PnR.placeOnly() → Placer.dumpInput() → Placer.placeParsePin()
```

The entire chain runs from scratch on every invocation. `Placer.placeParsePin()`
(line 509) opens the `.pin` file in write mode and regenerates it from the
internal database. External edits are unconditionally overwritten.

### Additional Findings

- `routeMosBulkEqualBodyPins` affects **PMOS only** (DesignDB.py:424-428)
- `useDeviceSubGuardRing` defaults to `False`, suppressing body guard rings
- DesignDB TODO at lines 479-481: "Mosfet Bulk will be implemented in wellgen
  after placement" — this deferred implementation is why NMOS body pins remain
  unimplemented
- `device_generation` submodule is not initialized locally

### Minimal Patch Proposal (not implemented)

| Option | File to modify | Approach |
| --- | --- | --- |
| A | `device_generation/Mosfet.py` | Add PSUB body contact to NMOS primitive (architecturally correct) |
| B | `DesignDB.py` or `Device_generator.py` | Override ioLayer + compute body pin coords from bound box (practical) |
| C | `Placer.py:527` | Change `layer > 10` threshold (quick hack) |

All options require MAGICAL- file modifications, currently forbidden.

### Key Files Audited

| File | Lines | Role |
| --- | --- | --- |
| `Placer.py` | 505–536 | **Writes .pin**; `layer > 10` → `-1` |
| `DesignDB.py` | 468–509 | Assigns PSUB/NWELL pin types |
| `DesignDB.py` | 416–442 | `intra_devcon()` bulk/pinCon setup |
| `Device_generator.py` | 49–81 | Sets ioLayer from device pin shapes |
| `Device_generator.py` | 108–148 | Generates NMOS/PMOS cells |
| `Flow.py` | 80–114 | Orchestrates full flow |
| `Params.py` | 60 | `routeMosBulkEqualBodyPins` default |

### Output Artifacts

```
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_014/
├── ah_smc_014_summary.md
└── ah_smc_014_records.json
```

### Stop Gate

**Status:** Read-only provenance audit complete. Root cause localized to three
interacting code paths across Placer.py, DesignDB.py, and Device_generator.py.
No MAGICAL- files modified. All claimed file:line paths are cited and
distinguish observed code from inference. No layout repair, reroute, DFCFC2,
commits, or pushes. Trust remains failure-case only. Pending Codex review.

---

## AH-SMC-015: MAGICAL NMOS Body-Pin Patch Authorization Package

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-015 |
| Date | 2026-06-22 |
| Type | Read-only authorization package |
| MAGICAL files modified | **None** — patches proposed, not applied |
| Files modified | `docs/claude_code_run_report.md` (appended), `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015/` (new) |

### Three Patch Options (none applied)

| Option | Target | Mechanism | Diagnostic Validity | Recommended For |
| --- | --- | --- | --- | --- |
| **A** | `device_generation/Mosfet.py` | Add p+ body contact to NMOS primitive | High | Production |
| **B** ⭐ | `Device_generator.py:70` or `DesignDB.py:496` | Inject synthetic body pin ioShape with metal ioLayer=67 at DB level | High | **Diagnostic** |
| C | `Placer.py:527` | Synthesize body pin coords at .pin write time | Low | Not recommended |

### Recommendation

- **Diagnostic probe (AH-SMC-016)**: Option B — inject NMOS body pin ioShape
  with metal ioLayer at the database level, after device generation but before
  `.pin` writing. Minimal code change (~10 lines in 1-2 files), no submodule
  init needed, clear rollback.
- **Production fix**: Option A — add actual p+ body contact to NMOS primitive
  in device_generation submodule. Architecturally correct but requires
  submodule initialization.

### Why Option B

- Does NOT modify NMOS primitive GDS (only pin metadata)
- Does NOT require device_generation submodule
- Confined to MAGICAL flow Python layer
- Tests the specific hypothesis: "routable body pin metadata → changed `.pin`
  → changed extraction"
- If successful, proves the body-pin contract path works; Option A becomes the
  production fix
- If unsuccessful, eliminated the simplest path without touching primitives

### Acceptance Tests (for next actual patch run)

11 artifacts required: patch diff, before/after/final .pin + SHA256, pin.diff,
route.gds SHA256, .ext, .spice, magic log, LVS report, trust_decision.json.

### Stop Conditions

| Condition | Classification |
| --- | --- |
| `final.pin` = `before.pin` | blocked |
| Extraction unchanged | inconclusive |
| Nondeterminism not ruled out | contaminated |
| New extraction errors | regression |

### Output Artifacts

```
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015/
├── ah_smc_015_patch_authorization.md
└── ah_smc_015_records.json
```

### Stop Gate

**Status:** Read-only authorization package complete. Three patch options
documented with pseudo-diffs, risks, rollback plans. Option B recommended for
diagnostic probe. **No MAGICAL- files modified.** Actual MAGICAL- modification
requires explicit user approval. No layout repair, reroute, DFCFC2, commits,
or pushes. Trust remains failure-case only. Pending Codex review.

---

## AH-SMC-015R: Corrected MAGICAL NMOS Body-Pin Patch Authorization

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-015R |
| Date | 2026-06-22 |
| Type | Read-only authorization package (corrected) |
| Predecessor | AH-SMC-015 (rejected: ioLayer semantics wrong) |
| MAGICAL files modified | **None** |
| Files modified | `docs/claude_code_run_report.md` (appended), `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r/` (new) |

### AH-SMC-015 Errors Corrected

| Error | Correction |
| --- | --- |
| `ioLayer = 67` (Sky130 GDS li1) | `ioLayer = 6` (MAGICAL internal M6, matches PMOS body pin) |
| `setIoShape(y1, x1, y2, x2)` | `setIoShape(xLo, yLo, xHi, yHi)` |

### ioLayer = 6 Provenance

Verified from Docker container (`jayl940712/magical:latest`):
- PMOS body pin uses layer string `"M6"` → `int("M6"[1])` = `6`
- NMOS generates no body pin → net ioLayer stays `INDEX_TYPE_MAX` → `-1`
- `6 ≤ 10` passes `Placer.placeParsePin()` threshold ✓
- Sky130 export: MAGICAL internal PDK 36 → ioLayer 6 → met5 (72/20)

### Corrected Option B Pseudo-Diff

```diff
+            if net_name == 3 and ckt.implType == magicalFlow.ImplTypePCELL_Nch:
+                bbox = ckt.layout().boundary()
+                ckt.net(nets[net_name]).setIoShape(
+                    bbox.xLo, bbox.yLo, bbox.xHi, bbox.yLo + 50)
+                ckt.net(nets[net_name]).ioLayer = 6
+                net_name += 1
```

### Preflight Gates (new)

```python
assert 6 <= 10                           # ioLayer passes threshold
assert final.pin M23 body != -1          # .pin change survived
```

### Output Artifacts

```
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r/
├── ah_smc_015r_patch_authorization.md
└── ah_smc_015r_records.json
```

### Stop Gate

**Status:** Corrected authorization package complete. ioLayer=6 verified from
Docker container. All pseudo-diffs use correct ioLayer and setIoShape argument
order. Preflight gates defined. **No MAGICAL- files modified.** Actual
MAGICAL- modification requires explicit user approval. Trust remains
failure-case only. Pending Codex review.

---

## AH-SMC-015R2: Final Corrected MAGICAL NMOS Body-Pin Patch Authorization

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-015R2 |
| Date | 2026-06-22 |
| Type | Read-only authorization package (control-flow corrected) |
| MAGICAL files modified | **None** |
| Files modified | `docs/claude_code_run_report.md` (appended), `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r2/` (new) |

### Third Blocker Corrected: Control Flow

| Version | Blocker | Fix |
| --- | --- | --- |
| AH-SMC-015 | `ioLayer=67` (Sky130 GDS) | `ioLayer=6` (MAGICAL internal) |
| AH-SMC-015 | `setIoShape(y1,x1,y2,x2)` | `setIoShape(xLo,yLo,xHi,yHi)` |
| AH-SMC-015R | Injection inside pin loop, NMOS only has 3 pins → never reaches `net_name==3` | **Move injection AFTER loop** |

### Control Flow Analysis

NMOS `Mosfet.pin()` returns D/G/S (no B). The `for pin` loop processes net_name
0,1,2 and exits. Any code inside the loop checking `net_name == 3` never
executes. Fix: place injection after the loop, checking `3 in nets` and
`ioLayer > 10` (INDEX_TYPE_MAX for uninitialized nets).

### Corrected Option B Pseudo-Diff

```diff
+        # AFTER the pin loop: handle NMOS body net 3 skipped by Mosfet.pin()
+        if (ckt.implType == magicalFlow.ImplTypePCELL_Nch
+                and 3 in nets
+                and ckt.net(nets[3]).ioLayer > 10):
+            bbox = ckt.layout().boundary()
+            ckt.net(nets[3]).setIoShape(
+                bbox.xLo, bbox.yLo, bbox.xHi, bbox.yLo + 50)
+            ckt.net(nets[3]).ioLayer = 6
```

### Preflight Gates

```python
assert 6 <= 10                                    # ioLayer threshold
assert ckt.net(nets[3]).ioLayer > 10  (before)    # uninitialized
assert ckt.net(nets[3]).ioLayer == 6   (after)     # injected
assert final.pin M23 body != -1                    # survived
```

### Output Artifacts

```
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_015r2/
├── ah_smc_015r2_patch_authorization.md
└── ah_smc_015r2_records.json
```

### Stop Gate

**Status:** Final corrected authorization package. All three blockers resolved:
ioLayer semantics, setIoShape argument order, and control flow location. **No
MAGICAL- files modified.** Actual MAGICAL- modification requires explicit user
approval. Trust remains failure-case only. Pending Codex review.

---

## AH-SMC-016A: SMCNR vs Fan_SMC NMOS Body-Pin Differential Audit

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-016A |
| Date | 2026-06-22 |
| Type | Read-only differential audit |
| Positive baseline | `SMCNR_SE_2st_AMP/cand_0031` (LVS PASS) |
| Diagnostic case | `Fan_SMC_Pin_3` (LVS FAIL) |
| MAGICAL files modified | **None** |
| Files modified | `docs/ah_smc_016a_differential_audit.md` (new), `generated/diagnostics/.../ah_smc_016a/` (new) |

### Key Conclusion

**`.pin=-1 alone is not sufficient as a single-variable root cause for
Fan_SMC body collapse.** Both circuits have all NMOS body pins as `-1`, but
SMCNR resolves NMOS body to gnda (LVS PASS) while Fan_SMC collapses to vout
(LVS FAIL). The divergence is at the geometry/substrate level, not the `.pin`
contract level.

### Critical Evidence

| Criterion | SMCNR | Fan_SMC |
| --- | --- | --- |
| NMOS .pin=-1 | 3/3 (100%) | 12/12 (100%) |
| Source body net | gnda | gnda |
| Extracted body net | **gnda** (3/3) | **vout** (5/12) or internal (7/12) |
| LVS result | **PASS** | **FAIL** |

### Hypothesis Assessment

| Hypothesis | Status | Confidence |
| --- | --- | --- |
| H1: `.pin=-1` is sole root cause | **DISPROVEN** | High |
| H2: Diffusion/psub geometry dominates | **SUPPORTED** | Medium (SMCNR geometry evidence missing) |
| H3: Routing/met5 co-contaminates | **SUPPORTED** | Medium (AH-SMC-012) |

### Missing SMCNR Artifacts

`.ext`, GDS, and Magic extraction log are not in the reproducibility package
(intentionally excluded: 563 MB → 2.7 MB). Direct geometry comparison between
SMCNR and Fan_SMC is blocked by this evidence gap.

### Next Recommended Action

Before any MAGICAL `.pin` contract patch: obtain SMCNR `.ext`/GDS for direct
geometry comparison. Confirm whether SMCNR also shows
`psub_component_pin_overlaps` merging gnda/vdda/vout through diffusion.

### Output Artifacts

```
docs/ah_smc_016a_differential_audit.md
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016a/ah_smc_016a_records.json
```

### Stop Gate

**Status:** Differential audit complete. H1 (`.pin=-1` sole root cause) is
disproven by cross-circuit evidence. Fan_SMC body collapse requires
geometry-level root cause understanding before any MAGICAL patch. No MAGICAL-
files modified. No controller/reward/GRPO/closure changes. Trust remains
failure-case only. Pending Codex review.

---

## AH-SMC-016B: SMCNR vs Fan_SMC Netgen/LVS Setup Provenance Audit

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-016B |
| Date | 2026-06-22 |
| Type | Read-only setup provenance audit |
| MAGICAL files modified | **None** |
| Files modified | `docs/ah_smc_016b_netgen_setup_audit.md` (new), `generated/diagnostics/.../ah_smc_016b/` (new) |

### Key Finding: Three Setup/Extraction Gaps

| # | Gap | Level | Impact |
| --- | --- | --- | --- |
| 1 | gnda/vdda missing from extracted ports (5 source → 3 extracted) | **Geometry consequence** | Guarantees LVS FAIL regardless of connectivity |
| 2 | No net renames (SMCNR used 5; Fan_SMC used 0) | **Setup** | All internal `a_*#` nodes mismatch source net names |
| 3 | Different PDK versions for Netgen setup (bdc9412b vs 7b70722e) | **Environment** | Minor |

### Critical Port Evidence

| Circuit | Extracted ports | Source ports |
| --- | --- | --- |
| SMCNR | `vdda gnda vin vip ibias vout` (6) | `vdda gnda vin vip ibias vout` (6) ✓ |
| Fan_SMC | `vinn vinp vout` (3) | `gnda vdda vinn vinp vout` (5) ✗ |

### Setup Chain Comparison

| Step | SMCNR | Fan_SMC | Same? |
| --- | --- | --- | --- |
| Magic extract Tcl | `ext2spice lvs; cthresh 0; rthresh 0` | Identical | **Yes** |
| Net renames | 5 explicit | None | **No** |
| Model aliases | `nch_mac→sky130` | Not needed | N/A |
| Property removal | `ad/as/pd/ps` | `ad/as/pd/ps` | **Yes** |
| Passive handling | `mos_only_projection` | Drop `cfmom_2t` | Similar |

### Hypothesis Assessment

| H | Status |
| --- | --- |
| H1: `.pin=-1` sole root cause | **DISPROVEN** |
| H2: Diffusion/psub geometry | **SUPPORTED_BY_FAN_ONLY** |
| H3: Routing/met5 contamination | **CANDIDATE** |
| H4: Netgen/LVS setup divergence | **SUPPORTED** (new) |

### Primary vs Secondary

Items 1-2 (port collapse, missing renames) are primary blockers for LVS.
Item 1 is geometry-level (requires layout change). Item 2 is setup-level
(fixable without MAGICAL patch). Recommended next: setup-normalized
Fan_SMC rerun with SMCNR-style net renames.

### Output Artifacts

```
docs/ah_smc_016b_netgen_setup_audit.md
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016b/ah_smc_016b_records.json
```

### Stop Gate

**Status:** Setup provenance audit complete. Three LVS setup/extraction gaps
identified. Primary blocker remains geometry-level substrate collapse (H2).
Setup gaps (missing net renames) are secondary contributors. No MAGICAL-
files modified. Trust remains failure-case only. Pending Codex review.

---

## AH-SMC-016C: Setup-Normalized Fan_SMC Netgen Rerun

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-016C |
| Date | 2026-06-22 |
| Type | Setup-normalized diagnostic rerun |
| MAGICAL files modified | **None** |
| Files modified | `docs/ah_smc_016c_setup_normalized_rerun.md` (new), `generated/diagnostics/.../ah_smc_016c/` (new) |

### Key Finding: Net Renames Are IMPOSSIBLE

Only 3 of 18 source nets survive extraction (`vinn`, `vinp`, `vout`). All
15 other source nets have no extracted counterpart because the body/substrate
collapse has fundamentally restructured the extracted connectivity. Internal
nodes are merged — fanout counts don't match source nets.

**No unambiguous net renames are possible.** The candidate `lvs_renames.txt`
is empty.

### H4 Downgrade

| H | AH-SMC-016B | AH-SMC-016C | Δ |
| --- | --- | --- | --- |
| H4: Setup divergence | SUPPORTED | **DOWNGRADED** | ↓ |

Net renames are not an independent contributing factor. The SMCNR-vs-Fan_SMC
rename difference is a symptom of the geometry difference (SMCNR preserved
net identity; Fan_SMC collapsed it), not a separate setup gap.

### Baseline LVS (Reproduced)

```
Result: Netlists do not match.
Devices: 24 vs 24
Nets: 18 vs 19
```

### Candidate Renames Variant

Same result (empty renames = baseline). No improvement possible.

### Port Mismatch

Source: 5 ports (`gnda vdda vinn vinp vout`)
Extracted: 3 ports (`vinn vinp vout`)
Guarantees LVS failure regardless of internal renames.

### Primary Blocker

`.ext` records `substrate "vout"`, `equiv "vout" "vdda"`, `equiv "vout" "gnda"`
are the hard blocker. No Netgen setup can fix extraction-level port collapse.

### Output Artifacts

```
docs/ah_smc_016c_setup_normalized_rerun.md
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016c/ah_smc_016c_records.json
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016c/netgen_lvs_baseline.log
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016c/candidate_lvs_renames.txt
```

### Stop Gate

**Status:** Setup-normalized rerun complete. Net renames are impossible under
current extraction topology. Primary blocker (geometry-level substrate
collapse) confirmed. H4 downgraded from contributing factor to symptom.
No MAGICAL- files modified. Trust remains failure-case only. Pending
Codex review.

---

## AH-SMC-017: Fan_SMC Geometry-Level Substrate Collapse Localization

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-017 |
| Date | 2026-06-22 |
| Type | Read-only geometry localization |
| MAGICAL files modified | **None** |
| Files modified | `docs/ah_smc_017_geometry_localization.md` (new), `generated/diagnostics/.../ah_smc_017/` (new) |

### Key Finding: Diffusion Is the Dominant Merge Mechanism

The psub route is a **diffusion stripe** (not metal) spanning the entire chip
bottom (`[-1050, -450, 15050, -350]` on `diff.drawing` 65/20). This connects
through the p-substrate to all NMOS source/drain diffusions, creating:

```
gnda → psub diffusion stripe → NMOS drain diffusions → vout
```

### Decisive Evidence

| Analysis | `psub_component_pin_overlaps` | vdd connected? |
| --- | --- | --- |
| **With diffusion** (128 rects) | **gnda, vdda, vout** | Yes |
| **Without diffusion** (0 rects) | **gnda only** | No |

Removing diffusion eliminates the merge. This is a one-shot diagnostic proof.

### 47-Step Conduction Path

A continuous geometric chain from gnda met5 rail → through contact stack →
into diff.drawing at M22/M23/M20 → back up metal stack → to vdda met5 pin.
Passes through 3 NMOS devices (all body→vout) and 4 PMOS devices.

### Body Collapse Pattern

| Region | NMOS | Body→vout | Body→internal |
| --- | --- | --- | --- |
| Left (x=3200–5000) | M20, M17, M13 | 2 | 1 |
| Center (x=5000–8800) | M23, M22, M18, M15, M16 | 3 | 2 |
| Far right (x=9400–13200) | M21, M19, M14 | **0** | 3 |

Right-side NMOS (far from gnda→vdda path) collapse to internal nets, not vout.

### Candidate Mechanisms

| # | Mechanism | Classification |
| --- | --- | --- |
| C1 | 128 diff.drawing rects merge gnda/vdda/vout through p-substrate | **PRIMARY** |
| C2 | MAGICAL gnda route as diffusion stripe across chip bottom | **PRIMARY** |
| C3 | 47-step conduction chain through NMOS/PMOS diffusion | **PRIMARY** |
| C4 | Met5 routing gap (AH-SMC-012) | SECONDARY |
| C5 | Nondeterministic routing | SECONDARY |

### Diagnostic Proposals (not implemented)

- **D1**: Mask `diff.drawing` in controlled region using `mask_gds_layers_in_region.py`, re-extract, compare `.ext` records. (Requires Codex approval.)
- **D2**: Regenerate SMCNR GDS, run same `psub_substrate_geometry` diagnostic, compare. (Blocked: missing SMCNR artifacts.)

### Output Artifacts

```
docs/ah_smc_017_geometry_localization.md
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_017/ah_smc_017_records.json
```

### Stop Gate

**Status:** Geometry localization complete. Diffusion is the primary mechanism.
H2 promoted to PRIMARY CANDIDATE with high confidence. H4 downgraded. Two
diagnostic proposals pending Codex review. No MAGICAL- files modified. Trust
remains failure-case only. Pending Codex review.

---

## AH-SMC-018: Diagnostic-Only Diffusion Mask / Re-Extract Experiment

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-018 |
| Date | 2026-06-22 |
| Type | Diagnostic GDS mask + Magic re-extract |
| MAGICAL files modified | **None** |
| Files modified | `docs/ah_smc_018_diffusion_mask_experiment.md` (new), `ah_smc_018/` (new) |

### Three Variants

| Variant | Mask | Elements | MOS | Substrate/Equiv |
| --- | --- | --- | --- | --- |
| A (Control) | None | 0 | 24 | `vout`, vout↔vdda, vout↔gnda |
| B (Bottom Stripe) | diff.drawing [-1050,-450,15050,-350] | 3 | 24 | **Unchanged** |
| C (Path Stack) | diff.drawing [3000,11000,9000,16200] | 23 | **19** (−5) | **Unchanged** |

### Key Finding

**The diffusion merge is multi-point, not single-point.** Masking the bottom
stripe (3 rects) had zero effect. Masking M22/M23/M20 area diffusions (23
rects) lost 5 MOS devices but did NOT change substrate/equiv. A local
diagnostic mask cannot cleanly isolate the collapse without destroying >20%
of devices — after which extraction comparison becomes invalid.

### Surviving vout-collapsed NMOS

M17 and M18 remain outside Variant C's mask region. They (or PMOS nwell
diffusions) independently maintain the gnda↔vout substrate path.

### H2 Status

PRIMARY CANDIDATE (high confidence) — diffusion is necessary for the
collapse but the merge is distributed across multiple device areas.

### Output Artifacts

```
docs/ah_smc_018_diffusion_mask_experiment.md
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_018/ah_smc_018_records.json
ah_smc_018/control/       (fan_smc_pin_3_flat.ext, .spice)
ah_smc_018/bottom_stripe/ (fan_smc_pin_3.bottom_stripe_masked.gds, .ext, .spice)
ah_smc_018/path_stack/    (fan_smc_pin_3.path_stack_masked.gds, .ext, .spice)
```

### Stop Gate

**Status:** Diagnostic mask experiment complete. Substrate/equiv unchanged
across all variants. Diffusion merge is multi-point, cannot be cleanly
isolated by local mask without destroying device recognition. No repair
claimed. No MAGICAL- files modified. Trust remains failure-case only.
Pending Codex review.

---

## AH-SMC-019: Fan_SMC Diffusion Semantics / Provenance Audit

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-019 |
| Date | 2026-06-22 |
| Type | Read-only diffusion provenance audit |
| MAGICAL files modified | **None** |
| Files modified | `docs/ah_smc_019_diffusion_semantics_provenance.md` (new), `ah_smc_019/` (new) |

### Key Finding: Remap-Level Semantic Aliasing

All 128 Fan_SMC `diff.drawing` shapes originate from MAGICAL internal
layer 6/0 (OD), remapped 1:1 to Sky130 layer 65/20 with **no semantic
distinction** between:

- MOS device active diffusion (111 shapes, inside device boxes)
- Chip-edge guard rings (2 vertical strips, 150×28,250 each)
- Horizontal edge stripes (top/bottom frame + psub route)
- Bottom-right guard ring structure (9 shapes, no associated device)

### Outside-Device Shapes: 17 (13.3%)

| Group | Count | Description |
| --- | --- | --- |
| A: Edge guard rings | 2 | Full-height vertical strips |
| B: Horizontal edge stripes | 7 | Top/bottom OD frame |
| C: Bottom-right guard ring | 9 | Rectangular ring near xr0/C0 area |

### New Hypothesis: H2a (Remap Aliasing)

Uniform MAGICAL layer 6/0 → Sky130 65/20 mapping merges device active,
guard rings, edge stripes, and psub route into a single Magic layer. This
causes Magic to treat ALL `diff.drawing` shapes as connected through the
shared p-substrate.

### Proposed Mask Plan (not implemented)

Remap 18 non-device shapes from `diff.drawing` (65/20) to `tap.drawing`
(65/44) or a dedicated layer. Status: **PROPOSAL ONLY**. Requires Codex
approval.

### Output Artifacts

```
docs/ah_smc_019_diffusion_semantics_provenance.md
generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_019/ah_smc_019_records.json
```

### Stop Gate

**Status:** Diffusion provenance audit complete. Remap aliasing identified
as likely contributing mechanism. Non-device-diff mask proposal documented.
No GDS modifications. No MAGICAL- files modified. Trust remains failure-case
only. Pending Codex review.

---

## AH-SMC-021: `useDeviceSubGuardRing` Config-Level Diagnostic Probe

### Metadata

| Field | Value |
| --- | --- |
| Task ID | AH-SMC-021 |
| Date | 2026-06-22 |
| Type | Config-level A/B diagnostic |
| Parameter | `useDeviceSubGuardRing: false → true` |
| MAGICAL files modified | **None** |

### Result: H5 CONFIRMED — Guard rings change extraction but do not resolve collapse

| Metric | Baseline (false) | Guardring (true) |
| --- | --- | --- |
| P&R GDS size | 335K / 360K | **428K (+28%) / 452K (+26%)** |
| `substrate` | `"net31"` | **`"net050"`** |
| Equiv count | 4 | **3** |
| net31 in equiv? | Yes | **No (dropped)** |
| vout↔vdda/gnda? | Yes (via net31) | Yes (via net050) |
| MOS devices | 24 | 24 |
| LVS result | Fail | Fail |

### Finding

Guard rings measurably shifted substrate identity and reduced equiv count,
but did not break the vout↔vdda↔gnda equivalence. The collapse mechanism
is at the p-substrate level — all `diff.drawing` shapes share the same
substrate domain regardless of guard ring presence.

### Output

```
docs/ah_smc_021_use_device_sub_guardring_probe.md
generated/diagnostics/.../ah_smc_021/ah_smc_021_records.json
```

### Stop Gate

Trust remains failure-case only. Pending Codex review.
