import type { WorkflowState } from "../state/workflowReducer";

export function GrpoPanel({ state }: { state: WorkflowState }) {
  const groupId = state.grpoGroupOrder.at(-1);
  const group = groupId ? state.grpoGroups[groupId] : undefined;
  return (
    <section className="cockpit-card grpo-card" aria-labelledby="grpo-panel-title">
      <header><span>GRPO OPTIMIZER</span><b>{group?.groupId ?? "IDLE"}</b></header>
      <div className="panel-title-line">
        <h2 id="grpo-panel-title">Sizing 搜索</h2>
        <span>W / NF ONLY</span>
      </div>
      {group ? (
        <>
          <div className="candidate-table">
            <div className="table-head"><span>候选</span><span>约束</span><span>REWARD</span></div>
            {group.candidates.map((candidate) => (
              <div className="candidate-row" key={candidate.candidateId}>
                <span><i>#{candidate.sampleIndex + 1}</i>{candidate.candidateId}</span>
                <span className={candidate.constraintsPassed ? "pass" : "fail"}>
                  {candidate.constraintsPassed == null ? "—" : candidate.constraintsPassed ? "PASS" : "FAIL"}
                </span>
                <strong>{candidate.reward == null ? "—" : candidate.reward.toFixed(3)}</strong>
              </div>
            ))}
          </div>
          <div className="policy-update">
            <span>POLICY UPDATE</span>
            <strong>{group.update ? `#${group.update.updateIndex}` : "等待 group 完成"}</strong>
            <small>{group.update ? `mean reward ${group.update.meanReward.toFixed(3)}` : `${group.candidates.length} candidates observed`}</small>
          </div>
        </>
      ) : (
        <div className="panel-empty"><span className="waiting-pulse" />等待 Agent 发起 sizing 搜索</div>
      )}
    </section>
  );
}
