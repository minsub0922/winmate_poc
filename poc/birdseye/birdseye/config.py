"""설정 — winmate 루트의 .env 를 그대로 읽는다(위로 올라가며 찾음). 환경 변수가 .env 보다 우선."""
from __future__ import annotations

import os
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]


def find_env(start: Path) -> Path | None:
    if os.environ.get("BIRDSEYE_ENV"):
        p = Path(os.environ["BIRDSEYE_ENV"]).expanduser()
        return p if p.exists() else None
    cur = start.resolve()
    for _ in range(6):
        cand = cur / ".env"
        if cand.exists():
            return cand
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def parse_env(path: Path) -> dict[str, str]:
    out = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if k.startswith("export "):
            k = k[7:].strip()
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        else:
            v = v.split(" #", 1)[0].strip()
        out[k] = v
    return out


class Settings:
    def __init__(self, env_path: Path | None = None):
        self.env_path = env_path if env_path is not None else find_env(POC_ROOT)
        self.env_dir = self.env_path.parent if self.env_path else POC_ROOT
        self.file_vals = parse_env(self.env_path) if self.env_path else {}

    def get(self, key: str, default: str | None = None) -> str | None:
        if key in os.environ:
            return os.environ[key]
        v = self.file_vals.get(key)
        return v if v not in (None, "") else default

    def get_bool(self, key: str, default: bool = False) -> bool:
        v = self.get(key)
        if v is None:
            return default
        return v.strip().lower() in ("1", "true", "yes", "on", "y")

    def get_int(self, key: str, default: int) -> int:
        try:
            return int(float(self.get(key, str(default))))
        except (TypeError, ValueError):
            return default

    def get_float(self, key: str, default: float) -> float:
        try:
            return float(self.get(key, str(default)))
        except (TypeError, ValueError):
            return default

    def path(self, key: str, default: str | None = None) -> Path | None:
        v = self.get(key, default)
        if not v:
            return None
        p = Path(v).expanduser()
        return p if p.is_absolute() else (self.env_dir / p).resolve()

    # ── 자주 쓰는 값 ──
    @property
    def data_dir(self) -> Path:
        base = self.path("BIRDSEYE_DATA_DIR") or ((self.path("DATA_DIR") or (POC_ROOT / "data")) / "birdseye")
        base.mkdir(parents=True, exist_ok=True)
        return base

    @property
    def kb_dir(self) -> Path | None:
        p = self.path("WKB_KB")
        if p and (p / "winmate_kb.sqlite").exists():
            return p
        for cand in (POC_ROOT.parent / "winmate-kb" / "kb", POC_ROOT.parent.parent / "winmate-kb" / "kb"):
            if (cand / "winmate_kb.sqlite").exists():
                return cand
        return None

    @property
    def host(self) -> str:
        return self.get("BIRDSEYE_HOST", self.get("APP_HOST", "127.0.0.1"))

    @property
    def port(self) -> int:
        return self.get_int("BIRDSEYE_PORT", 8710)

    @property
    def model_mode(self) -> str:
        return (self.get("BIRDSEYE_MODEL_MODE") or self.get("MODEL_MODE", "live")).lower()

    def service(self, name: str) -> dict:
        """LLM · I2T 서비스 설정(winmate .env 의 같은 키)."""
        n = name.upper()
        provider = (self.get(f"{n}_PROVIDER", "gemini") or "gemini").lower()
        key = self.get(f"{n}_API_KEY") or (self.get("GEMINI_API_KEY") if provider == "gemini" else None)
        base = self.get(f"{n}_BASE_URL") or (self.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com") if provider == "gemini" else None)
        return {
            "name": n, "provider": provider, "base_url": (base or "").rstrip("/"), "api_key": key,
            "model": self.get(f"{n}_MODEL", "gemini-3.1-flash-lite"),
            "json_schema": self.get_bool(f"{n}_SUPPORTS_JSON_SCHEMA", True),
            "timeout": self.get_float(f"{n}_TIMEOUT_S", 90.0),
            "rpm": self.get_int(f"{n}_RPM", 30),
            "temperature": self.get_float("LLM_TEMPERATURE", 0.2),
            "max_output": self.get_int("LLM_MAX_OUTPUT_TOKENS", 4096),
            "thinking": self.get("GEMINI_THINKING_LEVEL", ""),
            "allow_confidential": self.get_bool(f"{n}_ALLOW_CONFIDENTIAL", False),
            "max_side": self.get_int("I2T_MAX_IMAGE_SIDE_PX", 1536),
        }

    @property
    def blender(self) -> dict:
        return {
            "path": self.get("BLENDER_PATH"),
            "bpy_python": self.get("BPY_PYTHON"),
            "engine": (self.get("RENDER_ENGINE", "cycles") or "cycles").lower(),
            "device": (self.get("RENDER_DEVICE", "auto") or "auto").lower(),
            "timeout": self.get_int("RENDER_TIMEOUT_S", 1800),
            "threads": self.get_int("RENDER_THREADS", 0),
        }

    def describe(self) -> dict:
        llm = self.service("LLM")
        return {"env_file": str(self.env_path) if self.env_path else None, "data_dir": str(self.data_dir),
                "model_mode": self.model_mode, "llm": {k: llm[k] for k in ("provider", "model")} | {"key_set": bool(llm["api_key"])},
                "kb_dir": str(self.kb_dir) if self.kb_dir else None}
