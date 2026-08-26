import type { WorkflowState } from "../state/workflowReducer";

const actionLabels: Record<string, string> = {
  run_grpo: "调用 GRPO 继续 sizing",
  retry_layout: "返回版图生成",
  proceed_post_layout: "进入后仿真验证",
  stop: "终止当前闭环",
  quarantine_candidate: "隔离当前候选",
};

export function AgentDecisionPanel({ state }: { state: WorkflowState }) {
  const decision = state.agentDecisions.at(-1);
  return (
    <section className="cockpit-card agent-card" aria-labelledby="agent-panel-title">
      <header><span>AGENT REASONING</span><i className={decision ? "active" : ""} /></header>
      <h2 id="agent-panel-title">决策轨迹</h2>
      {decision ? (
        <div className="decision-stack">
          <DecisionRow index="01" label="观察" value={decision.observation} />
          <DecisionRow index="02" label="归因" value={decision.judgment} mono />
          <DecisionRow index="03" label="动作" value={actionLabels[decision.action] ?? decision.action} accent />
          <DecisionRow index="04" label="依据" value={decision.rationale} />
          <div className="reason-code">{decision.reasonCode} · EVENT #{decision.sequence}</div>
        </div>
      ) : (
        <EmptyPanel text="等待首个诊断证据包" />
      )}
    </section>
  );
}

function DecisionRow({ index, label, value, mono, accent }: { index: string; label: string; value: string; mono?: boolean; accent?: boolean }) {
  return (
    <div className={`decision-row ${accent ? "accent" : ""}`}>
      <span>{index}</span>
      <small>{label}</small>
      <p className={mono ? "mono" : ""}>{value}</p>
    </div>
  );
}

function EmptyPanel({ text }: { text: string }) {
  return <div className="panel-empty"><span className="waiting-pulse" />{text}</div>;
}
