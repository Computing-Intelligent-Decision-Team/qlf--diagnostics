# IOT — 模拟集成电路智能设计工作区

本工作区用于 AI 驱动的模拟/混合信号 IC 设计研究，当前主线是把自然语言规格、输入网表、LLM 生成电路和前端优化结果逐步连接到版图生成、DRC/LVS/PEX、前后仿 Harness 和 reward 反馈。

核心链路不是固定绑定某一个版图生成器，而是围绕一个可替换的 layout backend abstraction 展开：当前可实验 Native/GLayout 自建生成器，也保留 MAGICAL/Magic 系列、ALIGN 等后端路线。最终目标是形成“网表/规格输入 -> 电路生成与参数优化 -> 版图生成 -> 物理验证 -> 后仿反馈 -> 上游修正”的闭环。

高层链路：

```text
spec / netlist / LLM circuit
-> circuit reasoning and repair
-> frontend sizing optimization
-> constraint and candidate adapter
-> pluggable layout backend
-> DRC/LVS/PEX
-> post-layout simulation
-> reward / report / feedback
```

## 端到端任务闭环

### 1. 输入与意图层：Specification / Netlist Ingestion

这一层回答“用户到底给了什么、想要什么”。

可能输入：

- 自然语言规格：例如“设计一个 100 dB 运放”“给出一个低功耗 OTA”。
- 已有网表：SPICE、PySpice、Xschem / X-Gemini 导出的 netlist。
- LLM 生成电路：由 AnalogCoderPro 或其他 LLM Agent 生成的 PySpice / SPICE 代码。
- 约束与工艺：例如 Sky130、VDD、输入/输出节点、bias、`nf/finger=2`、哪些参数允许优化。
- 测试目标：DC、AC、transient、PVT、gain、bandwidth、phase margin、power、area、FOM。

如果用户输入的是自然语言，这一层会整理成标准化 design task；如果用户直接输入网表，则不会从零生成拓扑，而是进入网表接收、端口识别、模型检查、testbench 绑定和参数抽取。

典型产物：

```text
design_task:
  circuit_type
  input_nodes / output_nodes
  supply / bias assumptions
  target_metrics
  process / PDK
  fixed_constraints
  optimizable_parameters
  simulation_plan
```

### 2. 电路推理层：LLM / AnalogCoderPro

这一层回答“能不能把输入变成可运行、可仿真、可优化的电路表示”。

当输入是自然语言规格时，AnalogCoderPro / LLM Agent 负责：

- 根据 prompt 生成电路拓扑说明。
- 生成可运行 PySpice / SPICE 代码。
- 保证输入输出节点、供电、bias、器件连接存在。
- 调用仿真检查基础功能。

当输入已经是网表时，这一层不再做 topology generation，而是做：

- 网表结构理解：识别差分对、电流镜、负载、补偿电容、bias 网络等。
- 仿真诊断：检查 floating node、模型缺失、端口不一致、工作点失败、语法错误。
- 错误反馈：把仿真错误转化为 LLM repair prompt，重新生成或修补电路。
- 参数化：把固定 `W/L/M/R/C/bias` 提取为 `params`，生成搜索空间和初始值。
- 语义约束：区分 `M`、`nf/finger`、并联器件、版图展开方式，避免前后仿语义错位。

典型产物：

```text
create_circuit(params)
initial_params
param_ranges_definition
simulation_check_result
netlist_diagnosis
repair_log
```

### 3. 前端优化层：AnalogGym-Opt / GRPO Sizing

这一层回答“在给定拓扑和参数空间下，哪些 sizing 候选更好”。

主要工具：

- `analoggym-opt代码/`
- `ngspice`
- GRPO / RL sizing 逻辑
- circuit config、simulation files、training saves

核心职责：

- 调用 ngspice 做前仿。
- 搜索 `W/L/M`、bias、补偿参数等连续/离散变量。
- 输出候选设计、reward 和性能指标。
- 保持参数语义清晰：例如当前会议约束中，`M` 仍是 multiplier / 优化变量，`nf/finger` 固定为 2。

典型产物：

```text
candidate:
  action_real / real_action
  parameter_names
  reward
  performance
  objective_rewards
  simulation_log
```

### 4. 候选适配层：Candidate Adapter / Constraint IR

这一层回答“优化器输出怎么喂给不同版图生成器”。

这一层非常关键，因为 AnalogGym-Opt 的候选参数不能直接等同于版图工具配置。它需要一个中间表示，把电路参数、约束和后端要求拆开。

主要职责：

- 将 `action_real` 映射到器件参数：`W/L/M/nf/R/C/bias`。
- 固化前后仿一致性约束：例如 `nf=2`、差分对匹配、电流镜匹配、对称性。
- 生成不同 layout backend 需要的配置文件。
- 记录哪些字段来自优化器，哪些字段来自会议约束/工艺约束。

推荐抽象：

```text
candidate JSON
-> normalized circuit parameter IR
-> constraint IR
-> backend-specific layout config
```

后端配置可以分别面向：

- Native/GLayout 自建 Python 版图生成器。
- MAGICAL/Magic 系列流程。
- ALIGN 自动版图流程。
- 后续可能接入的商业 EDA 或 Virtuoso bridge。

### 5. 版图生成层：Pluggable Layout Backend

这一层回答“如何把候选参数变成真实版图/GDS”。

当前不应把流程写死为 Native。根据 5.17 会议记录，后端路线应保持三类角色：

- **Native/GLayout-backed generator**：适合自定义模板、快速验证、精细控制 `W/L/M/nf` 映射、reward 试验。
- **MAGICAL/Magic 系列路线**：适合探索从网表到 GDS 的自动生成、Magic DRC/LVS/PEX 工具链和 PDK 层映射。
- **ALIGN**：适合作为自动版图 baseline 和约束驱动布局参考，尤其用于对比现有开源 analog layout automation。

这一层的输入不是“自然语言”，而应该是候选适配层生成的 backend-specific config。

典型产物：

```text
layout output:
  gds
  layout netlist
  generated spice
  placement/routing metadata
  backend logs
```

### 6. 物理验证层：DRC / LVS / PEX

这一层回答“生成出来的版图在物理和电气上是否成立”。

主要验证：

- DRC：检查是否违反工艺规则。
- LVS：检查版图提取网表是否与参考网表等价。
- PEX：提取寄生电阻、电容和后仿 netlist。

会议中反复强调的风险是：前仿网表和版图提取网表可能存在语义不一致。例如 `nf=2` 在原理图中是抽象参数，但 Magic / PEX 后可能展开成多个实际 MOS 段，导致前后仿口径不同。因此这层不仅要看“过没过”，还要记录前后网表语义差异。

典型产物：

```text
drc_report
lvs_report
pex_netlist
extracted_layout_netlist
semantic_diff_report
```

### 7. 后仿与反馈层：Post-layout Harness / Reward

这一层回答“版图实现后，性能是否还满足目标，以及失败原因如何反馈给上游”。

主要职责：

- 使用 PEX netlist 做 post-layout simulation。
- 对比前仿与后仿：gain、bandwidth、phase margin、power、area、FOM 等。
- 将 DRC/LVS/PEX/post-sim 结果转成 reward、报告和可视化证据。
- 把失败原因反馈给：
  - LLM / AnalogCoderPro：修复网表、bias、拓扑或 testbench。
  - AnalogGym-Opt：调整参数搜索范围、reward 权重或约束。
  - Candidate Adapter：修正 `M/nf`、匹配、对称、展开语义。
  - Layout Backend：修正模板、层映射、器件生成逻辑。

最终闭环：

```text
input spec / netlist
-> LLM circuit reasoning
-> frontend optimization
-> candidate adapter
-> layout backend
-> DRC/LVS/PEX
-> post-layout simulation
-> reward and diagnosis
-> feedback to LLM / optimizer / constraints / backend
```

## 主线工程

| 目录 | 定位 | 说明 |
|---|---|---|
| `references/MAGICAL-/` | MAGICAL Sky130 baseline | 师兄 MAGICAL fork；当前版图生成与验证主线。 |
| `agent_workflow/` | Agent 任务编排 | workstream、task DAG、execution log、验证命令。 |
| `.github/skills/` | 可复用领域 workflow | EDA research、analog layout closure、debugging、visualization 等 skill。 |
| `docs/` | 文档与证据 | meetings、weekly、papers、learning、experiments、figures、plans 等。 |
| `plans/` | 长期记忆层 | 项目上下文、路线图、架构决策、当前 workstream 索引。 |
| `scripts/` | 通用脚本 | ngspice parser、plot、doctor 等辅助工具。 |

## 外部参考与前端来源

详细索引见 `EXTERNALS.md`。

| 目录/文件 | 定位 | 当前用途 |
|---|---|---|
| `AnalogCoderPro/` | LLM natural-language-to-circuit frontend | 自然语言需求到 PySpice/初始拓扑/修复循环的参考入口。 |
| `analoggym-opt代码/` | AnalogGym-Opt / GRPO sizing frontend | 师兄发来的前端 sizing 优化代码包。 |
| `docs/papers/AnalogGym-Opt.pdf` | AnalogGym-Opt 论文 | 解释 GRPO sizing、PVT-aware search、structured electrical records。 |
| `virtuoso-bridge-lite/` | Virtuoso automation | 独立相关项目，用于 Cadence Virtuoso Agent 控制。 |

## 学习与历史材料

| 目录 | 定位 |
|---|---|
| `MyLearning/` | 已于 2026-08-26 清空，不再作为工作入口。 |
| `PreviousProjects/` | 已于 2026-08-26 清空，不再作为工作入口。 |
| `Others'Projects/` | 已于 2026-08-27 清空，不再作为工作入口。 |
| `LLM/` | 已于 2026-08-27 清空；未来 Agent/LoRA 工具链需要时重新拉取，不保留旧本地副本。 |
| `.archive/` | 根目录清理归档，不作为当前工作入口。 |

已清空的第三方/旧参考项目：`OpenFASOC/`、`references/ALIGN-public/`、
`BBOPlace-Bench/`、`AncstrGNN_benchmark/`、`Others'Projects/`、`LLM/`。删除清单见
`archives/deleted_third_party_personal_20260826_manifest.txt`。

## 当前重点 workstream

```text
agent_workflow/workstreams/2026-05-18_constraint_extraction_harness_workflow/
```

该 workstream 将 5.17 会议共识整理为：

- MAGICAL / ALIGN / Native 三后端角色；
- constraint IR 草案；
- Harness 输入输出契约；
- skill / harness / config / workstream 分层；
- 组会沟通稿。

## 快速入口

Agent 上下文包：

```bash
npx repomix --config repomix.config.json
```

默认生成 `docs/context/generated/iot-core-pack.xml`。该文件只作为当前会话或 handoff 输入，不提交到 Git。更多场景见 `docs/context/repomix_context_guide.md`。

MAGICAL Sky130 环境：

```bash
source scripts/env/magical_sky130_env.sh
bash scripts/env/check_magical_sky130_env.sh
```

前端优化参考：

```bash
cd "analoggym-opt代码/Analoggym_opt_moo_Mahalanobis_paper"
python main_AMP_grpo.py
```

AnalogCoderPro 参考：

```bash
cd AnalogCoderPro
python run.py --task_id=19 --num_per_task=3 --model=gpt-5-mini
```

## 整理原则

- 主线工程留在根目录，外部独立 Git 仓库不强行移动。
- 散落论文进入 `docs/papers/`，散落日志/输出进入 `.archive/`。
- `plans/` 记录长期上下文，`agent_workflow/` 记录具体执行状态。
- 退役路线的经验材料进入 `docs/_archive/`；活跃主线只保留当前会继续运行和维护的工程。

最后更新：2026-05-20
