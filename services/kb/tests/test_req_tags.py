"""요구 태그(R01~R24) · 제안 콘텐츠(P01~P22) 코드표 — curation/req_tags.yaml(원문 winmate-kb/raw 의 meta.taxonomy)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "winmate-kb" / "raw" / "prior_case_studies.json"


async def test_codebook_endpoint(client, ok):
    body = ok(await client.get("/v1/req-tags"))
    assert [r["code"] for r in body["req_tags"]] == [f"R{i:02d}" for i in range(1, 25)]
    assert [p["code"] for p in body["proposal_contents"]] == [f"P{i:02d}" for i in range(1, 23)]
    r = {x["code"]: x for x in body["req_tags"]}
    assert r["R01"] == {"code": "R01", "label": "다지점·원격 통합 관리", "description": "콘텐츠/기기를 본사·관리실에서 일괄"}
    assert r["R05"]["label"] == "에너지 절감·운영비 절감" and r["R05"]["description"] is None
    assert r["R08"]["label"] == "고객(이용자) 경험·서비스 혁신"            # 붙은 괄호는 이름표에 남는다
    p = {x["code"]: x["label"] for x in body["proposal_contents"]}
    assert p["P02"] == "공간별 제품 배치(조감도/공간 맵)" and p["P22"] == "의사결정 요약·다음 단계"
    assert body["source_tier"] == "T5_llm_extracted" and body["source"].endswith("#meta.taxonomy")


async def test_insights_labels_from_codebook(client, ok):
    book = {x["code"]: x for x in ok(await client.get("/v1/req-tags"))["req_tags"]}
    for seg in ("FB", "HT", "OF"):
        ins = ok(await client.get(f"/v1/segments/{seg}/insights", params={"top_req": 24}))
        for t in ins["req_types"]:
            assert t["label"] == book[t["code"]]["label"] and t["description"] == book[t["code"]]["description"]
            assert t["label_source"] == "codebook"


@pytest.mark.skipif(not RAW.exists(), reason="winmate-kb/raw 없음")
def test_yaml_matches_raw():
    """curation/req_tags.yaml 이 raw 원문에서 다시 만든 것과 같다(손으로 고치지 않았다)."""
    script = Path(__file__).resolve().parents[1] / "scripts" / "make_req_tags.py"
    r = subprocess.run([sys.executable, str(script), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    tax = json.loads(RAW.read_text(encoding="utf-8"))["meta"]["taxonomy"]
    assert len(tax["req_tags"]) == 24
