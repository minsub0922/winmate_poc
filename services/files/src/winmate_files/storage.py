"""바이너리 저장소(내용 주소, 중복 제거)와 캐시 폴더.

    <DATA_DIR>/files/blobs/<sha[:2]>/<sha256>
    <DATA_DIR>/files/cache/{parsed,thumbs,pages,soffice,icons}/…
"""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class BlobStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, sha: str) -> Path:
        return self.root / sha[:2] / sha

    def exists(self, sha: str) -> bool:
        return self.path(sha).is_file()

    def put(self, data: bytes, sha: str | None = None) -> str:
        sha = sha or sha256_of(data)
        p = self.path(sha)
        if not p.is_file():
            _atomic_write(p, data)
        return sha

    def read(self, sha: str) -> bytes:
        return self.path(sha).read_bytes()

    def delete(self, sha: str) -> None:
        try:
            self.path(sha).unlink()
        except FileNotFoundError:
            pass


class Cache:
    """파생물 캐시. 모두 sha256(내용) 기준이라 같은 내용이면 레코드가 달라도 함께 쓴다."""

    KINDS = ("parsed", "thumbs", "pages", "soffice", "icons")

    def __init__(self, root: Path):
        self.root = root
        for k in self.KINDS:
            (root / k).mkdir(parents=True, exist_ok=True)

    def path(self, kind: str, sha: str, suffix: str) -> Path:
        return self.root / kind / sha[:2] / f"{sha}{suffix}"

    def icon_path(self, name: str) -> Path:
        return self.root / "icons" / name

    def read(self, path: Path) -> bytes | None:
        try:
            return path.read_bytes()
        except (FileNotFoundError, NotADirectoryError):
            return None

    def write(self, path: Path, data: bytes) -> None:
        _atomic_write(path, data)

    def purge(self, sha: str) -> None:
        """그 내용(sha)의 파생물을 모두 지운다(마지막 레코드가 지워졌을 때)."""
        for k in ("parsed", "thumbs", "pages", "soffice"):
            d = self.root / k / sha[:2]
            if not d.is_dir():
                continue
            for p in d.glob(f"{sha}*"):
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    try:
                        p.unlink()
                    except OSError:
                        pass
