# Review Queue

Last updated: 2026-06-22

## Current Judgment

Codex should review evidence and conclusions before code or reports are treated
as project facts. Claude can implement extraction and reports, but trust labels
and novelty language require review.

## Pending Reviews

| ID | Owner | Item | Expected evidence | Status |
| --- | --- | --- | --- | --- |
| PM-001 | Claude/Codex | Dataset v0 extractor under `tools/analog_harness/ml/` | Code, focused tests, generated JSONL sample | Implemented, focused tests pass |
| PM-002 | Codex | `docs/parasitic_modeling_dataset_v0.md` | Dataset schema, sample table, trust flags | Implemented |
| PM-003 | Codex | Literature/novelty wording | Survey references and source links | Implemented, needs future expansion |
| PM-004 | Codex | SMCNR PEX fact correction | `pex_summary.md` and raw extracted SPICE | Done |
| PM-005 | Codex | `docs/codex_parasitic_dataset_v0_review.md` | Fresh test output and JSONL audit | Done |
| PM-006 | Codex | `docs/analoggym_opt_data_request.md` | Candidate batch schema and trust boundary | Done |
| PM-007 | Claude/Codex | SMCNR local replay report | R1/R2 DRC/extract/LVS logs under `generated/smcnr_local_replay*/` and `docs/smcnr_local_replay_report.md` | R1/R2 PASS; PEX packaged-summary alignment pending |
| PM-008 | Claude/Codex | AnalogGym-Opt importer smoke test | `tools/analog_harness/ml/analoggym_importer.py`, `smoke_test_analoggym.py`, importer tests | Mock smoke PASS; ready for real small batch |

## Claude Next Task

Next review should check the first real AnalogGym-Opt small batch before any
model training task starts.

## Acceptance Criteria

- Review entries include artifact paths, not only prose.
- Any disagreement between generated output and source artifacts is listed as a
  blocker.
- Trust flags must be traceable to the positive baseline contract or diagnostic
  closure document.

## Forbidden Claims

- Do not mark an item reviewed because it exists.
- Do not accept a generated dataset record without artifact provenance.
- Do not merge model conclusions into the review queue before data extraction
  is verified.
