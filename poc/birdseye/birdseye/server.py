"""HTTP 서버(표준 라이브러리) — JSON API + 정적 웹 화면."""
from __future__ import annotations

import copy
import datetime as dt
import json
import mimetypes
import re
import shutil
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import exporters as EX
from . import pipeline3d, samples, vision
from .analyze3d import FURN, LIB
from .app import App
from .catalog import CATEGORY_NAMES, MOUNT_NAMES
from .drawing import plan_svg
from .furnish import furnish
from .jobs import Job
from .layout2d import STRATEGY_NAMES, layout_lines, line_strategy, recommend_all
from .rules import Rules
from .suggest import suggest_products
from .scene3d import CAMERAS, LIGHTS, QUALITY
from .validate import apply_ops, autofix, geom, validate
from .zones import order_zones, suggest_zones

WEB = Path(__file__).resolve().parents[1] / "web"
SAMPLE_DIR = Path(__file__).resolve().parents[1] / "samples"
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("image/svg+xml", ".svg")


class ApiError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status
        self.msg = msg


def _rules(p):
    return Rules(p.get("rules_override"))


def new_project(kind: str, body: dict) -> dict:
    if kind == "2d":
        return {"kind": "2d", "title": body.get("title") or "새 2D 조감도", "customer": body.get("customer", ""),
                "proposal": body.get("proposal", ""), "confidential": False,
                "space": {"name": body.get("title") or "새 공간", "space_type": body.get("space_type") or "lobby",
                          "width": 12000, "depth": 9000, "height": 3000,
                          "openings": [{"id": "E1", "kind": "entrance", "wall": "front", "start": 5100, "length": 1800,
                                        "label": "주출입구", "sill": 0, "head": 2400}],
                          "pillars": [], "outlets": [], "source": "manual"},
                "lines": [], "placements": [], "fixtures": [], "zones": [], "notes": [], "ignored": [],
                "step": "space", "status": "in_progress", "version": 1}
    if kind == "3d":
        return {"kind": "3d", "title": body.get("title") or "새 3D 조감도", "customer": body.get("customer", ""),
                "proposal": body.get("proposal", ""), "confidential": False, "linked_2d": None,
                "input": {"text": "", "space_type": body.get("space_type") or "lobby", "moods": [], "products": [],
                          "scale": {"area_pyeong": None, "height": "normal"}, "photos": [], "quality": "standard"},
                "status": "draft", "step": "brief", "renders": []}
    raise ApiError(400, "kind 는 2d 또는 3d")


def summarize(app: App, p: dict) -> dict:
    s = {}
    if p["kind"] == "2d":
        tot = len(p.get("placements", []))
        kinds = len({pl["product"] for pl in p.get("placements", [])})
        s.update(kinds=kinds, total=tot, zones=len(p.get("zones", [])), memos=len(p.get("notes", [])))
        if p.get("placements") or p.get("fixtures"):
            try:
                v = validate(p, app.catalog, _rules(p))
                s["warnings"] = v["summary"]["warnings"]
            except Exception:  # noqa: BLE001
                s["warnings"] = None
    else:
        s.update(renders=len(p.get("renders", [])), concept=(LIB["concepts"].get((p.get("brief") or {}).get("concept"), {}) or {}).get("label"))
    return s


def _mini(app: App, p: dict) -> dict | None:
    """작업 목록 썸네일용 — 벽 · 창 · 기둥 · 제품 · 집기 윤곽(정수 mm)."""
    sp = p.get("space")
    if not sp:
        return None
    try:
        g = geom(p, app.catalog)
    except Exception:  # noqa: BLE001
        g = {"placements": {}, "fixtures": {}}
    ri = lambda poly: [[round(x), round(y)] for x, y in poly]  # noqa: E731
    return {"w": sp["width"], "d": sp["depth"],
            "openings": [[o["wall"], round(o["start"]), round(o["length"]), o["kind"]] for o in sp.get("openings", [])],
            "pillars": [[round(pi["x"]), round(pi["y"]), round(pi["w"]), round(pi["d"])] for pi in sp.get("pillars", [])],
            "items": [[ri(x["poly"]), "f"] for x in g["fixtures"].values()] + [[ri(x["poly"]), "p"] for x in g["placements"].values()]}


def list_item(app: App, p: dict) -> dict:
    d = {k: p.get(k) for k in ("id", "kind", "title", "customer", "proposal", "status", "step", "updated_at", "version",
                               "linked_2d", "summary", "sample")}
    d["space_name"] = (p.get("space") or {}).get("name")
    d["space_type"] = (p.get("space") or {}).get("space_type") or (p.get("input") or {}).get("space_type")
    if p["kind"] == "2d":
        d["mini"] = _mini(app, p)
    else:
        rs = p.get("renders", [])
        best = ([r for r in rs if r.get("variant") == "after" and r.get("camera") == "aerial45" and r.get("lighting") == "day"]
                or [r for r in rs if r.get("variant") == "after" and r.get("lighting") == "day"]
                or [r for r in rs if r.get("variant") == "after"] or rs)
        d["thumb"] = f"/files/{p['id']}/{best[-1]['file']}" if best else None
        d["summary"] = dict(p.get("summary") or {}, renders=len(rs),
                            concept=(LIB["concepts"].get((p.get("brief") or {}).get("concept"), {}) or {}).get("label"))
        d["photo_count"] = len((p.get("input") or {}).get("photos") or [])
        d["has_photo_read"] = bool((p.get("input") or {}).get("photo_read"))
        try:
            d["jobs"] = [j.to_dict()["pct"] for j in app.jobs.active_for(p["id"])]
        except Exception:  # noqa: BLE001
            d["jobs"] = []
    return d


def install_samples(app: App, force: bool = False) -> list[str]:
    ids = []
    cat = app.catalog
    builders = [("2d-sample-lobby", lambda: samples.build_lobby_2d(cat)), ("2d-sample-hospital", lambda: samples.build_hospital_2d(cat)),
                ("3d-sample-lobby", lambda: samples.build_lobby_3d(cat, "2d-sample-lobby")), ("3d-sample-control", lambda: samples.build_control_3d(cat))]
    for pid, fn in builders:
        try:
            app.store.get(pid)
            if not force:
                ids.append(pid)
                continue
            app.store.delete(pid)
        except KeyError:
            pass
        p = fn()
        p["id"] = pid
        p["sample"] = True
        p["summary"] = summarize(app, p)
        # 미리 만든 샘플 렌더(이 PoC 파이프라인 결과)를 붙인다
        pre = SAMPLE_DIR / pid
        if p["kind"] == "3d" and (pre / "sample.json").exists():
            extra = json.loads((pre / "sample.json").read_text(encoding="utf-8"))
            dst = app.store.renders_dir(pid) / "sample"
            dst.mkdir(parents=True, exist_ok=True)
            for f in [*pre.glob("*.png"), *pre.glob("*.jpg")]:
                shutil.copy2(f, dst / f.name)
            p.update(extra)
        app.store.save(p)
        ids.append(pid)
    return ids


class Handler(BaseHTTPRequestHandler):
    app: App = None  # type: ignore
    server_version = "WinmateBirdseyePoC/0.1"

    def log_message(self, fmt, *args):  # 조용히
        pass

    # ── 응답 도우미 ──
    def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def json(self, obj, status=200):
        self._send(status, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"), "application/json; charset=utf-8")

    def file(self, path: Path, download: str | None = None):
        if not path.exists() or not path.is_file():
            raise ApiError(404, "파일 없음")
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        extra = {"Content-Disposition": _disp(download)} if download else None
        self._send(200, path.read_bytes(), ctype, extra)

    def body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        limit = self.app.settings.get_int("UPLOAD_MAX_MB", 50) * 1024 * 1024 * 4
        if n > limit:
            raise ApiError(413, "요청이 너무 커요")
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            raise ApiError(400, "JSON 형식이 아니에요") from None

    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method: str):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        q = {k: v[-1] for k, v in urllib.parse.parse_qs(url.query).items()}
        try:
            for m, pat, fn in ROUTES:
                if m != method:
                    continue
                mm = re.fullmatch(pat, path)
                if mm:
                    return fn(self, q, *mm.groups())
            if method == "GET":
                return self.static(path)
            raise ApiError(404, "없는 주소")
        except ApiError as e:
            self.json({"error": e.msg}, e.status)
        except KeyError as e:
            self.json({"error": f"찾을 수 없어요: {e}"}, 404)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self.json({"error": f"{type(e).__name__}: {e}"}, 500)

    def static(self, path: str):
        if path in ("/", "/index.html"):
            return self.file(WEB / "index.html")
        if path.startswith(("/api/", "/files/")):
            raise ApiError(404, "없는 주소")
        rel = path.lstrip("/")
        p = (WEB / rel).resolve()
        if not str(p).startswith(str(WEB.resolve())):
            raise ApiError(403, "접근 불가")
        if p.is_file():
            return self.file(p)
        return self.file(WEB / "index.html")


def _disp(name: str) -> str:
    q = urllib.parse.quote(name)
    return f"attachment; filename=\"download\"; filename*=UTF-8''{q}"


# ── 라우트 함수 ──

def r_env(h, q):
    h.json(h.app.env())


def _confidential(h, b) -> bool:
    """올린 도면·사진을 기밀로 볼지 — 화면에서 고른 값, 없으면 UPLOAD_DEFAULT_CONFIDENTIAL(기본 true)."""
    if "confidential" in b:
        return bool(b["confidential"])
    if "public" in b:
        return not b["public"]
    return h.app.settings.get_bool("UPLOAD_DEFAULT_CONFIDENTIAL", True)


def r_env_refresh(h, q):
    h.app.blender(refresh=True)
    h.json(h.app.env())


def r_library(h, q):
    rules = Rules()
    h.json({
        "furniture": FURN["types"], "space_types": FURN["space_types"], "materials": {k: LIB[k] for k in LIB if k != "about"},
        "rules": rules.all(), "mounts": MOUNT_NAMES, "categories": CATEGORY_NAMES, "strategies": STRATEGY_NAMES,
        "cameras": CAMERAS, "lights": LIGHTS, "quality": {k: {"label": v["label"], "res": v["res"], "samples": v["samples"]} for k, v in QUALITY.items()},
    })


def r_catalog(h, q):
    h.json({"items": h.app.catalog.search(q.get("q", ""), int(q.get("limit", 30))), "kb": h.app.catalog.kb_available()})


def r_catalog_item(h, q):
    p = h.app.catalog.get(q.get("code", ""))
    if not p:
        raise ApiError(404, "제품 없음")
    h.json(p)


def r_projects(h, q):
    h.json({"items": [list_item(h.app, p) for p in h.app.store.list()]})


def r_project_create(h, q):
    b = h.body()
    p = new_project(b.get("kind"), b)
    p["summary"] = summarize(h.app, p)
    h.json(h.app.store.save(p))


def r_project_get(h, q, pid):
    h.json(h.app.store.get(pid))


def r_project_put(h, q, pid):
    b = h.body()
    p = b.get("project") or b
    old = h.app.store.get(pid)
    p["id"] = pid
    for k in ("created_at", "renders", "brief_history", "alternatives"):
        if k in old and k not in p:
            p[k] = old[k]
    p["summary"] = summarize(h.app, p)
    h.json(h.app.store.save(p, bump=bool(b.get("bump"))))


PATCHABLE = {"title", "customer", "proposal", "input", "linked_2d", "space", "confidential", "step", "status", "rules_override", "export_name"}


def r_project_patch(h, q, pid):
    """일부만 바꾸기 — 3D 작업은 렌더 작업이 같은 파일을 고치므로 전체 덮어쓰기 대신 이것을 쓴다."""
    b = h.body()
    p = h.app.store.get(pid)
    for k, v in (b.get("set") or {}).items():
        if k not in PATCHABLE:
            raise ApiError(400, f"바꿀 수 없는 항목: {k}")
        if k == "input" and isinstance(v, dict):
            p.setdefault("input", {}).update(v)
        elif v is None and k in ("space", "linked_2d"):
            p.pop(k, None) if k == "space" else p.update({k: None})
        else:
            p[k] = v
    p["summary"] = summarize(h.app, p)
    h.json(h.app.store.save(p))


def r_project_delete(h, q, pid):
    h.app.store.delete(pid)
    h.json({"ok": True})


def r_project_dup(h, q, pid):
    p = copy.deepcopy(h.app.store.get(pid))
    for k in ("id", "created_at", "renders", "alternatives", "brief_history", "sample"):
        p.pop(k, None)
    p["title"] = (p.get("title") or "") + " (복제)"
    p["version"] = 1
    if p["kind"] == "3d":
        p["status"] = "draft"
        p["step"] = "brief"
    h.json(h.app.store.save(p))


def r_samples(h, q):
    b = h.body()
    ids = install_samples(h.app, force=bool(b.get("force", True)))
    h.json({"ids": ids})


def r_to3d(h, q, pid):
    p2 = h.app.store.get(pid)
    if p2["kind"] != "2d":
        raise ApiError(400, "2D 작업에서만 만들 수 있어요")
    codes = []
    for l in p2.get("lines", []):
        if (l.get("qty") or 0) > 0 and l["product"] not in codes:
            codes.append(l["product"])
    sp = p2["space"]
    area_py = round(sp["width"] * sp["depth"] / 1e6 / 3.3058)
    p3 = new_project("3d", {"title": p2.get("title"), "customer": p2.get("customer"), "proposal": p2.get("proposal"),
                            "space_type": sp.get("space_type")})
    p3["linked_2d"] = pid
    p3["input"].update(products=codes, scale={"area_pyeong": area_py, "height": "high" if sp["height"] >= 4000 else "normal"})
    p3["space"] = copy.deepcopy(sp)
    p3["summary"] = summarize(h.app, p3)
    h.json(h.app.store.save(p3))


# 2D 계산(저장하지 않음 — 화면이 들고 있는 작업 사본으로 계산)

def _proj(h):
    b = h.body()
    p = b.get("project")
    if not p or p.get("kind") != "2d":
        raise ApiError(400, "project(2d)가 필요해요")
    return b, p


def r_2d_recommend(h, q):
    b, p = _proj(h)
    recs = recommend_all(p, h.app.catalog, _rules(p))
    h.json({"recs": recs})


def r_2d_layout(h, q):
    b, p = _proj(h)
    rules = _rules(p)
    cat = h.app.catalog
    regen = b.get("regenerate")
    for line in p.get("lines", []):
        if line.get("qty") is None:
            line["qty"] = recommend_all({**p, "lines": [line]}, cat, rules)[line["id"]]["qty_rec"] or 1
    layout_lines(p, cat, rules, set(regen) if regen is not None else None)
    log = None
    if b.get("fixtures") == "suggest" or (b.get("fixtures") == "auto" and not p.get("fixtures")):
        fx, log = furnish(p, cat, rules, mode="2d")
        p["fixtures"] = fx
    if b.get("zones") == "suggest" or (b.get("zones") == "auto" and not p.get("zones")):
        st = {l["id"]: line_strategy(p, l, cat) for l in p.get("lines", [])}
        p["zones"] = suggest_zones(p, cat, st)
    v = validate(p, cat, rules)
    h.json({"project": p, "validation": v, "furnish_log": log})


def r_2d_validate(h, q):
    b, p = _proj(h)
    h.json(validate(p, h.app.catalog, _rules(p)))


def r_2d_fix(h, q):
    b, p = _proj(h)
    rules = _rules(p)
    v = validate(p, h.app.catalog, rules)
    w = next((w for w in v["warnings"] if w["id"] == b.get("warning_id")), None)
    if not w:
        raise ApiError(404, "그 경고가 이제 없어요")
    fixes = [w.get("fix")] + list(w.get("alt_fixes") or [])
    idx = int(b.get("alt") or 0)
    fx = fixes[idx] if idx < len(fixes) else None
    if not fx:
        raise ApiError(400, "자동으로 고칠 방법이 없어요")
    log = apply_ops(p, fx["ops"])
    h.json({"project": p, "validation": validate(p, h.app.catalog, rules), "log": log, "fix": fx["label"]})


def r_2d_autofix(h, q):
    b, p = _proj(h)
    rules = _rules(p)
    p2, log = autofix(p, h.app.catalog, rules, b.get("ids"))
    h.json({"project": p2, "validation": validate(p2, h.app.catalog, rules), "log": log})


def r_2d_fixtures(h, q):
    b, p = _proj(h)
    fx, log = furnish(p, h.app.catalog, _rules(p), mode="2d")
    h.json({"fixtures": fx, "log": log})


def r_2d_zones(h, q):
    b, p = _proj(h)
    if b.get("mode") == "order":  # 지금 존을 입구에서 가까운 순(동선 순서)으로 다시 번호
        h.json({"zones": order_zones(p, [dict(z) for z in p.get("zones", [])])})
        return
    st = {l["id"]: line_strategy(p, l, h.app.catalog) for l in p.get("lines", [])}
    h.json({"zones": suggest_zones(p, h.app.catalog, st)})


def r_2d_nl(h, q):
    b, p = _proj(h)
    res = vision.nl_edit(h.app.llm, p, h.app.catalog, b.get("text", ""))
    log = vision.apply_nl_ops(p, res["ops"])
    h.json({"project": p, "reply": res["reply"], "ops": res["ops"], "log": log, "source": res.get("source"),
            "validation": validate(p, h.app.catalog, _rules(p))})


def r_2d_suggest(h, q):
    b, p = _proj(h)
    h.json({"items": suggest_products(p, h.app.catalog, _rules(p), b.get("skip") or [], int(b.get("limit") or 1))})


def r_2d_zone_points(h, q):
    b, p = _proj(h)
    res = vision.zone_points(h.app.llm, p, h.app.catalog, b.get("text", ""))
    by_no = {z["no"]: z for z in res["zones"]}
    for z in p.get("zones", []):
        if z.get("no") in by_no:
            z["name"] = by_no[z["no"]]["name"]
            z["point"] = by_no[z["no"]]["point"]
    h.json({"project": p, "reply": res["reply"], "source": res.get("source")})


def r_2d_plan(h, q):
    b = h.body()
    if not b.get("image"):
        raise ApiError(400, "도면 이미지가 없어요")
    res = vision.recognize_plan(h.app.i2t, b["image"], confidential=_confidential(h, b))
    h.json(res)


def _saved2d(h, pid):
    p = h.app.store.get(pid)
    if p["kind"] != "2d":
        raise ApiError(400, "2D 작업이 아니에요")
    return p, validate(p, h.app.catalog, _rules(p))


def r_drawing(h, q, pid):
    p, v = _saved2d(h, pid)
    layers = q.get("layers")
    layers = tuple(x for x in layers.split(",") if x) if layers is not None else None
    svg = plan_svg(p, h.app.catalog, q.get("kind", "plan"), q.get("paper", "A3"), layers, v)
    extra = {"Content-Disposition": _disp(q["download"])} if q.get("download") else None
    h._send(200, svg.encode("utf-8"), "image/svg+xml; charset=utf-8", extra)


def r_qty_json(h, q, pid):
    p, v = _saved2d(h, pid)
    rows = EX.qty_rows(p, h.app.catalog)
    fx: dict[str, dict] = {}
    for f in p.get("fixtures", []):
        try:
            lab = h.app.catalog.furniture_type(f["type"])["label"]
        except KeyError:
            lab = f.get("label") or f["type"]
        fx.setdefault(f["type"], {"type": f["type"], "label": lab, "count": 0})["count"] += 1
    h.json({"rows": rows, "fixtures": list(fx.values()), "total": sum(r["qty"] for r in rows), "kinds": len(rows),
            "validation": {"summary": v["summary"], "warnings": v["warnings"]}})


def r_qty_xlsx(h, q, pid):
    p, v = _saved2d(h, pid)
    data = EX.qty_workbook(p, h.app.catalog, v, q.get("fixtures", "1") == "1")
    h._send(200, data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            {"Content-Disposition": _disp(f"{p['title']}_수량표.xlsx")})


def r_qty_csv(h, q, pid):
    p, v = _saved2d(h, pid)
    h._send(200, EX.qty_csv(p, h.app.catalog), "text/csv; charset=utf-8", {"Content-Disposition": _disp(f"{p['title']}_수량표.csv")})


def r_dxf(h, q, pid):
    p, v = _saved2d(h, pid)
    h._send(200, EX.to_dxf(p, h.app.catalog, v), "application/dxf", {"Content-Disposition": _disp(f"{p['title']}.dxf")})


def r_payload(h, q, pid):
    p, v = _saved2d(h, pid)
    h.json(EX.proposal_payload(p, h.app.catalog, v))


def r_zip(h, q, pid):
    b = h.body()
    p, v = _saved2d(h, pid)
    items = b.get("items") or ["plan", "zones", "flow", "qty"]
    data = EX.bundle_zip(p, h.app.catalog, items, b.get("paper", "A3"), bool(b.get("include_fixtures", True)), v)
    name = (b.get("filename") or p["title"]).strip() or "birdseye"
    h._send(200, data, "application/zip", {"Content-Disposition": _disp(f"{name}.zip")})


# 3D

def _p3(h, pid):
    p = h.app.store.get(pid)
    if p["kind"] != "3d":
        raise ApiError(400, "3D 작업이 아니에요")
    return p


def _need_blender(h):
    b = h.app.blender()
    if not b.get("kind"):
        raise ApiError(409, b.get("note") or "Blender 없음")


def r_render(h, q, pid):
    b = h.body()
    p = _p3(h, pid)
    _need_blender(h)
    if h.app.jobs.active_for(pid):
        raise ApiError(409, "이 작업에서 이미 렌더가 진행 중이에요")
    mode = b.get("mode", "full")
    if mode in ("cuts", "request") and not p.get("brief"):
        mode = "full"
    quality = b.get("quality") or p["input"].get("quality") or "standard"
    cuts = b.get("cuts") or ([["aerial45", "day", "after"], ["entrance", "day", "after"]] if mode == "full" else [["aerial45", "day", "after"]])
    for c in cuts:
        if c[0] not in CAMERAS or c[1] not in LIGHTS or c[2] not in ("after", "before"):
            raise ApiError(400, f"컷 설정이 이상해요: {c}")
    job = Job("render", pid, {"full": "3D 조감도 만들기", "cuts": "컷 추가", "request": "한 줄 요청 반영"}.get(mode, mode))
    job.result = {"mode": mode, "cuts": cuts, "quality": quality}
    p["status"] = "building"
    p["step"] = "build"
    p["last_job"] = job.id
    h.app.store.save(p)
    h.app.jobs.submit(job, pipeline3d.run_render, h.app, pid, mode, cuts, quality, b.get("text"))
    h.json(job.to_dict())


def r_alternatives(h, q, pid):
    b = h.body()
    _p3(h, pid)
    _need_blender(h)
    if h.app.jobs.active_for(pid):
        raise ApiError(409, "이 작업에서 이미 렌더가 진행 중이에요")
    job = Job("alternatives", pid, "다른 안 2개")
    h.app.jobs.submit(job, pipeline3d.run_alternatives, h.app, pid, b.get("quality", "draft"))
    h.json(job.to_dict())


def r_alt_pick(h, q, pid, alt):
    p = _p3(h, pid)
    alts = (p.get("alternatives") or {}).get("items", [])
    a = next((x for x in alts if x["id"] == alt), None)
    if not a:
        raise ApiError(404, "그 안이 없어요")
    br = copy.deepcopy(a["brief"])
    br["meta"] = dict(br.get("meta", {}), mode="alternative_pick")
    pipeline3d._save_brief(p, br, f"다른 안 선택: {a['label']}")
    p["layout"] = dict(a.get("layout", {}), brief_rev=p["brief"]["rev"], space_basis=(p.get("layout") or {}).get("space_basis"))
    p.setdefault("renders", []).append({
        "id": f"{alt}-{p['alternatives']['job']}", "job": p["alternatives"]["job"], "cut": "aerial45_day_after", "camera": "aerial45",
        "lighting": "day", "variant": "after", "file": a["file"], "res": a.get("res"), "label": f"조감 45° · 주간 · {a['label']}",
        "zones": a.get("zones", []), "visibility": [], "brief_rev": p["brief"]["rev"], "quality": "draft",
        "created": dt.datetime.now().isoformat(timespec="seconds")})
    h.json(h.app.store.save(p))


def r_job(h, q, jid):
    j = h.app.jobs.get(jid)
    if not j:
        raise ApiError(404, "작업 없음(서버를 다시 켰다면 사라져요)")
    h.json(j.to_dict())


def r_job_cancel(h, q, jid):
    h.json({"ok": h.app.jobs.cancel(jid)})


def r_project_jobs(h, q, pid):
    h.json({"items": [j.to_dict() for j in h.app.jobs.active_for(pid)]})


def r_photos(h, q):
    b = h.body()
    imgs = b.get("images") or []
    res = vision.read_photos(h.app.i2t, imgs, b.get("text", ""), confidential=_confidential(h, b))
    pid = b.get("project_id")
    if pid and res.get("ok"):
        p = _p3(h, pid)
        inp = p.setdefault("input", {})
        est = res.get("estimate", {})
        bad = [x for x in res.get("photos", []) if not x.get("ok")]
        inp["photo_read"] = {"basis": f"현장 사진 {len(imgs)}장 기준 · {res.get('source')}", "structure": res.get("structure", []),
                             "mood": res.get("mood", []), "finishes": res.get("finishes", {}), "estimate": est,
                             "photos": res.get("photos", []),
                             "needs": [f"사진 {x.get('index', 0) + 1}: {x.get('issue') or '다시 찍으면 좋아요'}" for x in bad][:3]}
        if b.get("text"):
            inp["photo_text"] = b["text"]
        if est.get("width_mm_est") and est.get("depth_mm_est") and not p.get("linked_2d"):
            from .scene3d import estimate_space
            W, D = est["width_mm_est"], est["depth_mm_est"]
            Hh = est.get("height_mm_est") or 3000
            sp, _ = estimate_space({**inp, "scale": {"area_pyeong": round(W * D / 1e6 / 3.3058), "height": "normal"}})
            sp.update(width=W, depth=D, height=Hh, source="photos", estimated=True)
            p["space"] = sp
            inp["scale"] = {"area_pyeong": round(W * D / 1e6 / 3.3058), "height": "high" if Hh >= 4000 else ("low" if Hh < 2700 else "normal")}
        p["status"] = "draft"
        h.app.store.save(p)
        res["project"] = p
    h.json(res)


def r_files(h, q, pid, rel):
    base = h.app.store.dir(pid).resolve()
    p = (base / rel).resolve()
    if not str(p).startswith(str(base)) or "renders" not in p.relative_to(base).parts[:1]:
        raise ApiError(403, "접근 불가")
    h.file(p, q.get("download"))


ROUTES = [
    ("GET", r"/api/env", r_env), ("POST", r"/api/env/refresh", r_env_refresh), ("GET", r"/api/library", r_library),
    ("GET", r"/api/catalog", r_catalog), ("GET", r"/api/catalog/item", r_catalog_item),
    ("GET", r"/api/projects", r_projects), ("POST", r"/api/projects", r_project_create),
    ("GET", r"/api/projects/([\w-]+)", r_project_get), ("PUT", r"/api/projects/([\w-]+)", r_project_put),
    ("DELETE", r"/api/projects/([\w-]+)", r_project_delete), ("POST", r"/api/projects/([\w-]+)/patch", r_project_patch), ("POST", r"/api/projects/([\w-]+)/duplicate", r_project_dup),
    ("POST", r"/api/samples", r_samples), ("POST", r"/api/projects/([\w-]+)/to3d", r_to3d),
    ("POST", r"/api/2d/recommend", r_2d_recommend), ("POST", r"/api/2d/layout", r_2d_layout),
    ("POST", r"/api/2d/validate", r_2d_validate), ("POST", r"/api/2d/fix", r_2d_fix), ("POST", r"/api/2d/autofix", r_2d_autofix),
    ("POST", r"/api/2d/fixtures", r_2d_fixtures), ("POST", r"/api/2d/zones", r_2d_zones), ("POST", r"/api/2d/nl", r_2d_nl),
    ("POST", r"/api/2d/plan", r_2d_plan), ("POST", r"/api/2d/suggest", r_2d_suggest),
    ("POST", r"/api/2d/zone_points", r_2d_zone_points),
    ("GET", r"/api/projects/([\w-]+)/drawing\.svg", r_drawing), ("GET", r"/api/projects/([\w-]+)/qty\.xlsx", r_qty_xlsx),
    ("GET", r"/api/projects/([\w-]+)/qty\.json", r_qty_json),
    ("GET", r"/api/projects/([\w-]+)/qty\.csv", r_qty_csv), ("GET", r"/api/projects/([\w-]+)/layout\.dxf", r_dxf),
    ("GET", r"/api/projects/([\w-]+)/payload\.json", r_payload), ("POST", r"/api/projects/([\w-]+)/export\.zip", r_zip),
    ("POST", r"/api/projects/([\w-]+)/render", r_render), ("POST", r"/api/projects/([\w-]+)/alternatives", r_alternatives),
    ("POST", r"/api/projects/([\w-]+)/alternatives/(alt\d)/pick", r_alt_pick),
    ("GET", r"/api/projects/([\w-]+)/jobs", r_project_jobs),
    ("GET", r"/api/jobs/([\w-]+)", r_job), ("POST", r"/api/jobs/([\w-]+)/cancel", r_job_cancel),
    ("POST", r"/api/3d/photos", r_photos),
    ("GET", r"/files/([\w-]+)/(.+)", r_files),
]


def serve(app: App, host: str, port: int):
    Handler.app = app
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd
