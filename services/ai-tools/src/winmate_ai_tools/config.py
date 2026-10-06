"""ai-tools 설정 — `.env` 값을 호출할 때마다 읽는다(테스트에서 환경 변수를 바꿔도 바로 반영).

코드의 기본값은 `.env.example` 과 같아야 한다. 기능(capability)마다 제공자·모델·한도·지원 여부를 따로 정한다.

    cfg = load("llm")      # LLM_* 키
    cfg.provider, cfg.model, cfg.supports_json_schema, cfg.rpm, ...
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from winmate_common import env
from winmate_common.env import repo_root, resolve_path

CAPS = ("llm", "i2t", "t2i", "websearch")
MODES = ("live", "mock", "record", "replay")
PREFIX = {"llm": "LLM", "i2t": "I2T", "t2i": "T2I", "websearch": "WEBSEARCH"}

# .env.example 과 같은 기본값
_DEFAULTS: dict[str, dict[str, object]] = {
    "llm": {"PROVIDER": "gemini", "MODEL": "gemini-3.1-flash-lite", "TIMEOUT_S": 90, "MAX_CONCURRENCY": 4,
            "RPM": 30, "DAILY_LIMIT": 2000},
    "i2t": {"PROVIDER": "gemini", "MODEL": "gemini-3.1-flash-lite", "TIMEOUT_S": 90, "MAX_CONCURRENCY": 4,
            "RPM": 30, "DAILY_LIMIT": 3000},
    "t2i": {"PROVIDER": "gemini", "MODEL": "gemini-3.1-flash-lite-image", "TIMEOUT_S": 120, "MAX_CONCURRENCY": 2,
            "RPM": 0, "DAILY_LIMIT": 100},
    "websearch": {"PROVIDER": "gemini_grounding", "MODEL": "gemini-3.5-flash-lite", "TIMEOUT_S": 60,
                  "MAX_CONCURRENCY": 2, "RPM": 0, "DAILY_LIMIT": 150},
}

GEMINI_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"


def model_mode() -> str:
    """MODEL_MODE: live | mock | record | replay (모르는 값은 live)."""
    mode = (env.get("MODEL_MODE", "live") or "live").lower()
    return mode if mode in MODES else "live"


def replay_fallback() -> str | None:
    """REPLAY_FALLBACK=mock 이면 카세트가 없을 때 mock 으로 답한다(기본: 404 CASSETTE_MISS)."""
    v = (env.get("REPLAY_FALLBACK") or "").lower()
    return v if v == "mock" else None


def cassette_dir() -> Path:
    return resolve_path(env.get("MODEL_CASSETTE_DIR", "./data/cassettes") or "./data/cassettes")


def cache_dir() -> Path:
    return resolve_path(env.get("CACHE_DIR", "./data/cache") or "./data/cache")


def mocks_dir() -> Path:
    """mock 고정 응답 폴더(기본 <루트>/mocks/ai-tools). 테스트는 AI_TOOLS_MOCKS_DIR 로 바꾼다."""
    custom = env.get("AI_TOOLS_MOCKS_DIR")
    return resolve_path(custom) if custom else repo_root() / "mocks" / "ai-tools"


def call_log_mode() -> str:
    """MODEL_CALL_LOG: full(요청·응답 본문까지) | meta(메타데이터만) | off."""
    v = (env.get("MODEL_CALL_LOG", "full") or "full").lower()
    return v if v in ("full", "meta", "off") else "full"


def call_log_retention_days() -> int:
    return env.get_int("MODEL_CALL_LOG_RETENTION_DAYS", 30)


def gemini_thinking_level() -> str | None:
    v = (env.get("GEMINI_THINKING_LEVEL", "low") or "").strip().lower()
    return None if v in ("", "none", "off", "default") else v


@dataclass(frozen=True)
class CapConfig:
    cap: str
    provider: str
    model: str
    base_url: str | None
    api_key: str | None
    timeout_s: float
    max_concurrency: int
    rpm: int
    daily_limit: int
    allow_confidential: bool
    # LLM
    max_input_tokens: int = 32000
    max_output_tokens: int = 4096
    temperature: float = 0.2
    supports_json_schema: bool = True
    supports_tools: bool = True
    supports_streaming: bool = True
    # I2T
    max_images_per_call: int = 4
    max_image_side_px: int = 1536
    supports_bbox: bool = True
    bbox_format: str = "gemini_yxyx_1000"
    # T2I
    default_aspect: str = "16:9"
    max_side_px: int = 1024
    supports_reference_images: bool = True
    max_reference_images: int = 4
    supports_edit: bool = True
    supports_mask: bool = False
    images_per_call: int = 1
    # WEBSEARCH
    return_sources: bool = False
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def provider_key(self) -> str:
        """제공자 이름 정규화(gemini_grounding → gemini)."""
        p = self.provider.lower()
        return {"gemini_grounding": "gemini", "openai": "openai_compat"}.get(p, p)

    def gemini_key(self) -> str | None:
        return self.api_key or env.get("GEMINI_API_KEY")

    def gemini_base_url(self) -> str:
        # <CAP>_BASE_URL 은 openai_compat 용. gemini 는 GEMINI_BASE_URL(사내 프록시 등)을 쓴다.
        return (env.get("GEMINI_BASE_URL", GEMINI_DEFAULT_BASE_URL) or GEMINI_DEFAULT_BASE_URL).rstrip("/")


def load(cap: str) -> CapConfig:
    if cap not in PREFIX:
        raise KeyError(cap)
    p = PREFIX[cap]
    d = _DEFAULTS[cap]

    def s(key: str, default: str | None = None) -> str | None:
        return env.get(f"{p}_{key}", default)

    def i(key: str, default: int) -> int:
        return env.get_int(f"{p}_{key}", default)

    def b(key: str, default: bool) -> bool:
        return env.get_bool(f"{p}_{key}", default)

    common = dict(
        cap=cap,
        provider=(s("PROVIDER", str(d["PROVIDER"])) or str(d["PROVIDER"])).lower(),
        model=s("MODEL", str(d["MODEL"])) or str(d["MODEL"]),
        base_url=(s("BASE_URL") or None),
        api_key=(s("API_KEY") or None),
        timeout_s=float(env.get_float(f"{p}_TIMEOUT_S", float(d["TIMEOUT_S"]))),  # type: ignore[arg-type]
        max_concurrency=max(1, i("MAX_CONCURRENCY", int(d["MAX_CONCURRENCY"]))),  # type: ignore[arg-type]
        rpm=max(0, i("RPM", int(d["RPM"]))),  # type: ignore[arg-type]
        daily_limit=max(0, i("DAILY_LIMIT", int(d["DAILY_LIMIT"]))),  # type: ignore[arg-type]
        allow_confidential=b("ALLOW_CONFIDENTIAL", False),
    )
    if cap == "llm":
        return CapConfig(
            **common,  # type: ignore[arg-type]
            max_input_tokens=i("MAX_INPUT_TOKENS", 32000),
            max_output_tokens=i("MAX_OUTPUT_TOKENS", 4096),
            temperature=env.get_float("LLM_TEMPERATURE", 0.2),
            supports_json_schema=b("SUPPORTS_JSON_SCHEMA", True),
            supports_tools=b("SUPPORTS_TOOLS", True),
            supports_streaming=b("SUPPORTS_STREAMING", True),
        )
    if cap == "i2t":
        return CapConfig(
            **common,  # type: ignore[arg-type]
            max_output_tokens=i("MAX_OUTPUT_TOKENS", 4096),
            temperature=env.get_float("I2T_TEMPERATURE", 0.2),
            max_images_per_call=max(1, i("MAX_IMAGES_PER_CALL", 4)),
            max_image_side_px=max(64, i("MAX_IMAGE_SIDE_PX", 1536)),
            supports_json_schema=b("SUPPORTS_JSON_SCHEMA", True),
            supports_bbox=b("SUPPORTS_BBOX", True),
            bbox_format=(s("BBOX_FORMAT", "gemini_yxyx_1000") or "gemini_yxyx_1000").lower(),
        )
    if cap == "t2i":
        return CapConfig(
            **common,  # type: ignore[arg-type]
            default_aspect=s("DEFAULT_ASPECT", "16:9") or "16:9",
            max_side_px=max(64, i("MAX_SIDE_PX", 1024)),
            supports_reference_images=b("SUPPORTS_REFERENCE_IMAGES", True),
            max_reference_images=max(0, i("MAX_REFERENCE_IMAGES", 4)),
            supports_edit=b("SUPPORTS_EDIT", True),
            supports_mask=b("SUPPORTS_MASK", False),
            images_per_call=max(1, i("IMAGES_PER_CALL", 1)),
        )
    return CapConfig(
        **common,  # type: ignore[arg-type]
        max_output_tokens=i("MAX_OUTPUT_TOKENS", 2048),
        temperature=env.get_float("WEBSEARCH_TEMPERATURE", 0.2),
        return_sources=b("RETURN_SOURCES", False),
    )


# ── 검색 API · 수집 · 임베딩 ───────────────────────────────

@dataclass(frozen=True)
class SearchConfig:
    provider: str          # none | brave | tavily | serper | google_cse | searxng | internal | mock
    base_url: str | None
    api_key: str | None
    cx: str | None         # google_cse 검색 엔진 ID(SEARCH_API_CX)
    timeout_s: float


def search_config() -> SearchConfig:
    return SearchConfig(
        provider=(env.get("SEARCH_API_PROVIDER", "none") or "none").lower(),
        base_url=env.get("SEARCH_API_BASE_URL"),
        api_key=env.get("SEARCH_API_KEY"),
        cx=env.get("SEARCH_API_CX"),
        timeout_s=env.get_float("SEARCH_API_TIMEOUT_S", 20.0),
    )


@dataclass(frozen=True)
class FetchConfig:
    enabled: bool
    user_agent: str
    respect_robots: bool
    rate_limit_rps: float
    timeout_s: float
    cache_ttl_hours: float
    allowed_domains: tuple[str, ...]
    max_bytes: int


def fetch_config() -> FetchConfig:
    domains = tuple(d.strip().lower().lstrip(".") for d in (env.get("WEB_FETCH_ALLOWED_DOMAINS") or "").split(",") if d.strip())
    return FetchConfig(
        enabled=env.get_bool("WEB_FETCH_ENABLED", True),
        user_agent=env.get("WEB_FETCH_USER_AGENT", "WinmateBot/0.1") or "WinmateBot/0.1",
        respect_robots=env.get_bool("WEB_FETCH_RESPECT_ROBOTS", True),
        rate_limit_rps=env.get_float("WEB_FETCH_RATE_LIMIT_RPS", 0.5),
        timeout_s=env.get_float("WEB_FETCH_TIMEOUT_S", 20.0),
        cache_ttl_hours=env.get_float("WEB_FETCH_CACHE_TTL_HOURS", 168.0),
        allowed_domains=domains,
        max_bytes=env.get_int("WEB_FETCH_MAX_BYTES", 5 * 1024 * 1024),
    )


@dataclass(frozen=True)
class EmbedConfig:
    provider: str          # lsa | none | local | openai_compat | internal
    model: str
    model_path: str | None
    base_url: str | None
    api_key: str | None
    device: str
    dim: int | None
    timeout_s: float


_KNOWN_DIMS = {"baai/bge-m3": 1024, "intfloat/multilingual-e5-small": 384, "intfloat/multilingual-e5-base": 768,
               "intfloat/multilingual-e5-large": 1024, "text-embedding-3-small": 1536, "text-embedding-3-large": 3072}


def embed_config() -> EmbedConfig:
    model = env.get("EMBEDDING_MODEL", "BAAI/bge-m3") or "BAAI/bge-m3"
    dim = env.get_int("EMBEDDING_DIM", 0) or _KNOWN_DIMS.get(model.lower())
    return EmbedConfig(
        provider=(env.get("EMBEDDING_PROVIDER", "lsa") or "lsa").lower(),
        model=model,
        model_path=env.get("EMBEDDING_MODEL_PATH", "./models/bge-m3"),
        base_url=env.get("EMBEDDING_BASE_URL"),
        api_key=env.get("EMBEDDING_API_KEY"),
        device=env.get("LOCAL_MODEL_DEVICE", "cpu") or "cpu",
        dim=dim,
        timeout_s=env.get_float("EMBEDDING_TIMEOUT_S", 60.0),
    )
