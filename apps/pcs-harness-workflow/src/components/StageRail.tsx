import type { WorkflowState } from "../state/workflowReducer";

const closureStages = ["L0", "L1", "L2", "L3", "L4", "L5", "L6"] as const;
const labels: Record<(typeof closureStages)[number], string> = {
  L0: "编译",
  L1: "前仿真",
  L2: "前仿 PVT",
  L3: "版图",
  L4: "物理签核",
  L5: "后仿真",
  L6: "后仿 PVT",
};

export function StageRail({ state }: { state: WorkflowState }) {
  return (
    <nav className="stage-rail" aria-label="PCS-Harness L0 至 L6 进度">
      {closureStages.map((stage, index) => {
        const status = state.stages[stage].status;
        return (
          <div className={`rail-stage ${status} ${state.currentStage === stage ? "current" : ""}`} key={stage}>
            <span className="rail-node">{status === "completed" ? "✓" : index}</span>
            <div><b>{stage}</b><small>{labels[stage]}</small></div>
            {index < closureStages.length - 1 && <i />}
          </div>
        );
      })}
    </nav>
  );
}
