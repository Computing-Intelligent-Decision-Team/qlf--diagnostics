import { useEffect, useMemo, useState } from "react";

import type { PhysicalVisualization } from "../contracts/physical";
import type { IterationView, WorkflowState } from "../state/workflowReducer";
import { IterationCompare, type IterationEvidence } from "./IterationCompare";
import { LayoutStage } from "./LayoutStage";
import { ParasiticOverlay } from "./ParasiticOverlay";
import { VerificationPanel } from "./VerificationPanel";

type ViewMode = "layout" | "parasitics" | "comparison";

export function PhysicalWorkspace({ state, physical }: { state: WorkflowState; physical: PhysicalVisualization | null }) {
  const [mode, setMode] = useState<ViewMode>("layout");
  const comparison = useMemo(() => comparisonEvidence(state), [state]);
  useEffect(() => {
    if (["PEX", "L5", "L6"].includes(state.currentStage ?? "") && physical) setMode("parasitics");
    if (["Agent", "GRPO"].includes(state.currentStage ?? "") && comparison) setMode("comparison");
  }, [comparison, physical, state.currentStage]);

  const lvs = physical?.lvs;
  return (
    <div className="physical-workspace">
      <div className="workspace-toolbar">
        <div>
          <button className={mode === "layout" ? "active" : ""} onClick={() => setMode("layout")} disabled={!physical}>版图演进</button>
          <button className={mode === "parasitics" ? "active" : ""} onClick={() => setMode("parasitics")} disabled={!physical}>寄生覆盖</button>
          <button className={mode === "comparison" ? "active" : ""} onClick={() => setMode("comparison")} disabled={!comparison}>迭代对比</button>
        </div>
        <span>REAL ARTIFACT COORDINATES</span>
      </div>
      <div className="workspace-content">
        {!physical && <PhysicalWaiting stage={state.currentStage} />}
        {physical && mode === "layout" && <LayoutStage data={physical.layout} />}
        {physical && mode === "parasitics" && <ParasiticOverlay layout={physical.layout} overlay={physical.parasitics} />}
        {mode === "comparison" && comparison && <IterationCompare before={comparison[0]} after={comparison[1]} />}
      </div>
      <VerificationPanel
        drc={{ status: physical?.drc.status ?? state.stages.DRC.status, count: physical?.drc.count ?? null, artifactHash: physical?.drc.source_artifact_sha256 }}
        lvs={{ status: lvs?.status ?? state.stages.LVS.status, sourceDevices: lvs?.source_devices, extractedDevices: lvs?.extracted_devices, artifactHash: lvs?.source_artifact_sha256 }}
        pex={{ status: state.stages.PEX.status, capacitorCount: physical?.parasitics.selected_count, artifactHash: physical?.parasitics.source_artifact_sha256 }}
      />
    </div>
  );
}

function PhysicalWaiting({ stage }: { stage: string | null }) {
  return (
    <div className="physical-waiting">
      <div className="scan-frame"><i /><i /><span>{stage ?? "L0"}</span></div>
      <div><small>CURRENT OPERATION</small><h2>{stage ? `正在执行 ${stage}` : "建立运行环境"}</h2><p>GDS、DRC、LVS 与 PEX 产物生成后将在同一坐标系中显示。</p></div>
    </div>
  );
}

function comparisonEvidence(state: WorkflowState): [IterationEvidence, IterationEvidence] | null {
  if (state.iterationOrder.length < 2) return null;
  const before = toEvidence(state.iterations[state.iterationOrder.at(-2)!]);
  const after = toEvidence(state.iterations[state.iterationOrder.at(-1)!]);
  return before && after ? [before, after] : null;
}

function toEvidence(iteration: IterationView): IterationEvidence | null {
  const sizing = objectNumbers(iteration.stages.L0?.sizing ?? iteration.stages.L5?.sizing);
  const gds = iteration.artifacts.find((artifact) => /gds/i.test(artifact.name));
  const pex = iteration.artifacts.find((artifact) => /raw_pex|raw.*spice|pex/i.test(artifact.name));
  const cap = firstNumber(iteration.stages.PEX, ["total_capacitance_ff", "parasitic_cap_ff", "selected_capacitance_ff"]);
  if (!gds || !pex || cap == null || !Object.keys(iteration.metrics).length) return null;
  return {
    candidateId: iteration.candidateId,
    sizing,
    gdsHash: gds.sha256,
    pexHash: pex.sha256,
    parasiticCapFf: cap,
    metrics: iteration.metrics,
  };
}

function objectNumbers(value: unknown): Record<string, number> {
  if (!value || typeof value !== "object") return {};
  return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, number] => typeof entry[1] === "number"));
}

function firstNumber(record: Record<string, unknown> | undefined, keys: string[]) {
  for (const key of keys) if (typeof record?.[key] === "number") return record[key] as number;
  return null;
}
