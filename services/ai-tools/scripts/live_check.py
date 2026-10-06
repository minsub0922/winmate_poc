#!/usr/bin/env python3
"""ai-tools 실제 제공자 점검 — 맥에서 실제 Gemini(또는 사내 OpenAI 호환 API)로 한 바퀴 돌린다.

    MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py
    MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py --provider openai_compat   # 사내망 이전 점검
    MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py --only llm_json,i2t
    MODEL_MODE=record uv run python services/ai-tools/scripts/live_check.py                      # 카세트도 남김

- 게이트웨이를 거치지 않고 서비스 함수(llm.chat · i2t.analyze · t2i.generate/edit · websearch.search)를 직접 부른다.
- Redis(5379)가 없으면 메모리(fakeredis)로 한도를 센다.
- T2I 결과는 files 서비스에 저장하고, files 서비스가 없으면 data/ai-tools/live_check/ 에 저장한다.
- 하나라도 실패하면 종료 코드 1.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import os
import sys
import time
import traceback
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

CHECKS = ["llm_text", "llm_json", "llm_tools", "i2t", "t2i", "t2i_edit", "websearch"]


class Skip(Exception):
    pass


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ai-tools 실제 제공자 점검")
    ap.add_argument("--provider", choices=["env", "gemini", "openai_compat"], default="env",
                    help="env(.env 그대로) · gemini · openai_compat(LLM/I2T/T2I/WEBSEARCH_BASE_URL 필요)")
    ap.add_argument("--only", default="", help=f"쉼표로 고른 점검만: {','.join(CHECKS)}")
    ap.add_argument("--out", default="", help="files 서비스가 없을 때 이미지를 저장할 폴더(기본 data/ai-tools/live_check)")
    return ap.parse_args()


def setup_env(args: argparse.Namespace) -> None:
    os.environ.setdefault("WINMATE_SERVICE", "ai-tools")
    os.environ.setdefault("MODEL_MODE", "live")
    if args.provider != "env":
        for cap in ("LLM", "I2T", "T2I", "WEBSEARCH"):
            value = "gemini_grounding" if (cap == "WEBSEARCH" and args.provider == "gemini") else args.provider
            os.environ[f"{cap}_PROVIDER"] = value


async def ensure_redis() -> str:
    from winmate_common.jobs import redis, set_redis_factory

    try:
        await asyncio.wait_for(redis().ping(), timeout=1.5)
        return "redis"
    except Exception:  # noqa: BLE001
        pass
    try:
        import fakeredis

        server = fakeredis.FakeServer()
        set_redis_factory(lambda: fakeredis.FakeAsyncRedis(server=server, decode_responses=True))
        return "fakeredis(메모리)"
    except ImportError:
        from winmate_ai_tools import limits

        async def _acquire(cfg: Any, units: int = 1) -> Any:
            return limits.Reservation(cfg.cap, units, limits.today(), False)

        limits.acquire = _acquire  # type: ignore[assignment]
        return "없음(한도 검사 생략)"


def test_image() -> bytes:
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (960, 640), (250, 250, 250))
    d = ImageDraw.Draw(im)
    d.ellipse((80, 120, 380, 420), fill=(220, 30, 40))          # 빨간 원
    d.rectangle((520, 160, 880, 460), fill=(30, 80, 200))       # 파란 사각형
    d.text((560, 500), "WINMATE", fill=(0, 0, 0))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


class Runner:
    def __init__(self, out_dir: Path):
        self.rows: list[tuple[str, str, int, str, str]] = []
        self.out_dir = out_dir
        self.generated: bytes | None = None

    async def sink(self, name: str, data: bytes, mime: str, meta: dict[str, Any], confidential: bool) -> str:
        from winmate_common.errors import ApiError
        from winmate_ai_tools import t2i

        try:
            return await t2i.files_sink(name, data, mime, meta, confidential)
        except ApiError:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            p = self.out_dir / name
            p.write_bytes(data)
            (self.out_dir / (name + ".json")).write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
            return f"local:{p}"

    async def run(self, name: str, fn: Callable[[], Awaitable[tuple[dict[str, Any], str]]]) -> None:
        from winmate_common.errors import ApiError

        t0 = time.perf_counter()
        try:
            res, note = await fn()
            ms = int((time.perf_counter() - t0) * 1000)
            who = f"{res.get('provider')}/{res.get('model')}"
            self.rows.append((name, "PASS", ms, who, note))
        except Skip as exc:
            self.rows.append((name, "SKIP", 0, "-", str(exc)))
        except ApiError as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            self.rows.append((name, "FAIL", ms, "-", f"{exc.status} {exc.code}: {exc.message[:120]}"))
        except Exception as exc:  # noqa: BLE001
            ms = int((time.perf_counter() - t0) * 1000)
            self.rows.append((name, "FAIL", ms, "-", f"{type(exc).__name__}: {exc}"[:160]))
            if os.environ.get("LIVE_CHECK_TRACE"):
                traceback.print_exc()

    def table(self) -> str:
        head = ("점검", "결과", "ms", "제공자/모델", "비고")
        rows = [head, *[(a, b, str(c), d, e) for a, b, c, d, e in self.rows]]
        widths = [max(_w(r[i]) for r in rows[:]) for i in range(4)]
        lines = []
        for i, r in enumerate(rows):
            lines.append("  ".join(_pad(r[j], widths[j]) for j in range(4)) + "  " + r[4])
            if i == 0:
                lines.append("-" * (sum(widths) + 8 + 30))
        return "\n".join(lines)


def _w(s: str) -> int:
    import unicodedata

    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s)


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _w(s))


async def main() -> int:
    args = parse_args()
    setup_env(args)

    from jsonschema import Draft202012Validator

    from winmate_common.env import settings
    from winmate_ai_tools import config, i2t, llm, t2i, websearch
    from winmate_ai_tools.schemas import (
        ChatMessage,
        ChatRequest,
        I2TRequest,
        ImageRef,
        MaskRef,
        T2IEditRequest,
        T2IGenerateRequest,
        ToolCall,
        ToolSpec,
        WebSearchRequest,
    )

    only = [c.strip() for c in args.only.split(",") if c.strip()] or CHECKS
    out_dir = Path(args.out) if args.out else settings().data_dir / "ai-tools" / "live_check"
    mode = config.model_mode()
    redis_kind = await ensure_redis()
    print(f"MODEL_MODE={mode} · 한도 카운터={redis_kind}")
    for cap in config.CAPS:
        c = config.load(cap)
        extra = f" base_url={c.base_url}" if c.provider_key == "openai_compat" else ""
        print(f"  {cap:<9} {c.provider}/{c.model}{extra}")
    if mode == "mock":
        print("주의: MODEL_MODE=mock 이라 실제 제공자를 부르지 않습니다(MODEL_MODE=live 로 실행하세요)")
    print()

    def user(text: str) -> ChatMessage:
        return ChatMessage(role="user", content=text)

    async def llm_text() -> tuple[dict[str, Any], str]:
        res = await llm.chat(ChatRequest(task="live.text", max_tokens=300,
                                         messages=[user("삼성 B2B 디스플레이 제안서의 첫 문장을 한 줄로 써 줘.")]))
        assert res["content"].strip(), "빈 응답"
        return res, res["content"].strip().replace("\n", " ")[:50]

    async def llm_json() -> tuple[dict[str, Any], str]:
        schema = {"type": "object", "properties": {
            "customer": {"type": "string"}, "products": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "budget_krw": {"anyOf": [{"type": "integer"}, {"type": "null"}]}}, "required": ["customer", "products", "budget_krw"]}
        res = await llm.chat(ChatRequest(task="live.json", json_schema=schema, schema_name="Extract", messages=[user(
            "다음 문장에서 고객사, 제품 목록, 예산(원)을 뽑아라: '가나다호텔 로비에 QMC 75인치 4대와 키오스크 2대를 3천만원 예산으로 검토'")]))
        errors = list(Draft202012Validator(schema).iter_errors(res["json"]))
        assert not errors, f"스키마 불일치: {errors[0].message}"
        return res, f"fallback={res['fallback']} {json.dumps(res['json'], ensure_ascii=False)[:60]}"

    async def llm_tools() -> tuple[dict[str, Any], str]:
        tools = [ToolSpec(name="get_product_spec", description="모델명으로 제품 스펙을 찾는다",
                          parameters={"type": "object", "properties": {"model": {"type": "string"}}, "required": ["model"]})]
        msgs = [user("QM75C 의 밝기를 알려줘. 반드시 도구로 확인해.")]
        r1 = await llm.chat(ChatRequest(task="live.tools", messages=msgs, tools=tools, tool_choice="required"))
        if not r1["tool_calls"] and r1["provider"] == "mock":
            raise Skip("mock 은 고정 응답(mocks/ai-tools/live.tools.json) 없이는 도구를 부르지 않습니다")
        assert r1["tool_calls"], f"도구 호출이 없습니다: {r1['content'][:80]}"
        tc = r1["tool_calls"][0]
        msgs2 = [*msgs, ChatMessage(role="assistant", content=r1["content"] or "", tool_calls=[ToolCall(**tc)]),
                 ChatMessage(role="tool", tool_call_id=tc["id"], name=tc["name"],
                             content=json.dumps({"model": "QM75C", "brightness_nits": 500}, ensure_ascii=False))]
        r2 = await llm.chat(ChatRequest(task="live.tools", messages=msgs2, tools=tools))   # 2턴: thought signature 왕복
        assert r2["content"].strip(), "두 번째 턴 응답이 비었습니다"
        return r2, f"fallback={r1['fallback']} {tc['name']}({json.dumps(tc['arguments'], ensure_ascii=False)}) → {r2['content'].strip()[:30]}"

    async def i2t_check() -> tuple[dict[str, Any], str]:
        schema = {"type": "object", "properties": {
            "shapes": {"type": "array", "items": {"type": "object", "properties": {"shape": {"type": "string"}, "color": {"type": "string"}},
                                                  "required": ["shape", "color"]}},
            "text": {"type": "string"}}, "required": ["shapes", "text"]}
        img = ImageRef(data_b64=base64.b64encode(test_image()).decode(), mime="image/png")
        res = await i2t.analyze(I2TRequest(task="live.i2t", images=[img], prompt="그림 속 도형과 색, 글자를 알려줘",
                                           json_schema=schema, want_bbox=True))
        errors = list(Draft202012Validator(schema).iter_errors(res["json"]))
        assert not errors, f"스키마 불일치: {errors[0].message}"
        return res, f"shapes={len(res['json']['shapes'])} text={res['json']['text']!r} boxes={len(res['boxes'])} {res['warnings'] or ''}"

    runner = Runner(out_dir)

    async def t2i_check() -> tuple[dict[str, Any], str]:
        res = await t2i.generate(T2IGenerateRequest(task="live.t2i", prompt="A modern hotel lobby with a large digital signage "
                                                    "display on the wall, photorealistic, daylight", aspect="16:9"),
                                 sink=runner.sink)
        img = res["images"][0]
        if img["file_id"].startswith("local:"):
            runner.generated = Path(img["file_id"][6:]).read_bytes()
        else:
            from winmate_common.platform import file_bytes

            runner.generated, _ = await file_bytes(img["file_id"])
        return res, f"{img['width']}x{img['height']} {img['file_id']} fallbacks={res['fallbacks']}"

    async def t2i_edit_check() -> tuple[dict[str, Any], str]:
        base = runner.generated or test_image()
        res = await t2i.edit(T2IEditRequest(task="live.t2i_edit", image=ImageRef(data_b64=base64.b64encode(base).decode()),
                                            prompt="Show a colorful coffee menu on the screen area",
                                            mask=MaskRef(box=[0.3, 0.2, 0.7, 0.6])), sink=runner.sink)
        img = res["images"][0]
        return res, f"{img['width']}x{img['height']} fallbacks={res['fallbacks']} {img['file_id']}"

    async def websearch_check() -> tuple[dict[str, Any], str]:
        res = await websearch.search(WebSearchRequest(task="live.websearch", query="삼성전자 스마트 사이니지 최신 소식"))
        assert res["summary"].strip(), "빈 요약"
        hidden = "" if res["returned_sources"] else "(WEBSEARCH_RETURN_SOURCES=false 라 숨김)"
        return res, f"요약 {len(res['summary'])}자 · 출처 {len(res['sources'])}{hidden} · 검색어 {res['queries'][:2]}"

    table: dict[str, Callable[[], Awaitable[tuple[dict[str, Any], str]]]] = {
        "llm_text": llm_text, "llm_json": llm_json, "llm_tools": llm_tools, "i2t": i2t_check, "t2i": t2i_check,
        "t2i_edit": t2i_edit_check, "websearch": websearch_check,
    }
    for name in only:
        if name not in table:
            print(f"알 수 없는 점검: {name}", file=sys.stderr)
            return 2
        await runner.run(name, table[name])
    print(runner.table())
    failed = [r for r in runner.rows if r[1] == "FAIL"]
    print()
    passed = sum(1 for r in runner.rows if r[1] == "PASS")
    print(f"{passed}/{len(runner.rows)} 통과" + (f" · 실패: {', '.join(r[0] for r in failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
