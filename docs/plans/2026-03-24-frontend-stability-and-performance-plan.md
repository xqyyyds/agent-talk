# Frontend Stability And Performance Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate route scroll jumps, empty-state flicker, and major frontend loading inefficiencies across the question, hotspot, and feed flows while establishing a maintainable enterprise-grade page-state pattern.

**Architecture:** Add a router-level scroll policy, introduce explicit first-load state gates on route-driven pages, and refactor page data loading so initial render shows loading/skeleton states instead of transient empty states. Keep existing APIs where possible, parallelize non-dependent requests, and reduce component-side fetch side effects on hot paths.

**Tech Stack:** Vue 3, Vue Router 4, TypeScript, Vite, Axios, UnoCSS

---

### Task 1: Document Current Failure Modes In Tests/Checks

**Files:**
- Modify: `frontend/src/router.ts`
- Verify: `frontend/src/views/QuestionPage.vue`
- Verify: `frontend/src/views/HotspotsPage.vue`
- Verify: `frontend/src/views/QuestionsPage.vue`
- Verify: `frontend/src/views/DebatesPage.vue`

**Step 1: Write the failing check target**

Capture the behaviors to fix:
- route transitions into detail pages should scroll to top
- initial route entry should not render empty-state copy before the first request resolves
- route param changes on reused components should reset to loading state before showing new content

**Step 2: Run the smallest available verification**

Run: `pnpm build`
Expected: PASS before code changes, but manual behavior still reproduces in browser

**Step 3: Use the failures as implementation guardrails**

Treat the following as regressions if they remain after implementation:
- entering `/question/:id` starts mid-page
- question/hotspot pages flash `还没有回答` / `暂无热点数据` before loading
- hotspot/question list pages briefly show empty-state text on first render

**Step 4: Re-run build after each page refactor**

Run: `pnpm build`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/router.ts frontend/src/views/QuestionPage.vue frontend/src/views/HotspotsPage.vue frontend/src/views/QuestionsPage.vue frontend/src/views/DebatesPage.vue
git commit -m "fix: stabilize page initialization and route scrolling"
```

### Task 2: Add Router-Level Scroll Behavior

**Files:**
- Modify: `frontend/src/router.ts`

**Step 1: Write the failing expectation**

Expected router behavior:
- browser back/forward uses `savedPosition`
- all other navigations reset to `{ top: 0 }`
- no reused detail page keeps prior scroll offset

**Step 2: Run build as pre-change guard**

Run: `pnpm build`
Expected: PASS

**Step 3: Write the minimal implementation**

Add `scrollBehavior(to, from, savedPosition)` to the router:
- return `savedPosition` when present
- otherwise return `{ top: 0 }`

**Step 4: Run build to verify**

Run: `pnpm build`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/router.ts
git commit -m "fix: reset route scroll position by default"
```

### Task 3: Stabilize Question Detail Initial State

**Files:**
- Modify: `frontend/src/views/QuestionPage.vue`

**Step 1: Write the failing expectation**

Question page should:
- show loading on first render
- avoid rendering `还没有回答` until answers request completes
- reset to loading on `questionId` and `answerId` route changes
- parallelize question detail and answer loading when safe

**Step 2: Run build before code changes**

Run: `pnpm build`
Expected: PASS

**Step 3: Write minimal implementation**

Add:
- explicit `pageInitialized` / `answersInitialized` refs
- a single route refresh function that resets state before fetching
- first-load empty-state guard so empty text only appears after answer fetch completes
- route-change scroll-to-top fallback via router behavior only, no page-local scroll hacks

**Step 4: Run build to verify**

Run: `pnpm build`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/views/QuestionPage.vue
git commit -m "fix: prevent question detail flicker on initial load"
```

### Task 4: Stabilize Hotspot Detail And Hotspot List Initial State

**Files:**
- Modify: `frontend/src/views/HotspotsPage.vue`

**Step 1: Write the failing expectation**

Hotspots page should:
- never show `热点详情不存在或已删除` before the first detail request finishes
- never show `暂无热点数据` before the list request for the selected date finishes
- avoid duplicate/serial initial list loads triggered by `loadDates()` plus watchers
- keep detail body visible while Agent answers stream in separately

**Step 2: Run build before changes**

Run: `pnpm build`
Expected: PASS

**Step 3: Write minimal implementation**

Add:
- separate `listInitialized` / `detailInitialized`
- guarded query-sync behavior so initialization does not immediately trigger duplicate list fetches
- dedicated initial loading state for detail and list modes
- non-blocking agent-answer follow-up after hotspot detail loads

**Step 4: Run build to verify**

Run: `pnpm build`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/views/HotspotsPage.vue
git commit -m "fix: remove hotspot page empty-state flicker"
```

### Task 5: Stabilize Feed Pages For Questions And Debates

**Files:**
- Modify: `frontend/src/views/QuestionsPage.vue`
- Modify: `frontend/src/views/DebatesPage.vue`

**Step 1: Write the failing expectation**

Feed pages should:
- show loading or skeleton on first render, not empty text
- avoid duplicate `refreshFeed` / `refreshDebates` calls during route query initialization
- keep page/date state transitions explicit

**Step 2: Run build before changes**

Run: `pnpm build`
Expected: PASS

**Step 3: Write minimal implementation**

Add:
- `feedInitialized` refs
- guarded empty-state rendering
- initialization flow that loads dates then feed without watcher-caused duplicate fetches

**Step 4: Run build to verify**

Run: `pnpm build`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/views/QuestionsPage.vue frontend/src/views/DebatesPage.vue
git commit -m "fix: stabilize feed first-render states"
```

### Task 6: Reduce Remaining Hot-Path Component Fetch Overhead

**Files:**
- Modify: `frontend/src/components/AnswerItem.vue`
- Modify: `frontend/src/views/ProfilePage.vue`

**Step 1: Write the failing expectation**

Profile and answer-heavy views should avoid per-item collection status fetches when batch data is available or can be preloaded.

**Step 2: Run build before changes**

Run: `pnpm build`
Expected: PASS

**Step 3: Write minimal implementation**

Extend current batch-collection strategy to profile answer lists or add page-level gating so `AnswerItem` does not trigger avoidable hot-path requests.

**Step 4: Run build to verify**

Run: `pnpm build`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/components/AnswerItem.vue frontend/src/views/ProfilePage.vue
git commit -m "perf: reduce collection status overhead on profile answers"
```

### Task 7: Final Verification And Regression Pass

**Files:**
- Verify: `frontend/src/router.ts`
- Verify: `frontend/src/views/QuestionPage.vue`
- Verify: `frontend/src/views/HotspotsPage.vue`
- Verify: `frontend/src/views/QuestionsPage.vue`
- Verify: `frontend/src/views/DebatesPage.vue`
- Verify: `frontend/src/components/AnswerItem.vue`
- Verify: `frontend/src/views/ProfilePage.vue`

**Step 1: Run build**

Run: `pnpm build`
Expected: PASS

**Step 2: Run lint if feasible**

Run: `pnpm lint`
Expected: PASS or capture pre-existing lint noise separately

**Step 3: Manual verification checklist**

Confirm in browser:
- opening a question detail starts at top
- opening hotspot detail starts at top
- question detail no longer flashes `还没有回答` before load
- hotspot list/detail no longer flashes `暂无热点数据` / `热点详情不存在`
- question feed and debate feed no longer flash empty states on first visit
- profile answer list does not trigger avoidable collection-status thrash

**Step 4: Inspect diff for accidental behavior changes**

Run: `git diff --stat`
Expected: only planned frontend files changed

**Step 5: Commit**

```bash
git add frontend/src/router.ts frontend/src/views/QuestionPage.vue frontend/src/views/HotspotsPage.vue frontend/src/views/QuestionsPage.vue frontend/src/views/DebatesPage.vue frontend/src/components/AnswerItem.vue frontend/src/views/ProfilePage.vue docs/plans/2026-03-24-frontend-stability-and-performance-plan.md
git commit -m "feat: harden frontend page stability and loading behavior"
```
