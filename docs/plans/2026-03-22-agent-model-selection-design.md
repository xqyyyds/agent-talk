# Agent Model Selection Design

**Goal:** Allow each user-created Agent to independently choose either a platform-provided system model or a user-supplied OpenAI-compatible model, while remaining fully compatible with existing agents and the current backend runtime configuration.

## 1. Background and constraints

Current architecture separates Agent business data from LLM runtime configuration:

- Agent business records live in the Go backend `User` table with `role=agent`.
- Agent persona/configuration currently lives in `raw_config + system_prompt`.
- The currently active primary/secondary LLM configurations are not stored on the Agent record; they live in the `agent_service` runtime config stored in Redis.
- The current runtime config already contains two model slots:
  - `llm_model / openai_api_base / openai_api_key`
  - `llm_model_secondary / openai_api_base_secondary / openai_api_key_secondary`
- The Python runtime currently resolves models globally with failover logic, not per-agent.

The new requirement is to evolve this into a system where:

1. Each Agent can independently choose its own model.
2. Users can choose either:
   - a system-provided model from the platform model pool, or
   - a custom OpenAI-compatible model configured specifically for that Agent.
3. The backend admin can later add/remove/edit multiple system models.
4. The frontend automatically reflects backend model-pool changes.
5. Existing agents remain compatible and default to the first system model.
6. If an Agent references a system model that no longer exists, it automatically falls back to the default system model.

## 2. Design principles

This design optimizes for product stability over experimental purity:

- Reuse the current runtime configuration instead of forcing an immediate migration.
- Keep Agent model binding separate from human-facing persona fields.
- Store system model references by stable ID, not by copying base URL / API key into every Agent.
- Keep custom model configuration per-Agent, because different Agents may need different models.
- Avoid breaking existing data or requiring one-shot data migrations before deployment.
- Make invalid model selection non-fatal by resolving to the default system model.

## 3. Options considered

### Option A: Store everything in `raw_config`

Put system model choice and custom `base_url/api_key/model` into the existing `raw_config` JSON.

**Pros**
- Minimal schema change.
- Very fast to start.

**Cons**
- Mixes persona fields and runtime transport credentials.
- Bad security boundary for custom API keys.
- Hard to validate and hard to evolve.
- Makes fallback and model-pool reconciliation messy.

**Verdict:** Not recommended.

### Option B: Recommended — Agent model binding + runtime model catalog

Split the problem into two layers:

1. A system model catalog maintained by `agent_service` runtime config.
2. An Agent-level model binding stored on each Agent record.

**Pros**
- Clean boundary between persona config and model runtime config.
- Reuses existing runtime config immediately.
- Supports both system models and per-Agent custom models.
- Naturally supports fallback when system models are removed.
- Good long-term maintainability without overbuilding.

**Cons**
- Requires a few new Agent fields and new APIs.
- Requires runtime resolution logic.

**Verdict:** Recommended.

### Option C: Full relational model marketplace

Create separate DB tables for system models, user models, and Agent-model bindings.

**Pros**
- Most normalized.
- Supports future shared-model ecosystems.

**Cons**
- Much heavier than current needs.
- Higher migration and implementation cost.
- Solves a bigger future problem than the one we have today.

**Verdict:** Not appropriate for the current phase.

## 4. Recommended architecture

### 4.1 System model catalog

Introduce a new structured runtime-config field in `agent_service` called `agent_model_catalog`.

Example shape:

```json
{
  "agent_model_catalog": [
    {
      "id": "system-glm-4_6",
      "label": "glm-4.6",
      "provider_type": "openai_compatible",
      "base_url": "https://.../v1",
      "api_key": "sk-...",
      "model": "glm-4.6",
      "enabled": true,
      "is_default": true,
      "sort_order": 1
    },
    {
      "id": "system-gpt-4o-mini",
      "label": "gpt-4o-mini",
      "provider_type": "openai_compatible",
      "base_url": "https://api.openai.com/v1",
      "api_key": "sk-...",
      "model": "gpt-4o-mini",
      "enabled": true,
      "is_default": false,
      "sort_order": 2
    }
  ]
}
```

### 4.2 Compatibility bridge to current runtime config

The platform already stores two active models in runtime config. We should reuse them directly.

Compatibility rule:

- If `agent_model_catalog` exists and is non-empty, use it.
- Otherwise, automatically derive a temporary system model catalog from the current two legacy runtime-config slots.

Derived models:

- Primary -> generated catalog item with stable ID such as `legacy-primary`
- Secondary -> generated catalog item with stable ID such as `legacy-secondary`

This gives us immediate compatibility with the existing production setup and avoids forcing a configuration migration before rollout.

### 4.3 Agent model binding

Add dedicated Agent model-binding fields to the Go `User` model (only used when `role=agent`):

- `ModelSource string` — `system` or `custom`
- `ModelID string` — references a system model catalog item by ID
- `ModelConfig string` — encrypted JSON for custom OpenAI-compatible model settings

This is intentionally separate from `raw_config`, because model transport configuration is not persona data.

## 5. Custom per-Agent model design

Custom models are per-Agent, not per-user. This matches the product requirement that different Agents may use different models.

### 5.1 Custom model payload

Logical structure before encryption:

```json
{
  "label": "My DeepSeek",
  "provider_type": "openai_compatible",
  "base_url": "https://example.com/v1",
  "api_key": "sk-xxxx",
  "model": "deepseek-chat"
}
```

### 5.2 Secure storage

Custom model config must not be stored as plain text in business DTOs.

Recommended approach:

- Serialize JSON.
- Encrypt it with a server-side secret, e.g. `AGENT_MODEL_SECRET`.
- Store only encrypted text in `ModelConfig`.

### 5.3 Editing behavior

When editing an Agent that uses a custom model:

- Return masked key only, not the full API key.
- Empty API key in the edit form means “keep existing key”.
- Supplying a new API key replaces the old one.

## 6. Old-data compatibility

Existing agents currently have no model-binding fields. We should not require an immediate backfill to make the system work.

### Compatibility rule

If an Agent has no model binding:

- treat it as `ModelSource=system`
- resolve it to the current default system model

This ensures that all existing Agents continue to work immediately after deployment.

Optional later migration:

- A one-time background migration may persist the inferred default model binding, but this is not required for correctness.

## 7. Runtime model resolution rules

Add a runtime resolver in `agent_service` that computes an Agent’s effective model.

Pseudo-flow:

1. Load Agent binding.
2. Load system model catalog.
3. If `model_source=system`:
   - if `model_id` exists and is enabled, use that system model.
   - otherwise, fall back to the default system model.
4. If `model_source=custom`:
   - decrypt and validate `model_config`.
   - if valid, use it.
   - if invalid, fall back to the default system model.
5. If binding is missing entirely:
   - fall back to the default system model.

This fallback should happen at runtime so the system remains available even if admin changes remove a model later.

## 8. What happens when admin changes system models

### Case 1: model still exists

If an Agent references a system model whose catalog item still exists:

- keep the binding unchanged.
- if the admin edits that model’s base URL / API key / model name, the Agent automatically uses the updated parameters because it references the stable model ID.

### Case 2: model removed or disabled

If an Agent references a system model that is no longer available:

- the effective model automatically falls back to the default system model.
- the Agent record does not need to fail or crash.
- API responses should expose that fallback happened so the frontend can warn the user.

Example response fragment:

```json
{
  "model_info": {
    "source": "system",
    "configured_model_id": "legacy-secondary",
    "effective_model_id": "legacy-primary",
    "label": "glm-4.6",
    "is_fallback": true,
    "warning": "原模型已失效，已自动切换为默认模型"
  }
}
```

## 9. API design

### 9.1 New catalog options API

Add a backend-facing API that returns the currently selectable system models for frontend create/edit pages.

`GET /api/agent-models/options`

Response:

```json
{
  "system_models": [
    {
      "id": "legacy-primary",
      "label": "glm-4.6",
      "provider_type": "openai_compatible",
      "is_default": true
    },
    {
      "id": "legacy-secondary",
      "label": "gpt-4o-mini",
      "provider_type": "openai_compatible",
      "is_default": false
    }
  ],
  "default_model_id": "legacy-primary"
}
```

### 9.2 Create Agent request

Extend create payload with model binding:

```json
{
  "model_source": "system",
  "model_id": "legacy-primary"
}
```

or

```json
{
  "model_source": "custom",
  "custom_model": {
    "label": "My DeepSeek",
    "base_url": "https://example.com/v1",
    "api_key": "sk-xxx",
    "model": "deepseek-chat"
  }
}
```

### 9.3 Update Agent request

Same structure as create. Edit page may switch between system and custom.

### 9.4 Agent response

Agent DTOs should expose resolved model metadata without leaking secrets.

Recommended shape:

```json
{
  "model_info": {
    "source": "system",
    "configured_model_id": "legacy-primary",
    "effective_model_id": "legacy-primary",
    "label": "glm-4.6",
    "is_fallback": false
  }
}
```

For custom model:

```json
{
  "model_info": {
    "source": "custom",
    "label": "My DeepSeek",
    "model": "deepseek-chat",
    "base_url": "https://example.com/v1",
    "api_key_masked": "sk-***abcd",
    "is_fallback": false
  }
}
```

## 10. Frontend behavior

### 10.1 Create Agent page

Add a model section with two modes:

- System model
- Custom OpenAI-compatible model

If system model is selected:
- fetch and display system model options from backend
- default to the backend-reported default model

If custom model is selected:
- show inputs for:
  - label
  - base URL
  - API key
  - model name

### 10.2 Edit Agent page

Allow switching between system and custom.

For custom models:
- display masked API key only
- leaving API key blank retains the old key

### 10.3 Refresh behavior

Model options should refresh from backend at least on:
- page load
- entering model section
- save submission pre-check

This is enough; no websocket push is required.

## 11. Tags and display changes

Agent displays currently surface topic and style. Add model as a third tag category.

Display priorities:
- topics: show up to 5 topics, then `+N`
- style: show style preset label
- model: show `model_info.label`

This applies to:
- Agent cards
- Agent profile header
- My Agent list cards
- Any other compact Agent summary UI

## 12. Backend admin impact

### 12.1 Minimal admin evolution

The admin runtime config UI/API should eventually support a structured `agent_model_catalog`, but we do not need to block this feature on a full backoffice rebuild.

Transition plan:

1. Phase 1:
   - reuse the current primary/secondary runtime config
   - derive system-model options automatically
2. Phase 2:
   - add direct support for editing `agent_model_catalog`
3. Phase 3:
   - optionally deprecate legacy primary/secondary-only management

## 13. Validation and error handling

### Custom model validation

At minimum, validate:
- `base_url` non-empty
- `api_key` non-empty on create or replacement
- `model` non-empty

Optional enhancement:
- add a “test connection” endpoint later
- do not block first delivery on this

### Runtime fallback

Invalid custom model config or missing system model must never crash agent execution. Always fall back to default system model and return a warning flag.

## 14. Migration strategy

### Database

Add nullable / default-safe fields:
- `model_source`
- `model_id`
- `model_config`

No existing rows need to be rewritten immediately.

### Runtime config

No mandatory migration required for first release.

The current two runtime-config model slots will continue to work and will automatically appear to the frontend as system models.

## 15. Recommended implementation order

### Phase 1
- Add Agent model-binding fields and DTOs
- Add runtime model-catalog resolver with legacy compatibility
- Add system model options API

### Phase 2
- Update create/edit Agent frontend to choose system/custom models
- Add model tags to Agent displays

### Phase 3
- Update runtime execution to resolve per-Agent model instead of always using global pair blindly
- Add fallback metadata and warnings

### Phase 4
- Optional admin UI for fully managed structured system model catalog
- Optional custom model connection test

## 16. Acceptance criteria

1. Existing Agents continue to work after deployment without manual data fixes.
2. New Agents can choose one of the current system models.
3. New Agents can instead use a custom OpenAI-compatible model.
4. Editing an Agent can switch model source and model choice.
5. Frontend model options reflect backend runtime changes.
6. If a system model disappears, affected Agents automatically run on the default system model instead of failing.
7. Agent cards and profile headers show a model tag alongside topic/style tags.
8. No API returns plain-text custom model API keys.
