# Customer Consultation Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a concise, static customer consultation workspace that opens from each “服务咨询” button and shows the selected service without enabling chat.

**Architecture:** Keep the marketing pages and their existing header/footer unchanged. Add one query-driven consultation route with a dedicated immersive shell, a small service-selection helper, and a pure presentational workspace component; the route wrapper supplies translations and selected-service data.

**Tech Stack:** React 18, React Router 7, TypeScript, Tailwind CSS 4, Vite 6, Node test runner, Chromium CDP integration test.

**Spec:** `docs/superpowers/specs/2026-08-26-customer-consultation-workspace-design.md`

## Global Constraints

- The workspace is static: no sending, upload, persistence, backend, order, payment, or Agent behavior.
- “购买服务” remains unchanged.
- “我的咨询” is visible but disabled; “购买记录” remains visible.
- The conversation contains no seeded message or system card.
- Unknown service IDs resolve to `frontend`.
- Preserve the existing blue-white Rongzhixin visual language and keep the page concise.
- Work in the current `apps/analog-circuit-platform` checkout because its current page implementation is dirty and not reproducible from a clean worktree; do not overwrite unrelated user changes.

---

### Task 1: Consultation URL Contract and Service Entry Links

**Files:**
- Create: `apps/analog-circuit-platform/src/lib/consultation.ts`
- Modify: `apps/analog-circuit-platform/src/pages/ServicesPage.tsx:1-155`
- Test: `apps/analog-circuit-platform/tests/consultation-routing.test.mjs`

**Interfaces:**
- Consumes: `services: ServiceItem[]` from `src/data/services.ts`.
- Produces: `consultationHref(serviceId: string): string` and `resolveConsultationService(serviceId: string | null): ServiceItem`.

- [ ] **Step 1: Write the failing routing contract test**

```js
import assert from "node:assert/strict";
import test from "node:test";
import { createServer } from "vite";

test("builds consultation links and defaults unknown services to frontend", async (t) => {
  const vite = await createServer({ appType: "custom", server: { middlewareMode: true } });
  t.after(() => vite.close());

  const { consultationHref, resolveConsultationService } =
    await vite.ssrLoadModule("/src/lib/consultation.ts");

  assert.equal(consultationHref("backend"), "/consultations/new?service=backend");
  assert.equal(resolveConsultationService("custom").id, "custom");
  assert.equal(resolveConsultationService("unknown").id, "frontend");
  assert.equal(resolveConsultationService(null).id, "frontend");
});
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd apps/analog-circuit-platform && node --test tests/consultation-routing.test.mjs`

Expected: FAIL because `/src/lib/consultation.ts` does not exist.

- [ ] **Step 3: Implement the consultation URL helper**

```ts
import { services, type ServiceItem } from "../data/services";

export function consultationHref(serviceId: string): string {
  return `/consultations/new?service=${encodeURIComponent(serviceId)}`;
}

export function resolveConsultationService(serviceId: string | null): ServiceItem {
  return services.find((service) => service.id === serviceId) ?? services[0];
}
```

- [ ] **Step 4: Wire only “服务咨询” to the new URL**

In `ServicesPage.tsx`, import `consultationHref`, replace the second CTA `<button>` with this link, and leave the first “购买服务” button untouched:

```tsx
<Link
  to={consultationHref(service.id)}
  className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-3 text-base font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400/50"
>
  <MessageCircle className="size-4" />
  {t("服务咨询")}
</Link>
```

- [ ] **Step 5: Verify GREEN and regression build**

Run: `cd apps/analog-circuit-platform && node --test tests/consultation-routing.test.mjs && pnpm build`

Expected: routing test passes and Vite reports `✓ built`.

- [ ] **Step 6: Update workstream log and commit this task**

Append the RED/GREEN commands and outputs to `agent_workflow/workstreams/2026-08-26_customer_consultation_workspace/execution-log.md`, then commit only Task 1 files in the nested app repository and the workstream log in the root repository with message `feat: route service consultations to workspace`.

---

### Task 2: Static Immersive Consultation Workspace

**Files:**
- Create: `apps/analog-circuit-platform/src/components/ConsultationWorkspace.tsx`
- Create: `apps/analog-circuit-platform/src/pages/ConsultationWorkspacePage.tsx`
- Modify: `apps/analog-circuit-platform/src/app/App.tsx:1-145`
- Modify: `apps/analog-circuit-platform/src/i18n/translations.ts:1-65`
- Test: `apps/analog-circuit-platform/tests/consultation-workspace.test.mjs`

**Interfaces:**
- Consumes: `resolveConsultationService(serviceId)` from Task 1, `HeaderBrand`, `useT`, and `useLang`.
- Produces: `ConsultationWorkspace(props)` and default `ConsultationWorkspacePage` for route `/consultations/new`.

- [ ] **Step 1: Write the failing static-workspace test**

```js
import assert from "node:assert/strict";
import test from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const copy = {
  brandName: "融智芯",
  brandSubtitle: "模拟芯片设计服务平台",
  back: "返回服务详情",
  myConsultations: "我的咨询",
  purchaseHistory: "购买记录",
  login: "登录/注册",
  currentConsultation: "当前咨询",
  notStarted: "未开始",
  emptyHint: "请描述您的芯片设计需求",
  intendedService: "意向服务",
  materialStatus: "资料状态",
  notSubmitted: "未提交",
  advisor: "对接运营",
  pendingAssignment: "待分配",
  inputPlaceholder: "咨询功能暂未开放",
  attachment: "添加附件",
  send: "发送",
};

test("renders an empty consultation with every composer control disabled", async (t) => {
  const vite = await createServer({ appType: "custom", server: { middlewareMode: true } });
  t.after(() => vite.close());
  const { ConsultationWorkspace } =
    await vite.ssrLoadModule("/src/components/ConsultationWorkspace.tsx");

  const html = renderToStaticMarkup(ConsultationWorkspace({
    serviceTitle: "后端服务",
    copy,
    lang: "zh",
    onLangChange: () => {},
  }));

  assert.match(html, />后端服务</);
  assert.match(html, />未开始</);
  assert.match(html, />请描述您的芯片设计需求</);
  assert.equal((html.match(/disabled=""/g) ?? []).length, 4);
  assert.doesNotMatch(html, /data-message/);
});
```

The four disabled controls are “我的咨询”, attachment, textarea, and send.

- [ ] **Step 2: Run the test and verify RED**

Run: `cd apps/analog-circuit-platform && node --test tests/consultation-workspace.test.mjs`

Expected: FAIL because `ConsultationWorkspace.tsx` does not exist.

- [ ] **Step 3: Create the pure workspace component**

Create the exported component with this semantic structure; apply the existing slate/blue-white Tailwind tokens without adding extra cards or messages:

```tsx
import { ArrowLeft, MessageCircle, Paperclip, Send, ShoppingBag, UserPlus } from "lucide-react";
import { HeaderBrand } from "./HeaderBrand";

export type ConsultationWorkspaceCopy = {
  brandName: string;
  brandSubtitle: string;
  back: string;
  myConsultations: string;
  purchaseHistory: string;
  login: string;
  currentConsultation: string;
  notStarted: string;
  emptyHint: string;
  intendedService: string;
  materialStatus: string;
  notSubmitted: string;
  advisor: string;
  pendingAssignment: string;
  inputPlaceholder: string;
  attachment: string;
  send: string;
};

export function ConsultationWorkspace({
  serviceTitle,
  copy,
  lang,
  onLangChange,
}: {
  serviceTitle: string;
  copy: ConsultationWorkspaceCopy;
  lang: "zh" | "en";
  onLangChange: (lang: "zh" | "en") => void;
}) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="flex h-[76px] items-center justify-between px-5 lg:px-8">
          <HeaderBrand logoSrc="/logo.jpg" primaryName={copy.brandName} subtitle={copy.brandSubtitle} />
          <div className="flex items-center gap-2">
            <a href="/services" className="inline-flex items-center gap-2 text-sm text-slate-600">
              <ArrowLeft className="size-4" />{copy.back}
            </a>
            <div aria-label="Language">
              <button type="button" aria-pressed={lang === "zh"} onClick={() => onLangChange("zh")}>中</button>
              <button type="button" aria-pressed={lang === "en"} onClick={() => onLangChange("en")}>EN</button>
            </div>
            <button type="button" disabled>{copy.myConsultations}</button>
            <button type="button"><ShoppingBag className="size-4" />{copy.purchaseHistory}</button>
            <button type="button"><UserPlus className="size-4" />{copy.login}</button>
          </div>
        </div>
      </header>

      <div className="grid min-h-[calc(100vh-76px)] lg:grid-cols-[240px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)_300px]">
        <aside className="hidden border-r border-slate-200 bg-white p-5 lg:block">
          <p className="text-xs font-semibold text-slate-500">{copy.currentConsultation}</p>
          <div className="mt-4 rounded-lg border border-slate-200 p-4">
            <MessageCircle className="size-4 text-slate-500" />
            <p className="mt-3 font-semibold">{serviceTitle}</p>
            <p className="mt-1 text-xs text-slate-500">{copy.notStarted}</p>
          </div>
        </aside>

        <main className="flex min-w-0 flex-col bg-white">
          <div className="flex flex-1 items-center justify-center p-8 text-sm text-slate-400">
            {copy.emptyHint}
          </div>
          <div className="border-t border-slate-200 p-4">
            <div className="flex items-end gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
              <button type="button" disabled aria-label={copy.attachment}><Paperclip className="size-5" /></button>
              <textarea disabled rows={2} placeholder={copy.inputPlaceholder} className="min-h-12 flex-1 resize-none bg-transparent" />
              <button type="button" disabled aria-label={copy.send}><Send className="size-5" /></button>
            </div>
          </div>
        </main>

        <aside className="hidden border-l border-slate-200 bg-slate-50 p-6 xl:block">
          <dl className="space-y-6 text-sm">
            <div><dt className="text-slate-500">{copy.intendedService}</dt><dd className="mt-1 font-semibold">{serviceTitle}</dd></div>
            <div><dt className="text-slate-500">{copy.materialStatus}</dt><dd className="mt-1">{copy.notSubmitted}</dd></div>
            <div><dt className="text-slate-500">{copy.advisor}</dt><dd className="mt-1">{copy.pendingAssignment}</dd></div>
          </dl>
        </aside>
      </div>
    </div>
  );
}
```

During implementation, retain this semantic tree and disabled behavior; Tailwind class refinements may improve spacing and responsive typography but must not add functionality.

- [ ] **Step 4: Create the query/translation page wrapper**

`ConsultationWorkspacePage.tsx` must use `useSearchParams`, `resolveConsultationService`, `useT`, and `useLang`. It passes the translated service title, a complete `ConsultationWorkspaceCopy` object, `lang`, and `onLangChange={setLang}`. The 中/EN switch is the only active workspace control besides navigation back to services.

Add exact Chinese/English translation entries for every key in `copy`, including:

```ts
"我的咨询": { zh: "我的咨询", en: "My Consultations" },
"当前咨询": { zh: "当前咨询", en: "Current Consultation" },
"未开始": { zh: "未开始", en: "Not Started" },
"请描述您的芯片设计需求": { zh: "请描述您的芯片设计需求", en: "Describe your chip design needs" },
"意向服务": { zh: "意向服务", en: "Service of Interest" },
"资料状态": { zh: "资料状态", en: "Materials" },
"未提交": { zh: "未提交", en: "Not Submitted" },
"对接运营": { zh: "对接运营", en: "Service Coordinator" },
"待分配": { zh: "待分配", en: "Pending Assignment" },
"咨询功能暂未开放": { zh: "咨询功能暂未开放", en: "Consultation messaging is not yet available" },
"添加附件": { zh: "添加附件", en: "Attach file" },
"发送": { zh: "发送", en: "Send" },
```

- [ ] **Step 5: Add the immersive route without changing marketing chrome**

In `App.tsx`, import `useLocation` and `ConsultationWorkspacePage`. Add `/consultations/new` to `Routes`. When `location.pathname === "/consultations/new"`, hide the marketing `Header`, `Footer`, and `Tweaks`; all other routes retain their current rendering.

- [ ] **Step 6: Verify GREEN and all unit tests**

Run: `cd apps/analog-circuit-platform && node --test tests/consultation-workspace.test.mjs && pnpm test`

Expected: the new test and all existing tests pass with zero failures.

- [ ] **Step 7: Update workstream log and commit this task**

Append RED/GREEN evidence to the execution log. Commit the Task 2 app files in the nested app repository with message `feat: add static customer consultation workspace`, then commit the updated root workstream log separately.

---

### Task 3: Browser Integration and Responsive Verification

**Files:**
- Create: `apps/analog-circuit-platform/tests/consultation-workspace-browser.test.mjs`
- Modify only if the RED test exposes a defect: `apps/analog-circuit-platform/src/components/ConsultationWorkspace.tsx`
- Modify only if the RED test exposes a routing defect: `apps/analog-circuit-platform/src/pages/ServicesPage.tsx`

**Interfaces:**
- Consumes: the `/services` and `/consultations/new?service=<id>` routes from Tasks 1–2.
- Produces: browser-level proof that the selected service reaches the workspace and the static layout does not overflow.

- [ ] **Step 1: Write a failing Chromium integration test**

Reuse the proven CDP setup and targeted `/tmp` profile cleanup from `tests/header-brand-responsive.test.mjs`. The new assertions must execute in the real page:

```js
const backendConsultation = document.querySelector(
  'a[href="/consultations/new?service=backend"]',
);
backendConsultation.click();

// After location changes and the workspace renders:
const snapshot = {
  path: location.pathname,
  query: location.search,
  service: document.querySelector('[data-testid="intended-service"]')?.textContent,
  messageCount: document.querySelectorAll("[data-message]").length,
  disabledComposerCount: document.querySelectorAll("textarea:disabled, button[data-composer-control]:disabled").length,
  hasMarketingFooter: document.querySelector("footer") !== null,
  overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
};
```

Assert the literal values:

```js
assert.deepEqual(snapshot, {
  path: "/consultations/new",
  query: "?service=backend",
  service: "后端服务",
  messageCount: 0,
  disabledComposerCount: 3,
  hasMarketingFooter: false,
  overflow: false,
});
```

Run the same overflow assertion after `Emulation.setDeviceMetricsOverride` at widths 1440 and 320.

- [ ] **Step 2: Run the browser test and verify RED**

Run: `cd apps/analog-circuit-platform && node --test tests/consultation-workspace-browser.test.mjs`

Expected: FAIL on the first uncovered routing, selector, or responsive contract. If it passes immediately, temporarily remove the backend consultation link, confirm the test fails, restore it, and rerun.

- [ ] **Step 3: Apply only the minimal integration/responsive fix**

Ensure the implementation exposes these stable semantic hooks:

```tsx
<dd data-testid="intended-service">{serviceTitle}</dd>
<button data-composer-control type="button" disabled aria-label={copy.attachment}>…</button>
<textarea data-composer-control disabled … />
<button data-composer-control type="button" disabled aria-label={copy.send}>…</button>
```

For 320px, keep both sidebars hidden and use `min-w-0`, compact header spacing, and hidden secondary button labels where necessary. Do not enable any static control.

- [ ] **Step 4: Run full verification**

Run:

```bash
cd apps/analog-circuit-platform
pnpm test
pnpm build
git diff --check
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3102/consultations/new?service=backend
```

Expected: all tests pass, Vite reports `✓ built`, `git diff --check` is silent, and the running development server returns HTTP `200`.

- [ ] **Step 5: Perform structured code review**

Use `superpowers:requesting-code-review` against only the files in this plan. Fix all Critical and Important findings, rerun Step 4, and record Minor findings as residual notes.

- [ ] **Step 6: Update logs and finish the branch**

Append final verification, review findings, decisions, and artifact paths to `agent_workflow/workstreams/2026-08-26_customer_consultation_workspace/execution-log.md`. Mark all rows complete in `tasks.md`, then use `superpowers:finishing-a-development-branch` to offer merge/PR/keep/discard options without touching unrelated dirty files.
