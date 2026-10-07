"""제품 카탈로그 — PoC 시드(seed/products.json) + winmate-kb 실시간 조회(있으면).

사실값(치수·전력·무게·밝기)은 KB 원문에서만 온다. KB 에 없는 값은 비워 두고 `assumed` 에 가정을 적는다.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent / "seed"

_NUM = r"(\d[\d,]*(?:\.\d+)?)"
_DIM_RE = re.compile(_NUM + r"\s*[x×X*]\s*" + _NUM + r"\s*[x×X*]\s*" + _NUM)

# KB subcategory_slug → 배치 전략 분류
SUBCAT_TO_CATEGORY = {
    "outdoor-dual": "window_signage",
    "standalone": "signage",
    "business-tv": "signage",
    "videowall": "videowall",
    "the-wall": "led_allinone",
    "indoor": "led_cabinet",
    "flip": "flip",
    "outdoor": "outdoor_signage",
    "e-paper": "epaper",
    "spatial-signage": "spatial",
    "cooling-single-indoor": "hvac_cassette",
}

CATEGORY_MOUNTS = {
    "window_signage": ["ceiling_hang", "floor_stand"],
    "signage": ["wall", "pillar_wrap", "floor_stand", "ceiling_hang"],
    "signage_large": ["wall", "floor_stand"],
    "led_allinone": ["wall", "floor_stand"],
    "led_cabinet": ["wall"],
    "flip": ["stand", "wall"],
    "videowall": ["wall"],
    "outdoor_signage": ["floor_stand", "wall"],
    "spatial": ["floor_lean", "wall"],
    "epaper": ["wall"],
    "hvac_cassette": ["ceiling"],
    "device": ["floor_stand", "wall"],
}

CATEGORY_NAMES = {
    "window_signage": "창면 사이니지",
    "signage": "사이니지",
    "signage_large": "대형 사이니지",
    "led_allinone": "LED 올인원",
    "led_cabinet": "LED 캐비닛",
    "flip": "전자칠판",
    "videowall": "비디오월",
    "outdoor_signage": "실외 사이니지",
    "spatial": "스페이셜 사이니지",
    "epaper": "E Paper",
    "hvac_cassette": "천장형 냉난방기",
    "device": "기타 제품",
}

MOUNT_NAMES = {
    "ceiling_hang": "천장 행잉",
    "floor_stand": "바닥 스탠드",
    "wall": "벽부형",
    "pillar_wrap": "기둥 랩핑",
    "stand": "이동형 스탠드",
    "floor_lean": "기대어 세움",
    "ceiling": "천장 매립",
}


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def parse_dims(raw: str):
    """'1253.4 x 724.2 x 54.5 mm' → dict(w,h,d) (mm). 단위가 cm 면 환산."""
    if not raw:
        return None
    m = _DIM_RE.search(raw)
    if not m:
        return None
    a, b, c = (_num(g) for g in m.groups())
    if re.search(r"\bcm\b", raw) and not re.search(r"\bmm\b", raw):
        a, b, c = a * 10, b * 10, c * 10
    return {"w": a, "h": b, "d": c}


def _first_num(raw: str):
    m = re.search(_NUM, raw or "")
    return _num(m.group(1)) if m else None


def parse_spec_fields(specs: dict) -> dict:
    """KB spec 원문 묶음({"그룹|속성": 값}) → 정규화된 필드 + 쓴 원문."""
    out: dict = {"raw": {}}

    def take(key, label, val):
        out["raw"][key] = f"{label} = {val}"

    for label, val in specs.items():
        grp, _, attr = label.partition("|")
        a = attr.replace(" ", "")
        if "포장" in a:
            continue
        if ("가로x높이x깊이" in a or "W×H×D" in attr or "WxHxD" in attr or "치수" in a) and "실외기" not in grp:
            dims = parse_dims(val)
            if not dims:
                continue
            if "판넬" in a:
                out["panel_dims"] = dims
                take("panel_dims", label, val)
            elif grp == "실내기" or "본체" in a or "dims" not in out:
                if "dims" in out and grp != "실내기":
                    continue
                out["dims"] = dims
                take("dims", label, val)
        elif "대각선" in a:
            out["diag_cm"] = _first_num(val)
            take("diag_cm", label, val)
        elif a.startswith("밝기"):
            out["brightness_nit"] = _first_num(val)
            take("brightness_nit", label, val)
        elif "소비전력(OnMode)" in a or (a == "소비전력(Typical)" and "power_w" not in out):
            out["power_w"] = _first_num(val)
            take("power_w", label, val)
        elif a == "제품무게":
            out["weight_kg"] = _first_num(val)
            take("weight_kg", label, val)
        elif "픽셀피치" in a:
            v = _first_num(val)
            if v is not None and ("㎛" in val or v > 50):
                v = v / 1000.0
            out["pixel_pitch_mm"] = v
            take("pixel_pitch_mm", label, val)
        elif a in ("해상도", "화면해상도"):
            m = re.search(r"(\d[\d,]*)\s*[x×]\s*(\d[\d,]*)", val)
            if m:
                out["resolution"] = f"{_num(m.group(1)):.0f}×{_num(m.group(2)):.0f}"
                take("resolution", label, val)
        elif "시야각" in a:
            out["view_angle_deg"] = _first_num(val)
            take("view_angle_deg", label, val)
        elif "제품사용시간" in a:
            out["operation"] = val.strip()
            take("operation", label, val)
        elif "베젤두께" in a:
            out["bezel_mm"] = _first_num(val)
            take("bezel_mm", label, val)
        elif a.startswith("냉방성능(최소/정격/최대)[kW]") or a.startswith("정격냉방"):
            nums = [_num(x) for x in re.findall(_NUM, val)]
            if nums:
                out["cooling_kw"] = nums[1] if len(nums) >= 3 else nums[0]
                take("cooling_kw", label, val)
        elif a.startswith("난방성능(최소/정격/최대)[kW]") or a.startswith("정격난방"):
            nums = [_num(x) for x in re.findall(_NUM, val)]
            if nums:
                out["heating_kw"] = nums[1] if len(nums) >= 3 else nums[0]
                take("heating_kw", label, val)
        elif "출시년월" in a:
            out["release"] = val.strip()
            take("release", label, val)
    if "dims" in out and "panel_dims" in out:
        out["body_dims"] = out["dims"]
    return out


class Catalog:
    """시드 + (선택) KB 실시간 조회. 스레드 안전하게 KB 커넥션은 호출마다 연다."""

    def __init__(self, kb_dir: Path | None = None):
        doc = json.loads((SEED_DIR / "products.json").read_text(encoding="utf-8"))
        self.seed = {p["code"]: p for p in doc["products"]}
        self.kb_dir = Path(kb_dir) if kb_dir else None
        self._kb_cache: dict[str, dict] = {}
        self._lock = threading.Lock()
        self.furniture = json.loads((SEED_DIR / "furniture.json").read_text(encoding="utf-8"))

    # ── KB ──
    @property
    def kb_path(self) -> Path | None:
        if self.kb_dir and (self.kb_dir / "winmate_kb.sqlite").exists():
            return self.kb_dir / "winmate_kb.sqlite"
        return None

    def kb_available(self) -> bool:
        return self.kb_path is not None

    def _kb(self):
        c = sqlite3.connect(f"file:{self.kb_path}?mode=ro", uri=True, check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    def _kb_product(self, code: str) -> dict | None:
        if not self.kb_available():
            return None
        with self._lock:
            if code in self._kb_cache:
                return self._kb_cache[code]
        c = self._kb()
        try:
            m = c.execute("select * from product_model where model_code=?", (code,)).fetchone()
            if not m:
                return None
            f = c.execute("select * from product_family where id=?", (m["family_id"],)).fetchone()
            rows = c.execute("select group_name, attr_name, value_raw from spec_value where model_id=?", (m["id"],)).fetchall()
            specs = {f"{r['group_name']}|{r['attr_name']}": r["value_raw"] for r in rows}
            fields = parse_spec_fields(specs)
            if not fields.get("dims"):
                return None
            cat = SUBCAT_TO_CATEGORY.get(f["subcategory_slug"] or "", "device")
            if cat == "hvac_cassette" and not fields.get("panel_dims"):
                cat = "device"
            dims = fields["dims"]
            w, h, d = dims["w"], dims["h"], dims["d"]
            if cat == "hvac_cassette":
                p = fields["panel_dims"]
                w, d, h = p["w"], p["d"], p["h"]
            name = f"{f['name_ko']} {m['option_value'] or ''}".strip()
            prod = {
                "code": code, "short": code[:10], "name": re.sub(r"\s+", " ", name), "family": f["name_ko"],
                "category": cat, "mounts": CATEGORY_MOUNTS.get(cat, ["floor_stand"]),
                "default_mount": CATEGORY_MOUNTS.get(cat, ["floor_stand"])[0],
                "w": w, "h": h, "d": d,
                "kb": {"model_id": m["id"], "family_id": f["id"], "category_id": f["category_id"], "subcategory": f["subcategory_slug"]},
                "source": {"url": f["detail_url"], "page": f["detail_url"], "extracted_from": "winmate-kb (실시간 조회)",
                           "fields": fields["raw"]},
                "content": "brand" if cat not in ("hvac_cassette", "device") else None,
                "double_sided": False, "assumed": {"short": "약칭 없음 — 모델 코드 앞부분 표시"}, "from_kb": True,
            }
            for k in ("power_w", "weight_kg", "brightness_nit", "pixel_pitch_mm", "resolution", "diag_cm",
                      "view_angle_deg", "operation", "bezel_mm", "cooling_kw", "heating_kw", "release"):
                if fields.get(k) is not None:
                    prod[k] = fields[k]
            with self._lock:
                self._kb_cache[code] = prod
            return prod
        finally:
            c.close()

    # ── 공개 API ──
    def get(self, code: str) -> dict | None:
        return self.seed.get(code) or self._kb_product(code)

    def require(self, code: str) -> dict:
        p = self.get(code)
        if not p:
            raise KeyError(f"제품을 찾을 수 없어요: {code}")
        return p

    def list_seed(self) -> list[dict]:
        return list(self.seed.values())

    def search(self, q: str, limit: int = 30) -> list[dict]:
        """시드 + KB 이름·모델 코드 검색. KB 결과는 치수가 있는 모델만."""
        ql = (q or "").strip().lower()
        res, seen = [], set()
        for p in self.seed.values():
            hay = f"{p['code']} {p['short']} {p['name']} {CATEGORY_NAMES.get(p['category'], '')}".lower()
            if not ql or all(t in hay for t in ql.split()):
                res.append(p)
                seen.add(p["code"])
        if ql and self.kb_available():
            c = self._kb()
            try:
                like = f"%{q.strip()}%"
                rows = c.execute(
                    """select m.model_code from product_model m join product_family f on f.id=m.family_id
                       where (m.model_code like ? or f.name_ko like ? or f.marketing_model like ?)
                       limit 80""", (like, like, like)).fetchall()
            finally:
                c.close()
            for r in rows:
                code = r["model_code"]
                if code in seen:
                    continue
                p = self._kb_product(code)
                if p:
                    res.append(p)
                    seen.add(code)
                if len(res) >= limit:
                    break
        return res[:limit]

    def furniture_type(self, t: str) -> dict:
        for f in self.furniture["types"]:
            if f["type"] == t:
                return f
        raise KeyError(t)


def screen_size(prod: dict, portrait: bool = False) -> tuple[float, float]:
    """설치 방향을 반영한 (화면 가로, 화면 세로) mm — 제품 외형 기준. portrait=True 면 긴 변이 세로."""
    if prod["category"] == "hvac_cassette":
        return prod["w"], prod["d"]
    lo, hi = sorted((prod["w"], prod["h"]))
    return (lo, hi) if portrait else (hi, lo)


def native_portrait(prod: dict) -> bool:
    return prod["category"] != "hvac_cassette" and prod["h"] > prod["w"]


def footprint_depth(prod: dict, mount: str) -> float:
    """바닥 평면에서 차지하는 깊이(mm). 스탠드·기대어 세우는 설치는 가정값."""
    if mount == "stand":
        return 700.0
    if mount == "floor_lean":
        return 450.0
    if mount == "floor_stand":
        return max(prod["d"], 450.0)
    if prod["category"] == "hvac_cassette":
        return prod["d"]
    return prod["d"]
