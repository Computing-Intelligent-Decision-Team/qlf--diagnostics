import { describe, expect, it } from "vitest";

import type { WorkflowEvent } from "../contracts/events";
import { initialWorkflowState, workflowReducer } from "./workflowReducer";

function event(
  sequence: number,
  event_type: WorkflowEvent["event_type"],
  overrides: Partial<WorkflowEvent> = {},
): WorkflowEvent {
  return {
    schema_version: "pcs_harness_workflow_event.v1",
    run_id: "run_001",
    source: "harness",
    event_type,
    sequence,
    occurred_at: "2026-08-26T00:00:00Z",
    elapsed_ms: sequence * 100,
    payload: {},
    candidate_id: null,
    stage: null,
    artifact_refs: [],
    ...overrides,
  } as WorkflowEvent;
}

describe("workflowReducer", () => {
  it("is idempotent and detects a sequence gap without applying the future event", () => {
    const first = workflowReducer(
      initialWorkflowState("run_001"),
      { type: "event", event: event(1, "stage.started", { stage: "L0" }) },
    );
    expect(workflowReducer(first, { type: "event", event: event(1, "stage.started", { stage: "L0" }) })).toBe(first);

    const gap = workflowReducer(first, {
      type: "event",
      event: event(3, "stage.completed", { stage: "L0" }),
    });
    expect(gap.lastSequence).toBe(1);
    expect(gap.sequenceGap).toEqual({ expected: 2, received: 3 });
    expect(gap.stages.L0.status).toBe("running");
  });

  it("tracks stage transitions and preserves candidate N and N+1 evidence", () => {
    let state = initialWorkflowState("run_001");
    state = workflowReducer(state, {
      type: "event",
      event: event(1, "stage.started", { stage: "L5", candidate_id: "cand_0001" }),
    });
    expect(state.currentStage).toBe("L5");
    expect(state.stages.L5.status).toBe("running");
    state = workflowReducer(state, {
      type: "event",
      event: event(2, "stage.completed", {
        stage: "L5",
        candidate_id: "cand_0001",
        payload: { metrics: { GBW: 4_200_000 } },
      }),
    });
    state = workflowReducer(state, {
      type: "event",
      event: event(3, "stage.completed", {
        stage: "L5",
        candidate_id: "cand_0002",
        payload: { metrics: { GBW: 4_760_000 } },
      }),
    });
    expect(state.iterations.cand_0001.metrics.GBW).toBe(4_200_000);
    expect(state.iterations.cand_0002.metrics.GBW).toBe(4_760_000);
    expect(state.iterationOrder).toEqual(["cand_0001", "cand_0002"]);

    state = workflowReducer(state, {
      type: "event",
      event: event(4, "stage.failed", { stage: "L6", payload: { error: "corner failed" } }),
    });
    expect(state.stages.L6.status).toBe("failed");
    expect(state.stages.L6.detail).toBe("corner failed");
  });

  it("separates concise Agent evidence and groups GRPO candidates relative to their update", () => {
    let state = initialWorkflowState("run_001");
    state = workflowReducer(state, {
      type: "event",
      event: event(1, "agent.decision", {
        source: "agent",
        candidate_id: "cand_0001",
        payload: {
          observation: "PEX 后 GBW 低于目标",
          failure_owner: "sizing_optimizer",
          action: "run_grpo",
          reason_code: "post_pex_gbw_regression",
          rationale: "物理验证通过，应回到 sizing。",
          chain_of_thought: "must never render",
        },
      }),
    });
    expect(state.agentDecisions[0]).toEqual({
      candidateId: "cand_0001",
      observation: "PEX 后 GBW 低于目标",
      judgment: "sizing_optimizer",
      action: "run_grpo",
      reasonCode: "post_pex_gbw_regression",
      rationale: "物理验证通过，应回到 sizing。",
      sequence: 1,
    });
    expect(JSON.stringify(state.agentDecisions)).not.toContain("must never render");

    state = workflowReducer(state, {
      type: "event",
      event: event(2, "grpo.candidate", {
        source: "grpo",
        candidate_id: "cand_0002",
        payload: { group_id: "group_03", sample_index: 1, reward: 0.42, constraints_passed: true },
      }),
    });
    state = workflowReducer(state, {
      type: "event",
      event: event(3, "grpo.policy_updated", {
        source: "grpo",
        payload: { group_id: "group_03", update_index: 3, mean_reward: 0.31 },
      }),
    });
    expect(state.grpoGroups.group_03.candidates[0].reward).toBe(0.42);
    expect(state.grpoGroups.group_03.update).toEqual({ updateIndex: 3, meanReward: 0.31 });
  });

  it("records terminal success or failure", () => {
    const completed = workflowReducer(initialWorkflowState("run_001"), {
      type: "event",
      event: event(1, "run.completed", { payload: { candidate_id: "cand_0003" } }),
    });
    expect(completed.terminal).toEqual({ status: "completed", detail: "cand_0003" });

    const failed = workflowReducer(initialWorkflowState("run_001"), {
      type: "event",
      event: event(1, "run.failed", { payload: { reason: "budget_exhausted" } }),
    });
    expect(failed.terminal).toEqual({ status: "failed", detail: "budget_exhausted" });
  });
});
