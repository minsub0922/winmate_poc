"""LibreOffice(soffice) 변환 — SOFFICE_PATH 가 있을 때만 쓴다(없으면 501 PDF_CONVERTER_UNAVAILABLE).

- convert(data, ext, "pdf"): PPTX · DOCX · XLSX → PDF · convert(data, "xls", "xlsx"): 옛 형식 고객사 양식 → .xlsx
- render_pngs(pptx, max_slides, width): PPTX → PDF → 쪽마다 PNG(pypdfium2)
호출마다 임시 사용자 프로필(-env:UserInstallation)을 써서 동시 변환이 서로 막지 않게 한다.

SOFFICE_PATH 값(files 서비스와 같은 뜻): 경로(또는 PATH 의 이름) · off(끔). **비우면 export 는 끈다** — files 와 달리 PATH 에서
스스로 찾지 않는다(무거운 변환을 설정 없이 켜지 않고, 다른 서비스 테스트가 501 을 기대한다). 대신 status() 가 이 서버에서 찾은
soffice 경로(detected)를 알려 501 메시지 · /v1/info 에 「SOFFICE_PATH=… 를 넣으세요」로 보인다.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from winmate_common.env import get

OFF = {"off", "false", "0", "no", "none", "disable", "disabled"}
MAC_SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
INSTALL_HINT = ("우분투: sudo apt-get install -y --no-install-recommends libreoffice-calc-nogui libreoffice-impress-nogui "
                "fonts-noto-cjk · 맥: brew install --cask libreoffice (docs/OPERATIONS.md)")


class ConverterUnavailable(RuntimeError):
    pass


class ConversionFailed(RuntimeError):
    pass


@dataclass(frozen=True)
class Status:
    path: str | None          # 쓸 실행 파일(없으면 None)
    reason: str               # env(SOFFICE_PATH) · off · missing(SOFFICE_PATH 경로 없음) · unset(비어 있음)
    value: str | None = None  # SOFFICE_PATH 값
    detected: str | None = None  # 이 서버에서 찾은 soffice(쓰지 않을 때도 — 안내용)


def detect() -> str | None:
    """PATH · 맥 기본 위치에서 soffice 찾기(안내용 — 비어 있는 SOFFICE_PATH 를 대신하지 않는다)."""
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    return MAC_SOFFICE if Path(MAC_SOFFICE).is_file() else None


def status() -> Status:
    raw = get("SOFFICE_PATH")
    if not raw:
        return Status(None, "unset", None, detect())
    if raw.lower() in OFF:
        return Status(None, "off", raw, detect())
    p = Path(raw).expanduser()
    if p.is_file() and os.access(p, os.X_OK):
        return Status(str(p), "env", raw, str(p))
    found = shutil.which(raw)
    return Status(found, "env", raw, found) if found else Status(None, "missing", raw, detect())


def soffice_path() -> str | None:
    return status().path


def available() -> bool:
    return soffice_path() is not None


def unavailable_message(what: str) -> tuple[str, dict[str, str]]:
    """501 PDF_CONVERTER_UNAVAILABLE 의 메시지 · details — 왜 없는지와 고칠 방법."""
    st = status()
    if st.reason == "off":
        why = "SOFFICE_PATH=off 로 꺼져 있습니다"
    elif st.reason == "missing":
        why = f"SOFFICE_PATH 의 실행 파일을 찾을 수 없습니다({st.value})"
    else:
        why = "SOFFICE_PATH 가 비어 있습니다"
    fix = (f"이 서버에 {st.detected} 가 있으니 .env 에 SOFFICE_PATH={st.detected} 를 넣고 export · export-worker 를 다시 시작해 주세요"
           if st.detected else f"LibreOffice(headless)를 설치하고 .env 에 SOFFICE_PATH 를 넣어 주세요 — {INSTALL_HINT}")
    details = {"env": "SOFFICE_PATH", "reason": st.reason, "feature": what, "fix": fix}
    if st.detected:
        details["detected"] = st.detected
    if st.value:
        details["value"] = st.value
    return f"{what}에는 LibreOffice 가 필요합니다 — {why}. {fix}", details


def convert(data: bytes, ext: str, to: str = "pdf", timeout: int = 240) -> bytes:
    exe = soffice_path()
    if not exe:
        raise ConverterUnavailable("SOFFICE_PATH 가 없습니다")
    ext = ext.lstrip(".").lower()
    with tempfile.TemporaryDirectory(prefix="wm-soffice-") as tmp:
        src = Path(tmp) / f"in.{ext}"
        src.write_bytes(data)
        profile = Path(tmp) / "profile"
        cmd = [exe, f"-env:UserInstallation=file://{profile}", "--headless", "--norestore", "--nologo",
               "--convert-to", to, "--outdir", tmp, str(src)]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ConversionFailed(f"변환 시간이 {timeout}초를 넘었습니다") from exc
        out = Path(tmp) / f"in.{to.split(':')[0]}"
        if proc.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
            err = (proc.stderr or proc.stdout or b"").decode("utf-8", "replace")[-400:]
            raise ConversionFailed(f"LibreOffice 변환 실패(code {proc.returncode}): {err}")
        return out.read_bytes()


def pdf_to_pngs(pdf: bytes, *, max_pages: int | None = None, width: int = 1280) -> list[bytes]:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf)
    out: list[bytes] = []
    try:
        n = len(doc) if not max_pages else min(len(doc), max_pages)
        for i in range(n):
            page = doc[i]
            img = page.render(scale=width / page.get_width()).to_pil().convert("RGB")
            buf = io.BytesIO()
            img.save(buf, "PNG", optimize=True)
            out.append(buf.getvalue())
    finally:
        doc.close()
    return out


def render_pngs(pptx: bytes, *, max_slides: int | None = None, width: int = 1280) -> list[bytes]:
    return pdf_to_pngs(convert(pptx, "pptx", "pdf"), max_pages=max_slides, width=width)


@lru_cache(maxsize=8)
def font_status(family: str) -> dict[str, Any]:
    """fontconfig 가 family 를 무엇으로 고르는지 — LibreOffice PDF 의 글꼴(줄바꿈)이 PPTX 와 같은지 미리 안다.

    ok: True(그 글꼴 · Noto Sans KR 이면 Noto Sans CJK KR 별칭) · False(다른 글꼴로 바뀜) · None(fc-match 없음).
    프로세스마다 한 번 본다(글꼴을 깔았으면 export · export-worker 를 다시 시작).
    """
    exe = shutil.which("fc-match")
    if not exe:
        return {"family": family, "resolved": None, "ok": None}
    try:
        proc = subprocess.run([exe, "-f", "%{family}", family], capture_output=True, timeout=5, check=False)
        names = [x.strip() for x in proc.stdout.decode("utf-8", "replace").split(",") if x.strip()]
    except (OSError, subprocess.SubprocessError):
        return {"family": family, "resolved": None, "ok": None}

    def key(x: str) -> str:
        return re.sub(r"[\s_-]+", "", x).lower()

    want = key(family)
    ok = any(key(n) == want for n in names) or (want == "notosanskr" and any(key(n).startswith("notosanscjkkr") for n in names))
    return {"family": family, "resolved": names[0] if names else None, "ok": ok}


def font_warning(family: str) -> str | None:
    """LibreOffice 로 만든 PDF 에 붙일 경고(글꼴이 바뀌면) — 없으면 None."""
    st = font_status(family)
    if st["ok"] is False:
        return (f"PDF 글꼴: 서버에서 '{family}' 이 '{st['resolved']}'(으)로 바뀌어 줄바꿈이 PPTX 와 다를 수 있어요 — "
                f"글꼴 설치 또는 fontconfig 별칭(Noto Sans KR → Noto Sans CJK KR, docs/OPERATIONS.md)")
    return None
