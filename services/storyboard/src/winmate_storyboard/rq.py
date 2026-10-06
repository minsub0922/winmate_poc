"""requirements 호출(01-requirements.md §6 — 계약 contracts/requirements.json 으로 검증) + 스냅숏 정리.

정의서 버전 스냅숏(§5.9)에서 읽는 것만 쓴다: 항목 `id · code · text · short · keyman · needs_confirmation · entities`,
키맨 · 가중치, 최종 제안대상, 제작자 의견(**internal** — 내부 목표 판별에만, 고객용 출력 금지), 열린 고객 질문, `context`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError

from . import repo

log = logging.getLogger("winmate.storyboard.rq")


def client() -> ServiceClient:
    return ServiceClient("requirements", timeout=30)


def _upstream(exc: Exception, what: str) -> ApiError:
    if isinstance(exc, ApiError):
        if exc.status == 404:
            return ApiError(404, "NOT_FOUND", f"{what}을(를) 찾을 수 없어요", {"upstream": exc.code})
        if exc.status < 500 and exc.code not in ("UNAUTHENTICATED",):
            return exc
    return ApiError(502, "UPSTREAM_FAILED", f"요구사항 정의서를 불러오지 못했어요({what}). 잠시 후 다시 시도해 주세요.",
                    {"service": "requirements", "error": str(exc)[:300]})


def _val(field_: Any) -> Any:
    """정의서 Field({value, source}) 또는 값 그대로."""
    if isinstance(field_, dict) and "value" in field_:
        return field_.get("value")
    return field_


@dataclass
class RqItem:
    id: str
    code: str
    text: str
    short: str = ""
    keyman_id: str | None = None
    keyman_name: str = ""
    needs_confirmation: bool = False
    entities: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RqSnapshot:
    requirement_id: str
    version: int
    title: str = ""
    project_id: str | None = None
    customer_name: str = ""
    project_name: str = ""
    final_audience: str = ""
    author_note: str = ""            # internal — 고객용 출력에 넣지 않는다
    keymen: list[dict[str, Any]] = field(default_factory=list)
    items: list[RqItem] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    customer_questions: list[dict[str, Any]] = field(default_factory=list)
    note: str | None = None
    saved_at: str | None = None
    source_files: list[dict[str, Any]] = field(default_factory=list)

    @property
    def open_questions(self) -> list[dict[str, Any]]:
        return [q for q in self.customer_questions if (q.get("status") or "open") == "open"]

    def item_by_code(self, code: str) -> RqItem | None:
        code = normalize_code(code)
        return next((i for i in self.items if i.code == code), None)

    def spaces(self) -> list[dict[str, Any]]:
        return [s for s in (self.context.get("spaces") or []) if isinstance(s, dict) and s.get("name")]

    def vertical_id(self) -> str | None:
        v = self.context.get("vertical") or {}
        top = (v.get("top2") or []) if isinstance(v, dict) else []
        if top and isinstance(top[0], dict) and not v.get("ask"):
            return top[0].get("id")
        return None

    def items_text(self) -> list[str]:
        return [i.text for i in self.items]

    def customer_facing_text(self) -> list[str]:
        """숫자 가드 허용 목록에 쓰는 글(제작자 의견은 넣지 않는다)."""
        out = [self.title, self.customer_name, self.project_name, self.final_audience]
        out += [i.text for i in self.items] + [i.short for i in self.items]
        out += [q.get("text", "") for q in self.customer_questions]
        for k in ("scale_text", "deadline_text"):
            if self.context.get(k):
                out.append(str(self.context[k]))
        return [t for t in out if t]


def normalize_code(code: str) -> str:
    code = (code or "").strip().upper().replace(" ", "")
    if code.startswith("RQ") and not code.startswith("RQ-"):
        code = "RQ-" + code[2:]
    if code.startswith("RQ-"):
        num = code[3:]
        if num.isdigit():
            code = f"RQ-{int(num):02d}"
    return code


def parse_snapshot(rq_id: str, raw: dict[str, Any], requirement: dict[str, Any] | None = None) -> RqSnapshot:
    """RequirementVersion(contracts/requirements.json) → RqSnapshot."""
    snap = raw.get("snapshot") or raw
    form = snap.get("form") or {}
    keymen = []
    names: dict[str, str] = {}
    for km in (snap.get("keymen") or form.get("keymen") or []):
        names[km.get("id", "")] = km.get("name", "")
        keymen.append({"id": km.get("id"), "name": km.get("name", ""), "weight": km.get("weight")})
    items: list[RqItem] = []
    flat = snap.get("items_flat")
    if flat is None:  # 폼 안 키맨 항목에서 펼친다(이전 형식 대비)
        flat = []
        for km in form.get("keymen") or []:
            for it in km.get("items") or []:
                flat.append({**it, "keyman_id": km.get("id"), "keyman_name": km.get("name")})
    for i, it in enumerate(flat, 1):
        items.append(RqItem(
            id=it.get("id") or f"ri_{i}", code=normalize_code(it.get("code") or f"RQ-{i:02d}"), text=it.get("text") or "",
            short=it.get("short") or "", keyman_id=it.get("keyman_id"),
            keyman_name=it.get("keyman_name") or names.get(it.get("keyman_id") or "", ""),
            needs_confirmation=bool(it.get("needs_confirmation")), entities=list(it.get("entities") or []),
        ))
    items.sort(key=lambda x: x.code)
    req = requirement or {}
    customer = raw.get("customer_name") or _val(form.get("customer_name")) or ""
    project = raw.get("project_name") or _val(form.get("project_name")) or ""
    title = raw.get("title") or req.get("title") or " ".join(x for x in (customer, project) if x) or "요구사항 정의서"
    author = _val(snap.get("author_note")) or _val(form.get("author_note")) or ""
    return RqSnapshot(
        requirement_id=rq_id, version=int(raw.get("version") or req.get("version") or 0), title=title,
        project_id=raw.get("project_id") or req.get("project_id"), customer_name=customer,
        project_name=project, final_audience=raw.get("final_audience") or _val(form.get("final_audience")) or "",
        author_note=author, keymen=keymen, items=items, context=snap.get("context") or {},
        customer_questions=list(snap.get("customer_questions") or []), note=raw.get("note"),
        saved_at=raw.get("created_at") or req.get("saved_at"), source_files=list(snap.get("source_files") or []),
    )


# ── 호출 ──────────────────────────────────────────────────

async def get_requirement(rq_id: str) -> dict[str, Any]:
    try:
        return await client().get(f"/v1/requirements/{rq_id}")
    except Exception as exc:  # noqa: BLE001
        raise _upstream(exc, "정의서") from exc


async def get_snapshot(rq_id: str, version: int, *, requirement: dict[str, Any] | None = None) -> RqSnapshot:
    raw = await repo.cached_snapshot(rq_id, version)
    if raw is None:
        try:
            raw = await client().get(f"/v1/requirements/{rq_id}/versions/{version}")
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, ApiError) and exc.status == 404:
                raise ApiError(404, "VERSION_NOT_FOUND", f"정의서 v{version}을(를) 찾을 수 없어요") from exc
            raise _upstream(exc, f"정의서 v{version}") from exc
        await repo.cache_snapshot(rq_id, version, raw)
    return parse_snapshot(rq_id, raw, requirement)


async def get_diff(rq_id: str, frm: int, to: int) -> dict[str, Any]:
    try:
        return await client().get(f"/v1/requirements/{rq_id}/diff", params={"from": frm, "to": to})
    except Exception as exc:  # noqa: BLE001
        raise _upstream(exc, "정의서 비교") from exc


async def get_reply(rq_id: str, reply_id: str) -> dict[str, Any]:
    try:
        return await client().get(f"/v1/requirements/{rq_id}/replies/{reply_id}")
    except Exception as exc:  # noqa: BLE001
        raise _upstream(exc, "고객 답변 분석") from exc


async def get_versions(rq_id: str) -> list[dict[str, Any]]:
    """정의서 버전 목록(요약 · 메모 · 변경 수) — SB3 띠 한 줄(`rq_update.note`)에 쓴다."""
    try:
        res = await client().get(f"/v1/requirements/{rq_id}/versions")
    except Exception as exc:  # noqa: BLE001
        raise _upstream(exc, "정의서 버전") from exc
    return list((res or {}).get("items") or [])


def update_note(versions: list[dict[str, Any]], frm: int, to: int) -> str | None:
    """지금 쓰는 버전(frm) 뒤 새로 저장된 버전들(…to)의 변경 수 합 · 가장 최근 저장 메모 — 「변경 3건 · 키맨 연락처 갱신」."""
    newer = sorted((v for v in versions if frm < int(v.get("version") or 0) <= to), key=lambda v: int(v.get("version") or 0))
    if not newer:
        return None
    n = sum(int(v.get("change_count") or 0) for v in newer)
    memo = next((str(v["note"]).strip() for v in reversed(newer) if (v.get("note") or "").strip()), None)
    parts = [f"변경 {n}건" if n else None, memo]
    return " · ".join(p for p in parts if p) or None


async def get_links(rq_id: str) -> list[dict[str, Any]]:
    try:
        res = await client().get(f"/v1/requirements/{rq_id}/links")
    except Exception as exc:  # noqa: BLE001
        raise _upstream(exc, "쓰는 곳") from exc
    return list((res or {}).get("items") or [])


async def put_link(rq_id: str, sb_id: str, *, title: str, route: str, rq_version: int,
                   depends_on: list[dict[str, Any]]) -> dict[str, Any] | None:
    body = {"title": title, "route": route, "rq_version": rq_version, "depends_on": depends_on}
    try:
        return await client().put(f"/v1/requirements/{rq_id}/links/storyboard/{sb_id}", json=body)
    except Exception as exc:  # noqa: BLE001 — 링크 등록 실패가 본 작업을 막지 않는다(다음 저장 때 다시)
        log.warning("정의서 링크 등록 실패 %s/%s: %s", rq_id, sb_id, exc)
        return None


async def add_customer_question(rq_id: str, *, sb_id: str, text: str, short_label: str, place_label: str,
                                target: dict[str, Any] | None = None, keyman_id: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "text": text[:120], "short_label": short_label[:24],
        "origin": {"kind": "storyboard", "service": "storyboard", "ref_id": sb_id, "place_label": place_label[:60]},
    }
    if target:
        body["target"] = target
    if keyman_id:
        body["keyman_id"] = keyman_id
    try:
        return await client().post(f"/v1/requirements/{rq_id}/customer-questions", json=body)
    except Exception as exc:  # noqa: BLE001
        raise _upstream(exc, "고객 질문 추가") from exc
