"""LibreOffice(soffice) 변환 — PPTX/DOCX/XLSX → PDF(쪽 이미지 · 썸네일), 옛 형식(.doc .ppt .xls …) → OOXML.

- SOFFICE_PATH 로 경로를 준다(off 면 끔). 없으면 PATH · macOS 기본 위치에서 찾는다.
- 결과는 <cache>/soffice/<sha[:2]>/<sha>.<형식> 에 둔다. 실패는 1시간 동안 다시 시도하지 않는다(.fail 표시).
- 동시 실행은 SOFFICE_CONCURRENCY(기본 1)개, 실행마다 따로 쓰는 사용자 프로필 폴더를 쓴다.
"""
from __future__ import annotations

import logging
import os
import queue
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from winmate_common import env

from .storage import Cache, sha256_of

log = logging.getLogger("winmate.files.soffice")

_PPT_PDF = 'pdf:impress_pdf_Export:{"ExportHiddenSlides":{"type":"boolean","value":"true"},' \
           '"ExportNotesPages":{"type":"boolean","value":"false"}}'
_FAIL_TTL_S = 3600


def _kill_group(proc: subprocess.Popen[bytes]) -> None:
    """변환이 끝났거나 시간이 지나면 soffice 프로세스 묶음(oosplash → soffice.bin)을 모두 정리한다."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


class Soffice:
    def __init__(self, path: str | None, cache: Cache, timeout_s: int):
        self.path = path
        self.cache = cache
        self.timeout_s = timeout_s
        n = max(1, env.get_int("SOFFICE_CONCURRENCY", 1))
        self._slots: queue.Queue[int] = queue.Queue()
        for i in range(n):
            self._slots.put(i)
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    @property
    def available(self) -> bool:
        return bool(self.path)

    def _lock_for(self, key: str) -> threading.Lock:
        with self._locks_guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = self._locks[key] = threading.Lock()
            return lock

    def convert(self, data: bytes, name: str, target: str, *, sha: str | None = None, src_kind: str | None = None) -> bytes | None:
        """data(이름 name)를 target(pdf · docx · pptx · xlsx · png) 로. 실패 · 없음이면 None."""
        if not self.path:
            return None
        sha = sha or sha256_of(data)
        out_path = self.cache.path("soffice", sha, f".{target}")
        hit = self.cache.read(out_path)
        if hit:
            return hit
        fail = out_path.with_name(out_path.name + ".fail")
        try:
            if fail.is_file() and time.time() - fail.stat().st_mtime < _FAIL_TTL_S:
                return None
        except OSError:
            pass
        with self._lock_for(f"{sha}.{target}"):
            hit = self.cache.read(out_path)
            if hit:
                return hit
            filters = [target]
            if target == "pdf" and (src_kind == "pptx" or name.lower().endswith((".pptx", ".ppt", ".odp", ".potx", ".ppsx"))):
                filters = [_PPT_PDF, "pdf"]
            result = None
            for flt in filters:
                result = self._run(data, name, target, flt)
                if result:
                    break
            if result:
                self.cache.write(out_path, result)
                try:
                    fail.unlink()
                except OSError:
                    pass
                return result
            try:
                fail.parent.mkdir(parents=True, exist_ok=True)
                fail.write_text(str(time.time()))
            except OSError:
                pass
            return None

    def _run(self, data: bytes, name: str, target: str, flt: str) -> bytes | None:
        slot = self._slots.get()
        try:
            profile = self.cache.root / "soffice" / "_profiles" / f"slot{slot}"
            profile.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="wm-soffice-") as tmp:
                ext = name.rsplit(".", 1)[-1].lower() if "." in name else "bin"
                src = Path(tmp) / f"input.{ext}"
                src.write_bytes(data)
                outdir = Path(tmp) / "out"
                outdir.mkdir()
                cmd = [self.path, f"-env:UserInstallation={profile.resolve().as_uri()}", "--headless", "--invisible",
                       "--norestore", "--nolockcheck", "--nodefault", "--convert-to", flt, "--outdir", str(outdir), str(src)]
                envv = dict(os.environ, SAL_USE_VCLPLUGIN="svp", HOME=str(profile))
                logfile = Path(tmp) / "soffice.log"
                t0 = time.time()
                # 출력은 파일로(파이프를 쓰면 남은 손자 프로세스가 파이프를 잡고 있어 기다림이 길어질 수 있다)
                with open(logfile, "wb") as logf:
                    try:
                        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=logf, stderr=subprocess.STDOUT,
                                                env=envv, start_new_session=True)
                    except OSError as exc:
                        log.warning("soffice 실행 실패: %s", exc)
                        return None
                    try:
                        proc.wait(timeout=self.timeout_s)
                    except subprocess.TimeoutExpired:
                        log.warning("soffice 시간 초과(%ss): %s → %s", self.timeout_s, name, target)
                        return None
                    finally:
                        _kill_group(proc)
                produced = sorted(outdir.glob(f"*.{target}"))
                if not produced:
                    tail = logfile.read_bytes()[-400:].decode("utf-8", "replace") if logfile.is_file() else ""
                    log.info("soffice 변환 결과 없음(%s → %s, %s): %s", name, flt.split(":")[0], proc.returncode, tail)
                    return None
                log.info("soffice %s → %s %.1fs", name, target, time.time() - t0)
                return produced[0].read_bytes()
        finally:
            self._slots.put(slot)
