# Tasks

| task_id | title | status | depends_on | target | artifact | verify |
| --- | --- | --- | --- | --- | --- | --- |
| T001 | Define the experiment and visualization design | done | - | Approved scope, evidence contract, timing protocol and app boundary | `docs/superpowers/specs/2026-08-26-pcs-harness-workflow-design.md` | `rg -n "目标|成功标准|实验协议|计时口径|验证策略" docs/superpowers/specs/2026-08-26-pcs-harness-workflow-design.md` |
| T002 | Write the implementation plan and task DAG | done | T001 | Executable TDD plan with exact paths, commands, gates and verification | `docs/superpowers/plans/2026-08-26-pcs-harness-workflow.md`; updated `tasks.md` | Plan self-review and placeholder scan pass |
| T003 | Create isolated PCS-Harness implementation worktree | done | T002 | Clean branch pinned to audited PCS commit | `references/.codex-worktrees/pcs-harness-workflow`; baseline log | Narrow baseline `unittest` suites pass |
| T004 | Add event and timing contracts | done | T003 | Durable ordered event stream and measured stage timing | `workflow_events.py`; `workflow_timing.py`; commit `ca9d02c` | Event/timing tests pass |
| T005 | Instrument L0–L6 and physical sub-stages | done | T004 | Real stage and artifact events without closure-semantic changes | controller/layout instrumentation; commit `5c212a0` | Instrumentation and regression tests pass |
| T006 | Add Agent decision bridge and dispatcher | done | T005 | Fail-closed validated Agent actions | `workflow_agent.py`; decision artifacts; commit `0ae672a` | Agent/orchestration tests pass |
| T007 | Freeze OTA GRPO action space and provenance | done | T005 | W/NF-only real GRPO proposals with immutable bias/L/multi | demo config; provenance gate; commit `b612f7a` | Config/native-GRPO tests pass |
| T008 | Implement reproducible boundary scan | done | T007 | 32-candidate pre-scan and 6–8 physical shortlist command | `workflow_boundary_scan.py`; `selection.json` schema; commit `e7c1957` | Boundary-selection tests pass |
| T009 | Derive physical visualization evidence | done | T005 | Shared-coordinate GDS, DRC and net-anchored PEX data | `workflow_visualization.py`; commit `70b95c0` | Visualization and raw-PEX tests pass |
| T010 | Build live-only API | done | T006,T008,T009 | OTA input gate, run control, SSE and safe artifacts | `apps/pcs-harness-workflow/backend`; commit `6fa4e73` | Backend API tests pass |
| T011 | Build input-gate frontend | done | T010 | Type/upload/parse/preflight/one-click flow | standalone React app; commit `73d5a01` | Component test and production build pass |
| T012 | Build live Agent/GRPO cockpit | in_progress | T010,T011 | Reducer, reconnect, L0–L6, Agent and GRPO panels | frontend state and panels | Reducer/SSE/component tests pass |
| T013 | Build physical and iteration visualization | pending | T009,T012 | Layout/DRC/LVS/PEX animation and N/N+1 comparison | physical UI components | Frontend tests/build and 1920×1080 visual check pass |
| T014 | Wire automatic recording run | pending | T006,T007,T010,T013 | One-click bounded Agent→GRPO→EDA→L6 workflow | runner, CLI, launcher | Runner and cross-stack regression tests pass |
| T015 | Run campaign and rehearsal | pending | T008,T014 | Fixed true boundary candidate, real L6 run, measured timings | generated run root and reports | Machine evidence checks and recording review pass |

Statuses: `pending`, `in_progress`, `review`, `blocked`, `done`.
