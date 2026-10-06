"""kb 서비스 경로·설정.

환경 변수(모두 선택)
- WKB_ROOT        winmate-kb 폴더(기본 <저장소>/winmate-kb). build/query.py · seed · dashboard 가 여기 있다.
- WKB_KB          지식 DB 폴더(기본 <WKB_ROOT>/kb). winmate_kb.sqlite · models/*.joblib
- WKB_THUMBS_DIR  썸네일 묶음(thumbs_pack*.bin, 'WTHB') 폴더(기본 <WKB_ROOT>/dashboard/build)
- WKB_IMAGE_DIR   원본 이미지 로컬 사본 폴더(기본 <DATA_DIR>/kb/images). scripts/kb_fetch_images.py 가 채운다
- KB_WARMUP       0 이면 시작할 때 미리 데우지 않는다(기본 1)
"""
from __future__ import annotations

from pathlib import Path

from winmate_common import env


def wkb_root() -> Path:
    return env.resolve_path(env.get("WKB_ROOT") or "winmate-kb")


def kb_dir() -> Path:
    v = env.get("WKB_KB")
    return env.resolve_path(v) if v else wkb_root() / "kb"


def db_path() -> Path:
    return kb_dir() / "winmate_kb.sqlite"


def build_dir() -> Path:
    return wkb_root() / "build"


def thumbs_dir() -> Path:
    v = env.get("WKB_THUMBS_DIR")
    return env.resolve_path(v) if v else wkb_root() / "dashboard" / "build"


def thumb_select_path() -> Path:
    return wkb_root() / "dashboard" / "thumb_select.json"


def image_dir() -> Path:
    v = env.get("WKB_IMAGE_DIR")
    if v:
        return env.resolve_path(v)
    return env.settings().data_dir / "kb" / "images"


def image_meta_path() -> Path:
    """원본 메타 사이드카(kb_fetch_images.py 가 쓴다). 있으면 ImageMeta.original 에 쓴다(G-IMG-1)."""
    return image_dir() / "_originals.json"


def warmup_enabled() -> bool:
    return env.get_bool("KB_WARMUP", True)


# 브라우저에 주는 이미지 주소(게이트웨이 경로). 외부 URL 은 절대 내보내지 않는다.
def thumb_url(asset_id: str) -> str:
    return f"/api/kb/v1/images/{asset_id}/thumb"


def file_url(asset_id: str) -> str:
    return f"/api/kb/v1/images/{asset_id}/file"
