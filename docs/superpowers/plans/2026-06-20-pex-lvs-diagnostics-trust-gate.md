# PEX/LVS Diagnostics Trust Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an observation-only PEX/LVS diagnostics and sample trust gate layer to AnalogHarness.

**Architecture:** Implement small pure-Python diagnostics modules under `tools/analog_harness/diagnostics/` that parse existing artifacts and produce structured JSON-compatible dictionaries. Keep the first integration outside controller reward decisions; the diagnostics should be callable by tests and later wired into `LayoutVerificationAdapter` or the controller.

**Tech Stack:** Python standard library, `unittest`, existing AnalogHarness `EvidencePacket` schema.

---

## File Structure

- Create `tools/analog_harness/diagnostics/__init__.py`
  - Expose the diagnostics package without side effects.
- Create `tools/analog_harness/diagnostics/pex_structuring.py`
  - Parse Magic extracted SPICE/parasitic summaries into capacitor counts,
    total capacitance, and per-node capacitance.
- Create `tools/analog_harness/diagnostics/lvs_failure_taxonomy.py`
  - Parse Netgen/LVS summary text and classify failure categories.
- Create `tools/analog_harness/diagnostics/artifact_verifier.py`
  - Check whether artifact paths are present, curated, generated-only, or not
    portable.
- Create `tools/analog_harness/diagnostics/sample_trust_gate.py`
  - Combine DRC/LVS/PEX/post/PVT/passive evidence into a trust decision.
- Create `tools/analog_harness/tests/test_diagnostics_trust_gate.py`
  - Unit tests for the pure diagnostics functions using small inline fixtures.

### Task 1: Package Skeleton

**Files:**
- Create: `tools/analog_harness/diagnostics/__init__.py`
- Test: `tools/analog_harness/tests/test_diagnostics_trust_gate.py`

- [ ] **Step 1: Write the import test**

```python
import unittest


class DiagnosticsPackageTest(unittest.TestCase):
    def test_imports_diagnostics_package(self):
        import tools.analog_harness.diagnostics as diagnostics

        self.assertTrue(hasattr(diagnostics, "__all__"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Expected: FAIL with `ModuleNotFoundError` for
`tools.analog_harness.diagnostics`.

- [ ] **Step 3: Create minimal package**

```python
"""Observation-only diagnostics for AnalogHarness verification artifacts."""

__all__ = [
    "artifact_verifier",
    "lvs_failure_taxonomy",
    "pex_structuring",
    "sample_trust_gate",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Expected: PASS for `test_imports_diagnostics_package`.

### Task 2: LVS Failure Taxonomy

**Files:**
- Create: `tools/analog_harness/diagnostics/lvs_failure_taxonomy.py`
- Modify: `tools/analog_harness/tests/test_diagnostics_trust_gate.py`

- [ ] **Step 1: Add tests for pass and mismatch classification**

```python
from tools.analog_harness.diagnostics.lvs_failure_taxonomy import classify_lvs_summary


class LvsFailureTaxonomyTest(unittest.TestCase):
    def test_classifies_clean_lvs_summary(self):
        text = """
        LVS status: **PASS**
        Device mismatch detected: no
        Net mismatch detected: no
        Property mismatch detected: no
        """

        diagnosis = classify_lvs_summary(text)

        self.assertTrue(diagnosis["lvs_match"])
        self.assertEqual(diagnosis["status"], "pass")
        self.assertEqual(diagnosis["failure_categories"], [])

    def test_classifies_net_and_device_mismatch(self):
        text = """
        LVS status: **FAIL**
        Device mismatch detected: yes
        Net mismatch detected: yes
        Property mismatch detected: no
        """

        diagnosis = classify_lvs_summary(text)

        self.assertFalse(diagnosis["lvs_match"])
        self.assertEqual(diagnosis["status"], "fail")
        self.assertIn("device_mismatch", diagnosis["failure_categories"])
        self.assertIn("net_mismatch", diagnosis["failure_categories"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Expected: FAIL with missing `lvs_failure_taxonomy`.

- [ ] **Step 3: Implement classifier**

```python
from __future__ import annotations


def classify_lvs_summary(text: str) -> dict:
    lowered = text.lower()
    status = "pass" if "lvs status: **pass**" in lowered else "fail"
    categories = []
    if "device mismatch detected: yes" in lowered:
        categories.append("device_mismatch")
    if "net mismatch detected: yes" in lowered:
        categories.append("net_mismatch")
    if "property mismatch detected: yes" in lowered:
        categories.append("property_mismatch")
    if "power" in lowered and "short" in lowered:
        categories.append("power_domain_short")
    return {
        "status": status,
        "lvs_match": status == "pass" and not categories,
        "failure_categories": categories,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Expected: PASS for LVS taxonomy tests.

### Task 3: Sample Trust Gate

**Files:**
- Create: `tools/analog_harness/diagnostics/sample_trust_gate.py`
- Modify: `tools/analog_harness/tests/test_diagnostics_trust_gate.py`

- [ ] **Step 1: Add tests for positive and failure cases**

```python
from tools.analog_harness.diagnostics.sample_trust_gate import decide_sample_trust


class SampleTrustGateTest(unittest.TestCase):
    def test_positive_full_scope_sample_is_training_usable(self):
        decision = decide_sample_trust(
            {
                "candidate_id": "cand_0031",
                "drc_clean": True,
                "lvs_match": True,
                "pex_available": True,
                "post_sim_valid": True,
                "pvt_valid": True,
                "evidence_scope": "full_passive_inclusive_gds_lvs",
            }
        )

        self.assertTrue(decision["usable_for_reward"])
        self.assertTrue(decision["usable_for_post_sim"])
        self.assertTrue(decision["usable_for_training"])
        self.assertTrue(decision["usable_for_parasitic_modeling"])
        self.assertFalse(decision["usable_only_as_failure_case"])

    def test_lvs_failure_is_failure_case_not_training_sample(self):
        decision = decide_sample_trust(
            {
                "candidate_id": "dfcfc2_probe",
                "drc_clean": True,
                "lvs_match": False,
                "pex_available": True,
                "post_sim_valid": False,
                "pvt_valid": False,
                "evidence_scope": "mos_only_projection",
            }
        )

        self.assertFalse(decision["usable_for_reward"])
        self.assertFalse(decision["usable_for_post_sim"])
        self.assertFalse(decision["usable_for_training"])
        self.assertTrue(decision["usable_for_parasitic_modeling"])
        self.assertTrue(decision["usable_only_as_failure_case"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Expected: FAIL with missing `sample_trust_gate`.

- [ ] **Step 3: Implement trust gate**

```python
from __future__ import annotations


def decide_sample_trust(evidence: dict) -> dict:
    drc_clean = bool(evidence.get("drc_clean"))
    lvs_match = bool(evidence.get("lvs_match"))
    pex_available = bool(evidence.get("pex_available"))
    post_sim_valid = bool(evidence.get("post_sim_valid"))
    pvt_valid = bool(evidence.get("pvt_valid"))
    scope = evidence.get("evidence_scope") or "unknown"

    usable_for_post_sim = drc_clean and lvs_match and pex_available
    usable_for_training = (
        usable_for_post_sim
        and post_sim_valid
        and pvt_valid
        and scope == "full_passive_inclusive_gds_lvs"
    )

    return {
        "candidate_id": evidence.get("candidate_id"),
        "evidence_scope": scope,
        "usable_for_reward": usable_for_post_sim and post_sim_valid,
        "usable_for_post_sim": usable_for_post_sim,
        "usable_for_training": usable_for_training,
        "usable_for_parasitic_modeling": drc_clean and pex_available,
        "usable_only_as_failure_case": not usable_for_training,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Expected: PASS for trust gate tests.

### Task 4: Artifact Verifier

**Files:**
- Create: `tools/analog_harness/diagnostics/artifact_verifier.py`
- Modify: `tools/analog_harness/tests/test_diagnostics_trust_gate.py`

- [ ] **Step 1: Add tests for local and generated-only paths**

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.analog_harness.diagnostics.artifact_verifier import verify_artifact_path


class ArtifactVerifierTest(unittest.TestCase):
    def test_existing_local_path_is_present(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            path.write_text("{}", encoding="utf-8")

            report = verify_artifact_path(str(path), repo_root=Path(tmp))

            self.assertEqual(report["status"], "present")
            self.assertTrue(report["portable"])

    def test_generated_path_missing_is_generated_only(self):
        report = verify_artifact_path(
            "generated/analog_harness/smcnr/cand_0001/magic.log",
            repo_root=Path("."),
        )

        self.assertEqual(report["status"], "generated_only_reference")
        self.assertFalse(report["portable"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Expected: FAIL with missing `artifact_verifier`.

- [ ] **Step 3: Implement path verifier**

```python
from __future__ import annotations

from pathlib import Path


def verify_artifact_path(path_text: str, repo_root: Path | None = None) -> dict:
    repo_root = repo_root or Path.cwd()
    normalized = path_text.replace("\\", "/")
    is_absolute_or_windows = Path(path_text).is_absolute() or ":" in path_text[:3]

    path = Path(path_text)
    if path.exists():
        return {"path": path_text, "status": "present", "portable": not is_absolute_or_windows}

    repo_path = repo_root / normalized
    if repo_path.exists():
        return {"path": path_text, "status": "present", "portable": not is_absolute_or_windows}

    if normalized.startswith("generated/"):
        return {"path": path_text, "status": "generated_only_reference", "portable": False}

    return {"path": path_text, "status": "missing", "portable": False}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Expected: PASS for artifact verifier tests.

### Task 5: PEX Structuring

**Files:**
- Create: `tools/analog_harness/diagnostics/pex_structuring.py`
- Modify: `tools/analog_harness/tests/test_diagnostics_trust_gate.py`

- [ ] **Step 1: Add test for simple capacitor parsing**

```python
from tools.analog_harness.diagnostics.pex_structuring import summarize_pex_caps


class PexStructuringTest(unittest.TestCase):
    def test_summarizes_simple_capacitors_in_ff(self):
        spice = """
        C0 vout gnda 1.5f
        C1 vdda gnda 2.0f
        R0 vout net1 10
        """

        summary = summarize_pex_caps(spice)

        self.assertEqual(summary["pex_caps"], 2)
        self.assertAlmostEqual(summary["pex_total_cap_ff"], 3.5)
        self.assertAlmostEqual(summary["per_node_cap_ff"]["vout"], 1.5)
        self.assertAlmostEqual(summary["per_node_cap_ff"]["gnda"], 3.5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Expected: FAIL with missing `pex_structuring`.

- [ ] **Step 3: Implement PEX summarizer**

```python
from __future__ import annotations


def _cap_to_ff(value: str) -> float:
    text = value.strip().lower()
    if text.endswith("ff"):
        return float(text[:-2])
    if text.endswith("f"):
        return float(text[:-1])
    if text.endswith("p"):
        return float(text[:-1]) * 1000.0
    return float(text) * 1e15


def summarize_pex_caps(spice_text: str) -> dict:
    per_node = {}
    total = 0.0
    count = 0
    for raw_line in spice_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("*") or not line[0].lower() == "c":
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        node_a, node_b, value = parts[1], parts[2], parts[3]
        cap_ff = _cap_to_ff(value)
        count += 1
        total += cap_ff
        per_node[node_a] = per_node.get(node_a, 0.0) + cap_ff
        per_node[node_b] = per_node.get(node_b, 0.0) + cap_ff
    return {
        "pex_caps": count,
        "pex_total_cap_ff": total,
        "per_node_cap_ff": per_node,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Expected: PASS for all diagnostics tests.

### Task 6: Baseline Regression

**Files:**
- No new files.

- [ ] **Step 1: Run existing AnalogHarness tests**

Run:

```bash
python3 -m unittest discover -s tools/analog_harness/tests -v
```

Expected: Existing suite result recorded. If unrelated pre-existing failures
remain, document exact failing tests and do not claim the full suite passes.

- [ ] **Step 2: Run focused diagnostics tests**

Run:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Expected: diagnostics tests pass.

## Self-Review

- Spec coverage: The plan covers mapping old MAGICAL- artifacts into
  AnalogHarness diagnostics, keeps first integration observation-only, and
  preserves evidence scope separation.
- Placeholder scan: No TODO/TBD placeholders are used in implementation steps.
- Type consistency: All planned functions accept plain strings/dicts/paths and
  return JSON-compatible dictionaries.
