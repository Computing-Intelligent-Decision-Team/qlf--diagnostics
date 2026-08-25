# PCS-Harness Workflow 可视化与 OTA 闭环实验设计

日期：2026-08-26

## 1. 目标

新建独立应用 `apps/pcs-harness-workflow`，用一个可重复的 `ota_core` 实验展示 PCS-Harness 从 L0 到 L6 的真实闭环。演示重点不是终端日志，而是结构化呈现以下能力：

1. Agent 阅读候选状态和验证证据，判断下一步动作；
2. Harness 校验并自动执行 Agent 的结构化决策；
3. GRPO 在固定偏置下搜索物理 MOS sizing；
4. PCS-Harness 生成并验证新版图，完成 DRC、LVS、PEX、后仿与 PVT；
5. 页面实时展示运行过程，完整事件记录用于审计，真实运行画面录制为视频后放入 PPT。

本设计不修改现有 `apps/analog-circuit-platform`。两个应用可共享品牌语言，但依赖、路由、构建和部署相互独立。

## 2. 成功标准

### 2.1 实验成功标准

- 使用 `ota_core` 和 `ota_voltage_bias_v1` measurement contract；
- 固定 `bias_voltage_v = 0.8 V`，不允许 GRPO 搜索 testbench bias；
- 第一版 GRPO action space 仅包含 MOS `W/NF`；
- 找到一个真实边界候选：前仿满足合同，DRC=0、LVS明确匹配，PEX有效，但后仿 GBW 低于 5 MHz；
- Agent 根据结构化证据选择 `run_grpo`；
- GRPO 输出至少一个物理 sizing 不同的候选；
- 新旧候选的 GDS hash 与 raw PEX 数据均不同；
- 新候选后仿 GBW 高于旧候选并达到 5 MHz；
- 增益不低于 15 dB、相位裕度不低于 60 度、功耗不高于 0.05；
- 最终候选通过 post-layout TT/SS/FF PVT，达到 `L6_post_layout_pvt`。

### 2.2 页面成功标准

- 实时展示 PCS-Harness 阶段、Agent 决策、GRPO group/candidate、版图检查点、DRC/LVS/PEX、后仿和 PVT；
- 所有画面来自持久化事件或可追溯派生数据，不依赖手工填写结果；
- 页面只支持真实运行时的实时展示，不设计离线回放模式；
- 第 N 轮和第 N+1 轮并列保存，页面不覆盖历史候选；
- 页面能以布局差异、寄生差异和性能差异解释闭环改进；
- 页面不展示私有 chain-of-thought，只展示可审计的观察、判断、动作和简洁理由。

## 3. 边界

### 3.1 Agent

Agent 只负责：

- 查看 DiagnosticReport 和已允许动作；
- 判断失败归属；
- 选择下一步动作；
- 输出 `reason_code` 和简洁 `rationale`。

Agent 不直接修改 sizing、网表、版图或 EDA 配置。

### 3.2 Harness

Harness 负责：

- 生成候选与证据包；
- 校验 Agent 决策与 report hash；
- 自动派发受允许的动作；
- 调用 GRPO 和 EDA 工具；
- 保持候选、事件和产物的可追溯关系。

### 3.3 GRPO

GRPO 负责在受限 action space 和性能合同下搜索物理 sizing。第一版允许：

- `input_pair_w`、`input_pair_nf`；
- `load_pmos_w`、`load_pmos_nf`；
- `tail_nmos_w`、`tail_nmos_nf`。

`L`、`multi` 和 `bias_voltage_v` 固定。只有在预扫描不能得到可复现实验时，才通过独立设计变更审查逐步开放其他物理参数。

### 3.4 EDA 工具

ngspice、MAGICAL、Magic、Netgen 和 PEX 流程产生事实证据。网页只解释和展示这些证据，不改变验证结论。

## 4. PCS-Harness 阶段模型

演示沿用 PCS-Harness closure 语义：

| Level | 实验事件 | 页面画面 |
| --- | --- | --- |
| L0 | candidate ingest、legalize、SPICE compile | sizing与合同卡片 |
| L1 | nominal pre-layout simulation | 前仿曲线与指标 |
| L2 | pre-layout TT/SS/FF PVT | 三个corner状态 |
| L3 | floorplan、placement、routing、final GDS | 真实GDS检查点逐步绘制 |
| L4 | GDS适配、DRC、extraction、LVS、raw PEX | 规则检查、连通性对比、寄生覆盖层 |
| L5 | nominal post-layout simulation | 前后仿曲线与违例 |
| L6 | post-layout TT/SS/FF PVT | 最终合同与L6总结 |

当前 PCS-Harness 的正式 closure evaluator 在物理部分可能由 L2 直接晋升到 L4。页面可以把真实 placement/routing checkpoint 呈现为 L3 过程，但不能在没有独立证据时把它误报成新的正式 closure 状态。

实验专用配置开启 `run_pre_layout_pvt`，确保 L2 具有真实证据。

## 5. 实验协议

### 5.1 固定运行环境

- PCS-Harness 基线：`be2937eb180c377dd8b918453d1ae96835769ef6`；
- AnalogGym-Opt 使用固定 checkout 和记录的 commit；
- Sky130A 使用固定版本目录并记录 sentinel hashes；
- Magic 使用 Harness 环境中的 8.3.486，满足配置要求 `>=8.3.411`；
- 记录 ngspice、Netgen、Docker image digest、Python版本和输入文件hash；
- 在独立 worktree 中开发，实验写入全新 run root，不修改历史候选。

### 5.2 边界候选扫描

第一层做低成本预扫描：

- 固定 bias、L、multi；
- 对 W/NF 生成约 32 个确定性候选；
- 运行 nominal pre-layout simulation；
- 保留增益、相位裕度和功耗通过，且 GBW 位于 5.2–6.0 MHz 的候选。

第二层做物理筛选：

- 从第一层选择约 6–8 个候选；
- 对每个候选执行完整 layout、DRC、LVS、PEX 和 post-layout simulation；
- 选择满足前仿 GBW >= 5 MHz、后仿 GBW < 5 MHz 的候选；
- 候选必须满足 DRC=0、LVS match、raw PEX非空且R/C可解析；
- 如有多个候选，优先选择后仿 GBW 为 4.0–4.9 MHz 且其他指标仍通过者。

扫描只用于选择可复现的初始条件，不作为正式录屏过程。

### 5.3 正式录制运行

- 固定边界候选、GRPO checkpoint/config和随机种子；
- GRPO 默认每组 4 个候选，目标 2 组，最多 3 组；
- 每个真实 candidate、group-relative reward和policy update均产生事件；
- 找到符合合同的候选后，由 Harness提升候选并重新完成物理闭环；
- 停止条件为 L6且 `performance_feasible=true`，或达到候选、group、layout、runtime预算；
- 失败必须保留失败证据和明确终止原因，不得静默替换成预设成功数据。

## 6. 数据与目录

### 6.1 原始事实来源

```text
/home/qlf/IOT/generated/analog_harness/ota_core_grpo_demo_20260826/
├── runtime/
├── boundary_scan/
│   ├── pre_layout/
│   ├── physical_screen/
│   └── selection.json
├── recording_run/
│   ├── cand_*/
│   ├── optimizer/
│   ├── agent_decisions/
│   └── feedback_trace.json
├── events/run_events.jsonl
├── timing/
├── visualization/
└── final_report/
```

候选目录保持 PCS-Harness 原生格式。任何展示派生物都引用原始文件路径和hash。

### 6.2 独立应用

```text
/home/qlf/IOT/apps/pcs-harness-workflow/
├── src/
├── public/
├── tests/
└── dist/
```

`public/` 只保存应用自身的静态资产，不复制实验候选、GDS、PEX网表或离线demo run。页面录制时直接连接当次 PCS-Harness 运行。

### 6.3 可信导出

只有候选独立满足 sizing lineage、DRC=0、LVS match、raw PEX存在且R/C可解析后，才生成只读导出和 tar.gz。PVT与性能结果作为观察字段，不替代寄生样本信任条件。

## 7. 事件与实时更新

所有组件写入统一事件封装：

```json
{
  "schema_version": "pcs_harness_workflow_event.v1",
  "run_id": "ota_core_grpo_demo_20260826",
  "candidate_id": "cand_0007",
  "source": "harness",
  "event_type": "stage.completed",
  "stage": "post_sim",
  "sequence": 142,
  "occurred_at": "2026-08-26T00:00:00Z",
  "elapsed_ms": 1832,
  "payload": {},
  "artifact_refs": []
}
```

要求：

- `sequence` 在单个 run 内严格递增；
- 事件先追加写入 JSONL，再通过 SSE推送；
- 页面断线后用最后 sequence 补读，不丢事件；
- 页面时间轴只使用真实 `occurred_at`，不插入人工延时；
- JSONL用于证据审计和实时页面断线重连，不对用户提供回放控件。

## 8. 可视化设计

### 8.1 主界面

- 顶部：run id、当前候选、总耗时和L0–L6状态；
- 主舞台：当前阶段的版图、曲线或寄生覆盖层；
- 证据面板：Agent看到的指标、验证状态和artifact引用；
- 决策面板：观察摘要、失败归属、动作和理由；
- GRPO面板：group、candidate、reward、约束和policy update；
- 底部：第N轮与第N+1轮的指标趋势和目标线。

### 8.2 版图动画

使用真实 `floorplan.gds`、`place.gds`、`route.gds`、final/pinned GDS，并在同一坐标系中渲染。若当前 router 不产生内部迭代checkpoint，页面只能标为“路由结果逐层展示”，不能声称为router真实搜索轨迹。

DRC marker必须来自真实坐标。DRC-clean候选展示规则扫描和最终0 violations，不虚构错误。

### 8.3 寄生覆盖层

- 从 Magic `.ext` 读取 node代表坐标和cap端点；
- 从 raw PEX SPICE读取后仿实际使用的电容值；
- 对地寄生显示为节点光圈，耦合寄生显示为节点间曲线；
- 默认显示Top 10和VOUT相关寄生；
- 线宽采用对数缩放；
- 点击覆盖层显示原始netlist行和artifact hash。

`.ext` node坐标是网络代表坐标，不是分布式寄生的精确几何中心。页面必须使用“net-anchored parasitic overlay”口径。

### 8.4 迭代对比

第N轮和第N+1轮分别保留：

- sizing diff；
- GDS overlay/diff；
- PEX节点和电容差异；
- 前仿、后仿和PVT指标；
- Agent决策和GRPO候选来源。

旧版图用红色，新版图用青色，重叠区域用中性灰。性能图使用固定目标线，禁止通过改变坐标尺度夸大改善。

## 9. 计时口径

每个阶段用 monotonic wall-clock 计时，并保存UTC开始/结束时间：

| 计时项 | 起点 | 终点 |
| --- | --- | --- |
| L0 | 候选进入Harness | SPICE candidate compile完成 |
| L1 | nominal pre-layout启动 | 指标packet完成 |
| L2 | pre-layout PVT启动 | 三个corner聚合完成 |
| L3 | layout pipeline启动 | final GDS生成 |
| DRC | Magic DRC启动 | DRC结果解析完成 |
| LVS | Netgen启动 | connectivity结果解析完成 |
| PEX | Magic extraction启动 | raw PEX与summary完成 |
| Agent | DiagnosticReport冻结 | validated decision落盘 |
| GRPO candidate | candidate evaluation启动 | reward可用 |
| GRPO group | group sampling启动 | policy update完成 |
| L5 | nominal post-layout启动 | 指标packet完成 |
| L6 | post-layout PVT启动 | 三个corner聚合完成 |
| Total | 首个L0事件 | 最终L6或终止事件 |

输出：

- `timing/stage_timing.json`：完整机器可读记录；
- `timing/stage_timing.csv`：每阶段、每候选、每corner；
- `timing/timing_report.md`：总时间、均值、中位数、范围和录屏加速建议。

历史 `final_v3` 的269.452秒/3候选只作为约89.8秒/完整候选的粗基线，不用于伪造分阶段时间。正式估计必须来自本次彩排。

## 10. 错误处理

- 环境或版本不匹配时产生 `runtime_blocked`，不计为电路失败；
- GRPO候选非法时保留legalization/拒绝原因，不静默裁剪；
- DRC/LVS/PEX缺失或含糊时候选不得进入可信导出；
- Agent决策不在allowed actions、candidate/report hash不匹配时拒绝执行；
- SSE断线不影响原始运行，页面从JSONL恢复；
- 达到预算仍未闭环时如实输出失败总结，不切换到预录成功值。

## 11. 验证策略

- 事件schema、sequence和实时状态reducer单元测试；
- Agent decision closed schema与stale hash拒绝测试；
- GRPO action space测试，确保bias、L和multi不可变；
- 阶段计时嵌套与总时间一致性测试；
- GDS checkpoint解析和同坐标系渲染测试；
- `.ext`/raw SPICE寄生解析交叉核对；
- 信任合同测试：DRC、LVS或raw PEX任一缺失必须拒绝导出；
- SSE断线重连后根据sequence补读事件的一致性测试；
- 前端组件测试、生产构建和录屏分辨率视觉检查；
- 最终使用一次全新run root完成端到端彩排。

## 12. 非目标

- 不修改现有模拟芯片设计服务网站；
- 不开发离线回放、播放速度或预置demo run功能；
- 不构建浏览器版图编辑器；
- 不显示Agent私有chain-of-thought；
- 不宣称完整foundry signoff；
- 不将MOS-only connectivity LVS表述为property-level/passive-aware signoff；
- 不把展示动画时间当作真实EDA运行时间；
- 不把预设sizing恢复冒充GRPO搜索结果。
