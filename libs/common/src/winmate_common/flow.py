"""새 콘텐츠 흐름(docs/scenarios/11-content-flow.md)의 Storyboard 허브 호출 도우미 — 콘텐츠 서비스가 쓴다.

    from winmate_common.flow import get_flow, push_stage

    flow = await get_flow("SB-01")                       # flow.json 전체(사전 작업 값: flow["stages"]["dss"] …), 없으면 None
    out = await push_stage("SB-01", "mi", ref="MI-01", ver=1, res_id=doc_id, title="용산 오피스 시장 분석",
                           value={...stages.mi 실제 값...}, md="- 담은 정보 11 …", card={...ContentPopup 값...})
    # out = {"flow": FlowDoc, "key": "mi", "md_added": "...", "synced": [...]} · 허브가 안 되면 None(콘텐츠 저장은 계속)

호출하는 서비스는 config/services.yaml consumes 에 storyboard 가 있어야 한다. 계약: contracts/storyboard.json `/v1/flows*`.
"""
from __future__ import annotations

import logging
from typing import Any

from .client import ServiceClient
from .errors import ApiError

log = logging.getLogger("winmate.flow")


async def get_flow(sb_id: str) -> dict[str, Any] | None:
    try:
        return await ServiceClient("storyboard").get(f"/v1/flows/{sb_id}")
    except ApiError as exc:
        if exc.status == 404:
            return None
        log.warning("Storyboard %s 를 읽지 못함: %s", sb_id, exc.code)
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("Storyboard %s 를 읽지 못함: %s", sb_id, exc)
        return None


async def push_stage(sb_id: str, key: str, *, ref: str, ver: int = 1, value: dict[str, Any], md: str = "",
                     res_id: str | None = None, title: str | None = None, card: dict[str, Any] | None = None) -> dict[str, Any] | None:
    body: dict[str, Any] = {"ref": ref, "ver": ver, "value": value, "md": md, "res_id": res_id, "title": title}
    if card:
        body["card"] = card
    try:
        return await ServiceClient("storyboard").put(f"/v1/flows/{sb_id}/stages/{key}", json=body)
    except ApiError as exc:
        if exc.code == "PREREQUISITE_MISSING":
            raise
        log.warning("Storyboard %s stages.%s 반영 실패: %s %s", sb_id, key, exc.code, exc.message)
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("Storyboard %s stages.%s 반영 실패: %s", sb_id, key, exc)
        return None


async def create_flow(name: str, *, customer: str | None = None, target: str | None = None, rq: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """고객 요구사항 저장 → Storyboard 자동 생성(requirements 전용)."""
    try:
        return await ServiceClient("storyboard").post("/v1/flows", json={"name": name, "customer": customer, "target": target, "rq": rq})
    except Exception as exc:  # noqa: BLE001
        log.warning("Storyboard 자동 생성 실패: %s", exc)
        return None
