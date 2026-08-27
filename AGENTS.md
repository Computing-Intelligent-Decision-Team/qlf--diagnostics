# IOT Codex 工作流指令

本仓库后续开发任务默认按“agent_workflow + Superpowers”融合流程执行。除非用户明确要求只做分析、只回答问题或跳过流程，否则不要直接进入编码。

## 总原则

- 用户的当前明确指令优先。
- 任务开始前先澄清目标、成功标准和边界。
- 开发任务必须拆成小而明确的 task，每个 task 都要有依赖、产物和一条可验证命令。
- 实现类任务优先使用 TDD：先写失败测试，再写最小实现，再重构。
- 验证必须在完成声明之前执行；不能只靠代码阅读判断完成。
- 日志必须即时更新，不能事后批量补。
- 发现 bug 不要顺手混改；创建 fix task，挂到对应 workstream。

## agent_workflow 框架

任务编排框架位于 `agent_workflow/`，用于把大想法拆成可执行的小任务闭环。

五阶段生命周期：

1. `spec`：澄清目标，写清楚成功标准与边界。
2. `plan`：把 idea 拆成 task DAG，标明串行依赖和可并行部分。
3. `execute`：按 task 执行，每步即时更新日志。
4. `review`：运行验证命令，检查产物和回归。
5. `finish`：汇总结果，整理后续 task，完成 git 收尾。

`tasks.md` 总览页至少包含：

- `task_id`
- `title`
- `status`
- `depends_on`
- `target`
- `artifact`
- `verify`

## Superpowers 方法

如果当前 Codex 会话已加载 Superpowers 插件/技能，开发任务按相关 skill 执行：

1. `brainstorming`：苏格拉底式追问，理清需求，输出设计文档。
2. `using-git-worktrees`：创建隔离分支和 worktree。
3. `writing-plans`：拆成 2-5 分钟小任务，每个任务包含完整代码路径和验证步骤。
4. `subagent-driven-development`：每个任务派独立子代理，并进行规格审查和代码质量审查。
5. `test-driven-development`：执行 RED-GREEN-REFACTOR。
6. `requesting-code-review`：对照计划做结构化审查，严重问题阻塞进度。
7. `retrospective`：完成一个 task 或 workstream 后，自动触发回顾与改进提议流程，等待用户选择接受/改进/否决。

8. `finishing-a-development-branch`：验证测试，选择 merge、PR、保留或丢弃。

调试类任务优先使用：

- `systematic-debugging`：四阶段根因分析。
- `verification-before-completion`：完成前验证。

如果 Superpowers 插件/技能没有在当前会话中暴露，明确告知用户，并按同等方法手动执行：先澄清、再拆任务、TDD、验证、审查和日志化。

## 融合流程

收到开发任务时，默认按以下顺序执行：

1. 使用 Superpowers `brainstorming` 方法澄清需求，不要直接写代码。
2. 如果任务属于已有 workstream，在 `agent_workflow/workstreams/` 下找到它；否则创建新的 workstream。
3. 使用 `agent_workflow` 的 `tasks.md` DAG 格式拆解任务，并标明依赖关系。
4. 使用 Superpowers `using-git-worktrees` 方法创建隔离开发环境；如果当前环境不适合创建 worktree，说明原因并采用当前工作区。
5. 对每个 task 使用 TDD：先写测试，确认失败，再写实现，再运行验证。
6. 每完成一个 task，立即更新对应 task 文件和 `execution-log.md`。
7. task 完成后运行代码审查；发现问题时按严重程度处理。
8. 发现 bug 时创建 fix task，挂到当前 workstream，不把无关修复混入当前 task。
9. 全部 task 完成后进入 `finish`：汇总产物、验证命令、残余风险和后续 task。

## 日志要求

`execution-log.md` 使用追加式记录。每条记录至少包含：

- 时间戳。
- 完成了哪个 task。
- 使用了哪个 Superpowers skill 或对应方法。
- 验证命令及关键输出。
- 遇到的问题、决策和产物路径。

## 适用例外

以下情况可以不创建 workstream 或不完整执行五阶段流程，但要在回复中说明原因：

- 用户明确要求只解释、只阅读、只审查或只给建议。
- 极小任务，例如查看命令输出、定位文件、回答环境问题。
- 当前沙箱或权限不允许写文件、创建 worktree、运行验证命令。

即使跳过完整流程，也要保持验证优先和结论可追溯。

## 专利任务专用路由

涉及中国专利的任务统一以 `patent-disclosure-skill` 作为唯一主流程，包括：

- 专利点挖掘与可专利性分析。
- 现有技术检索与查新压力测试。
- 权利要求书、说明书、摘要和技术交底书编写。
- 发明、实用新型和外观设计材料整理。
- 专利通俗解读、政策分析和审查意见答复。

执行专利任务时遵守以下边界：

1. 不启动 `agent_workflow`、Superpowers 开发流程、TDD、git worktree 或开发任务 DAG。
2. 专利的章节结构、分析步骤、检索流程、权利要求组织和交付格式以 `patent-disclosure-skill` 为准，不用其他通用写作或开发 skill 替代。
3. PDF/OCR、数学公式排版、图片处理和公开数据库访问能力仅可作为辅助工具；不得改变专利 skill 的专业流程和结论口径。
4. 只有任务明确要求修改、测试或实现仓库代码时，代码部分才切换到开发工作流；专利内容部分仍由 `patent-disclosure-skill` 独立负责。
5. 专利分析、查新笔记、交底书和权利要求草案等产物默认保存到 `references/专利/`，除非用户指定其他位置。
