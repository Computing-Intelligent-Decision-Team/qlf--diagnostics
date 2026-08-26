export interface CircuitType {
  id: string;
  name: string;
  supported: boolean;
  demo_ready: boolean;
  design_profiles: string[];
}

export interface ParseResult {
  parse_id: string;
  circuit_type: string;
  filename: string;
  netlist: {
    top_cell: string;
    ports: string[];
    device_counts: Record<string, number>;
    sha256: string;
    size_bytes: number;
  };
  preflight: { ready: boolean; code: string };
  binding: {
    design_id: string | null;
    profile_path: string;
    profile_sha256: string;
    verified_netlist_sha256: string;
  };
}

export interface RunSummary {
  run_id: string;
  status: string;
  run_root?: string;
  events_path?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || `请求失败（${response.status}）`);
  }
  return payload as T;
}

export const workflowApi = {
  async getCircuitTypes(): Promise<CircuitType[]> {
    const payload = await request<{ items: CircuitType[] }>("/api/circuit-types");
    return payload.items;
  },

  parseNetlist(circuitType: string, file: File): Promise<ParseResult> {
    return file.text().then((content) =>
      request<ParseResult>("/api/netlists/parse", {
        method: "POST",
        body: JSON.stringify({ circuit_type: circuitType, filename: file.name, content }),
      }),
    );
  },

  startRun(parseId: string): Promise<RunSummary> {
    return request<RunSummary>("/api/runs", {
      method: "POST",
      body: JSON.stringify({ parse_id: parseId }),
    });
  },
};
