"""export_run(§7.12) — 범위 · 버전 → 렌더 문서 → (영문이면 번역 `pr.translate_en`) → export 로 형식마다 → 팀 폴더 복사.

검토 코멘트 · '추론' 표시는 넣지 않는다. 영문은 export 가 [확정 필요] → [TBD] 로 바꾼다.
"""
from __future__ import annotations

import copy
import logging
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.jobs import JobContext

from .. import clients, config, core, defs, prompts, render_doc as R, repo, versions as VER
from . import common as G

log = logging.getLogger("winmate.proposal.export")

SKIP_KEYS = {"file_id", "url", "type", "highlight_col", "highlight_rows", "unit", "kind", "caption"}


def collect_texts(doc: dict[str, Any]) -> list[tuple[list[Any], str]]:
    """번역할 글(경로, 글) — 칸 값 · 표 · 카드 · 노트 · 표지."""
    out: list[tuple[list[Any], str]] = []

    def walk(v: Any, path: list[Any]) -> None:
        if isinstance(v, str):
            if v.strip() and any("가" <= ch <= "힣" for ch in v):
                out.append((path, v))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, [*path, i])
        elif isinstance(v, dict):
            for k, x in v.items():
                if k in SKIP_KEYS:
                    continue
                walk(x, [*path, k])
    walk(doc.get("cover") or {}, ["cover"])
    for i, s in enumerate(doc.get("slides") or []):
        walk(s.get("slots") or {}, ["slides", i, "slots"])
        if s.get("notes"):
            walk(s["notes"], ["slides", i, "notes"])
    for k in ("title", "footer"):
        if doc.get(k):
            walk(doc[k], [k])
    return out


def _set(doc: Any, path: list[Any], value: str) -> None:
    cur = doc
    for p in path[:-1]:
        cur = cur[p]
    cur[path[-1]] = value


async def translate(doc: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """→ (영문 문서, 번역 못 한 문장 수). 값 토큰은 이미 풀린 상태(표시 문자열)."""
    out = copy.deepcopy(doc)
    texts = collect_texts(out)
    missing = 0
    for start in range(0, len(texts), 40):
        batch = texts[start:start + 40]
        items = [{"id": f"t{start + i + 1}", "text": t} for i, (_p, t) in enumerate(batch)]
        user = "제안서 슬라이드 글을 영어로. 숫자 · 단위 · 모델명 · [00] 같은 자리표시 · [확정 필요] 표시는 그대로 둔다.\n" + "\n".join(
            f"- id={x['id']} · {x['text']}" for x in items)
        res = await G.llm_json("pr.translate_en", system=prompts.RULES, user=user, schema=prompts.TRANSLATE, confidential=G.customer_conf())
        got = {str(x.get("id")): x.get("en") for x in (res or {}).get("items") or [] if x.get("en")}
        for i, (path, _t) in enumerate(batch):
            en = got.get(f"t{start + i + 1}")
            if en:
                _set(out, path, en)
            else:
                missing += 1
    out["lang"] = "en"
    return out, missing


async def handle(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid, xid = pl["proposal_id"], pl["export_id"]

    async def run(_s: dict[str, Any]) -> dict[str, Any]:
        x = await repo.amust("exports", xid)
        await repo.amutate("exports", xid, lambda d: d.update({"status": "running"}))
        p = await core.load(pid)
        snap = None
        v = x.get("pr_version")
        if v and (int(v) != int(p.get("saved_version") or 0) or int(p.get("edits_since_version") or 0) > 0):
            ver = await VER.get_version(pid, int(v))
            snap = (ver or {}).get("snapshot")
        shs = (snap or {}).get("sheets") if snap else await core.sheets_of(pid)
        sc = x.get("scope") or {}
        sheet_ids = None
        if sc.get("kind") == "sections":
            sheet_ids = [s["id"] for s in shs or [] if s.get("section_key") in (sc.get("section_keys") or [])]
        elif sc.get("kind") == "sheets":
            from ..ops.exports import parse_range
            nos = set(parse_range(sc.get("range") or "", max((int(s.get("sheet_no") or 0) for s in shs or []), default=0)))
            sheet_ids = [s["id"] for s in shs or [] if int(s.get("sheet_no") or 0) in nos]
        inc = x.get("include") or {}
        built = await R.build(pid, sheet_ids=sheet_ids, tbd_mode=x.get("tbd_mode") or "keep_marks", include_inferred_marks=False,
                              snapshot=snap, include_notes=bool(inc.get("speaker_notes", True)), include_sources=bool(inc.get("footnotes", True)),
                              master_id=x.get("master_id"), for_export=True)
        langs = ["ko", "en"] if x.get("lang") == "ko_en" else [x.get("lang") or "ko"]
        files: list[dict[str, Any]] = []
        warnings: list[str] = []
        base = x.get("filename_base") or R.file_base(p, int(v or p.get("saved_version") or 1))
        total = len(langs) * len(x.get("formats") or [])
        done = 0
        for lg in langs:
            await G.check_cancel()
            doc = built["document"]
            if lg == "en":
                doc, missing = await translate(doc)
                if missing:
                    warnings.append(f"영문 번역을 받지 못한 문장 {missing}개는 한국어로 두었어요")
            for fmt in x.get("formats") or ["pptx"]:
                name = f"{base}_{lg.upper()}" if x.get("lang") == "ko_en" else base
                try:
                    res = await R.export_pptx(pid, {**built, "document": doc}, filename=name, language=lg, tbd_mode=x.get("tbd_mode") or "keep_marks",
                                              fmt=fmt)
                except ApiError as exc:
                    if fmt == "pdf" and exc.code in ("PDF_CONVERTER_UNAVAILABLE", "NOT_IMPLEMENTED") or exc.status == 501:
                        warnings.append("PDF 변환기가 없어 PDF는 만들지 못했어요(PPTX 를 PowerPoint 에서 PDF 로 저장해 주세요)")
                        continue
                    raise
                for f in res.get("files") or ([res["file"]] if res.get("file") else []):
                    files.append({"lang": (f.get("lang") or lg).lower(), "format": fmt, "name": f.get("name") or f"{name}.{fmt}", "file_id": f["id"],
                                  "size": f.get("size"), "url": f"/api/files/v1/files/{f['id']}/content?download=true"})
                warnings += res.get("warnings") or []
                done += 1
                await G.progress(int(90 * done / max(1, total)), f"{name}.{fmt}")
        team_files: list[str] = []
        tf = x.get("team_folder") or {}
        if tf.get("enabled") and files:
            for f in files:
                cp = await clients.call("files", "POST", f"/v1/files/{f['file_id']}/copy", json={"folder": tf.get("path"), "project_id": p.get("project_id")},
                                        quiet=True)
                if cp and cp.get("id"):
                    team_files.append(cp["id"])
        await repo.amutate("exports", xid, lambda d: d.update({"status": "done", "files": files, "warnings": list(dict.fromkeys(warnings)),
                                                             "team_folder_files": team_files, "done_iso": config.now_iso()}))
        if not v or int(v) == int(p.get("saved_version") or 0):
            pdf = next((f["file_id"] for f in files if f["format"] == "pdf" and f["lang"] in ("ko", langs[0])), None)
            if pdf:
                await core.mutate(pid, lambda y: y.update({"files": {**(y.get("files") or {}), "pdf_file_id": pdf}}), bump=False)
        return {"result": {"proposal_id": pid, "export_id": xid, "files": files, "warnings": warnings}}

    try:
        final = await G.run(ctx, G.single("export", run), {}, labels={"export": "내보내기"}, progress_map={"export": 100})
    except BaseException as exc:
        err = {"code": getattr(exc, "code", None) or type(exc).__name__, "message": getattr(exc, "message", None) or str(exc)}
        try:
            await repo.amutate("exports", xid, lambda d: d.update({"status": "failed", "error": err}))
        except Exception:  # noqa: BLE001
            pass
        raise
    return (final or {}).get("result") or {}
