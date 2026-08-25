# Tasks

| task_id | title | status | depends_on | target | artifact | verify |
| --- | --- | --- | --- | --- | --- | --- |
| T001 | Define the experiment and visualization design | review | - | Approved scope, evidence contract, timing protocol and app boundary | `docs/superpowers/specs/2026-08-26-pcs-harness-workflow-design.md` | `rg -n "目标|成功标准|实验协议|计时口径|验证策略" docs/superpowers/specs/2026-08-26-pcs-harness-workflow-design.md` |
| T002 | Write the implementation plan and task DAG | blocked | T001 | 2–5 minute implementation tasks with isolated verification | `docs/superpowers/plans/2026-08-26-pcs-harness-workflow.md`; updated `tasks.md` | User approves T001, then plan self-review passes |

Statuses: `pending`, `in_progress`, `review`, `blocked`, `done`.
