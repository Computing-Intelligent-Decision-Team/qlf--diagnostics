export interface GdsShape {
  kind: "polygon" | "path";
  layer: number | null;
  datatype: number | null;
  width: number | null;
  points: number[][];
  normalized_points: number[][];
}

export interface GdsCheckpoint {
  name: string;
  source_path: string;
  source_sha256: string;
  bounds: number[] | null;
  view_box: number[];
  shapes: GdsShape[];
  labels: Array<{ text: string; layer: number | null; texttype: number | null; xy: number[] | null; normalized_xy?: number[] }>;
}

export interface LayoutVisualization {
  view_box: number[];
  coordinate_transform: { offset: number[]; scale: number };
  checkpoints: GdsCheckpoint[];
}

export interface ParasiticAnchor {
  net: string;
  xy: number[];
  source_line_number: number;
}

export interface ParasiticCap {
  cap_id: string;
  node_1: string;
  node_2: string;
  capacitance_ff: number;
  source_line: string;
  source_line_number: number;
  visual_width: number;
  anchors: ParasiticAnchor[];
}

export interface ParasiticVisualization {
  label: "net-anchored parasitic overlay";
  coordinate_disclosure: string;
  selection: { top_n: number; include_output_net: string };
  selected_count: number;
  ground_caps: ParasiticCap[];
  coupling_caps: ParasiticCap[];
  unmatched: Array<Record<string, unknown>>;
  scaling: { method: "logarithmic"; width_range: number[]; unit: "fF" };
  source_artifact_sha256: string;
  ext_source_artifact_sha256: string;
}

export interface PhysicalVisualization {
  schema_version: "pcs_harness_physical_visualization.v1";
  layout: LayoutVisualization;
  drc: {
    status: "clean" | "violations" | "not_provided";
    count: number | null;
    markers: Array<{ rule: string; box: number[]; normalized_box?: number[] }>;
    view_box: number[];
    source_artifact_sha256?: string;
  };
  lvs?: { status: "clean" | "failed"; source_devices: number; extracted_devices: number; source_artifact_sha256: string };
  parasitics: ParasiticVisualization;
}
