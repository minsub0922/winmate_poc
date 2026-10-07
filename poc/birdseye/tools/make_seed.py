#!/usr/bin/env python3
"""winmate-kb 추출본(seed/kb_extract_*.json) → seed/products.json.

치수·전력·무게·밝기 같은 사실값은 KB 원문(spec_value.value_raw)에서만 가져온다.
이 파일이 정하는 것은 "어떻게 쓸지"(약칭, 배치 전략용 분류, 설치 방식, 3D 화면 콘텐츠)뿐이다.

    python tools/make_seed.py                       # 기본 추출본으로 다시 만들기
    python tools/make_seed.py --kb ../../winmate-kb/kb   # KB 에서 직접 다시 뽑기(같은 모델 목록)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from birdseye.catalog import parse_spec_fields  # noqa: E402

# 약칭은 도면 라벨용 PoC 표기(사내 통용 약칭과 다를 수 있음). 분류·설치 방식은 배치 전략 선택용.
CURATION = {
    "LH55OMBEBGBXKR": dict(short="OM55B", category="window_signage", mounts=["ceiling_hang", "floor_stand"], content="brand"),
    "LH46OMBEBGBXKR": dict(short="OM46B", category="window_signage", mounts=["ceiling_hang", "floor_stand"], content="brand"),
    "LH55OMNDSGBXKR": dict(short="OM55D", category="window_signage", mounts=["ceiling_hang", "floor_stand"], content="menu",
                            double_sided=True),
    "LH43QMCEBGCXKR": dict(short="QM43C", category="signage", mounts=["pillar_wrap", "wall", "floor_stand", "ceiling_hang"], content="brand"),
    "LH55QMCEBGCXKR": dict(short="QM55C", category="signage", mounts=["wall", "pillar_wrap", "floor_stand", "ceiling_hang"], content="info"),
    "LH75QMCEBGCXKR": dict(short="QM75C", category="signage", mounts=["wall", "floor_stand"], content="brand"),
    "LH98QMCEBGCXKR": dict(short="QM98C", category="signage_large", mounts=["wall", "floor_stand"], content="brand"),
    "LH015IACCHS/KR": dict(short="IAC 130\"", category="led_allinone", mounts=["wall", "floor_stand"], content="brand", bezel=0),
    "LH65WMFWBGCXKR": dict(short="Flip 65\"", category="flip", mounts=["stand", "wall"], content="board"),
    "LH75WMFWLGCXKR": dict(short="Flip 75\"", category="flip", mounts=["stand", "wall"], content="board"),
    "LH55VMCEBGBXKR": dict(short="VM55C-E", category="videowall", mounts=["wall"], content="dashboard"),
    "LH55VHCRBGBXKR": dict(short="VH55C-R", category="videowall", mounts=["wall"], content="dashboard"),
    "LH55OHAOSGBXKR": dict(short="OH55A", category="outdoor_signage", mounts=["floor_stand", "wall"], content="brand"),
    "LH85SMHPBGCXKR": dict(short="SM85H", category="spatial", mounts=["floor_lean", "wall"], content="art"),
    "LH32SMHPBGCXKR": dict(short="SM32H", category="spatial", mounts=["floor_lean", "wall"], content="art"),
    "LH55BEHHLBFXKR": dict(short="BEH 55\"", category="signage", mounts=["wall", "floor_stand"], content="info"),
    "LH43BEHHLBFXKR": dict(short="BEH 43\"", category="signage", mounts=["wall", "floor_stand"], content="info"),
    "LH32EMDIAGBXKR": dict(short="EM32DX", category="epaper", mounts=["wall"], content="epaper"),
    "LH13EMDIBGBXKR": dict(short="EM13DX", category="epaper", mounts=["wall"], content="epaper"),
    "LH015IEACLS/KR": dict(short="IEA 1.5", category="led_cabinet", mounts=["wall"], content="brand", bezel=0),
    "AC060CN4FBH1": dict(short="무풍4Way 6.0", category="hvac_cassette", mounts=["ceiling"], content=None),
    "AC060CN6PBH1": dict(short="360 6.0", category="hvac_cassette", mounts=["ceiling"], content=None),
}

# 같은 PDP 가 여러 크기를 묶어 보여 줄 때 이름에 크기를 붙인다.
SIZE_NAMES = {"cm": "{v} cm"}


def build(extract: dict) -> list[dict]:
    out = []
    for it in extract["items"]:
        if it.get("missing"):
            continue
        cur = CURATION.get(it["code"])
        if not cur:
            continue
        fields = parse_spec_fields(it["specs"])
        if not fields.get("dims"):
            print("치수 없음 — 건너뜀:", it["code"], file=sys.stderr)
            continue
        w, h, d = fields["dims"]["w"], fields["dims"]["h"], fields["dims"]["d"]
        if cur["category"] == "hvac_cassette":
            # 천장 카세트: 바닥 평면에서 보이는 것은 판넬. 판넬 W×D, 보이는 높이는 판넬 두께.
            pan = fields.get("panel_dims") or fields["dims"]
            w, d, h = pan["w"], pan["d"], pan["h"]
        size = it.get("option") or ""
        name = it["family_name"].strip()
        if size and size not in name:
            name = f"{name} {size}"
        prod = {
            "code": it["code"],
            "short": cur["short"],
            "name": re.sub(r"\s+", " ", name),
            "family": it["family_name"].strip(),
            "category": cur["category"],
            "mounts": cur["mounts"],
            "default_mount": cur["mounts"][0],
            "w": w, "h": h, "d": d,
            "kb": {"model_id": it["model_id"], "family_id": it["family_id"], "category_id": it["category_id"],
                   "subcategory": it["subcategory"]},
            "source": {
                "url": it.get("spec_source_url") or it.get("detail_url"),
                "page": it.get("detail_url"),
                "extracted_from": "winmate-kb (samsung.com/sec/business 수집 2026-10-04)",
                "fields": fields["raw"],
            },
            "content": cur.get("content"),
            "double_sided": bool(cur.get("double_sided")),
            "assumed": {},
        }
        for k in ("power_w", "weight_kg", "brightness_nit", "pixel_pitch_mm", "resolution", "diag_cm", "view_angle_deg",
                  "operation", "bezel_mm", "cooling_kw", "heating_kw", "release", "body_dims"):
            if fields.get(k) is not None:
                prod[k] = fields[k]
        if "bezel" in cur:
            prod["bezel_mm"] = cur["bezel"]
        if cur["category"] == "flip":
            prod["assumed"]["stand"] = "이동식 스탠드 외형은 KB에 없음 — 바닥 점유 폭 = 제품 폭, 깊이 700 mm, 화면 하단 800 mm로 가정"
        if cur["category"] == "spatial":
            prod["assumed"]["lean"] = "기대어 세우는 설치 — 바닥 점유 깊이 450 mm로 가정"
        if cur["category"] == "led_allinone":
            prod["assumed"]["stand"] = "벽부형 기준. 스탠드형 바닥 점유 깊이 600 mm로 가정"
        out.append(prod)
    return out


def from_kb(kb_dir: Path, codes: list[str]) -> dict:
    import sqlite3
    c = sqlite3.connect(kb_dir / "winmate_kb.sqlite")
    c.row_factory = sqlite3.Row
    items = []
    for code in codes:
        m = c.execute("select * from product_model where model_code=?", (code,)).fetchone()
        if not m:
            items.append({"code": code, "missing": True})
            continue
        f = c.execute("select * from product_family where id=?", (m["family_id"],)).fetchone()
        specs = c.execute("select group_name, attr_name, value_raw, source_occurrence_id from spec_value where model_id=?", (m["id"],)).fetchall()
        url = None
        for s in specs:
            if s["source_occurrence_id"]:
                r = c.execute("select d.url from occurrence o join source_document d on d.id=o.document_id where o.id=?",
                              (s["source_occurrence_id"],)).fetchone()
                url = r["url"] if r else None
                break
        keep = {f"{s['group_name']}|{s['attr_name']}": s["value_raw"] for s in specs if "포장" not in (s["attr_name"] or "")}
        items.append({"code": code, "model_id": m["id"], "family_id": f["id"], "family_name": f["name_ko"],
                      "category_id": f["category_id"], "subcategory": f["subcategory_slug"], "detail_url": f["detail_url"],
                      "spec_source_url": url, "option": m["option_value"], "specs": keep})
    return {"items": items}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", default=str(ROOT / "birdseye/seed/kb_extract_2026-10-04.json"))
    ap.add_argument("--kb", help="winmate-kb/kb 폴더 — 주면 KB 에서 직접 다시 뽑는다")
    ap.add_argument("--out", default=str(ROOT / "birdseye/seed/products.json"))
    a = ap.parse_args()
    if a.kb:
        extract = from_kb(Path(a.kb), list(CURATION))
    else:
        extract = json.loads(Path(a.extract).read_text(encoding="utf-8"))
    prods = build(extract)
    doc = {
        "about": "PoC 제품 시드. 치수·사양은 winmate-kb 원문 값(source.fields), 약칭·분류·설치 방식은 PoC 큐레이션.",
        "kb_extracted": "2026-10-04",
        "products": prods,
    }
    Path(a.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(prods)}개 → {a.out}")


if __name__ == "__main__":
    main()
