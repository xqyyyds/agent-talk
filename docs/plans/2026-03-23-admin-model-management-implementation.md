# Admin Model Management And Active User Metrics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the admin panel’s legacy single/dual-fallback model configuration with a first-class system model management module, and fix the dashboard’s 24-hour active-user metric to count real recent visitors instead of login-only users.

**Architecture:** Keep `agent_service` as the source of truth for runtime model catalog data, but stop exposing model operations only through the generic runtime-config editor. Add a dedicated admin model-management API and page, preserve compatibility with legacy primary/secondary config by deriving a catalog when needed, and unify dashboard activity metrics around the existing Redis presence `last_seen` signal.

**Tech Stack:** Python FastAPI (`agent_service`, admin backend), Redis runtime config + presence ZSET, Vue 3 + TypeScript admin frontend, SQLAlchemy admin analytics.

---

### Task 1: Add failing tests for dashboard active-user metric semantics

**Files:**
- Create: `admin/backend/tests/test_dashboard_metrics.py`
- Modify: `admin/backend/app/routers/dashboard.py`

**Step 1: Write the failing test**

Add tests that verify:
- `online_users_5m` counts users from Redis presence in the last 5 minutes
- `active_users_24h` counts users from Redis presence in the last 24 hours
- `active_users_24h` is independent from `UserLoginEvent`
- `login_events_24h` remains a separate login-event count

Example assertions:

```python
def test_overview_uses_presence_for_active_users_24h():
    # seed Redis ZSET with 3 users in 24h, 2 users in 5m
    # seed DB login events with only 1 user
    payload = client.get("/admin/dashboard/overview", headers=auth_headers).json()
    assert payload["active_users_24h"] == 3
    assert payload["online_users_5m"] == 2
    assert payload["login_events_24h"] >= 1
```

**Step 2: Run test to verify it fails**

Run: `pytest admin/backend/tests/test_dashboard_metrics.py -v`
Expected: FAIL because `active_users_24h` still uses `UserLoginEvent`.

**Step 3: Write minimal implementation**

Add:
- `_active_users_24h()` using the same Redis presence ZSET as `_online_users_5m()`
- update `dashboard_overview()` to return presence-based `active_users_24h`
- keep `login_events_24h` unchanged

**Step 4: Run test to verify it passes**

Run: `pytest admin/backend/tests/test_dashboard_metrics.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add admin/backend/tests/test_dashboard_metrics.py admin/backend/app/routers/dashboard.py
git commit -m "fix: align 24h active user metric with presence tracking"
```

---

### Task 2: Add failing tests for runtime model catalog compatibility

**Files:**
- Modify: `agent_service/tests/test_agent_model_catalog.py`
- Modify: `agent_service/app/core/agent_model_catalog.py`

**Step 1: Write the failing test**

Add tests covering:
- if `agent_model_catalog` exists, it is returned as the system model pool
- if `agent_model_catalog` is empty, legacy primary/secondary config are converted into two catalog items
- one model is always resolved as default
- disabled entries are excluded from selectable output

**Step 2: Run test to verify it fails**

Run: `cd agent_service; python -m unittest tests.test_agent_model_catalog -v`
Expected: FAIL if compatibility behavior does not fully match the admin page needs.

**Step 3: Write minimal implementation**

Adjust catalog normalization so admin APIs can consume a stable, display-ready catalog shape with:
- `id`
- `label`
- `provider_type`
- `base_url`
- `model`
- `enabled`
- `is_default`
- `sort_order`

**Step 4: Run test to verify it passes**

Run: `cd agent_service; python -m unittest tests.test_agent_model_catalog -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add agent_service/tests/test_agent_model_catalog.py agent_service/app/core/agent_model_catalog.py
git commit -m "feat: normalize system model catalog with legacy compatibility"
```

---

### Task 3: Add dedicated model catalog admin APIs in agent_service

**Files:**
- Create: `agent_service/app/api/admin_model_catalog.py`
- Modify: `agent_service/app/main.py`
- Modify: `agent_service/app/core/runtime_config.py`
- Create: `agent_service/tests/test_admin_model_catalog_api.py`

**Step 1: Write the failing test**

Cover:
- `GET /admin/model-catalog`
- `POST /admin/model-catalog`
- `PUT /admin/model-catalog/{id}`
- enable / disable
- set-default
- reorder

Example:

```python
def test_get_model_catalog_returns_selectable_models():
    resp = client.get("/admin/model-catalog", headers={"x-runtime-token": token})
    assert resp.status_code == 200
    assert "models" in resp.json()["data"]
```

**Step 2: Run test to verify it fails**

Run: `cd agent_service; python -m unittest tests.test_admin_model_catalog_api -v`
Expected: FAIL because endpoint does not exist.

**Step 3: Write minimal implementation**

Implement CRUD-style operations over `agent_model_catalog`, still persisting via runtime config.

**Step 4: Run test to verify it passes**

Run: `cd agent_service; python -m unittest tests.test_admin_model_catalog_api -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add agent_service/app/api/admin_model_catalog.py agent_service/app/main.py agent_service/tests/test_admin_model_catalog_api.py
git commit -m "feat: add dedicated admin model catalog APIs"
```

---

### Task 4: Add model connection testing and validation endpoint

**Files:**
- Modify: `agent_service/app/api/admin_model_catalog.py`
- Create: `agent_service/tests/test_admin_model_catalog_test_connection.py`
- Reference: `agent_service/app/clients/llm_client.py`

**Step 1: Write the failing test**

Add tests for:
- valid OpenAI-compatible config returns success
- invalid base URL / token returns normalized error
- test endpoint never persists changes by itself

**Step 2: Run test to verify it fails**

Run: `cd agent_service; python -m unittest tests.test_admin_model_catalog_test_connection -v`
Expected: FAIL because test endpoint does not exist.

**Step 3: Write minimal implementation**

Add `POST /admin/model-catalog/test` that:
- accepts provider config
- performs a lightweight connectivity check
- returns success, latency, and error details

**Step 4: Run test to verify it passes**

Run: `cd agent_service; python -m unittest tests.test_admin_model_catalog_test_connection -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add agent_service/app/api/admin_model_catalog.py agent_service/tests/test_admin_model_catalog_test_connection.py
git commit -m "feat: add model connection test endpoint"
```

---

### Task 5: Add admin-backend proxy routes for model management

**Files:**
- Modify: `admin/backend/app/routers/ops.py`
- Create: `admin/backend/tests/test_ops_model_catalog_proxy.py`

**Step 1: Write the failing test**

Cover:
- proxying `GET /admin/ops/model-catalog`
- proxying create / update / enable / disable / set-default / reorder / test
- forwarding runtime token
- normalizing upstream errors
- writing audit logs for mutating operations

**Step 2: Run test to verify it fails**

Run: `pytest admin/backend/tests/test_ops_model_catalog_proxy.py -v`
Expected: FAIL because proxy routes do not exist.

**Step 3: Write minimal implementation**

Add proxy routes and corresponding `log_action(...)` calls for:
- create
- update
- enable/disable
- set-default
- reorder
- test

**Step 4: Run test to verify it passes**

Run: `pytest admin/backend/tests/test_ops_model_catalog_proxy.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add admin/backend/app/routers/ops.py admin/backend/tests/test_ops_model_catalog_proxy.py
git commit -m "feat: proxy admin model catalog management routes"
```

---

### Task 6: Add model usage / impact analysis API

**Files:**
- Modify: `admin/backend/app/routers/ops.py`
- Create: `admin/backend/tests/test_ops_model_usage.py`
- Modify: `backend/internal/service/agent_model.go` or add a new helper if the admin backend queries backend APIs for usage
- Possibly create: `admin/backend/app/services/model_usage.py`

**Step 1: Write the failing test**

Cover:
- model usage returns agent counts per system model
- includes active-agent count when available
- includes fallback count / invalid-reference warnings

**Step 2: Run test to verify it fails**

Run: `pytest admin/backend/tests/test_ops_model_usage.py -v`
Expected: FAIL because usage endpoint does not exist.

**Step 3: Write minimal implementation**

Expose a model-usage view that returns:
- `agent_count`
- `active_agent_count`
- `fallback_agent_count`
- `warnings`

Use existing backend Agent model binding and fallback-resolution logic rather than duplicating rules.

**Step 4: Run test to verify it passes**

Run: `pytest admin/backend/tests/test_ops_model_usage.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add admin/backend/app/routers/ops.py admin/backend/tests/test_ops_model_usage.py
git commit -m "feat: add admin model usage analysis"
```

---

### Task 7: Add admin frontend API methods for model catalog management

**Files:**
- Modify: `admin/frontend/src/api/index.ts`
- Modify: `admin/frontend/src/api/index.js` (if still checked in and used)
- Create: `admin/frontend/src/types/modelCatalog.ts` (optional)

**Step 1: Write the failing test**

If frontend API tests exist, add tests for the new methods. If not, use `tsc` / build as the minimal safety net and define the expected API signatures first.

Required methods:
- `getModelCatalog`
- `createModelCatalogItem`
- `updateModelCatalogItem`
- `enableModelCatalogItem`
- `disableModelCatalogItem`
- `setDefaultModelCatalogItem`
- `reorderModelCatalog`
- `testModelCatalogItem`
- `getModelCatalogUsage`

**Step 2: Run test or typecheck to verify it fails**

Run: `cd admin/frontend; pnpm vue-tsc --noEmit`
Expected: FAIL because methods/types do not exist.

**Step 3: Write minimal implementation**

Add typed API helpers for the new routes.

**Step 4: Run typecheck to verify it passes**

Run: `cd admin/frontend; pnpm vue-tsc --noEmit`
Expected: PASS.

**Step 5: Commit**

```bash
git add admin/frontend/src/api/index.ts admin/frontend/src/api/index.js
git commit -m "feat: add admin frontend model catalog API client"
```

---

### Task 8: Build a dedicated admin Model Management page

**Files:**
- Create: `admin/frontend/src/pages/ModelManagementPage.vue`
- Modify: `admin/frontend/src/router.ts`
- Modify: `admin/frontend/src/router.js`
- Modify navigation component(s), likely `admin/frontend/src/App.vue` or sidebar/header component
- Test: `admin/frontend` typecheck/build

**Step 1: Write the failing test**

If page/component tests exist, add them. Otherwise define the page contract and verify through typecheck/build.

The page must include:
- system model catalog table
- legacy compatibility panel
- usage / impact summary
- test connection action
- add/edit modal
- enable / disable / set default actions

**Step 2: Run typecheck to verify it fails**

Run: `cd admin/frontend; pnpm vue-tsc --noEmit`
Expected: FAIL because page/route/nav entries do not exist.

**Step 3: Write minimal implementation**

Build the page with these sections:
- Catalog list
- Legacy source panel
- Usage / risk panel
- Health/test results panel

Keep UI simple and readable; do not overdesign.

**Step 4: Run typecheck/build to verify it passes**

Run:
- `cd admin/frontend; pnpm vue-tsc --noEmit`
- `cd admin/frontend; pnpm run build`

Expected: PASS.

**Step 5: Commit**

```bash
git add admin/frontend/src/pages/ModelManagementPage.vue admin/frontend/src/router.ts admin/frontend/src/router.js
git commit -m "feat: add admin model management page"
```

---

### Task 9: Downgrade OpsPage model config to compatibility/read-only guidance

**Files:**
- Modify: `admin/frontend/src/pages/OpsPage.vue`
- Test: `admin/frontend` typecheck/build

**Step 1: Write the failing test / define expected UI change**

Expected behavior:
- legacy primary / secondary model fields are no longer the recommended editing surface
- page shows clear guidance pointing admins to the new model-management page
- if needed, legacy fields stay read-only or visibly marked as compatibility-only

**Step 2: Run typecheck/build to verify it fails**

Run: `cd admin/frontend; pnpm vue-tsc --noEmit`
Expected: FAIL after template changes are stubbed in.

**Step 3: Write minimal implementation**

Update `OpsPage.vue` so:
- it no longer presents single/dual-fallback as the primary product path
- it clearly states this section is compatibility / runtime legacy state
- it links to the dedicated model-management page

**Step 4: Run typecheck/build to verify it passes**

Run:
- `cd admin/frontend; pnpm vue-tsc --noEmit`
- `cd admin/frontend; pnpm run build`

Expected: PASS.

**Step 5: Commit**

```bash
git add admin/frontend/src/pages/OpsPage.vue
git commit -m "refactor: demote legacy runtime model config in ops page"
```

---

### Task 10: Update dashboard labels and chart semantics

**Files:**
- Modify: `admin/frontend/src/pages/DashboardPage.vue`
- Test: `admin/frontend` typecheck/build

**Step 1: Write the failing test / define expected behavior**

Expected labels:
- `5分钟在线用户`
- `24小时访问活跃用户`
- `24小时登录事件`

Ensure no text still implies that `active_users_24h` means “login users”.

**Step 2: Run typecheck to verify it fails**

Run: `cd admin/frontend; pnpm vue-tsc --noEmit`
Expected: FAIL if template text/state changes are incomplete.

**Step 3: Write minimal implementation**

Update labels, card descriptions, and any helper text so the dashboard accurately reflects the new metric semantics.

**Step 4: Run typecheck/build to verify it passes**

Run:
- `cd admin/frontend; pnpm vue-tsc --noEmit`
- `cd admin/frontend; pnpm run build`

Expected: PASS.

**Step 5: Commit**

```bash
git add admin/frontend/src/pages/DashboardPage.vue
git commit -m "fix: clarify dashboard active-user metric labels"
```

---

### Task 11: Add audit coverage for model-management actions

**Files:**
- Modify: `admin/backend/app/routers/ops.py`
- Create: `admin/backend/tests/test_model_catalog_audit.py`

**Step 1: Write the failing test**

Cover that create/update/enable/disable/set-default/reorder operations create audit log entries with:
- actor
- target model id
- action type
- key payload summary

**Step 2: Run test to verify it fails**

Run: `pytest admin/backend/tests/test_model_catalog_audit.py -v`
Expected: FAIL because logging is incomplete or missing.

**Step 3: Write minimal implementation**

Add `log_action(...)` to all mutating model catalog operations with concise payloads.

**Step 4: Run test to verify it passes**

Run: `pytest admin/backend/tests/test_model_catalog_audit.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add admin/backend/app/routers/ops.py admin/backend/tests/test_model_catalog_audit.py
git commit -m "feat: audit admin model catalog changes"
```

---

### Task 12: End-to-end verification

**Files:**
- Modify as needed from earlier tasks

**Step 1: Run backend tests**

Run:
- `pytest admin/backend/tests -v`
- `cd agent_service; python -m unittest -v`

Expected: PASS.

**Step 2: Run frontend checks**

Run:
- `cd admin/frontend; pnpm vue-tsc --noEmit`
- `cd admin/frontend; pnpm run build`

Expected: PASS.

**Step 3: Manual verification checklist**

Verify:
- admin can view model catalog
- admin can add/edit/enable/disable/set default/reorder models
- legacy primary/secondary config still appears as compatibility information
- deleting/disabling a model shows impact information
- 24-hour active users is never lower than 5-minute online users under the same presence dataset
- dashboard labels clearly distinguish presence activity from login counts

**Step 4: Final commit**

```bash
git add .
git commit -m "feat: add admin model management and fix active-user metrics"
```
