# Agent Model Selection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add per-Agent model selection with support for platform-provided system models and Agent-specific OpenAI-compatible custom models, while keeping existing Agents compatible with the current runtime config.

**Architecture:** The Go backend stores Agent-level model bindings (`system` vs `custom`) and exposes DTOs/APIs for create/edit/display. The Python `agent_service` remains the source of truth for the system model catalog, first via compatibility with existing primary/secondary runtime config and later via a structured catalog. Runtime model resolution always yields an effective model and falls back to the default system model when bindings become invalid.

**Tech Stack:** Go + Gin + GORM, Python FastAPI, Redis runtime config, Vue 3 + TypeScript.

---

### Task 1: Add failing backend tests for Agent model binding compatibility

**Files:**
- Create: `backend/internal/controller/agent_model_test.go`
- Modify: `backend/internal/controller/agent.go`
- Modify: `backend/internal/model/user.go`

**Step 1: Write the failing test**

Add tests covering:
- existing Agent with empty model fields is reported as default system model
- create/update payloads can carry `model_source/system/model_id/custom_model`
- Agent response exposes `model_info`

**Step 2: Run test to verify it fails**

Run: `go test ./backend/internal/controller -run TestAgentModel -v`
Expected: FAIL because fields and DTOs do not yet exist.

**Step 3: Write minimal implementation**

Add model-binding structs/fields and response wiring to satisfy the tests.

**Step 4: Run test to verify it passes**

Run: `go test ./backend/internal/controller -run TestAgentModel -v`
Expected: PASS.

### Task 2: Add runtime model catalog resolver in agent_service

**Files:**
- Create: `agent_service/app/core/agent_model_catalog.py`
- Create: `agent_service/tests/test_agent_model_catalog.py`
- Modify: `agent_service/app/core/runtime_config.py`

**Step 1: Write the failing test**

Add tests covering:
- when `agent_model_catalog` exists, resolver uses it
- when it does not exist, resolver derives models from legacy primary/secondary runtime config
- default model is selected correctly
- disabled/missing models are excluded from selectable list

**Step 2: Run test to verify it fails**

Run: `cd agent_service; python -m unittest tests.test_agent_model_catalog -v`
Expected: FAIL because resolver does not exist.

**Step 3: Write minimal implementation**

Implement catalog normalization and legacy compatibility derivation.

**Step 4: Run test to verify it passes**

Run: `cd agent_service; python -m unittest tests.test_agent_model_catalog -v`
Expected: PASS.

### Task 3: Expose system model options API

**Files:**
- Create: `backend/internal/controller/agent_model.go`
- Modify: `backend/main.go`
- Create: `backend/internal/service/agent_model_service.go`
- Optionally create: `backend/internal/clients/agent_service_runtime.go`

**Step 1: Write the failing test**

Add tests for `GET /api/agent-models/options` response shape and default-model selection behavior.

**Step 2: Run test to verify it fails**

Run: `go test ./backend/internal/controller -run TestGetAgentModelOptions -v`
Expected: FAIL because route/controller do not exist.

**Step 3: Write minimal implementation**

Implement backend endpoint that fetches/derives the system model catalog.

**Step 4: Run test to verify it passes**

Run: `go test ./backend/internal/controller -run TestGetAgentModelOptions -v`
Expected: PASS.

### Task 4: Extend Agent create/update payloads and persistence

**Files:**
- Modify: `backend/internal/model/user.go`
- Modify: `backend/internal/controller/agent.go`
- Modify: `backend/internal/dto/response.go`
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/agent.ts`

**Step 1: Write the failing test**

Add tests for:
- creating with system model binding
- creating with custom model payload
- updating from system to custom and back
- old Agent with no binding still loads correctly

**Step 2: Run test to verify it fails**

Run: `go test ./backend/internal/controller -run TestCreateOrUpdateAgentModelBinding -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Persist `model_source`, `model_id`, `model_config` and expose safe `model_info` DTOs.

**Step 4: Run test to verify it passes**

Run: `go test ./backend/internal/controller -run TestCreateOrUpdateAgentModelBinding -v`
Expected: PASS.

### Task 5: Implement encrypted custom model storage

**Files:**
- Create: `backend/internal/service/model_secret.go`
- Create: `backend/internal/service/model_secret_test.go`
- Modify: `backend/internal/controller/agent.go`
- Modify: `backend/internal/dto/response.go`

**Step 1: Write the failing test**

Cover:
- encrypt/decrypt round trip
- masked key response behavior
- blank API key on edit retains existing stored key

**Step 2: Run test to verify it fails**

Run: `go test ./backend/internal/service -run TestModelSecret -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Add encryption helper and safe response masking.

**Step 4: Run test to verify it passes**

Run: `go test ./backend/internal/service -run TestModelSecret -v`
Expected: PASS.

### Task 6: Resolve effective per-Agent model at runtime

**Files:**
- Modify: `agent_service/app/core/llm_runtime.py`
- Create: `agent_service/app/core/agent_model_resolver.py`
- Create: `agent_service/tests/test_agent_model_resolver.py`
- Possibly modify: `agent_service/app/clients/backend_api.py`

**Step 1: Write the failing test**

Cover:
- system-bound Agent uses configured model when it exists
- missing/disabled system model falls back to default
- custom model resolves when valid
- invalid custom model falls back to default

**Step 2: Run test to verify it fails**

Run: `cd agent_service; python -m unittest tests.test_agent_model_resolver -v`
Expected: FAIL.

**Step 3: Write minimal implementation**

Add a resolver returning effective model config and fallback metadata.

**Step 4: Run test to verify it passes**

Run: `cd agent_service; python -m unittest tests.test_agent_model_resolver -v`
Expected: PASS.

### Task 7: Add create/edit UI for system/custom model choice

**Files:**
- Modify: `frontend/src/views/CreateAgentPage.vue`
- Modify: `frontend/src/views/EditAgentPage.vue`
- Modify: `frontend/src/api/types.ts`
- Create or modify: `frontend/src/api/agentModels.ts`
- Test: `frontend` component/unit tests if present, otherwise typecheck/build

**Step 1: Write the failing test**

If component tests exist, add tests for:
- loading system model options
- switching between system/custom modes
- custom API key left blank on edit preserving existing key
- invalid form state blocking submit

If tests do not exist, first add a small focused test or use vue-tsc build as minimal safety net.

**Step 2: Run test to verify it fails**

Run relevant frontend test command or `pnpm vue-tsc --noEmit`
Expected: FAIL because fields/components do not exist.

**Step 3: Write minimal implementation**

Add model selection UI using Composition API, keeping existing agent form flow intact.

**Step 4: Run test to verify it passes**

Run frontend test command or `pnpm vue-tsc --noEmit`
Expected: PASS.

### Task 8: Add model tag display across Agent surfaces

**Files:**
- Modify: `frontend/src/views/MyAgentsPage.vue`
- Modify: `frontend/src/views/ProfilePage.vue`
- Modify: `frontend/src/views/AgentDetailPage.vue`
- Modify: `frontend/src/components/AnswerItem.vue` (only if Agent summary there needs model tag)
- Create/modify helper: `frontend/src/utils/agentMeta.ts`

**Step 1: Write the failing test**

Add tests or assertions for:
- topic/style/model tags render together
- model label comes from resolved `model_info.label`
- overflow behavior for topics remains intact

**Step 2: Run test to verify it fails**

Run relevant test command or `pnpm vue-tsc --noEmit`
Expected: FAIL.

**Step 3: Write minimal implementation**

Render model tag consistently on compact and detail surfaces.

**Step 4: Run test to verify it passes**

Run frontend test command or `pnpm vue-tsc --noEmit`
Expected: PASS.

### Task 9: Build integration and compatibility verification

**Files:**
- Modify as needed from previous tasks
- Optionally add: `docs/plans/2026-03-22-agent-model-selection-notes.md`

**Step 1: Run backend tests**

Run: `go test ./...`
Expected: PASS.

**Step 2: Run agent_service tests**

Run: `cd agent_service; python -m unittest`
Expected: PASS.

**Step 3: Run frontend build/typecheck**

Run: `cd frontend; pnpm vue-tsc --noEmit; pnpm run build`
Expected: PASS.

**Step 4: Manual compatibility checklist**

Verify:
- old Agent without model fields loads as default system model
- create Agent with system model works
- edit Agent to custom model works
- invalid custom model falls back safely
- removed system model reports fallback warning

**Step 5: Commit**

```bash
git add backend agent_service frontend docs/plans/2026-03-22-agent-model-selection-design.md docs/plans/2026-03-22-agent-model-selection-implementation.md
git commit -m "feat: add per-agent model selection"
```
