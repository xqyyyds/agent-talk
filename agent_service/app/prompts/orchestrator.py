"""
Sanitized orchestrator prompts.

Private orchestration logic text is redacted for open-source publishing.
"""

ORCHESTRATOR_SYSTEM_PROMPT = """[PRIVATE_PROMPT_PLACEHOLDER]
You are a task orchestrator agent.
Execute tools in the expected order and do not fabricate tool outputs.
"""

HOTSPOT_TASK_TEMPLATE = """[PRIVATE_PROMPT_PLACEHOLDER]
Hotspot task:
- topic: {topic}
- category: {category}
- source: {source}

Question instruction:
{question_instruction}

Answerers ({answerer_count}):
{answerer_lines}

Return final status in plain text.
"""

ZHIHU_QUESTION_INSTRUCTION = """[PRIVATE_PROMPT_PLACEHOLDER]
Use source title/content directly.
- title: \"{clean_title}\"
- content: \"{clean_content}\"
- agent_username: \"system\"
"""

OTHER_QUESTION_INSTRUCTION = """[PRIVATE_PROMPT_PLACEHOLDER]
Generate a discussion-oriented title and short content.
- agent_username: \"{questioner_name}\"
"""
