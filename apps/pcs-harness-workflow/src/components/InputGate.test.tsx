import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { InputGate, type WorkflowApi } from "./InputGate";

const circuitTypes = [
  {
    id: "ota",
    name: "运算跨导放大器（OTA）",
    supported: true,
    demo_ready: true,
    design_profiles: ["ota_core"],
  },
  {
    id: "inverter",
    name: "反相器",
    supported: true,
    demo_ready: false,
    design_profiles: ["inverter_core"],
  },
];

function readyParse() {
  return {
    parse_id: "parse_001",
    circuit_type: "ota",
    filename: "ota_core.sp",
    netlist: {
      top_cell: "ota_core",
      ports: ["VINP", "VINM", "IB", "VDD", "VOUT", "GND"],
      device_counts: { M: 5 },
      sha256: "a".repeat(64),
      size_bytes: 512,
    },
    preflight: { ready: true, code: "verified_ota_ready" },
    binding: {
      design_id: "ota_core",
      profile_path: "/pcs/configs/ota_core_workflow_demo.yaml",
      profile_sha256: "b".repeat(64),
      verified_netlist_sha256: "a".repeat(64),
    },
  };
}

describe("InputGate", () => {
  it("progresses from type selection through verified preflight before closure starts", async () => {
    const user = userEvent.setup();
    const api: WorkflowApi = {
      getCircuitTypes: vi.fn().mockResolvedValue(circuitTypes),
      parseNetlist: vi.fn().mockResolvedValue(readyParse()),
      startRun: vi.fn().mockResolvedValue({ run_id: "run_001", status: "running" }),
    };
    render(<InputGate api={api} onRunStarted={vi.fn()} />);

    await screen.findByRole("option", { name: /运算跨导放大器/ });
    expect(screen.getByRole("button", { name: "解析并预检" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "开始设计闭环" })).toBeDisabled();

    await user.selectOptions(screen.getByLabelText("电路类型"), "ota");
    const file = new File(["subckt ota_core VINP VINM IB VDD VOUT GND"], "ota_core.sp", {
      type: "text/plain",
    });
    await user.upload(screen.getByLabelText("上传 SPICE 网表"), file);
    expect(screen.getByRole("button", { name: "解析并预检" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "开始设计闭环" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "解析并预检" }));
    expect(await screen.findByText("ota_core")).toBeVisible();
    expect(screen.getByText("6 ports")).toBeVisible();
    expect(screen.getByText("5 MOS")).toBeVisible();
    expect(screen.getByText("输入与已验证 OTA 基线一致")).toBeVisible();
    expect(screen.getByRole("button", { name: "开始设计闭环" })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "开始设计闭环" }));
    await waitFor(() => expect(api.startRun).toHaveBeenCalledWith("parse_001"));
  });

  it("shows supported non-demo types without presenting them as closure-ready", async () => {
    const user = userEvent.setup();
    const api: WorkflowApi = {
      getCircuitTypes: vi.fn().mockResolvedValue(circuitTypes),
      parseNetlist: vi.fn().mockResolvedValue({
        ...readyParse(),
        circuit_type: "inverter",
        preflight: { ready: false, code: "circuit_type_not_demo_ready" },
      }),
      startRun: vi.fn(),
    };
    render(<InputGate api={api} onRunStarted={vi.fn()} />);

    await user.selectOptions(await screen.findByLabelText("电路类型"), "inverter");
    await user.upload(
      screen.getByLabelText("上传 SPICE 网表"),
      new File([".subckt inverter A Y VDD GND"], "inverter.spice"),
    );
    await user.click(screen.getByRole("button", { name: "解析并预检" }));

    expect(await screen.findByText("该类型可解析，当前自动闭环仅绑定已验证的 OTA 基线")).toBeVisible();
    expect(screen.getByRole("button", { name: "开始设计闭环" })).toBeDisabled();
    expect(api.startRun).not.toHaveBeenCalled();
  });
});
