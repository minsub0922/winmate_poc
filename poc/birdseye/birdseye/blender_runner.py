"""Blender 실행기 — Blender 앱(-b) 또는 bpy 모듈이 있는 파이썬으로 build_scene.py 를 돌린다."""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from .config import Settings

SCRIPT = Path(__file__).resolve().parent / "blender" / "build_scene.py"
COMMON_PATHS = [
    "/Applications/Blender.app/Contents/MacOS/Blender",
    str(Path.home() / "Applications/Blender.app/Contents/MacOS/Blender"),
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe",
    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe",
    "C:/Program Files/Blender Foundation/Blender 4.5/blender.exe",
    "/usr/bin/blender", "/usr/local/bin/blender", "/opt/blender/blender", "/snap/bin/blender",
]

_cache: dict | None = None
_lock = threading.Lock()


def _version_binary(path: str) -> str | None:
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r"Blender\s+([\d.]+(?:\s*LTS)?)", out)
        return m.group(1) if m else out.strip().splitlines()[0][:40]
    except Exception:  # noqa: BLE001
        return None


def _version_bpy(python: str) -> str | None:
    try:
        out = subprocess.run([python, "-c", "import bpy;print(bpy.app.version_string)"], capture_output=True, text=True, timeout=120)
        lines = [l for l in out.stdout.strip().splitlines() if re.match(r"^\d", l.strip())]
        return lines[-1].strip() if lines else None
    except Exception:  # noqa: BLE001
        return None


def locate(settings: Settings, refresh: bool = False) -> dict:
    """{kind: binary|bpy|None, cmd: [...], version, path, note}"""
    global _cache
    with _lock:
        if _cache is not None and not refresh:
            return _cache
        b = settings.blender
        res = {"kind": None, "cmd": None, "version": None, "path": None,
               "note": "Blender 를 찾지 못했어요 — .env 에 BLENDER_PATH(앱 실행 파일) 또는 BPY_PYTHON(bpy 를 설치한 파이썬)을 넣어 주세요."}
        cands = []
        if b["path"]:
            cands.append(("binary", b["path"]))
        if b["bpy_python"]:
            cands.append(("bpy", b["bpy_python"]))
        for pth in COMMON_PATHS:
            cands.append(("binary", pth))
        w = shutil.which("blender")
        if w:
            cands.append(("binary", w))
        if importlib.util.find_spec("bpy") is not None:
            cands.append(("bpy", sys.executable))
        for kind, pth in cands:
            if not pth or not Path(pth).exists():
                continue
            ver = _version_binary(pth) if kind == "binary" else _version_bpy(pth)
            if not ver:
                continue
            cmd = ([pth, "-b", "--factory-startup", "-noaudio", "--python", str(SCRIPT), "--"] if kind == "binary"
                   else [pth, str(SCRIPT)])
            res = {"kind": kind, "cmd": cmd, "version": ver, "path": pth,
                   "note": f"{'Blender 앱' if kind == 'binary' else 'bpy 모듈'} {ver} · {platform.system()}"}
            break
        _cache = res
        return res


class RenderCancelled(Exception):
    pass


def run(settings: Settings, spec_path: Path, out_dir: Path, on_event, cancel: threading.Event, timeout: int | None = None) -> dict:
    loc = locate(settings)
    if not loc["kind"]:
        raise RuntimeError(loc["note"])
    cmd = loc["cmd"] + [str(spec_path), str(out_dir)]
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    log_path = Path(out_dir) / "blender.log"
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env,
                            encoding="utf-8", errors="replace")
    tmo = timeout or settings.blender["timeout"]
    done = threading.Event()
    timed_out = {"v": False}

    def watchdog():
        import time as _t
        t0 = _t.time()
        while not done.wait(0.5):
            if cancel.is_set() or _t.time() - t0 > tmo:
                timed_out["v"] = not cancel.is_set()
                try:
                    proc.terminate()
                except Exception:  # noqa: BLE001
                    pass
                return

    threading.Thread(target=watchdog, daemon=True).start()
    last_err = None
    with open(log_path, "w", encoding="utf-8") as log:
        for line in proc.stdout:
            log.write(line)
            log.flush()
            s = line.strip()
            if s.startswith("@@BIRDSEYE "):
                try:
                    evt = json.loads(s[len("@@BIRDSEYE "):])
                except json.JSONDecodeError:
                    continue
                if evt.get("kind") == "error":
                    last_err = evt.get("msg")
                on_event(evt)
            else:
                m = re.search(r"Sample (\d+)/(\d+)", s)
                if m:
                    on_event({"kind": "sample", "a": int(m.group(1)), "b": int(m.group(2))})
    rc = proc.wait()
    done.set()
    if cancel.is_set() and rc != 0:
        raise RenderCancelled()
    if timed_out["v"]:
        raise RuntimeError(f"렌더 시간 초과({tmo}s) — RENDER_TIMEOUT_S 를 늘리거나 품질을 낮춰 주세요")
    if rc != 0:
        raise RuntimeError(last_err or f"Blender 종료 코드 {rc} — {log_path} 확인")
    man = Path(out_dir) / "manifest.json"
    if not man.exists():
        raise RuntimeError("manifest.json 이 없어요 — Blender 로그 확인")
    return json.loads(man.read_text(encoding="utf-8"))
