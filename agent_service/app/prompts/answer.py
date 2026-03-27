"""
Sanitized answer/comment prompts.

The original answer generation prompt details are redacted.
"""

EXPRESSIVENESS_INSTRUCTIONS = {
    "terse": "[LENGTH_POLICY] Keep very short output.",
    "balanced": "[LENGTH_POLICY] Keep medium output.",
    "verbose": "[LENGTH_POLICY] Keep detailed output.",
    "dynamic": "[LENGTH_POLICY] Adjust output length by topic relevance.",
}

ANSWER_USER_PROMPT = """[PRIVATE_PROMPT_PLACEHOLDER]
Task: answer a community question in natural first-person style.

Question title: {question_title}
Question content: {question_content}
{search_results_section}
{existing_answers_section}

Style policy:
{expressiveness_instruction}

Output rules:
- Return plain text only.
- Avoid markdown formatting.
- Keep persona-consistent viewpoint.
"""

EXISTING_ANSWERS_SECTION = """
[EXISTING_ANSWERS]
{existing_answers_text}
"""

COMMENT_USER_PROMPT = """[PRIVATE_PROMPT_PLACEHOLDER]
Task: comment on an existing answer.

Target answer:
{answer_content}

Style policy:
{expressiveness_instruction}

Output rules:
- Return 1-3 short sentences.
- Keep plain text only.
- Keep first-person and natural tone.
"""
