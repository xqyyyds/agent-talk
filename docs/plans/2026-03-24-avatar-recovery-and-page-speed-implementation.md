# Avatar Recovery And Page Speed Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore avatar availability after container rebuilds and reduce question/debate detail page latency without changing database schema.

**Architecture:** Persist backend avatar files on disk, add frontend avatar fallback rendering, and replace per-answer collection status requests with a single batch status fetch per answer list.

**Tech Stack:** Go + Gin + Gorm, Vue 3 + TypeScript, Docker Compose

---

### Task 1: Persist Avatar Files

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Add backend uploads volume**

- Mount `./backend/uploads:/app/uploads` for the `backend` service so `/uploads` survives container rebuilds.

**Step 2: Verify compose syntax**

Run: `docker compose config`
Expected: config renders successfully with backend volume present.

### Task 2: Add Avatar Fallback Rendering

**Files:**
- Modify: `frontend/src/components/AvatarImage.vue`

**Step 1: Add failing expectation mentally**

- Avatar component should swap to fallback/default source if `src` fails to load.

**Step 2: Implement local error fallback state**

- Track current source in component state.
- Reset when `src` changes.
- On `error`, switch to `fallback`.

**Step 3: Verify existing consumers still compile**

Run: frontend build/type check command.

### Task 3: Add Batch Collection Status API

**Files:**
- Modify: `backend/internal/controller/collection.go`
- Modify: `backend/main.go`

**Step 1: Add request/response structures**

- Accept `answer_ids` query/body form.
- Return map/list keyed by answer id.

**Step 2: Implement single query for all answer IDs**

- Join `collections` and `collection_items` once.
- Group results by answer id.

**Step 3: Register route and keep old single-answer route**

- Preserve backward compatibility.

**Step 4: Run backend tests**

Run: `go test ./...`
Expected: PASS

### Task 4: Wire Frontend Batch Collection Fetch

**Files:**
- Modify: `frontend/src/api/collection.ts`
- Modify: `frontend/src/views/DebatePage.vue`
- Modify: `frontend/src/views/QuestionPage.vue`
- Modify: `frontend/src/components/AnswerItem.vue`

**Step 1: Add batch collection API client**

- Return a lightweight answer-id keyed map.

**Step 2: Update detail pages**

- After answer list loads, if logged in and answers exist, request batch collection statuses once.
- Store results in page-level state.

**Step 3: Update AnswerItem**

- Accept initial collection status from parent.
- Skip per-item fetch when parent already provided status.

**Step 4: Lower debate page first-page size**

- Reduce `getAnswerList(..., 50)` to a smaller first-page size.

### Task 5: Validate End-to-End

**Files:**
- Verify only

**Step 1: Run backend tests**

Run: `go test ./...`
Expected: PASS

**Step 2: Run admin backend compile check**

Run: `python -m compileall admin/backend/app`
Expected: PASS

**Step 3: Run frontend build checks if available**

- Build main frontend.

**Step 4: Manual verification**

- Open debate/question detail page.
- Confirm avatar 404s are gone or gracefully fallback.
- Confirm batch collection request replaces many single-item requests.
