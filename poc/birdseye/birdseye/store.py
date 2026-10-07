"""작업(프로젝트) 저장소 — data/birdseye/projects/<id>/project.json (+ renders/)."""
from __future__ import annotations

import datetime as dt
import json
import os
import secrets
import shutil
import threading
from pathlib import Path


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


class Store:
    def __init__(self, root: Path):
        self.root = Path(root) / "projects"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def dir(self, pid: str) -> Path:
        if not pid or "/" in pid or ".." in pid:
            raise KeyError(pid)
        return self.root / pid

    def new_id(self, kind: str) -> str:
        return f"{kind}-{dt.datetime.now().strftime('%m%d%H%M%S')}-{secrets.token_hex(2)}"

    def list(self) -> list[dict]:
        out = []
        for d in self.root.iterdir():
            f = d / "project.json"
            if not f.exists():
                continue
            try:
                p = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            out.append(p)
        out.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        return out

    def get(self, pid: str) -> dict:
        f = self.dir(pid) / "project.json"
        if not f.exists():
            raise KeyError(pid)
        return json.loads(f.read_text(encoding="utf-8"))

    def save(self, p: dict, bump: bool = False) -> dict:
        with self._lock:
            if not p.get("id"):
                p["id"] = self.new_id(p.get("kind", "p"))
                p.setdefault("created_at", now())
            if bump:
                p["version"] = int(p.get("version", 1)) + 1
            p.setdefault("version", 1)
            p["updated_at"] = now()
            d = self.dir(p["id"])
            d.mkdir(parents=True, exist_ok=True)
            tmp = d / "project.json.tmp"
            tmp.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, d / "project.json")
            return p

    def delete(self, pid: str):
        with self._lock:
            d = self.dir(pid)
            if d.exists():
                shutil.rmtree(d)

    def renders_dir(self, pid: str) -> Path:
        d = self.dir(pid) / "renders"
        d.mkdir(parents=True, exist_ok=True)
        return d
