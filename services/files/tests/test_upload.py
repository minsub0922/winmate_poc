"""올리기 · 메타 · 내려받기 · 목록 · 바꾸기 · 지우기 · 사본 · 내부 저장."""
from __future__ import annotations

import base64
import re
from urllib.parse import quote

import files_samples as S

ID_RE = re.compile(r"^file_[0-9A-HJKMNP-TV-Z]{26}$")


async def test_upload_pdf_meta(client, up):
    meta = await up(client, "용산_제안요청서.pdf", S.pdf_rfp(), confidential="true", project_id="prj_1", purpose="rq.source")
    assert ID_RE.match(meta["id"])
    assert meta["kind"] == "pdf" and meta["mime"] == "application/pdf"
    assert meta["name"] == "용산_제안요청서.pdf"
    assert meta["source"] == "upload" and meta["confidential"] is True
    assert meta["owner"] == "u_test" and meta["owner_name"] == "테스터"
    assert meta["project_id"] == "prj_1" and meta["parent_id"] is None and meta["purpose"] == "rq.source"
    assert meta["pages"] == 2
    assert meta["doc_props"]["title"] == "용산 업무시설 제안요청서"
    assert meta["doc_props"]["author"] == "E 자산운용"
    assert meta["url"] == f"/api/files/v1/files/{meta['id']}/content"
    assert meta["thumb_url"] == f"/api/files/v1/files/{meta['id']}/thumbnail"
    assert meta["parse_status"] in ("pending", "parsing", "done")
    assert len(meta["sha256"]) == 64 and meta["size"] > 1000
    r = await client.get(f"/v1/files/{meta['id']}")
    assert r.status_code == 200 and r.json()["id"] == meta["id"]


async def test_upload_pptx_slide_count_and_props(client, up):
    meta = await up(client, "제안지원요청서_용산 업무시설 재개발.pptx", S.pptx_deck())
    assert meta["kind"] == "pptx" and meta["pages"] == 3
    assert meta["doc_props"]["author"] == "김하늘"
    assert meta["meta"]["slide_size"]["aspect"] == "16:9"


async def test_upload_potx_keeps_template_mime(client, up):
    meta = await up(client, "B2B_master.potx", S.as_potx(S.pptx_deck()))
    assert meta["kind"] == "pptx"
    assert meta["mime"].endswith("presentationml.template")
    assert meta["meta"]["format"] == "potx"
    r = await client.get(f"/v1/files/{meta['id']}/parsed")
    assert r.status_code == 200 and r.json()["page_count"] == 3


async def test_heic_converted_to_jpeg(client, up):
    meta = await up(client, "IMG_0001.HEIC", S.heic(64, 48))
    assert meta["kind"] == "image" and meta["mime"] == "image/jpeg"
    assert meta["name"] == "IMG_0001.jpg"
    assert meta["meta"]["original_mime"] == "image/heic"
    assert meta["meta"]["original_name"] == "IMG_0001.HEIC"
    assert (meta["width"], meta["height"]) == (64, 48)
    r = await client.get(f"/v1/files/{meta['id']}/content")
    assert r.content[:3] == b"\xff\xd8\xff"
    assert r.headers["content-type"].startswith("image/jpeg")


async def test_exif_orientation_dims(client, up):
    meta = await up(client, "현장사진.jpg", S.jpeg_rotated(400, 200, 6))
    assert (meta["width"], meta["height"]) == (200, 400)  # 회전 반영
    assert meta["meta"]["exif"]["orientation"] == 6
    assert meta["meta"]["exif"]["make"] == "Samsung"
    assert meta["doc_props"]["created"].startswith("2025-11-04T10:30")
    th = await client.get(f"/v1/files/{meta['id']}/thumbnail", params={"w": 100, "format": "png"})
    from io import BytesIO

    from PIL import Image

    img = Image.open(BytesIO(th.content))
    assert img.size == (100, 200)  # 세로로 선 사진


async def test_detect_by_magic_not_extension(client, up):
    meta = await up(client, "잘못된확장자.txt", S.png(10, 10))
    assert meta["kind"] == "image" and meta["mime"] == "image/png"
    meta = await up(client, "noext", S.docx_minutes())
    assert meta["kind"] == "docx"


async def test_text_encoding_cp949(client, up):
    meta = await up(client, "고객 미팅 메모_11월 4일.txt", S.text_cp949())
    assert meta["kind"] == "text" and meta["meta"]["encoding"] == "cp949"
    r = await client.get(f"/v1/files/{meta['id']}/content")
    assert r.headers["content-type"] == "text/plain; charset=euc-kr"
    assert r.content == S.text_cp949()


async def test_nfd_name_normalized(client, up):
    import unicodedata

    nfd = unicodedata.normalize("NFD", "회의록.txt")
    meta = await up(client, nfd, "메모".encode())
    assert meta["name"] == "회의록.txt"
    meta = await up(client, "C:\\fakepath\\보고서.txt", b"x")
    assert meta["name"] == "보고서.txt"


async def test_content_disposition_korean(client, up):
    name = "제안요청서 최종(v2).pdf"
    meta = await up(client, name, S.pdf_pages(1))
    r = await client.get(f"/v1/files/{meta['id']}/content")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    cd = r.headers["content-disposition"]
    assert cd.startswith("inline;")
    assert f"filename*=UTF-8''{quote(name, safe='')}" in cd
    assert 'filename="' in cd and cd.split('filename="')[1].split('"')[0].isascii()
    assert r.headers["etag"] == f'"{meta["sha256"]}"'
    r = await client.get(f"/v1/files/{meta['id']}/content", params={"download": 1})
    assert r.headers["content-disposition"].startswith("attachment;")
    r = await client.get(f"/v1/files/{meta['id']}/content", headers={"Range": "bytes=0-3"})
    assert r.status_code == 206 and r.content == b"%PDF"


async def test_html_served_as_attachment(client, up):
    meta = await up(client, "page.html", b"<html><body><script>alert(1)</script><h1>t</h1></body></html>")
    r = await client.get(f"/v1/files/{meta['id']}/content")
    assert r.headers["content-disposition"].startswith("attachment;")
    assert "sandbox" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"


async def test_too_large_413(client_small):
    # 핸들러에서 거절(Content-Length 는 여유 범위 안)
    r = await client_small.post("/v1/files", files={"file": ("big.bin", b"\x00" * (1024 * 1024 + 10))})
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    # Content-Length 로 바로 거절(본문은 버림)
    r = await client_small.post("/v1/files", files={"file": ("bigger.bin", b"\x00" * (4 * 1024 * 1024))})
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    # 내부 저장도 같은 한도
    r = await client_small.post("/v1/files/bytes", json={"name": "big.bin", "data_b64": base64.b64encode(b"\x00" * (1024 * 1024 + 1)).decode()})
    assert r.status_code == 413


async def test_empty_file_rejected(client):
    r = await client.post("/v1/files", files={"file": ("empty.txt", b"")})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_ARGUMENT"


async def test_not_found(client):
    r = await client.get("/v1/files/file_01J00000000000000000000000")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    r = await client.get("/v1/files/not-an-id")
    assert r.status_code == 422


async def test_bytes_route_is_internal_and_inherits(client, up):
    from winmate_files.main import app

    spec = app.openapi()
    assert spec["paths"]["/v1/files/bytes"]["post"]["tags"] == ["internal"]
    parent = await up(client, "deck.pptx", S.pptx_deck(), confidential="true", project_id="prj_9")
    body = {"name": "render.png", "mime": "image/png", "data_b64": base64.b64encode(S.png(32, 32)).decode(),
            "source": "derived", "parent_id": parent["id"], "meta": {"slide": 2}}
    r = await client.post("/v1/files/bytes", json=body)
    assert r.status_code == 201, r.text
    child = r.json()
    assert child["source"] == "derived" and child["parent_id"] == parent["id"]
    assert child["confidential"] is True and child["project_id"] == "prj_9"  # 원본에서 이어받음
    assert child["meta"]["slide"] == 2 and child["meta"]["depth"] == 1
    assert child["parse_status"] == "none"  # 서비스 저장은 요청할 때 파싱
    r = await client.post("/v1/files/bytes", json={**body, "parent_id": "file_01J00000000000000000000000"})
    assert r.status_code == 404
    r = await client.post("/v1/files/bytes", json={"name": "x.json", "data_b64": base64.b64encode(b'{"a":1}').decode(),
                                                   "mime": "application/json", "source": "generated"})
    assert r.status_code == 201 and r.json()["mime"] == "application/json" and r.json()["kind"] == "text"


async def test_list_filters_and_cursor(client, up):
    a = await up(client, "a_report.pdf", S.pdf_pages(1), project_id="prj_1")
    b = await up(client, "b_photo.png", S.png(20, 20), project_id="prj_1")
    c = await up(client, "c_deck.pptx", S.pptx_deck(), project_id="prj_2")
    r = await client.get("/v1/files", params={"limit": 2})
    page1 = r.json()
    assert [i["id"] for i in page1["items"]] == [c["id"], b["id"]]  # 최신순
    assert page1["next_cursor"]
    r = await client.get("/v1/files", params={"limit": 2, "cursor": page1["next_cursor"]})
    assert [i["id"] for i in r.json()["items"]] == [a["id"]] and r.json()["next_cursor"] is None
    r = await client.get("/v1/files", params={"project_id": "prj_1"})
    assert {i["id"] for i in r.json()["items"]} == {a["id"], b["id"]}
    r = await client.get("/v1/files", params={"kind": "pdf,image"})
    assert {i["id"] for i in r.json()["items"]} == {a["id"], b["id"]}
    r = await client.get("/v1/files", params={"q": "DECK"})
    assert [i["id"] for i in r.json()["items"]] == [c["id"]]
    # 추출 이미지(자식)는 기본 목록에서 빠지고 parent_id 로 본다
    await client.get(f"/v1/files/{c['id']}/parsed")
    r = await client.get("/v1/files")
    assert all(i["parent_id"] is None for i in r.json()["items"])
    r = await client.get("/v1/files", params={"parent_id": c["id"]})
    kids = r.json()["items"]
    assert kids and all(i["parent_id"] == c["id"] and i["source"] == "derived" for i in kids)
    r = await client.get("/v1/files", params={"source": "derived"})
    assert {i["id"] for i in r.json()["items"]} == {k["id"] for k in kids}


async def test_list_owner_and_confidential_visibility(env, up):
    from winmate_common import testing
    from winmate_files.main import app

    async with testing.api_client(app, user_id="u_a", user_name="에이") as ca:
        mine = await up(ca, "mine.txt", b"a", project_id="prj_x")
        secret = await up(ca, "secret.txt", b"b", confidential="true", project_id="prj_x")
    async with testing.api_client(app, user_id="u_b", user_name="비") as cb:
        r = await cb.get("/v1/files")
        assert r.json()["items"] == []
        r = await cb.get("/v1/files", params={"owner": "all"})
        assert [i["id"] for i in r.json()["items"]] == [mine["id"]]  # 남의 기밀은 숨김
        r = await cb.get("/v1/files", params={"owner": "u_a", "project_id": "prj_x"})
        assert {i["id"] for i in r.json()["items"]} == {mine["id"], secret["id"]}
        # 남의 파일은 바꾸거나 지울 수 없다
        r = await cb.patch(f"/v1/files/{mine['id']}", json={"name": "x.txt"})
        assert r.status_code == 403
        r = await cb.delete(f"/v1/files/{mine['id']}")
        assert r.status_code == 403
    from winmate_files.service import service

    await service().wait_idle()


async def test_patch(client, up):
    meta = await up(client, "deck.pptx", S.pptx_deck(), project_id="prj_1")
    await client.get(f"/v1/files/{meta['id']}/parsed")
    r = await client.patch(f"/v1/files/{meta['id']}", json={"name": "새 이름.pptx", "confidential": True,
                                                            "meta": {"note": "검토", "format": None}, "folder": "B2B 제안서/A 커피/"})
    assert r.status_code == 200
    p = r.json()
    assert p["name"] == "새 이름.pptx" and p["confidential"] is True and p["meta"]["note"] == "검토"
    assert p["folder"] == "B2B 제안서/A 커피" and p["project_id"] == "prj_1"
    # 자식(추출 이미지)도 기밀을 따라간다
    kids = (await client.get("/v1/files", params={"parent_id": meta["id"]})).json()["items"]
    assert kids and all(k["confidential"] for k in kids)
    r = await client.patch(f"/v1/files/{meta['id']}", json={"project_id": None})
    assert r.json()["project_id"] is None and r.json()["name"] == "새 이름.pptx"


async def test_soft_delete_keeps_shared_blob(client, up):
    from winmate_files.service import service

    data = S.pdf_pages(2)
    a = await up(client, "a.pdf", data)
    b = await up(client, "b.pdf", data)
    assert a["sha256"] == b["sha256"]
    blob = service().blobs.path(a["sha256"])
    assert blob.is_file()
    r = await client.delete(f"/v1/files/{a['id']}")
    assert r.status_code == 204
    assert (await client.get(f"/v1/files/{a['id']}")).status_code == 404
    assert (await client.get(f"/v1/files/{a['id']}/content")).status_code == 404
    assert blob.is_file()  # b 가 아직 쓴다
    r = await client.get(f"/v1/files/{b['id']}/content")
    assert r.status_code == 200 and r.content == data
    await client.delete(f"/v1/files/{b['id']}")
    assert not blob.exists()
    # 레코드는 소프트 삭제로 남아 있다
    assert service().get(a["id"], include_deleted=True)["name"] == "a.pdf"


async def test_late_status_update_does_not_resurrect(client, up):
    """백그라운드 상태 갱신이 레코드를 읽은 뒤 지우기가 끼어들어도 되살아나지 않는다."""
    from winmate_common.context import User
    from winmate_files.service import service

    svc = service()
    meta = await up(client, "race.pdf", S.pdf_pages(1))
    await svc.wait_idle()
    rec = svc.get(meta["id"])
    user = User(id="u_test", name="테스터")
    real_get = svc.store.get
    state = {"deleted": False}

    def get_then_delete(coll, fid, **kw):  # noqa: ANN001
        cur = real_get(coll, fid, **kw)
        if not state["deleted"] and cur is not None and not cur.get("deleted"):
            state["deleted"] = True
            svc.delete(rec, user)  # 읽은 직후 지우기가 끼어든다
        return cur

    svc.store.get = get_then_delete  # type: ignore[method-assign]
    try:
        svc._set_status(meta["id"], "done", None)  # 늦게 도착한 상태 갱신
    finally:
        svc.store.get = real_get  # type: ignore[method-assign]
    assert state["deleted"]
    assert (await client.get(f"/v1/files/{meta['id']}")).status_code == 404
    assert meta["id"] not in [i["id"] for i in (await client.get("/v1/files")).json()["items"]]


async def test_copy_to_folder(client, up):
    meta = await up(client, "제안서_v3.pptx", S.pptx_deck(), project_id="prj_1")
    r = await client.post(f"/v1/files/{meta['id']}/copy", json={"folder": "B2B 제안서/A 커피 프랜차이즈", "project_id": "prj_2"})
    assert r.status_code == 201
    cp = r.json()
    assert cp["id"] != meta["id"] and cp["sha256"] == meta["sha256"]
    assert cp["folder"] == "B2B 제안서/A 커피 프랜차이즈" and cp["project_id"] == "prj_2"
    assert cp["meta"]["copied_from"] == meta["id"]
    r = await client.get("/v1/files", params={"folder": "B2B 제안서/A 커피 프랜차이즈"})
    assert [i["id"] for i in r.json()["items"]] == [cp["id"]]


async def test_platform_helpers_against_contract(client, up):
    """winmate_common.platform 도우미(계약 검증 strict)로 저장 · 조회 · 파싱."""
    from winmate_common import platform, testing
    from winmate_files.main import app

    with testing.inprocess({"files": app}):
        saved = await platform.save_file("export.pdf", S.pdf_rfp(), "application/pdf", source="export",
                                         confidential=True, project_id="prj_1", meta={"job": "job_1"})
        assert saved["source"] == "export" and saved["confidential"] is True
        meta = await platform.file_meta(saved["id"])
        assert meta["pages"] == 2
        data, ctype = await platform.file_bytes(saved["id"])
        assert data.startswith(b"%PDF") and ctype.startswith("application/pdf")
        doc = await platform.parsed_document(saved["id"])
        assert doc["file_id"] == saved["id"] and doc["page_count"] == 2
        assert doc["pages"][0]["image_file_ids"]
