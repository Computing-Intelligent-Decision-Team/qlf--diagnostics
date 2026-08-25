# AnalogHarness 可信寄生数据导出 Skill 设计

## 目标

创建可移植的 Codex skill `analog-harness-parasitic-export`。安装后，使用者只需调用
`$analog-harness-parasitic-export`，Codex 即可扫描指定时间窗口内的 AnalogHarness/PCS
候选，重新判定可信寄生标签，复制证据并生成带清单和校验和的压缩包。

## 核心契约

可信正样本必须同时满足：

1. sizing 来源链可追溯到候选网表及版图产物；
2. DRC 明确 PASS；
3. connectivity LVS 明确 PASS；
4. raw PEX 文件存在、非空且可解析出寄生 R/C 元件。

PM、reward、前仿、PVT 和后仿性能只记录，不参与正样本筛选。DRC/LVS/PEX
失败或证据不完整的候选进入拒绝清单，不得混入监督回归正样本。当前若采用 MOS-only
投影，清单必须标明验证范围，不得声称 property-level 或 native-passive signoff。

## 输入与发现

- 默认时间窗口为执行时刻向前 7 天；支持显式 `--since`、`--until`。
- 接受一个或多个 `--root`；未指定时从当前仓库及常见 `generated/analog_harness`
  路径发现候选。
- 以 `state.json` 的 evidence 时间为主、文件时间为后备，目录名仅用于发现，不能证明 L6。
- 默认只读源数据；复制到独立 staging 目录，不移动、不删除、不改写原实验。

## 输出

输出目录包含 `trusted_candidates/`、`MANIFEST.json`、`candidates.csv`、
`rejected_candidates.csv`、`duplicate_groups.json`、`README.md` 和 `SHA256SUMS`，随后生成
`.tar.gz`。每条记录保存身份、时间、closure、验证范围、DRC/LVS/PEX 判定、拒绝原因、
关键产物路径与 SHA-256。重复样本保留并分组，不静默去重。

## 安全边界

- 不读取或打包凭据、许可证、套接字、锁文件和缓存。
- 默认只复制可信正样本的完整候选目录；拒绝样本只写清单，除非用户显式要求失败证据包。
- skill 负责生成压缩包与路径；上传或发送只有在目标和工具已获授权时执行。
- 任一可信性条件无法从证据证明时，结论必须是 rejected/unknown，不得猜测 PASS。

## 交付

- qlf 仓库源码：`references/codex-skills/analog-harness-parasitic-export/`
- 可安装包：`references/codex-skills/dist/analog-harness-parasitic-export.tar.gz`
- 测试覆盖：时间筛选、可信门槛、性能字段非门槛、PEX 解析、拒绝原因、复制与归档校验。
