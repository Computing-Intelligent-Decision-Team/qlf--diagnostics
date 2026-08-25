# AnalogHarness Parasitic Export Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and package a reusable Codex skill that exports only physically trustworthy AnalogHarness parasitic-label candidates.

**Architecture:** A concise `SKILL.md` directs Codex to a deterministic, standard-library Python exporter. The exporter discovers `state.json` candidates, evaluates an evidence-based trust contract, copies trusted candidate trees, emits manifests/checksums, and creates a reproducible tar archive.

**Tech Stack:** Python 3 standard library, `unittest`, Codex Agent Skills format, POSIX tar/gzip.

**Spec:** `docs/superpowers/specs/2026-08-25-analog-harness-parasitic-export-skill-design.md`

## Global Constraints

- Source experiment directories are read-only.
- Trusted labels require lineage, DRC PASS, connectivity LVS PASS, and parseable non-empty raw PEX.
- PM, reward, pre-layout simulation, PVT, and post-layout performance never gate trust.
- Unknown evidence rejects the candidate; it never defaults to PASS.
- No third-party Python dependency is permitted.

---

### Task 1: Workflow and behavioral baseline

**Files:**
- Create: `agent_workflow/workstreams/2026-08-25_analog_harness_parasitic_export_skill/idea.md`
- Create: `agent_workflow/workstreams/2026-08-25_analog_harness_parasitic_export_skill/tasks.md`
- Create: `agent_workflow/workstreams/2026-08-25_analog_harness_parasitic_export_skill/execution-log.md`

**Interfaces:**
- Consumes: approved design and no-skill subagent response.
- Produces: traceable DAG and documented baseline omissions.

- [ ] Record the baseline response and the missing DRC/LVS/lineage/PEX trust gate.
- [ ] Verify: `test -f agent_workflow/workstreams/2026-08-25_analog_harness_parasitic_export_skill/tasks.md`.

### Task 2: Exporter RED tests and implementation

**Files:**
- Create: `references/codex-skills/analog-harness-parasitic-export/tests/test_export_parasitics.py`
- Create: `references/codex-skills/analog-harness-parasitic-export/scripts/export_parasitics.py`

**Interfaces:**
- Consumes: candidate roots containing `state.json` and artifact files.
- Produces: `evaluate_candidate(path, since, until)` and CLI archive output.

- [ ] Write fixtures for trusted, DRC-failed, LVS-failed, missing-lineage, missing-PEX, and performance-failed candidates.
- [ ] Run `python3 -m unittest discover -s references/codex-skills/analog-harness-parasitic-export/tests -v`; expect import/file failure.
- [ ] Implement evidence parsing, raw PEX validation, manifests, copy, hashes, duplicates, and tar creation.
- [ ] Re-run the same command; expect all tests to pass.

### Task 3: Skill instructions and metadata

**Files:**
- Create: `references/codex-skills/analog-harness-parasitic-export/SKILL.md`
- Create: `references/codex-skills/analog-harness-parasitic-export/agents/openai.yaml`
- Create: `references/codex-skills/analog-harness-parasitic-export/references/trust-contract.md`

**Interfaces:**
- Consumes: exporter CLI and design contract.
- Produces: discoverable `$analog-harness-parasitic-export` workflow.

- [ ] Initialize the skill structure with the bundled skill initializer.
- [ ] Replace scaffold content with minimal invocation, preflight, execution, validation, and handoff instructions.
- [ ] Validate with `quick_validate.py` and a fresh forward-testing subagent.

### Task 4: Package and end-to-end verification

**Files:**
- Create: `references/codex-skills/dist/analog-harness-parasitic-export.tar.gz`

**Interfaces:**
- Consumes: validated skill directory.
- Produces: portable installation archive with SHA-256.

- [ ] Run unit tests and syntax compilation.
- [ ] Run exporter on a synthetic mixed-status root and inspect manifest counts.
- [ ] Package only the skill directory and list archive contents.
- [ ] Run `quick_validate.py` on both source and extracted package.
- [ ] Run `git diff --check` and record exact outputs in the execution log.
