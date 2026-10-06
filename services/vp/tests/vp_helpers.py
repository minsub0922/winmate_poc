"""vp 테스트 도우미(잡 처리 · 파일 올리기 · 픽스처 문장)."""
from __future__ import annotations

from winmate_common import testing


async def run_jobs(max_jobs: int = 50) -> int:
    from winmate_vp.worker import HANDLERS

    return await testing.drain_jobs("vp", HANDLERS, max_jobs=max_jobs)


async def upload(name: str, text: str, mime: str = "text/plain") -> str:
    from winmate_common.platform import save_file

    fm = await save_file(name, text.encode("utf-8"), mime, source="upload", confidential=True)
    return fm["id"]


RFP_TEXT = """A 커피 프랜차이즈 디지털 메뉴보드 도입 제안요청서(RFP)

1. 사업 개요
전국 직영 · 가맹 매장 320곳의 종이 메뉴보드를 디지털 메뉴보드로 바꾼다.

2. 현황과 문제
메뉴가 바뀔 때마다 인쇄물을 만들어 매장에 배송하고 있어 인쇄 · 배송 비용 부담이 크다.
매장마다 가격 표기가 달라 오표기가 반복된다.
피크 시간 주문 대기가 길어 손님 불편이 크다.

3. 바라는 모습
본사에서 모든 매장 메뉴를 한 번에 운영하는 것이 목표다.

4. 결재
결재는 본사 운영본부장이 한다.

5. 평가 기준
기술 이해도 40점
운영 편의성 30점
수행 능력 30점
"""


async def ready_vp(client, *, customer: str = "A 커피 프랜차이즈", note: str = "", rfp: bool = True, generate: bool = True,
                   **body) -> str:
    """RFP 첨부 → 재료 → (되묻기 기본값) → 생성까지 끝낸 작업 id."""
    r = await client.post("/v1/vps", json={"start": "direct", "customer_name": customer, "note": note or None, **body})
    assert r.status_code == 201, r.text
    vid = r.json()["id"]
    if rfp:
        fid = await upload("A커피_디지털메뉴보드_RFP.txt", RFP_TEXT)
        r = await client.post(f"/v1/vps/{vid}/attachments", json={"file_id": fid})
        assert r.status_code == 201, r.text
    r = await client.post(f"/v1/vps/{vid}/materials:collect", json={})
    assert r.status_code == 202, r.text
    await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    if [q for q in doc["questions"] if q["status"] == "open"]:
        r = await client.post(f"/v1/vps/{vid}/questions:answer", json={"answers": [], "proceed": True})
        assert r.status_code == 200, r.text
        await run_jobs()
    if generate:
        r = await client.post(f"/v1/vps/{vid}/generate", json={})
        assert r.status_code == 202, r.text
        await run_jobs()
        doc = (await client.get(f"/v1/vps/{vid}")).json()
        assert doc["generated"] is True, doc.get("last_error")
    return vid
