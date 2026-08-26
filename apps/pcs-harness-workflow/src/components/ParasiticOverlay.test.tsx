import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { physicalFixture } from "./LayoutStage.test";
import { ParasiticOverlay } from "./ParasiticOverlay";

describe("ParasiticOverlay", () => {
  it("renders Top-10 union VOUT ground halos and coupling curves with provenance", () => {
    render(<ParasiticOverlay layout={physicalFixture.layout} overlay={physicalFixture.parasitics} />);
    expect(screen.getByText("net-anchored parasitic overlay")).toBeVisible();
    expect(screen.getByText("Top 10 + VOUT")).toBeVisible();
    expect(screen.getByTestId("ground-cap-C1")).toHaveAttribute("data-capacitance-ff", "0.2");
    expect(screen.getByTestId("coupling-cap-C2")).toHaveAttribute("stroke-width", "8");
    expect(screen.getByTestId("coupling-cap-C2")).toHaveAttribute(
      "aria-label",
      expect.stringContaining("C2 VOUT net1 2f"),
    );
    expect(screen.getByTestId("coupling-cap-C2")).toHaveAttribute(
      "data-artifact-sha256",
      "p".repeat(64),
    );
    expect(screen.getByText(/representative net anchors/)).toBeVisible();
  });
});
