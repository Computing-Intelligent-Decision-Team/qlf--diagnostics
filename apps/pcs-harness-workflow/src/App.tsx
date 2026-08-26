import { useState } from "react";

import { workflowApi, type RunSummary } from "./api/workflowApi";
import { InputGate } from "./components/InputGate";

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

      {run ? (
        <main className="run-transition" aria-live="polite">
          <span className="run-kicker">WORKFLOW INITIALIZED</span>
          <h1>设计闭环已启动</h1>
          <p>正在连接 PCS-Harness 实时事件流…</p>
          <code>{run.run_id}</code>
        </main>
      ) : (
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

function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 42 42" aria-hidden="true">
      <rect x="1" y="1" width="40" height="40" rx="3" />
      <path d="M10 11h8v8h-8zM24 23h8v8h-8zM18 15h8v12h-8z" />
      <path className="signal" d="M4 21h6M32 21h6M21 4v7M21 31v7" />
    </svg>
  );
}
