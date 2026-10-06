"""환경 변수와 저장소 경로.

- 저장소 루트: `config/services.yaml` 이 있는 디렉터리(또는 WINMATE_ROOT).
- `.env` 는 루트에서 한 번만 읽는다(이미 있는 환경 변수가 우선).
- 빈 문자열은 "값 없음"으로 본다.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_LOADED = False


@lru_cache(maxsize=1)
def repo_root() -> Path:
    env = os.environ.get("WINMATE_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for start in (Path.cwd().resolve(), here):
        for parent in (start, *start.parents):
            if (parent / "config" / "services.yaml").is_file():
                return parent
    raise RuntimeError("저장소 루트를 찾지 못했다(config/services.yaml). WINMATE_ROOT 를 설정하라.")


def load_env() -> None:
    global _LOADED
    if _LOADED:
        return
    env_file = os.environ.get("WINMATE_ENV_FILE") or str(repo_root() / ".env")
    if Path(env_file).is_file():
        load_dotenv(env_file, override=False)
    _LOADED = True


def get(key: str, default: str | None = None) -> str | None:
    load_env()
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def get_bool(key: str, default: bool = False) -> bool:
    value = get(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on", "y"}


def get_int(key: str, default: int) -> int:
    value = get(key)
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def get_float(key: str, default: float) -> float:
    value = get(key)
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def resolve_path(value: str | Path) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (repo_root() / p).resolve()


def _read_or_create_secret(path: Path, nbytes: int = 32) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(nbytes)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(token)
        return token
    except FileExistsError:  # 다른 프로세스가 먼저 만들었다
        return path.read_text(encoding="utf-8").strip()


@dataclass(frozen=True)
class CommonSettings:
    root: Path
    data_dir: Path
    winmate_env: str          # dev | intranet
    redis_url: str
    gateway_url: str
    internal_token: str
    model_mode: str           # live | mock | record | replay
    log_level: str
    contract_validation: str  # strict | warn | off
    upload_max_mb: int
    service: str | None       # 이 프로세스의 서비스 이름(WINMATE_SERVICE)

    def service_data_dir(self, service: str) -> Path:
        d = self.data_dir / service
        d.mkdir(parents=True, exist_ok=True)
        return d


@lru_cache(maxsize=1)
def settings() -> CommonSettings:
    load_env()
    root = repo_root()
    data_dir = resolve_path(get("DATA_DIR", "./data") or "./data")
    data_dir.mkdir(parents=True, exist_ok=True)
    winmate_env = get("WINMATE_ENV", "dev") or "dev"
    # 레지스트리의 Redis 포트를 기본값으로 쓴다(5000번대)
    from .registry import redis_port, service_port

    redis_url = get("REDIS_URL") or f"redis://127.0.0.1:{redis_port()}/0"
    gateway_url = (get("GATEWAY_URL") or f"http://127.0.0.1:{service_port('gateway')}").rstrip("/")
    internal_token = get("INTERNAL_TOKEN") or _read_or_create_secret(data_dir / ".internal_token")
    default_validation = "strict" if winmate_env == "dev" else "warn"
    return CommonSettings(
        root=root,
        data_dir=data_dir,
        winmate_env=winmate_env,
        redis_url=redis_url,
        gateway_url=gateway_url,
        internal_token=internal_token,
        model_mode=(get("MODEL_MODE", "live") or "live").lower(),
        log_level=(get("LOG_LEVEL", "INFO") or "INFO").upper(),
        contract_validation=(get("CONTRACT_VALIDATION", default_validation) or default_validation).lower(),
        upload_max_mb=get_int("UPLOAD_MAX_MB", 50),
        service=get("WINMATE_SERVICE"),
    )


def reset_caches() -> None:
    """테스트용: 환경 변수를 바꾼 뒤 설정 캐시를 비운다."""
    global _LOADED
    _LOADED = False
    settings.cache_clear()
    repo_root.cache_clear()
    from . import registry

    registry._load.cache_clear()
