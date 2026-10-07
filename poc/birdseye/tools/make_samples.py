"""3D 샘플 렌더 묶기 — 실행 중인 데이터 폴더의 작업(기본 3d-sample-lobby)에서 렌더 · 브리프 · 배치를 samples/<id>/ 로 복사한다.

    python3 tools/make_samples.py [--data DATA_DIR/birdseye] [--id 3d-sample-lobby] [--kb ../winmate-kb/kb]

--kb 를 주면 참고 사례(winmate-kb 공간 배치 이미지)를 그 KB 에서 다시 찾아 넣는다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from birdseye import kbref  # noqa: E402
from birdseye.catalog import Catalog  # noqa: E402
from birdseye.config import Settings  # noqa: E402

KEEP = ("brief", "brief_history", "refs", "layout", "qc", "space")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data")
    ap.add_argument("--id", default="3d-sample-lobby")
    ap.add_argument("--kb")
    ap.add_argument("--only-refs", action="store_true", help="렌더는 그대로 두고 참고 사례만 다시 찾기")
    a = ap.parse_args()
    out = ROOT / "samples" / a.id
    out.mkdir(parents=True, exist_ok=True)
    if a.only_refs:
        extra = json.loads((out / "sample.json").read_text(encoding="utf-8"))
    else:
        data = Path(a.data) if a.data else Settings().data_dir
        p = json.loads((data / "projects" / a.id / "project.json").read_text(encoding="utf-8"))
        rev = (p.get("brief") or {}).get("rev")
        renders = [r for r in p.get("renders", []) if r.get("brief_rev") == rev] or p.get("renders", [])
        seen, keep = set(), []
        for r in reversed(renders):  # 같은 컷은 마지막 것만
            if r["cut"] in seen:
                continue
            seen.add(r["cut"])
            keep.append(r)
        keep.reverse()
        for f in out.glob("*.png"):
            f.unlink()
        rs = []
        for r in keep:
            src = data / "projects" / a.id / r["file"]
            name = Path(r["file"]).name
            shutil.copy2(src, out / name)
            rs.append(dict(r, file=f"renders/sample/{name}", job="sample", id=f"sample-{r['cut']}"))
        extra = {k: p[k] for k in KEEP if k in p}
        extra.update(renders=rs, status="done", step="result")
        extra.pop("alternatives", None)
    if a.kb:
        cat = Catalog(Path(a.kb))
        fams, cats = [], []
        for c in (extra.get("layout") or {}).get("lines", []) or []:
            prod = cat.get(c["product"])
            if prod:
                fams.append(prod["kb"]["family_id"])
                cats.append(prod["kb"]["category_id"])
        st = (extra.get("space") or {}).get("space_type") or "lobby"
        extra["refs"] = kbref.reference_images(Path(a.kb), st, fams, cats, 3)
    (out / "sample.json").write_text(json.dumps(extra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out} — 렌더 {len(extra.get('renders', []))}컷 · 참고 사례 {len((extra.get('refs') or {}).get('images', []))}건")


if __name__ == "__main__":
    main()
