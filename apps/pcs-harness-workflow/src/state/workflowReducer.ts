import type { ArtifactRef, StageName, WorkflowEvent } from "../contracts/events";

export type StageStatus = "waiting" | "running" | "completed" | "failed";

export interface StageState {
  status: StageStatus;
  sequence?: number;
  candidateId?: string;
  elapsedMs?: number;
  detail?: string;
}

export interface AgentDecisionView {
  candidateId: string;
  observation: string;
  judgment: string;
  action: string;
  reasonCode: string;
  rationale: string;
  sequence: number;
}

export interface GrpoCandidateView {
  candidateId: string;
  sampleIndex: number;
  reward: number | null;
  constraintsPassed: boolean | null;
  sizing?: Record<string, number>;
}

export interface GrpoGroupView {
  groupId: string;
  candidates: GrpoCandidateView[];
  update?: { updateIndex: number; meanReward: number };
}

export interface IterationView {
  candidateId: string;
  metrics: Record<string, number>;
  stages: Record<string, Record<string, unknown>>;
  artifacts: ArtifactRef[];
}

export interface WorkflowState {
  runId: string;
  lastSequence: number;
  sequenceGap: { expected: number; received: number } | null;
  connection: "connecting" | "live" | "recovering" | "closed" | "error";
  currentStage: StageName | null;
  activeCandidate: string | null;
  stages: Record<string, StageState>;
  iterations: Record<string, IterationView>;
  iterationOrder: string[];
  agentDecisions: AgentDecisionView[];
  grpoGroups: Record<string, GrpoGroupView>;
  grpoGroupOrder: string[];
  artifacts: ArtifactRef[];
  terminal: { status: "completed" | "failed" | "blocked"; detail: string } | null;
}

export type WorkflowAction =
  | { type: "event"; event: WorkflowEvent }
  | { type: "connection"; status: WorkflowState["connection"] }
  | { type: "gap"; expected: number; received: number };

const stageNames: StageName[] = ["L0", "L1", "L2", "L3", "DRC", "LVS", "PEX", "L4", "L5", "L6", "Agent", "GRPO"];

export function initialWorkflowState(runId: string): WorkflowState {
  return {
    runId,
    lastSequence: 0,
    sequenceGap: null,
    connection: "connecting",
    currentStage: null,
    activeCandidate: null,
    stages: Object.fromEntries(stageNames.map((stage) => [stage, { status: "waiting" as const }])),
    iterations: {},
    iterationOrder: [],
    agentDecisions: [],
    grpoGroups: {},
    grpoGroupOrder: [],
    artifacts: [],
    terminal: null,
  };
}

export function workflowReducer(state: WorkflowState, action: WorkflowAction): WorkflowState {
  if (action.type === "connection") return { ...state, connection: action.status };
  if (action.type === "gap") {
    return {
      ...state,
      connection: "recovering",
      sequenceGap: { expected: action.expected, received: action.received },
    };
  }
  const event = action.event;
  if (event.run_id !== state.runId || event.sequence <= state.lastSequence) return state;
  if (event.sequence !== state.lastSequence + 1) {
    return {
      ...state,
      connection: "recovering",
      sequenceGap: { expected: state.lastSequence + 1, received: event.sequence },
    };
  }

  let next: WorkflowState = {
    ...state,
    lastSequence: event.sequence,
    sequenceGap: null,
    connection: "live",
    activeCandidate: event.candidate_id ?? state.activeCandidate,
    artifacts: mergeArtifacts(state.artifacts, event.artifact_refs),
  };

  if (event.event_type.startsWith("stage.") && event.stage) next = reduceStage(next, event);
  if (event.event_type === "agent.decision") next = reduceAgent(next, event);
  if (event.event_type.startsWith("grpo.")) next = reduceGrpo(next, event);
  if (["run.completed", "run.failed", "runtime.blocked"].includes(event.event_type)) {
    const status = event.event_type === "run.completed" ? "completed" : event.event_type === "runtime.blocked" ? "blocked" : "failed";
    const detail = String(event.payload.candidate_id ?? event.payload.reason ?? event.payload.detail ?? "");
    next = { ...next, terminal: { status, detail }, connection: "closed" };
  }
  return next;
}

function reduceStage(state: WorkflowState, event: WorkflowEvent): WorkflowState {
  const stage = event.stage as StageName;
  const status: StageStatus = event.event_type === "stage.started" ? "running" : event.event_type === "stage.failed" ? "failed" : "completed";
  const detail = String(event.payload.error ?? event.payload.reason ?? event.payload.status ?? "");
  const stages = {
    ...state.stages,
    [stage]: {
      status,
      sequence: event.sequence,
      candidateId: event.candidate_id ?? undefined,
      elapsedMs: event.elapsed_ms,
      detail: detail || undefined,
    },
  };
  let iterations = state.iterations;
  let iterationOrder = state.iterationOrder;
  if (event.candidate_id) {
    const current = state.iterations[event.candidate_id] ?? {
      candidateId: event.candidate_id,
      metrics: {},
      stages: {},
      artifacts: [],
    };
    iterations = {
      ...state.iterations,
      [event.candidate_id]: {
        ...current,
        metrics: { ...current.metrics, ...numericRecord(event.payload.metrics) },
        stages: { ...current.stages, [stage]: { ...event.payload } },
        artifacts: mergeArtifacts(current.artifacts, event.artifact_refs),
      },
    };
    if (!state.iterationOrder.includes(event.candidate_id)) {
      iterationOrder = [...state.iterationOrder, event.candidate_id];
    }
  }
  return { ...state, stages, iterations, iterationOrder, currentStage: stage };
}

function reduceAgent(state: WorkflowState, event: WorkflowEvent): WorkflowState {
  const payload = event.payload;
  const decision: AgentDecisionView = {
    candidateId: event.candidate_id ?? "—",
    observation: String(payload.observation_summary ?? payload.observation ?? "证据包已冻结"),
    judgment: String(payload.failure_owner ?? "unclassified"),
    action: String(payload.action ?? "stop"),
    reasonCode: String(payload.reason_code ?? "unspecified"),
    rationale: String(payload.rationale ?? ""),
    sequence: event.sequence,
  };
  return {
    ...state,
    currentStage: "Agent",
    agentDecisions: [...state.agentDecisions, decision],
    stages: { ...state.stages, Agent: { status: "completed", sequence: event.sequence } },
  };
}

function reduceGrpo(state: WorkflowState, event: WorkflowEvent): WorkflowState {
  const groupId = String(event.payload.group_id ?? "unassigned");
  const current = state.grpoGroups[groupId] ?? { groupId, candidates: [] };
  let group: GrpoGroupView = current;
  if (event.event_type === "grpo.candidate") {
    const candidate: GrpoCandidateView = {
      candidateId: event.candidate_id ?? "—",
      sampleIndex: Number(event.payload.sample_index ?? current.candidates.length),
      reward: typeof event.payload.reward === "number" ? event.payload.reward : null,
      constraintsPassed: typeof event.payload.constraints_passed === "boolean" ? event.payload.constraints_passed : null,
      sizing: numericRecord(event.payload.sizing),
    };
    group = { ...current, candidates: [...current.candidates.filter((item) => item.candidateId !== candidate.candidateId), candidate] };
  } else if (event.event_type === "grpo.policy_updated") {
    group = {
      ...current,
      update: {
        updateIndex: Number(event.payload.update_index ?? 0),
        meanReward: Number(event.payload.mean_reward ?? 0),
      },
    };
  }
  return {
    ...state,
    currentStage: "GRPO",
    grpoGroups: { ...state.grpoGroups, [groupId]: group },
    grpoGroupOrder: state.grpoGroupOrder.includes(groupId) ? state.grpoGroupOrder : [...state.grpoGroupOrder, groupId],
    stages: { ...state.stages, GRPO: { status: event.event_type === "grpo.policy_updated" ? "completed" : "running", sequence: event.sequence } },
  };
}

function numericRecord(value: unknown): Record<string, number> {
  if (!value || typeof value !== "object") return {};
  return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, number] => typeof entry[1] === "number"));
}

function mergeArtifacts(current: ArtifactRef[], incoming: ArtifactRef[]): ArtifactRef[] {
  const byId = new Map(current.map((artifact) => [artifact.artifact_id, artifact]));
  for (const artifact of incoming) byId.set(artifact.artifact_id, artifact);
  return [...byId.values()];
}
