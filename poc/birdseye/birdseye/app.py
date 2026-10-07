"""앱 컨텍스트 — 설정 · 카탈로그 · 저장소 · 작업 관리자 · 모델 클라이언트를 한곳에."""
from __future__ import annotations

import threading

from . import blender_runner
from .catalog import Catalog
from .config import Settings
from .jobs import JobManager
from .llm import ModelClient
from .store import Store


class App:
    def __init__(self, settings: Settings | None = None, llm_transport=None):
        self.settings = settings or Settings()
        self.catalog = Catalog(self.settings.kb_dir)
        self.store = Store(self.settings.data_dir)
        self.jobs = JobManager(max(1, min(2, self.settings.get_int("BIRDSEYE_RENDER_WORKERS", 1))))
        self.llm = ModelClient(self.settings, "LLM", transport=llm_transport)
        self.i2t = ModelClient(self.settings, "I2T", transport=llm_transport)
        self._blender = None
        threading.Thread(target=self.blender, daemon=True).start()  # 시작할 때 Blender 위치·버전 확인

    def blender(self, refresh: bool = False) -> dict:
        if self._blender is None or refresh:
            self._blender = blender_runner.locate(self.settings, refresh)
        return self._blender

    def env(self) -> dict:
        d = self.settings.describe()
        b = self._blender
        return {
            "env_file": d["env_file"], "data_dir": d["data_dir"],
            "llm": self.llm.status(), "i2t": self.i2t.status(),
            "blender": b if b is not None else {"kind": None, "note": "확인 중…"},
            "kb": {"available": self.catalog.kb_available(), "path": d["kb_dir"]},
            "products_seed": len(self.catalog.seed),
            "model_mode": self.settings.model_mode,
            "upload_default_confidential": self.settings.get_bool("UPLOAD_DEFAULT_CONFIDENTIAL", True),
            "render_workers": self.settings.get_int("BIRDSEYE_RENDER_WORKERS", 1),
        }
