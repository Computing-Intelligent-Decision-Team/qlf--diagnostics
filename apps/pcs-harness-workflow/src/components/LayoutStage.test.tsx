import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { LayoutStage } from "./LayoutStage";
import type { PhysicalVisualization } from "../contracts/physical";

export const physicalFixture: PhysicalVisualization = {
  schema_version: "pcs_harness_physical_visualization.v1",
  layout: {
    view_box: [0, -20, 220, 140],
    coordinate_transform: { offset: [0, -20], scale: 1 / 220 },
    checkpoints: ["floorplan", "place", "route", "final"].map((name, index) => ({
      name,
      source_path: `/run/${name}.gds`,
      source_sha256: String(index).repeat(64),
      bounds: [index * 10, -20, 180 + index * 10, 120],
      view_box: [0, -20, 220, 140],
      shapes: [{ kind: "polygon", layer: 67 + index, datatype: 20, width: null, points: [[0, 0], [100, 0], [100, 80], [0, 80], [0, 0]], normalized_points: [] }],
      labels: [],
    })),
  },
  drc: { status: "clean", count: 0, markers: [], view_box: [0, -20, 220, 140], source_artifact_sha256: "d".repeat(64) },
  parasitics: {
    label: "net-anchored parasitic overlay",
    coordinate_disclosure: "Magic .ext node coordinates are representative net anchors, not exact locations.",
    selection: { top_n: 10, include_output_net: "VOUT" },
    selected_count: 2,
    ground_caps: [{ cap_id: "C1", node_1: "VOUT", node_2: "0", capacitance_ff: 0.2, source_line: "C1 VOUT 0 0.2f", source_line_number: 8, visual_width: 1, anchors: [{ net: "VOUT", xy: [180, 60], source_line_number: 3 }] }],
    coupling_caps: [{ cap_id: "C2", node_1: "VOUT", node_2: "net1", capacitance_ff: 2, source_line: "C2 VOUT net1 2f", source_line_number: 9, visual_width: 8, anchors: [{ net: "VOUT", xy: [180, 60], source_line_number: 3 }, { net: "net1", xy: [50, 30], source_line_number: 4 }] }],
    unmatched: [],
    scaling: { method: "logarithmic", width_range: [1, 8], unit: "fF" },
    source_artifact_sha256: "p".repeat(64),
    ext_source_artifact_sha256: "e".repeat(64),
  },
};

describe("LayoutStage", () => {
  it("labels real checkpoints and keeps one shared GDS coordinate system", async () => {
    const user = userEvent.setup();
    render(<LayoutStage data={physicalFixture.layout} />);
    for (const label of ["布局边界", "器件放置", "路由结果", "最终版图"]) {
      expect(screen.getByRole("button", { name: label })).toBeVisible();
    }
    expect(screen.getByText("路由结果逐层展示")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "路由结果" }));
    const svg = screen.getByTestId("layout-canvas");
    expect(svg).toHaveAttribute("viewBox", "0 -20 220 140");
    expect(svg).toHaveAttribute("data-shared-coordinate-system", "true");
    expect(screen.getByTestId("gds-shape-0")).toHaveAttribute("data-layer", "69/20");
  });
});
