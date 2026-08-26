export type StageName =
  | "L0"
  | "L1"
  | "L2"
  | "L3"
  | "DRC"
  | "LVS"
  | "PEX"
  | "L4"
  | "L5"
  | "L6"
  | "Agent"
  | "GRPO";

export interface ArtifactRef {
  artifact_id: string;
  name: string;
  relative_path: string;
  sha256: string;
  size_bytes: number;
}

interface EventBase {
  schema_version: "pcs_harness_workflow_event.v1";
  run_id: string;
  source: string;
  sequence: number;
  occurred_at: string;
  elapsed_ms: number;
  candidate_id: string | null;
  stage: StageName | null;
  artifact_refs: ArtifactRef[];
}

export interface StageEvent extends EventBase {
  event_type: "stage.started" | "stage.completed" | "stage.failed";
  payload: {
    metrics?: Record<string, number>;
    error?: string;
    reason?: string;
    status?: string;
    [key: string]: unknown;
  };
}

export interface AgentEvent extends EventBase {
  event_type: "agent.started" | "agent.decision" | "agent.failed";
  payload: {
    observation?: string;
    observation_summary?: string;
    failure_owner?: string;
    action?: string;
    reason_code?: string;
    rationale?: string;
    reason?: string;
    [key: string]: unknown;
  };
}

export interface GrpoEvent extends EventBase {
  event_type: "grpo.group_started" | "grpo.candidate" | "grpo.policy_updated";
  payload: {
    group_id: string;
    sample_index?: number;
    reward?: number;
    constraints_passed?: boolean;
    update_index?: number;
    mean_reward?: number;
    sizing?: Record<string, number>;
    [key: string]: unknown;
  };
}

export interface RunTerminalEvent extends EventBase {
  event_type: "run.completed" | "run.failed" | "runtime.blocked";
  payload: { candidate_id?: string; reason?: string; detail?: string; [key: string]: unknown };
}

export interface GenericEvent extends EventBase {
  event_type: string;
  payload: Record<string, unknown>;
}

export type WorkflowEvent = StageEvent | AgentEvent | GrpoEvent | RunTerminalEvent | GenericEvent;

export function isWorkflowEvent(value: unknown): value is WorkflowEvent {
  if (!value || typeof value !== "object") return false;
  const event = value as Partial<WorkflowEvent>;
  return (
    event.schema_version === "pcs_harness_workflow_event.v1" &&
    typeof event.run_id === "string" &&
    typeof event.event_type === "string" &&
    Number.isInteger(event.sequence) &&
    (event.sequence ?? 0) > 0 &&
    typeof event.elapsed_ms === "number" &&
    Boolean(event.payload && typeof event.payload === "object") &&
    Array.isArray(event.artifact_refs)
  );
}
