import type { WorkflowState } from "../state/workflowReducer";

export function EvidencePanel({ state }: { state: WorkflowState }) {
  const iteration = state.activeCandidate ? state.iterations[state.activeCandidate] : undefined;
  const metrics = Object.entries(iteration?.metrics ?? {}).slice(0, 5);
  return (
    <section className="evidence-strip" aria-labelledby="evidence-title">
      <div className="evidence-strip-title">
        <span>LIVE EVIDENCE</span>
        <h2 id="evidence-title">当前证据</h2>
      </div>
      <div className="live-metrics">
        {metrics.length ? metrics.map(([name, value]) => (
          <span key={name}><small>{name}</small><strong>{formatMetric(name, value)}</strong></span>
        )) : <p>等待仿真指标写入…</p>}
      </div>
      <div className="artifact-count">
        <small>VERIFIED ARTIFACTS</small>
        <strong>{String(state.artifacts.length).padStart(2, "0")}</strong>
        <span>SHA-256 indexed</span>
      </div>
    </section>
  );
}

function formatMetric(name: string, value: number) {
  const key = name.toLowerCase();
  if (key.includes("gbw") || key.includes("bandwidth")) return `${(value / 1e6).toFixed(2)} MHz`;
  if (key.includes("power")) return `${(value * 1e3).toFixed(2)} mW`;
  if (key.includes("phase") || key.includes("gain")) return `${value.toFixed(1)}°`;
  return value.toPrecision(4);
}
