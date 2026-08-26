import { useEffect, useReducer, useState } from "react";

import { connectLiveEvents } from "./api/liveEvents";
import { workflowApi, type RunSummary } from "./api/workflowApi";
import { AgentDecisionPanel } from "./components/AgentDecisionPanel";
import { EvidencePanel } from "./components/EvidencePanel";
import { GrpoPanel } from "./components/GrpoPanel";
import { InputGate } from "./components/InputGate";
import { PhysicalWorkspace } from "./components/PhysicalWorkspace";
import { StageRail } from "./components/StageRail";
import type { PhysicalVisualization } from "./contracts/physical";
import { initialWorkflowState, workflowReducer } from "./state/workflowReducer";

export default function App() {
  const [run, setRun] = useState<RunSummary | null>(null);

  return (
    <div className="app-frame">
      <header className="product-header">
        <a className="brand" href="/" aria-label="PCS-Harness 首页">
          <BrandMark />
          <span><strong>PCS</strong>—HARNESS</span>
        </a>
        <div className="header-meta">
          <span>PHYSICAL CLOSURE SYSTEM</span>
          <i />
          <span>SKY130 / REV. 26.08</span>
        </div>
      </header>

      {run ? <WorkflowCockpit run={run} /> : (
        <InputGate api={workflowApi} onRunStarted={setRun} />
      )}

      <footer className="product-footer">
        <span>PCS-HARNESS ENGINE</span>
        <span className="coordinate">31.2304° N / 121.4737° E</span>
        <span>LIVE EVIDENCE · APPEND-ONLY</span>
      </footer>
    </div>
  );
}

function WorkflowCockpit({ run }: { run: RunSummary }) {
  const [state, dispatch] = useReducer(workflowReducer, run.run_id, initialWorkflowState);
  const [physical, setPhysical] = useState<PhysicalVisualization | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    dispatch({ type: "connection", status: "connecting" });
    connectLiveEvents({
      runId: run.run_id,
      signal: controller.signal,
      lastEventId: state.lastSequence,
      onEvent: (event) => dispatch({ type: "event", event }),
      onGap: ({ expected, received }) => dispatch({ type: "gap", expected, received }),
    })
      .then(() => dispatch({ type: "connection", status: "closed" }))
      .catch(() => {
        if (!controller.signal.aborted) dispatch({ type: "connection", status: "error" });
      });
    return () => controller.abort();
    // A single connection owns sequencing for the lifetime of this run.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run.run_id]);

  const physicalArtifact = [...state.artifacts].reverse().find((artifact) => /physical.*visual|workflow.*visual/i.test(artifact.name));
  useEffect(() => {
    if (!physicalArtifact) return;
    const controller = new AbortController();
    fetch(`/api/runs/${encodeURIComponent(run.run_id)}/artifacts/${encodeURIComponent(physicalArtifact.artifact_id)}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`physical evidence ${response.status}`);
        return response.json();
      })
      .then((payload: PhysicalVisualization) => {
        if (payload.schema_version === "pcs_harness_physical_visualization.v1") setPhysical(payload);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [physicalArtifact, run.run_id]);

  const latestElapsed = Math.max(0, ...Object.values(state.stages).map((stage) => stage.elapsedMs ?? 0));
  return (
    <main className="cockpit-shell">
      <div className="run-bar">
        <div><span className={`connection-dot ${state.connection}`} /><small>RUN ID</small><code>{run.run_id}</code></div>
        <div><small>CANDIDATE</small><strong>{state.activeCandidate ?? "等待生成"}</strong></div>
        <div><small>ELAPSED</small><strong>{formatElapsed(latestElapsed)}</strong></div>
        <div><small>EVENT STREAM</small><strong>{state.connection.toUpperCase()} · #{state.lastSequence}</strong></div>
      </div>
      <StageRail state={state} />
      <div className="cockpit-grid">
        <section className="stage-focus cockpit-card">
          <header><span>ACTIVE WORKSPACE</span><b>{state.currentStage ?? "INITIALIZING"}</b></header>
          <PhysicalWorkspace state={state} physical={physical} />
        </section>
        <AgentDecisionPanel state={state} />
        <GrpoPanel state={state} />
      </div>
      <EvidencePanel state={state} />
    </main>
  );
}

function formatElapsed(milliseconds: number) {
  const seconds = Math.floor(milliseconds / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}


function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 42 42" aria-hidden="true">
      <rect x="1" y="1" width="40" height="40" rx="3" />
      <path d="M10 11h8v8h-8zM24 23h8v8h-8zM18 15h8v12h-8z" />
      <path className="signal" d="M4 21h6M32 21h6M21 4v7M21 31v7" />
    </svg>
  );
}
