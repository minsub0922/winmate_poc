"""프롬프트(task `pr.<동작>`) — 출력은 JSON 스키마로 강제. 모든 프롬프트는 「사실을 지어내지 않는다」를 첫 규칙으로 둔다."""
from __future__ import annotations

from typing import Any

RULES = (
    "너는 삼성 B2B 제안서 작성 도우미 W 다. 한국어로 쓴다.\n"
    "규칙: (1) 숫자 · 모델명 · 고객명 · 경쟁사명 · 수치는 입력에 있는 것만 쓴다. 입력에 없는 수치는 [00] · [00]% · [0]일 · [00]시간 같은 자리표시로 둔다.\n"
    "(2) 경쟁사는 '경쟁사 A · B · C' 익명 라벨로만 쓴다. (3) '최초 · 유일 · 최고 · 1위 · 보장' 같은 단정은 입력 원문에 있을 때만.\n"
    "(4) 한 문장은 짧게(제목 46자 · 부제 80자 이내). (5) 출력은 주어진 JSON 스키마만."
)

POINT = {"type": "object", "properties": {"title": {"type": "string"}, "body": {"type": "string"}, "kpi": {"type": "string"},
                                          "tag": {"type": "string"}, "after": {"type": "string"}}, "required": ["title"]}
STEP = {"type": "object", "properties": {"when": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}}, "required": ["title"]}
KPI = {"type": "object", "properties": {"label": {"type": "string"}, "value": {"type": "string"}, "unit": {"type": "string"}}, "required": ["label", "value"]}
TABLE = {"type": "object", "properties": {"columns": {"type": "array", "items": {"type": "string"}},
                                          "rows": {"type": "array", "items": {"type": "object", "properties": {
                                              "label": {"type": "string"}, "cells": {"type": "array", "items": {"type": "object", "properties": {
                                                  "text": {"type": "string"}, "mark": {"type": "string"}}, "required": ["text"]}}},
                                              "required": ["label"]}}}, "required": ["columns", "rows"]}

SHEET_DRAFT = {
    "type": "object",
    "properties": {
        "sheet_key": {"type": "string", "description": "요청의 sheet_key 그대로(역할 코드 또는 시트 id)"},
        "title": {"type": "string", "description": "슬라이드 제목 — 이 장의 핵심 메시지 한 문장"},
        "subtitle": {"type": "string"}, "message": {"type": "string"},
        "points": {"type": "array", "items": POINT}, "bullets": {"type": "array", "items": {"type": "string"}},
        "kpis": {"type": "array", "items": KPI}, "steps": {"type": "array", "items": STEP}, "table": TABLE,
        "notes": {"type": "string", "description": "발표자 노트"},
        "signals": {"type": "object", "description": "데이터 모양 신호(km · stakeholders · competitors · criteria · trends …)"},
    },
    "required": ["sheet_key", "title"],
}
SECTION_DRAFT = {"type": "object", "properties": {"sheets": {"type": "array", "items": SHEET_DRAFT}, "summary": {"type": "string"}},
                 "required": ["sheets"]}


def section_draft(*, section_key: str, section_name: str, mode: str, customer: str, project: str, type_name: str,
                  requirements: list[str], sheets: list[dict[str, Any]], memos: list[str], request: str | None, extra: str = "") -> str:
    rq = "\n".join(f"- {x}" for x in requirements) or "- (요구사항 정의서 없음)"
    memo = "\n".join(f"사용자 방향 메모: {m}" for m in memos)
    req = f"\n섹션 수정 요청: {request}" if request else ""
    sh = "\n".join(f"- sheet_key={s['sheet_key']} · 역할 {s['role']}({s['role_name']}) · 시트 「{s['title']}」 · 말하는 것 “{s['msg']}”\n  재료: {s['material']}"
                   for s in sheets)
    return (f"섹션: {section_key} ({section_name}) · 작성 방식: {mode}\n고객: {customer} · 프로젝트: {project} · 유형: {type_name}\n"
            f"요구사항:\n{rq}\n{memo}{req}\n{extra}\n시트마다 내용을 써라(재료에 있는 사실만):\n{sh}")


SHEET_REWRITE = {"type": "object", "properties": {"sheet": SHEET_DRAFT, "reply": {"type": "string", "description": "바꾼 내용 한두 문장"}},
                 "required": ["sheet", "reply"]}

REQUEST_ROUTE = {"type": "object", "properties": {"sheet_keys": {"type": "array", "items": {"type": "string"}}, "instruction": {"type": "string"}},
                 "required": ["sheet_keys"]}

NOTES = {"type": "object", "properties": {"notes": {"type": "array", "items": {"type": "object", "properties": {
    "sheet_key": {"type": "string"}, "text": {"type": "string"}}, "required": ["sheet_key", "text"]}}}, "required": ["notes"]}

RFP_FIELDS = {
    "type": "object",
    "properties": {"fields": {"type": "array", "items": {"type": "object", "properties": {
        "key": {"type": "string", "enum": ["customer", "title", "industry", "scale", "requirements", "submit_due", "presentation", "budget", "decision_makers"]},
        "value": {"type": "string"}, "page": {"type": "integer"}, "quote": {"type": "string"},
        "items": {"type": "array", "items": {"type": "string"}}}, "required": ["key"]}}},
    "required": ["fields"],
}

COMMENT_PATCH = {"type": "object", "properties": {"applicable": {"type": "boolean"}, "suggestion_text": {"type": "string"},
                                                  "ops": {"type": "array", "items": {"type": "object", "properties": {
                                                      "op": {"type": "string"}, "path": {"type": "string"}, "value": {}}}}},
                 "required": ["applicable", "suggestion_text"]}

ANONYMIZE = {"type": "object", "properties": {"label": {"type": "string", "description": "업종 표현(예 국내 커피 프랜차이즈)"}}, "required": ["label"]}
QUESTION = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
RESEARCH_QUERY = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
TRANSLATE = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"}, "en": {"type": "string"}}, "required": ["id", "en"]}}}, "required": ["items"]}
SHORTEN = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"}, "text": {"type": "string"}}, "required": ["id", "text"]}}}, "required": ["items"]}


def sheet_rewrite(*, sheet_key: str, role: str, role_name: str, title: str, msg: str, material: str, target: str, instruction: str,
                  options: list[str], customer: str, memos: list[str]) -> str:
    memo = "\n".join(f"사용자 방향 메모: {m}" for m in memos)
    opt = " · ".join(options) or "없음"
    return (f"시트 다듬기 · sheet_key={sheet_key} · 역할 {role}({role_name}) · 시트 「{title}」 · 말하는 것 “{msg}”\n고객: {customer}\n"
            f"고칠 곳: {target}\n지시: {instruction}\n옵션: {opt}\n{memo}\n지금 내용(재료에 있는 사실만 유지):\n{material}\n"
            "바꾼 시트 전체를 sheet 로, 바꾼 내용을 reply 에 한두 문장으로.")


def request_route(*, text: str, sheets: list[dict[str, Any]]) -> str:
    rows = "\n".join(f"- sheet_key={s['key']} · {s['no']:02d} {s['section']} · {s['title']}" for s in sheets)
    return f"제안서 수정 요청 · 어느 시트를 고칠지 고른다\n요청: {text}\n시트 목록:\n{rows}\n고칠 시트의 sheet_key 와 시트마다 줄 지시(instruction)를 돌려줘."


def notes(*, customer: str, sheets: list[dict[str, Any]]) -> str:
    rows = "\n".join(f"- sheet_key={s['key']} · 역할 {s['role']}({s['role_name']}) · 「{s['title']}」 · 내용: {s['material']}" for s in sheets)
    return f"발표자 노트 · 고객: {customer}\n시트마다 30초 분량 발표자 노트를 써라(내용에 있는 사실만, 수치는 그대로).\n{rows}"


def shorten(*, items: list[dict[str, Any]]) -> str:
    rows = "\n".join(f"- id={x['id']} · 최대 {x['max']}자 · {x['text']}" for x in items)
    return f"칸 넘침 줄이기 · 값 토큰({{{{fact:…}}}})과 숫자는 그대로 두고 글자 수만 줄여라\n{rows}"


# ── 기존 제안서 활용(§7.11) — 모두 기밀 ─────────────────────
LINE_REWRITE = {"type": "object", "properties": {"text": {"type": "string", "description": "새로 쓴 한 줄"}}, "required": ["text"]}


def reuse_rewrite(*, section_key: str, section_name: str, customer: str, project: str, requirements: list[str],
                  sheets: list[dict[str, Any]]) -> str:
    """재작성 판정 시트 — 역할은 지키고 이번 요구사항 기준으로 다시 쓴다. 원본 줄은 참고만(기밀 · 비복제 줄은 이미 뺌)."""
    rq = "\n".join(f"- {x}" for x in requirements) or "- (요구사항 정의서 없음)"
    sh = "\n".join(f"- sheet_key={s['sheet_key']} · 역할 {s['role']}({s['role_name']}) · 시트 「{s['title']}」 · 이번엔: {s['note']}\n"
                   f"  원본 줄(참고만): " + " / ".join(s["source_lines"]) for s in sheets)
    return (f"원본 기반 재작성 · 섹션: {section_key} ({section_name})\n고객: {customer} · 프로젝트: {project}\n요구사항:\n{rq}\n"
            "원본 시트의 역할은 지키되 메시지 · 기준은 이번 요구사항으로 다시 쓴다. 원본의 출처 없는 수치는 쓰지 않고 [00] 자리표시로 둔다.\n"
            f"시트마다:\n{sh}")


def reuse_line_rewrite(*, role: str, role_name: str, title: str, field: str, neighbors: list[str], requirements: list[str]) -> str:
    """흐름 차용 누출 검사에 걸린 줄 다시 쓰기 — 원본 글은 넣지 않는다(§10.12)."""
    rq = " / ".join(requirements[:8]) or "(요구사항 없음)"
    nb = " / ".join(neighbors[:6]) or "(없음)"
    return (f"흐름 차용 줄 다시 쓰기 · 역할 {role}({role_name}) · 시트 「{title}」 · 칸 {field}\n"
            f"같은 시트의 다른 줄: {nb}\n이번 요구사항: {rq}\n"
            "이 자리에 들어갈 새 문장 한 줄을 이번 고객 기준으로 쓴다. 수치가 필요하면 [00] 자리표시.")
