import { useEffect, useReducer, useState } from "react";

import { connectLiveEvents } from "./api/liveEvents";
import { workflowApi, type RunSummary } from "./api/workflowApi";
import { AgentDecisionPanel } from "./components/AgentDecisionPanel";
import { EvidencePanel } from "./components/EvidencePanel";
import { GrpoPanel } from "./components/GrpoPanel";
import { InputGate } from "./components/InputGate";
import { StageRail } from "./components/StageRail";
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
          <div className="focus-grid">
            <div className="focus-crosshair"><i /><i /><span>{state.currentStage ?? "L0"}</span></div>
            <div>
              <small>CURRENT OPERATION</small>
              <h2>{stageTitle(state.currentStage)}</h2>
              <p>物理视图与性能曲线将随当前工具阶段切换，数据只从本次运行产物生成。</p>
            </div>
          </div>
          <div className="physical-subrail">
            {(["DRC", "LVS", "PEX"] as const).map((stage) => (
              <span className={state.stages[stage].status} key={stage}><i />{stage}<small>{state.stages[stage].status}</small></span>
            ))}
          </div>
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

function stageTitle(stage: string | null) {
  const titles: Record<string, string> = {
    L0: "编译候选电路",
    L1: "标称前仿真",
    L2: "前仿真 PVT",
    L3: "生成物理版图",
    DRC: "设计规则检查",
    LVS: "版图网表一致性",
    PEX: "提取版图寄生",
    L4: "冻结物理证据",
    L5: "寄生后仿真",
    L6: "后仿真 PVT",
    Agent: "Agent 读取证据并决策",
    GRPO: "GRPO 搜索 MOS sizing",
  };
  return stage ? titles[stage] ?? stage : "建立运行环境";
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
