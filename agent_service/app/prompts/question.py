"""
Sanitized question-task prompts.

The original task prompt copywriting is redacted for open-source publishing.
"""

EXPRESSIVENESS_INSTRUCTIONS = {
    "terse": "[LENGTH_POLICY] Keep very short output.",
    "balanced": "[LENGTH_POLICY] Keep medium output.",
    "verbose": "[LENGTH_POLICY] Keep detailed output.",
    "dynamic": "[LENGTH_POLICY] Adjust output length by relevance and confidence.",
}

QUESTION_MEMORY_SECTION = """
[MEMORY_CONTEXT]
Recent questions:
{recent_questions_text}

Recent topics:
{recent_topics_text}
"""

QUESTION_USER_PROMPT = """[PRIVATE_PROMPT_PLACEHOLDER]
Task: create one community-style question from a trending topic.

Inputs:
- category: {category}
- topic: {topic}
{search_results_section}
{memory_section}

Style policy:
{expressiveness_instruction}

Output rules:
- Return plain text only.
- Keep first-person and natural tone.
- Avoid markdown formatting.
"""
