"""files 서비스 본체 — 레코드(DocStore) · 바이너리(BlobStore) · 파싱(캐시 · 자식 파일) · 미리보기.

동기 메서드는 스레드에서(asyncio.to_thread) 부른다. 파싱은 내용(sha256) 기준으로 한 번만 하고,
레코드마다 자식 파일(추출 이미지 · 메일 첨부)을 만들어 ref → file id 로 바꾼다(materialize).
"""
from __future__ import annotations

import asyncio
import base64
import copy
import json
import logging
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable

from winmate_common.context import User
from winmate_common.errors import ApiError, bad_request, forbidden, not_found
from winmate_common.ids import new_id
from winmate_common.store import DocStore, VersionConflict

from . import imaging, pdfium
from .detect import SOFFICE_CONVERTIBLE, Detected, detect, kind_label, sanitize_name
from .docprops import quick_meta
from .models import ParsedDocument
from .parsers import ParseContext, ParseError, Unsupported, parse_kind, parseable
from .settings import PARSER_VERSION, FilesSettings, files_settings, soffice_path
from .soffice import Soffice
from .storage import BlobStore, Cache

log = logging.getLogger("winmate.files")

COLL = "files"
SCAN_MAX = 5000
OFFICE_KINDS = ("pptx", "docx", "xlsx")
_RISKY_INLINE = ("text/html", "application/xhtml+xml", "application/xml", "text/xml", "application/javascript", "text/javascript")


def _too_large(size: int, limit: int) -> ApiError:
    return ApiError(413, "PAYLOAD_TOO_LARGE", f"파일당 {limit // (1024 * 1024)}MB까지 올릴 수 있어요",
                    {"size": size, "limit": limit})


class _StaleCache(Exception):
    pass


class FilesService:
    def __init__(self, cfg: FilesSettings | None = None):
        self.cfg = cfg or files_settings()
        self.data_dir = self.cfg.data_dir
        self.store = DocStore.for_service("files")
        for field in ("owner", "sha256", "parent_id", "project_id", "kind", "folder"):
            self.store.index(COLL, field)
        self.blobs = BlobStore(self.cfg.blobs_dir)
        self.cache = Cache(self.cfg.cache_dir)
        self.soffice = Soffice(soffice_path(), self.cache, self.cfg.soffice_timeout_s)
        self._content_inflight: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._record_inflight: dict[str, asyncio.Task[bytes]] = {}
        self._bg: set[asyncio.Task[Any]] = set()
        self._sem: asyncio.Semaphore | None = None
        self._sem_loop: asyncio.AbstractEventLoop | None = None

    # ── 레코드 ─────────────────────────────────────────
    def get(self, file_id: str, *, include_deleted: bool = False) -> dict[str, Any]:
        rec = self.store.get(COLL, file_id, include_deleted=include_deleted) if file_id.startswith("file_") else None
        if rec is None or (rec.get("deleted") and not include_deleted):
            raise not_found("파일", file_id)
        return rec

    def _update(self, file_id: str, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
        """낙관적 버전으로 고친다. 지운 레코드(data.deleted)는 다시 쓰지 않는다
        (DocStore.put 은 deleted 표시를 지우므로, 지우기와 겹친 상태 갱신이 레코드를 되살리지 않게)."""
        for _ in range(8):
            cur = self.store.get(COLL, file_id)
            if cur is None or cur.get("deleted"):
                raise not_found("파일", file_id)
            new = fn(copy.deepcopy(cur))
            try:
                return self.store.put(COLL, file_id, new, expected_version=cur["version"], keep_history=False)
            except VersionConflict:
                time.sleep(0.01)
        raise ApiError(409, "CONFLICT", "동시에 바뀌어 저장하지 못했어요. 다시 시도해 주세요")

    @staticmethod
    def to_meta(rec: dict[str, Any]) -> dict[str, Any]:
        fid = rec["id"]
        return {
            "id": fid, "name": rec["name"], "mime": rec["mime"], "size": rec["size"], "sha256": rec["sha256"],
            "kind": rec["kind"], "source": rec["source"], "confidential": bool(rec.get("confidential")),
            "owner": rec["owner"], "owner_name": rec.get("owner_name") or "", "project_id": rec.get("project_id"),
            "parent_id": rec.get("parent_id"), "width": rec.get("width"), "height": rec.get("height"),
            "pages": rec.get("pages"), "meta": rec.get("meta") or {}, "created_at": rec["created_at"],
            "updated_at": rec.get("updated_at"), "url": f"/api/files/v1/files/{fid}/content",
            "thumb_url": f"/api/files/v1/files/{fid}/thumbnail", "purpose": rec.get("purpose"), "folder": rec.get("folder"),
            "doc_props": rec.get("doc_props"), "parse_status": rec.get("parse_status") or "none",
            "parse_error": rec.get("parse_error"),
        }

    def can_parse(self, kind: str, fmt: str) -> bool:
        return parseable(kind, fmt, soffice=self.soffice.available)

    # ── 저장(올리기 · 내부 저장 · 자식) ─────────────────
    def ingest(
        self,
        data: bytes,
        name: str | None,
        declared_mime: str | None,
        *,
        user: User,
        source: str = "upload",
        confidential: bool = False,
        project_id: str | None = None,
        parent_id: str | None = None,
        purpose: str | None = None,
        folder: str | None = None,
        meta_extra: dict[str, Any] | None = None,
        parent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not data:
            raise bad_request("빈 파일은 올릴 수 없어요")
        limit = self.cfg.upload_max_bytes
        if len(data) > limit:
            raise _too_large(len(data), limit)
        if parent is None and parent_id:
            parent = self.get(parent_id)
        name = sanitize_name(name, "file")
        det = detect(data, name, declared_mime)
        meta: dict[str, Any] = {}
        if det.kind == "image" and det.fmt in ("heic", "heif"):
            try:
                jpeg, info = imaging.heic_to_jpeg(data)
                meta.update({"original_mime": det.mime, "original_name": name, "original_size": len(data)})
                stem = name.rsplit(".", 1)[0] if "." in name else name
                data, name = jpeg, f"{stem}.jpg"
                det = Detected("image", "image/jpeg", "jpeg")
            except Exception as exc:  # noqa: BLE001 — 변환 실패면 원본 그대로
                log.warning("HEIC 변환 실패(%s): %s", name, exc)
                meta["conversion_error"] = type(exc).__name__
        sha = self.blobs.put(data)
        q = quick_meta(data, det)
        meta.update(q["meta"])
        if det.kind in ("image",) and det.fmt not in ("jpeg", "png"):
            meta.setdefault("format", det.fmt)
        if det.kind == "text" and det.fmt != "txt":
            meta.setdefault("format", det.fmt)
        if meta_extra:
            meta.update({k: v for k, v in meta_extra.items() if v is not None})
        if parent is not None:
            confidential = bool(confidential or parent.get("confidential"))
            project_id = project_id or parent.get("project_id")
            meta["depth"] = int((parent.get("meta") or {}).get("depth") or 0) + 1
        can = self.can_parse(det.kind, det.fmt)
        status = "pending" if (source == "upload" and can) else ("none" if can else "unsupported")
        rec = {
            "name": name, "mime": det.mime, "size": len(data), "sha256": sha, "kind": det.kind, "fmt": det.fmt,
            "source": source, "confidential": bool(confidential), "owner": user.id, "owner_name": user.name,
            "project_id": project_id or None, "parent_id": parent["id"] if parent else None,
            "width": q.get("width"), "height": q.get("height"), "pages": q.get("pages"), "meta": meta,
            "purpose": purpose or None, "folder": _norm_folder(folder), "doc_props": q.get("doc_props"),
            "parse_status": status, "parse_error": None, "parse_version": None,
        }
        return self.store.put(COLL, new_id("file"), rec, keep_history=False)

    def copy(self, rec: dict[str, Any], *, user: User, folder: str | None, project_id: str | None, name: str | None) -> dict[str, Any]:
        new = {k: copy.deepcopy(v) for k, v in rec.items() if k not in ("id", "version", "created_at", "updated_at")}
        new.update({
            "name": sanitize_name(name, rec["name"]) if name else rec["name"], "owner": user.id, "owner_name": user.name,
            "folder": _norm_folder(folder) if folder is not None else rec.get("folder"),
            "project_id": project_id if project_id is not None else rec.get("project_id"), "parent_id": None,
            "parse_status": "none" if self.can_parse(rec["kind"], rec.get("fmt") or "") else "unsupported",
            "parse_error": None, "parse_version": None,
        })
        new["meta"] = {**(rec.get("meta") or {}), "copied_from": rec["id"]}
        return self.store.put(COLL, new_id("file"), new, keep_history=False)

    def patch(self, rec: dict[str, Any], changes: dict[str, Any], user: User) -> dict[str, Any]:
        _check_owner(rec, user)

        def apply(cur: dict[str, Any]) -> dict[str, Any]:
            if "name" in changes and changes["name"]:
                cur["name"] = sanitize_name(changes["name"], cur["name"])
            if "confidential" in changes and changes["confidential"] is not None:
                cur["confidential"] = bool(changes["confidential"])
            if "project_id" in changes:
                cur["project_id"] = changes["project_id"] or None
            if "purpose" in changes:
                cur["purpose"] = changes["purpose"] or None
            if "folder" in changes:
                cur["folder"] = _norm_folder(changes["folder"])
            if changes.get("meta") is not None:
                meta = dict(cur.get("meta") or {})
                for k, v in changes["meta"].items():
                    if v is None:
                        meta.pop(k, None)
                    else:
                        meta[k] = v
                cur["meta"] = meta
            return cur

        updated = self._update(rec["id"], apply)
        if "confidential" in changes and changes["confidential"] is not None and \
                bool(changes["confidential"]) != bool(rec.get("confidential")):
            self._propagate_confidential(updated["id"], bool(changes["confidential"]))
        return updated

    def _propagate_confidential(self, parent_id: str, value: bool, depth: int = 0) -> None:
        if depth > 3:
            return
        children, _ = self.store.list(COLL, where={"parent_id": parent_id}, limit=SCAN_MAX)
        for ch in children:
            if ch.get("source") == "derived" and bool(ch.get("confidential")) != value:
                try:
                    self._update(ch["id"], lambda cur: {**cur, "confidential": value})
                except ApiError as exc:
                    if exc.status != 404:
                        raise
                    continue
                self._propagate_confidential(ch["id"], value, depth + 1)

    def delete(self, rec: dict[str, Any], user: User) -> None:
        _check_owner(rec, user)
        # 먼저 데이터에 지움 표시(버전이 올라 겹친 갱신은 충돌 → 다시 읽으면 404), 그다음 DocStore 소프트 삭제
        self._update(rec["id"], lambda cur: {**cur, "deleted": True, "deleted_by": user.id})
        self.store.delete(COLL, rec["id"])
        sha = rec["sha256"]
        if self.store.count(COLL, where={"sha256": sha}) == 0:
            self.blobs.delete(sha)
            self.cache.purge(sha)

    def list(
        self,
        *,
        user: User,
        owner: str,
        project_id: str | None,
        source: str | None,
        kind: str | None,
        q: str | None,
        parent_id: str | None,
        purpose: str | None,
        folder: str | None,
        include_children: bool,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        where: dict[str, Any] = {}
        if owner == "me":
            where["owner"] = user.id
        elif owner and owner != "all":
            where["owner"] = owner
        if project_id:
            where["project_id"] = project_id
        if source:
            where["source"] = source
        if kind:
            kinds = [k.strip() for k in kind.split(",") if k.strip()]
            where["kind"] = kinds if len(kinds) > 1 else kinds[0]
        if purpose:
            where["purpose"] = purpose
        if folder:
            where["folder"] = _norm_folder(folder)
        if parent_id:
            where["parent_id"] = parent_id
        elif not include_children and source != "derived":
            where["parent_id"] = None
        rows, _ = self.store.list(COLL, where=where, order_by="-created_at", limit=SCAN_MAX)
        needle = unicodedata.normalize("NFC", q).casefold().strip() if q else ""
        out = []
        for r in rows:
            if r.get("deleted"):
                continue
            if needle and needle not in unicodedata.normalize("NFC", r["name"]).casefold():
                continue
            # 남의 기밀 파일은 프로젝트로 거를 때만 보인다
            if r.get("confidential") and r.get("owner") != user.id and not project_id:
                continue
            out.append(r)
        offset = _decode_cursor(cursor)
        page = out[offset:offset + limit]
        nxt = _encode_cursor(offset + limit) if offset + limit < len(out) else None
        return page, nxt

    # ── 파싱 ───────────────────────────────────────────
    def _semaphore(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        if self._sem is None or self._sem_loop is not loop:
            self._sem = asyncio.Semaphore(self.cfg.parse_concurrency)
            self._sem_loop = loop
        return self._sem

    def _record_cache_path(self, rec: dict[str, Any]) -> Path:
        return self.cache.path("parsed", rec["sha256"], f".v{PARSER_VERSION}.{rec['id']}.json")

    def _content_cache_path(self, sha: str, extract: bool) -> Path:
        return self.cache.path("parsed", sha, f".v{PARSER_VERSION}{'' if extract else '.nochild'}.json")

    async def parsed_json(self, rec: dict[str, Any], *, force: bool = False) -> bytes:
        """레코드의 ParsedDocument(JSON 바이트). 진행 중이면 그 작업을 기다린다."""
        if not self.can_parse(rec["kind"], rec.get("fmt") or ""):
            raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "이 형식은 읽을 수 없어요",
                           {"kind": rec["kind"], "format": rec.get("fmt")})
        if not force:
            hit = await asyncio.to_thread(self.cache.read, self._record_cache_path(rec))
            if hit:
                return hit
            if rec.get("parse_status") == "failed" and rec.get("parse_version") == PARSER_VERSION and rec.get("parse_error"):
                err = rec["parse_error"]
                raise ApiError(422, err.get("code") or "PARSE_FAILED", err.get("message") or "파일을 읽지 못했어요")
        task = self._record_inflight.get(rec["id"])
        if task is None or task.done() or force:
            task = asyncio.get_running_loop().create_task(self._parse_record(rec["id"], force))
            self._record_inflight[rec["id"]] = task
            task.add_done_callback(lambda t, fid=rec["id"]: self._record_done(fid, t))
        return await asyncio.shield(task)

    def _record_done(self, file_id: str, task: asyncio.Task[bytes]) -> None:
        if self._record_inflight.get(file_id) is task:
            self._record_inflight.pop(file_id, None)
        if not task.cancelled():
            task.exception()  # 기다리는 쪽이 없어도 경고가 나지 않게

    async def _parse_record(self, file_id: str, force: bool) -> bytes:
        rec = await asyncio.to_thread(self.get, file_id)
        await asyncio.to_thread(self._set_status, file_id, "parsing", None)
        try:
            extract = int((rec.get("meta") or {}).get("depth") or 0) == 0
            for attempt in range(2):
                content = await self._content(rec, extract, force or attempt > 0)
                try:
                    body, page_count = await asyncio.to_thread(self._materialize, rec, content)
                    break
                except _StaleCache:
                    continue
            else:
                raise ParseError("PARSE_FAILED", "자식 파일을 만들지 못했어요")
        except ParseError as exc:
            await asyncio.to_thread(self._set_status, file_id, "failed", {"code": exc.code, "message": exc.message})
            raise ApiError(422, exc.code, exc.message) from exc
        except Unsupported as exc:
            await asyncio.to_thread(self._set_status, file_id, "unsupported", {"code": "UNSUPPORTED_MEDIA_TYPE", "message": str(exc)})
            raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", str(exc)) from exc
        except ApiError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.exception("parse failed %s", file_id)
            await asyncio.to_thread(self._set_status, file_id, "failed", {"code": "PARSE_FAILED", "message": f"파일을 읽지 못했어요({type(exc).__name__})"})
            raise ApiError(422, "PARSE_FAILED", "파일을 읽지 못했어요", {"type": type(exc).__name__}) from exc
        await asyncio.to_thread(self._set_status, file_id, "done", None, page_count)
        return body

    def _set_status(self, file_id: str, status: str, error: dict[str, Any] | None, pages: int | None = None) -> None:
        def apply(cur: dict[str, Any]) -> dict[str, Any]:
            cur["parse_status"] = status
            cur["parse_error"] = error
            cur["parse_version"] = PARSER_VERSION if status in ("done", "failed", "unsupported") else cur.get("parse_version")
            if pages is not None and status == "done" and cur.get("kind") != "image":
                cur["pages"] = pages
            return cur

        try:
            self._update(file_id, apply)
        except ApiError as exc:
            if exc.status != 404:
                raise

    async def _content(self, rec: dict[str, Any], extract: bool, force: bool) -> dict[str, Any]:
        sha = rec["sha256"]
        path = self._content_cache_path(sha, extract)
        if not force:
            hit = await asyncio.to_thread(self.cache.read, path)
            if hit:
                try:
                    return json.loads(hit)
                except ValueError:
                    pass
        key = f"{sha}:{int(extract)}"
        fut = self._content_inflight.get(key)
        if fut is not None and not force:
            return await asyncio.shield(fut)
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        fut.add_done_callback(lambda f: f.cancelled() or f.exception())
        self._content_inflight[key] = fut
        try:
            async with self._semaphore():
                result = await asyncio.to_thread(self._run_parser, rec, extract)
            fut.set_result(result)
            return result
        except asyncio.CancelledError:
            if not fut.done():
                fut.cancel()
            raise
        except BaseException as exc:
            if not fut.done():
                fut.set_exception(exc)
            raise
        finally:
            if self._content_inflight.get(key) is fut:
                self._content_inflight.pop(key, None)

    def _convert_fn(self, sha: str) -> Callable[[bytes, str, str], bytes | None] | None:
        if not self.soffice.available:
            return None

        def convert(data: bytes, name: str, target: str) -> bytes | None:
            return self.soffice.convert(data, name, target, sha=sha)

        return convert

    def _run_parser(self, rec: dict[str, Any], extract: bool) -> dict[str, Any]:
        sha = rec["sha256"]
        try:
            data = self.blobs.read(sha)
        except FileNotFoundError as exc:
            raise ParseError("BLOB_MISSING", "파일 내용이 없어요") from exc
        ctx = ParseContext(
            name=rec["name"], fmt=rec.get("fmt") or "", extract_children=extract, max_children=self.cfg.max_children,
            pdf_layout_max_pages=self.cfg.pdf_layout_max_pages, src_path=self.blobs.path(sha), convert=self._convert_fn(sha),
        )
        t0 = time.time()
        out = parse_kind(rec["kind"], data, ctx)
        children = out.pop("_children", [])
        manifest = []
        for ch in children:
            self.blobs.put(ch.data, ch.key)
            manifest.append({"key": ch.key, "name": ch.name, "mime": ch.mime, "size": len(ch.data), "meta": ch.meta})
        out["children"] = manifest
        out["parser_version"] = PARSER_VERSION
        self.cache.write(self._content_cache_path(sha, extract), json.dumps(out, ensure_ascii=False).encode("utf-8"))
        log.info("parsed %s (%s, %d쪽, 자식 %d) %.2fs", rec["id"], rec["kind"], out.get("page_count", 0), len(manifest), time.time() - t0)
        return out

    def _materialize(self, rec: dict[str, Any], content: dict[str, Any]) -> tuple[bytes, int]:
        doc = copy.deepcopy({k: v for k, v in content.items() if k != "children"})
        mapping: dict[str, str] = {}
        children = content.get("children") or []
        if children:
            existing, _ = self.store.list(COLL, where={"parent_id": rec["id"]}, limit=SCAN_MAX)
            by_key = {(c.get("meta") or {}).get("child_key"): c["id"] for c in existing if c.get("source") == "derived"}
            user = User(id=rec["owner"], name=rec.get("owner_name") or "")
            for ch in children:
                fid = by_key.get(ch["key"])
                if fid is None:
                    try:
                        data = self.blobs.read(ch["key"])
                    except FileNotFoundError as exc:
                        raise _StaleCache(ch["key"]) from exc
                    meta = dict(ch.get("meta") or {})
                    meta["child_key"] = ch["key"]
                    try:
                        child = self.ingest(data, ch["name"], ch["mime"], user=user, source="derived",
                                            confidential=bool(rec.get("confidential")), project_id=rec.get("project_id"),
                                            meta_extra=meta, parent=rec)
                    except ApiError as exc:
                        log.info("child skipped (%s): %s", ch["name"], exc.message)
                        continue
                    fid = child["id"]
                    by_key[ch["key"]] = fid
                mapping[ch["key"]] = fid
        for page in doc.get("pages") or []:
            refs = page.pop("image_refs", []) or []
            page["image_file_ids"] = [mapping[r] for r in refs if r in mapping]
            page["images"] = [{"file_id": mapping[i["ref"]], "bbox": i.get("bbox")}
                              for i in (page.get("images") or []) if i.get("ref") in mapping]
            for b in page.get("blocks") or []:
                ref = b.pop("ref", None)
                if ref and ref in mapping:
                    b["file_id"] = mapping[ref]
        email = doc.get("email")
        if email:
            refs = email.pop("attachment_refs", []) or []
            email["attachments"] = [mapping[r] for r in refs if r in mapping]
            for a in email.get("attachment_list") or []:
                ref = a.pop("ref", None)
                a["file_id"] = mapping.get(ref) if ref else None
        doc["file_id"] = rec["id"]
        doc["kind"] = rec["kind"]
        model = ParsedDocument.model_validate(doc)
        body = model.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
        self.cache.write(self._record_cache_path(rec), body)
        return body, model.page_count

    def schedule_parse(self, rec: dict[str, Any]) -> None:
        """업로드 직후 백그라운드 파싱(결과는 parse_status · 캐시에 남는다)."""
        if rec["id"] in self._record_inflight:
            return

        async def run() -> None:
            try:
                await self.parsed_json(rec)
            except ApiError:
                pass
            except Exception:  # noqa: BLE001
                log.exception("background parse %s", rec["id"])

        try:
            task = asyncio.get_running_loop().create_task(run())
        except RuntimeError:
            return
        self._bg.add(task)
        task.add_done_callback(self._bg.discard)

    def maybe_resume(self, rec: dict[str, Any]) -> None:
        """'pending/parsing' 인데 이 프로세스에서 돌고 있지 않으면(재시작 등) 다시 시작한다."""
        if rec.get("parse_status") in ("pending", "parsing") and rec["id"] not in self._record_inflight:
            self.schedule_parse(rec)

    async def wait_idle(self) -> None:
        """테스트용: 백그라운드 파싱이 끝날 때까지.

        끝난 작업은 정리 콜백(call_soon)이 돌기 전까지 목록에 남는다. 끝난 것만 남았을 때 gather 는
        이벤트 루프에 양보하지 않고 바로 끝나므로(3.12 eager 완료) 끝나지 않은 작업만 기다리고, 없으면 한 번 양보한다.
        """
        while True:
            pending = [t for t in list(self._bg) + list(self._record_inflight.values()) if not t.done()]
            if not pending:
                await asyncio.sleep(0)
                pending = [t for t in list(self._bg) + list(self._record_inflight.values()) if not t.done()]
                if not pending:
                    return
            await asyncio.wait(pending)

    def content_doc_sync(self, rec: dict[str, Any]) -> dict[str, Any] | None:
        """미리보기용(자리표시 카드): 내용 파싱 캐시를 읽거나, 없으면 지금 파싱한다(자식은 만들지 않음)."""
        for extract in (True, False):
            hit = self.cache.read(self._content_cache_path(rec["sha256"], extract))
            if hit:
                try:
                    return json.loads(hit)
                except ValueError:
                    pass
        try:
            return self._run_parser(rec, False)
        except Exception as exc:  # noqa: BLE001
            log.info("preview parse failed %s: %s", rec["id"], exc)
            return None

    # ── 미리보기 ───────────────────────────────────────
    def _office_pdf(self, rec: dict[str, Any]) -> bytes | None:
        """PPTX · DOCX · XLSX · 옛 형식 → PDF(LibreOffice, 캐시)."""
        kind, fmt = rec["kind"], rec.get("fmt") or ""
        if kind not in OFFICE_KINDS and not (kind == "other" and fmt in SOFFICE_CONVERTIBLE):
            return None
        if not self.soffice.available:
            return None
        data = self.blobs.read(rec["sha256"])
        name = rec["name"] if "." in rec["name"] else f"{rec['name']}.{fmt or kind}"
        src_kind = "pptx" if kind == "pptx" or fmt in ("ppt", "odp") else kind
        return self.soffice.convert(data, name, "pdf", sha=rec["sha256"], src_kind=src_kind)

    def _pdf_source(self, rec: dict[str, Any]) -> bytes | Path | None:
        if rec["kind"] == "pdf":
            return self.blobs.path(rec["sha256"])
        return self._office_pdf(rec)

    def thumbnail(self, rec: dict[str, Any], w: int, fmt: str) -> tuple[bytes, str]:
        w = max(16, min(int(w), 1024))
        fmt = "png" if fmt == "png" else "webp"
        kind = rec["kind"]
        sha = rec["sha256"]
        lo = "lo" if self.soffice.available else "ph"
        path = self.cache.path("thumbs", sha, f"_{kind}_{lo}_w{w}.{fmt}")
        hit = self.cache.read(path)
        if hit:
            return hit, f"image/{fmt}"
        data: bytes | None = None
        try:
            if kind == "image":
                data = imaging.image_thumbnail(self.blobs.read(sha), w, fmt)
            elif kind == "pdf" or (kind in OFFICE_KINDS or (kind == "other" and rec.get("fmt") in SOFFICE_CONVERTIBLE)):
                src = self._pdf_source(rec)
                if src is not None:
                    img = pdfium.render_page(src, 1, w, max_ratio=2.0)
                    data = imaging.encode(imaging.fit_width(img, w), fmt)
                elif kind == "pptx":
                    data = imaging.encode(self._slide_card(rec, 1, w), fmt)
            elif kind == "svg" and self.soffice.available:
                png = self.soffice.convert(self.blobs.read(sha), rec["name"] if rec["name"].endswith(".svg") else "image.svg", "png", sha=sha)
                if png:
                    data = imaging.image_thumbnail(png, w, fmt)
        except Exception as exc:  # noqa: BLE001 — 미리보기 실패는 아이콘으로
            log.info("thumbnail failed %s: %s", rec["id"], exc)
            data = None
        if data is None:
            return self.icon(rec, w), "image/png"
        self.cache.write(path, data)
        return data, f"image/{fmt}"

    def icon(self, rec: dict[str, Any], w: int) -> bytes:
        label = kind_label(rec["kind"], rec.get("fmt") or "")
        if rec["kind"] == "email":
            label = "MAIL"
        path = self.cache.icon_path(f"{rec['kind']}_{label}_{w}.png".replace("/", "_"))
        hit = self.cache.read(path)
        if hit:
            return hit
        data = imaging.file_icon(label, rec["kind"], w)
        self.cache.write(path, data)
        return data

    def _slide_card(self, rec: dict[str, Any], n: int, w: int) -> Any:
        doc = self.content_doc_sync(rec) or {}
        pages = doc.get("pages") or []
        page = pages[n - 1] if 0 < n <= len(pages) else {}
        size = (doc.get("meta") or {}).get("slide_size") or (rec.get("meta") or {}).get("slide_size") or {}
        aspect = (size.get("width_emu") or 16) / (size.get("height_emu") or 9)
        body = [b["text"] for b in page.get("blocks") or [] if b.get("type") in ("body", "list", "heading") and b.get("text")]
        images = [b["bbox"] for b in page.get("blocks") or [] if b.get("type") == "image" and b.get("bbox")]
        return imaging.slide_card(title=page.get("title"), body=body[:4], images=images, page_no=n,
                                  page_count=len(pages) or (rec.get("pages") or 0), aspect=aspect, w=w)

    def page_count_for_preview(self, rec: dict[str, Any]) -> int | None:
        kind = rec["kind"]
        if kind == "image":
            return int((rec.get("meta") or {}).get("frames") or 1)
        return rec.get("pages")

    def page_image(self, rec: dict[str, Any], n: int, w: int, fmt: str, *, thumb: bool = False) -> tuple[bytes, str]:
        """n 쪽 그림. thumb 이면 렌더러가 없을 때 자리표시 카드 · 아이콘으로 대신한다."""
        fmt = fmt if fmt in ("png", "webp", "jpeg") else "png"
        w = max(16, min(int(w), 4096))
        kind = rec["kind"]
        sha = rec["sha256"]
        if n < 1:
            raise _page_not_found(n, None)
        known = self.page_count_for_preview(rec)
        if known is not None and kind != "pptx" and n > known:
            raise _page_not_found(n, known)
        lo = "lo" if self.soffice.available else "ph"
        path = self.cache.path("pages", sha, f"_p{n}_{lo}_w{w}.{fmt}")
        hit = self.cache.read(path)
        if hit:
            return hit, f"image/{fmt}"
        media = f"image/{fmt}"
        if kind == "image":
            data = self.blobs.read(sha)
            if n > 1:
                img = imaging.open_image(data)
                try:
                    img.seek(n - 1)
                except EOFError as exc:
                    raise _page_not_found(n, known) from exc
                out = imaging.encode(imaging.fit_width(img.convert("RGB"), w, max_ratio=100.0), fmt)
            else:
                out = imaging.page_image(data, w, fmt)
        else:
            src = self._pdf_source(rec)
            if src is None:
                if thumb:
                    if kind == "pptx":
                        if known is not None and n > known:
                            raise _page_not_found(n, known)
                        return imaging.encode(self._slide_card(rec, n, w), fmt), media
                    if n > 1:
                        raise _page_not_found(n, known)
                    return self.icon(rec, w), "image/png"
                if kind in OFFICE_KINDS or (kind == "other" and rec.get("fmt") in SOFFICE_CONVERTIBLE):
                    raise ApiError(501, "PREVIEW_UNAVAILABLE", "LibreOffice 가 없어 쪽 미리보기를 만들 수 없어요(SOFFICE_PATH)",
                                   {"kind": kind})
                raise ApiError(501, "PREVIEW_UNAVAILABLE", "이 형식은 쪽 미리보기가 없어요", {"kind": kind})
            try:
                img = pdfium.render_page(src, n, w)
            except IndexError as exc:
                total = None
                try:
                    total = pdfium.page_count(src)
                except Exception:  # noqa: BLE001
                    pass
                raise _page_not_found(n, total) from exc
            except pdfium.EncryptedPdf as exc:
                raise ApiError(422, "FILE_ENCRYPTED", "암호가 걸린 PDF 라 미리보기를 만들 수 없어요") from exc
            out = imaging.encode(img, fmt)
        self.cache.write(path, out)
        return out, media

    # ── 내용 내려주기 ───────────────────────────────────
    def content_headers(self, rec: dict[str, Any], download: bool) -> tuple[Path, str, dict[str, str]]:
        path = self.blobs.path(rec["sha256"])
        if not path.is_file():
            raise ApiError(410, "BLOB_MISSING", "파일 내용이 없어요")
        mime = rec["mime"]
        media = mime
        if rec["kind"] == "text" or mime.startswith("text/"):
            from .textutil import http_charset

            cs = http_charset((rec.get("meta") or {}).get("encoding")) or "utf-8"
            media = f"{mime}; charset={cs}"
        risky = mime in _RISKY_INLINE or mime.endswith("+xml") and mime != "image/svg+xml"
        disposition = "attachment" if (download or risky) else "inline"
        headers = {
            "content-disposition": content_disposition(disposition, rec["name"]),
            "etag": f'"{rec["sha256"]}"',
            "cache-control": "private, max-age=86400",
            "x-content-type-options": "nosniff",
        }
        if mime == "image/svg+xml" or risky:
            headers["content-security-policy"] = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; sandbox"
        return path, media, headers


# ── 도우미 ─────────────────────────────────────────────────────

def _check_owner(rec: dict[str, Any], user: User) -> None:
    if user.id not in (rec.get("owner"), "system"):
        raise forbidden("올린 사람만 바꾸거나 지울 수 있어요", owner=rec.get("owner"))


def _page_not_found(n: int, total: int | None) -> ApiError:
    return ApiError(404, "PAGE_NOT_FOUND", f"{n}쪽이 없어요", {"page": n, "page_count": total})


def _norm_folder(folder: str | None) -> str | None:
    if folder is None:
        return None
    parts = [unicodedata.normalize("NFC", p).strip() for p in folder.replace("\\", "/").split("/")]
    parts = [p for p in parts if p and p not in (".", "..")]
    return "/".join(parts)[:300] or None


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        pad = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(cursor + pad).decode()
        return max(0, int(raw.split(":", 1)[1])) if raw.startswith("o:") else 0
    except (ValueError, IndexError):
        return 0


def content_disposition(disposition: str, name: str) -> str:
    """RFC 6266/5987: ASCII 대체 이름 + filename*=UTF-8''(한글 이름)."""
    from urllib.parse import quote

    stem, dot, ext = name.rpartition(".")
    if not dot or not ext.isascii() or not ext.isalnum() or len(ext) > 10:
        stem, ext = name, ""
    ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    ascii_stem = "".join(ch if (ch.isalnum() or ch in "._- ()[]") else "_" for ch in ascii_stem)
    ascii_stem = " ".join(ascii_stem.split()).strip(" ._-")
    if not any(ch.isalnum() for ch in ascii_stem):
        ascii_stem = "file"
    ascii_name = (ascii_stem[:140] + (f".{ext}" if ext else "")).replace('"', "")
    return f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name, safe='')}"


_service: FilesService | None = None


def service() -> FilesService:
    """프로세스 하나에 하나. 테스트에서 DATA_DIR 이 바뀌면 새로 만든다."""
    global _service
    cfg = files_settings()
    if _service is None or _service.data_dir != cfg.data_dir:
        _service = FilesService(cfg)
    return _service


def b64decode_strict(data_b64: str) -> bytes:
    s = data_b64.strip()
    if s.startswith("data:") and "," in s[:200]:
        s = s.split(",", 1)[1]
    try:
        return base64.b64decode(s, validate=False)
    except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        raise bad_request("data_b64 가 올바른 base64 가 아니에요") from exc

