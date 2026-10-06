"""OLE 복합 문서(Compound File Binary, MS-CFB) 최소 판독기 — 외부 의존성 없음.

Outlook .msg · 옛 Office(.doc .xls .ppt) · HWP 5 가 이 형식이다. 쓰기는 하지 않는다.

    cfb = CFB(data)
    cfb.list()                       # ["__substg1.0_0037001F", "__attach_version1.0_#00000000/…", …]
    cfb.read("__substg1.0_0037001F")
"""
from __future__ import annotations

import struct

MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_FREE, _END, _FAT, _DIF = 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD, 0xFFFFFFFC
_NOSTREAM = 0xFFFFFFFF
_MAXREG = 0xFFFFFFFA


class CFBError(ValueError):
    pass


def is_cfb(data: bytes) -> bool:
    return data[:8] == MAGIC


class _Entry:
    __slots__ = ("idx", "name", "type", "left", "right", "child", "start", "size")

    def __init__(self, idx: int, name: str, type_: int, left: int, right: int, child: int, start: int, size: int):
        self.idx, self.name, self.type = idx, name, type_
        self.left, self.right, self.child = left, right, child
        self.start, self.size = start, size


class CFB:
    def __init__(self, data: bytes):
        if len(data) < 512 or not is_cfb(data):
            raise CFBError("OLE 복합 문서가 아니다")
        self.data = data
        (major,) = struct.unpack_from("<H", data, 0x1A)
        (sector_shift, mini_shift) = struct.unpack_from("<HH", data, 0x1E)
        if sector_shift not in (9, 12) or mini_shift != 6:
            raise CFBError("지원하지 않는 섹터 크기")
        self.ssize = 1 << sector_shift
        self.mini_ssize = 1 << mini_shift
        self.major = major
        (n_fat, first_dir, _tx, self.mini_cutoff, first_minifat, n_minifat, first_difat, n_difat) = struct.unpack_from(
            "<IIIIIIII", data, 0x2C
        )
        self.n_sectors = max(0, (len(data) - self.ssize) // self.ssize + 1)
        # DIFAT → FAT 섹터 목록
        fat_sectors = [s for s in struct.unpack_from("<109I", data, 0x4C) if s < _MAXREG]
        sec, guard = first_difat, 0
        per = self.ssize // 4 - 1
        while sec < _MAXREG and guard < n_difat + 1 and guard < self.n_sectors:
            vals = struct.unpack_from(f"<{per + 1}I", self._sector(sec))
            fat_sectors.extend(v for v in vals[:per] if v < _MAXREG)
            sec = vals[per]
            guard += 1
        fat_sectors = fat_sectors[: max(n_fat, 0) or len(fat_sectors)]
        fat: list[int] = []
        for s in fat_sectors:
            fat.extend(struct.unpack_from(f"<{self.ssize // 4}I", self._sector(s)))
        self.fat = fat
        # 디렉터리
        dir_bytes = self._chain(first_dir)
        self.entries: list[_Entry] = []
        for i in range(len(dir_bytes) // 128):
            raw = dir_bytes[i * 128:(i + 1) * 128]
            name_len = struct.unpack_from("<H", raw, 0x40)[0]
            name = raw[: max(0, min(name_len, 64) - 2)].decode("utf-16-le", "replace")
            type_ = raw[0x42]
            left, right, child = struct.unpack_from("<III", raw, 0x44)
            start = struct.unpack_from("<I", raw, 0x74)[0]
            size = struct.unpack_from("<Q", raw, 0x78)[0]
            if self.major == 3:
                size &= 0xFFFFFFFF
            self.entries.append(_Entry(i, name, type_, left, right, child, start, size))
        if not self.entries or self.entries[0].type != 5:
            raise CFBError("루트 항목이 없다")
        root = self.entries[0]
        self.ministream = self._chain(root.start, root.size) if root.size else b""
        self.minifat: list[int] = []
        if n_minifat and first_minifat < _MAXREG:
            mf = self._chain(first_minifat)
            self.minifat = list(struct.unpack_from(f"<{len(mf) // 4}I", mf))
        self._paths: dict[str, _Entry] = {}
        self._walk(root, "")

    # ── 섹터 ───────────────────────────────────────────
    def _sector(self, n: int) -> bytes:
        off = (n + 1) * self.ssize
        if n >= _MAXREG or off + self.ssize > len(self.data) + self.ssize:
            raise CFBError(f"섹터 범위 밖: {n}")
        chunk = self.data[off:off + self.ssize]
        if len(chunk) < self.ssize:
            chunk = chunk + b"\x00" * (self.ssize - len(chunk))
        return chunk

    def _chain(self, start: int, size: int | None = None) -> bytes:
        out = bytearray()
        sec, seen = start, 0
        limit = len(self.fat) + 1
        while sec < _MAXREG:
            if seen > limit:
                raise CFBError("FAT 순환")
            out += self._sector(sec)
            seen += 1
            if size is not None and len(out) >= size:
                break
            sec = self.fat[sec] if sec < len(self.fat) else _END
        return bytes(out if size is None else out[:size])

    def _mini_chain(self, start: int, size: int) -> bytes:
        out = bytearray()
        sec, seen = start, 0
        while sec < _MAXREG and len(out) < size:
            if seen > len(self.minifat) + 1:
                raise CFBError("미니 FAT 순환")
            off = sec * self.mini_ssize
            out += self.ministream[off:off + self.mini_ssize]
            seen += 1
            sec = self.minifat[sec] if sec < len(self.minifat) else _END
        return bytes(out[:size])

    # ── 트리 ───────────────────────────────────────────
    def _siblings(self, first: int) -> list[_Entry]:
        out: list[_Entry] = []
        stack, seen = [first], set()
        while stack:
            i = stack.pop()
            if i == _NOSTREAM or i >= len(self.entries) or i in seen:
                continue
            seen.add(i)
            e = self.entries[i]
            out.append(e)
            stack.append(e.left)
            stack.append(e.right)
        return out

    def _walk(self, storage: _Entry, prefix: str, depth: int = 0) -> None:
        if depth > 32:
            return
        for e in self._siblings(storage.child):
            path = f"{prefix}{e.name}"
            self._paths[path] = e
            if e.type == 1:
                self._walk(e, path + "/", depth + 1)

    # ── 공개 API ──────────────────────────────────────
    def list(self) -> list[str]:
        return sorted(p for p, e in self._paths.items() if e.type == 2)

    def storages(self, prefix: str = "") -> list[str]:
        """prefix 바로 아래 저장소(폴더) 이름."""
        out = []
        for p, e in self._paths.items():
            if e.type == 1 and p.startswith(prefix) and "/" not in p[len(prefix):]:
                out.append(p[len(prefix):])
        return sorted(out)

    def exists(self, path: str) -> bool:
        return path in self._paths

    def is_storage(self, path: str) -> bool:
        e = self._paths.get(path)
        return e is not None and e.type == 1

    def read(self, path: str) -> bytes:
        e = self._paths.get(path)
        if e is None or e.type != 2:
            raise KeyError(path)
        if e.size < self.mini_cutoff:
            return self._mini_chain(e.start, e.size)
        return self._chain(e.start, e.size)


def classify(data: bytes) -> str | None:
    """OLE 문서 종류: msg | doc | xls | ppt | hwp | None."""
    try:
        cfb = CFB(data)
    except (CFBError, struct.error, IndexError):
        return None
    names = set(cfb._paths)
    if any(n.startswith("__substg1.0_") for n in names):
        return "msg"
    if "WordDocument" in names:
        return "doc"
    if "Workbook" in names or "Book" in names:
        return "xls"
    if "PowerPoint Document" in names:
        return "ppt"
    if "FileHeader" in names and any(n.startswith("BodyText") for n in names):
        return "hwp"
    return None
