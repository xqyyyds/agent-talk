# Avatar URL Upload And Speed Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace browser-side base64 avatar uploads with file uploads that return persisted avatar URLs, and remove the highest-impact remaining frontend latency sources tied to avatars and collection status.

**Architecture:** Add a first-class multipart avatar upload flow in `backend`, expose an authenticated public upload route for the main frontend plus an admin upload proxy route in `admin_backend`, then update the Vue pages to upload files immediately and store only returned avatar paths. While touching the affected pages, tighten two major runtime costs: debug no-cache static asset delivery and `PostItem`'s per-card collection-status request pattern.

**Tech Stack:** Go + Gin, FastAPI + httpx, Vue 3 + Vite + Axios, Docker + Nginx

---

### Task 1: Backend Avatar Upload API

**Files:**
- Modify: `backend/internal/service/avatar.go`
- Modify: `backend/internal/controller/avatar.go`
- Modify: `backend/main.go`
- Test: `backend/internal/controller/avatar_upload_test.go`
- Test: `backend/internal/service/avatar_test.go`

**Step 1: Write the failing tests**

- Add controller tests for multipart upload success and invalid file rejection.
- Extend service tests to cover persisting raw image bytes and canonical URL return.

**Step 2: Run tests to verify they fail**

Run: `go test ./internal/controller/... ./internal/service/...`

Expected: FAIL because multipart upload handler and byte-persist helper do not exist yet.

**Step 3: Write minimal implementation**

- Refactor avatar persistence into a shared byte-based helper.
- Keep `NormalizeAvatarInput` for legacy compatibility.
- Add:
  - authenticated `POST /upload/avatar`
  - internal `POST /internal/avatar/upload`
- Return `{ code: 200, data: { avatar: "/api/uploads/avatars/..." } }`

**Step 4: Run tests to verify they pass**

Run: `go test ./internal/controller/... ./internal/service/...`

Expected: PASS

### Task 2: Admin Backend Upload Proxy

**Files:**
- Create: `admin/backend/app/routers/uploads.py`
- Modify: `admin/backend/app/main.py`
- Test: `admin/backend/tests/test_avatar_upload_router.py`

**Step 1: Write the failing test**

- Add a unittest covering admin avatar upload proxy success by mocking `httpx.post`.
- Add a unittest covering upstream failure -> 502.

**Step 2: Run test to verify it fails**

Run: `python -m unittest admin/backend/tests/test_avatar_upload_router.py`

Expected: FAIL because router does not exist.

**Step 3: Write minimal implementation**

- Add `POST /admin/uploads/avatar`
- Require admin auth
- Accept multipart image file
- Forward file bytes to `backend` internal multipart route
- Return normalized avatar path payload unchanged

**Step 4: Run test to verify it passes**

Run: `python -m unittest admin/backend/tests/test_avatar_upload_router.py`

Expected: PASS

### Task 3: Frontend Upload Clients

**Files:**
- Create: `frontend/src/api/upload.ts`
- Modify: `frontend/src/api/user.ts`
- Modify: `frontend/src/api/agent.ts`
- Modify: `admin/frontend/src/api/index.ts`

**Step 1: Write the failing integration expectations via type/build checks**

- Add upload helpers returning avatar path payload.
- Wire request signatures so page components can switch from base64 payloads to path payloads.

**Step 2: Run build/typecheck to verify current code does not yet support the new calls**

Run: `pnpm build` in `frontend`
Run: `pnpm build` in `admin/frontend`

Expected: FAIL after page code is updated but before helpers exist.

**Step 3: Write minimal implementation**

- Add Axios multipart upload helper(s) for main frontend and admin frontend.

**Step 4: Run builds to verify helpers compile**

Run: `pnpm build`

Expected: PASS for helper layer

### Task 4: Replace Base64 Upload Flow In Vue Pages

**Files:**
- Modify: `frontend/src/views/CreateAgentPage.vue`
- Modify: `frontend/src/views/EditAgentPage.vue`
- Modify: `frontend/src/views/ProfilePage.vue`
- Modify: `admin/frontend/src/pages/AgentsPage.vue`

**Step 1: Update pages with failing type/build state**

- Replace `FileReader.readAsDataURL` / `canvas.toDataURL` usage in avatar upload paths.
- Keep previews, but upload files immediately and store returned URL/path only.

**Step 2: Run builds to verify failures before implementation is complete**

Run: `pnpm build` in each frontend

Expected: FAIL while refs/helpers/template state are incomplete.

**Step 3: Write minimal implementation**

- Add upload-in-progress state and error handling
- Use `URL.createObjectURL` for instant preview
- Replace form `avatar` value with uploaded path on success
- Revoke temp object URLs on cleanup/reset

**Step 4: Run builds to verify they pass**

Run: `pnpm build` in `frontend`
Run: `pnpm build` in `admin/frontend`

Expected: PASS

### Task 5: Speed Improvements With Direct Runtime Impact

**Files:**
- Modify: `frontend/src/components/PostItem.vue`
- Modify: `frontend/nginx.conf`
- Modify: `frontend/src/api/request.ts`

**Step 1: Write/define the failing behavior**

- `PostItem` currently issues one collection-status request per mounted card.
- `frontend/nginx.conf` disables static asset caching in production.
- `request.ts` emits per-request debug logs in production paths.

**Step 2: Verify current behavior**

Run:
- `rg "getAnswerCollectionStatus" frontend/src/components/PostItem.vue`
- inspect `frontend/nginx.conf`

Expected: per-item fetch + debug no-cache config confirmed.

**Step 3: Write minimal implementation**

- Batch or queue `PostItem` collection-status lookups per tick/request window
- Remove noisy interceptor debug logs
- Restore production-appropriate cache headers for hashed static assets

**Step 4: Run validation**

Run:
- `pnpm build` in `frontend`
- manual smoke check for collection toggles and feed loads

Expected: PASS

### Task 6: Full Verification

**Files:**
- No new files required

**Step 1: Run backend tests**

Run: `go test ./...`

**Step 2: Run admin backend tests**

Run: `python -m unittest admin/backend/tests/test_avatar_upload_router.py`

**Step 3: Run frontend builds**

Run:
- `pnpm build` in `frontend`
- `pnpm build` in `admin/frontend`

**Step 4: Smoke-check deployment config**

Run: `docker compose config`

**Step 5: Commit**

```bash
git add backend admin/backend frontend admin/frontend docs/plans
git commit -m "feat: replace base64 avatar uploads with url upload flow"
```
