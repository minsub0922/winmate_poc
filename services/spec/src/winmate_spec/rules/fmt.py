"""숫자 · 단위 · 표시명 · 조사 — 결정적 표시 규칙(06-spec §4.16 · §9.2 · §9.3, 셸 G-PRD-1)."""
from __future__ import annotations

import math
import re
from decimal import ROUND_HALF_UP, Decimal

MM_PER_INCH = Decimal("25.4")
LB_PER_KG = Decimal("2.20462")
PENDING_KO = "[확정 필요]"
PENDING_EN = "[To be confirmed]"
SYNC_KO = "[값]"
SYNC_EN = "[Pending]"

GRADES = {(3840, 2160): "UHD", (1920, 1080): "FHD", (2560, 1440): "QHD", (7680, 4320): "8K"}
GRADE_ALIASES = {"UHD": (3840, 2160), "4K": (3840, 2160), "4K UHD": (3840, 2160), "FHD": (1920, 1080), "FULL HD": (1920, 1080),
                 "QHD": (2560, 1440), "8K": (7680, 4320)}


def round1(x: float | Decimal) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def _plain(d: Decimal) -> str:
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def fmt_num(x: float | int | Decimal | None, number_format: str = "1,234.5", *, decimals: int | None = None, group: bool = True) -> str:
    """천 단위는 1,000 이상의 수에만. decimals=None 이면 값 그대로(불필요한 0 없음)."""
    if x is None:
        return ""
    d = Decimal(str(x))
    if decimals is not None:
        d = d.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    s = _plain(d)
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    ip, _, fp = s.partition(".")
    if group and len(ip) > 3:
        ip = f"{int(ip):,}"
    thou, dec = (",", ".") if number_format != "1.234,5" else (".", ",")
    ip = ip.replace(",", "\0").replace("\0", thou)
    out = ip + (dec + fp if fp else "")
    return ("-" if neg else "") + out


def mm_to_in(mm: float) -> Decimal:
    return round1(Decimal(str(mm)) / MM_PER_INCH)


def kg_to_lb(kg: float) -> Decimal:
    return round1(Decimal(str(kg)) * LB_PER_KG)


def inch_from_code(model_code: str | None) -> int | None:
    """모델코드 크기 숫자(LH55QMCEBGCXKR → 55, LH115QHFEBGXKR → 115)."""
    if not model_code:
        return None
    m = re.match(r"^[A-Z]{2}(\d{2,3})[A-Z]", model_code)
    return int(m.group(1)) if m else None


def inch_from_cm(cm: float | None) -> int | None:
    """셸 §9.2: ceil(cm ÷ 2.54 − 0.05)."""
    if cm is None:
        return None
    return int(math.ceil(cm / 2.54 - 0.05))


def grade_label(w: int | None, h: int | None) -> str | None:
    if not w or not h:
        return None
    return GRADES.get((int(w), int(h)))


def parse_resolution(raw: str | None) -> tuple[int, int] | None:
    if not raw:
        return None
    m = re.search(r"(\d[\d,]*)\s*[x×*]\s*(\d[\d,]*)", raw)
    if not m:
        return None
    return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))


def first_number(raw: str | None) -> float | None:
    if not raw:
        return None
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", raw)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def numbers(raw: str | None) -> list[float]:
    if not raw:
        return []
    out = []
    for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", raw):
        try:
            out.append(float(m.group(0).replace(",", "")))
        except ValueError:
            continue
    return out


# ── 표시명 · 계열명(G-PRD-1) ───────────────────────────

_CATEGORY_LABEL = {
    "cat_smart-signage": ("스마트 사이니지", "사이니지", "Smart Signage"),
    "cat_led-signage": ("LED 사이니지", "LED 사이니지", "LED Signage"),
    "cat_interactive-display": ("인터랙티브 디스플레이", "인터랙티브 디스플레이", "Interactive Display"),
    "cat_hotel-tv": ("호텔 TV", "호텔 TV", "Hotel TV"),
}


def category_label(category_id: str | None, fallback: str | None = None) -> str:
    """찾기 카드 계열 앞부분(`스마트 사이니지`). 큐레이션(Q-KB-3) — 없으면 KB 분류 이름."""
    if category_id and category_id in _CATEGORY_LABEL:
        return _CATEGORY_LABEL[category_id][0]
    if category_id and "signage" in category_id:
        return "스마트 사이니지"
    return fallback or "제품"


def category_short(category_id: str | None) -> str:
    """SP2 공통점 문장의 짧은 분류(`사이니지`)."""
    if category_id and category_id in _CATEGORY_LABEL:
        return _CATEGORY_LABEL[category_id][1]
    if category_id and "signage" in category_id:
        return "사이니지"
    return "제품"


def category_en(category_id: str | None) -> str | None:
    if category_id and category_id in _CATEGORY_LABEL:
        return _CATEGORY_LABEL[category_id][2]
    if category_id and "signage" in category_id:
        return "Smart Signage"
    return None


def series_code(series_label: str | None) -> str | None:
    if not series_label:
        return None
    s = re.sub(r"\s*Series$", "", series_label.strip(), flags=re.I)
    return s if re.fullmatch(r"[A-Za-z0-9-]{2,8}", s) else None


def family_en_from_label(label_en: str | None, display_name: str | None) -> str | None:
    """`Smart Signage QM55C` − `QM55C` → `Smart Signage`."""
    if not label_en:
        return None
    if display_name and label_en.endswith(display_name):
        rest = label_en[: -len(display_name)].strip()
        return rest or None
    return None


def display_name_guess(text: str) -> str | None:
    """사용자 글에서 표시명 모양(QM55R · OH55C · WA75D)을 찾는다."""
    m = re.search(r"\b([A-Z]{2}\d{2,3}[A-Z])\b", text.upper())
    return m.group(1) if m else None


def series_size_of(display_or_code: str | None) -> tuple[str, int] | None:
    """`QM55R` → ('QM', 55) · `LH55QMCEBGCXKR` → ('QM', 55)."""
    if not display_or_code:
        return None
    s = display_or_code.upper()
    m = re.match(r"^([A-Z]{2})(\d{2,3})[A-Z]$", s)
    if m:
        return m.group(1), int(m.group(2))
    m = re.match(r"^[A-Z]{2}(\d{2,3})([A-Z]{2})", s)
    if m:
        return m.group(2), int(m.group(1))
    return None


# ── 조사 ───────────────────────────────────────────────

_LATIN_BATCHIM = set("lmnr")  # 영어 끝소리 근사(QM55C → '씨' 받침 없음)
_DIGIT_BATCHIM = {"0": True, "1": True, "2": False, "3": True, "4": False, "5": False, "6": True, "7": True, "8": True, "9": False}


def has_batchim(word: str) -> bool:
    w = word.strip().rstrip(")\"'”’ ")
    if not w:
        return False
    ch = w[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    if ch.isdigit():
        return _DIGIT_BATCHIM[ch]
    if ch.isalpha():
        return ch.lower() in _LATIN_BATCHIM
    return False


def josa(word: str, with_batchim: str, without: str) -> str:
    return with_batchim if has_batchim(word) else without


def safe_filename(s: str) -> str:
    s = re.sub(r'[/\\:*?"<>|\s]+', "_", s.strip())
    return re.sub(r"_+", "_", s).strip("_")
