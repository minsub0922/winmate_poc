#!/usr/bin/env python3
"""Winmate 공간 조감도 PoC — 실행: python3 run.py  (브라우저 http://127.0.0.1:8710)

옵션
  --port 8710         포트(기본: .env 의 BIRDSEYE_PORT 또는 8710)
  --host 127.0.0.1    다른 PC 에서 보려면 0.0.0.0
  --open              브라우저 자동으로 열기
  --reset-samples     샘플 작업 4개를 처음 상태로 다시 만들기
  --check             환경(.env · KB · Blender · 모델)만 점검하고 끝내기
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import webbrowser
from pathlib import Path

if sys.version_info < (3, 9):
    sys.exit("Python 3.9 이상이 필요해요 (지금 %d.%d)" % sys.version_info[:2])

sys.path.insert(0, str(Path(__file__).resolve().parent))

from birdseye.app import App  # noqa: E402
from birdseye.config import Settings  # noqa: E402
from birdseye.server import install_samples, serve  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Winmate 공간 조감도 PoC")
    ap.add_argument("--port", type=int)
    ap.add_argument("--host")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--reset-samples", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    settings = Settings()
    app = App(settings)
    if a.check:
        for _ in range(100):  # Blender 버전 확인(백그라운드)이 끝날 때까지 잠깐 기다림
            if app._blender is not None:
                break
            time.sleep(0.1)
        print(json.dumps(app.env(), ensure_ascii=False, indent=2))
        return
    ids = install_samples(app, force=a.reset_samples)
    host = a.host or settings.host
    port = a.port or settings.port
    httpd = serve(app, host, port)
    url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '') else host}:{port}"
    env = settings.describe()
    print("Winmate 공간 조감도 PoC")
    print(f"  주소     {url}")
    print(f"  .env     {env['env_file'] or '없음 — 기본값으로 실행(모델 호출 없음)'}")
    print(f"  데이터   {env['data_dir']}")
    print(f"  KB       {env['kb_dir'] or '연결 안 됨 — 내장 제품 22종만 사용(WKB_KB 로 지정)'}")
    print(f"  모델     {env['llm']['provider']} · {env['llm']['model']} · {env['model_mode']} · 키 {'있음' if env['llm']['key_set'] else '없음'}")
    print(f"  샘플     {', '.join(ids)}")
    print("  끝내기   Ctrl+C")
    if a.open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n끝냈어요.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
