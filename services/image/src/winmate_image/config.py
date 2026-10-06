"""image 서비스 설정 — 환경 변수는 부를 때마다 읽는다(테스트에서 바꿔도 바로 반영). 기본값 = 07-image §10.4."""
from __future__ import annotations

import math

from winmate_common import env

SERVICE = "image"
FEATURE = "IMG"          # workspace feature 값(계약 enum)

# ── 보드 수치(§10.1) ─────────────────────────────────────
KINDS = ("space", "background", "scenario", "composite")
KIND_LABEL = {"space": "공간", "background": "배경", "scenario": "시나리오", "composite": "제품 합성"}
KIND_TITLE_SUFFIX = {"space": "시안", "background": "배경 이미지", "scenario": "시나리오 컷", "composite": "벽면 합성"}
STYLES = ("photo", "minimal_3d", "illustration")
STYLE_LABEL = {"photo": "실사 렌더", "minimal_3d": "미니멀 3D", "illustration": "일러스트"}
STYLE_SHORT = {"photo": "실사", "minimal_3d": "3D", "illustration": "일러스트"}
GEN_ASPECTS = ("16:9", "4:3", "1:1")
RENDITION_ASPECTS = ("16:9", "4:3", "1:1", "9:16")
ASPECT_USE = {"16:9": "슬라이드 · 표지", "4:3": "4:3 제안서 템플릿", "1:1": "SNS · 썸네일", "9:16": "세로형 사이니지 · 모바일"}
COUNTS = (2, 4)
ASPECT_KEYS = ("color_light", "composition", "placement", "material")
ASPECT_LABEL = {"color_light": "색감 · 조명", "composition": "구도", "placement": "제품 배치", "material": "소재"}
STRENGTH_LABEL = {"low": "약", "mid": "중", "high": "강"}
MAX_REFERENCES = 3
MAX_QTY = 9
DESC_MAX = 500
COMPOSITE_COUNT = 4
VARIANT_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def worker_concurrency() -> int:
    return max(1, env.get_int("IMAGE_WORKER_CONCURRENCY", 2))


def light_concurrency() -> int:
    """사진 인식 · 참조 분석 · 내보내기 같은 가벼운 잡의 동시 수."""
    return max(1, env.get_int("IMAGE_LIGHT_CONCURRENCY", 2))


def max_running_per_user() -> int:
    return max(1, env.get_int("IMAGE_MAX_RUNNING_PER_USER", 1))


def shot_concurrency() -> int:
    return max(1, env.get_int("IMAGE_SHOT_CONCURRENCY", 2))


def qc_max_retry() -> int:
    return max(0, env.get_int("QC_MAX_RETRY", 1))


def product_match_min() -> float:
    return env.get_float("PRODUCT_MATCH_MIN", 0.6)


def product_aspect_tol() -> float:
    return env.get_float("PRODUCT_ASPECT_TOL", 0.15)


def variant_layout_iou_min() -> float:
    return env.get_float("VARIANT_LAYOUT_IOU_MIN", 0.5)


def global_edit_product_iou_min() -> float:
    return env.get_float("GLOBAL_EDIT_PRODUCT_IOU_MIN", 0.8)


def composite_edge_iou_min() -> float:
    return env.get_float("COMPOSITE_EDGE_IOU_MIN", 0.9)


def feather_px() -> int:
    return env.get_int("FEATHER_PX", 8)


def ring_px() -> int:
    return env.get_int("SEAM_RING_PX", 16)


def dark_luma() -> float:
    return env.get_float("IMAGE_DARK_LUMA", 0.22)


def product_ref_max() -> int:
    return env.get_int("PRODUCT_REF_MAX", 2)


def upscaler() -> str:
    """none | realesrgan_x4v3 (모델 파일이 있어야 한다 — 없으면 none 으로 본다)."""
    v = (env.get("UPSCALER", "none") or "none").lower()
    if v == "realesrgan_x4v3":
        path = env.get("UPSCALER_MODEL_PATH")
        if not path:
            return "none"
        try:
            from pathlib import Path

            if not Path(env.resolve_path(path)).is_file():
                return "none"
            import onnxruntime  # noqa: F401
        except Exception:  # noqa: BLE001
            return "none"
        return v
    return "none"


def prefill_timeout_s() -> float:
    return env.get_float("IMAGE_PREFILL_TIMEOUT_S", 10.0)


def llm_timeout_s() -> float:
    """prefill · 사전 검사의 LLM 제한(prefill 전체 10초 안에서)."""
    return env.get_float("IMAGE_LLM_TIMEOUT_S", 8.0)


def retry_delays() -> list[float]:
    raw = env.get("IMAGE_RETRY_DELAYS", "2,6") or "2,6"
    out = []
    for p in raw.split(","):
        try:
            out.append(max(0.0, float(p)))
        except ValueError:
            continue
    return out or [2.0, 6.0]


def dev_shot_delay_s() -> float:
    """개발용: mock 모델이 너무 빨라 생성 중 화면을 볼 수 없을 때 단계마다 쉰다(기본 0)."""
    return max(0.0, env.get_float("IMAGE_DEV_SHOT_DELAY_S", 0.0))


def default_ema_s() -> float:
    return env.get_float("IMAGE_DEFAULT_SHOT_S", 25.0)


# ── 해상도 사다리(§10.2) ──────────────────────────────────

def parse_aspect(aspect: str) -> tuple[int, int]:
    try:
        a, b = aspect.replace(" ", "").split(":")
        x, y = int(a), int(b)
        if x > 0 and y > 0:
            return x, y
    except (ValueError, AttributeError):
        pass
    return 16, 9


def ratio_of(aspect: str) -> float:
    x, y = parse_aspect(aspect)
    return x / y


def _even(v: float) -> int:
    n = int(round(v))
    return n if n % 2 == 0 else n + 1


def size_for(aspect: str, kind: str) -> tuple[int, int]:
    """렌디션 크기. native = 긴 변 1024, fhd/uhd/uhd8k = 짧은 변 1080/2160/4320."""
    r = ratio_of(aspect)
    if kind == "native":
        long = env.get_int("T2I_MAX_SIDE_PX", 1024)
        return (long, _even(long / r)) if r >= 1 else (_even(long * r), long)
    short = {"fhd": 1080, "uhd": 2160, "uhd8k": 4320, "thumb": 180}.get(kind, 1080)
    if kind == "thumb":
        return (320, max(1, round(320 / r)))
    if r >= 1:
        return (_even(short * r), short)
    return (short, _even(short / r))


UPSCALE_KIND = {"1x": "fhd", "2x": "uhd", "4x": "uhd8k"}
UPSCALE_LABEL = {"1x": "원본", "2x": "×2", "4x": "×4"}


def nearest_aspect(w: int, h: int, choices: tuple[str, ...] = RENDITION_ASPECTS) -> str:
    r = w / max(1, h)
    return min(choices, key=lambda a: abs(math.log(ratio_of(a) / r)))
