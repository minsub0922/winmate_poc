"""모델 클라이언트 — 실제 호출 없이 가짜 전송으로: Gemini 요청 단계 낮추기 · OpenAI 호환 · 기밀 차단 · 녹화/재생 · 3D 분석."""
import json
import unittest

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # noqa: E402 — python -m unittest tests.x 로도 돌게
from _util import catalog, temp_settings

from birdseye import samples
from birdseye.analyze3d import analyze, apply_request_rules, normalize, rule_brief
from birdseye.llm import ModelClient, ModelError
from birdseye.rules import Rules
from birdseye.scene3d import layout_info

GOOD = {"concept": "modern_minimal", "floor": "light_oak", "wall": "cool_white", "accent": "white_metal", "fabric": "gray",
        "light_k": 4000, "lighting": "day", "plants": "few", "screen_content": "brand", "understanding": "'밝은 미니멀 로비'",
        "concept_reason": "테스트", "finish_reason": "테스트", "lighting_reason": "테스트", "furniture": []}


class FakeGemini:
    def __init__(self, fail_shapes=("thinking",)):
        self.calls = []
        self.fail = fail_shapes

    def __call__(self, url, body, headers, timeout):
        g = body["generationConfig"]
        shape = "thinking" if "thinkingConfig" in g else ("schema" if "responseJsonSchema" in g else "json")
        self.calls.append(shape)
        if shape in self.fail:
            raise ModelError("HTTP 400: unsupported field")
        assert headers.get("x-goog-api-key") == "test-key"
        return {"candidates": [{"content": {"parts": [{"text": "생각", "thought": True}, {"text": "```json\n" + json.dumps(GOOD) + "\n```"}]}}]}


class LlmTest(unittest.TestCase):
    def test_gemini_degrades_from_thinking_to_schema(self):
        s = temp_settings({"GEMINI_API_KEY": "test-key", "GEMINI_THINKING_LEVEL": "low"})
        fake = FakeGemini()
        c = ModelClient(s, "LLM", transport=fake)
        obj, meta = c.generate_json("sys", "user", {"type": "object"}, "t")
        self.assertEqual(obj["concept"], "modern_minimal")
        self.assertEqual(meta["source"], "llm")
        self.assertEqual(meta["request_shape"], "schema")
        self.assertEqual(fake.calls, ["thinking", "schema"])

    def test_gemini_last_resort_json_only(self):
        s = temp_settings({"GEMINI_API_KEY": "test-key"})
        fake = FakeGemini(fail_shapes=("schema",))
        obj, meta = ModelClient(s, "LLM", transport=fake).generate_json("sys", "user", {"type": "object"}, "t")
        self.assertEqual(meta["request_shape"], "json-only")
        self.assertEqual(obj["floor"], "light_oak")

    def test_no_key_falls_back_without_calling(self):
        s = temp_settings()
        called = []
        obj, meta = ModelClient(s, "LLM", transport=lambda *a: called.append(a)).generate_json("s", "u", {}, "t")
        self.assertIsNone(obj)
        self.assertEqual(meta["source"], "rules")
        self.assertFalse(called)

    def test_confidential_blocked_unless_allowed(self):
        s = temp_settings({"GEMINI_API_KEY": "test-key"})
        obj, meta = ModelClient(s, "I2T", transport=FakeGemini(())).generate_json("s", "u", {}, "t", confidential=True)
        self.assertIsNone(obj)
        self.assertIn("ALLOW_CONFIDENTIAL", meta["reason"])
        s2 = temp_settings({"GEMINI_API_KEY": "test-key", "I2T_ALLOW_CONFIDENTIAL": "true"})
        obj2, _ = ModelClient(s2, "I2T", transport=FakeGemini(())).generate_json("s", "u", {}, "t", confidential=True)
        self.assertIsNotNone(obj2)

    def test_openai_compat_ladder(self):
        s = temp_settings({"LLM_PROVIDER": "openai_compat", "LLM_BASE_URL": "http://intra.example/v1", "LLM_API_KEY": "k"})
        shapes = []

        def fake(url, body, headers, timeout):
            self.assertTrue(url.endswith("/v1/chat/completions"))
            rf = (body.get("response_format") or {}).get("type", "plain")
            shapes.append(rf)
            if rf == "json_schema":
                raise ModelError("HTTP 400: json_schema not supported")
            return {"choices": [{"message": {"content": json.dumps(GOOD)}}]}

        obj, meta = ModelClient(s, "LLM", transport=fake).generate_json("s", "u", {"type": "object"}, "t")
        self.assertEqual(shapes, ["json_schema", "json_object"])
        self.assertEqual(meta["request_shape"], "json_object")

    def test_record_then_replay(self):
        s = temp_settings({"GEMINI_API_KEY": "test-key", "MODEL_MODE": "record"})
        ModelClient(s, "LLM", transport=FakeGemini(())).generate_json("s", "u", {}, "t")
        s.file_vals["MODEL_MODE"] = "replay"
        obj, meta = ModelClient(s, "LLM", transport=lambda *a: self.fail("재생 모드는 호출하면 안 됨")).generate_json("s", "u", {}, "t")
        self.assertEqual(meta["source"], "replay")
        self.assertEqual(obj["concept"], "modern_minimal")


class Analyze3dTest(unittest.TestCase):
    def setUp(self):
        self.cat = catalog()
        self.p2 = samples.build_lobby_2d(self.cat)
        self.p3 = samples.build_lobby_3d(self.cat, "x")
        self.info = layout_info(self.p3, self.p2, self.cat, Rules())

    def test_rule_brief_for_gallery_lobby(self):
        b = rule_brief(self.p3, self.info)
        self.assertEqual(b["concept"], "gallery_warm")
        self.assertIn("갤러리", b["understanding"])
        types = {f["type"] for f in b["furniture"]}
        self.assertIn("bench", types)  # 2D 집기 블록 그대로

    def test_model_output_is_normalized(self):
        raw = dict(GOOD, floor="gold_floor", light_k=3300)
        fallback = rule_brief(self.p3, self.info)
        b, fixed = normalize(raw, fallback, True, self.p3["input"]["products"])
        self.assertEqual(b["concept"], "modern_minimal")
        self.assertEqual(b["floor"], fallback["floor"])  # 목록에 없는 값은 규칙 값으로
        self.assertIn("floor", fixed)

    def test_analyze_with_fake_model_and_request_rules(self):
        s = temp_settings({"GEMINI_API_KEY": "test-key"})
        b = analyze(self.p3, self.info, self.cat, ModelClient(s, "LLM", transport=FakeGemini(())))
        self.assertEqual(b["meta"]["source"], "llm")
        req = apply_request_rules(b, "더 밝게, 식물은 빼고", self.info)
        self.assertEqual(req["lighting"], "day")
        self.assertEqual(req["plants"], "few")


if __name__ == "__main__":
    unittest.main()
