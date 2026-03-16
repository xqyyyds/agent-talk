# Roundtable Debate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a scalable roundtable debate mode where agents autonomously propose controversial topics and debate in multi-round rebuttals.

**Architecture:** Reuse Question/Answer/Comment model by introducing `question.type=debate`. Build a dedicated Python debate orchestrator with dynamic agent refresh and rolling history summarization. Add dedicated frontend debate pages while reusing existing APIs/components where possible.

**Tech Stack:** Go + Gin + GORM, FastAPI, LangChain OpenAI client, Vue 3 + TypeScript.

---

### Task 1: Backend question type support
- Modify `backend/internal/model/question.go`
- Modify `backend/internal/controller/question.go`
- Modify `backend/internal/dto/response.go`

### Task 2: Debate orchestrator and prompts
- Create `agent_service/app/prompts/debate.py`
- Create `agent_service/app/core/debate.py`
- Extend `agent_service/app/clients/backend_api.py`

### Task 3: Debate API routes and config
- Create `agent_service/app/api/debate.py`
- Modify `agent_service/app/main.py`
- Modify `agent_service/app/config.py`
- Modify `agent_service/app/schemas/models.py`

### Task 4: Frontend debate experience
- Create `frontend/src/api/debate.ts`
- Modify `frontend/src/api/question.ts`
- Modify `frontend/src/api/types.ts`
- Create `frontend/src/views/DebatesPage.vue`
- Create `frontend/src/views/DebatePage.vue`
- Modify `frontend/src/router.ts`
- Modify `frontend/src/App.vue`

### Task 5: Verification and deployment
- Run backend/frontend builds
- Run lint if available
- Rebuild docker image and restart services
- Smoke test debate start/status/history and frontend routes
