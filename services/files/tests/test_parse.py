"""파싱 — PDF · PPTX · DOCX · XLSX · 메일(EML · MSG) · 텍스트 · 이미지 · HWPX, 자식 파일, 캐시, 상태."""
from __future__ import annotations

import files_samples as S

from winmate_files.models import ParsedDocument


async def _parsed(client, file_id: str) -> dict:
    r = await client.get(f"/v1/files/{file_id}/parsed")
    assert r.status_code == 200, r.text
    doc = r.json()
    ParsedDocument.model_validate(doc)  # 계약 모양
    return doc


async def test_pdf_korean_text_table_headings(client, up):
    meta = await up(client, "rfp.pdf", S.pdf_rfp(), confidential="true", project_id="prj_1")
    doc = await _parsed(client, meta["id"])
    assert doc["kind"] == "pdf" and doc["page_count"] == 2
    assert doc["title"] == "용산 업무시설 제안요청서"
    p1, p2 = doc["pages"]
    assert "고객사는 E 자산운용입니다" in p1["text"]
    assert p1["tables"] == [[["구분", "요구사항", "비고"], ["디스플레이", "55인치 이상", "필수"], ["솔루션", "MagicINFO", "선택"]]]
    types = [b["type"] for b in p1["blocks"]]
    assert types[0] == "title" and "table" in types and "image" in types
    title = p1["blocks"][0]
    assert title["font_size"] == 20.0 and title["level"] == 1
    assert all(0.0 <= v <= 1.0 for v in title["bbox"]) and title["bbox"][1] < 0.2
    assert p1["title"] == "용산 업무시설 제안요청서"
    assert p2["title"] == "2. 요구사항"
    assert any(b["type"] == "heading" and b["text"] == "2. 요구사항" for b in p2["blocks"])
    assert any(b["type"] == "list" for b in p2["blocks"])
    assert "용산 업무시설 제안요청서" in doc["text"] and "에너지 절감" in doc["text"]
    assert doc["meta"]["author"] == "E 자산운용"
    assert [o["title"] for o in doc["meta"]["outline"]] == ["개요", "요구사항"]
    # 그림 추출 → 자식 파일(기밀 · 프로젝트 이어받음)
    assert len(p1["image_file_ids"]) == 1
    img_id = p1["image_file_ids"][0]
    assert p1["images"][0]["file_id"] == img_id and len(p1["images"][0]["bbox"]) == 4
    child = (await client.get(f"/v1/files/{img_id}")).json()
    assert child["parent_id"] == meta["id"] and child["source"] == "derived" and child["kind"] == "image"
    assert child["confidential"] is True and child["project_id"] == "prj_1" and child["meta"]["pages"] == [1]
    # 파싱이 끝나면 메타 상태도 done
    m = (await client.get(f"/v1/files/{meta['id']}")).json()
    assert m["parse_status"] == "done" and m["pages"] == 2


async def test_pdf_scanned_page_warning(client, up):
    meta = await up(client, "scan.pdf", S.pdf_scanned())
    doc = await _parsed(client, meta["id"])
    assert "scanned_page:1" in doc["warnings"]
    assert "scanned_page:2" not in doc["warnings"]
    assert doc["pages"][0]["blocks"][0]["type"] == "image"
    assert doc["pages"][0]["image_file_ids"] == []  # 스캔 쪽 전체 그림은 자식으로 뽑지 않는다
    assert "text layer" in doc["pages"][1]["text"]


async def test_pdf_encrypted_fails_cleanly(client, up):
    meta = await up(client, "secret.pdf", S.pdf_encrypted())
    r = await client.get(f"/v1/files/{meta['id']}/parsed")
    assert r.status_code == 422 and r.json()["error"]["code"] == "FILE_ENCRYPTED"
    m = (await client.get(f"/v1/files/{meta['id']}")).json()
    assert m["parse_status"] == "failed" and m["parse_error"]["code"] == "FILE_ENCRYPTED"
    assert m["meta"]["encrypted"] is True


async def test_corrupt_pdf(client, up):
    meta = await up(client, "broken.pdf", b"%PDF-1.4\n garbage garbage")
    r = await client.get(f"/v1/files/{meta['id']}/parsed")
    assert r.status_code == 422 and r.json()["error"]["code"] == "PARSE_FAILED"


async def test_pptx_slides(client, up):
    meta = await up(client, "deck.pptx", S.pptx_deck(), confidential="true")
    doc = await _parsed(client, meta["id"])
    assert doc["kind"] == "pptx" and doc["page_count"] == 3
    assert doc["title"] == "용산 AI Ready 오피스 제안"
    assert doc["meta"]["slide_size"]["aspect"] == "16:9" and doc["meta"]["author"] == "김하늘"
    s1, s2, s3 = doc["pages"]
    assert s1["title"] == "용산 업무시설 AI Ready 오피스" and s1["layout"] == "Title Slide"
    assert s1["blocks"][0]["type"] == "title"
    assert any(b["type"] == "heading" and "제안지원요청서" in b["text"] for b in s1["blocks"])
    assert s2["title"] == "요구사항 정리" and s2["layout"] == "Title Only"
    assert s2["notes"] == "발표자 노트: 성수 오피스 대비 최초 AI Ready 강조"
    assert s2["tables"] == [[["구분", "요구", "비고"], ["디스플레이", "55인치", "필수"], ["솔루션", "MagicINFO", "선택"]]]
    body = next(b for b in s2["blocks"] if "에너지 절감" in b["text"])
    assert body["font_size"] == 18.0
    grouped = next(b for b in s2["blocks"] if b["text"] == "그룹 안 글")
    assert abs(grouped["bbox"][0] - 0.6) < 0.01  # 그룹 좌표 변환
    assert "사용자를 인식하고" in s2["text"] and "발표자 노트" not in s2["text"]
    # 차트 데이터 → 표
    assert ["2024", "150"] in s3["tables"][0]
    assert s3["hidden"] is True
    # 같은 그림은 자식 하나(중복 제거), 두 슬라이드가 같은 id 를 가리킨다
    assert len(s2["image_file_ids"]) == 1 and s2["image_file_ids"] == s3["image_file_ids"]
    img = next(b for b in s2["blocks"] if b["type"] == "image")
    assert img["file_id"] == s2["image_file_ids"][0] and img["bbox"][1] > 0.6
    kids = (await client.get("/v1/files", params={"parent_id": meta["id"]})).json()["items"]
    assert len(kids) == 1 and kids[0]["confidential"] is True and kids[0]["meta"]["pages"] == [2, 3]


async def test_docx_structure(client, up):
    meta = await up(client, "회의록.docx", S.docx_minutes())
    doc = await _parsed(client, meta["id"])
    assert doc["kind"] == "docx" and doc["page_count"] == 2  # 명시적 쪽 나눔
    assert doc["title"] == "고객 미팅 회의록"
    p1, p2 = doc["pages"]
    kinds = [(b["type"], b.get("level")) for b in p1["blocks"]]
    assert kinds[0] == ("title", 1) and ("heading", 1) in kinds
    assert [b["text"] for b in p1["blocks"] if b["type"] == "list"] == ["대표이사: AI Ready 오피스", "공간컨텐츠실장: 업무환경 플랫폼"]
    assert p1["tables"] == [[["구분", "내용", "담당"], ["디스플레이", "55인치 이상", "개발사업팀장"], ["일정", "12월 제출", ""]]]
    assert len(p1["image_file_ids"]) == 1
    assert p2["blocks"][0] == {"type": "heading", "text": "2. 요구사항", "level": 2}
    assert p2["title"] == "2. 요구사항"


async def test_xlsx_sheets(client, up):
    meta = await up(client, "고객사_스펙양식.xlsx", S.xlsx_spec())
    assert meta["pages"] == 2 and meta["meta"]["sheet_names"] == ["스펙", "가격"]
    doc = await _parsed(client, meta["id"])
    assert doc["kind"] == "xlsx" and doc["page_count"] == 2
    spec, price = doc["sheets"]
    assert spec["name"] == "스펙" and spec["merged"] == ["A1:C1"] and spec["dims"] == "A1:C5"
    assert spec["rows"][0] == ["고객사 스펙 양식"]
    assert spec["rows"][2] == ["밝기(nit)", 500, 350]
    assert spec["rows"][3] == ["무게(kg)", 17.5, 14.1]
    assert spec["rows"][4] == ["출시일", "2024-03-01"]
    assert price["hidden"] is True and price["merged"] == ["A3:B4"] and price["rows"][1] == ["QM55C", 1234567]
    assert doc["pages"][0]["title"] == "스펙" and "밝기(nit)\t500\t350" in doc["pages"][0]["text"]
    assert doc["pages"][1]["hidden"] is True


async def test_eml_attachments_and_depth_limit(client, up):
    inner = S.eml()
    meta = await up(client, "고객 메일.eml", S.eml(attach_eml=inner), confidential="true")
    assert meta["kind"] == "email" and meta["doc_props"]["title"] == "[E 자산운용] 용산 오피스 제안 관련 자료"
    doc = await _parsed(client, meta["id"])
    em = doc["email"]
    assert em["subject"] == "[E 자산운용] 용산 오피스 제안 관련 자료"
    assert em["from"] == "홍길동 <hong@e-am.co.kr>"
    assert em["to"] == ["최민섭 <minseop@samsung.com>", "김하늘 <sky@samsung.com>"]
    assert em["cc"] == ["개발사업팀장 <dev@e-am.co.kr>"]
    assert em["date"] == "2025-11-04T01:30:00Z"
    assert "에너지 사용량 자료를 첨부합니다" in em["body"]
    names = {a["name"]: a for a in em["attachment_list"]}
    assert names["logo.png"]["inline"] is True
    assert len(em["attachments"]) == 2  # 본문 안 그림 제외: PDF · 원본메일.eml
    att = {(await client.get(f"/v1/files/{fid}")).json()["name"]: fid for fid in em["attachments"]}
    assert set(att) == {"성수오피스_에너지사용량_2025.pdf", "원본메일.eml"}
    pdf_child = (await client.get(f"/v1/files/{att['성수오피스_에너지사용량_2025.pdf']}")).json()
    assert pdf_child["kind"] == "pdf" and pdf_child["confidential"] is True and pdf_child["parent_id"] == meta["id"]
    assert pdf_child["parse_status"] == "none"  # 자식은 요청할 때 읽는다
    child_doc = await _parsed(client, pdf_child["id"])
    assert child_doc["page_count"] == 1
    # 첨부된 메일(깊이 1)은 읽되 그 첨부는 다시 뽑지 않는다
    nested = await _parsed(client, att["원본메일.eml"])
    assert nested["email"]["subject"] == "[E 자산운용] 용산 오피스 제안 관련 자료"
    assert nested["email"]["attachments"] == []
    assert len(nested["email"]["attachment_list"]) == 2
    assert any(w.startswith("children_skipped:depth") for w in nested["warnings"])
    grand = (await client.get("/v1/files", params={"parent_id": att["원본메일.eml"]})).json()["items"]
    assert grand == []
    assert "보낸 사람: 홍길동" in doc["pages"][0]["text"] and doc["pages"][0]["blocks"][0]["type"] == "title"


async def test_msg_outlook(client, up):
    meta = await up(client, "견적 회신.msg", S.msg())
    assert meta["kind"] == "email" and meta["mime"] == "application/vnd.ms-outlook"
    assert meta["doc_props"]["author"] == "홍길동 <hong@e-am.co.kr>"
    doc = await _parsed(client, meta["id"])
    em = doc["email"]
    assert em["subject"] == "[E 자산운용] 견적 요청 회신"
    assert em["to"] == ["최민섭 <minseop@samsung.com>"] and em["cc"] == ["김하늘 <sky@samsung.com>"]
    assert em["date"] == "2025-11-05T09:00:00Z"
    assert em["body"] == "견적 관련 자료 보내드립니다.\n\n대표이사 의견 포함."
    kids = {(await client.get(f"/v1/files/{f}")).json()["name"]: f for f in em["attachments"]}
    assert set(kids) == {"견적.txt", "현장사진.png"}
    r = await client.get(f"/v1/files/{kids['견적.txt']}/content")
    assert r.text == "QM55C 1대 견적\n"


async def test_text_and_markdown(client, up):
    meta = await up(client, "메모.txt", S.text_cp949())
    doc = await _parsed(client, meta["id"])
    assert doc["meta"]["encoding"] == "cp949" and doc["title"] == "고객 미팅 메모"
    blocks = doc["pages"][0]["blocks"]
    assert blocks[1] == {"type": "body", "text": "제작자 의견: 설계 단계 스펙인이 목표.", "line": 3}
    assert blocks[2]["type"] == "list" and blocks[2]["line"] == 5
    md = "# 제목\n\n## 배경\n\n- 하나\n- 둘\n\n| 모델 | 밝기 |\n|---|---|\n| QM55C | 500 |\n".encode()
    meta = await up(client, "notes.md", md)
    doc = await _parsed(client, meta["id"])
    b = doc["pages"][0]["blocks"]
    assert b[0] == {"type": "title", "text": "제목", "level": 1, "line": 1}
    assert b[1]["type"] == "heading" and b[1]["level"] == 2
    assert doc["pages"][0]["tables"] == [[["모델", "밝기"], ["QM55C", "500"]]]
    meta = await up(client, "list.csv", "모델,밝기\nQM55C,500\nQB55C,350\n".encode("utf-8-sig"))
    doc = await _parsed(client, meta["id"])
    assert doc["sheets"][0]["rows"] == [["모델", "밝기"], ["QM55C", "500"], ["QB55C", "350"]]


async def test_image_and_hwpx(client, up):
    meta = await up(client, "photo.png", S.png(120, 80))
    doc = await _parsed(client, meta["id"])
    assert doc["kind"] == "image" and doc["meta"]["width"] == 120
    assert doc["pages"][0]["blocks"] == [{"type": "image", "text": "", "bbox": [0.0, 0.0, 1.0, 1.0]}]
    meta = await up(client, "제안요청서.hwpx", S.hwpx())
    assert meta["kind"] == "other" and meta["meta"]["format"] == "hwpx"
    doc = await _parsed(client, meta["id"])
    assert "사업명: 용산 AI Ready 오피스" in doc["text"]


async def test_zip_bomb_guard(client, up, monkeypatch):
    from winmate_files import parsers

    monkeypatch.setattr(parsers, "MAX_UNZIPPED", 10_000)
    meta = await up(client, "huge.pptx", S.pptx_deck())
    r = await client.get(f"/v1/files/{meta['id']}/parsed")
    assert r.status_code == 422 and r.json()["error"]["code"] == "FILE_TOO_COMPLEX"


async def test_unsupported(client, up):
    meta = await up(client, "data.bin", bytes(range(256)) * 4)
    assert meta["kind"] == "other" and meta["parse_status"] == "unsupported"
    r = await client.get(f"/v1/files/{meta['id']}/parsed")
    assert r.status_code == 415 and r.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    r = await client.post(f"/v1/files/{meta['id']}/parse")
    assert r.status_code == 202 and r.json()["parse_status"] == "unsupported"


async def test_parse_cache_shared_by_content(client, up, monkeypatch):
    from winmate_files import service as svc_mod

    calls = []
    real = svc_mod.parse_kind

    def counting(kind, data, ctx):  # noqa: ANN001
        calls.append(kind)
        return real(kind, data, ctx)

    monkeypatch.setattr(svc_mod, "parse_kind", counting)
    data = S.pptx_deck()
    a = await up(client, "a.pptx", data)
    b = await up(client, "b.pptx", data)
    da = await _parsed(client, a["id"])
    db = await _parsed(client, b["id"])
    assert calls == ["pptx"]  # 내용이 같으면 한 번만 읽는다
    assert da["file_id"] == a["id"] and db["file_id"] == b["id"]
    ia, ib = da["pages"][1]["image_file_ids"][0], db["pages"][1]["image_file_ids"][0]
    assert ia != ib  # 자식 파일은 레코드마다
    assert (await client.get(f"/v1/files/{ib}")).json()["parent_id"] == b["id"]
    # 다시 읽어도 자식이 늘지 않는다
    r = await client.post(f"/v1/files/{a['id']}/parse", params={"force": "true"})
    assert r.status_code == 202
    from winmate_files.service import service

    await service().wait_idle()
    assert calls == ["pptx", "pptx"]
    kids = (await client.get("/v1/files", params={"parent_id": a["id"]})).json()["items"]
    assert [k["id"] for k in kids] == [ia]


async def test_parse_endpoint_and_status(client, up):
    import base64

    r = await client.post("/v1/files/bytes", json={"name": "gen.pdf", "data_b64": base64.b64encode(S.pdf_pages(3)).decode(),
                                                   "source": "generated"})
    meta = r.json()
    assert meta["parse_status"] == "none"
    r = await client.post(f"/v1/files/{meta['id']}/parse")
    assert r.status_code == 202 and r.json()["parse_status"] == "parsing" and r.json()["parser_version"]
    from winmate_files.service import service

    await service().wait_idle()
    m = (await client.get(f"/v1/files/{meta['id']}")).json()
    assert m["parse_status"] == "done" and m["pages"] == 3
    r = await client.post(f"/v1/files/{meta['id']}/parse")
    assert r.json()["parse_status"] == "done"
