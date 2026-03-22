import unittest

from app.core.debate_topic_mix import (
    TRACK_GENERAL_CONTROVERSY,
    TRACK_GENERAL_HUMAN_AI,
    TRACK_PLATFORM_HUMAN_AI,
    select_topic_track,
)
from app.prompts.debate import (
    DEBATE_HOST_SUMMARY_PROMPT,
    DEBATE_OPENING_PROMPT,
    DEBATE_REBUTTAL_PROMPT,
    build_topic_candidates_prompt,
    build_topic_selector_prompt,
)


class TestDebateTopicMix(unittest.TestCase):
    def test_select_topic_track_respects_fixed_boundaries(self) -> None:
        self.assertEqual(select_topic_track(0.00), TRACK_PLATFORM_HUMAN_AI)
        self.assertEqual(select_topic_track(0.4199), TRACK_PLATFORM_HUMAN_AI)
        self.assertEqual(select_topic_track(0.42), TRACK_GENERAL_HUMAN_AI)
        self.assertEqual(select_topic_track(0.6999), TRACK_GENERAL_HUMAN_AI)
        self.assertEqual(select_topic_track(0.70), TRACK_GENERAL_CONTROVERSY)
        self.assertEqual(select_topic_track(0.9999), TRACK_GENERAL_CONTROVERSY)

    def test_platform_prompt_is_agenttalk_anchored(self) -> None:
        prompt = build_topic_candidates_prompt(
            TRACK_PLATFORM_HUMAN_AI,
            agent_name="逻辑炼金术士",
            system_prompt="你是一个擅长拆解平台互动的人。",
            recent_topics="- 无",
        )
        self.assertIn("AgentTalk", prompt)
        self.assertIn("真人用户与 AI Agent 共同发帖", prompt)
        self.assertIn("人类", prompt)
        self.assertIn("AI", prompt)
        self.assertIn("高质量示例", prompt)

    def test_general_human_ai_prompt_focuses_on_human_ai_conflict(self) -> None:
        prompt = build_topic_candidates_prompt(
            TRACK_GENERAL_HUMAN_AI,
            agent_name="逻辑炼金术士",
            system_prompt="你是一个擅长拆解平台互动的人。",
            recent_topics="- 无",
        )
        self.assertIn("人类", prompt)
        self.assertIn("AI", prompt)
        self.assertIn("不要求强绑定 AgentTalk", prompt)

    def test_general_controversy_prompt_focuses_on_broader_conflicts(self) -> None:
        prompt = build_topic_candidates_prompt(
            TRACK_GENERAL_CONTROVERSY,
            agent_name="逻辑炼金术士",
            system_prompt="你是一个擅长拆解平台互动的人。",
            recent_topics="- 无",
        )
        self.assertIn("社会", prompt)
        self.assertIn("职场", prompt)
        self.assertIn("不要强行写成人类 vs AI", prompt)

    def test_selector_prompt_uses_track_label(self) -> None:
        prompt = build_topic_selector_prompt("平台相关人机冲突", "- 题目A\n- 题目B")
        self.assertIn("平台相关人机冲突", prompt)
        self.assertIn("评论区", prompt)
        self.assertIn("真人用户与 AI Agent 共同发帖", prompt)

    def test_depth_prompts_encode_required_structure(self) -> None:
        self.assertIn("立场一句话", DEBATE_OPENING_PROMPT)
        self.assertIn("两个理由", DEBATE_OPENING_PROMPT)
        self.assertIn("预判", DEBATE_OPENING_PROMPT)

        self.assertIn("引用", DEBATE_REBUTTAL_PROMPT)
        self.assertIn("漏洞", DEBATE_REBUTTAL_PROMPT)
        self.assertIn("替代解释", DEBATE_REBUTTAL_PROMPT)
        self.assertIn("不要脑补对方没说过的立场", DEBATE_REBUTTAL_PROMPT)

        self.assertIn("最强观点", DEBATE_HOST_SUMMARY_PROMPT)
        self.assertIn("开放问题", DEBATE_HOST_SUMMARY_PROMPT)


if __name__ == "__main__":
    unittest.main()
