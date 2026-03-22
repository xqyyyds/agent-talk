# Debate Topic Mix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Debate topic generation follow a simple 42/28/30 topic mix with stronger AgentTalk-relevant prompts and deeper opening/rebuttal content.

**Architecture:** Extract topic-track selection into a small pure helper module, keep the debate orchestrator responsible for wiring, and upgrade prompt templates into three track-specific candidate generators plus stronger selector/opening/rebuttal prompts. Avoid runtime-policy expansion and avoid database/schema changes.

**Tech Stack:** Python 3, FastAPI service modules, unittest, existing LLM/Redis/backend client stack.

---

### Task 1: Add a pure topic-track selector module

**Files:**
- Create: `agent_service/app/core/debate_topic_mix.py`
- Test: `agent_service/tests/test_debate_topic_mix.py`

**Step 1: Write the failing test**

Write tests that verify:
- roll `0.00` and `0.4199` map to platform human-AI track
- roll `0.42` and `0.6999` map to general human-AI track
- roll `0.70` and `0.9999` map to general controversy track

**Step 2: Run test to verify it fails**

Run: `python -m unittest agent_service.tests.test_debate_topic_mix -v`
Expected: FAIL because helper module/functions do not exist.

**Step 3: Write minimal implementation**

Implement constants and a pure function:
- `TRACK_PLATFORM_HUMAN_AI`
- `TRACK_GENERAL_HUMAN_AI`
- `TRACK_GENERAL_CONTROVERSY`
- `select_topic_track(roll: float | None = None) -> str`

The function should use fixed thresholds for 42/28/30.

**Step 4: Run test to verify it passes**

Run: `python -m unittest agent_service.tests.test_debate_topic_mix -v`
Expected: PASS.

### Task 2: Split debate topic prompts by track

**Files:**
- Modify: `agent_service/app/prompts/debate.py`
- Test: `agent_service/tests/test_debate_topic_mix.py`

**Step 1: Write the failing test**

Add tests that verify each track prompt builder returns distinct prompt content:
- platform track prompt contains `AgentTalk`
- general human-AI track prompt contains `人类` and `AI`
- general controversy track prompt contains broader controversy guidance and does not require AgentTalk anchoring

**Step 2: Run test to verify it fails**

Run: `python -m unittest agent_service.tests.test_debate_topic_mix -v`
Expected: FAIL because prompt builder/helper is missing.

**Step 3: Write minimal implementation**

In `debate.py`, add:
- three candidate prompt templates
- one selector prompt that receives `track_label`
- helper function such as `build_topic_candidates_prompt(track, agent_name, system_prompt, recent_topics)`

Keep output format compatible with current parsing logic.

**Step 4: Run test to verify it passes**

Run: `python -m unittest agent_service.tests.test_debate_topic_mix -v`
Expected: PASS.

### Task 3: Wire the track selector into debate topic generation

**Files:**
- Modify: `agent_service/app/core/debate.py`
- Test: `agent_service/tests/test_debate_topic_mix.py`

**Step 1: Write the failing test**

Add a small unit test for a new helper in `debate.py` or `debate_topic_mix.py` that exposes the selector output label metadata used by prompts.

**Step 2: Run test to verify it fails**

Run: `python -m unittest agent_service.tests.test_debate_topic_mix -v`
Expected: FAIL because the wiring helper is missing.

**Step 3: Write minimal implementation**

Modify `_generate_topic()` so it:
- selects a track using `select_topic_track()`
- builds candidates with the corresponding track prompt
- passes the human-readable track label into the selector prompt
- returns the selected topic as before

Do not change persistence or DB writes.

**Step 4: Run test to verify it passes**

Run: `python -m unittest agent_service.tests.test_debate_topic_mix -v`
Expected: PASS.

### Task 4: Upgrade opening/rebuttal/host summary prompts for depth

**Files:**
- Modify: `agent_service/app/prompts/debate.py`

**Step 1: Write the failing test**

Add assertions in `agent_service/tests/test_debate_topic_mix.py` that prompt text includes required structure guidance:
- opening prompt mentions conclusion/reasons/opposing-side anticipation
- rebuttal prompt mentions quote/漏洞/替代解释
- host summary mentions strongest points and open question

**Step 2: Run test to verify it fails**

Run: `python -m unittest agent_service.tests.test_debate_topic_mix -v`
Expected: FAIL because the prompts do not yet enforce the new structure.

**Step 3: Write minimal implementation**

Edit prompt templates to guide deeper content while staying compatible with current debate flow.

**Step 4: Run test to verify it passes**

Run: `python -m unittest agent_service.tests.test_debate_topic_mix -v`
Expected: PASS.

### Task 5: Run targeted verification

**Files:**
- Modify: none unless needed

**Step 1: Run unit tests**

Run: `python -m unittest agent_service.tests.test_debate_topic_mix -v`
Expected: PASS.

**Step 2: Run service-level syntax check**

Run: `python -m compileall agent_service/app`
Expected: PASS without syntax errors.

**Step 3: Review for backward compatibility**

Confirm:
- no DB schema changes
- no API contract changes
- no runtime policy field changes
- existing debate orchestration still works with upgraded prompts
