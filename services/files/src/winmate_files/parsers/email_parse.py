"""메일 — .eml(RFC 822, 표준 라이브러리) · .msg(Outlook, OLE 복합 문서).

머리(제목 · 보낸 사람 · 받는 사람 · 참조 · 날짜)는 디코딩해서 주고, 본문은 text/plain 을 우선, 없으면 HTML 을 글자로 바꾼다.
첨부는 자식 파일(source=derived)로 뽑는다. 본문 안 그림(cid)은 inline 으로 표시하고 email.attachments 에서는 뺀다.
"""
from __future__ import annotations

import base64
import binascii
import logging
import mimetypes
import quopri
import re
import struct
from datetime import datetime, timedelta, timezone
from email import policy
from email.message import Message
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from typing import Any

from .. import cfb as cfbmod
from ..detect import sanitize_name
from ..textutil import clean, decode_text
from .common import Doc, ParseContext, ParseError

log = logging.getLogger("winmate.files.email")


# ── 공통 ───────────────────────────────────────────────────────

def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_addr(name: str, addr: str) -> str:
    name, addr = clean(name), clean(addr)
    if name and addr and name != addr:
        return f"{name} <{addr}>"
    return addr or name


def html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "head", "title"]):
        t.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.split("\n")]
    out: list[str] = []
    for ln in lines:
        if ln or (out and out[-1]):
            out.append(ln)
    return clean("\n".join(out))


def _build(doc: Doc, info: dict[str, Any], atts: list[dict[str, Any]]) -> None:
    subject = info.get("subject") or ""
    body = info.get("body") or ""
    header_lines = []
    if info.get("from"):
        header_lines.append(f"보낸 사람: {info['from']}")
    if info.get("to"):
        header_lines.append("받는 사람: " + ", ".join(info["to"]))
    if info.get("cc"):
        header_lines.append("참조: " + ", ".join(info["cc"]))
    if info.get("date"):
        header_lines.append(f"날짜: {info['date']}")
    blocks: list[dict[str, Any]] = []
    if subject:
        blocks.append({"type": "title", "text": subject, "level": 1})
    if header_lines:
        blocks.append({"type": "note", "text": "\n".join(header_lines)})
    for para in re.split(r"\n\s*\n", body):
        t = para.strip()
        if not t:
            continue
        quoted = all(ln.lstrip().startswith(">") for ln in t.split("\n") if ln.strip())
        blocks.append({"type": "note" if quoted else "body", "text": t})
    real = [a for a in atts if not a.get("inline")]
    page = doc.page(1, title=subject or None)
    for a in atts:
        if a.get("ref") and a["mime"].startswith("image/"):
            page["image_refs"].append(a["ref"])
            page["images"].append({"ref": a["ref"], "bbox": None})
    if real:
        blocks.append({"type": "note", "text": "첨부: " + ", ".join(a["name"] for a in real)})
    page["blocks"] = blocks
    parts = [subject] if subject else []
    if header_lines:
        parts.append("\n".join(header_lines))
    if body:
        parts.append(body)
    if real:
        parts.append("첨부: " + ", ".join(a["name"] for a in real))
    page["text"] = "\n\n".join(parts)
    doc.email = {
        "subject": subject or None,
        "from": info.get("from"),
        "to": info.get("to") or [],
        "cc": info.get("cc") or [],
        "date": info.get("date"),
        "body": body,
        "attachment_refs": [a["ref"] for a in real if a.get("ref")],
        "attachment_list": [{"name": a["name"], "mime": a["mime"], "size": a["size"], "ref": a.get("ref"),
                             "inline": bool(a.get("inline"))} for a in atts],
    }
    doc.title = subject or None
    doc.meta.update({"title": subject or None, "author": info.get("from"), "created": info.get("date")})


def _add_attachment(doc: Doc, data: bytes, name: str, mime: str, inline: bool, atts: list[dict[str, Any]]) -> None:
    name = sanitize_name(name, "attachment")
    ref = doc.add_child(data, name, mime or "application/octet-stream", {"from": "email", "inline": inline or None}, page=1)
    atts.append({"name": name, "mime": mime or "application/octet-stream", "size": len(data), "ref": ref, "inline": inline})


# ── EML ────────────────────────────────────────────────────────

def _hdr(msg: Message, key: str) -> str:
    try:
        v = msg.get(key)
    except Exception:  # noqa: BLE001 — 깨진 머리
        v = None
    if v is None:
        try:
            raw = msg.get_all(key, failobj=[])
            v = raw[0] if raw else None
        except Exception:  # noqa: BLE001
            v = None
    return clean(str(v)) if v is not None else ""


def _addrs(msg: Message, key: str) -> list[str]:
    try:
        values = [str(v) for v in (msg.get_all(key) or [])]
    except Exception:  # noqa: BLE001
        return []
    out = [_fmt_addr(n, a) for n, a in getaddresses(values) if (n or a)]
    return [x for x in out if x][:200]


def _date(msg: Message) -> str | None:
    raw = _hdr(msg, "date")
    if not raw:
        return None
    try:
        return _iso(parsedate_to_datetime(raw))
    except (TypeError, ValueError, IndexError):
        return None


def _content(part: Message) -> str:
    try:
        c = part.get_content()  # type: ignore[attr-defined]
        if isinstance(c, bytes):
            return decode_text(c)[0]
        return str(c)
    except (LookupError, ValueError, AssertionError, KeyError, AttributeError):
        payload = part.get_payload(decode=True) or b""
        charset = part.get_content_charset() or ""
        try:
            return payload.decode(charset or "utf-8")
        except (LookupError, UnicodeDecodeError):
            return decode_text(payload)[0]


def _embedded_message(part: Message) -> bytes | None:
    """message/rfc822 첨부의 원래 바이트. base64 · quoted-printable 로 감싼 것(비표준이지만 흔함)도 푼다."""
    try:
        inner = part.get_payload(0)
    except (IndexError, TypeError):
        return None
    cte = str(part.get("content-transfer-encoding") or "").strip().lower()
    if cte in ("base64", "quoted-printable") and isinstance(inner, Message) and not inner.is_multipart() \
            and not inner.keys():
        raw = str(inner.get_payload(decode=False) or "")
        try:
            if cte == "base64":
                return base64.b64decode(raw)
            return quopri.decodestring(raw.encode("ascii", "replace"))
        except (ValueError, binascii.Error):
            pass
    try:
        return inner.as_bytes(policy=policy.default)
    except Exception:  # noqa: BLE001
        try:
            return inner.as_bytes()
        except Exception:  # noqa: BLE001
            return None


def _leaves(part: Message, depth: int = 0) -> list[Message]:
    if depth > 20:
        return []
    ctype = part.get_content_type()
    if ctype == "message/rfc822":
        return [part]
    if part.is_multipart():
        out: list[Message] = []
        for sub in part.get_payload() or []:
            if isinstance(sub, Message):
                out.extend(_leaves(sub, depth + 1))
        return out
    return [part]


def parse_eml(data: bytes, ctx: ParseContext) -> dict[str, Any]:
    doc = Doc("email", ctx)
    try:
        msg = BytesParser(policy=policy.default).parsebytes(data)
    except Exception as exc:  # noqa: BLE001
        raise ParseError("PARSE_FAILED", f"메일을 읽을 수 없어요: {exc}") from exc
    info: dict[str, Any] = {
        "subject": _hdr(msg, "subject"), "from": ", ".join(_addrs(msg, "from")) or _hdr(msg, "from") or None,
        "to": _addrs(msg, "to"), "cc": _addrs(msg, "cc"), "date": _date(msg),
    }
    plain = html = None
    atts: list[dict[str, Any]] = []
    for i, part in enumerate(_leaves(msg)):
        ctype = part.get_content_type()
        disp = (part.get_content_disposition() or "").lower()
        try:
            filename = part.get_filename()
        except Exception:  # noqa: BLE001
            filename = None
        if ctype in ("text/plain", "text/html") and not filename and disp != "attachment":
            if ctype == "text/plain" and plain is None:
                plain = _content(part)
                continue
            if ctype == "text/html" and html is None:
                html = _content(part)
                continue
        if ctype == "message/rfc822":
            blob = _embedded_message(part)
            if not blob:
                continue
            sub = _hdr(BytesParser(policy=policy.default).parsebytes(blob[:100_000], headersonly=True), "subject") or "message"
            _add_attachment(doc, blob, filename or f"{sub[:80]}.eml", "message/rfc822", False, atts)
            continue
        try:
            payload = part.get_payload(decode=True)
        except Exception:  # noqa: BLE001
            payload = None
        if not payload:
            continue
        has_cid = bool(part.get("content-id"))
        inline = ctype.startswith("image/") and (disp == "inline" or (has_cid and disp != "attachment"))
        if not filename:
            ext = mimetypes.guess_extension(ctype) or ".bin"
            filename = f"attachment{i + 1}{'.jpg' if ext == '.jpe' else ext}"
        _add_attachment(doc, payload, filename, ctype, inline, atts)
    body = clean(plain) if plain and plain.strip() else (html_to_text(html) if html else "")
    info["body"] = body
    _build(doc, info, atts)
    if not ctx.extract_children and atts:
        doc.warn("attachments_not_extracted:depth")
    return doc.finish()


# ── MSG (Outlook) ──────────────────────────────────────────────

_CODEPAGES = {949: "cp949", 51949: "euc-kr", 65001: "utf-8", 1252: "cp1252", 932: "cp932", 936: "gbk", 950: "cp950",
              20127: "ascii", 28591: "latin-1", 1200: "utf-16-le", 50220: "iso2022_jp", 50221: "iso2022_jp", 51932: "euc_jp"}


def _filetime(raw8: bytes) -> str | None:
    (v,) = struct.unpack("<Q", raw8)
    if v == 0 or v > 2650467743990000000:
        return None
    try:
        return _iso(datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=v // 10))
    except OverflowError:
        return None


class _MsgObj:
    """메시지 · 받는 사람 · 첨부 한 개의 속성(가변 길이 스트림 + 고정 길이 속성 표)."""

    def __init__(self, c: cfbmod.CFB, prefix: str, header: int, codepage: str | None = None):
        self.c, self.prefix = c, prefix
        self.fixed: dict[int, tuple[int, bytes]] = {}
        try:
            raw = c.read(prefix + "__properties_version1.0")
            for off in range(header, len(raw) - 15, 16):
                tag = int.from_bytes(raw[off:off + 4], "little")
                self.fixed[tag >> 16] = (tag & 0xFFFF, raw[off + 8:off + 16])
        except KeyError:
            pass
        self.codepage = codepage
        if self.codepage is None:
            for pid in (0x3FFD, 0x3FDE):
                if pid in self.fixed:
                    cp = int.from_bytes(self.fixed[pid][1][:4], "little")
                    if cp in _CODEPAGES:
                        self.codepage = _CODEPAGES[cp]
                        break
                    if cp:
                        self.codepage = f"cp{cp}"
                        break

    def _stream(self, pid: int, ptype: int) -> bytes | None:
        path = f"{self.prefix}__substg1.0_{pid:04X}{ptype:04X}"
        try:
            return self.c.read(path)
        except KeyError:
            return None

    def string(self, pid: int) -> str | None:
        raw = self._stream(pid, 0x001F)
        if raw is not None:
            return clean(raw.decode("utf-16-le", "replace").rstrip("\x00"))
        raw = self._stream(pid, 0x001E)
        if raw is not None:
            raw = raw.rstrip(b"\x00")
            for enc in (self.codepage, "utf-8", "cp949"):
                if not enc:
                    continue
                try:
                    return clean(raw.decode(enc))
                except (LookupError, UnicodeDecodeError):
                    continue
            return clean(raw.decode("latin-1"))
        return None

    def binary(self, pid: int) -> bytes | None:
        return self._stream(pid, 0x0102)

    def int32(self, pid: int) -> int | None:
        v = self.fixed.get(pid)
        if v is None:
            return None
        return int.from_bytes(v[1][:4], "little", signed=True)

    def time(self, pid: int) -> str | None:
        v = self.fixed.get(pid)
        if v is None or v[0] != 0x0040:
            return None
        return _filetime(v[1])

    def is_storage(self, pid: int, ptype: int) -> bool:
        return self.c.is_storage(f"{self.prefix}__substg1.0_{pid:04X}{ptype:04X}")


def _msg_html(m: _MsgObj) -> str | None:
    raw = m.binary(0x1013)
    if raw is None:
        s = m.string(0x1013)
        return s
    cp = None
    cpid = m.int32(0x3FDE)
    if cpid and cpid in _CODEPAGES:
        cp = _CODEPAGES[cpid]
    match = re.search(rb'charset=["\']?([A-Za-z0-9_\-]+)', raw[:4096])
    for enc in (cp, match.group(1).decode("ascii", "ignore") if match else None, "utf-8", "cp949"):
        if not enc:
            continue
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("latin-1")


def parse_msg(data: bytes, ctx: ParseContext) -> dict[str, Any]:
    doc = Doc("email", ctx)
    try:
        c = cfbmod.CFB(data)
    except (cfbmod.CFBError, struct.error, IndexError) as exc:
        raise ParseError("PARSE_FAILED", f"Outlook 메일(.msg)을 읽을 수 없어요: {exc}") from exc
    m = _MsgObj(c, "", 32)
    info: dict[str, Any] = {"subject": m.string(0x0037) or "", "to": [], "cc": []}
    headers = m.string(0x007D)
    hdr_msg = None
    if headers:
        try:
            hdr_msg = BytesParser(policy=policy.default).parsebytes(headers.encode("utf-8", "replace") + b"\n\n", headersonly=True)
        except Exception:  # noqa: BLE001
            hdr_msg = None
    sender_name = m.string(0x0C1A) or m.string(0x0042)
    sender_addr = m.string(0x5D01) or m.string(0x5D02) or m.string(0x0C1F) or m.string(0x0065)
    if sender_addr and sender_addr.upper().startswith("/O="):
        sender_addr = None  # Exchange 내부 주소(X.500)
    info["from"] = _fmt_addr(sender_name or "", sender_addr or "") or None
    if hdr_msg is not None and not info["from"]:
        info["from"] = ", ".join(_addrs(hdr_msg, "from")) or None
    info["date"] = m.time(0x0039) or m.time(0x0E06) or (_date(hdr_msg) if hdr_msg is not None else None) or m.time(0x3007)
    # 받는 사람
    for st in c.storages(""):
        if not st.startswith("__recip_version1.0_"):
            continue
        r = _MsgObj(c, st + "/", 8, m.codepage)
        name = r.string(0x3001) or ""
        addr = r.string(0x39FE) or r.string(0x3003) or ""
        if addr.upper().startswith("/O="):
            addr = ""
        rtype = r.int32(0x0C15) or 1
        entry = _fmt_addr(name, addr)
        if not entry:
            continue
        if rtype == 2:
            info["cc"].append(entry)
        elif rtype == 1:
            info["to"].append(entry)
    if not info["to"] and hdr_msg is not None:
        info["to"] = _addrs(hdr_msg, "to")
        info["cc"] = info["cc"] or _addrs(hdr_msg, "cc")
    if not info["to"]:
        disp = m.string(0x0E04)
        info["to"] = [x.strip() for x in (disp or "").split(";") if x.strip()]
    if not info["cc"]:
        disp = m.string(0x0E03)
        info["cc"] = [x.strip() for x in (disp or "").split(";") if x.strip()]
    body = m.string(0x1000)
    if not body or not body.strip():
        html = _msg_html(m)
        body = html_to_text(html) if html else ""
        if not body and c.exists("__substg1.0_10090102"):
            doc.warn("msg_body_rtf_only")
    info["body"] = clean(body)
    # 첨부
    atts: list[dict[str, Any]] = []
    for st in c.storages(""):
        if not st.startswith("__attach_version1.0_"):
            continue
        a = _MsgObj(c, st + "/", 8, m.codepage)
        name = a.string(0x3707) or a.string(0x3704) or a.string(0x3001) or "attachment"
        mime = (a.string(0x370E) or mimetypes.guess_type(name)[0] or "application/octet-stream").lower()
        if a.is_storage(0x3701, 0x000D):
            doc.warn("msg_embedded_message_skipped")
            atts.append({"name": sanitize_name(name if "." in name else f"{name}.msg", "message.msg"),
                         "mime": "application/vnd.ms-outlook", "size": 0, "ref": None, "inline": False})
            continue
        blob = a.binary(0x3701)
        if not blob:
            continue
        hidden = False
        hv = a.fixed.get(0x7FFE)
        if hv is not None:
            hidden = bool(int.from_bytes(hv[1][:2], "little"))
        cid = a.string(0x3712)
        inline = mime.startswith("image/") and (hidden or bool(cid))
        _add_attachment(doc, blob, name, mime, inline, atts)
    _build(doc, info, atts)
    if not ctx.extract_children and atts:
        doc.warn("attachments_not_extracted:depth")
    return doc.finish()


def parse_email(data: bytes, ctx: ParseContext) -> dict[str, Any]:
    if cfbmod.is_cfb(data):
        return parse_msg(data, ctx)
    return parse_eml(data, ctx)


def quick_headers(data: bytes, fmt: str) -> dict[str, Any]:
    """목록 표시용 머리(제목 · 보낸 사람 · 날짜)만."""
    if cfbmod.is_cfb(data):
        try:
            c = cfbmod.CFB(data)
            m = _MsgObj(c, "", 32)
            name = m.string(0x0C1A) or m.string(0x0042) or ""
            addr = m.string(0x5D01) or m.string(0x0C1F) or ""
            if addr.upper().startswith("/O="):
                addr = ""
            return {"subject": m.string(0x0037), "from": _fmt_addr(name, addr) or None,
                    "date": m.time(0x0039) or m.time(0x0E06)}
        except Exception:  # noqa: BLE001
            return {}
    try:
        msg = BytesParser(policy=policy.default).parsebytes(data[:200_000], headersonly=True)
    except Exception:  # noqa: BLE001
        return {}
    return {"subject": _hdr(msg, "subject") or None, "from": ", ".join(_addrs(msg, "from")) or None, "date": _date(msg)}
