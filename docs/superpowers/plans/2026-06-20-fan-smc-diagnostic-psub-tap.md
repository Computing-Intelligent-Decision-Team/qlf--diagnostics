# Fan_SMC Diagnostic Psubstrate Tap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and evaluate exactly one top-level diagnostic p+ substrate-contact stack tied physically to the existing `gnda` met5 rail in the bounded-C0 `Fan_SMC_Pin_3` candidate.

**Architecture:** A focused binary-GDS tool validates the target cell, anchor rail, and forbidden-layer clearance, then inserts fourteen BOUNDARY elements before the target cell's `ENDSTR` without rewriting original bytes. Synthetic fixtures prove preservation and rejection behavior before one real A/B; Magic/Netgen evidence then feeds an observation-only trust decision without changing Harness control logic.

**Tech Stack:** Python 3 standard library, `unittest`, existing Sky130 GDS inspectors, Magic with Sky130 PDK, Netgen, AnalogHarness diagnostics.

---

## File Map

- Create `tools/sky130_adapter/add_diagnostic_psub_tap_stack.py`: parser, validation, insertion, report, JSON summary.
- Create `tools/sky130_adapter/test_add_diagnostic_psub_tap_stack.py`: synthetic-GDS TDD.
- Create artifacts only under `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/`.
- Modify `docs/dfcfc2_smc_campaign_status.md` and `docs/claude_code_handoff.md`.
- Create `docs/codex_ah_smc_009_review.md`.

## Fixed Contract

Use these constants exactly:

```python
STACK_SPECS = (
    ("tap.drawing", 65, 44, (-150, -150, 150, 150)),
    ("psdm.drawing", 94, 20, (-250, -250, 250, 250)),
    ("licon1.drawing", 66, 44, (-25, -25, 25, 25)),
    ("li1.drawing", 67, 20, (-150, -150, 150, 150)),
    ("mcon.drawing", 67, 44, (-50, -50, 50, 50)),
    ("met1.drawing", 68, 20, (-150, -150, 150, 150)),
    ("via.drawing", 68, 44, (-25, -25, 25, 25)),
    ("met2.drawing", 69, 20, (-150, -150, 150, 150)),
    ("via2.drawing", 69, 44, (-25, -25, 25, 25)),
    ("met3.drawing", 70, 20, (-150, -150, 150, 150)),
    ("via3.drawing", 70, 44, (-25, -25, 25, 25)),
    ("met4.drawing", 71, 20, (-150, -150, 150, 150)),
    ("via4.drawing", 71, 44, (-50, -50, 50, 50)),
    ("met5.drawing", 72, 20, (-150, -150, 150, 150)),
)
FORBIDDEN_LAYERS = {
    (65, 20): "diff.drawing",
    (65, 44): "tap.existing",
    (64, 20): "nwell.drawing",
    (66, 20): "poly.drawing",
}
```

Coordinates are integer GDS DBU. Edge touch is not overlap. Clearance uses the widest proposed bbox, `psdm.drawing`. Existing tap geometry is forbidden so two experiments cannot silently merge.

### Task 1: RED Exact Insertion and Preservation Test

**Files:**
- Create: `tools/sky130_adapter/test_add_diagnostic_psub_tap_stack.py`

- [ ] **Step 1: Create the synthetic fixture and valid-insertion test**

Write this module foundation. It intentionally imports a module that does not exist yet:

```python
#!/usr/bin/env python3
from __future__ import annotations
import json
import struct
import tempfile
import unittest
from pathlib import Path

from add_diagnostic_psub_tap_stack import STACK_SPECS, inject_stack
from inspect_gds_structure import parse_gds

def record(kind: int, dtype: int = 0, payload: bytes = b"") -> bytes:
    return struct.pack(">HBB", len(payload) + 4, kind, dtype) + payload

def int2(kind: int, value: int) -> bytes:
    return record(kind, 2, struct.pack(">h", value))

def ascii_record(kind: int, value: str) -> bytes:
    payload = value.encode("ascii")
    if len(payload) % 2:
        payload += b"\0"
    return record(kind, 6, payload)

def boundary(layer: int, datatype: int, box: tuple[int, int, int, int]) -> bytes:
    x1, y1, x2, y2 = box
    xy = (x1, y1, x1, y2, x2, y2, x2, y1, x1, y1)
    return b"".join((
        record(0x08), int2(0x0D, layer), int2(0x0E, datatype),
        record(0x10, 3, struct.pack(">10l", *xy)), record(0x11),
    ))

def structure(name: str, elements: bytes) -> bytes:
    return record(0x05) + ascii_record(0x06, name) + elements + record(0x07)

def fixture(*extra: bytes, include_rail: bool = True) -> bytes:
    rail = boundary(72, 20, (150, -2050, 650, 11650)) if include_rail else b""
    harmless = boundary(68, 20, (2000, 2000, 2200, 2200))
    return b"".join((
        record(0x00),
        structure("OTHER", boundary(70, 20, (0, 0, 10, 10))),
        structure("fan_smc_pin_3_flat", rail + harmless + b"".join(extra)),
        record(0x04),
    ))

class AddDiagnosticPsubstrateTapStackTest(unittest.TestCase):
    def test_adds_exact_stack_and_preserves_original_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source, output = root / "input.gds", root / "output.gds"
            report, summary_path = root / "report.md", root / "summary.json"
            original = fixture()
            source.write_bytes(original)
            summary = inject_stack(
                input_gds=source, output_gds=output, report=report,
                summary_json=summary_path, cell="fan_smc_pin_3_flat",
                anchor=(400, -1000),
                expected_met5_box=(150, -2050, 650, 11650),
            )
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(summary["added_boundary_count"], 14)
            self.assertEqual(summary["added_text_count"], 0)
            self.assertTrue(summary["original_records_byte_identical"])
            self.assertTrue(summary["original_record_order_preserved"])
            self.assertEqual(summary["stack_count"], 1)
            self.assertEqual(json.loads(summary_path.read_text()), summary)
            cell = parse_gds(output)["fan_smc_pin_3_flat"]
            for name, layer, datatype, relative_box in STACK_SPECS:
                with self.subTest(name=name):
                    expected_count = 2 if (layer, datatype) == (72, 20) else 1
                    self.assertEqual(
                        cell.layer_counts[f"{layer}/{datatype}/BOUNDARY"],
                        expected_count,
                    )
                    self.assertIn({
                        "name": name, "layer": layer, "datatype": datatype,
                        "relative_bbox": list(relative_box),
                    }, summary["stack_spec"])
            self.assertEqual(cell.element_counts.get("TEXT", 0), 0)
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/sky130_adapter
python3 -m unittest test_add_diagnostic_psub_tap_stack.AddDiagnosticPsubstrateTapStackTest.test_adds_exact_stack_and_preserves_original_bytes -v
```

Expected: import-time `ModuleNotFoundError` for `add_diagnostic_psub_tap_stack`. Record the command and failure.

### Task 2: RED Fail-Before-Write Tests

**Files:**
- Modify: `tools/sky130_adapter/test_add_diagnostic_psub_tap_stack.py`

- [ ] **Step 1: Add the rejection helper**

Add inside the test class:

```python
    def assert_rejected(
        self, data: bytes, pattern: str, *, cell: str = "fan_smc_pin_3_flat",
        same_path: bool = False,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "input.gds"
            output = source if same_path else root / "output.gds"
            report, summary = root / "report.md", root / "summary.json"
            source.write_bytes(data)
            with self.assertRaisesRegex(ValueError, pattern):
                inject_stack(
                    input_gds=source, output_gds=output, report=report,
                    summary_json=summary, cell=cell, anchor=(400, -1000),
                    expected_met5_box=(150, -2050, 650, 11650),
                )
            if not same_path:
                self.assertFalse(output.exists())
            self.assertFalse(report.exists())
            self.assertFalse(summary.exists())
```

- [ ] **Step 2: Add every validation case**

```python
    def test_rejects_absent_target_cell(self) -> None:
        self.assert_rejected(fixture(), "target cell.*missing", cell="ABSENT")

    def test_rejects_missing_met5_anchor(self) -> None:
        self.assert_rejected(fixture(include_rail=False), "met5.*anchor")

    def test_rejects_forbidden_overlaps(self) -> None:
        for layer, datatype, label in (
            (66, 20, "poly.drawing"), (64, 20, "nwell.drawing"),
            (65, 20, "diff.drawing"), (65, 44, "tap.existing"),
        ):
            with self.subTest(label=label):
                self.assert_rejected(
                    fixture(boundary(layer, datatype, (300, -1100, 500, -900))),
                    f"forbidden overlap.*{label}",
                )

    def test_allows_edge_touch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source, output = root / "input.gds", root / "output.gds"
            source.write_bytes(fixture(boundary(66, 20, (650, -1250, 800, -750))))
            summary = inject_stack(
                input_gds=source, output_gds=output, report=root / "report.md",
                summary_json=root / "summary.json", cell="fan_smc_pin_3_flat",
                anchor=(400, -1000),
                expected_met5_box=(150, -2050, 650, 11650),
            )
            self.assertEqual(summary["forbidden_overlap_count"], 0)

    def test_rejects_same_input_output(self) -> None:
        self.assert_rejected(fixture(), "input and output.*different", same_path=True)

    def test_rejects_truncated_gds(self) -> None:
        self.assert_rejected(b"\x00\x10\x00\x00bad", "truncated|invalid GDS")
```

- [ ] **Step 3: Confirm RED**

Run `cd tools/sky130_adapter && python3 -m unittest test_add_diagnostic_psub_tap_stack -v`.

Expected: import-time failure only. Fix test syntax if needed, but do not add implementation during this step.

### Task 3: GREEN Minimal GDS Tool

**Files:**
- Create: `tools/sky130_adapter/add_diagnostic_psub_tap_stack.py`

- [ ] **Step 1: Implement strict record parsing**

Define frozen `GdsRecord(raw, record_type, data_type, payload, offset)` and `GdsElement(layer, datatype, bbox)`. Implement `parse_records(data)` to reject: fewer than four header bytes, length below four, odd length, or a record crossing EOF. Implement `scan_target(records, cell)` tracking `BGNSTR/STRNAME/ENDSTR` and `BOUNDARY/LAYER/DATATYPE/XY/ENDEL`; return the exact target `ENDSTR` byte offset and target elements.

Use signed big-endian int32 XY. Require a closed, axis-aligned five-point rectangle. Raise:

```python
raise ValueError(f"target cell is missing: {cell}")
raise ValueError("unsupported non-rectangular BOUNDARY in target cell")
```

- [ ] **Step 2: Implement geometry and ordered validation**

Use:

```python
def parse_box(value: str) -> tuple[int, int, int, int]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("box must contain four comma-separated integers")
    x1, y1, x2, y2 = (int(part) for part in parts)
    if x1 >= x2 or y1 >= y2:
        raise ValueError("box must satisfy x1 < x2 and y1 < y2")
    return x1, y1, x2, y2

def absolute_box(anchor, relative):
    ax, ay = anchor
    x1, y1, x2, y2 = relative
    return ax + x1, ay + y1, ax + x2, ay + y2
def overlaps(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
def contains_point(box, point):
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]
```

Validation order:

1. Resolved input and output paths differ.
2. Input parses completely.
3. Exact cell exists.
4. Anchor is inside `expected_met5_box`.
5. A target-cell `72/20` BOUNDARY contains the anchor and overlaps the proposed met5 patch.
6. Absolute psdm bbox overlaps none of `FORBIDDEN_LAYERS`.

Create no output parent directory before all checks pass.

- [ ] **Step 3: Insert exactly fourteen boundaries**

Implement GDS `BOUNDARY/LAYER/DATATYPE/XY/ENDEL` encoding. Build records in `STACK_SPECS` order and write:

```python
result = source[:endstr_offset] + inserted + source[endstr_offset:]
assert result[:endstr_offset] == source[:endstr_offset]
assert result[endstr_offset + len(inserted):] == source[endstr_offset:]
```

The summary must include: `input_gds`, `output_gds`, `cell`, `anchor`, `expected_gnda_met5_box`, `matched_gnda_met5_boxes`, `stack_spec`, `absolute_rectangles`, `added_boundary_count`, `added_text_count`, `stack_count`, `forbidden_overlap_count`, byte counts, and both preservation booleans.

- [ ] **Step 4: Implement API, report, and CLI**

The public API is named `inject_stack`; it takes keyword-only `Path` arguments
`input_gds`, `output_gds`, `report`, and `summary_json`, string `cell`, integer
pair `anchor`, and four-integer `expected_met5_box`, and returns the exact
dictionary serialized to the summary JSON.

CLI options: `--input-gds --output-gds --report --summary-json --cell --anchor-x --anchor-y --expected-gnda-met5-box`.

Success output:

```text
output_gds=<absolute path>
added_boundary_count=14
preservation_verified=true
```

Markdown includes one row per absolute rectangle and explicitly says no TEXT or pin-purpose geometry was added.

- [ ] **Step 5: Run GREEN**

Run `cd tools/sky130_adapter && python3 -m unittest test_add_diagnostic_psub_tap_stack -v`.

Expected: all seven tests `ok`, final `OK`.

### Task 4: Regression and Scope Check

**Files:**
- Test: the new module and neighboring adapter modules.

- [ ] **Step 1: Run focused regressions**

```bash
cd tools/sky130_adapter
python3 -m unittest \
  test_add_diagnostic_psub_tap_stack \
  test_add_local_power_stripe_to_gds \
  test_inspect_gds_structure \
  test_prepare_lvs_netlists -v
```

Expected: all pass. Existing failure is a stop until proved pre-existing or narrowly fixed.

- [ ] **Step 2: Confirm no control-plane edits**

```bash
git status --short
git diff -- tools/analog_harness/controller.py tools/analog_harness/models.py
```

Expected: controller/models diff empty. Do not commit or push.

### Task 5: Generate the One Real Candidate

**Files:**
- Input: `generated/diagnostics/fan_smc_c0_proxy_94x10/fan_smc_pin_3.pinned_shapes.gds`
- Outputs: `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/`

- [ ] **Step 1: Hash the immutable input**

```bash
mkdir -p generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap
sha256sum generated/diagnostics/fan_smc_c0_proxy_94x10/fan_smc_pin_3.pinned_shapes.gds | tee generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/input.sha256
```

- [ ] **Step 2: Run the approved anchor once**

```bash
python3 tools/sky130_adapter/add_diagnostic_psub_tap_stack.py \
  --input-gds generated/diagnostics/fan_smc_c0_proxy_94x10/fan_smc_pin_3.pinned_shapes.gds \
  --output-gds generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds \
  --report generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/psub_tap_injection.md \
  --summary-json generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/psub_tap_injection.json \
  --cell fan_smc_pin_3_flat --anchor-x 400 --anchor-y -1000 \
  --expected-gnda-met5-box 150,-2050,650,11650
```

Expected: 14 boundaries and preservation true. Do not try another anchor.

- [ ] **Step 3: Independent structure audit**

```bash
python3 tools/sky130_adapter/inspect_gds_structure.py \
  --gds generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds \
  --report generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/gds_structure.md \
  --summary-json generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/gds_structure.json
sha256sum -c generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/input.sha256
```

Expected: parse succeeds, source hash `OK`, one added shape per fixed layer.

### Task 6: Magic DRC and Extraction

**Files:**
- Create `magic_drc.tcl`, `magic_extract.tcl`, raw logs, `.ext`, and `.spice` under the experiment directory.

- [ ] **Step 1: Write deterministic scripts**

`magic_drc.tcl`:

```tcl
gds read fan_smc_pin_3.psub_tap.gds
load fan_smc_pin_3_flat
select top cell
drc euclidean on
drc check
puts "AH_SMC_009_DRC_COUNT [drc count total]"
quit -noprompt
```

`magic_extract.tcl`:

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

- [ ] **Step 2: Run DRC**

```bash
bash -lc 'source ../../scripts/env/magical_sky130_env.sh && cd generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap && magic -dnull -noconsole -rcfile "$SKY130A/libs.tech/magic/sky130A.magicrc" magic_drc.tcl > magic_drc.log 2>&1'
```

Expected: exit zero and one `AH_SMC_009_DRC_COUNT` line. Nonzero DRC remains evidence but forbids trust upgrades.

- [ ] **Step 3: Run extraction**

```bash
bash -lc 'source ../../scripts/env/magical_sky130_env.sh && cd generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap && magic -dnull -noconsole -rcfile "$SKY130A/libs.tech/magic/sky130A.magicrc" magic_extract.tcl > magic_extract.log 2>&1'
```

Expected: exit zero, `fan_smc_pin_3_flat.ext` and `.spice` exist unedited.

- [ ] **Step 4: Capture gate facts**

```bash
grep -nE '^(port|substrate|equiv)|M11|M23' generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext | tee generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/ext_key_records.txt
grep -c '^X.*sky130_fd_pr__[np]fet_01v8' generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.spice | tee generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/mos_count.txt
grep -niE 'unknown layer|unknown datatype|warning|error' generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/magic_extract.log | tee generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/extract_warnings.txt
```

Record exact ports, MOS count, substrate, equivalences, M11/M23 terminals, and warnings. A grep with no matches is not itself a test failure.

### Task 7: Conditional LVS and Trust Decision

**Files:**
- Create prepared netlists/direct Netgen report only if extraction gate passes.
- Create `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/trust_decision.json`.

- [ ] **Step 1: Apply the extraction gate**

Pass only if: MOS count is 24; top ports are nonempty; `vout` and `gnda` remain distinguishable; extracted SPICE parses as a top subcircuit. Record `pass` or `fail`.

On failure, do not run Netgen and use reason `lvs_not_run_extraction_gate_failed`.

- [ ] **Step 2: Only on pass, prepare and run LVS**

```bash
python3 tools/sky130_adapter/prepare_lvs_netlists.py \
  --source generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.sp \
  --extracted generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.spice \
  --out-dir generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared \
  --report generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/lvs_preparation_report.md \
  --prefix fan_smc_pin_3
```

Create `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/run_lvs.tcl` with:

```tcl
set root /home/qlf/IOT/references/AnalogHarness/generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared
set setup [file join $::env(SKY130A) libs.tech netgen sky130A_setup.tcl]
lvs [list [file join $root fan_smc_pin_3_source.connectivity.spice] fan_smc_pin_3] [list [file join $root fan_smc_pin_3_extracted.connectivity.spice] fan_smc_pin_3_flat] $setup [file join $root netgen_lvs_report.log]
quit
```

Then run:

```bash
bash -lc 'source ../../scripts/env/magical_sky130_env.sh && netgen -batch source generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/run_lvs.tcl > generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/netgen_stdout.log 2>&1'
```

Set LVS pass only when `netgen_lvs_report.log` states a unique circuit match. Equal device counts are insufficient.

- [ ] **Step 3: Write conservative trust JSON**

```json
{
  "candidate_id": "AH-SMC-009",
  "circuit": "Fan_SMC_Pin_3",
  "experiment_scope": "single_top_level_diagnostic_psub_tap",
  "drc_clean": false,
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
  "reasons": []
}
```

Only direct logs may alter `drc_clean` or `lvs_match`. All usability flags remain exactly shown because C0 equivalence and PEX/post-sim/PVT are absent. Reasons may use only: `lvs_not_matched`, `lvs_not_run_extraction_gate_failed`, `drc_not_clean`, `pex_missing`, `post_sim_invalid`, `pvt_invalid`, `scope_not_full_passive_lvs`.

### Task 8: Review, Documentation, Stop Gate

**Files:**
- Modify `docs/dfcfc2_smc_campaign_status.md`, `docs/claude_code_handoff.md`, `docs/claude_code_run_report.md`.
- Create `docs/codex_ah_smc_009_review.md`.

- [ ] **Step 1: Claude worker report**

Record exact commands/exit codes, hashes, injection, DRC, extracted ports/MOS/substrate/equivalence/M11/M23, extraction gate, LVS result or non-run reason, trust JSON, and changed files. Separate observations from inference.

- [ ] **Step 2: Independent Codex review**

Use exactly:

```markdown
# Codex AH-SMC-009 Review
## Scope And Baseline
## Structural Preservation
## DRC Evidence
## Extraction Evidence
## LVS Evidence
## Hypothesis Assessment
## Trust Decision
## Stop-Gate Decision
```

Choose one assessment: `supported`, `partially_supported`, `not_supported`, or `inconclusive`. Cite raw artifact paths. Never conflate Fan_SMC with the SMCNR/cand_0031 positive baseline.

- [ ] **Step 3: Update campaign/handoff**

Set AH-SMC-009 to the reviewed outcome and link the Codex review. State that no second tap, primitive/C0 edit, post-layout/PVT run, controller/reward change is authorized.

- [ ] **Step 4: Final verification**

```bash
cd tools/sky130_adapter && python3 -m unittest test_add_diagnostic_psub_tap_stack -v
cd ../..
python3 -m unittest discover -s tools/analog_harness/diagnostics -p 'test_*.py' -v
python3 -m json.tool generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/psub_tap_injection.json >/dev/null
python3 -m json.tool generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/trust_decision.json >/dev/null
git diff --check
git status --short
```

Expected: tests pass, current diagnostics pass count is preserved, JSON validates, diff check is silent. Report unrelated dirty files separately. Do not commit or push.

## Execution Boundary

This plan authorizes one diagnostic candidate only. It does not authorize a second anchor, multiple taps, NMOS primitive changes, C0 changes, PEX/post-layout/PVT work, DFCFC2 execution, Harness control changes, commits, or pushes. A later experiment requires a fresh reviewed specification.
