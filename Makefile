# Winmate 운영·개발 명령. 자세한 내용은 docs/OPERATIONS.md
SHELL := /bin/bash
ROOT := $(shell pwd)
UV ?= uv
PM2 := $(ROOT)/ops/node_modules/.bin/pm2
ECO := $(ROOT)/ops/pm2/ecosystem.config.cjs
PY := $(ROOT)/.venv/bin/python
SERVICE ?=
port = $(shell $(PY) -c "import yaml;print(yaml.safe_load(open('config/services.yaml'))['services']['$(1)']['port'])")
module = winmate_$(subst -,_,$(1))

.PHONY: help setup py-setup ops-setup web-setup up down restart status logs dev test test-all contracts contracts-check \
        web-dev web-build web-gen e2e e2e-feature typecheck dev-bg dev-stop health kb-doctor clean-data

help:
	@echo "make setup                 # 파이썬·pm2·웹 의존성 설치, 계약·API 타입 생성, 웹 빌드"
	@echo "make up | down | restart | status | logs SERVICE=x"
	@echo "make dev SERVICE=x         # x 만 pm2 에서 빼고 리로드 모드로 실행"
	@echo "make test [SERVICE=x]      # 서비스(또는 전체) 테스트"
	@echo "make contracts [SERVICE=x] # 계약 갱신 + 웹 API 타입 생성"
	@echo "make contracts-check       # 코드와 계약 일치 검사"
	@echo "make web-dev | web-build | e2e | health"

setup: py-setup ops-setup web-setup contracts web-build

py-setup:
	$(UV) sync --all-packages

ops-setup:
	cd ops && npm install --no-audit --no-fund

web-setup:
	cd web && npm install --no-audit --no-fund

up:
	$(PM2) start $(ECO) --update-env
	@echo "→ 게이트웨이: http://localhost:$(call port,gateway)   상태: make health"

down:
	-$(PM2) delete $(ECO)

restart:
	$(PM2) reload $(ECO) --update-env

status:
	$(PM2) ls

logs:
	$(PM2) logs $(SERVICE) --lines 100

dev:
	@test -n "$(SERVICE)" || (echo "SERVICE=<이름> 필요" && exit 1)
	-$(PM2) stop $(SERVICE) >/dev/null 2>&1
	WINMATE_SERVICE=$(SERVICE) $(ROOT)/.venv/bin/uvicorn $(call module,$(SERVICE)).main:app --reload \
	  --reload-dir services/$(SERVICE)/src --reload-dir libs/common/src --port $(call port,$(SERVICE))

# 기능 세션용: 이 서비스 API(리로드) + 워커를 백그라운드로(게이트웨이 · 플랫폼은 pm2 그대로). 끄기: make dev-stop SERVICE=x
dev-bg:
	@test -n "$(SERVICE)" || (echo "SERVICE=<이름> 필요" && exit 1)
	@mkdir -p data/logs data/run
	-@$(MAKE) -s dev-stop SERVICE=$(SERVICE)
	@$(PM2) stop $(SERVICE) $(SERVICE)-worker >/dev/null 2>&1 || true
	@WINMATE_SERVICE=$(SERVICE) setsid nohup $(ROOT)/.venv/bin/uvicorn $(call module,$(SERVICE)).main:app --reload \
	  --reload-dir services/$(SERVICE)/src --reload-dir libs/common/src --host 127.0.0.1 --port $(call port,$(SERVICE)) \
	  > data/logs/dev-$(SERVICE).log 2>&1 & echo $$! > data/run/dev-$(SERVICE).pid
	@WINMATE_SERVICE=$(SERVICE) setsid nohup $(PY) -m $(call module,$(SERVICE)).worker > data/logs/dev-$(SERVICE)-worker.log 2>&1 & \
	  echo $$! > data/run/dev-$(SERVICE)-worker.pid
	@echo "→ $(SERVICE) :$(call port,$(SERVICE)) (게이트웨이 /api/$(SERVICE)/...) 로그 data/logs/dev-$(SERVICE).log · 워커 로그 data/logs/dev-$(SERVICE)-worker.log"

dev-stop:
	@test -n "$(SERVICE)" || (echo "SERVICE=<이름> 필요" && exit 1)
	-@for f in data/run/dev-$(SERVICE).pid data/run/dev-$(SERVICE)-worker.pid; do \
	  if [ -f $$f ]; then kill -- -$$(cat $$f) 2>/dev/null || kill $$(cat $$f) 2>/dev/null; rm -f $$f; fi; done; true

dev-worker:
	@test -n "$(SERVICE)" || (echo "SERVICE=<이름> 필요" && exit 1)
	-$(PM2) stop $(SERVICE)-worker >/dev/null 2>&1
	WINMATE_SERVICE=$(SERVICE) $(PY) -m $(call module,$(SERVICE)).worker

test:
ifeq ($(SERVICE),)
	$(UV) run pytest libs/common services
else
	$(UV) run pytest services/$(SERVICE)
endif

contracts:
	$(UV) run python scripts/contracts.py export $(SERVICE)
	@if [ -d web/node_modules ]; then cd web && npm run gen:api --silent -- $(SERVICE); fi

contracts-check:
	$(UV) run python scripts/contracts.py check

web-dev:
	cd web && npm run dev

web-build:
	cd web && npm run build

web-gen:
	cd web && npm run gen:api

e2e:
	cd web && npx playwright test

# 기능 세션용: 그 기능 e2e 만, 자기 포트의 Vite 개발 서버로(세션끼리 포트 · 빌드 폴더가 겹치지 않게)
e2e-feature:
	@test -n "$(SERVICE)" || (echo "SERVICE=<이름> 필요" && exit 1)
	cd web && if [ -z "$$PLAYWRIGHT_BROWSERS_PATH" ] && [ -d /opt/pw-browsers ]; then export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers; fi; \
	  WM_E2E_SUITE=$(SERVICE) WM_E2E_DEV=1 WM_E2E_PORT=$$($(PY) -c "import yaml;print(yaml.safe_load(open('../config/services.yaml'))['services']['$(SERVICE)']['port']+100)") \
	  npx playwright test e2e/$(SERVICE) --workers=1

typecheck:
	cd web && node scripts/typecheck.mjs $(SERVICE)

health:
	@curl -s http://127.0.0.1:$(call port,gateway)/api/_health | $(PY) -m json.tool

# 이미지 · 사례 검색 · 솔루션이 안 될 때: 파일 · 판 · 검색 · 게이트웨이를 한 번에 점검(services/kb/scripts/kb_doctor.py)
kb-doctor:
	$(PY) services/kb/scripts/kb_doctor.py --gateway http://127.0.0.1:$(call port,gateway)
