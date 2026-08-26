import { PerformanceChart } from "./PerformanceChart";

export interface IterationEvidence {
  candidateId: string;
  sizing: Record<string, number>;
  gdsHash: string;
  pexHash: string;
  parasiticCapFf: number;
  metrics: Record<string, number>;
  gdsShapes?: Array<{ id: string; points: string }>;
}

export function IterationCompare({ before, after }: { before: IterationEvidence; after: IterationEvidence }) {
  const sizingKeys = [...new Set([...Object.keys(before.sizing), ...Object.keys(after.sizing)])].filter(
    (key) => before.sizing[key] !== after.sizing[key],
  );
  const commonMetrics = Object.keys(before.metrics).filter((key) => typeof after.metrics[key] === "number");
  const gdsChanged = before.gdsHash !== after.gdsHash;
  const pexDelta = after.parasiticCapFf - before.parasiticCapFf;
  return (
    <div className="iteration-compare">
      <div className="compare-heading">
        <span>ITERATION N <b>{before.candidateId}</b></span><i>→</i><span>ITERATION N+1 <b>{after.candidateId}</b></span>
      </div>
      <div className="compare-body">
        <div className="diff-summary">
          <small>MOS SIZING DIFF</small>
          {sizingKeys.slice(0, 4).map((key) => <strong key={key}>{key} {before.sizing[key]} → {after.sizing[key]}</strong>)}
          <div className="physical-diff">
            <span title={`${before.gdsHash} → ${after.gdsHash}`}>{gdsChanged ? "GDS 已更新" : "GDS 未变化"}</span>
            <span title={`${before.pexHash} → ${after.pexHash}`}>PEX {pexDelta >= 0 ? "+" : "−"}{Math.abs(pexDelta).toFixed(2)} fF</span>
          </div>
          <div className="geometry-legend"><span className="old-legend">旧版图</span><span className="overlap-legend">重叠区域</span><span className="new-legend">新版图</span></div>
        </div>
        <div className="chart-stack">
          {commonMetrics.slice(0, 3).map((metric) => (
            <PerformanceChart key={metric} metric={metric} before={before.metrics[metric]} after={after.metrics[metric]} />
          ))}
        </div>
      </div>
    </div>
  );
}
