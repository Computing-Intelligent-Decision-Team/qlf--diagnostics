# Customer Consultation Workspace Tasks

| task_id | title | status | depends_on | target | artifact | verify |
|---|---|---|---|---|---|---|
| CCW-001 | Consultation URL contract and service entry links | pending | — | `apps/analog-circuit-platform/src/lib/consultation.ts`, `src/pages/ServicesPage.tsx` | Service-specific consultation URLs | `node --test tests/consultation-routing.test.mjs && pnpm build` |
| CCW-002 | Static immersive consultation workspace | pending | CCW-001 | `src/components/ConsultationWorkspace.tsx`, `src/pages/ConsultationWorkspacePage.tsx`, `src/app/App.tsx`, translations | Empty three-column customer workspace | `node --test tests/consultation-workspace.test.mjs && pnpm test` |
| CCW-003 | Browser integration and responsive closure | pending | CCW-002 | Browser test and any scoped responsive fixes | Desktop/mobile evidence and final review | `pnpm test && pnpm build && git diff --check` |

Plan: `docs/superpowers/plans/2026-08-26-customer-consultation-workspace.md`

Spec: `docs/superpowers/specs/2026-08-26-customer-consultation-workspace-design.md`

