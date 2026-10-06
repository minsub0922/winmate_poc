"""기록 · 재생 카세트 — MODEL_MODE=record 로 남기고 replay 로 다시 쓴다.

경로: `MODEL_CASSETTE_DIR/<capability>/<task>/<sha256(정규화 요청)>.json`

정규화 요청 = API 요청에서 결과에 영향을 주는 값만(기밀 표시 · metadata · 호출 ID 는 뺀다).
이미지는 file_id 대신 **내용 해시**로 바꿔 넣는다 — 맥과 사내망의 files 서비스 ID 가 달라도 같은 키가 된다.
제공자 · 모델 이름도 키에 넣지 않는다(맥에서 기록 → 사내망에서 재생해 회귀 비교).

생성 이미지(t2i)는 카세트 옆 파일(`<key>.<n>.png`)로 두고, 재생할 때 files 서비스에 다시 저장해 새 file_id 를 돌려준다.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from winmate_common.ids import now_iso

from .config import cassette_dir

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe(name: str) -> str:
    return _SAFE.sub("_", name or "_")[:120] or "_"


def request_key(payload: dict[str, Any]) -> str:
    canon = json.dumps(_drop_none(payload), sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _drop_none(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _drop_none(x) for k, x in v.items() if x is not None}
    if isinstance(v, list):
        return [_drop_none(x) for x in v]
    return v


def path_for(capability: str, task: str, key: str) -> Path:
    return cassette_dir() / _safe(capability) / _safe(task) / f"{key}.json"


def load(capability: str, task: str, key: str) -> dict[str, Any] | None:
    p = path_for(capability, task, key)
    if not p.is_file():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    blobs = []
    for name in data.get("blobs", []):
        bp = p.parent / name
        blobs.append(bp.read_bytes() if bp.is_file() else b"")
    data["_blobs"] = blobs
    return data


def save(capability: str, task: str, key: str, *, request: dict[str, Any], response: dict[str, Any],
         provider: str | None, model: str | None, blobs: list[tuple[bytes, str]] | None = None) -> Path:
    p = path_for(capability, task, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    for i, (data, ext) in enumerate(blobs or []):
        name = f"{key}.{i}.{ext.lstrip('.') or 'bin'}"
        (p.parent / name).write_bytes(data)
        names.append(name)
    doc = {
        "capability": capability, "task": task, "key": key, "recorded_at": now_iso(),
        "provider": provider, "model": model, "request": _drop_none(request), "response": response, "blobs": names,
    }
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    tmp.replace(p)
    return p
