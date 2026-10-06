#!/usr/bin/env python3
"""KB 이미지 원본 내려받기 — 인터넷이 되는 맥(개발 PC)에서 한 번 돌려 로컬 사본을 만든다.

사내망 PC 는 samsung.com 에 붙지 못한다. kb 서비스는 이미지 바이너리를 로컬 사본(없으면 썸네일)으로만 준다
(`GET /api/kb/v1/images/{id}/file`). 이 스크립트가 그 로컬 사본과 원본 메타(갭 G-IMG-1 · G-IMG-2)를 만든다.

    # 저장소 루트에서(필요: Python 3.11+, Pillow — 저장소 .venv 에 이미 있다)
    uv run python services/kb/scripts/kb_fetch_images.py                 # 전부(우선순위 목록 먼저)
    uv run python services/kb/scripts/kb_fetch_images.py --only-priority # 대시보드 우선 목록(약 3,400장)만
    uv run python services/kb/scripts/kb_fetch_images.py --limit 50      # 시험
    uv run python services/kb/scripts/kb_fetch_images.py --report        # 지금 상태만 요약

- 순서: winmate-kb/dashboard/thumb_select.json 순서(업종 장면 · 사례 사진 · 제품 대표 이미지 …) → 나머지(등급 A → A?C → C → D → E).
- 저장: <출력 폴더>/<asset_id>.webp — 긴 변 1600px 이하로 줄여 WebP(품질 82). 이미 있으면 건너뛴다(이어 받기).
- 원본 메타: <출력 폴더>/_originals.json — {"images": {asset_id: {"original": {width, height, format, bytes}, "stored": {...}, "source_url", "fetched_at"}}}
  kb 서비스가 ImageMeta.original(원본 가로 · 세로 · 형식 · 용량)로 쓴다.
- 실패 목록: <출력 폴더>/_failures.json (다음 실행 때 다시 시도, --skip-failed 면 건너뜀). 요약: _report.json
- 속도: 초당 2건(--rps). 429 · 5xx 는 3번까지 다시 시도(지수 대기). 403 · 404 는 실패로 남긴다.
- 출력 폴더 기본값 = kb 서비스와 같다: $WKB_IMAGE_DIR → ($DATA_DIR 또는 .env 의 DATA_DIR, 기본 ./data)/kb/images
- 사내망으로 옮길 때: 출력 폴더를 통째로 복사해 kb 서비스의 이미지 폴더($WKB_IMAGE_DIR, 기본 data/kb/images)에 둔다.
  파일만 바꿨다면 재시작은 필요 없다(요청마다 파일과 _originals.json 수정 시각을 본다).
  WKB_IMAGE_DIR 값을 새로 바꿨다면 그때만 `pm2 restart kb --update-env`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
GRADE_ORDER = {"A": 0, "A?C": 1, "B": 2, "C": 3, "D": 4, "E": 5}
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36 winmate-kb-fetch/1")
SKIP_MEDIA = {"video", "vector"}


def _dotenv(key: str) -> str | None:
    p = ROOT / ".env"
    if not p.is_file():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            v = line.split("=", 1)[1].strip().strip("'\"")
            return v or None
    return None


def default_out() -> Path:
    v = os.environ.get("WKB_IMAGE_DIR")
    if v:
        return Path(v).expanduser().resolve()
    data = os.environ.get("DATA_DIR") or _dotenv("DATA_DIR") or "./data"
    p = Path(data).expanduser()
    if not p.is_absolute():
        p = ROOT / p
    return (p / "kb" / "images").resolve()


def default_db() -> Path:
    v = os.environ.get("WKB_KB")
    base = Path(v).expanduser() if v else Path(os.environ.get("WKB_ROOT") or ROOT / "winmate-kb") / "kb"
    return (base / "winmate_kb.sqlite").resolve()


def load_assets(db: Path) -> list[dict[str, Any]]:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("SELECT id, url, url_mobile, media_type, grade_hint FROM image_asset ORDER BY rowid")]
    c.close()
    return rows


def priority_ids(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return []
    out, seen = [], set()
    for x in data:
        i = x.get("id") if isinstance(x, dict) else None
        if i and i not in seen:
            seen.add(i)
            out.append(i)
    return out


def order_assets(assets: list[dict[str, Any]], prio: list[str], only_priority: bool) -> list[dict[str, Any]]:
    by = {a["id"]: a for a in assets}
    first = [by[i] for i in prio if i in by]
    if only_priority:
        return first
    seen = {a["id"] for a in first}
    rest = sorted((a for a in assets if a["id"] not in seen), key=lambda a: (GRADE_ORDER.get(a["grade_hint"] or "", 9), a["id"]))
    return first + rest


def norm_url(u: str | None) -> str | None:
    if not u:
        return None
    u = u.strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return "https://www.samsung.com" + u
    return u


def read_json(p: Path, default: Any) -> Any:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(p: Path, obj: Any) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


class RateLimiter:
    def __init__(self, rps: float):
        self.gap = 1.0 / rps if rps > 0 else 0.0
        self.last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        d = self.last + self.gap - now
        if d > 0:
            time.sleep(d)
        self.last = time.monotonic()


def fetch(url: str, limiter: RateLimiter, timeout: float, retries: int = 3) -> tuple[bytes | None, str | None, int | None]:
    """→ (바이트, content-type, 실패 상태). 429 · 5xx · 네트워크 오류는 다시 시도."""
    delay = 2.0
    for attempt in range(retries + 1):
        limiter.wait()
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.samsung.com/",
                                                   "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.headers.get("Content-Type"), None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            return None, None, e.code
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            return None, None, 0
    return None, None, 0


def convert(raw: bytes, max_side: int, quality: int) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(raw)) as im:
        fmt = (im.format or "").upper()
        orig = {"width": int(im.size[0]), "height": int(im.size[1]), "format": "JPG" if fmt == "JPEG" else (fmt or None),
                "bytes": len(raw)}
        im.seek(0)                                       # 움짤(GIF)은 첫 장
        frame = ImageOps.exif_transpose(im) if hasattr(ImageOps, "exif_transpose") else im
        if frame.mode in ("P", "LA", "PA"):
            frame = frame.convert("RGBA")
        elif frame.mode in ("CMYK", "I", "I;16", "F", "1", "L") and frame.mode != "RGBA":
            frame = frame.convert("RGB")
        w, h = frame.size
        s = max(w, h)
        if s > max_side:
            frame = frame.resize((max(1, round(w * max_side / s)), max(1, round(h * max_side / s))), Image.LANCZOS)
        buf = io.BytesIO()
        frame.save(buf, "WEBP", quality=quality, method=4)
        data = buf.getvalue()
        stored = {"width": frame.size[0], "height": frame.size[1], "format": "WEBP", "bytes": len(data)}
    return data, orig, stored


def human(n: float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:,.1f} {u}"
        n /= 1024
    return f"{n:,.1f} TB"


def summarize(out: Path, assets: list[dict[str, Any]]) -> dict[str, Any]:
    meta = read_json(out / "_originals.json", {}).get("images") or {}
    fails = read_json(out / "_failures.json", {}) or {}
    have = {p.stem for p in out.glob("img_*.webp")} if out.is_dir() else set()
    stored_bytes = sum((out / f"{i}.webp").stat().st_size for i in have)
    return {"total_assets": len(assets), "downloaded": len(have), "with_original_meta": len(meta),
            "failed": len(fails), "remaining": len([a for a in assets if a["id"] not in have and a["id"] not in fails
                                                     and (a["media_type"] or "image") not in SKIP_MEDIA]),
            "skipped_media": len([a for a in assets if (a["media_type"] or "image") in SKIP_MEDIA]),
            "stored_bytes": stored_bytes, "stored_human": human(stored_bytes),
            "original_bytes": sum((m.get("original") or {}).get("bytes") or 0 for m in meta.values()),
            "failures_by_status": _count(str(f.get("status")) for f in fails.values())}


def _count(xs: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="KB 이미지 원본 → 로컬 WebP 사본(긴 변 1600) + 원본 메타 사이드카")
    ap.add_argument("--db", type=Path, default=default_db())
    ap.add_argument("--out", type=Path, default=default_out())
    ap.add_argument("--priority", type=Path, default=ROOT / "winmate-kb" / "dashboard" / "thumb_select.json")
    ap.add_argument("--only-priority", action="store_true", help="우선 목록(thumb_select.json)만")
    ap.add_argument("--ids", help="쉼표로 구분한 asset id 만")
    ap.add_argument("--limit", type=int, default=0, help="이번 실행에서 내려받을 최대 수(0 = 제한 없음)")
    ap.add_argument("--max-side", type=int, default=1600)
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--rps", type=float, default=2.0, help="초당 요청 수(기본 2)")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--skip-failed", action="store_true", help="이전에 실패한 것은 다시 시도하지 않음")
    ap.add_argument("--dry-run", action="store_true", help="받을 목록만 보여 준다")
    ap.add_argument("--report", action="store_true", help="지금 상태만 요약")
    a = ap.parse_args()

    if not a.db.is_file():
        print(f"지식 DB 가 없습니다: {a.db}", file=sys.stderr)
        return 2
    out: Path = a.out
    out.mkdir(parents=True, exist_ok=True)
    assets = load_assets(a.db)
    if a.report:
        print(json.dumps(summarize(out, assets), ensure_ascii=False, indent=1))
        return 0
    todo = order_assets(assets, priority_ids(a.priority), a.only_priority)
    if a.ids:
        want = {x.strip() for x in a.ids.split(",") if x.strip()}
        todo = [x for x in todo if x["id"] in want]
    meta_doc = read_json(out / "_originals.json", {"version": 1, "images": {}})
    meta: dict[str, Any] = meta_doc.setdefault("images", {})
    fails: dict[str, Any] = read_json(out / "_failures.json", {}) or {}

    queue = []
    skipped_existing = skipped_media = skipped_failed = 0
    for x in todo:
        if (x["media_type"] or "image") in SKIP_MEDIA:
            skipped_media += 1
            continue
        if (out / f"{x['id']}.webp").is_file() and x["id"] in meta:
            skipped_existing += 1
            continue
        if a.skip_failed and x["id"] in fails:
            skipped_failed += 1
            continue
        queue.append(x)
    if a.limit:
        queue = queue[:a.limit]
    print(f"대상 {len(todo):,} · 이미 있음 {skipped_existing:,} · 영상/벡터 건너뜀 {skipped_media:,} · 실패 건너뜀 {skipped_failed:,} "
          f"→ 이번에 받을 것 {len(queue):,} (초당 {a.rps}건 ≈ {len(queue) / max(a.rps, 0.01) / 60:,.0f}분)")
    print(f"출력: {out}")
    if a.dry_run:
        for x in queue[:20]:
            print(" ", x["id"], norm_url(x["url"] or x["url_mobile"]))
        return 0

    limiter = RateLimiter(a.rps)
    t0 = time.time()
    done = failed = 0
    bytes_orig = bytes_stored = 0
    try:
        for n, x in enumerate(queue, 1):
            url = norm_url(x["url"] or x["url_mobile"])
            if not url:
                fails[x["id"]] = {"status": "no_url", "url": None, "at": dt.datetime.now(dt.timezone.utc).isoformat()}
                failed += 1
                continue
            raw, ctype, status = fetch(url, limiter, a.timeout)
            if raw is None and x["url_mobile"] and norm_url(x["url_mobile"]) != url:
                url = norm_url(x["url_mobile"]) or url                       # PC 원본이 없으면 모바일 변형
                raw, ctype, status = fetch(url, limiter, a.timeout)
            if raw is None:
                fails[x["id"]] = {"status": status, "url": url, "at": dt.datetime.now(dt.timezone.utc).isoformat()}
                failed += 1
            else:
                try:
                    data, orig, stored = convert(raw, a.max_side, a.quality)
                except Exception as exc:  # noqa: BLE001 — 그림이 아니거나 깨진 파일
                    fails[x["id"]] = {"status": "decode_error", "error": f"{type(exc).__name__}: {exc}", "url": url,
                                      "content_type": ctype, "at": dt.datetime.now(dt.timezone.utc).isoformat()}
                    failed += 1
                else:
                    p = out / f"{x['id']}.webp"
                    tmp = p.with_suffix(".webp.tmp")
                    tmp.write_bytes(data)
                    os.replace(tmp, p)
                    meta[x["id"]] = {"original": orig, "stored": {**stored, "file": p.name}, "source_url": url,
                                     "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat()}
                    fails.pop(x["id"], None)
                    done += 1
                    bytes_orig += orig["bytes"]
                    bytes_stored += stored["bytes"]
            if n % 25 == 0 or n == len(queue):
                meta_doc.update({"version": 1, "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                                 "max_side": a.max_side, "format": "WEBP"})
                write_json(out / "_originals.json", meta_doc)
                write_json(out / "_failures.json", fails)
                el = time.time() - t0
                print(f"  {n:,}/{len(queue):,} 받음 {done:,} 실패 {failed:,} · 원본 {human(bytes_orig)} → 저장 {human(bytes_stored)} · {el / 60:,.1f}분")
    except KeyboardInterrupt:
        print("\n중단 — 지금까지 받은 것은 저장합니다(다시 실행하면 이어서 받음).")
    finally:
        meta_doc.update({"version": 1, "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "max_side": a.max_side, "format": "WEBP"})
        write_json(out / "_originals.json", meta_doc)
        write_json(out / "_failures.json", fails)
        rep = {"run": {"downloaded": done, "failed": failed, "original_bytes": bytes_orig, "stored_bytes": bytes_stored,
                       "seconds": round(time.time() - t0, 1), "finished_at": dt.datetime.now(dt.timezone.utc).isoformat()},
               "state": summarize(out, assets)}
        write_json(out / "_report.json", rep)
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
