import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VerificationPanel } from "./VerificationPanel";

describe("VerificationPanel", () => {
  it("shows a real clean DRC scan and source/extracted LVS agreement", () => {
    render(
      <VerificationPanel
        drc={{ status: "clean", count: 0, artifactHash: "d".repeat(64) }}
        lvs={{ status: "clean", sourceDevices: 5, extractedDevices: 5, artifactHash: "l".repeat(64) }}
        pex={{ status: "completed", capacitorCount: 47, artifactHash: "p".repeat(64) }}
      />,
    );
    expect(screen.getByText("0 violations")).toBeVisible();
    expect(screen.getByText("5 source / 5 extracted")).toBeVisible();
    expect(screen.getByText("47 capacitors")).toBeVisible();
    expect(screen.queryByText(/模拟错误|example violation/i)).not.toBeInTheDocument();
  });
});
