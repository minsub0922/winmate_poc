#!/usr/bin/env python3
"""커버리지·품질 점검: DR 지표, 시나리오 상태, 시나리오 프로브(수용 기준 자동 확인) → dr_metric·scenario_status·리포트.

python build/qa.py            # kb/winmate_kb.sqlite 를 점검하고 docs/BUILD_REPORT.md 를 쓴다
"""
from __future__ import annotations

import collections
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from query import KB  # noqa: E402

KB_DIR = Path(os.environ.get("WKB_KB", ROOT / "kb"))
DB_PATH = KB_DIR / "winmate_kb.sqlite"
REPORT = Path(os.environ.get("WKB_REPORT", ROOT / "docs" / "BUILD_REPORT.md"))


def one(c, sql, args=()):
    r = c.execute(sql, args).fetchone()
    return r[0] if r else None


def pct(a, b):
    return f"{(100.0 * a / b):.1f}%" if b else "n/a"


def dr_metrics(c):
    M = []

    def add(dr, name, metric, value, status, note=""):
        M.append((dr, name, metric, str(value), status, note))

    seg_total = one(c, "SELECT count(*) FROM segment_mapping")
    seg_ok = one(c, "SELECT count(*) FROM segment_mapping WHERE kr_vertical_codes NOT LIKE '%<<FILL%' AND us_vertical_codes NOT LIKE '%<<FILL%'")
    add("DR01", "업종·세그먼트 대응표", "FILL 없는 Winmate 세그먼트 / 전체", f"{seg_ok}/{seg_total}", "partial",
        "모두 draft. 빈칸은 사람이 채워야 함")
    leaves = [r[0] for r in c.execute("""SELECT v.id FROM vertical v WHERE v.scheme='kr_site' AND v.url IS NOT NULL""")]
    with_seq = one(c, f"""SELECT count(DISTINCT vertical_id) FROM industry_section WHERE kind='scene' AND space_type_id IS NOT NULL
                          AND vertical_id IN ({','.join('?' * len(leaves))})""", leaves) if leaves else 0
    add("DR02", "업종별 공간 시퀀스", "공간이 있는 장면을 가진 KR 업종 페이지", f"{with_seq}/{len(leaves)}",
        "ready" if leaves and with_seq == len(leaves) else "partial", "업종 페이지 장면 순서 = 공간 시퀀스")
    sp_total = one(c, "SELECT count(*) FROM space_type")
    sp_attr = one(c, "SELECT count(*) FROM space_type WHERE default_attrs_json IS NOT NULL")
    add("DR03", "공간 속성", "속성 있는 공간 유형", f"{sp_attr}/{sp_total}", "blocked_by_source", "사이트에 공간 속성(시청거리·직사광 등) 구조 데이터 없음")
    scenes = one(c, "SELECT count(*) FROM industry_section WHERE kind='scene'")
    add("DR04", "UseCase·Need·Persona", "업종 페이지 장면(UseCase 대용) 수", scenes, "partial",
        "장면 제목·설명을 UseCase 로 사용. 페르소나는 소스에 없음")
    req = one(c, "SELECT count(*) FROM requires")
    add("DR05", "공간 → 역량(requires)", "requires 엣지(모두 draft)", req, "partial", "시드 초안. 전문가 승인 필요")
    rules = one(c, "SELECT count(*) FROM capability_rule")
    auto = one(c, "SELECT count(*) FROM capability_rule WHERE status='draft_auto'")
    prov = one(c, "SELECT count(*) FROM provides")
    add("DR06", "역량 룰", "presence 자동 규칙 / 전체 규칙, provides 행", f"{auto}/{rules}, provides={prov}", "partial",
        "임계값 규칙(휘도·IP·온도)은 파라미터 빈칸으로 비활성")
    cats = one(c, "SELECT count(*) FROM category")
    fams = one(c, "SELECT count(*) FROM product_family")
    mdls = one(c, "SELECT count(*) FROM product_model")
    add("DR07", "제품 마스터", "카테고리 / 제품군(카드) / 모델코드", f"{cats} / {fams} / {mdls}", "ready" if fams else "blocked_by_build")
    m_spec = one(c, "SELECT count(DISTINCT model_id) FROM spec_value")
    f_spec = one(c, "SELECT count(DISTINCT family_id) FROM spec_value")
    normed = one(c, "SELECT count(*) FROM spec_value WHERE norm_key IS NOT NULL")
    sv = one(c, "SELECT count(*) FROM spec_value")
    add("DR08", "정규화 스펙", "스펙 있는 모델 / 제품군, 정규 키 비율", f"{m_spec}/{mdls} 모델, {f_spec}/{fams} 제품군, 정규화 {pct(normed, sv)}",
        "ready" if m_spec else "blocked_by_build", "솔루션·서비스 상품 일부는 사이트에 스펙 없음")
    add("DR09", "판매 상태", "사이트 목록 노출 = 판매 중으로 간주", f"{fams} 제품군", "partial", "목록에서 빠진 단종 모델 정보는 사이트에 없음")
    add("DR10", "세대·후속 모델", "succession 엣지", 0, "blocked_by_source", "e-카탈로그·내부 자료 필요")
    sol = one(c, "SELECT count(*) FROM solution")
    sold = one(c, "SELECT count(*) FROM kg_edge WHERE rel='SOLD_AS'")
    sdoc = one(c, "SELECT count(*) FROM solution WHERE document_id IS NOT NULL")
    add("DR11", "솔루션", "솔루션 / 상품코드 연결 / 상세 페이지 연결", f"{sol} / {sold} / {sdoc}", "partial", "호환 기기 목록(compat)은 소스에 구조화되어 있지 않음")
    svc = one(c, "SELECT count(*) FROM service_product")
    add("DR12", "서비스 상품", "서비스 수", svc, "partial")
    dep = one(c, "SELECT count(*) FROM deployment")
    di = one(c, "SELECT count(*) FROM deployment_item")
    di_ok = one(c, "SELECT count(*) FROM deployment_item WHERE target_id IS NOT NULL")
    di_link = one(c, "SELECT count(*) FROM deployment_item WHERE source='case_related_link'")
    add("DR13", "구축사례", "사례 수, 사용 항목 해소율, 사이트 '관련 제품' 링크 수", f"{dep}, {pct(di_ok, di)}, {di_link}", "ready" if dep else "blocked_by_build",
        "수량은 소스에 거의 없음. 대부분 카테고리 단위 해소")
    kd = one(c, "SELECT count(DISTINCT deployment_id) FROM kpi_claim")
    add("DR14", "성과 KPI", "KPI 있는 사례 비율", pct(kd, dep), "partial", "이전 세션 LLM 추출(T5), 원문 대조 필요")
    vp = dict(c.execute("SELECT level, count(*) FROM value_prop GROUP BY level").fetchall())
    add("DR15", "Value Prop 계층", "레벨별 문구 수", json.dumps(vp, ensure_ascii=False), "ready" if vp else "blocked_by_build", "전부 원문 그대로(verbatim)")
    add("DR16", "강점·비교 축", "strength_point", 0, "blocked_by_source", "경쟁 비교 자료 필요")
    a_sp = one(c, """SELECT count(DISTINCT a.id) FROM image_asset a JOIN image_occurrence o ON o.asset_id=a.id
                     WHERE a.grade_hint='A' AND o.context_space_type_id IS NOT NULL""")
    a_all = one(c, "SELECT count(*) FROM image_asset WHERE grade_hint='A'")
    ac = one(c, "SELECT count(*) FROM image_asset WHERE grade_hint='A?C'")
    add("DR17", "A등급 공간 배치 이미지", "A 힌트(공간 맥락 있음) / A 전체 / A?C 미판정", f"{a_sp} / {a_all} / {ac}", "partial", "VLM 판정 전. 등급은 페이지 유형·파일명·alt 문장 규칙")
    fam_c = one(c, """SELECT count(DISTINCT d.target_id) FROM depicts d JOIN image_asset a ON a.id=d.asset_id
                      WHERE a.grade_hint='C' AND d.target_kind='family'""")
    add("DR18", "C등급 단독컷", "단독컷 있는 제품군", f"{fam_c}/{fams} ({pct(fam_c, fams)})", "ready" if fam_c else "blocked_by_build")
    dimg = one(c, "SELECT count(*) FROM image_asset WHERE grade_hint='D'")
    add("DR19", "UI·구성도 이미지", "D 힌트 이미지", dimg, "partial")
    dph = one(c, "SELECT count(DISTINCT target_id) FROM depicts WHERE target_kind='deployment'")
    add("DR20", "사례 사진", "사진 있는 사례 비율", pct(dph, dep), "ready" if dph else "blocked_by_build")
    add("DR21", "배치 룰(active)", "active placement_rule", one(c, "SELECT count(*) FROM placement_rule WHERE status='active'"), "blocked_by_source",
        "수량·크기 기준은 영업·기술 기준 필요")
    rec = one(c, "SELECT count(*) FROM kg_edge WHERE rel='RECOMMENDED_BY_SITE'")
    feat = one(c, "SELECT count(*) FROM kg_edge WHERE rel='FEATURED_BY_SITE'")
    add("DR22", "공식 권장(사이트)", "공간 추천 / 업종 추천 엣지", f"{rec} / {feat}", "ready" if rec else "blocked_by_build",
        "e-카탈로그 권장은 별도 소스(이번 빌드 범위 밖)")
    add("DR23", "과거 제안서 구조", "proposal_doc", 0, "blocked_by_source", "제안서 파일 필요")
    add("DR24", "Winmate 템플릿 메타", "sheet_role 수", one(c, "SELECT count(*) FROM sheet_role"), "partial", "data_shape 빈칸")
    ch = one(c, "SELECT count(*) FROM text_chunk")
    ch_e = one(c, "SELECT count(*) FROM text_chunk WHERE entity_refs_json != '[]'")
    vec = one(c, "SELECT count(*) FROM vec_index")
    add("DR25", "근거 원문 인덱스", "청크 / 엔티티 연결 비율 / 벡터", f"{ch} / {pct(ch_e, ch)} / {vec}", "ready" if ch else "blocked_by_build",
        "벡터는 LSA(문자 n-gram) — 신경망 임베딩은 모델 다운로드 차단으로 보류")
    men = one(c, "SELECT count(*) FROM mention")
    amb = one(c, "SELECT count(*) FROM mention WHERE confidence < 0.7")
    si = one(c, "SELECT count(*) FROM industry_section_item")
    si_un = one(c, "SELECT count(*) FROM industry_section_item WHERE target_id IS NULL")
    add("DR26", "언급 해소", "언급 수 / 저신뢰 비율 / 업종 항목 미해소", f"{men} / {pct(amb, men)} / {si_un}/{si}", "partial")
    return M


SCENARIOS = {
    "S1": ("고객 요구사항 → 필요 제품 추론", ["DR02", "DR05", "DR06", "DR07", "DR08", "DR13", "DR22", "DR26"]),
    "S2": ("업종·공간 → 솔루션 시나리오·제품 배치", ["DR02", "DR07", "DR15", "DR17", "DR22"]),
    "S3": ("업종·공간 → 제품 리스트", ["DR02", "DR07", "DR08", "DR21", "DR22"]),
    "S4": ("Value Prop 추출", ["DR15", "DR07"]),
    "S5": ("관련 이미지 활용", ["DR17", "DR18", "DR19", "DR20"]),
    "S6": ("제품·솔루션 상세(흩어진 정보 통합)", ["DR07", "DR08", "DR11", "DR13", "DR26"]),
    "S7": ("스펙 비교·요구 스펙 대응표", ["DR07", "DR08", "DR10"]),
    "S8": ("유사 사례·성과 수치", ["DR13", "DR14", "DR20"]),
    "S9": ("업종 판별·인사이트", ["DR01", "DR02", "DR13"]),
    "S10": ("솔루션 구성·BOM", ["DR11", "DR12"]),
    "S11": ("공간 배치·수량 산정", ["DR03", "DR21"]),
    "S12": ("기존 제안서 활용", ["DR23", "DR24"]),
    "S13": ("자유 질문 RAG", ["DR25"]),
    "S14": ("변경 영향", ["DR10", "DR23"]),
    "S15": ("화면별 자동 판단", ["DR02", "DR05", "DR06", "DR22"]),
}


def probes(kb: KB, c):
    """실제 데이터에서 프로브 질의를 만들고 수용 기준을 자동 확인한다."""
    out = []

    def rec(sc, name, ok, detail):
        out.append({"scenario": sc, "probe": name, "pass": bool(ok), "detail": detail})

    # S1: hard 역량 충족 + 근거 경로
    row = c.execute("""SELECT s.vertical_id, s.space_type_id, v.name_ko, st.name_ko FROM industry_section s JOIN vertical v ON v.id=s.vertical_id
                       JOIN space_type st ON st.id=s.space_type_id WHERE s.kind='scene' AND v.scheme='kr_site'
                       GROUP BY s.vertical_id, s.space_type_id ORDER BY count(*) DESC LIMIT 1""").fetchone()
    texts = []
    if row:
        texts.append(f"{row[2]} {row[3]}에 24시간 운영하는 디스플레이가 필요해")
    texts.append("호텔 객실 TV를 통합 관리하고 로비에 대형 사이니지를 설치하고 싶어")
    texts.append("매장 입구 쇼윈도에 햇빛에서도 잘 보이는 사이니지")
    for t in texts:
        r = kb.S1(t)
        fams = [(p["space"], f) for p in r["result"]["by_space"] for f in p["families"]]
        bad = [f["id"] for sp, f in fams if f["missing_hard"] and "HARD_CONFLICT" not in r["decision_reasons"]]
        no_path = [f["id"] for sp, f in fams if not f["reasons"]]
        rec("S1", f"S1 '{t}'", fams and not bad and not no_path,
            f"후보 {len(fams)}개, hard 미충족 {len(bad)}, 근거 없음 {len(no_path)}, 판단 {r['decision_hint']} {r['decision_reasons']}")
    # S1: 실외 요구 → weatherproof 없는 모델 금지
    r = kb.C2(["weatherproof"], category="top_display")
    fams = r["result"]["families"]
    rec("S1", "실외 요구 → 실외 대응 없는 모델 제외", all("cap_weatherproof" in f["satisfies"] for f in fams) and fams,
        f"후보 {len(fams)}: " + ", ".join(f["name"] for f in fams[:5]))
    # S2: 업종 프리셋 장면
    for vid in [r[0] for r in c.execute("SELECT DISTINCT vertical_id FROM industry_section WHERE kind='scene' AND vertical_id LIKE 'kr_%' LIMIT 3")]:
        b = kb.S2(vid)["result"]
        ok = b["scenes"] and all(s["space_types"] or s["items"] for s in b["scenes"])
        rec("S2", f"S2 {vid} 장면", ok, f"장면 {len(b['scenes'])}, 공간 있는 장면 {sum(1 for s in b['scenes'] if s['space_types'])}")
    # S3: 공간별 제품 리스트
    sp = c.execute("SELECT src_id, count(*) n FROM kg_edge WHERE rel='RECOMMENDED_BY_SITE' GROUP BY src_id ORDER BY n DESC LIMIT 3").fetchall()
    for s, _ in sp:
        r = kb.C2([], space=s)
        rec("S3", f"S3 공간 {s} 제품", r["result"]["families"] or r["result"]["solutions"],
            f"제품군 {len(r['result']['families'])}, 솔루션 {len(r['result']['solutions'])}")
    # S4: 원문 일치
    vps = c.execute("""SELECT v.id, v.text, b.text FROM value_prop v JOIN occurrence o ON o.id=v.source_occurrence_id
                       JOIN document_block b ON b.id=o.block_id ORDER BY random() LIMIT 200""").fetchall()
    def nz(s):
        return re.sub(r"\s+", "", s or "")
    mism = [v for v in vps if nz(v[1]) not in nz(v[2]) and nz(v[2]) not in nz(v[1])]   # 2블록 연결 문구(히어로·태그라인+이름) 허용
    rec("S4", "메시지 문장 = 출처 블록 원문(200건 표본)", len(mism) <= len(vps) * 0.05, f"불일치 {len(mism)}/{len(vps)}"
        + (f" 예: {mism[0][1][:40]} ↔ {mism[0][2][:40]}" if mism else ""))
    tree = c.execute("SELECT count(*) FROM value_prop p JOIN value_prop k ON k.parent_id=p.id").fetchone()[0]
    rec("S4", "key_message → proof_point 계층", tree > 0, f"부모-자식 쌍 {tree}")
    # S5: 이미지
    sp = c.execute("""SELECT o.context_space_type_id, count(*) n FROM image_occurrence o JOIN image_asset a ON a.id=o.asset_id
                      WHERE o.context_space_type_id IS NOT NULL GROUP BY 1 ORDER BY n DESC LIMIT 3""").fetchall()
    for s, _ in sp:
        r = kb.G1(s)
        imgs = r["result"]["images"]
        ok = imgs and all(i["page_url"] and i["sp"] == s for i in imgs) and all(i["caption_rule"] for i in imgs)
        rec("S5", f"G1 공간 {s}", ok, f"{len(imgs)}장, 폴백 {r['fallback_level']}")
    # S6: 흩어진 정보 통합
    fam = c.execute("""SELECT m.resolved_id FROM mention m JOIN source_document d ON d.id=m.document_id WHERE m.resolved_kind='family'
                       GROUP BY m.resolved_id ORDER BY count(DISTINCT d.page_type) DESC, count(*) DESC LIMIT 1""").fetchone()
    if fam:
        e = kb.entity("family", fam[0])["result"]
        kinds = {m["page_type"] for m in e["mentions_by_source"]}
        rec("S6", f"제품군 {fam[0]} 통합 보기", len(kinds) >= 2, f"언급 페이지 유형 {sorted(kinds)}, 모델 {len(e.get('models', []))}, 스펙 {len(e.get('key_specs', []))}")
    sol = c.execute("SELECT id FROM solution WHERE document_id IS NOT NULL LIMIT 1").fetchone()
    if sol:
        e = kb.entity("solution", sol[0])["result"]
        rec("S6", f"솔루션 {sol[0]} 통합 보기", e["edges_in"] or e["edges_out"], f"in {list(e['edges_in'])[:5]}, out {list(e['edges_out'])[:5]}")
    # S7: 스펙 판정 unknown 처리
    f = c.execute("SELECT family_id FROM spec_value WHERE norm_key='brightness_nit' AND value_num IS NOT NULL LIMIT 1").fetchone()
    if f:
        r = kb.C6(f[0], [{"key": "brightness_nit", "op": ">=", "value": 500}, {"key": "pixel_pitch_mm", "op": "<=", "value": 2}])
        rows = r["result"]["rows"]
        rec("S7", "C6 pass/fail/unknown", all(x["verdict"] in ("pass", "fail", "unknown") for x in rows), json.dumps(rows, ensure_ascii=False)[:200])
    # S8: 유사 사례
    v = c.execute("SELECT dst_id, count(*) FROM kg_edge WHERE rel='IN_VERTICAL' GROUP BY dst_id ORDER BY 2 DESC LIMIT 1").fetchone()
    if v:
        r = kb.D1(vertical=v[0], text="로비 사이니지")
        deps = r["result"]["deployments"]
        rec("S8", f"D1 {v[0]}", deps and all(d["url"] or d.get("format") in ("video", "pdf", "report", "youtube") for d in deps)
            and all("similarity_breakdown" in d for d in deps), f"{len(deps)}건, URL 없는 사례 형식 {[d.get('format') for d in deps if not d['url']]}")
    # S9: 업종 판별
    for t, exp in [("병원 입원실 환자용 태블릿", "kr_medical"), ("학교 교실 전자칠판", "kr_education"), ("호텔 객실 TV", "kr_hotel")]:
        r = kb.A2(t)
        top = [x["id"] for x in r["result"]["top2"]]
        rec("S9", f"A2 '{t}'", exp in top or any(c.execute("SELECT 1 FROM vertical WHERE id=? AND parent_id=?", (x, exp)).fetchone() for x in top),
            f"top2 {top}, ask={r['result']['ask']}")
    # S13: 검색 근거
    r = kb.search("객실 TV 원격 관리")
    rec("S13", "하이브리드 검색 근거 URL", r["result"]["chunks"] and all(h["url"] for h in r["result"]["chunks"]), f"{len(r['result']['chunks'])}건")
    return out


def scenario_status(dr, prb):
    st = {d[0]: d[4] for d in dr}
    pr = collections.defaultdict(list)
    for p in prb:
        pr[p["scenario"]].append(p["pass"])
    out = []
    for sc, (name, drs) in SCENARIOS.items():
        sts = [st.get(d, "partial") for d in drs]
        reasons = [f"{d}:{st.get(d)}" for d in drs if st.get(d) != "ready"]
        if all(s == "blocked_by_source" for s in sts) or sc in ("S10", "S11", "S12", "S14"):
            s = "blocked_by_source"
        elif any(s == "blocked_by_build" for s in sts):
            s = "blocked_by_build"
        elif pr.get(sc) and all(pr[sc]) and all(x == "ready" for x in sts):
            s = "ready"
        else:
            s = "partial"
        if pr.get(sc):
            reasons.append(f"probes {sum(pr[sc])}/{len(pr[sc])} pass")
        if sc == "S13":
            reasons.append("LLM RAG 는 이번 범위 밖(검색·근거 레이어만 구축)")
        out.append((sc, name, s, "; ".join(reasons)))
    return out


def main():
    c = sqlite3.connect(DB_PATH)
    kb = KB(DB_PATH)
    dr = dr_metrics(c)
    prb = probes(kb, c)
    sc = scenario_status(dr, prb)
    c.execute("DELETE FROM dr_metric")
    c.execute("DELETE FROM scenario_status")
    c.executemany("INSERT INTO dr_metric VALUES (?,?,?,?,?,?)", dr)
    c.executemany("INSERT INTO scenario_status VALUES (?,?,?,?)", sc)
    c.execute("INSERT OR REPLACE INTO kb_meta VALUES ('qa.probes', ?)", (json.dumps(prb, ensure_ascii=False),))
    c.commit()
    meta = dict(c.execute("SELECT key, value FROM kb_meta").fetchall())
    counts = {k[6:]: v for k, v in meta.items() if k.startswith("count.")}
    L = ["# Build report", "", f"- 빌드 DB: `{DB_PATH.name}` · 상품 수집 시각 {meta.get('products_fetched_at')}",
         f"- 외래키 위반: {meta.get('foreign_key_violations')}", f"- 인덱스: {meta.get('index.model')} dim={meta.get('index.dim')}", "",
         "## 적재 건수", "", "| 항목 | 건수 |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(counts.items())]
    L += ["", "## 데이터 요소(DR) 커버리지", "", "| DR | 요소 | 지표 | 값 | 상태 | 메모 |", "|---|---|---|---|---|---|"]
    L += [f"| {d[0]} | {d[1]} | {d[2]} | {d[3]} | {d[4]} | {d[5]} |" for d in dr]
    L += ["", "## 시나리오 상태", "", "| 시나리오 | 이름 | 상태 | 사유 |", "|---|---|---|---|"]
    L += [f"| {s[0]} | {s[1]} | {s[2]} | {s[3]} |" for s in sc]
    L += ["", "## 시나리오 프로브", "", "| 시나리오 | 프로브 | 결과 | 상세 |", "|---|---|---|---|"]
    L += [f"| {p['scenario']} | {p['probe']} | {'pass' if p['pass'] else 'FAIL'} | {p['detail'].replace('|', '/')} |" for p in prb]
    un = c.execute("SELECT label, occurrences FROM space_label WHERE space_type_id IS NULL ORDER BY occurrences DESC").fetchall()
    L += ["", "## 미매핑 공간 라벨(큐레이션 대상)", "", ", ".join(f"{a}({b})" for a, b in un) or "없음"]
    ui = c.execute("""SELECT i.item_name, count(*) FROM industry_section_item i WHERE i.target_id IS NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 40""").fetchall()
    L += ["", "## 미해소 업종 페이지 항목(상위 40)", "", ", ".join(f"{a}({b})" for a, b in ui) or "없음"]
    notes = json.loads(meta.get("notes") or "[]")
    if notes:
        L += ["", "## 빌드 메모", ""] + [f"- {n}" for n in notes]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(json.dumps({"scenarios": {s[0]: s[2] for s in sc}, "probes_pass": sum(p["pass"] for p in prb), "probes": len(prb)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
