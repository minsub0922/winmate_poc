"""결과 버전 만들기 · 집계 · 작업 상태 반영(§5.3). 실행 · 재분석 · 확정 반영 · 레이아웃 · 되돌리기 · 가져오기가 함께 쓴다."""
from __future__ import annotations

import copy
from typing import Any, Callable

from winmate_common.context import current_user
from winmate_common.ids import now_iso

from . import fixes, layout, service
from . import store as R


def counts(version: dict[str, Any]) -> dict[str, int]:
    srcs = list((version.get("sources") or {}).values())
    claims = list((version.get("claims") or {}).values())
    fx = version.get("fix_items") or {}
    return {
        "sources_total": len(srcs),
        "used": sum(1 for s in srcs if s.get("state", "used") == "used"),
        "checking": sum(1 for s in srcs if s.get("state") == "checking"),
        "excluded": sum(1 for s in srcs if s.get("state") == "excluded"),
        "needs_check": sum(1 for c in claims if c.get("status") not in ("matched", "confirmed")),
        "fix_open": sum(1 for f in fx.values() if f.get("status") == "warn"),
    }


def refresh_derived(analysis: dict[str, Any], version: dict[str, Any], previous: dict[str, Any] | None = None, *,
                    recompose_slides: bool = True) -> None:
    """확정 필요 항목 · 시트 구성 · 집계를 지금 결과로 다시 만든다(이전 버전 상태는 이어받는다)."""
    prev_fix = (previous or {}).get("fix_items") or version.get("fix_items") or {}
    version["fix_items"] = fixes.build(analysis, version, prev_fix)
    if recompose_slides:
        prev_slides = (previous or {}).get("slides") or version.get("slides") or []
        version["slides"] = layout.sheet_plan(analysis, version, previous=prev_slides)
    fix_by_area: dict[str, int] = {}
    for f in version["fix_items"].values():
        if f.get("status") == "warn":
            fix_by_area[f.get("tab", "")] = fix_by_area.get(f.get("tab", ""), 0) + 1
    for s in version.get("slides") or []:
        s["fix_open"] = fix_by_area.get(s.get("area") or "", 0)
    version["counts"] = counts(version)


async def save_new_version(analysis: dict[str, Any], base: dict[str, Any], *, kind: str, summary: str = "",
                           mutate: Callable[[dict[str, Any]], None] | None = None, stopped: bool = False,
                           recompose_slides: bool = True, status: str | None = "done") -> int:
    """base 를 복사(+ mutate)해 새 버전 n+1 로 저장하고 작업 상태 · 집계 · 색인을 갱신한다."""
    aid = analysis["id"]
    cur = await R.call(R.get_analysis, aid) or analysis
    n = int(cur.get("result_version") or 0) + 1
    v = copy.deepcopy(base)
    v.pop("id", None)
    if mutate:
        mutate(v)
    v["kind"] = kind
    v["created_at"] = now_iso()
    v["created_by"] = current_user().name
    v["stopped"] = stopped
    v["summary"] = summary or v.get("summary", "")
    refresh_derived(cur, v, v, recompose_slides=recompose_slides)      # 고친(mutate) 뒤 항목 · 시트 상태를 이어받는다
    await R.call(R.put_version, aid, n, v)

    def upd(doc: dict[str, Any]) -> None:
        doc["result_version"] = n
        if status:
            doc["status"] = status
        doc["edit_after_analysis"] = kind not in ("full", "changed_only", "resume", "auto")
        run = doc.setdefault("run", {})
        run["sources_used"] = v["counts"]["used"]
        run["fix_open"] = v["counts"]["fix_open"]
        run["sources_total"] = v["counts"]["sources_total"]

    saved = await R.call(R.update_analysis, aid, upd)
    await service.register(saved)
    return n


async def update_current(analysis: dict[str, Any], fn: Callable[[dict[str, Any]], None], *, recompose_slides: bool = False) -> dict[str, Any]:
    """지금 버전을 그 자리에서 고친다(출처 빼기 · 확정 값 입력 등 작업 상태 변경) + 집계 · 색인."""
    aid = analysis["id"]
    n = int(analysis.get("result_version") or 0)

    def change(v: dict[str, Any]) -> None:
        fn(v)
        refresh_derived(analysis, v, None, recompose_slides=recompose_slides)

    v = await R.call(R.update_version, aid, n, change)

    def upd(doc: dict[str, Any]) -> None:
        run = doc.setdefault("run", {})
        run["sources_used"] = v["counts"]["used"]
        run["fix_open"] = v["counts"]["fix_open"]

    saved = await R.call(R.update_analysis, aid, upd)
    await service.register(saved)
    return v
