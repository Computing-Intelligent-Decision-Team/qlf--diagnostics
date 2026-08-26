import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { IterationCompare } from "./IterationCompare";

describe("IterationCompare", () => {
  it("shows N/N+1 sizing, GDS, PEX and performance changes on fixed domains", () => {
    render(
      <IterationCompare
        before={{ candidateId: "cand_0007", sizing: { M1_W: 1.2, M1_NF: 2 }, gdsHash: "a".repeat(64), pexHash: "b".repeat(64), parasiticCapFf: 18.4, metrics: { GBW: 4_180_000, gain_db: 62.1, phase_margin_deg: 61 } }}
        after={{ candidateId: "cand_0008", sizing: { M1_W: 1.5, M1_NF: 4 }, gdsHash: "c".repeat(64), pexHash: "d".repeat(64), parasiticCapFf: 16.8, metrics: { GBW: 4_760_000, gain_db: 62.8, phase_margin_deg: 63 } }}
      />,
    );
    expect(screen.getByText("M1_W 1.2 → 1.5")).toBeVisible();
    expect(screen.getByText("M1_NF 2 → 4")).toBeVisible();
    expect(screen.getByText("GDS 已更新")).toBeVisible();
    expect(screen.getByText("PEX −1.60 fF")).toBeVisible();
    const chart = screen.getByTestId("performance-chart-GBW");
    expect(chart).toHaveAttribute("data-domain", "0,8000000");
    expect(chart).toHaveAttribute("data-target", "5000000");
    expect(screen.getByText("4.18 MHz → 4.76 MHz")).toBeVisible();
    expect(screen.getByText("旧版图", { exact: true })).toHaveClass("old-legend");
    expect(screen.getByText("新版图", { exact: true })).toHaveClass("new-legend");
    expect(screen.getByText("重叠区域", { exact: true })).toHaveClass("overlap-legend");
  });
});
