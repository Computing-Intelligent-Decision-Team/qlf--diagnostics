# Agent Workflow System

这个目录用于把一个大想法拆成可以由 agent 稳定执行的小任务闭环。

## 核心原则

1. 用户只需要先给出 `idea.md`
   - 目标要小、明确、可验证
   - 不要求写步骤，但必须写清楚 target
2. agent 负责把 `idea.md` 扩张成：
   - `tasks.md`
   - 每个 task 的定义文件
   - `execution-log.md`
3. task 必须满足：
   - 小而明确
   - 有依赖关系定义
   - 有明确产物
   - 有一条可以验证是否正确的命令
4. 更新必须即时进行
   - 不能攒一批任务后再统一补日志
   - 每完成一步就更新状态和执行记录
5. bug 不是“顺手改”
   - 发现 bug 后应新建 fix task
   - fix task 要挂到对应 workstream
   - fix task 和普通 task 一样记录目标、验证和日志

## 标准阶段

每个 workstream 都按下面五段推进：

1. `spec`
   - 澄清目标
   - 写清楚成功标准与边界
2. `plan`
   - 把 idea 拆成 task DAG
   - 标明串行依赖和可并行部分
3. `execute`
   - 按 task 执行
   - 每步即时更新状态
4. `review`
   - 运行验证命令
   - 检查产物和回归
5. `finish`
   - 汇总结果
   - 整理后续 task / fix task
   - 完成 git 收尾

## 目录结构

```text
agent_workflow/
  README.md
  templates/
    idea.md
    tasks.md
    task.md
    execution-log.md
  scripts/
    bootstrap_workstream.py
  workstreams/
    YYYY-MM-DD_slug/
      idea.md
      tasks.md
      execution-log.md
      tasks/
        T001_xxx.md
        T002_xxx.md
```

## `tasks.md` 约定

`tasks.md` 是总览页，至少要包含：

- `task_id`
- `title`
- `status`
- `depends_on`
- `target`
- `artifact`
- `verify`

状态统一使用：

- `todo`
- `in_progress`
- `blocked`
- `done`
- `cancelled`

## 单个 Task 文件约定

每个 task 定义文件必须写清楚：

- 目标
- 依赖
- 输入
- 输出 / 产物
- 接口或影响面
- 执行清单
- 验证方式
- 状态

## 执行日志约定

`execution-log.md` 采用追加式记录，不回写历史。

每条记录至少包括：

- 时间
- task_id
- 动作
- 结果
- 产物

## 对模拟集成电路项目的额外约束

IOT 是模拟集成电路项目，因此 task 应优先围绕以下几类可验证对象设计：

1. 工具链可用性
   - 例如 `xschem`、`ngspice`、PDK、版图验证工具
2. 原理图 / 网表产物
   - 例如 `main.sch`、`main.spice`
3. 前仿 / 后仿结果
   - 例如 `OP`、`AC`、`TRAN`、日志、摘要 JSON
4. 平台接口与页面
   - 例如 API payload、项目状态、诊断界面

对于这类项目，验证命令应尽量是：

- 一条测试命令
- 一条构建命令
- 一条仿真命令
- 或一个可以明确检查产物存在性的命令

## 使用方式

1. 用户先写一个新的 `idea.md`
2. agent 读取 idea，创建对应 workstream
3. agent 生成 `tasks.md` 与初始 task 文件
4. agent 执行 task，并即时更新：
   - task 状态
   - execution log
5. 如发现 bug，创建 fix task
6. workstream 完成后做总结与收尾
