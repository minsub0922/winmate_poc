"""썸네일 · 쪽 그림 — LibreOffice 없을 때(기본 픽스처)와 있을 때(env_lo, 없으면 건너뜀)."""
from __future__ import annotations

from io import BytesIO

import files_samples as S
from PIL import Image


def _img(content: bytes) -> Image.Image:
    return Image.open(BytesIO(content))


async def test_image_thumbnail_webp(client, up):
    meta = await up(client, "big.png", S.png(1200, 800))
    r = await client.get(f"/v1/files/{meta['id']}/thumbnail")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    assert _img(r.content).size == (320, 213)
    r = await client.get(f"/v1/files/{meta['id']}/thumbnail", params={"w": 64, "format": "png"})
    assert r.headers["content-type"] == "image/png" and _img(r.content).size == (64, 43)
    # 작은 그림은 키우지 않는다
    small = await up(client, "small.png", S.png(40, 20))
    r = await client.get(f"/v1/files/{small['id']}/thumbnail")
    assert _img(r.content).size == (40, 20)


async def test_thumbnail_cached_on_disk(client, up):
    from winmate_files.service import service

    meta = await up(client, "rfp.pdf", S.pdf_rfp())
    r1 = await client.get(f"/v1/files/{meta['id']}/thumbnail", params={"w": 200})
    assert r1.status_code == 200 and r1.headers["content-type"] == "image/webp"
    im = _img(r1.content)
    assert im.size[0] == 200 and im.size[1] > 200  # A4 세로
    cached = list((service().cache.root / "thumbs").rglob(f"{meta['sha256']}*_w200.webp"))
    assert len(cached) == 1
    r2 = await client.get(f"/v1/files/{meta['id']}/thumbnail", params={"w": 200})
    assert r2.content == r1.content


async def test_pdf_page_images(client, up):
    meta = await up(client, "rfp.pdf", S.pdf_rfp())
    r = await client.get(f"/v1/files/{meta['id']}/pages/2/image", params={"w": 600})
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    im = _img(r.content)
    assert im.size[0] == 600 and abs(im.size[1] / im.size[0] - 841.89 / 595.28) < 0.01
    r = await client.get(f"/v1/files/{meta['id']}/pages/3/image")
    assert r.status_code == 404 and r.json()["error"]["code"] == "PAGE_NOT_FOUND"
    assert r.json()["error"]["details"]["page_count"] == 2
    r = await client.get(f"/v1/files/{meta['id']}/pages/1/thumbnail")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp" and _img(r.content).size[0] == 320
    r = await client.get(f"/v1/files/{meta['id']}/pages/1/image", params={"format": "jpeg", "w": 300})
    assert r.headers["content-type"] == "image/jpeg"


async def test_image_page_is_the_image(client, up):
    meta = await up(client, "site.jpg", S.jpeg_rotated(400, 200, 6))
    r = await client.get(f"/v1/files/{meta['id']}/pages/1/image")
    assert r.status_code == 200 and _img(r.content).size == (200, 400)  # 회전 반영, 키우지 않음
    r = await client.get(f"/v1/files/{meta['id']}/pages/2/image")
    assert r.status_code == 404


async def test_pptx_without_libreoffice(client, up):
    meta = await up(client, "deck.pptx", S.pptx_deck())
    # 썸네일: 첫 슬라이드 제목을 그린 자리표시 카드(16:9)
    r = await client.get(f"/v1/files/{meta['id']}/thumbnail", params={"w": 320})
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    assert _img(r.content).size == (320, 180)
    # 쪽 그림은 렌더러가 없으면 501
    r = await client.get(f"/v1/files/{meta['id']}/pages/2/image")
    assert r.status_code == 501 and r.json()["error"]["code"] == "PREVIEW_UNAVAILABLE"
    # 쪽 썸네일은 그 슬라이드 카드로 대신
    r = await client.get(f"/v1/files/{meta['id']}/pages/2/thumbnail")
    assert r.status_code == 200 and _img(r.content).size == (320, 180)
    r = await client.get(f"/v1/files/{meta['id']}/pages/9/thumbnail")
    assert r.status_code == 404


async def test_icons_for_other_kinds(client, up):
    meta = await up(client, "메일.eml", S.eml())
    r = await client.get(f"/v1/files/{meta['id']}/thumbnail", params={"w": 128})
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert _img(r.content).size == (128, 160)
    r = await client.get(f"/v1/files/{meta['id']}/pages/1/image")
    assert r.status_code == 501
    meta = await up(client, "spec.xlsx", S.xlsx_spec())
    r = await client.get(f"/v1/files/{meta['id']}/thumbnail")
    assert r.headers["content-type"] == "image/png"  # LibreOffice 없으면 형식 아이콘
    meta = await up(client, "logo.svg", b'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40"><text x="0" y="20">Samsung</text></svg>')
    assert meta["kind"] == "svg" and (meta["width"], meta["height"]) == (120, 40)
    r = await client.get(f"/v1/files/{meta['id']}/thumbnail")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    r = await client.get(f"/v1/files/{meta['id']}/content")
    assert "sandbox" in r.headers["content-security-policy"] and r.headers["content-disposition"].startswith("inline")


# ── LibreOffice 가 있을 때만 ─────────────────────────────────────

async def test_pptx_pages_with_libreoffice(client_lo, up):
    meta = await up(client_lo, "deck.pptx", S.pptx_deck())
    r = await client_lo.get(f"/v1/files/{meta['id']}/pages/3/image", params={"w": 640})
    assert r.status_code == 200, r.text  # 숨긴 슬라이드도 쪽 번호가 맞는다
    w, h = _img(r.content).size
    assert w == 640 and abs(h - 360) <= 1
    r = await client_lo.get(f"/v1/files/{meta['id']}/thumbnail")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    w, h = _img(r.content).size
    assert w == 320 and abs(h - 180) <= 1
    r = await client_lo.get(f"/v1/files/{meta['id']}/pages/4/image")
    assert r.status_code == 404


async def test_docx_thumbnail_with_libreoffice(client_lo, up):
    meta = await up(client_lo, "회의록.docx", S.docx_minutes())
    r = await client_lo.get(f"/v1/files/{meta['id']}/thumbnail", params={"w": 200})
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    w, h = _img(r.content).size
    assert w == 200 and h > 250  # 세로 쪽
    r = await client_lo.get(f"/v1/files/{meta['id']}/pages/2/image", params={"w": 300})
    assert r.status_code == 200


async def test_legacy_doc_parsed_via_libreoffice(client_lo, up):
    from winmate_files.service import service

    svc = service()
    doc_bytes = svc.soffice.convert(S.docx_minutes(), "minutes.docx", "doc")
    assert doc_bytes and doc_bytes[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    meta = await up(client_lo, "옛 회의록.doc", doc_bytes)
    assert meta["kind"] == "other" and meta["meta"]["format"] == "doc"
    r = await client_lo.get(f"/v1/files/{meta['id']}/parsed")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["meta"]["parsed_as"] == "docx" and "converted_from:doc" in doc["warnings"]
    assert "공간컨텐츠실장" in doc["text"]
