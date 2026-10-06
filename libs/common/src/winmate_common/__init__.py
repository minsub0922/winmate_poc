"""Winmate 서비스 공통 라이브러리.

모듈
- env       환경 변수 · 저장소 루트 · 공통 설정(settings())
- registry  config/services.yaml (포트 · consumes · owns)
- app       create_app(): FastAPI 팩토리(요청 맥락 · 내부 토큰 · 오류 형식 · /healthz)
- client    ServiceClient: 게이트웨이 경유 + 계약 검증 서비스 호출
- contracts OpenAPI 계약 검증기
- errors    ApiError · 공통 오류 형식
- jobs      Redis 잡 큐 · 이벤트 · 취소 · 입력 · 메모 · 예약 · Worker
- graph     run_graph(): LangGraph 를 잡으로 실행(체크포인트 · interrupt)
- store     DocStore: 서비스별 SQLite 문서 저장소(버전)
- ai        ai-tools 호출 도우미(LLM · I2T · T2I · 웹 검색 · 수집 · 임베딩)
- platform  workspace 색인 · files 저장 도우미
- sse       SSE 응답
- testing   테스트 도우미(fakeredis · in-process 서비스 · 내부 토큰 클라이언트)
"""
__all__ = ["__version__"]
__version__ = "0.1.0"
