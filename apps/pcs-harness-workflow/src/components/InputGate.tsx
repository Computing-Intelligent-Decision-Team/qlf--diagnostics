import { useEffect, useId, useMemo, useState } from "react";

import type { CircuitType, ParseResult, RunSummary } from "../api/workflowApi";

export interface WorkflowApi {
  getCircuitTypes(): Promise<CircuitType[]>;
  parseNetlist(circuitType: string, file: File): Promise<ParseResult>;
  startRun(parseId: string): Promise<RunSummary>;
}

interface InputGateProps {
  api: WorkflowApi;
  onRunStarted: (run: RunSummary) => void;
}

type BusyState = "idle" | "parsing" | "starting";

const preflightCopy: Record<string, string> = {
  verified_ota_ready: "输入与已验证 OTA 基线一致",
  verified_input_hash_mismatch: "网表已解析，但与已验证 OTA 基线不一致",
  verified_top_cell_mismatch: "顶层电路与已验证 OTA 基线不一致",
  circuit_type_not_demo_ready: "该类型可解析，当前自动闭环仅绑定已验证的 OTA 基线",
};

export function InputGate({ api, onRunStarted }: InputGateProps) {
  const typeId = useId();
  const fileId = useId();
  const [types, setTypes] = useState<CircuitType[]>([]);
  const [circuitType, setCircuitType] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [parsed, setParsed] = useState<ParseResult | null>(null);
  const [busy, setBusy] = useState<BusyState>("idle");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api
      .getCircuitTypes()
      .then((items) => active && setTypes(items))
      .catch((reason: Error) => active && setError(reason.message));
    return () => {
      active = false;
    };
  }, [api]);

  const selectedType = useMemo(
    () => types.find((item) => item.id === circuitType),
    [circuitType, types],
  );
  const canParse = Boolean(circuitType && file && busy === "idle");
  const canStart = Boolean(parsed?.preflight.ready && busy === "idle");

  function resetEvidence() {
    setParsed(null);
    setError("");
  }

  async function parse() {
    if (!file || !circuitType) return;
    setBusy("parsing");
    setError("");
    try {
      setParsed(await api.parseNetlist(circuitType, file));
    } catch (reason) {
      setParsed(null);
      setError(reason instanceof Error ? reason.message : "网表解析失败");
    } finally {
      setBusy("idle");
    }
  }

  async function start() {
    if (!parsed?.preflight.ready) return;
    setBusy("starting");
    setError("");
    try {
      onRunStarted(await api.startRun(parsed.parse_id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "闭环启动失败");
      setBusy("idle");
    }
  }

  const mosCount = parsed?.netlist.device_counts.M ?? 0;

  return (
    <main className="input-shell">
      <section className="intro-panel" aria-labelledby="workflow-title">
        <div className="eyebrow"><span /> PCS-HARNESS / AUTONOMOUS CLOSURE</div>
        <h1 id="workflow-title">从电路描述<br />走向物理验证</h1>
        <p className="intro-copy">
          Agent 阅读每一阶段的真实证据，判断下一步动作；GRPO 负责 MOS sizing 搜索，
          EDA 工具链完成版图与签核验证。
        </p>
        <ol className="scope-list">
          <li><span>L0—L2</span><strong>电路编译与前仿真</strong></li>
          <li><span>L3—L4</span><strong>版图、DRC / LVS / PEX</strong></li>
          <li><span>L5—L6</span><strong>后仿真与 PVT 收敛</strong></li>
        </ol>
        <div className="system-line">
          <span className="live-dot" /> SKY130 TOOLCHAIN READY
          <span>BIAS 0.80 V · W/NF SEARCH</span>
        </div>
      </section>

      <section className="gate-panel" aria-labelledby="gate-title">
        <div className="gate-heading">
          <div>
            <span className="section-index">DESIGN INPUT</span>
            <h2 id="gate-title">启动自主设计闭环</h2>
          </div>
          <div className="step-count">01 <span>/ 03</span></div>
        </div>

        <div className="form-stack">
          <div className="field-group">
            <label htmlFor={typeId}>电路类型</label>
            <div className="select-wrap">
              <select
                id={typeId}
                value={circuitType}
                onChange={(event) => {
                  setCircuitType(event.target.value);
                  resetEvidence();
                }}
              >
                <option value="">选择 PCS-Harness 支持的类型</option>
                {types.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}{item.demo_ready ? " · 完整闭环" : " · 解析支持"}
                  </option>
                ))}
              </select>
              <span aria-hidden="true">⌄</span>
            </div>
            {selectedType && (
              <p className="field-hint">
                {selectedType.demo_ready
                  ? `已绑定 ${selectedType.design_profiles.join(", ")} 验证配置`
                  : `已识别 ${selectedType.design_profiles.length} 个配置；当前提供结构解析`}
              </p>
            )}
          </div>

          <div className="field-group">
            <label htmlFor={fileId}>上传 SPICE 网表</label>
            <label
              className={`file-drop ${file ? "has-file" : ""}`}
              htmlFor={fileId}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                setFile(event.dataTransfer.files[0] ?? null);
                resetEvidence();
              }}
            >
              <input
                id={fileId}
                type="file"
                accept=".sp,.spice,.cir"
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  resetEvidence();
                }}
              />
              <FileGlyph />
              <span className="file-primary">{file ? file.name : "选择或拖入电路网表"}</span>
              <span className="file-secondary">
                {file ? `${formatBytes(file.size)} · 等待解析` : ".sp  /  .spice  /  .cir · 最大 2 MB"}
              </span>
              <span className="file-action">{file ? "重新选择" : "浏览文件"}</span>
            </label>
          </div>

          <button className="secondary-action" type="button" disabled={!canParse} onClick={parse}>
            <span>{busy === "parsing" ? "正在解析电路结构…" : "解析并预检"}</span>
            <ArrowGlyph />
          </button>

          {parsed && <ParseEvidence parsed={parsed} mosCount={mosCount} />}
          {error && <div className="error-banner" role="alert">{error}</div>}

          <button className="primary-action" type="button" disabled={!canStart} onClick={start}>
            <span className="button-led" />
            {busy === "starting" ? "正在建立运行环境…" : "开始设计闭环"}
            <ArrowGlyph />
          </button>
        </div>

        <p className="gate-footnote">
          启动后，Agent 将基于实时验证结果自主选择下一阶段；所有指标均来自运行产物。
        </p>
      </section>
    </main>
  );
}

function ParseEvidence({ parsed, mosCount }: { parsed: ParseResult; mosCount: number }) {
  const ready = parsed.preflight.ready;
  return (
    <div className={`parse-evidence ${ready ? "is-ready" : "is-limited"}`} aria-live="polite">
      <div className="evidence-title">
        <span className="status-symbol">{ready ? "✓" : "!"}</span>
        <div>
          <strong>{preflightCopy[parsed.preflight.code] ?? parsed.preflight.code}</strong>
          <small>NETLIST PREFLIGHT / {ready ? "PASSED" : "LIMITED"}</small>
        </div>
      </div>
      <div className="evidence-metrics">
        <span><small>TOP CELL</small><b>{parsed.netlist.top_cell}</b></span>
        <span><small>INTERFACE</small><b>{parsed.netlist.ports.length} ports</b></span>
        <span><small>DEVICES</small><b>{mosCount} MOS</b></span>
        <span><small>SHA-256</small><b>{parsed.netlist.sha256.slice(0, 10)}…</b></span>
      </div>
    </div>
  );
}

function FileGlyph() {
  return (
    <svg className="file-glyph" viewBox="0 0 36 42" aria-hidden="true">
      <path d="M5 1h17l9 9v31H5z" />
      <path d="M22 1v10h9M11 20h14M11 26h14M11 32h9" />
    </svg>
  );
}

function ArrowGlyph() {
  return <span className="arrow-glyph" aria-hidden="true">→</span>;
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}
