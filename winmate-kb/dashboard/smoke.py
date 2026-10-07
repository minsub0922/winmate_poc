#!/usr/bin/env python3
"""대시보드 스모크 테스트(헤드리스 Chromium): 탭마다 오류 없이 그려지는지, 질의가 돌아가는지, 검수 표시가 저장·표시되는지.

python dashboard/smoke.py      # dashboard/site 를 로컬 서버로 띄워 확인, 스크린샷은 dashboard/build/shots/
window.claude 는 메모리 가짜(db·user·downloads)로 대신한다.
"""
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SITE, SHOTS = ROOT / "site", ROOT / "build" / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)

MOCK = """
(() => {
  const docs = new Map(); const subs = new Set();
  const snap = () => ({ docs: [...docs.entries()].sort().map(([id, v]) => ({ id, exists: true, data: () => JSON.parse(JSON.stringify(v)), metadata: {} })), size: docs.size, empty: !docs.size, docChanges: () => [], metadata: {} });
  const emit = () => setTimeout(() => subs.forEach((f) => f(snap())), 5);
  const col = { doc: (id) => ({ id, set: async (v) => { docs.set(id, v); emit(); }, delete: async () => { docs.delete(id); emit(); } }),
                onSnapshot: (f) => { subs.add(f); setTimeout(() => f(snap()), 5); return () => subs.delete(f); } };
  const db = { collection: (p) => col };
  const user = { id: async () => 'user_test', can: async () => true, me: async () => ({ id: 'user_test', name: '테스터' }), profiles: async (ids) => Object.fromEntries([].concat(ids).map((i) => [i, { id: i, name: i === 'user_test' ? '테스터' : '' }])) };
  const downloads = { save: async (r) => { window.__saved = r; return { status: 'saved' }; } };
  window.__mockdocs = docs;
  window.claude = { use: async (n) => ({ db, user, downloads })[n] || null };
})();
"""


def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    h.log_message = lambda *a, **k: None
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def main():
    # 게시 형태와 같게: 조각 페이지를 문서 골격에 넣어 로컬 index 로 쓴다
    body = (SITE / "index.html").read_text(encoding="utf-8")
    (SITE / "_local.html").write_text('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + body + "</body></html>", encoding="utf-8")
    srv = serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}/_local.html"
    errors, results = [], {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        for scheme, size in (("light", (1360, 900)), ("dark", (390, 844))):
            pg = br.new_page(viewport={"width": size[0], "height": size[1]}, color_scheme=scheme)
            pg.add_init_script(MOCK)
            pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
            pg.goto(base + "#overview")
            pg.wait_for_selector(".status-strip", timeout=30000)
            pg.screenshot(path=str(SHOTS / f"overview_{scheme}.png"), full_page=False)
            overflow = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
            results[f"{scheme}.overview_hscroll"] = overflow
            if scheme == "dark":
                for tab in ("verticals", "products", "cases", "images", "messages", "reviews", "query", "ctxmsg"):
                    pg.goto(base + "#" + tab)
                    pg.wait_for_timeout(1500)
                    results[f"dark.{tab}_hscroll"] = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                    pg.screenshot(path=str(SHOTS / f"{tab}_mobile.png"))
                pg.close()
                continue
            # 질의: 요구사항
            pg.goto(base + "#query")
            pg.click("[data-m=s1]")
            pg.fill("#qtext", "호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어")
            pg.click("#qrun")
            pg.wait_for_selector(".spacecard", timeout=120000)
            results["s1_spaces"] = pg.eval_on_selector_all(".spacecard h3", "els => els.map(e => e.textContent)")
            results["s1_first_family"] = pg.eval_on_selector(".spacecard tbody tr td:nth-child(2) .chip", "e => e.textContent")
            pg.screenshot(path=str(SHOTS / "query_s1.png"), full_page=True)
            # 검수 표시 저장
            pg.click(".spacecard tbody tr .rv button[data-v=ok]")
            pg.wait_for_timeout(300)
            results["review_saved"] = pg.evaluate("window.__mockdocs.size")
            results["review_btn_on"] = pg.eval_on_selector(".spacecard tbody tr .rv button[data-v=ok]", "e => e.classList.contains('on')")
            # 원문 검색·이미지 검색·업종 판별
            for mode, q, sel in (("search", "병상 태블릿 환자 소통", ".hit"), ("image", "카페 천장에 설치된 시스템에어컨", ".icard"), ("a2", "병원 진료 대기실", "table"), ("a1", "LH85WMBWLGCXKR 전자칠판을 강의실에", "table")):
                pg.click(f"[data-m={mode}]")
                pg.fill("#qtext", q)
                pg.click("#qrun")
                pg.wait_for_selector(f"#qout {sel}", timeout=120000)
                results[f"{mode}_n"] = pg.eval_on_selector_all(f"#qout {sel}", "els => els.length")
                pg.screenshot(path=str(SHOTS / f"query_{mode}.png"))
            # 컨텍스트 → 메시지: 예시(호텔 객실) → 섹션·검수·제품 입력 제안
            pg.goto(base + "#ctxmsg")
            pg.wait_for_selector("#cmex [data-cmpre]", timeout=30000)
            pg.click("#cmex [data-cmpre='0']")
            pg.wait_for_selector("#cmout .ctxtab", timeout=180000)
            pg.wait_for_timeout(800)
            results["cm_ctx_rows"] = pg.eval_on_selector_all("#cmout .ctxtab tr", "els => els.map(e => e.textContent.replace(/\\s+/g, ' ').trim().slice(0, 60))")
            results["cm_sections"] = pg.eval_on_selector_all("#cmout .section > h2", "els => els.map(e => e.textContent.trim().slice(0, 24))")
            results["cm_headline"] = pg.eval_on_selector_all("#cmout .headline .mtext", "els => els.map(e => e.textContent)")
            results["cm_km"] = pg.eval_on_selector_all("#cmout .mrow .mtext", "els => els.length")
            results["cm_thumbs"] = pg.eval_on_selector_all("#cmout img[data-aid]", "els => els.length")
            pg.screenshot(path=str(SHOTS / "ctxmsg.png"), full_page=True)
            before = pg.evaluate("window.__mockdocs.size")
            pg.click("#cmout .mrow .rv button[data-v=ok] >> nth=0")
            pg.wait_for_timeout(300)
            results["cm_review_saved"] = pg.evaluate("window.__mockdocs.size") - before
            results["cm_review_kind"] = pg.evaluate("[...window.__mockdocs.values()].map(v => v.kind).filter(k => k === 'ctxmsg').length")
            # 제품 입력 제안 → 칩 → 다시 뽑기(요구사항만 + 제품)
            pg.click("#cmclear")
            pg.fill("#cmpq", "비디오월")
            pg.wait_for_selector("#cmsugg.on button", timeout=10000)
            results["cm_sugg"] = pg.eval_on_selector_all("#cmsugg button", "els => els.slice(0, 4).map(e => e.textContent.trim().slice(0, 30))")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(200)
            results["cm_picked"] = pg.eval_on_selector_all("#cmppick .chip", "els => els.map(e => e.textContent)")
            pg.select_option("#cmsp", "lobby")
            pg.click("#cmrun")
            pg.wait_for_selector("#cmout .ctxtab", timeout=60000)
            pg.wait_for_timeout(500)
            results["cm2_first_prod"] = pg.eval_on_selector_all("#cmout .pcard header .chip", "els => els.slice(0, 3).map(e => e.textContent)")
            results["cm2_missing"] = pg.eval_on_selector_all("#cmout .ctxtab td .faint", "els => els.length")
            pg.screenshot(path=str(SHOTS / "ctxmsg_product.png"))
            # 업종 장면
            pg.goto(base + "#verticals")
            pg.wait_for_selector(".scene", timeout=30000)
            pg.wait_for_timeout(1500)
            results["vert_scenes"] = pg.eval_on_selector_all(".scene", "els => els.length")
            pg.screenshot(path=str(SHOTS / "verticals.png"), full_page=False)
            # 제품 → 드로어 → 전체 스펙
            pg.goto(base + "#products")
            pg.wait_for_selector(".fcard")
            results["prod_cards"] = pg.eval_on_selector_all(".fcard", "els => els.length")
            for q in ("무풍 4way", "시스템 에어컨", "전자칠판", "에어컨"):
                pg.fill("#pq", q)
                pg.wait_for_timeout(500)
                names = pg.eval_on_selector_all(".fcard .nm", "els => els.map(e => e.textContent)")
                total = pg.eval_on_selector("#plist > .small.muted", "e => e.textContent")
                cats = pg.eval_on_selector_all("[data-pcat]", "els => els.map(e => e.textContent)")
                results[f"psearch[{q}]"] = {"total": total[:20], "has_무풍4Way냉난방": "무풍 4Way 냉난방" in names, "first": names[:3], "cats": cats[:4]}
            pg.screenshot(path=str(SHOTS / "products_search.png"))
            pg.fill("#pq", "")
            pg.wait_for_timeout(400)
            pg.click(".fcard >> nth=0")
            pg.wait_for_selector("#drawer.on")
            pg.click("#loadpdp")
            pg.wait_for_selector("#fampdp details", timeout=60000)
            results["pdp_models"] = pg.eval_on_selector_all("#fampdp details", "els => els.length")
            pg.screenshot(path=str(SHOTS / "family_drawer.png"))
            pg.keyboard.press("Escape")
            # 사례
            pg.goto(base + "#cases")
            pg.wait_for_selector("#clist tbody tr")
            pg.click("#clist tbody tr >> nth=0")
            pg.wait_for_selector("#drawer.on")
            results["case_drawer"] = pg.eval_on_selector("#dhead h2", "e => e.textContent")
            pg.screenshot(path=str(SHOTS / "case_drawer.png"))
            pg.keyboard.press("Escape")
            # 이미지
            pg.goto(base + "#images")
            pg.wait_for_selector(".icard", timeout=60000)
            results["img_cards"] = pg.eval_on_selector_all(".icard", "els => els.length")
            pg.select_option(".icard >> nth=0 >> select[data-fix]", "C")
            pg.wait_for_timeout(300)
            pg.screenshot(path=str(SHOTS / "images.png"))
            # 메시지
            pg.goto(base + "#messages")
            pg.wait_for_selector("#mlist tbody tr", timeout=60000)
            results["msg_rows"] = pg.eval_on_selector_all("#mlist tbody tr", "els => els.length")
            # 검수 목록·CSV
            pg.goto(base + "#reviews")
            pg.wait_for_selector("#rvlist tbody tr")
            results["review_rows"] = pg.eval_on_selector_all("#rvlist tbody tr", "els => els.length")
            pg.click("#rvcsv")
            pg.wait_for_timeout(300)
            results["csv_saved"] = pg.evaluate("!!(window.__saved && window.__saved.data.includes('맞음'))")
            pg.screenshot(path=str(SHOTS / "reviews.png"))
            pg.close()
        br.close()
    srv.shutdown()
    (SITE / "_local.html").unlink()
    print(json.dumps(results, ensure_ascii=False, indent=1))
    errs = [e for e in errors if "favicon" not in e]
    print("errors:", len(errs))
    for e in errs[:30]:
        print(" ", e)
    bad = errs or any(v is True for k, v in results.items() if k.endswith("hscroll"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
