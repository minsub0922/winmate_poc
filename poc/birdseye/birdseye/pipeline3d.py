"""3D 조감도 작업 흐름(BR2) — ①분석 ②참고 사례 ③공간 모델링 ④가구 배치 ⑤렌더 ⑥품질 확인."""
from __future__ import annotations

import copy
import datetime as dt
import json
import threading
import time

from . import blender_runner, kbref
from .analyze3d import LIB, SPACE_TYPES, analyze
from .jobs import Job
from .rules import Rules
from .scene3d import QUALITY, build_layout, cut_label, layout_info, make_cuts, scene_spec


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def _load_2d(app, p):
    if not p.get("linked_2d"):
        return None
    try:
        return app.store.get(p["linked_2d"])
    except KeyError:
        return None


def _brief_note(p, info, brief) -> str:
    inp = p["input"]
    st = SPACE_TYPES.get(inp.get("space_type") or "lobby", {}).get("label", "")
    moods = " · ".join(LIB["moods"].get(m, m) for m in inp.get("moods", []))
    src = {"llm": "AI(LLM)", "replay": "AI(저장된 응답)", "rules": "규칙 기반"}.get(brief["meta"]["source"], brief["meta"]["source"])
    parts = [x for x in (st, moods, f"제품 {len(inp.get('products', []))}종", "2D 연결" if info["linked"] else None) if x]
    return " · ".join(parts) + f" — {src}"


def _save_brief(p, brief, source_note=None):
    hist = p.setdefault("brief_history", [])
    rev = len(hist) + 1
    b = copy.deepcopy(brief)
    b["rev"] = rev
    hist.append({"rev": rev, "created": _now(), "concept": b["concept"], "source": b["meta"]["source"], "note": source_note})
    p["brief"] = b
    return rev


def _refs(app, p, info):
    fams, cats = [], []
    for c in p["input"].get("products", []):
        prod = app.catalog.get(c)
        if prod:
            fams.append(prod["kb"]["family_id"])
            cats.append(prod["kb"]["category_id"])
    st = p["input"].get("space_type") or info["space"].get("space_type") or "lobby"
    return kbref.reference_images(app.settings.kb_dir, st, fams, cats, 3)


def _qc_summary(manifest: dict, layout: dict) -> dict:
    qc = manifest.get("qc", {})
    dims = qc.get("product_dims", [])
    max_err = max((d["err_mm"] for d in dims), default=0)
    vis = []
    for c in manifest.get("cuts", []):
        if c.get("variant") != "after":
            continue
        # 화면 안에 들어온 제품 중 가려지지 않고 보이는 비율(화면 밖은 카메라 선택이라 문제로 보지 않는다)
        inside = [v for v in c.get("visibility", []) if v["in_frame"] >= 0.4]
        seen = [v for v in inside if v["visible"] >= 0.4]
        vis.append({"cut": cut_label(c["camera"], c["lighting"], c["variant"]), "seen": len(seen), "inside": len(inside),
                    "total": len(c.get("visibility", []))})
    skipped = layout.get("log", {}).get("skipped", [])
    items = [
        {"name": "제품 비율", "ok": max_err < 1.0, "detail": f"제품 {len(dims)}대 외형 = KB 스펙 치수(오차 최대 {max_err:.1f} mm)"},
        {"name": "겹침", "ok": not qc.get("overlaps"), "detail": f"가구·제품 겹침 {len(qc.get('overlaps', []))}건"},
        {"name": "제품 노출", "ok": all(v["seen"] >= max(1, round(v["inside"] * 0.6)) for v in vis) if vis else True,
         "detail": " · ".join(f"{v['cut']} {v['seen']}/{v['inside']}대 보임" + (f"(화면 밖 {v['total'] - v['inside']})" if v["total"] > v["inside"] else "")
                              for v in vis) or "도입 전 컷만"},
        {"name": "로고 노출", "ok": True, "detail": "화면은 일반 패턴 콘텐츠 — 상표·로고 없음"},
        {"name": "AI 생성 표시", "ok": True, "detail": "모든 컷 왼쪽 아래에 'AI 생성 · 개략' 고정"},
    ]
    if skipped:
        items.append({"name": "생략한 가구", "ok": True, "detail": " · ".join(f"{s['label']}({s['reason']})" for s in skipped[:4])})
    return {"items": items, "ok": all(i["ok"] for i in items)}


def _run_blender(job: Job, app, out_dir, spec, label_prefix=""):
    out_dir.mkdir(parents=True, exist_ok=True)
    bs = app.settings.blender  # .env 의 RENDER_ENGINE · RENDER_DEVICE · RENDER_THREADS
    spec["render"].update(device=bs["device"], threads=bs["threads"],
                          engine="EEVEE" if bs["engine"].startswith("eevee") else "CYCLES")
    spec_path = out_dir / "scene.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    n = len(spec["cuts"])
    res, samples = spec["render"]["res"], spec["render"]["samples"]
    # 진행률을 Blender 가 알려주지 않을 때(bpy 모듈 등) 쓰는 시간 추정 — 첫 컷은 화소 × 샘플로, 다음 컷부터는 앞 컷 시간으로
    guess = max(20.0, min(1800.0, res[0] * res[1] * samples / 350000.0))
    state = {"done": 0, "cur": None, "t0": 0.0, "durs": [], "real": False}
    stop = threading.Event()

    def on_event(e):
        k = e.get("kind")
        if k == "preview":
            rel = out_dir.relative_to(app.store.dir(job.project_id)).as_posix()
            job.preview = f"/files/{job.project_id}/{rel}/{e['file']}"
        elif k == "cut_start":
            job.cut_progress[e["cut"]] = 0
            state.update(cur=e["cut"], t0=time.time())
        elif k == "render" and e.get("cut") in job.cut_progress:
            state["real"] = True
            job.progress_estimated = False
            job.cut_progress[e["cut"]] = e.get("pct", 0)
        elif k == "sample":  # Blender 앱이 찍는 'Sample a/b' — 지금 렌더 중인 컷에 붙인다
            state["real"] = True
            job.progress_estimated = False
            cur = next((c for c, v in job.cut_progress.items() if v < 100), None)
            if cur and e.get("b"):
                job.cut_progress[cur] = max(job.cut_progress[cur], min(99, round(100 * e["a"] / e["b"])))
        elif k == "cut_done":
            job.cut_progress[e["cut"]] = 100
            state["done"] += 1
            state["durs"].append(float(e.get("seconds") or (time.time() - state["t0"])))
            state["cur"] = None
            job.pct = max(job.pct, 66 + int(25 * state["done"] / max(1, n)))
            job.log.append(f"{label_prefix}{e['cut']} {e.get('seconds')}s")
        elif k == "error":
            job.log.append(e.get("msg", ""))

    def ticker():
        while not stop.wait(1.0):
            c = state["cur"]
            if not c or state["real"]:
                continue
            exp = sum(state["durs"]) / len(state["durs"]) if state["durs"] else guess
            pct = min(95, int(100 * (time.time() - state["t0"]) / max(5.0, exp)))
            if pct > job.cut_progress.get(c, 0):
                job.progress_estimated = True
                job.cut_progress[c] = pct
                job.pct = max(job.pct, 66 + int(25 * (state["done"] + pct / 100) / max(1, n)))

    threading.Thread(target=ticker, daemon=True).start()
    try:
        return blender_runner.run(app.settings, spec_path, out_dir, on_event, job.cancel)
    finally:
        stop.set()


def run_render(job: Job, app, pid: str, mode: str = "full", cuts: list | None = None, quality: str = "standard",
               request_text: str | None = None):
    p = app.store.get(pid)
    p2 = _load_2d(app, p)
    if p.get("linked_2d") and not p2:
        job.log.append("연결된 2D 조감도를 찾지 못해 연결 없이 진행해요")
    rules = Rules(p.get("rules_override"))
    info = layout_info(p, p2, app.catalog, rules)
    # ① 분석
    if mode == "full" or not p.get("brief"):
        job.step(1, "run")
        brief = analyze(p, info, app.catalog, app.llm)
        _save_brief(p, brief, "처음 분석")
        job.step(1, "done", _brief_note(p, info, brief))
    elif mode == "request":
        job.step(1, "run", "한 줄 요청 해석")
        brief = analyze(p, info, app.catalog, app.llm, "request", prev=p["brief"], request=request_text)
        _save_brief(p, brief, f"한 줄 요청: {request_text}")
        ch = brief.get("changes") or []
        job.step(1, "done", ("; ".join(ch[:3]) if ch else "바뀐 항목 없음") + f" — {brief['meta']['source']}")
    else:
        brief = p["brief"]
        job.step(1, "skip", "앞서 정한 구성 그대로 · 배치 · 가구는 그대로")
    # ② 참고 사례
    if mode == "full" or "refs" not in p:
        job.step(2, "run")
        p["refs"] = _refs(app, p, info)
        r = p["refs"]
        job.step(2, "done", f"{r.get('level') or '없음'} · {len(r.get('images', []))}건" if r.get("available") else r.get("note"))
    else:
        job.step(2, "skip", "앞서 찾은 사례 그대로")
    if job.cancel.is_set():
        raise RuntimeError("cancelled")
    # ③④ 공간·배치
    job.step(3, "run")
    lay = build_layout(p, info, brief, p2, app.catalog, rules)
    sp = lay["space"]
    if not p.get("space") or p["space"].get("estimated") and not info["linked"]:
        p["space"] = sp
    p["layout"] = {"placements": lay["placements"], "fixtures": lay["fixtures"], "zones": lay["zones"], "log": lay["log"],
                   "space_basis": info["space_basis"], "lines": lay["lines"], "brief_rev": p["brief"]["rev"]}
    job.step(3, "done", f"{sp['width']:,.0f} × {sp['depth']:,.0f} · 층고 {sp['height']:,.0f} — {info['space_basis']}")
    kinds = len({f['type'] for f in lay['fixtures']})
    sk = len(lay["log"].get("skipped", []))
    job.step(4, "done", f"마감 3종 · 가구 {kinds}종 {len(lay['fixtures'])}개 · 제품 {len(lay['placements'])}대" + (f" · 생략 {sk}" if sk else ""))
    p["status"] = "building"
    app.store.save(p)
    # ⑤ 렌더
    q = QUALITY.get(quality, QUALITY["standard"])
    cuts = cuts or [["aerial45", "day", "after"]]
    spec = scene_spec(lay, brief, app.catalog, make_cuts([tuple(c) for c in cuts]), quality, p.get("title", ""))
    if mode != "full":
        spec["render"]["preview"] = None
    loc = blender_runner.locate(app.settings)
    job.step(5, "run", f"{loc.get('note') or 'Blender'} · {q['res'][0]}×{q['res'][1]} · 샘플 {q['samples']} · 컷 {len(cuts)}")
    out_dir = app.store.renders_dir(pid) / job.id
    man = _run_blender(job, app, out_dir, spec)
    job.step(5, "done", f"{len(man['cuts'])}컷 · {man.get('seconds')}s · {man.get('device')}")
    # ⑥ 품질 확인
    qc = _qc_summary(man, lay)
    job.step(6, "done", "모두 통과" if qc["ok"] else "확인 필요 항목 있음")
    p = app.store.get(pid)
    renders = p.setdefault("renders", [])
    new = []
    for c in man["cuts"]:
        r = {"id": f"{job.id}-{c['id']}", "job": job.id, "cut": c["id"], "camera": c["camera"], "lighting": c["lighting"],
             "variant": c["variant"], "file": f"renders/{job.id}/{c['file']}", "res": c["res"], "label": cut_label(c["camera"], c["lighting"], c["variant"]),
             "zones": c["zones"], "visibility": c["visibility"], "brief_rev": brief.get("rev", p.get("brief", {}).get("rev")),
             "quality": quality, "created": _now(), "seconds": c["seconds"]}
        renders.append(r)
        new.append(r)
    p["qc"] = qc
    p["status"] = "done"
    p["step"] = "result"
    app.store.save(p)
    job.result = {"renders": new, "qc": qc}


def run_alternatives(job: Job, app, pid: str, quality: str = "draft"):
    p = app.store.get(pid)
    p2 = _load_2d(app, p)
    rules = Rules(p.get("rules_override"))
    info = layout_info(p, p2, app.catalog, rules)
    base = p.get("brief")
    if not base:
        raise RuntimeError("먼저 3D 조감도를 만들어 주세요")
    job.step(1, "run", "다른 콘셉트 2개")
    alts = []
    avoid = [base["concept"]]
    for i in range(2):
        info["avoid_concepts"] = list(avoid)
        b = analyze(p, info, app.catalog, app.llm, "alternative", prev=base if i == 0 else alts[-1]["brief"])
        if b["concept"] in avoid:  # 모델이 같은 콘셉트를 내면 규칙으로 바꾼다
            info["avoid_concepts"] = list(avoid)
            from .analyze3d import rule_brief, _rank_concepts
            nxt = next(k for _, k in _rank_concepts(p) if k not in avoid)
            b2 = rule_brief(p, info, nxt)
            b2["meta"] = dict(b.get("meta", {}), fixed=b.get("meta", {}).get("fixed", []) + ["concept(중복)"])
            b = b2
        avoid.append(b["concept"])
        alts.append({"id": f"alt{i + 1}", "brief": b})
    job.step(1, "done", " · ".join(LIB["concepts"][a["brief"]["concept"]]["label"] for a in alts))
    job.step(2, "skip", "앞서 찾은 사례 그대로")
    for i, a in enumerate(alts):
        if job.cancel.is_set():
            raise RuntimeError("cancelled")
        job.step(3, "run", f"안 {i + 1} 구성")
        lay = build_layout(p, info, a["brief"], p2, app.catalog, rules)
        job.step(3, "done")
        job.step(4, "done", f"안 {i + 1}: 가구 {len(lay['fixtures'])}개")
        spec = scene_spec(lay, a["brief"], app.catalog, make_cuts([("aerial45", "day", "after")]), quality, p.get("title", ""))
        spec["render"]["preview"] = None
        job.step(5, "run", f"안 {i + 1}/2 렌더")
        out_dir = app.store.renders_dir(pid) / job.id / a["id"]
        man = _run_blender(job, app, out_dir, spec, f"안{i + 1} ")
        c = man["cuts"][0]
        a.update(file=f"renders/{job.id}/{a['id']}/{c['file']}", label=LIB["concepts"][a["brief"]["concept"]]["label"],
                 zones=c["zones"], res=c["res"], layout={"placements": lay["placements"], "fixtures": lay["fixtures"], "zones": lay["zones"]})
    job.step(5, "done", "2안 렌더 완료")
    job.step(6, "done", "같은 시점 · 같은 조명으로 비교")
    p = app.store.get(pid)
    p["alternatives"] = {"job": job.id, "created": _now(), "items": alts, "base_rev": base.get("rev")}
    app.store.save(p)
    job.result = {"alternatives": [{k: a[k] for k in ("id", "file", "label")} for a in alts]}
