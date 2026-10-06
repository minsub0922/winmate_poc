"""임베딩 — POST /v1/embed.

EMBEDDING_PROVIDER
- lsa(기본) · none → 501 EMBEDDING_DISABLED (kb 서비스가 자체 LSA 를 쓴다)
- local → sentence-transformers(설치돼 있을 때만, 늦게 import). EMBEDDING_MODEL_PATH 가 있으면 그 폴더, 없으면 EMBEDDING_MODEL.
  e5 계열은 "query: " · "passage: " 접두어를 붙인다. LOCAL_MODEL_DEVICE(cpu 기본) · HF_HOME · HF_HUB_OFFLINE 그대로 쓴다.
- openai_compat → EMBEDDING_BASE_URL · EMBEDDING_API_KEY 의 /embeddings
- internal → 501(자리만)
- MODEL_MODE=mock(또는 EMBEDDING_PROVIDER=mock): 글자 n-gram 해시 벡터(결정적, 비슷한 글은 비슷한 벡터)
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any

import numpy as np

from winmate_common.env import resolve_path
from winmate_common.errors import ApiError

from . import config
from .errors import not_configured
from .runtime import track, with_retries
from .schemas import EmbedRequest

log = logging.getLogger("winmate.ai_tools.embed")
_models: dict[str, Any] = {}


def hash_vector(text: str, dim: int) -> list[float]:
    """글자 2·3-gram 특징 해싱 → L2 정규화."""
    v = np.zeros(dim, dtype=np.float64)
    s = f" {' '.join((text or '').lower().split())} "
    for n in (2, 3):
        for i in range(max(0, len(s) - n + 1)):
            h = int.from_bytes(hashlib.blake2b(s[i:i + n].encode("utf-8"), digest_size=8).digest(), "big")
            v[h % dim] += 1.0 if (h >> 63) & 1 else -1.0
    norm = float(np.linalg.norm(v))
    if norm == 0:
        v[0] = 1.0
        norm = 1.0
    return [round(float(x), 6) for x in v / norm]


def local_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("sentence_transformers") is not None
    except Exception:  # noqa: BLE001
        return False


async def local_embed(ec: config.EmbedConfig, texts: list[str], kind: str) -> list[list[float]]:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ApiError(501, "NOT_CONFIGURED",
                       "sentence-transformers 가 설치되어 있지 않아 로컬 임베딩(EMBEDDING_PROVIDER=local)을 쓸 수 없습니다. "
                       "EMBEDDING_PROVIDER=lsa(kb 자체 LSA) 또는 openai_compat 를 쓰거나, 플랫폼 담당에게 설치를 요청하세요",
                       {"provider": "local", "missing": "sentence-transformers"}) from exc
    path = ec.model
    if ec.model_path:
        p = resolve_path(ec.model_path)
        if Path(p).exists():
            path = str(p)
    model = _models.get(path)
    if model is None:
        model = await asyncio.to_thread(SentenceTransformer, path, device=ec.device)
        _models[path] = model
    prefix = ("query: " if kind == "query" else "passage: ") if "e5" in ec.model.lower() else ""
    arr = await asyncio.to_thread(model.encode, [prefix + t for t in texts], normalize_embeddings=True, convert_to_numpy=True)
    return [list(map(float, row)) for row in arr]


async def embed(req: EmbedRequest) -> dict[str, Any]:
    ec = config.embed_config()
    if ec.provider in ("lsa", "none", ""):
        raise ApiError(501, "EMBEDDING_DISABLED",
                       f"임베딩을 쓰지 않는 설정입니다(EMBEDDING_PROVIDER={ec.provider}) — kb 서비스는 자체 LSA 를 씁니다",
                       {"provider": ec.provider})
    async with track("embed", "embed", request=req.model_dump()) as call:
        call.provider_name, call.model = ec.provider, ec.model
        if call.effective == "mock" or ec.provider == "mock":
            call.provider_name = "mock"
            dim = ec.dim or 384
            vectors = [hash_vector(t, dim) for t in req.texts]
        elif ec.provider == "local":
            vectors = await local_embed(ec, req.texts, req.kind)
        elif ec.provider == "openai_compat":
            from .providers.openai_compat import embed as oa_embed

            vectors = await with_retries(lambda: oa_embed(ec.base_url, ec.api_key, ec.model, req.texts, ec.timeout_s),
                                         cap="embed", timeout_s=ec.timeout_s + 5, call=call)
        elif ec.provider == "internal":
            raise not_configured("사내 임베딩 제공자(internal)", provider="internal",
                                 hint="OpenAI 호환이면 EMBEDDING_PROVIDER=openai_compat + EMBEDDING_BASE_URL 을 쓰세요")
        else:
            raise not_configured(f"알 수 없는 EMBEDDING_PROVIDER '{ec.provider}'", provider=ec.provider)
        out = {"provider": call.provider_name, "model": ec.model, "dim": len(vectors[0]) if vectors else (ec.dim or 0),
               "vectors": vectors}
        call.response = out
        return out


def available(ec: config.EmbedConfig | None = None) -> bool:
    ec = ec or config.embed_config()
    if ec.provider in ("lsa", "none", ""):
        return False
    if ec.provider == "mock" or config.model_mode() == "mock":
        return True
    if ec.provider == "local":
        return local_available()
    if ec.provider == "openai_compat":
        return bool(ec.base_url)
    return False
