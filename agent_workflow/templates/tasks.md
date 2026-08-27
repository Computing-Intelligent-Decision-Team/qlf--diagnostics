# Tasks

## Workstream

- `name`:
- `owner`:
- `status`:

## DAG

| task_id | title | status | depends_on | context_pack | target | artifact | verify |
|---|---|---|---|---|---|---|---|
| T001 | example task | todo | - | iot-core-pack | 明确目标 | 产物路径 | 一条验证命令 |

## Rules

1. `depends_on` 为空表示可立即执行
2. 没有依赖关系的任务可以并行
3. `context_pack` 写本 task 默认读取的 Repomix 上下文包，例如 `iot-core-pack`、`layout-closure-pack`、`constraint-frontend-pack`
4. 每个 task 必须有独立验证方式
5. 状态变更后必须同步更新本文件和对应 task 文件
