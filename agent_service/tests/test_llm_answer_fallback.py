import unittest

from app.clients.llm_client import LLMClient
from app.schemas.models import AnswerOutput


class TestAnswerOutputFallback(unittest.TestCase):
    def setUp(self) -> None:
        self.client = LLMClient()

    def test_plain_text_can_be_coerced_to_answer_output(self) -> None:
        text = "我觉得这波消费回暖没那么快，工资没涨，大家还是会更谨慎。"
        result = self.client._coerce_plain_answer_output(text)
        self.assertIsInstance(result, AnswerOutput)
        self.assertEqual(result.content, text)
        self.assertTrue(result.viewpoint)
        self.assertEqual(result.evidence, [])
        self.assertEqual(result.references, [])

    def test_detect_json_parse_error(self) -> None:
        exc = ValueError("1 validation error for AnswerOutput Invalid JSON: expected value at line 1 column 1")
        self.assertTrue(self.client._is_json_parse_error(exc))

    def test_should_use_plain_for_glm_or_bigmodel(self) -> None:
        class FakeLLM:
            def __init__(self, model_name: str, openai_api_base: str):
                self.model_name = model_name
                self.openai_api_base = openai_api_base

        glm_llm = FakeLLM("glm-4.7", "https://open.bigmodel.cn/api/paas/v4")
        self.assertTrue(self.client._should_use_plain_answer_output(glm_llm))

        gpt_llm = FakeLLM("gpt-5-mini", "https://api.openai.com/v1")
        self.assertFalse(self.client._should_use_plain_answer_output(gpt_llm))

    def test_clean_markdown_keeps_paragraph_and_list_structure(self) -> None:
        raw = "## 标题\\n\\n- 第一条\\n- 第二条\\n\\n1. 序号一\\n2. 序号二\\n\\n**结论**"
        cleaned = self.client._clean_markdown_formatting(raw)
        self.assertNotIn("##", cleaned)
        self.assertIn("- 第一条", cleaned)
        self.assertIn("1. 序号一", cleaned)
        self.assertIn("结论", cleaned)


if __name__ == "__main__":
    unittest.main()
