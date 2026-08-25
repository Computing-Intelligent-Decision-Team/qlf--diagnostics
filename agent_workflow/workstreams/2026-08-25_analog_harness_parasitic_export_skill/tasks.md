# Tasks

## Workstream

- `name`: AnalogHarness trusted parasitic export skill
- `owner`: Codex
- `status`: done

## DAG

| task_id | title | status | depends_on | context_pack | target | artifact | verify |
|---|---|---|---|---|---|---|---|
| T001 | 固化规格与无 skill 基线 | done | - | user contract | 捕获普通 Codex 遗漏的可信门槛 | spec + baseline log | spec 和日志存在 |
| T002 | TDD 实现确定性导出器 | done | T001 | synthetic candidates | 正确分类并打包候选 | exporter + tests | 7 个 unittest 全通过 |
| T003 | 编写并验证 Codex skill | done | T002 | exporter contract | 一次安装、显式调用 | SKILL.md + metadata | quick_validate + forward test 通过 |
| T004 | 生成可安装包并验收 | done | T003 | validated skill | 可移植 tar.gz | dist archive + SHA256 | 解包复验 7 tests 通过 |

## Rules

1. 正样本必须同时满足 sizing lineage、DRC PASS、connectivity LVS PASS、raw PEX 可解析。
2. PM、reward、前仿、PVT、后仿只记录，不筛选。
3. 任何未知物理证据均拒绝，不猜测 PASS。
4. 源实验目录只读；skill 只复制。
5. 外部上传必须另有明确目标与授权。
