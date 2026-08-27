# Execution Log

### 2026-08-26 04:28 CST | T001-T003

- action: 对 IOT 顶层和 `references/` 做只读盘点；采用非破坏性导航层重构，创建 `projects/`、`datasets/`、`experiments/`、`external/`、`archives/`，并用软链接暴露当前核心代码仓库、正式 DFCFC2 数据集和关键实验输出。
- decision: 不直接移动 `references/pcs-harness-align-origin-main-20260815`，因为 PCS/GRPO 实验产物中存在大量绝对路径和哈希血缘；物理迁移会让历史 manifest 与 audit report 的可追溯性变差。
- result: 新日常入口为 `WORKSPACE.md`、`projects/pcs-harness-main`、`datasets/dfcfc2_parasitic/current`、`experiments/dfcfc2_grpo/step300_pool100_pcs`。`references/` 被明确降级为 provenance storage。
- artifact: `WORKSPACE.md`；`projects/README.md`；`datasets/README.md`；`datasets/dfcfc2_parasitic/README.md`；`experiments/README.md`；本 workstream。
- verify: 链接 resolve 检查全部存在；`datasets/dfcfc2_parasitic/current/dataset.json` 可读且为 95 个样本、27 维 sizing；`WORKSPACE.md` 与各 README 存在；`git diff --check` 退出 0。

### 2026-08-26 04:36 CST | T004

- action: 对 `references/.codex-archives`、`references/.codex-worktrees`、`references/.codex-trash`、`references/.codex-envs`、`references/.codex-backups` 做瘦身前盘点，检查大小、最近修改、Git worktree 注册状态和当前文档引用。
- result: 可疑空间约 8.0G：`.codex-archives` 6.7G、`.codex-worktrees` 901M、`.codex-trash` 210M、`.codex-envs` 249M、`.codex-backups` 36K。`.codex-worktrees/pcs-harness-workflow` 与 `.codex-worktrees/analoggym-dfcfc2-grpo-checkpoint` 是注册 worktree；`pcs-harness-workflow` 与 `patent-min-cause-replay` 存在脏状态，不能直接删除。最低风险物理清理候选是 `.codex-trash/grpo_batch_v4_0009_partial_20260822`；最大空间候选是 `.codex-archives/AnalogHarness-retired-20260809`。
- artifact: `WORKSPACE_CLEANUP_PLAN.md`。
- verify: `du -sh`、`git worktree list --porcelain`、`git -C <worktree> status --short`、`rg` 引用检查完成；本轮未删除任何目录。

### 2026-08-26 04:43 CST | T005

- action: 按最低风险策略处理 `references/.codex-trash/grpo_batch_v4_0009_partial_20260822`：生成原文件 SHA256 manifest 与 filelist，创建 tar.gz 归档，校验压缩包，再把原目录从 `.codex-trash` 移到 `archives/codex-trash-20260826/holding/`。
- result: `.codex-trash` 变为空目录；原始 141 个文件仍保留在 holding 中，大小 210M；压缩包大小 24M，归档 SHA-256 为 `9a2564285c5e7e2007937ed22d52ba49b7130c49b8f04997335639faf0cbdb34`。本轮没有做不可恢复删除，因此尚未释放 holding 占用的 210M；后续确认后可删除 holding 以释放空间。
- artifact: `archives/codex-trash-20260826/README.md`；`archives/codex-trash-20260826/grpo_batch_v4_0009_partial_20260822.tar.gz`；`archives/codex-trash-20260826/grpo_batch_v4_0009_partial_20260822.files.sha256`；`archives/codex-trash-20260826/holding/grpo_batch_v4_0009_partial_20260822/`。
- verify: `gzip -t` 退出 0；`sha256sum -c` 显示 archive OK；`tar -tzf` 可列出原始 `references/.codex-trash/...` 路径；holding 文件数 141；`.codex-trash` 无子项。

### 2026-08-26 05:34 CST | T006

- action: 用户确认后，删除 `archives/codex-trash-20260826/holding/grpo_batch_v4_0009_partial_20260822` 中已归档内容；删除前再次执行 `sha256sum -c` 与 `gzip -t` 校验压缩包。
- result: holding 大部分内容已删除，`references/.codex-trash` 仍为空；完整可恢复副本保留为 24M 的 `grpo_batch_v4_0009_partial_20260822.tar.gz`。当前仍剩 26 个 root-owned GDS 文件，约 9.2M，位于 holding 残留目录内；非交互 `sudo -n` 因需要密码失败，因此未强制删除这 9.2M。
- artifact: `archives/codex-trash-20260826/README.md` 更新为“压缩包为完整可恢复副本，holding 仅为权限残留”。
- verify: `sha256sum -c archives/codex-trash-20260826/grpo_batch_v4_0009_partial_20260822.tar.gz.sha256` 显示 OK；`gzip -t` 退出 0；`find references/.codex-trash -mindepth 1 -maxdepth 1` 计数为 0；holding 残留文件数为 26，大小 9.2M；`du -sh archives/codex-trash-20260826` 为 33M。

### 2026-08-26 22:31 CST | T007

- action: 按用户“第三方参考项目、个人学习旧项目清空；`apps` 保留；除非影响主线”的规则，先检查候选目录大小、最近修改、Git 状态和当前工作区引用，再删除不属于当前 DFCFC2/GRPO/PCS 寄生建模主线的实体目录。
- decision: `BBOPlace-Bench` 顶层仅 4K，为空占位，删除；`AncstrGNN_benchmark` 约 1.2M，只是旧 constraint extraction benchmark，不是当前 PCS 主线运行依赖，删除。`OpenFASOC` 与 `references/ALIGN-public` 只保留历史文档引用和路线参考价值，不属于当前寄生建模 runtime/provenance 依赖，删除。`apps` 明确保留。
- result: 已删除 `PreviousProjects/`、`MyLearning/`、`OpenFASOC/`、`BBOPlace-Bench/`、`AncstrGNN_benchmark/`、`references/ALIGN-public/`，并删除断开的 `external/align-public` 软链接。保留 `apps/`、`references/pcs-harness-align-origin-main-20260815/`、`references/MAGICAL-/`、`references/AnalogGym-Opt-9f2cbba1463efeb5d6160311630e5d56b297f9bf/`。
- artifact: `archives/deleted_third_party_personal_20260826_manifest.txt`；`README.md` 与 `EXTERNALS.md` 已更新删除状态。
- verify: 存在性检查显示目标目录均 `ABSENT`，保留目录均 `PRESENT`；`find . -maxdepth 3 -xtype l` 没有断软链接输出；`git diff --check -- README.md EXTERNALS.md archives/deleted_third_party_personal_20260826_manifest.txt` 退出 0。

### 2026-08-27 CST | T008

- action: 用户询问是否已清干净后重新盘点顶层目录，发现 `BBOPlace-Bench/` 空壳重新出现且 `Others'Projects/` 仍有 783M 第三方旧项目桶。
- decision: `BBOPlace-Bench/` 只有 4K 空目录；`Others'Projects/` 只有历史文档引用，没有当前 DFCFC2/PCS/SMCNR 主线依赖；按用户“第三方参考项目、个人学习旧项目清空；除非影响主线”的规则删除。
- result: 已删除 `BBOPlace-Bench/` 与 `Others'Projects/`；`apps/`、PCS 主线、MAGICAL、AnalogGym-Opt 保留。
- artifact: 追加更新 `archives/deleted_third_party_personal_20260826_manifest.txt`；更新 `README.md` 与 `EXTERNALS.md`。
- verify: 两个目标目录均 `ABSENT`。

### 2026-08-27 CST | T009

- action: 用户指出 `LLM/` 未删除后复查该目录。目录约 512M，主要包含旧 `LlamaFactory-main` 和历史 `SOFTWARE/project1`，只有文档引用，不是当前 DFCFC2/PCS/SMCNR 寄生建模主线依赖。
- decision: 未来如果做 Agent/LoRA，应重新建立 scoped checkout/环境，不保留这个旧本地副本。
- result: 已删除 `LLM/`。
- artifact: 追加更新 `archives/deleted_third_party_personal_20260826_manifest.txt`；更新 `README.md` 与 `EXTERNALS.md`。
- verify: `LLM/` 为 `ABSENT`。
