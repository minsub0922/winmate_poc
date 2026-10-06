"""프롬프트 · LLM 출력 스키마(task `sc.<동작>`). mock 고정 응답(`mocks/ai-tools/sc.*.json`)은 프롬프트의 고정 머리말
(「장면 라벨: 오픈」 · 「요청 종류: 더 짧게」 …)로 응답을 고른다 — 머리말을 바꾸면 픽스처도 같이 바꾼다.
"""
from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from . import seed, texts
from . import timeline as tl


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1)


# ── 스키마 ────────────────────────────────────────────────

class CharactersOut(BaseModel):
    characters: list[str] = Field(default_factory=list, description="문장에 나오는 역할명(사람 이름 아님, 2~12자)")


class PSlot(BaseModel):
    time: str | None = Field(None, description="HH:MM(문장에 시각이 있을 때만)")
    label: str = Field(description="시간대 이름(오픈 · 점심 피크 …, 8자 안팎)")


class PRole(BaseModel):
    name: str


class PBeat(BaseModel):
    slot: int = Field(description="slots 의 0부터 번호")
    role: str = Field(description="roles 의 name")
    text: str = Field(description="그 역할이 하는 일 한 줄(40자 이내)")
    place: str = Field("", description="장소(16자 이내, 문장에 없으면 짐작한 일반명)")


class PPersona(BaseModel):
    role: str
    intro: str = Field("", description="한 줄 소개(30자 안팎)")
    wants: list[str] = Field(default_factory=list, description="원하는 것 2개(짧은 구)")
    pains: list[str] = Field(default_factory=list, description="불편한 점 2개(짧은 구)")


class PSuggestion(BaseModel):
    slot: int | None = Field(None, description="빈 칸이 있는 시간대 번호. 새 시간대를 제안하면 null")
    time: str | None = None
    label: str | None = Field(None, description="새 시간대 이름(slot 이 null 일 때)")
    role: str
    text: str = Field(description="추천 장면 한 줄")
    place: str = ""


class ParseOut(BaseModel):
    title: str | None = Field(None, description="시나리오 제목(「{고객} {상황} 시나리오」, 고객이 문장에 없으면 빼기)")
    customer_name: str | None = Field(None, description="문장에 나온 고객사 이름 그대로(없으면 null)")
    space_label: str | None = Field(None, description="대표 공간(매장 · 외래 대기실 …)")
    slots: list[PSlot] = Field(default_factory=list)
    roles: list[PRole] = Field(default_factory=list)
    beats: list[PBeat] = Field(default_factory=list)
    personas: list[PPersona] = Field(default_factory=list)
    suggestion: PSuggestion | None = None
    suggested_roles: list[str] = Field(default_factory=list)


class SkeletonOut(BaseModel):
    times: list[str | None] = Field(default_factory=list, description="시간대마다 대표 시각 HH:MM(하루일 때만, 아니면 null)")
    beats: list[PBeat] = Field(default_factory=list)
    personas: list[PPersona] = Field(default_factory=list)
    suggested_roles: list[str] = Field(default_factory=list)


class AxesOut(BaseModel):
    axes: list[str] = Field(default_factory=list, description="시나리오 축 3개(방문객 동선 · 매장 하루 · 런칭 이벤트 당일 …)")


class RecItem(BaseModel):
    scene_no: int
    title_line: str = Field("", description="장면 한 줄 요약(「메뉴보드가 아침 메뉴로 켜진다」 — 제목 「{라벨} — {한 줄}」의 뒤)")
    product_only_text: str = Field(description="제품만일 때 모습 한 줄")
    solution: str = Field(description="솔루션 이름(고른 목록 · 동작 사전 안)")
    action: str = Field(description="동작 사전의 동작 라벨")
    tag: Literal["required", "recommended", "optional"]
    benefit: str = Field(description="효과 한 줄")
    evidence_quote: str = Field("", description="입력 원문에서 그대로 따온 근거 구절(없으면 빈칸)")
    needs_solution: bool = Field(False, description="제품만으로는 이 장면 이야기가 완성되지 않음(W 「장면 {목록}는 솔루션이 있어야」)")


class RecommendOut(BaseModel):
    items: list[RecItem] = Field(default_factory=list)


class EditOp(BaseModel):
    op: Literal["add_beat", "add_product", "add_solution", "add_scene", "rewrite"]
    scene: int | None = Field(None, description="장면 번호")
    role: str | None = None
    text: str | None = None
    product: str | None = None
    solution: str | None = None
    action: str | None = None
    after: int | None = None
    label: str | None = None
    time: str | None = None
    instruction: str | None = None


class EditOut(BaseModel):
    ops: list[EditOp] = Field(default_factory=list)


class TimelineEditOp(BaseModel):
    op: Literal["add_beat", "set_beat", "remove_beat", "add_slot", "add_role", "shorten_role"]
    time: str | None = None
    slot_label: str | None = None
    role: str | None = None
    text: str | None = None
    place: str | None = None
    scene: int | None = None
    new_text: str | None = None


class TimelineEditOut(BaseModel):
    ops: list[TimelineEditOp] = Field(default_factory=list)


class LaneBeat(BaseModel):
    scene: int
    text: str


class LaneRewriteOut(BaseModel):
    beats: list[LaneBeat] = Field(default_factory=list)


class SpaceMap(BaseModel):
    place: str
    space: str


class SpaceKeysOut(BaseModel):
    spaces: list[str] = Field(default_factory=list)
    mapping: list[SpaceMap] = Field(default_factory=list)


# ── 공통 맥락 ──────────────────────────────────────────────

def type_line(doc: dict[str, Any]) -> str:
    return "with 솔루션" if doc.get("type") == "with" else "without 솔루션"


def industry_line(doc: dict[str, Any]) -> str:
    ind = seed.industry(doc.get("vertical_code"))
    return ind["name"] if ind else "미정"


def roles_line(doc: dict[str, Any]) -> str:
    return ", ".join(r["name"] for r in tl.roles(doc))


def persona_block(doc: dict[str, Any], role_ids: list[str] | None = None) -> str:
    rows = []
    for r in tl.roles(doc):
        if role_ids is not None and r["id"] not in role_ids:
            continue
        parts = [f"- {r['name']}"]
        if r.get("intro"):
            parts.append(f"소개: {r['intro']}")
        if r.get("wants"):
            parts.append("원하는 것: " + ", ".join(r["wants"]))
        if r.get("pains"):
            parts.append("불편한 점: " + ", ".join(r["pains"]))
        rows.append(" / ".join(parts))
    return "\n".join(rows) or "(없음)"


def products_line(doc: dict[str, Any]) -> str:
    out = []
    for p in doc.get("product_picks") or []:
        out.append(f"{p['short']} ×{p['qty']}" if p.get("qty") and p["qty"] > 1 else p["short"])
    return ", ".join(out) or "(없음)"


def solutions_dictionary(solution_ids: list[str]) -> str:
    rows = []
    for sid in solution_ids:
        s = seed.solution(sid)
        if not s:
            continue
        for a in s["actions"]:
            rows.append(f"- {s['name']} · {a['label']}: {a['benefit']}")
    return "\n".join(rows) or "(솔루션 없음 — 제품 활용만 쓴다)"


def line_for_slot(doc: dict[str, Any], slot: dict[str, Any] | None) -> str:
    """입력 원문에서 그 시간대 줄(시각으로 시작)을 찾는다."""
    if not slot:
        return ""
    raw = doc.get("raw_text") or ""
    t = slot.get("time")
    for line in raw.splitlines():
        s = line.strip()
        if t and s.startswith(t):
            return s
        if t and s.startswith(t.lstrip("0")):
            return s
    lab = slot.get("label") or ""
    for line in raw.splitlines():
        if lab and lab in line:
            return line.strip()
    return ""


def scene_block(doc: dict[str, Any], sc: dict[str, Any]) -> str:
    slot = tl.slot_by_id(doc, sc["slot_id"]) or {}
    lines = [f"장면 번호: {sc['no']}", f"장면 라벨: {slot.get('label') or ''}", f"시각: {slot.get('time') or '(없음)'}",
             f"장소: {sc.get('place') or '(없음)'}", "비트:"]
    for b in sc.get("beats") or []:
        r = tl.role_by_id(doc, b.get("role_id"))
        lines.append(f"- {(r or {}).get('name') or '역할 없음'}: {b['text']}" + (f" ({b['place']})" if b.get("place") else ""))
    src = line_for_slot(doc, slot)
    if src:
        lines.append(f"입력 원문 줄: \"{src}\"")
    return "\n".join(lines)


# ── 프롬프트 ──────────────────────────────────────────────

def characters(raw_text: str) -> str:
    return ("요청 종류: 등장인물 뽑기\n아래 공간 시나리오 문장에 나오는 등장인물을 역할명으로 뽑아라. 실존 인물 이름은 역할명으로 바꾼다. "
            "팀(본사 마케팅팀)은 담당자(본사 마케팅 담당자)로.\n\n[문장]\n" + raw_text)


def parse_input(raw_text: str, characters_: list[str], lines: list[dict[str, Any]], industry: str) -> str:
    return (
        "요청 종류: 타임라인 나누기\n고객 공간의 하루 · 상황 문장을 시간대 × 역할 비트로 나눠라. 시각이 있는 줄은 그 시각이 시간대다. "
        "비트는 역할마다 한 줄(40자 이내), 장소는 16자 이내. 등장인물 칩에 있는 이름을 역할명으로 쓴다. "
        "페르소나 초안(소개 · 원하는 것 2 · 불편한 점 2)을 역할마다 쓰고, 빈 칸에 어울리는 추천 장면 1개와 추천 역할 2개를 낸다.\n"
        f"업종: {industry}\n등장인물 칩: {', '.join(characters_) or '(없음)'}\n"
        f"정규식으로 나눈 줄: {_dump(lines)}\n\n[문장]\n{raw_text}"
    )


def skeleton_template(ind: dict[str, Any], preset: dict[str, Any], is_day: bool) -> str:
    return (
        "요청 종류: 업종 골격\n업종 템플릿 프리셋으로 시나리오 골격을 써라. 시간대마다 역할별 비트 한 줄(40자 이내), 장소는 업종 대표 공간에서. "
        + ("'하루' 프리셋이니 시간대마다 대표 시각(HH:MM)을 제안해라. " if is_day else "시각은 비운다(null). ")
        + "업종 요구를 장면에 반영하고, 근거 없는 수치는 쓰지 않는다.\n"
        f"업종: {ind['name']}\n프리셋: {preset['title']}\n흐름: {' → '.join(preset['flow'])}\n역할: {' · '.join(preset['roles'])}\n"
        f"대표 공간: {' · '.join(ind['spaces'])}\n장면에 담을 요구: {' · '.join(ind['needs'])}"
    )


def skeleton_birdseye(title: str, axis: str, zones: list[dict[str, Any]], with_times: bool) -> str:
    rows = [f"- 존 {z['n']} {z['name']}: 제품 {', '.join(p.get('short') or p.get('label') for p in z['products']) or '없음'}"
            for z in zones]
    return (
        "요청 종류: 조감도 골격\n조감도의 존을 순서대로 장면으로 만든다. 장면 k 의 장소는 존 k. 역할은 방문객과 직원(축에 맞게). "
        + ("시간대마다 대표 시각(HH:MM)을 제안해라. " if with_times else "시각은 비운다(null). ")
        + f"\n조감도: {title}\n시나리오 축: {axis}\n존(순서):\n" + "\n".join(rows)
    )


def axes(title: str, zones: list[dict[str, Any]], industry: str) -> str:
    return (f"요청 종류: 시나리오 축\n조감도 공간 유형과 업종으로 시나리오 축 3개를 제안해라(예: 방문객 동선 · 매장 하루 · 런칭 이벤트 당일).\n"
            f"조감도: {title}\n업종: {industry}\n존: {', '.join(z['name'] for z in zones)}")


def recommend(doc: dict[str, Any], candidate_solutions: list[str]) -> str:
    scenes = "\n\n".join(scene_block(doc, sc) for sc in tl.scenes(doc))
    return (
        "요청 종류: 장면별 솔루션 추천\n장면마다 제품만일 때 모습과, 이야기를 완성하는 솔루션 동작 하나를 동작 사전에서 골라라. "
        "태그: 다수 사업장 일괄 · 원격 동작(전국 N개 매장에 배포)은 required, 문장 속 수작업을 자동화하면 recommended, "
        "제품 화면만으로 장면이 성립하면 optional. evidence_quote 는 입력 원문에서 그대로 따온 구절만(지어내지 않음).\n"
        f"유형: {type_line(doc)}\n업종: {industry_line(doc)}\n제품: {products_line(doc)}\n\n[동작 사전]\n"
        f"{solutions_dictionary(candidate_solutions)}\n\n[장면]\n{scenes}\n\n[입력 원문]\n{doc.get('raw_text') or ''}"
    )


SCENE_FORMAT = (
    "[출력 형식 — 이 다섯 줄만]\n"
    "제목: {라벨} — {한 줄}\n"
    "이야기: 1~2문장, 120자 이내(고른 솔루션 · 제품만, 근거 없는 수치는 [00])\n"
    "비트: 역할 | 한 줄(40자 이내) | 장소   (등장 역할마다 한 줄)\n"
    "솔루션: 솔루션 · 동작 (여러 개면 쉼표, 없으면 없음)\n"
    "제품: 약칭 ×수량 (여러 개면 쉼표)"
)


def write_scene(doc: dict[str, Any], sc: dict[str, Any], *, memos: list[str], allowed_solutions: list[str], kb_lines: list[str],
                others: list[dict[str, Any]], instruction: str | None = None, preset: str | None = None,
                pov_role: str | None = None, max_story: int = tl.STORY_MAX) -> str:
    head = "요청 종류: 장면 쓰기" if not (instruction or preset) else "요청 종류: 장면 다시 쓰기"
    other_lines = []
    for o in others:
        if o["id"] == sc["id"]:
            continue
        other_lines.append(f"- 장면 {o['no']} {tl.scene_label(doc, o)}: {o.get('title') or ''} {o.get('story') or ''}".strip())
    parts = [
        head,
        f"[시나리오] {doc.get('title') or ''} · 유형: {type_line(doc)}",
        f"고객: {doc.get('customer_name') or '(없음)'}",
        f"업종: {industry_line(doc)}",
        f"업종 요구: {' · '.join(doc.get('needs') or []) or '(없음)'}",
        "[이 장면]",
        scene_block(doc, sc),
    ]
    if sc.get("title") or sc.get("story"):
        parts.append(f"지금 제목: {sc.get('title') or ''}\n지금 이야기: {sc.get('story') or ''}")
    parts += [
        "[등장인물 페르소나]", persona_block(doc),
        "[쓸 수 있는 솔루션 동작]", solutions_dictionary(allowed_solutions),
        f"[쓸 수 있는 제품] {products_line(doc)}",
    ]
    if kb_lines:
        parts.append("[KB 근거]\n" + "\n".join(f"- {x}" for x in kb_lines[:6]))
    if memos:
        parts.append("진행 방향 메모: " + " / ".join(memos))
    if preset == "shorter":
        parts.append(f"수정 지시: 더 짧게 — 이야기를 {max_story}자 이내 한 문장으로")
    elif preset == "pov" and pov_role:
        parts.append(f"수정 지시: {pov_role} 시점으로 — {pov_role}이(가) 주인공이 되게")
    elif preset == "solution_detail":
        parts.append("수정 지시: 솔루션 동작 더 구체적으로 — 동작이 언제 무엇을 하는지 보이게")
    if instruction:
        parts.append(f"수정 지시: {instruction}")
    if other_lines:
        parts.append("[다른 장면 — 읽기 전용, 고치지 않음]\n" + "\n".join(other_lines))
    parts.append(f"[입력 원문]\n{doc.get('raw_text') or ''}")
    parts.append(SCENE_FORMAT)
    return "\n".join(parts)


def edit(doc: dict[str, Any], text: str) -> str:
    rows = []
    for sc in tl.scenes(doc):
        rows.append(f"- 장면 {sc['no']} {tl.scene_label(doc, sc)}: {sc.get('title') or ''} / 제품 "
                    f"{', '.join(p.get('short') for p in sc.get('products') or []) or '없음'}")
    return ("요청 종류: 시나리오 수정 요청\n수정 요청을 연산 목록으로 바꿔라(add_beat · add_product · add_solution · add_scene · rewrite). "
            "영향 장면 번호를 정확히.\n"
            f"역할: {roles_line(doc)}\n제품: {products_line(doc)}\n[장면]\n" + "\n".join(rows) + f"\n\n수정 요청: {text}")


def timeline_edit(doc: dict[str, Any], text: str) -> str:
    rows = []
    for sl in tl.slots(doc):
        cells = []
        for sc in [s for s in tl.scenes(doc) if s["slot_id"] == sl["id"]]:
            for b in sc.get("beats") or []:
                r = tl.role_by_id(doc, b.get("role_id"))
                cells.append(f"{(r or {}).get('name')}: {b['text']}(장면 {sc['no']})")
        rows.append(f"- {texts.join([sl.get('time') or '', sl['label']], ' ')} → {' / '.join(cells) or '빈 시간대'}")
    return ("요청 종류: 타임라인 편집 요청\n편집 요청을 타임라인 연산으로 바꿔라(add_beat · set_beat · remove_beat · add_slot · add_role · shorten_role).\n"
            f"역할: {roles_line(doc)}\n[타임라인]\n" + "\n".join(rows) + f"\n\n편집 요청: {text}")


def lane_rewrite(doc: dict[str, Any], role: dict[str, Any]) -> str:
    rows = []
    for sc in tl.scenes(doc):
        for b in sc.get("beats") or []:
            if b.get("role_id") == role["id"]:
                rows.append(f"- 장면 {sc['no']}: {b['text']}")
    return ("요청 종류: 레인 문장 다듬기\n바뀐 인물 설정에 맞게 이 역할의 비트 문장만 다시 써라(40자 이내, 다른 역할은 그대로).\n"
            f"역할: {role['name']}\n소개: {role.get('intro') or ''}\n원하는 것: {', '.join(role.get('wants') or [])}\n"
            f"불편한 점: {', '.join(role.get('pains') or [])}\n[이 역할의 비트]\n" + "\n".join(rows))


def space_keys(doc: dict[str, Any], places: list[str], candidates: list[str]) -> str:
    return ("요청 종류: 공간 정규화\n장면 장소를 시나리오 공간 목록으로 묶어라(같은 공간이면 같은 이름, 공간 이름은 8자 안팎).\n"
            f"공간 후보: {', '.join(candidates) or '(없음)'}\n장소: {', '.join(places)}\n시나리오: {doc.get('title') or ''}")


# ── 장면 글 해석(스트리밍 결과) ─────────────────────────────────

_LINE = re.compile(r"^\s*(제목|이야기|비트|솔루션|제품)\s*[:：]\s*(.*)$")


def parse_scene_text(text: str) -> dict[str, Any]:
    """「제목: … / 이야기: … / 비트: 역할 | 글 | 장소 / 솔루션: … / 제품: …」 → dict. 모르는 줄은 이야기에 붙인다."""
    out: dict[str, Any] = {"title": "", "story": "", "beats": [], "solutions": [], "products": []}
    for raw in (text or "").splitlines():
        m = _LINE.match(raw)
        if not m:
            if raw.strip() and out["story"] and not out["beats"]:
                out["story"] += " " + raw.strip()
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "제목":
            out["title"] = val
        elif key == "이야기":
            out["story"] = val
        elif key == "비트":
            cells = [c.strip() for c in val.split("|")]
            if len(cells) >= 2:
                out["beats"].append({"role": cells[0], "text": cells[1], "place": cells[2] if len(cells) > 2 else ""})
        elif key in ("솔루션", "제품") and val and val not in ("없음", "-"):
            out["solutions" if key == "솔루션" else "products"] += [x.strip() for x in re.split(r"[,，]", val) if x.strip()]
    return out


def partial_story(acc: str) -> str:
    """스트리밍 중 부분 글에서 「이야기:」 뒤만(SC4G 작성 중 카드)."""
    m = re.search(r"이야기\s*[:：]\s*(.*?)(?:\n\s*(?:비트|솔루션|제품)\s*[:：]|$)", acc or "", re.DOTALL)
    return (m.group(1).strip() if m else "").replace("\n", " ")
