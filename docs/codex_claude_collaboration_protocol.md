# Codex/Claude Collaboration Protocol

This protocol defines how Codex and Claude Code should collaborate on the
AnalogHarness PEX/LVS diagnostics work. It is a coordination document; it does
not change controller, reward, or closure-level behavior.

## Roles

### Codex

Codex is the technical reviewer and dispatch center.

Responsibilities:

- Maintain the technical route for PEX/LVS diagnostics and trust gating.
- Review evidence before it is promoted into diagnostics, trust decisions, or
  future `EvidencePacket`-style outputs.
- Split work into small Claude Code tasks with clear inputs, outputs, and
  acceptance criteria.
- Review Claude Code outputs, including logs, inventories, scripts, tests, and
  proposed conclusions.
- Decide whether a sample is suitable for reward, post-sim use, training,
  parasitic modeling, or failure-case use only.

Codex should avoid:

- Large controller, reward, GRPO, or closure-level changes before diagnostics
  evidence is reviewed.
- Treating report claims as equivalent to locally auditable artifacts.
- Treating DFCFC2 or Fan_SMC as permanently failing just because current runs
  are blockers.

### Claude Code

Claude Code is the execution worker and data reporter.

Responsibilities:

- Execute small, read-only or tightly scoped tasks assigned by Codex.
- Collect DFCFC2, Fan_SMC, and SMCNR artifacts from approved locations.
- Record exact commands, inspected files, artifact paths, and concise findings.
- Fill shared docs, especially artifact inventories and run reports.
- Return data to Codex for review before any trust-gate promotion.

Claude Code should avoid:

- Editing controller, reward, GRPO, or closure-level logic unless Codex
  explicitly assigns that work.
- Deleting or rewriting old MAGICAL- artifacts.
- Claiming any sample is training-safe without Codex review.

## Shared Files

Use the AnalogHarness repository as the common working surface.

Required shared context:

- `AGENTS.md`
- `AnalogHarness.md`
- `docs/dfcfc2_smc_diagnostics_mapping.md`
- `docs/trust_gate_evidence_contract.md`
- `docs/smcnr_cand0031_evidence_audit.md`
- `docs/diagnostics_module_status.md`
- `docs/superpowers/plans/2026-06-20-pex-lvs-diagnostics-trust-gate.md`
- `docs/claude_code_handoff.md`
- `docs/codex_artifact_inventory_review_checklist.md`
- `docs/codex_artifact_inventory_review.template.md`

Primary Claude output:

- `docs/dfcfc2_smc_artifact_inventory.md`

Primary Codex review output should be a short review note under `docs/` using
`docs/codex_artifact_inventory_review.template.md`, or a direct review response
that names accepted artifacts, weak artifacts, the first negative sample
candidate, and required follow-up.

## Evidence Vocabulary

Every claim must identify its evidence class:

- `report claim`: stated in a report, not yet backed by local artifact review
- `local artifact`: file exists locally and can be inspected
- `curated reproducibility package`: selected artifact package uploaded for
  audit, not necessarily the full original `generated/` tree
- `generated-only reference`: path points to an original generated location
  that may not exist locally
- `backfilled evidence`: later artifact updates a prior unsupported or partial
  evidence packet

Do not collapse these categories into a single "passed" or "failed" claim.

## Trust-Gate Vocabulary

Every candidate-level decision should keep these fields separate:

- `usable_for_reward`
- `usable_for_post_sim`
- `usable_for_training`
- `usable_for_parasitic_modeling`
- `usable_only_as_failure_case`

PEX availability alone is not enough for reward or training. LVS match,
post-layout simulation validity, PVT validity, and evidence scope must be
reviewed separately.

## Current Baseline Strategy

- Treat `smcnr_se_2st_amp/cand_0031` as the positive baseline because the
  curated SMCNR package contains auditable closure and passive evidence.
- Treat DFCFC2 and Fan_SMC/Fan_SMC_Pin_3 as blocker and stress samples while
  they are being repaired.
- Convert old MAGICAL- artifacts into diagnostics only after Codex reviews the
  inventory and selects a small negative fixture.
- Keep the first conversion observation-only: parser fixtures and trust-gate
  tests first, controller integration later.

## Handoff Cycle

1. Codex writes or updates a task in `docs/claude_code_handoff.md`.
2. Claude Code performs the assigned task and records evidence in the requested
   shared file.
3. Codex reviews the shared file using the matching checklist.
4. Codex either accepts the artifact for diagnostics, returns it for more data,
   or creates the next small implementation task.
5. No sample is promoted to training-safe or reward-safe status without this
   review cycle.
