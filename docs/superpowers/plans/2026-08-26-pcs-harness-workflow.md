# PCS-Harness Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a live-only PCS-Harness workflow application that accepts an OTA netlist, runs the verified `ota_core` L0–L6 closure experiment, and visualizes real Agent, GRPO, layout, DRC/LVS/PEX, simulation, PVT, and timing evidence for screen recording.

**Architecture:** Add a small event/timing/orchestration layer to PCS-Harness, then expose its append-only JSONL stream through a standalone FastAPI service. A separate React/Vite application consumes SSE and derives all UI state from versioned events. Geometry and parasitic overlays are generated from real GDS, Magic `.ext`, and raw PEX artifacts; no offline demo player or preset result path is permitted.

**Tech Stack:** Python 3.11+, existing PCS-Harness `unittest` suite, FastAPI/Uvicorn, React 18, TypeScript, Vite 6, Vitest, Testing Library, Recharts, SVG/Canvas.

**Spec:** `docs/superpowers/specs/2026-08-26-pcs-harness-workflow-design.md`

## Global Constraints

- Develop PCS-Harness changes in an isolated worktree created from commit `be2937eb180c377dd8b918453d1ae96835769ef6`; do not edit the dirty source checkout at `references/pcs-harness-align-origin-main-20260815`.
- Build the web application only under `apps/pcs-harness-workflow`; do not change `apps/analog-circuit-platform`.
- Use a fresh run root under `generated/analog_harness/ota_core_grpo_demo_20260826`; never overwrite historical candidates.
- Fix `bias_voltage_v=0.8`, all MOS `L`, and all MOS `multi`. Only the six approved `W/NF` variables may change.
- Events are appended to JSONL before SSE publication. The browser never fabricates results or artificial stage delays.
- The Agent may return only a closed, validated orchestration decision. It may not emit sizing, netlist edits, coordinates, or code patches.
- A candidate is successful only when real evidence satisfies the contracts in the design spec. No deterministic “successful demo” fallback is allowed.
- After every task: run its verification command, update `agent_workflow/workstreams/2026-08-26_pcs_harness_workflow/tasks.md`, append `execution-log.md`, and commit only that task's files.

## File Map

### PCS-Harness isolated worktree

- Create: `tools/analog_harness/workflow_events.py`
- Create: `tools/analog_harness/workflow_timing.py`
- Create: `tools/analog_harness/workflow_runner.py`
- Create: `tools/analog_harness/workflow_agent.py`
- Create: `tools/analog_harness/workflow_boundary_scan.py`
- Create: `tools/analog_harness/workflow_visualization.py`
- Create: `tools/analog_harness/configs/ota_core_workflow_demo.yaml`
- Modify: `tools/analog_harness/controller.py`
- Modify: `tools/analog_harness/layout.py`
- Modify: `tools/analog_harness/orchestration.py`
- Modify: `tools/analog_harness/cli.py`
- Create tests: `tools/analog_harness/tests/test_workflow_*.py`

### Standalone application

- Create: `apps/pcs-harness-workflow/backend/app.py`
- Create: `apps/pcs-harness-workflow/backend/run_service.py`
- Create: `apps/pcs-harness-workflow/backend/requirements.txt`
- Create: `apps/pcs-harness-workflow/src/contracts/events.ts`
- Create: `apps/pcs-harness-workflow/src/state/workflowReducer.ts`
- Create: `apps/pcs-harness-workflow/src/api/liveEvents.ts`
- Create: `apps/pcs-harness-workflow/src/components/*`
- Create: `apps/pcs-harness-workflow/src/App.tsx`
- Create: `apps/pcs-harness-workflow/src/styles.css`
- Create: `apps/pcs-harness-workflow/src/**/*.test.ts(x)`
- Create: `apps/pcs-harness-workflow/scripts/start-recording-demo.sh`
- Create: `apps/pcs-harness-workflow/package.json`, Vite/TypeScript/Vitest configuration

---

## Task 1: Create the isolated implementation worktree and prove the baseline

**Files:**

- Create: an isolated PCS-Harness worktree outside the dirty source checkout
- Modify: `agent_workflow/workstreams/2026-08-26_pcs_harness_workflow/execution-log.md`

- [ ] Record the dirty source checkout status and verify the pinned commit exists.

```bash
git -C references/pcs-harness-align-origin-main-20260815 status --short
git -C references/pcs-harness-align-origin-main-20260815 cat-file -e be2937eb180c377dd8b918453d1ae96835769ef6^{commit}
```

Expected: the first command shows existing user changes; the second exits 0.

- [ ] Load `superpowers:using-git-worktrees`, choose a collision-free worktree directory, and create branch `feat/pcs-harness-workflow` from the pinned commit.

- [ ] Run the narrow baseline suites in the isolated worktree.

```bash
python -m unittest \
  tools.analog_harness.tests.test_orchestration \
  tools.analog_harness.tests.test_native_grpo \
  tools.analog_harness.tests.test_design_init_ota
```

Expected: all tests pass before implementation.

- [ ] Commit the workstream record in the root repository.

```bash
git add agent_workflow/workstreams/2026-08-26_pcs_harness_workflow
git commit -m "chore: start isolated PCS workflow implementation"
```

## Task 2: Add the append-only event and monotonic timing contracts

**Files:**

- Create: `tools/analog_harness/workflow_events.py`
- Create: `tools/analog_harness/workflow_timing.py`
- Create: `tools/analog_harness/tests/test_workflow_events.py`
- Create: `tools/analog_harness/tests/test_workflow_timing.py`

- [ ] Write failing tests for schema validation, strictly increasing sequence numbers, write-before-publish ordering, JSONL recovery from a sequence, and nested monotonic timings.

```python
def test_event_is_durable_before_subscriber_observes_it(self):
    emitter.emit(event_type="stage.started", stage="pre_sim", payload={})
    self.assertEqual(json.loads(events_path.read_text().splitlines()[0])["sequence"], 1)
    self.assertEqual(subscriber.events[0]["sequence"], 1)

def test_recovery_returns_only_events_after_last_sequence(self):
    self.assertEqual([e["sequence"] for e in store.after(2)], [3, 4])
```

- [ ] Run RED.

```bash
python -m unittest tools.analog_harness.tests.test_workflow_events tools.analog_harness.tests.test_workflow_timing
```

Expected: import failures for the new modules.

- [ ] Implement immutable `WorkflowEvent`, `EventStore`, `EventEmitter`, and `StageTimer`. Use `time.perf_counter_ns()` for duration and UTC ISO-8601 for timestamps.

```python
@dataclass(frozen=True)
class WorkflowEvent:
    schema_version: str
    run_id: str
    source: str
    event_type: str
    sequence: int
    occurred_at: str
    elapsed_ms: float
    payload: dict[str, Any]
    candidate_id: str | None = None
    stage: str | None = None
    artifact_refs: tuple[dict[str, Any], ...] = ()
```

- [ ] Add atomic sequence allocation under a lock, flush and `fsync` before notifying subscribers, and export `stage_timing.json`, `.csv`, and `.md`.

- [ ] Run GREEN and commit.

```bash
python -m unittest tools.analog_harness.tests.test_workflow_events tools.analog_harness.tests.test_workflow_timing
git add tools/analog_harness/workflow_events.py tools/analog_harness/workflow_timing.py tools/analog_harness/tests/test_workflow_events.py tools/analog_harness/tests/test_workflow_timing.py
git commit -m "feat: add PCS workflow event and timing contracts"
```

## Task 3: Instrument L0–L6 and physical sub-stages without changing closure semantics

**Files:**

- Modify: `tools/analog_harness/controller.py`
- Modify: `tools/analog_harness/layout.py`
- Create: `tools/analog_harness/tests/test_workflow_instrumentation.py`

- [ ] Write a failing controller test using fake compiler/simulator/layout adapters. Assert ordered events for L0, L1, L2, L3, DRC, LVS, PEX, L5, L6 and that L3 is labelled `layout_checkpoint`, not a fabricated closure level.

- [ ] Run RED.

```bash
python -m unittest tools.analog_harness.tests.test_workflow_instrumentation
```

- [ ] Add an optional `EventEmitter` to `HarnessController` and `LayoutVerificationAdapter`; wrap existing operations in timers without changing their return values.

```python
with self.timing.stage("L1", candidate_id=candidate_id):
    pre = self.simulator.evaluate_pre_layout(compiled, skip_sim=skip_sim)
self.events.completed("pre_sim", candidate_id, evidence=pre)
```

- [ ] Emit artifact references only after the files exist and include SHA-256, size, and relative path. Preserve the current L2→L4 formal closure behavior.

- [ ] Run the new test plus controller/layout regression tests and commit.

```bash
python -m unittest \
  tools.analog_harness.tests.test_workflow_instrumentation \
  tools.analog_harness.tests.test_layout_optimizer_state \
  tools.analog_harness.tests.test_contracts_state
git commit -am "feat: instrument PCS closure stages"
```

## Task 4: Add the restricted live Agent decision bridge and dispatcher

**Files:**

- Create: `tools/analog_harness/workflow_agent.py`
- Modify: `tools/analog_harness/orchestration.py`
- Create: `tools/analog_harness/tests/test_workflow_agent.py`

- [ ] Write failing tests for JSON-over-stdin provider execution, timeout/non-zero exit, invalid JSON, forbidden decision fields, stale report hashes, and action dispatch. Assert raw provider output and the validated decision are separate artifacts.

- [ ] Run RED.

```bash
python -m unittest tools.analog_harness.tests.test_workflow_agent
```

- [ ] Implement a fail-closed `SubprocessDecisionProvider(command, timeout_s)` and `DecisionDispatcher`. The provider receives only `DiagnosticReport.to_dict()` and must return the existing closed decision schema.

```python
dispatch = {
    "run_grpo": runner.run_grpo,
    "run_layout_repair": runner.run_layout_repair,
    "diagnose_lvs": runner.diagnose_lvs,
    "repair_extraction": runner.repair_extraction,
    "accept_candidate": runner.accept_candidate,
    "quarantine_candidate": runner.quarantine_candidate,
    "stop": runner.stop,
}
```

- [ ] Emit only `observation_summary`, `failure_owner`, `action`, `reason_code`, and concise `rationale` to the UI. Do not retain or expose private chain-of-thought.

- [ ] Run GREEN, existing orchestration tests, and commit.

```bash
python -m unittest tools.analog_harness.tests.test_workflow_agent tools.analog_harness.tests.test_orchestration
git add tools/analog_harness/workflow_agent.py tools/analog_harness/orchestration.py tools/analog_harness/tests/test_workflow_agent.py
git commit -m "feat: dispatch validated Agent decisions"
```

## Task 5: Freeze the OTA demo profile and prove GRPO sizing provenance

**Files:**

- Create: `tools/analog_harness/configs/ota_core_workflow_demo.yaml`
- Create: `tools/analog_harness/tests/test_ota_workflow_demo_config.py`
- Modify: `tools/analog_harness/optimizer.py`
- Modify: `tools/analog_harness/native_grpo.py`

- [ ] Write failing tests asserting the exact mutable set is `{input_pair_w, input_pair_nf, load_pmos_w, load_pmos_nf, tail_nmos_w, tail_nmos_nf}` and that bias, L, and multi remain bit-for-bit equal to the boundary candidate.

- [ ] Add provenance assertions: every proposed candidate records backend, policy checkpoint hash, group/sample id, requested action, legalized action, old log probability, reward, and policy-update result. Reject configured backends that silently fall back to random/deterministic proposals.

- [ ] Run RED.

```bash
python -m unittest tools.analog_harness.tests.test_ota_workflow_demo_config
```

- [ ] Create the derived config with `run_pre_layout_pvt: true`, fixed seed, group size 4, target 2 groups, max 3 groups, and the GBW/gain/phase-margin/power contract from the spec.

- [ ] Implement the provenance gate and run GREEN plus native-GRPO regression tests.

```bash
python -m unittest \
  tools.analog_harness.tests.test_ota_workflow_demo_config \
  tools.analog_harness.tests.test_native_grpo \
  tools.analog_harness.tests.test_grpo_trusted_backend
```

- [ ] Commit.

```bash
git add tools/analog_harness/configs/ota_core_workflow_demo.yaml tools/analog_harness/optimizer.py tools/analog_harness/native_grpo.py tools/analog_harness/tests/test_ota_workflow_demo_config.py
git commit -m "feat: freeze OTA physical GRPO action space"
```

## Task 6: Implement deterministic boundary scanning and selection

**Files:**

- Create: `tools/analog_harness/workflow_boundary_scan.py`
- Modify: `tools/analog_harness/cli.py`
- Create: `tools/analog_harness/tests/test_workflow_boundary_scan.py`

- [ ] Write failing tests for deterministic 32-candidate generation, pre-layout filtering, 6–8 candidate physical shortlist, trust-gate rejection, and the 4.0–4.9 MHz post-PEX selection preference.

- [ ] Run RED.

```bash
python -m unittest tools.analog_harness.tests.test_workflow_boundary_scan
```

- [ ] Implement pure candidate generation and selection functions before wiring EDA execution.

```python
def boundary_rank(row: ScanRow) -> tuple[int, float, str]:
    preferred = 0 if 4.0e6 <= row.post_gbw_hz <= 4.9e6 else 1
    return preferred, abs(row.post_gbw_hz - 4.7e6), row.candidate_id
```

- [ ] Add CLI `workflow-boundary-scan --config ... --run-root ... --seed ...`, producing `boundary_scan/selection.json` with input/config/environment hashes and all rejection reasons.

- [ ] Run GREEN and commit without launching the costly campaign yet.

```bash
python -m unittest tools.analog_harness.tests.test_workflow_boundary_scan
git add tools/analog_harness/workflow_boundary_scan.py tools/analog_harness/cli.py tools/analog_harness/tests/test_workflow_boundary_scan.py
git commit -m "feat: add reproducible OTA boundary scan"
```

## Task 7: Generate truthful layout, DRC, and net-anchored PEX visualization data

**Files:**

- Create: `tools/analog_harness/workflow_visualization.py`
- Create: `tools/analog_harness/tests/test_workflow_visualization.py`

- [ ] Build small test fixtures for a GDS checkpoint set, Magic `.ext`, raw PEX SPICE, and DRC markers. Write failing tests for a shared viewBox, layer preservation, top-10 plus VOUT parasitics, original netlist-line references, and logarithmic cap scaling.

- [ ] Run RED.

```bash
python -m unittest tools.analog_harness.tests.test_workflow_visualization
```

- [ ] Implement GDS projection using the same dependency/environment that reads MAGICAL output. Export normalized polygons, paths, labels, layers, and one shared coordinate transform for floorplan/place/route/final.

- [ ] Parse `.ext` representative node coordinates and join them to raw PEX capacitances by normalized net identity. Keep unmatched items in the output with explicit reason; do not guess coordinates.

```json
{
  "label": "net-anchored parasitic overlay",
  "ground_caps": [],
  "coupling_caps": [],
  "source_artifact_sha256": "...",
  "unmatched": []
}
```

- [ ] Run GREEN plus existing raw-PEX graph tests and commit.

```bash
python -m unittest \
  tools.analog_harness.tests.test_workflow_visualization \
  tools.analog_harness.tests.test_stage3_raw_pex_graph \
  tools.analog_harness.tests.test_parasitic_raw_spice_graph_edges
git add tools/analog_harness/workflow_visualization.py tools/analog_harness/tests/test_workflow_visualization.py
git commit -m "feat: derive live physical visualization evidence"
```

## Task 8: Build the live-only API service

**Files:**

- Create: `apps/pcs-harness-workflow/backend/app.py`
- Create: `apps/pcs-harness-workflow/backend/run_service.py`
- Create: `apps/pcs-harness-workflow/backend/requirements.txt`
- Create: `apps/pcs-harness-workflow/backend/tests/test_api.py`

- [ ] Write failing API tests for supported circuit types, OTA upload/parse/preflight, verified-profile binding, single active run, SSE ordering, `Last-Event-ID` recovery, and unsupported arbitrary-netlist closure rejection.

- [ ] Run RED.

```bash
python -m unittest discover -s apps/pcs-harness-workflow/backend/tests -p 'test_*.py'
```

- [ ] Implement:

```text
GET  /api/circuit-types
POST /api/netlists/parse
POST /api/runs
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/events
GET  /api/runs/{run_id}/artifacts/{artifact_id}
```

The OTA recording path must hash-match the verified `ota_core` input/profile before enabling start. Artifact access must resolve IDs from event references and reject arbitrary filesystem paths.

- [ ] Start the Harness as a subprocess with an explicit environment and fresh run root. Stream persisted JSONL events; the API must not reinterpret pass/fail evidence.

- [ ] Run GREEN and commit in the root repository.

```bash
python -m unittest discover -s apps/pcs-harness-workflow/backend/tests -p 'test_*.py'
git add apps/pcs-harness-workflow/backend
git commit -m "feat: expose live PCS workflow API"
```

## Task 9: Scaffold the standalone frontend and implement the input gate

**Files:**

- Create: `apps/pcs-harness-workflow/package.json`
- Create: `apps/pcs-harness-workflow/index.html`
- Create: `apps/pcs-harness-workflow/vite.config.ts`
- Create: `apps/pcs-harness-workflow/tsconfig*.json`
- Create: `apps/pcs-harness-workflow/src/main.tsx`
- Create: `apps/pcs-harness-workflow/src/App.tsx`
- Create: `apps/pcs-harness-workflow/src/components/InputGate.tsx`
- Create: `apps/pcs-harness-workflow/src/components/InputGate.test.tsx`

- [ ] Write a failing component test for the exact progression: select type → upload `.sp/.spice/.cir` → parse → preflight → enable “开始设计闭环”. Assert other types reflect the backend registry and are not presented as full-demo-ready unless the backend says so.

- [ ] Run RED.

```bash
cd apps/pcs-harness-workflow && pnpm test --run src/components/InputGate.test.tsx
```

- [ ] Implement the input gate, API client, accessible error states, and a strict `1920×1080` recording-safe shell. Use Chinese product copy and English technical acronyms.

- [ ] Run GREEN, build, and commit.

```bash
cd apps/pcs-harness-workflow
pnpm test --run src/components/InputGate.test.tsx
pnpm build
git -C /home/qlf/IOT add apps/pcs-harness-workflow
git -C /home/qlf/IOT commit -m "feat: add PCS workflow input gate"
```

## Task 10: Implement the event reducer, reconnect logic, and engineering cockpit

**Files:**

- Create: `apps/pcs-harness-workflow/src/contracts/events.ts`
- Create: `apps/pcs-harness-workflow/src/state/workflowReducer.ts`
- Create: `apps/pcs-harness-workflow/src/state/workflowReducer.test.ts`
- Create: `apps/pcs-harness-workflow/src/api/liveEvents.ts`
- Create: `apps/pcs-harness-workflow/src/api/liveEvents.test.ts`
- Create: `apps/pcs-harness-workflow/src/components/StageRail.tsx`
- Create: `apps/pcs-harness-workflow/src/components/AgentDecisionPanel.tsx`
- Create: `apps/pcs-harness-workflow/src/components/GrpoPanel.tsx`
- Create: `apps/pcs-harness-workflow/src/components/EvidencePanel.tsx`

- [ ] Write failing reducer tests for idempotence, sequence-gap detection, N/N+1 preservation, current-stage transitions, Agent decision separation, group-relative GRPO updates, and terminal failure/success.

- [ ] Write a failing reconnect test asserting `Last-Event-ID` and gap backfill behavior. There must be no replay, scrubber, playback-rate, or demo-data API.

- [ ] Run RED.

```bash
cd apps/pcs-harness-workflow && pnpm test --run src/state/workflowReducer.test.ts src/api/liveEvents.test.ts
```

- [ ] Implement discriminated TypeScript event types and a pure reducer.

```typescript
type WorkflowEvent =
  | StageEvent
  | AgentDecisionEvent
  | GrpoCandidateEvent
  | ArtifactEvent
  | RunTerminalEvent;
```

- [ ] Build the top L0–L6 rail, evidence panel, Agent observation/judgment/action/rationale card, and live GRPO group/candidate/reward panel. Never render raw chain-of-thought.

- [ ] Run GREEN and commit.

```bash
cd apps/pcs-harness-workflow && pnpm test --run
git -C /home/qlf/IOT add apps/pcs-harness-workflow
git -C /home/qlf/IOT commit -m "feat: visualize live Agent and GRPO workflow"
```

## Task 11: Add physical-stage animation and iteration comparison

**Files:**

- Create: `apps/pcs-harness-workflow/src/components/LayoutStage.tsx`
- Create: `apps/pcs-harness-workflow/src/components/ParasiticOverlay.tsx`
- Create: `apps/pcs-harness-workflow/src/components/VerificationPanel.tsx`
- Create: `apps/pcs-harness-workflow/src/components/IterationCompare.tsx`
- Create: `apps/pcs-harness-workflow/src/components/PerformanceChart.tsx`
- Create: corresponding `*.test.tsx` files
- Modify: `apps/pcs-harness-workflow/src/App.tsx`
- Modify: `apps/pcs-harness-workflow/src/styles.css`

- [ ] Write failing tests for checkpoint labels, shared geometry coordinates, clean DRC scan with true zero, LVS source/extracted status, top-10/VOUT parasite filtering, artifact provenance tooltip, fixed chart domains, and N/N+1 sizing/GDS/PEX/performance diffs.

- [ ] Run RED.

```bash
cd apps/pcs-harness-workflow && pnpm test --run src/components
```

- [ ] Implement progressive real-checkpoint rendering. Animate only the reveal of already-produced geometry; label it “路由结果逐层展示” unless actual router iterations exist.

- [ ] Implement ground-cap halos and coupling curves from the net-anchored overlay, using log-scaled width and explicit disclosure that node anchors are representative coordinates.

- [ ] Implement red/gray/cyan old/overlap/new geometry and fixed-scale pre/post/PVT plots with target lines.

- [ ] Run tests, production build, then inspect a 1920×1080 screenshot for clipping, contrast, misleading labels, and unpolished competition-language strings.

```bash
cd apps/pcs-harness-workflow
pnpm test --run
pnpm build
```

- [ ] Commit.

```bash
git -C /home/qlf/IOT add apps/pcs-harness-workflow
git -C /home/qlf/IOT commit -m "feat: visualize physical closure and iteration gains"
```

## Task 12: Wire the automatic recording run and stop conditions

**Files:**

- Create: `tools/analog_harness/workflow_runner.py`
- Modify: `tools/analog_harness/cli.py`
- Create: `tools/analog_harness/tests/test_workflow_runner.py`
- Create: `apps/pcs-harness-workflow/scripts/start-recording-demo.sh`
- Create: `apps/pcs-harness-workflow/README.md`

- [ ] Write failing runner tests for one-click execution, Agent `run_grpo` dispatch, group/candidate budgets, L6 success stop, runtime-budget failure, immutable boundary input, and no silent success fallback.

- [ ] Run RED.

```bash
python -m unittest tools.analog_harness.tests.test_workflow_runner
```

- [ ] Implement CLI `workflow-run` that performs runtime preflight, evaluates the selected boundary candidate, asks the Agent, dispatches GRPO, promotes the selected candidate, and continues through post-layout PVT.

- [ ] Implement the launcher with explicit paths and no unresolved broad environment-variable targets.

```bash
./apps/pcs-harness-workflow/scripts/start-recording-demo.sh \
  --run-root /home/qlf/IOT/generated/analog_harness/ota_core_grpo_demo_20260826/recording_run
```

Expected: API on port 8103 and Vite on `http://localhost:3103/`; no run begins until the browser submits the verified OTA input.

- [ ] Run GREEN, regression tests, frontend tests/build, and commit both repositories separately.

## Task 13: Run the real campaign, report timings, and perform recording rehearsal

**Files:**

- Generate: `generated/analog_harness/ota_core_grpo_demo_20260826/boundary_scan/**`
- Generate: `generated/analog_harness/ota_core_grpo_demo_20260826/recording_run/**`
- Generate: `generated/analog_harness/ota_core_grpo_demo_20260826/timing/stage_timing.{json,csv}`
- Generate: `generated/analog_harness/ota_core_grpo_demo_20260826/timing/timing_report.md`
- Generate: `generated/analog_harness/ota_core_grpo_demo_20260826/final_report/verification.md`

- [ ] Run environment preflight and a single full candidate pilot first. Confirm stage timings and visualization artifacts are complete before spending the scan budget.

- [ ] Run the deterministic ~32 candidate pre-layout scan, then the 6–8 candidate physical screen. Do not proceed if no candidate meets the boundary/trust contract; report the measured distribution and open a design-change task instead.

- [ ] Freeze `selection.json`, GRPO checkpoint/config, seed, tool versions, and all input hashes. Start a completely fresh `recording_run` and exercise the UI from netlist upload to terminal state.

- [ ] Validate final evidence with machine checks:

```bash
python -m tools.analog_harness.cli summarize --config tools/analog_harness/configs/ota_core_workflow_demo.yaml
python -m unittest discover -s tools/analog_harness/tests -p 'test_*.py'
cd /home/qlf/IOT/apps/pcs-harness-workflow && pnpm test --run && pnpm build
```

Expected final report facts:

- initial pre-layout GBW is 5.2–6.0 MHz;
- initial post-PEX GBW is 4.0–4.9 MHz and below 5 MHz;
- DRC=0, LVS match, raw PEX R/C parseable;
- Agent chooses validated `run_grpo` from the frozen report;
- at least one approved W/NF changes and GDS/raw-PEX hashes change;
- recovered post-PEX GBW reaches 5 MHz while gain, phase margin, and power pass;
- TT/SS/FF post-layout PVT passes and closure is L6;
- timing report contains measured L0, L1, L2, L3, DRC, LVS, PEX, Agent, each GRPO candidate/group, L5, L6, and total durations.

- [ ] Capture a 1920×1080 rehearsal recording. Review that there is no “给评委看”, “作为评委展示”, “离线回放”, “默认证据回放”, “轻量案例”, private chain-of-thought, or fabricated stage wording.

- [ ] Load `superpowers:verification-before-completion`, perform final evidence review, update the workstream, request code review, and only then enter branch finishing.

---

## Execution Gates

1. Do not run the expensive boundary campaign before Tasks 2–8 pass; otherwise timings and evidence may be lost.
2. Do not start frontend polish before the event reducer consumes real contract fixtures.
3. Do not call the run “GRPO” unless Task 5 provenance checks pass.
4. Do not record the final video unless Task 13 reaches a genuine L6 or the user explicitly decides to present a truthful failed run.
5. If the scan finds no valid boundary candidate, stop and discuss whether to widen the deterministic W/NF scan or revise the physical action space; do not open L, multi, or bias automatically.
