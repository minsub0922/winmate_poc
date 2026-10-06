"""결정적 규칙 — 문구 · 상태 · 배지 · 일정 · 위치 표기 · 경로(02-storyboard.md §3.5 · §4 · §7.4.2–7.4.4 · §10).

LLM 없이 같은 입력이면 같은 결과를 낸다. 화면 문구는 보드 그대로.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

STEP_NAMES = ["요구사항 불러오기", "기획 방향", "목차 · 서사", "요구 추적", "일정 · 공유"]
SLOT_KEYS = ["action", "trigger", "response", "exception", "metric"]
SLOT_SHORT = {"action": "행위", "trigger": "트리거", "response": "반응", "exception": "예외", "metric": "지표"}
SLOT_FULL = {"action": "사용자 행위", "trigger": "트리거", "response": "시스템 반응", "exception": "예외", "metric": "성공 지표"}
SLOT_INFO = {
    "action": "누가 무엇을 하는지 정해요. 고른 순서대로 들어가요.",
    "trigger": "시스템이 알아차리는 순간이에요. 고른 순서대로 들어가요.",
    "response": "공간이 어떻게 답하는지 정해요. 고른 순서대로 들어가요.",
    "exception": "예외가 있어야 실제 운영 장면이 돼요. 고른 순서대로 들어가요.",
    "metric": "성공을 무엇으로 볼지 정해요. 모르는 수치는 [00]으로 둬요.",
}
# 칸을 모를 때 정의서에 더하는 고객 질문(제안 — 고객에게 보내는 문장이라 존댓말)
SLOT_CUSTOMER_Q = {
    "action": "{space}은(는) 주로 누가 어떻게 쓰나요?",
    "trigger": "{space}에서 시스템이 알아차려야 할 순간은 무엇인가요?",
    "response": "{space}에서 공간이 어떻게 반응하면 좋을까요?",
    "exception": "{space}에서 자주 생기는 예외 상황은 무엇인가요?",
    "metric": "{space}의 성과를 어떤 지표로 보시나요?",
}

STAGE_LABEL = {"concept": "컨셉 제안", "main": "본제안"}
DOCTYPE_LABEL = {"common_pitch": "공통 Pitch deck", "custom": "고객 맞춤 제안"}
VOLUME_LABEL = {12: "약 12장", 20: "약 20장", 30: "약 30장"}
LANG_LABEL = {"ko": "한국어", "en": "영문", "ko_en": "한 · 영 병기"}

# 분량별 뼈대(§10): 섹션 수 12장 8 · 20장 11 · 30장 14 (Part 2 = 1 섹션), 공간 상한 4 · 8 · 12
SKELETON = {12: {"part1": 1, "part3": 1, "spaces": 4}, 20: {"part1": 4, "part3": 1, "spaces": 8}, 30: {"part1": 6, "part3": 2, "spaces": 12}}
GROUP_KEYS = ["start", "part1", "part2", "part3", "end"]
GROUP_DEFAULT_NAME = {"start": "시작", "part1": "Part 1 사업 논리", "part2": "Part 2 공간 시나리오", "part3": "Part 3 실행 역량", "end": "마무리"}
START_SECTIONS = [("overview", "Overview"), ("key_considerations", "Key considerations"), ("intro", "Intro")]
END_SECTIONS = [("outro", "Outro"), ("timeline", "Timeline")]

# 일정(§7.4.4) — 20장 기준 D-범위, 12장 0.7배 · 30장 1.3배(반올림)
PHASES = [
    ("리서치 · 리뷰", "리서치", "영업 기획", 21, 17),
    ("스토리보드 공유 · 확정", "공유 · 확정", "영업 · 고객", 16, 14),
    ("DSS 자료 수급", "DSS 수급", "사업부 · 관계사", 15, 10),
    ("분담 작성", "분담 작성", "Part 1 영업 기획 · Part 2 솔루션 · Part 3 관계사 협업", 12, 6),
    ("취합 · 디자인 · 교정", "디자인", "디자인", 5, 2),
    ("검수 · 납품", "납품", "영업 기획", 1, 0),
]
VOLUME_SCALE = {12: 0.7, 20: 1.0, 30: 1.3}

# 기획 질의(§5.2) — 주제별 고정 문구(보드)
QUESTION_ORDER = ["decision", "audience", "comparison", "budget_scope", "timeline"]
QUESTION_COPY: dict[str, dict[str, Any]] = {
    "decision": {
        "topic_label": "결정할 것", "text": "이번 제안을 보고 고객이 결정할 것은 무엇인가요?",
        "info": "정의서에 없어서 여쭤봐요. 고른 순서대로 Overview 목적과 Outro의 다음 단계가 돼요.",
        "select": "multi_ordered", "order_roles": ["Overview 목적", "Outro 다음 단계"], "allow_custom": True,
        "affects": ["overview.purpose", "outro.next_step"],
    },
    "audience": {
        "topic_label": "청중", "text": "먼저 설득할 사람은 누구인가요?",
        "info": "고른 순서대로 Part 1 사업 논리와 Part 2 공간 경험의 비중을 나눠요.",
        "select": "multi_ordered", "order_roles": [], "allow_custom": True,
        "affects": ["overview.audience", "part1.weight", "part2.weight"],
    },
    "comparison": {
        "topic_label": "비교 기준", "text": "고객은 이 제안을 무엇과 비교해 볼까요?",
        "info": "Part 1-1 진화 구도와 Part 1-2 '성과 비교 기준'을 정해요.",
        "select": "single", "order_roles": [], "allow_custom": False,
        "affects": ["p1_1.frame", "p1_2.benchmark"],
    },
    "budget_scope": {
        "topic_label": "예산 범위", "text": "이번 제안에서 예산은 어디까지 다룰까요?",
        "info": "고른 순서대로 Part 3 실행 범위가 돼요.", "select": "multi_ordered", "order_roles": [], "allow_custom": True,
        "affects": ["p3_1.scope"],
    },
    "timeline": {
        "topic_label": "일정", "text": "고객이 원하는 일정은 언제인가요?",
        "info": "Timeline 섹션과 제작 일정에 들어가요.", "select": "single", "order_roles": [], "allow_custom": True,
        "affects": ["timeline.when"],
    },
}
# 질의 unknown 이 영향을 주는 섹션 키(§7.4.2 규칙 2)
UNKNOWN_AFFECTS = {"decision": ["overview", "outro"], "audience": ["overview"], "comparison": ["p1_1", "p1_2"],
                   "budget_scope": ["p3_1"], "timeline": ["timeline"]}
FOLLOWUP_LABELS = {"use_public": "고객 공개 자료 있음", "internal_only": "내부 자료만 있음", "placeholder": "모름 — [00]으로 두기"}

PLACEHOLDER_RE = re.compile(r"\[00\]|\[확인 필요\]")


# ── 조사 · 표기 ────────────────────────────────────────────

def josa_eul(n: int) -> str:
    """v{n}을/를 — 1·3·6·7·8·10 → 을, 2·4·5·9 → 를."""
    return "을" if str(n)[-1] in "0136780" else "를"


def josa_ro(n: int) -> str:
    """v{n}로/으로 — 3·6·10(0) → 으로, 그 밖 → 로(ㄹ받침 1·7·8 → 로)."""
    return "으로" if str(n)[-1] in "036" else "로"


def eun(word: str) -> str:
    """은/는 — 받침이 있으면 `은`."""
    ch = word.strip()[-1:] if word.strip() else ""
    if ch and 0xAC00 <= ord(ch) <= 0xD7A3:
        return "은" if (ord(ch) - 0xAC00) % 28 else "는"
    return "은" if ch in "0136781LMNRlmnr" else "는"


def tokens_of(text: str) -> list[str]:
    return PLACEHOLDER_RE.findall(text or "")


def two_digit(n: int) -> str:
    return f"{n:02d}"


# ── 설정 ──────────────────────────────────────────────────

def volume_for_spaces(n: int) -> int:
    if n <= 0:
        return 20
    if n <= 4:
        return 12
    if n <= 8:
        return 20
    return 30


def volume_hint(n: int) -> str | None:
    """§10 분량 힌트(해당 없으면 None)."""
    if n <= 0:
        return None
    if n <= 4:
        return f"{n}개 공간이면 약 12장으로도 담을 수 있어요"
    if n <= 8:
        return f"{n}개 공간을 담으려면 20장 이상"
    return f"{n}개 공간을 담으려면 30장 이상"


def settings_summary(settings: dict[str, Any]) -> str:
    return " · ".join([
        STAGE_LABEL.get(settings["stage"]["value"], ""), DOCTYPE_LABEL.get(settings["doc_type"]["value"], ""),
        VOLUME_LABEL.get(int(settings["volume"]["value"]), ""), LANG_LABEL.get(settings["language"]["value"], ""),
    ])


def finalize_settings(settings: dict[str, Any]) -> dict[str, Any]:
    settings["summary"] = settings_summary(settings)
    settings["all_from_rq"] = all(settings[k]["source"] == "rq" for k in ("stage", "doc_type", "volume", "language"))
    return settings


# ── 단계 · 상태 문구 ────────────────────────────────────────

def step_label(step: int, status: str) -> str:
    if status == "shared":
        return "완료 · 공유됨"
    if status == "done":
        return "완료"
    step = max(1, min(5, int(step)))
    return f"{step}/5 {STEP_NAMES[step - 1]}"


def status_label(status: str) -> str:
    return {"in_progress": "진행 중", "done": "완료", "shared": "완료 · 공유됨"}.get(status, status)


def draft_label(version: int, has_unsaved: bool) -> str:
    return f"v{version + 1} 초안" if (version == 0 or has_unsaved) else f"v{version}"


HANDOFF_NAMES = {"proposal": "제안서", "mi": "MI", "scenario": "공간 시나리오"}


def sub_line(doc: dict[str, Any]) -> str:
    """SB0 둘째 줄(§4.2 결정적 템플릿)."""
    status = doc.get("status", "in_progress")
    step = int(doc.get("step") or 1)
    if status == "shared":
        targets = []
        for h in doc.get("handoffs") or []:
            name = HANDOFF_NAMES.get(h.get("target", ""))
            if name and name not in targets:
                targets.append(name)
        if targets:
            last = targets[-1]
            ro = "으로" if (_has_final(last) and not _final_is_rieul(last)) else "로"
            return f"{' · '.join(targets)}{ro} 넘겼어요"
        if doc.get("exported"):
            return "내보냈어요"
        if doc.get("review_requested"):
            return "내부 검토를 요청했어요"
        return f"v{doc.get('saved_version', 0)} 저장"
    if status == "done":
        return f"v{doc.get('saved_version', 0)} 저장"
    active = doc.get("active_job") or {}
    outline = doc.get("outline") or {}
    if step == 1:
        qs = (doc.get("planning") or {}).get("questions") or []
        answers = {a["question_id"]: a for a in (doc.get("planning") or {}).get("answers") or []}
        answered = [q for q in qs if q["id"] in answers]
        if qs and answered:
            nxt = next((i for i, q in enumerate(qs, 1) if q["id"] not in answers), len(qs))
            return f"기획 질의 {nxt} / {len(qs)}"
        return "정의서를 고르는 중"
    if step == 2:
        return "기획 방향을 고르는 중"
    if step == 3:
        if active.get("kind") == "sb.outline":
            w = outline.get("writing") or {}
            return f"목차 쓰는 중 · {w.get('done', 0)} / {w.get('total', 0)} 섹션"
        empties = [s["name"] for s in outline.get("spaces") or [] if s.get("filled_count", 0) == 0]
        if empties:
            shown = " · ".join(empties[:2])
            extra = f" 외 {len(empties) - 2}" if len(empties) > 2 else ""
            return f"{shown}{extra} 시나리오가 비어 있어요"
        return "목차를 다듬는 중"
    if step == 4:
        items = [i for i in (doc.get("trace") or {}).get("items") or [] if i.get("state") == "to_resolve"]
        items.sort(key=lambda i: i.get("priority", 0))
        if items:
            return f"정리할 요구 {len(items)}개 · {items[0].get('short') or items[0].get('code')}"
        return "요구 추적 확인 중"
    return "일정 · 분담 작성 중"


def _has_final(word: str) -> bool:
    ch = word.strip()[-1:] if word.strip() else ""
    if not ch:
        return False
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        return (code - 0xAC00) % 28 > 0
    return ch.isdigit() and ch in "0136780"


def _final_is_rieul(word: str) -> bool:
    ch = word.strip()[-1:]
    if not ch:
        return False
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        return (code - 0xAC00) % 28 == 8
    return ch in "178"


def route_for(doc: dict[str, Any]) -> str:
    """지금 화면(사이드바 · SB0 `이어서` 가 가는 곳)."""
    sb = doc["id"]
    base = f"/storyboard/{sb}"
    status = doc.get("status", "in_progress")
    if status in ("done", "shared"):
        return f"{base}/saved?v={doc.get('saved_version', 0)}"
    step = int(doc.get("step") or 1)
    if step == 1:
        qs = (doc.get("planning") or {}).get("questions") or []
        answers = {a["question_id"] for a in (doc.get("planning") or {}).get("answers") or []}
        if qs and any(q["id"] in answers for q in qs):
            nxt = next((i for i, q in enumerate(qs, 1) if q["id"] not in answers), len(qs))
            return f"{base}/planning/{nxt}"
        return f"{base}/source"
    return {2: f"{base}/direction", 3: f"{base}/outline", 4: f"{base}/trace", 5: f"{base}/schedule"}.get(step, f"{base}/outline")


def cta_for(doc: dict[str, Any]) -> str:
    if doc.get("status") in ("done", "shared"):
        return "open"
    if (doc.get("active_job") or {}).get("kind") == "sb.outline":
        return "view"
    return "continue"


# ── 목차 · 섹션 · 공간 ──────────────────────────────────────

def section_label(sec: dict[str, Any]) -> str:
    """사람이 읽는 섹션 위치 이름(수정 요청 · 변경 기록)."""
    g = sec.get("group_key")
    if g == "part1":
        return f"Part {sec.get('code') or ''} {sec['name']}".strip()
    if g == "part2":
        return "Part 2 공간 시나리오"
    if g == "part3":
        code = sec.get("code") or "Part 3"
        prefix = code if code.startswith("Part") else f"Part {code}"
        return f"{prefix} {sec['name']}"
    return sec["name"]


def space_label(space: dict[str, Any], sep: str = " ") -> str:
    return f"Part 2{sep}{space['name']}"


def slot_text(slot: dict[str, Any] | None) -> str:
    if not slot:
        return ""
    return "".join(s.get("text", "") for s in slot.get("segments") or [])


def space_filled(space: dict[str, Any]) -> int:
    return sum(1 for k in SLOT_KEYS if ((space.get("slots") or {}).get(k) or {}).get("state") in ("filled", "unknown"))


def space_status(space: dict[str, Any]) -> str:
    if space.get("status") == "supplemented" and space_filled(space) > 0:
        return "supplemented"
    return "empty" if space_filled(space) == 0 else "draft"


def section_status(sec: dict[str, Any], *, spaces: list[dict[str, Any]], unknown_sections: set[str],
                   linked_unconfirmed: set[str], open_discussion_sections: set[str]) -> str:
    """§7.4.2 섹션 상태(위가 우선, Part 2 는 `작성 중` 을 먼저 본다)."""
    if sec.get("group_key") == "part2" and any(space_filled(sp) < 5 for sp in spaces):
        return "writing"
    if sec.get("tbd_reason"):
        return "tbd"
    has_tokens = any(tokens_of(ln.get("text", "")) or ln.get("claim") for ln in sec.get("lines") or [])
    if sec.get("group_key") == "part2":
        has_tokens = has_tokens or any(tokens_of(slot_text(sl)) or (sl or {}).get("state") == "unknown"
                                       for sp in spaces for sl in (sp.get("slots") or {}).values())
    if has_tokens or sec.get("key") in unknown_sections or sec["id"] in linked_unconfirmed:
        return "needs_confirmation"
    if sec["id"] in open_discussion_sections:
        return "reviewing"
    return "confirmed"


def group_badges(group_key: str, sections: list[dict[str, Any]], spaces: list[dict[str, Any]]) -> list[dict[str, str]]:
    """§7.4.3 묶음 배지(최대 2개, 이 순서)."""
    out: list[dict[str, str]] = []
    if group_key == "part2":
        if any(space_filled(sp) < 5 for sp in spaces):
            out.append({"label": "작성 중", "style": "draft"})
        empty = sum(1 for sp in spaces if space_filled(sp) == 0)
        if empty:
            out.append({"label": f"미완 {empty}", "style": "tbd"})
    nc = sum(1 for s in sections if s.get("status") == "needs_confirmation")
    if nc:
        out.append({"label": f"확인 필요 {nc}", "style": "soft"})
    rv = sum(1 for s in sections if s.get("status") == "reviewing")
    if rv:
        out.append({"label": f"검토 중 {rv}", "style": "line"})
    tbd = sum(1 for s in sections if s.get("status") == "tbd")
    if tbd:
        out.append({"label": "TBD" if tbd == 1 else f"TBD {tbd}", "style": "tbd"})
    return out[:2]


def group_meta(group_key: str, sections: list[dict[str, Any]], spaces: list[dict[str, Any]]) -> str:
    if group_key in ("start", "end"):
        return " · ".join(s["name"] for s in sections)
    if group_key == "part2":
        return f"공간 {len(spaces)}"
    return f"섹션 {len(sections)}"


# ── 일정 ──────────────────────────────────────────────────

def _scale(d: int, f: float) -> int:
    return int(math.floor(d * f + 0.5))


def schedule_phases(volume: int, *, saved: bool, open_questions: int, owners: dict[str, str] | None = None,
                    ids: list[str] | None = None) -> list[dict[str, Any]]:
    f = VOLUME_SCALE.get(int(volume), 1.0)
    current = 2 if saved else 1
    phases = []
    for i, (name, short, owner, a, b) in enumerate(PHASES, 1):
        d_from, d_to = _scale(a, f), _scale(b, f)
        if d_from < d_to:
            d_from = d_to
        if i == 4 and owners:
            owner = " · ".join(f"Part {k} {v}" for k, v in (("1", owners.get("part1")), ("2", owners.get("part2")),
                                                              ("3", owners.get("part3"))) if v) or owner
        badges = []
        if i == current:
            badges.append("지금")
        if i == 2 and open_questions > 0:
            badges.append(f"고객 확인 {open_questions}")
        phases.append({"id": (ids[i - 1] if ids and len(ids) >= i else f"phs_{i}"), "n": i, "name": name, "short": short,
                       "owner": owner, "d_from": d_from, "d_to": d_to, "badges": badges, "current": i == current})
    return phases


def timeline_direction(phases: list[dict[str, Any]]) -> str:
    return " → ".join(p["short"] for p in phases)


# ── 요구 추적 위치 표기 ─────────────────────────────────────

def places_label(places: list[dict[str, Any]], sections_by_id: dict[str, dict[str, Any]],
                 spaces_by_id: dict[str, dict[str, Any]]) -> str:
    """§4.22 결정적 위치 포맷: 같은 접두는 한 번, 연속 3개 이상은 `~`, 공간은 `Part 2 {공간 · 공간}`."""
    p1: list[tuple[int, str]] = []
    others_before: list[str] = []
    part2_section = False
    space_names: list[str] = []
    part3: list[str] = []
    tail: list[str] = []
    for pl in places:
        kind = pl.get("kind")
        if kind == "section":
            sec = sections_by_id.get(pl.get("id") or "")
            if not sec:
                if pl.get("label"):
                    tail.append(pl["label"])
                continue
            g = sec.get("group_key")
            if g == "part1":
                p1.append((sec.get("order", 0), sec.get("code") or ""))
            elif g == "part2":
                part2_section = True
            elif g == "part3":
                lab = pl.get("label") if (pl.get("label") or "").startswith("Part 3") else "Part 3"
                if lab not in part3:
                    part3.append(lab)
            else:
                if sec["name"] not in others_before:
                    others_before.append(sec["name"])
        elif kind == "space":
            sp = spaces_by_id.get(pl.get("id") or "")
            name = sp["name"] if sp else (pl.get("label") or "").replace("Part 2", "").strip()
            if name and name not in space_names:
                space_names.append(name)
        elif kind == "customer_question":
            if "고객에게 묻기" not in tail:
                tail.append("고객에게 묻기")
        elif kind == "owner_check":
            if "담당 확인 중" not in tail:
                tail.append("담당 확인 중")
    parts: list[str] = list(others_before)
    if p1:
        codes = [c for _, c in sorted(set(p1))]
        nums = []
        for c in codes:
            m = re.match(r"1-(\d+)$", c)
            nums.append(int(m.group(1)) if m else None)
        if len(codes) >= 3 and all(n is not None for n in nums) and nums == list(range(nums[0], nums[0] + len(nums))):  # type: ignore[operator]
            parts.append(f"Part {codes[0]} ~ {codes[-1]}")
        else:
            parts.append("Part " + " · ".join(codes))
    if space_names:
        parts.append("Part 2 " + " · ".join(space_names))
    elif part2_section:
        parts.append("Part 2")
    parts.extend(part3)
    parts.extend(tail)
    return " · ".join(p for p in parts if p)


def code_list_label(codes: list[str]) -> str:
    """`RQ-11 · 07 · 03 · 05` — 첫 코드만 `RQ-` 붙임."""
    if not codes:
        return ""
    rest = [c.replace("RQ-", "") for c in codes[1:]]
    return " · ".join([codes[0], *rest])


# ── 해시 ──────────────────────────────────────────────────

def stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def content_snapshot(doc: dict[str, Any]) -> dict[str, Any]:
    """버전 스냅숏(§5.7) — 작업본의 내용 부분."""
    keys = ("settings", "planning", "direction", "outline", "trace", "schedule", "requirement_ref")
    return {k: json.loads(json.dumps(doc.get(k), ensure_ascii=False, default=str)) for k in keys}


_VOLATILE = {"writing", "composing", "computed_at", "stale", "ready", "questions", "added_questions", "badges", "current",
             "latest_version", "open_question_count", "saved_at", "status", "filled_count", "summary", "all_from_rq",
             "extensions_acknowledged", "acknowledged", "qa_base", "questions_job", "compose_job"}


def _canon(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _canon(v) for k, v in obj.items() if k not in _VOLATILE}
    if isinstance(obj, list):
        return [_canon(v) for v in obj]
    return obj


def content_hash(doc: dict[str, Any]) -> str:
    """작업본 ≠ 최신 버전 판단용(파생 · 진행 표시 값은 뺀다)."""
    snap = content_snapshot(doc)
    planning = snap.get("planning") or {}
    canon = {
        "settings": {k: (snap.get("settings") or {}).get(k, {}).get("value") for k in ("stage", "doc_type", "volume", "language")},
        "answers": _canon(planning.get("answers") or []),
        "direction": _canon(snap.get("direction")),
        "outline": _canon({k: (snap.get("outline") or {}).get(k) for k in ("sections", "spaces", "discussions")}),
        "trace": _canon({k: (snap.get("trace") or {}).get(k) for k in ("items", "extensions")}),
        "rq": (snap.get("requirement_ref") or {}).get("version"),
    }
    return stable_hash(canon)
