"""모델 호출(LLM · I2T) — winmate .env 의 서비스 설정을 그대로 쓴다.

provider: gemini | openai_compat | internal(= openai_compat 형식) | mock
MODEL_MODE: live | record(호출 + 저장) | replay(저장본만) | mock(호출 안 함)
호출이 안 되거나 실패하면 None 을 돌려주고, 호출한 쪽은 규칙 기반 결과로 넘어간다(이유는 meta 에 남김).
표준 라이브러리(urllib)만 쓴다.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
import time
import urllib.error
import urllib.request

from .config import Settings


class ModelError(Exception):
    pass


def _strip_json(text: str):
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", t, flags=re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    raise ModelError("JSON 응답을 읽지 못했어요")


def parse_data_url(url: str) -> tuple[str, bytes]:
    m = re.match(r"data:([\w/+.-]+);base64,(.*)$", url or "", flags=re.S)
    if not m:
        raise ModelError("이미지 형식이 data URL 이 아니에요")
    return m.group(1), base64.b64decode(m.group(2))


class _Rate:
    def __init__(self, rpm: int):
        self.rpm = max(0, rpm)
        self.calls: list[float] = []
        self.lock = threading.Lock()

    def wait(self):
        if not self.rpm:
            return
        with self.lock:
            now = time.time()
            self.calls = [t for t in self.calls if now - t < 60]
            if len(self.calls) >= self.rpm:
                time.sleep(max(0.0, 60 - (now - self.calls[0])) + 0.05)
            self.calls.append(time.time())


class ModelClient:
    def __init__(self, settings: Settings, service: str = "LLM", transport=None):
        self.s = settings
        self.cfg = settings.service(service)
        self.mode = settings.model_mode
        self.rate = _Rate(self.cfg["rpm"])
        cas = settings.path("MODEL_CASSETTE_DIR")  # winmate .env 의 녹화 폴더를 쓰되 조감도 하위 폴더로 나눔
        self.cassettes = (cas / "birdseye") if cas else settings.data_dir / "cassettes"
        self.log_path = settings.data_dir / "model_calls.jsonl"
        self.log_level = (settings.get("MODEL_CALL_LOG", "meta") or "meta").lower()
        self.transport = transport or self._http

    # ── 상태 ──
    def status(self) -> dict:
        reason = self.unavailable_reason()
        return {"service": self.cfg["name"], "provider": self.cfg["provider"], "model": self.cfg["model"], "mode": self.mode,
                "available": reason is None, "reason": reason}

    def unavailable_reason(self, confidential: bool = False) -> str | None:
        if self.mode == "mock" or self.cfg["provider"] == "mock":
            return "mock 모드 — 규칙 기반으로 판단"
        if self.mode == "replay":
            return None
        if self.cfg["provider"] == "gemini" and not self.cfg["api_key"]:
            return "API 키 없음(GEMINI_API_KEY)"
        if self.cfg["provider"] in ("openai_compat", "internal") and not self.cfg["base_url"]:
            return f"{self.cfg['name']}_BASE_URL 없음"
        if confidential and not self.cfg["allow_confidential"]:
            return f"기밀 표시된 작업 — {self.cfg['name']}_ALLOW_CONFIDENTIAL=false 라 외부 모델로 보내지 않음"
        return None

    # ── 호출 ──
    def generate_json(self, system: str, user: str, schema: dict, schema_name: str, images: list[str] | None = None,
                      confidential: bool = False) -> tuple[dict | None, dict]:
        meta = {"service": self.cfg["name"], "provider": self.cfg["provider"], "model": self.cfg["model"], "mode": self.mode,
                "schema": schema_name}
        why = self.unavailable_reason(confidential)
        if why:
            meta.update(source="rules", reason=why)
            return None, meta
        key = self._key(system, user, schema_name, images)
        cas = self.cassettes / f"{key}.json"
        if self.mode == "replay":
            if cas.exists():
                obj = json.loads(cas.read_text(encoding="utf-8"))
                meta.update(source="replay", cassette=cas.name)
                return obj, meta
            meta.update(source="rules", reason="replay 모드인데 저장된 응답이 없음")
            return None, meta
        t0 = time.time()
        try:
            self.rate.wait()
            if self.cfg["provider"] == "gemini":
                obj, used = self._gemini(system, user, schema, images)
            else:
                obj, used = self._openai(system, user, schema, schema_name, images)
            meta.update(source="llm", ms=round((time.time() - t0) * 1000), request_shape=used)
            if self.mode == "record":
                self.cassettes.mkdir(parents=True, exist_ok=True)
                cas.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
                meta["cassette"] = cas.name
            self._log(meta, system, user, obj, None)
            return obj, meta
        except Exception as e:  # noqa: BLE001
            meta.update(source="rules", reason=f"모델 호출 실패 — {type(e).__name__}: {str(e)[:200]}", ms=round((time.time() - t0) * 1000))
            self._log(meta, system, user, None, str(e))
            return None, meta

    def _key(self, system, user, schema_name, images):
        h = hashlib.sha1()
        for part in (self.cfg["name"], self.cfg["model"], system, user, schema_name):
            h.update((part or "").encode("utf-8"))
        for im in images or []:
            h.update(hashlib.sha1(im.encode("utf-8")).digest())
        return h.hexdigest()[:20]

    def _log(self, meta, system, user, obj, err):
        if self.log_level == "off":
            return
        rec = dict(meta, ts=time.strftime("%Y-%m-%dT%H:%M:%S"), ok=err is None)
        if err:
            rec["error"] = err[:500]
        if self.log_level == "full":
            rec["system"] = system
            rec["user"] = user
            rec["response"] = obj
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _http(self, url: str, body: dict, headers: dict, timeout: float) -> dict:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:600]
            raise ModelError(f"HTTP {e.code}: {detail}") from None

    # Gemini generateContent — 실패하면 요청 모양을 단계적으로 낮춘다
    def _gemini(self, system, user, schema, images):
        url = f"{self.cfg['base_url']}/v1beta/models/{self.cfg['model']}:generateContent"
        parts = [{"text": user}]
        for im in images or []:
            mime, raw = parse_data_url(im)
            parts.append({"inlineData": {"mimeType": mime, "data": base64.b64encode(raw).decode("ascii")}})
        base = {"contents": [{"role": "user", "parts": parts}], "systemInstruction": {"parts": [{"text": system}]}}
        gen = {"temperature": self.cfg["temperature"], "maxOutputTokens": self.cfg["max_output"], "responseMimeType": "application/json"}
        ladder = []
        g1 = dict(gen)
        if self.cfg["json_schema"]:
            g1["responseJsonSchema"] = schema
        if self.cfg["thinking"]:
            g1["thinkingConfig"] = {"thinkingLevel": self.cfg["thinking"]}
        ladder.append(("schema+thinking", g1))
        if self.cfg["thinking"]:
            g2 = {k: v for k, v in g1.items() if k != "thinkingConfig"}
            ladder.append(("schema", g2))
        ladder.append(("json-only", dict(gen)))
        last = None
        for name, g in ladder:
            body = dict(base, generationConfig=g)
            if name == "json-only":
                body["contents"][0]["parts"][0] = {"text": user + "\n\n다음 JSON 스키마를 지켜 JSON 하나만 출력:\n" + json.dumps(schema, ensure_ascii=False)}
            try:
                resp = self.transport(url, body, {"x-goog-api-key": self.cfg["api_key"]}, self.cfg["timeout"])
            except ModelError as e:
                last = e
                if "HTTP 400" in str(e):
                    continue
                raise
            cands = resp.get("candidates") or []
            if not cands:
                raise ModelError(f"응답 후보 없음: {json.dumps(resp, ensure_ascii=False)[:300]}")
            texts = [p.get("text", "") for p in (cands[0].get("content") or {}).get("parts", []) if not p.get("thought")]
            return _strip_json("".join(texts)), name
        raise last or ModelError("요청 실패")

    def _openai(self, system, user, schema, schema_name, images):
        base = self.cfg["base_url"]
        url = base + ("/chat/completions" if base.endswith("/v1") or "/v1/" in base + "/" else "/v1/chat/completions")
        content = [{"type": "text", "text": user}]
        for im in images or []:
            content.append({"type": "image_url", "image_url": {"url": im}})
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": content if images else user}]
        body = {"model": self.cfg["model"], "messages": msgs, "temperature": self.cfg["temperature"], "max_tokens": self.cfg["max_output"]}
        ladder = []
        if self.cfg["json_schema"]:
            ladder.append(("json_schema", dict(body, response_format={"type": "json_schema", "json_schema": {"name": schema_name, "schema": schema}})))
        ladder.append(("json_object", dict(body, response_format={"type": "json_object"})))
        plain = dict(body)
        plain["messages"] = [msgs[0], {"role": "user", "content": (content if images else user + "\n\nJSON 스키마:\n" + json.dumps(schema, ensure_ascii=False))}]
        ladder.append(("plain", plain))
        headers = {"Authorization": f"Bearer {self.cfg['api_key']}"} if self.cfg["api_key"] else {}
        last = None
        for name, b in ladder:
            try:
                resp = self.transport(url, b, headers, self.cfg["timeout"])
            except ModelError as e:
                last = e
                if "HTTP 400" in str(e) or "HTTP 422" in str(e):
                    continue
                raise
            txt = resp["choices"][0]["message"]["content"]
            return _strip_json(txt if isinstance(txt, str) else json.dumps(txt)), name
        raise last or ModelError("요청 실패")
