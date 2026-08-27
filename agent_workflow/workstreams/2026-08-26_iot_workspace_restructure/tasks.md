# Tasks

## Workstream

- `name`: IOT workspace restructure
- `owner`: Codex
- `status`: active

## DAG

| task_id | title | status | depends_on | target | artifact | verify |
|---|---|---|---|---|---|---|
| T001 | 顶层空间盘点 | done | - | 识别 IOT 顶层、references 大目录和当前活动产物 | inventory notes in execution log | `du`/`find` 输出可复查 |
| T002 | 建立导航层 | done | T001 | 创建 projects/datasets/experiments/external/archives 并用软链接暴露核心工作区 | top-level link layer | 所有链接 resolve 成功 |
| T003 | 写入空间索引 | done | T002 | 明确主入口、数据集入口和 references 的边界 | `WORKSPACE.md` and README files | 文档路径存在且链接目标可读 |
| T004 | Codex 大目录瘦身清单 | done | T003 | 盘点 `.codex-archives`、`.codex-worktrees`、`.codex-trash`、`.codex-envs`、`.codex-backups` | `WORKSPACE_CLEANUP_PLAN.md` | 大目录大小、Git worktree 注册状态、保留/归档/删除候选分类可复查 |
| T005 | 最低风险 trash 归档试运行 | done | T004 | 归档 `.codex-trash/grpo_batch_v4_0009_partial_20260822` | archive + holding copy | tar/gzip/SHA256 验证通过；`.codex-trash` 清空；holding 可恢复 |
| T006 | 删除 holding 大头并记录权限残留 | partial | T005 | 删除已归档 holding 副本，仅保留可恢复压缩包；记录 root-owned 残留 | `archives/codex-trash-20260826/README.md` and execution log | archive SHA256/gzip 仍通过；`.codex-trash` 为空；holding 仅剩 26 个 root-owned GDS 文件 |
| T007 | 清空非主线第三方与个人旧项目 | done | T003 | 删除用户明确要求清空且不影响当前 DFCFC2/PCS 主线的旧目录 | deletion manifest + README/EXTERNALS updates | 目标目录不存在；`apps`、PCS 主线、MAGICAL、AnalogGym-Opt 仍存在；无断软链接 |
| T008 | 补删遗漏第三方桶 | done | T007 | 删除漏网的 `Others'Projects/` 与空壳 `BBOPlace-Bench/` | updated manifest + README/EXTERNALS | 两个目标目录不存在；无断软链接 |
| T009 | 补删旧 LLM 工具桶 | done | T008 | 删除非主线旧 `LLM/` 目录 | updated manifest + README/EXTERNALS | `LLM/` 不存在；主线目录仍存在 |

## Rules

1. 本轮不物理移动原始实验目录，避免破坏 `state.json`、manifest 和 audit report 中的绝对路径血缘。
2. `references/` 暂时保留为 provenance root；新的日常入口从 `projects/`、`datasets/`、`experiments/` 进入。
3. 后续如果要真正瘦身 39G 的 `references/`，必须先生成迁移清单、哈希校验和回滚方案。
4. 注册中的 Git worktree 只能通过 `git worktree remove` 处理；有脏状态的 worktree 不能直接删除。
