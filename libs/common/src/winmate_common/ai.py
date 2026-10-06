"""ai-tools 호출 도우미 — 기능 서비스는 외부 모델을 직접 부르지 않고 이것만 쓴다.

    from winmate_common.ai import ai
    data = await ai().json("rq.extract_form", prompt, schema=Form.model_json_schema(), confidential=True)
    text = await ai().text("rq.email", prompt)
    img  = await ai().generate_image("img.generate", prompt, aspect="16:9", n=2)

task 이름은 `<기능 코드 소문자>.<동작>` (예: rq.extract_form, mi.area_market). 호출 로그·기록/재생·mock 고정 응답
(`mocks/ai-tools/<task>.json`)의 키가 된다.
"""
from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

from .client import ServiceClient

Image = str | dict[str, Any]   # file_id 문자열 또는 {"file_id"} · {"url"} · {"data_b64", "mime"}


def _img(x: Image) -> dict[str, Any]:
    return {"file_id": x} if isinstance(x, str) else x


def schema_of(model: type[BaseModel]) -> dict[str, Any]:
    return model.model_json_schema()


def estimate_tokens(text: str) -> int:
    """대략적인 토큰 수(한국어 1.5자/토큰, 영어 4자/토큰 혼합 근사)."""
    if not text:
        return 0
    hangul = sum(1 for ch in text if "가" <= ch <= "힣")
    other = len(text) - hangul
    return int(hangul / 1.5 + other / 3.5) + 1


class AI:
    def __init__(self) -> None:
        self.c = ServiceClient("ai-tools", timeout=300)
        self._caps: tuple[float, dict[str, Any]] | None = None

    async def capabilities(self, *, max_age_s: float = 30) -> dict[str, Any]:
        if self._caps and time.time() - self._caps[0] < max_age_s:
            return self._caps[1]
        caps = await self.c.get("/v1/capabilities")
        self._caps = (time.time(), caps)
        return caps

    # ── LLM ───────────────────────────────────────────
    async def chat(
        self,
        task: str,
        messages: list[dict[str, Any]],
        *,
        json_schema: dict[str, Any] | None = None,
        schema_name: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        confidential: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"task": task, "messages": messages, "confidential": confidential}
        if json_schema is not None:
            body["json_schema"] = json_schema
            body["schema_name"] = schema_name or "Output"
        if tools:
            body["tools"] = tools
        if tool_choice:
            body["tool_choice"] = tool_choice
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        return await self.c.post("/v1/llm/chat", json=body)

    async def json(
        self,
        task: str,
        prompt: str | list[dict[str, Any]],
        schema: dict[str, Any] | type[BaseModel],
        *,
        system: str | None = None,
        confidential: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """JSON 스키마에 맞는 결과(dict)를 돌려준다. 스키마가 Pydantic 모델이면 그 모델로 검증한다."""
        model = schema if isinstance(schema, type) and issubclass(schema, BaseModel) else None
        js = schema_of(model) if model else schema  # type: ignore[arg-type]
        messages = prompt if isinstance(prompt, list) else [{"role": "user", "content": prompt}]
        if system:
            messages = [{"role": "system", "content": system}, *messages]
        res = await self.chat(task, messages, json_schema=js, schema_name=(model.__name__ if model else None),
                              confidential=confidential, temperature=temperature, max_tokens=max_tokens)
        data = res.get("json") or {}
        if model:
            return model.model_validate(data).model_dump()
        return data

    async def text(self, task: str, prompt: str, *, system: str | None = None, confidential: bool = False,
                   temperature: float | None = None, max_tokens: int | None = None) -> str:
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        if system:
            messages.insert(0, {"role": "system", "content": system})
        res = await self.chat(task, messages, confidential=confidential, temperature=temperature, max_tokens=max_tokens)
        return res.get("content") or ""

    # ── I2T ───────────────────────────────────────────
    async def vision(self, task: str, images: list[Image], prompt: str, *, schema: dict[str, Any] | type[BaseModel] | None = None,
                     want_bbox: bool = False, confidential: bool = False, max_tokens: int | None = None) -> dict[str, Any]:
        model = schema if isinstance(schema, type) and issubclass(schema, BaseModel) else None
        body: dict[str, Any] = {"task": task, "images": [_img(i) for i in images], "prompt": prompt,
                                "want_bbox": want_bbox, "confidential": confidential}
        if schema is not None:
            body["json_schema"] = schema_of(model) if model else schema
        if max_tokens:
            body["max_tokens"] = max_tokens
        res = await self.c.post("/v1/i2t/analyze", json=body)
        if model and res.get("json") is not None:
            res["json"] = model.model_validate(res["json"]).model_dump()
        return res

    # ── T2I ───────────────────────────────────────────
    async def generate_image(self, task: str, prompt: str, *, aspect: str | None = None, n: int = 1,
                             references: list[dict[str, Any]] | None = None, negative_prompt: str | None = None,
                             style: str | None = None, seed: int | None = None, confidential: bool = False,
                             metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"task": task, "prompt": prompt, "n": n, "confidential": confidential}
        for k, v in (("aspect", aspect), ("negative_prompt", negative_prompt), ("style", style), ("seed", seed),
                     ("reference_images", references), ("metadata", metadata)):
            if v is not None:
                body[k] = v
        return await self.c.post("/v1/t2i/generate", json=body)

    async def edit_image(self, task: str, image: Image, prompt: str, *, mask: dict[str, Any] | None = None,
                         references: list[dict[str, Any]] | None = None, aspect: str | None = None, n: int = 1,
                         confidential: bool = False, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"task": task, "image": _img(image), "prompt": prompt, "n": n, "confidential": confidential}
        for k, v in (("mask", mask), ("reference_images", references), ("aspect", aspect), ("metadata", metadata)):
            if v is not None:
                body[k] = v
        return await self.c.post("/v1/t2i/edit", json=body)

    # ── 웹 ─────────────────────────────────────────────
    async def websearch(self, task: str, query: str, *, locale: str = "ko-KR", max_sources: int = 8,
                        confidential: bool = False) -> dict[str, Any]:
        return await self.c.post("/v1/websearch", json={"task": task, "query": query, "locale": locale,
                                                         "max_sources": max_sources, "confidential": confidential})

    async def search(self, query: str, *, locale: str = "ko-KR", limit: int = 10) -> dict[str, Any]:
        return await self.c.post("/v1/search", json={"query": query, "locale": locale, "limit": limit})

    async def fetch(self, url: str, *, max_chars: int = 20000) -> dict[str, Any]:
        return await self.c.post("/v1/fetch", json={"url": url, "max_chars": max_chars})

    async def embed(self, texts: list[str], *, kind: str = "passage") -> dict[str, Any]:
        return await self.c.post("/v1/embed", json={"texts": texts, "kind": kind})


_ai: AI | None = None


def ai() -> AI:
    global _ai
    if _ai is None:
        _ai = AI()
    return _ai
