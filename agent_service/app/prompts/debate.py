"""Sanitized prompts for roundtable debate generation and rebuttal."""

from app.core.debate_topic_mix import (
    TRACK_GENERAL_CONTROVERSY,
    TRACK_GENERAL_HUMAN_AI,
    TRACK_PLATFORM_HUMAN_AI,
)

AGENTTALK_CONTEXT = """[PRIVATE_PROMPT_PLACEHOLDER]
This public version hides internal debate context copywriting.
"""

PLATFORM_HUMAN_AI_FEW_SHOTS = """[PRIVATE_FEW_SHOTS_PLACEHOLDER]"""
GENERAL_HUMAN_AI_FEW_SHOTS = """[PRIVATE_FEW_SHOTS_PLACEHOLDER]"""
GENERAL_CONTROVERSY_FEW_SHOTS = """[PRIVATE_FEW_SHOTS_PLACEHOLDER]"""
OPENING_FEW_SHOT = """[PRIVATE_FEW_SHOTS_PLACEHOLDER]"""
REBUTTAL_FEW_SHOTS = """[PRIVATE_FEW_SHOTS_PLACEHOLDER]"""

DEBATE_TOPIC_CANDIDATES_PLATFORM_HUMAN_AI_PROMPT = """[PRIVATE_PROMPT_PLACEHOLDER]
Agent: {agent_name}
Persona prompt:
{system_prompt}

Platform context:
{agenttalk_context}

Recent topics:
{recent_topics}

Few-shot references:
{few_shots}

Output 6 candidate topics as numbered lines.
"""

DEBATE_TOPIC_CANDIDATES_GENERAL_HUMAN_AI_PROMPT = """[PRIVATE_PROMPT_PLACEHOLDER]
Agent: {agent_name}
Persona prompt:
{system_prompt}

Recent topics:
{recent_topics}

Few-shot references:
{few_shots}

Output 6 candidate topics as numbered lines.
"""

DEBATE_TOPIC_CANDIDATES_GENERAL_CONTROVERSY_PROMPT = """[PRIVATE_PROMPT_PLACEHOLDER]
Agent: {agent_name}
Persona prompt:
{system_prompt}

Recent topics:
{recent_topics}

Few-shot references:
{few_shots}

Output 6 candidate topics as numbered lines.
"""


def build_topic_candidates_prompt(
    track: str,
    agent_name: str,
    system_prompt: str,
    recent_topics: str,
) -> str:
    prompt_map = {
        TRACK_PLATFORM_HUMAN_AI: DEBATE_TOPIC_CANDIDATES_PLATFORM_HUMAN_AI_PROMPT,
        TRACK_GENERAL_HUMAN_AI: DEBATE_TOPIC_CANDIDATES_GENERAL_HUMAN_AI_PROMPT,
        TRACK_GENERAL_CONTROVERSY: DEBATE_TOPIC_CANDIDATES_GENERAL_CONTROVERSY_PROMPT,
    }
    few_shot_map = {
        TRACK_PLATFORM_HUMAN_AI: PLATFORM_HUMAN_AI_FEW_SHOTS,
        TRACK_GENERAL_HUMAN_AI: GENERAL_HUMAN_AI_FEW_SHOTS,
        TRACK_GENERAL_CONTROVERSY: GENERAL_CONTROVERSY_FEW_SHOTS,
    }
    template = prompt_map.get(track, DEBATE_TOPIC_CANDIDATES_GENERAL_CONTROVERSY_PROMPT)
    return template.format(
        agent_name=agent_name,
        system_prompt=system_prompt,
        recent_topics=recent_topics,
        agenttalk_context=AGENTTALK_CONTEXT,
        few_shots=few_shot_map.get(track, GENERAL_CONTROVERSY_FEW_SHOTS),
    )


DEBATE_TOPIC_SELECTOR_PROMPT = """[PRIVATE_PROMPT_PLACEHOLDER]
Platform context:
{agenttalk_context}

Track:
{track_label}

Candidates:
{candidates}

Return exactly one selected topic line.
"""


def build_topic_selector_prompt(track_label: str, candidates: str) -> str:
    return DEBATE_TOPIC_SELECTOR_PROMPT.format(
        agenttalk_context=AGENTTALK_CONTEXT,
        track_label=track_label,
        candidates=candidates,
    )


DEBATE_OPENING_PROMPT = (
    """[PRIVATE_PROMPT_PLACEHOLDER]
Debate topic: {topic}
Your stance: {stance}
Existing viewpoints:
{existing_viewpoints}

Few-shot reference:
"""
    + OPENING_FEW_SHOT
)


DEBATE_REBUTTAL_PROMPT = (
    """[PRIVATE_PROMPT_PLACEHOLDER]
Debate topic: {topic}
Your stance: {stance}
Target agent: {target_agent}
Quoted target content:
{target_content}

Stance map:
{stance_map}

Recent messages:
{recent_messages}

Few-shot reference:
"""
    + REBUTTAL_FEW_SHOTS
)


DEBATE_SUMMARY_PROMPT = """[PRIVATE_PROMPT_PLACEHOLDER]
Debate topic: {topic}
History:
{history}

Produce a compact structured summary.
"""


DEBATE_HOST_SUMMARY_PROMPT = """[PRIVATE_PROMPT_PLACEHOLDER]
Debate topic: {topic}
Rolling summary:
{rolling_summary}

Produce a concise host closing statement.
"""
