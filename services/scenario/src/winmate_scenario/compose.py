"""장면 쓰기 · 연결 · 타임라인 나누기(LLM + 결정적 대체) — 그래프 노드들이 쓰는 공통 단계.

§7.2 모델 능력별 경로:
- 텍스트 → 타임라인: 시간 정규식 줄 + LLM JSON / 대체: 정규식 줄 = 시간대, 문장 주어 = 역할(등장인물 칩), 비트 = 줄 전체
- 등장인물: LLM JSON / 대체: 등장인물 사전
- 골격: LLM 비트 초안 / 대체: 「{역할}이 {장소}에서 {단계}」
- 장면 쓰기: LLM(스트리밍) / LLM 실패 = 잡 실패(다시 시도) — 단, 모델이 빈 글을 주면 비트로 결정적 초안(새 사실 없음)
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any

from . import kbq, llm, policy, prompts, seed, service, texts
from . import timeline as tl

log = logging.getLogger("winmate.scenario.compose")

TIME_LINE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*(.*)$")
TIME_LINE_KO = re.compile(r"^\s*(\d{1,2})시(?:\s*(\d{1,2})분)?\s*(.*)$")

ROLE_WORDS = ["본사 마케팅 담당자", "본사 담당자", "점장", "매니저", "손님", "고객", "직원", "스태프", "크루", "바리스타", "방문객", "관리자",
              "점주", "환자", "보호자", "의료진", "간호사", "학생", "교수", "교직원", "투숙객", "프런트", "작업자", "관중", "관객", "시민",
              "운전자", "라이더", "안내 직원", "운영팀", "관제 요원", "역무원", "입주민", "어르신", "요양보호사"]
LABEL_KEYWORDS = ["점심 피크", "저녁 피크", "피크", "오픈", "마감", "배포", "점검", "교대", "체크인", "체크아웃", "입장", "퇴장", "주문",
                  "픽업", "회의", "출근", "퇴근", "정산", "보충", "알림", "조치", "정상화", "예약", "집계"]


# ── 등장인물 ──────────────────────────────────────────────

def dictionary_characters(raw: str) -> list[str]:
    found: list[tuple[int, str]] = []
    text = raw or ""
    for m in re.finditer(r"((?:[가-힣]+\s)?[가-힣]+)팀(?=[이은을에의과와도]|\s|$)", text):
        phrase = m.group(1).strip()
        if phrase and not phrase.endswith("한"):
            found.append((m.start(), f"{phrase} 담당자"))
    for w in ROLE_WORDS:
        i = text.find(w)
        if i >= 0 and not any(w in f for _, f in found):
            found.append((i, w))
    found.sort()
    out: list[str] = []
    for _, name in found:
        if name not in out and not any(name in o for o in out):
            out.append(name)
    return out[:8]


async def extract_characters(raw: str, *, customer: str | None, exclude: list[str]) -> tuple[list[str], str]:
    clean, _ = policy.scrub_people(raw or "")
    res = await llm.try_json("sc.characters", prompts.characters(clean), prompts.CharactersOut, customer=customer, timeout=5,
                             retries=False)
    names: list[str] = []
    source = "llm"
    if res is not None:
        for n in res.data.get("characters") or []:
            n = policy.scrub_people(str(n).strip())[0]
            if 1 <= len(n) <= 16 and n not in names:
                names.append(n)
    if not names:
        names = dictionary_characters(clean)
        source = "dictionary"
    ex = set(exclude or [])
    return [n for n in names if n not in ex], source


# ── 타임라인 나누기 ──────────────────────────────────────────

def split_lines(raw: str) -> list[dict[str, Any]]:
    """정규식(`^\\s*(\\d{1,2}):(\\d{2})`) 줄 나누기 → [{time, text}] (시각 없는 줄도 순서대로)."""
    out = []
    for line in (raw or "").splitlines():
        s = line.strip()
        if not s or s.startswith("[공간]"):
            continue
        m = TIME_LINE.match(s) or TIME_LINE_KO.match(s)
        if m:
            h, mi = int(m.group(1)), int(m.group(2) or 0)
            if h <= 24 and mi <= 59:
                out.append({"time": f"{h:02d}:{mi:02d}", "text": m.group(3).strip()})
                continue
        out.append({"time": None, "text": s})
    return out


def label_of(text: str, i: int) -> str:
    first = re.split(r"[.!?]\s*", text.strip(), maxsplit=1)[0].strip()
    if 0 < len(first) <= 8:
        return first
    for k in LABEL_KEYWORDS:
        if k in text:
            return k
    return f"장면 {i + 1}"


def subject_role(text: str, roles: list[str]) -> str | None:
    best = None
    best_pos = 10 ** 6
    for r in roles:
        for cand in (r, texts.short_role(r)):
            if not cand:
                continue
            p = text.find(cand)
            if p >= 0 and p < best_pos:
                best, best_pos = r, p
    return best


def fallback_parse(lines: list[dict[str, Any]], characters: list[str]) -> dict[str, Any]:
    roles = list(characters) or dictionary_characters("\n".join(x["text"] for x in lines)) or ["담당자"]
    slots, beats = [], []
    for i, ln in enumerate(lines):
        slots.append({"time": ln["time"], "label": label_of(ln["text"], i)})
        role = subject_role(ln["text"], roles) or roles[0]
        beats.append({"slot": i, "role": role, "text": texts.clip(ln["text"], tl.BEAT_MAX), "place": ""})
    return {"slots": slots, "roles": [{"name": r} for r in roles], "beats": beats, "personas": [], "suggestion": None,
            "suggested_roles": []}


def usable_parse(data: dict[str, Any] | None) -> bool:
    return bool(data and data.get("slots") and data.get("beats"))


def build_from_parse(doc: dict[str, Any], data: dict[str, Any], *, source: str = "parsed") -> dict[str, Any]:
    """파싱 결과 → 시간대 · 역할 · 장면(시간대마다 장면 1, 첫 비트 주 시점) · 페르소나 · 추천. 실존 인물 이름은 역할로."""
    slots = []
    for i, s in enumerate(data.get("slots") or []):
        slots.append(tl.new_slot(policy.scrub_people(s.get("label") or "")[0] or f"장면 {i + 1}", s.get("time"), ord_=i))
    # 시각이 모두 있으면 시각 순
    if slots and all(s.get("time") for s in slots):
        order = sorted(range(len(slots)), key=lambda i: texts.time_key(slots[i]["time"]))
    else:
        order = list(range(len(slots)))
    remap = {old: new for new, old in enumerate(order)}
    slots = [slots[i] for i in order]
    for i, s in enumerate(slots):
        s["ord"] = i
    role_names: list[str] = []
    for r in data.get("roles") or []:
        n = policy.scrub_people((r.get("name") or "").strip())[0]
        if n and n not in role_names:
            role_names.append(n)
    for b in data.get("beats") or []:
        n = policy.scrub_people((b.get("role") or "").strip())[0]
        if n and n not in role_names:
            role_names.append(n)
    personas = {p.get("role"): p for p in data.get("personas") or [] if isinstance(p, dict)}
    roles = []
    for i, n in enumerate(role_names):
        p = personas.get(n) or {}
        roles.append(tl.new_role(n, ord_=i, source=source, intro=p.get("intro") or "", wants=p.get("wants") or [],
                                 pains=p.get("pains") or []))
    by_name = {r["name"]: r["id"] for r in roles}
    scenes_by_slot: dict[str, dict[str, Any]] = {}
    for b in data.get("beats") or []:
        si = b.get("slot")
        if not isinstance(si, int) or si not in remap:
            continue
        slot = slots[remap[si]]
        text = policy.clean(policy.scrub_people(b.get("text") or "")[0])
        if not text:
            continue
        rn = policy.scrub_people((b.get("role") or "").strip())[0]
        beat = tl.new_beat(by_name.get(rn), text, b.get("place") or "")
        sc = scenes_by_slot.get(slot["id"])
        if sc is None:
            beat["primary"] = True
            sc = tl.new_scene(slot["id"], [beat])
            scenes_by_slot[slot["id"]] = sc
        else:
            sc["beats"].append(beat)
    doc["slots"] = slots
    doc["roles"] = roles
    doc["scenes"] = list(scenes_by_slot.values())
    # 추천 장면(빈 칸 하나) · 추천 역할
    sug = data.get("suggestion") or None
    doc["suggestions"] = {"scene": None, "roles": [], "dismissed": list((doc.get("suggestions") or {}).get("dismissed") or [])}
    if sug and sug.get("text") and sug["text"] not in doc["suggestions"]["dismissed"]:
        slot_id = None
        si = sug.get("slot")
        if isinstance(si, int) and si in remap:
            slot_id = slots[remap[si]]["id"]
        elif sug.get("label") or sug.get("time"):
            ns = tl.new_slot(sug.get("label") or "새 시간대", sug.get("time"), is_new=True)
            doc["slots"].append(ns)
            doc["slots"].sort(key=lambda s: (texts.time_key(s.get("time")) if all(x.get("time") for x in doc["slots"]) else s["ord"]))
            for i, s in enumerate(doc["slots"]):
                s["ord"] = i
            slot_id = ns["id"]
        role_id = by_name.get((sug.get("role") or "").strip())
        if slot_id and role_id:
            doc["suggestions"]["scene"] = {"slot_id": slot_id, "role_id": role_id, "text": texts.clip(sug["text"], tl.BEAT_MAX),
                                           "place": sug.get("place") or ""}
    doc["suggestions"]["roles"] = [r for r in dict.fromkeys(data.get("suggested_roles") or []) if r and r not in by_name][:2]
    tl.normalize(doc)
    return doc


def fallback_suggested_roles(doc: dict[str, Any]) -> list[str]:
    ind = seed.industry(doc.get("vertical_code"))
    have = {r["name"] for r in doc.get("roles") or []}
    out = []
    for p in (ind or {}).get("presets") or []:
        for r in p.get("roles") or []:
            if r not in have and r not in out:
                out.append(r)
    return out[:2]


# ── 업종 짐작(프로젝트 업종이 없을 때) ───────────────────────────

_IND_WORDS = {"FB": ["카페", "커피", "메뉴보드", "음료", "레스토랑", "식당", "드라이브스루", "베이커리"],
              "MD": ["병원", "진료", "외래", "환자", "병실"], "ED": ["강의", "학생", "캠퍼스", "교실", "도서관"],
              "HT": ["호텔", "객실", "투숙객", "체크인"], "RT": ["플래그십", "쇼윈도", "체험존", "VMD"],
              "OF": ["오피스", "회의실", "사무실 직원"], "FN": ["영업점", "창구", "은행"], "MF": ["공장", "물류", "생산 라인", "작업자"],
              "PB": ["관제실", "역 대합실", "승강장"]}


async def guess_vertical(text: str) -> str | None:
    t = text or ""
    scores = {code: sum(1 for w in words if w in t) for code, words in _IND_WORDS.items()}
    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] > 0:
        return best[0]
    cands = await kbq.a2(t)
    if cands:
        ind = seed.industry_for_vertical(cands[0].get("id"))
        if ind and (len(cands) == 1 or (cands[0].get("score") or 0) - (cands[1].get("score") or 0) >= 0.2):
            return ind["code"]
    return None


# ── 장면 쓰기 · 연결 ─────────────────────────────────────────

def allowed_solutions(doc: dict[str, Any], sc: dict[str, Any]) -> list[str]:
    if doc.get("type") != "with":
        return []
    plan = sc.get("plan_solutions")
    picks = [p["solution_id"] for p in doc.get("solution_picks") or []]
    if plan is not None:
        return [x.get("solution_id") for x in plan if x.get("solution_id") in picks or not picks] or []
    return picks


def link_solutions(doc: dict[str, Any], sc: dict[str, Any], parsed: list[str], *, keep_existing: bool) -> list[dict[str, Any]]:
    allowed = allowed_solutions(doc, sc)
    out: list[dict[str, Any]] = []

    def add(sid: str, code: str) -> None:
        if sid not in allowed:
            return
        if any(x["solution_id"] == sid and x["action_code"] == code for x in out):
            return
        out.append({"solution_id": sid, "action_code": code, "label": seed.action_label(sid, code), "is_new": False})

    if keep_existing:
        for x in sc.get("solutions") or []:
            add(x["solution_id"], x["action_code"])
    plan = sc.get("plan_solutions") or []
    for raw in parsed:
        parts = [p.strip() for p in raw.split("·")]
        s = seed.solution_by_name(parts[0])
        if not s:
            continue
        labels = parts[1:] or []
        for lab in labels:
            a = seed.action_by_label(s["id"], lab)
            if a:
                add(s["id"], a["code"])
    # SC3R 에서 적용한 장면 동작은 꼭 남긴다
    for p in plan:
        if not any(x["solution_id"] == p.get("solution_id") for x in out):
            add(p.get("solution_id"), p.get("action_code"))
    if not out and allowed:
        # 모델이 동작을 못 댔으면 문장 키워드로(동작 사전 밖 표현 정규화)
        text = " ".join([sc.get("story") or "", *(b.get("text") or "" for b in sc.get("beats") or [])])
        best = seed.match_actions(text, allowed)
        if best:
            add(best[0]["solution_id"], best[0]["action_code"])
    return out[:3]


def _find_pick(doc: dict[str, Any], name: str) -> dict[str, Any] | None:
    n = re.sub(r"\s*[×xX]\s*\d+\s*$", "", name or "").strip().lower()
    if not n:
        return None
    for p in doc.get("product_picks") or []:
        for cand in (p.get("short"), p.get("label"), p.get("model_code")):
            c = (cand or "").lower()
            if c and (c == n or c in n or n in c):
                return p
    return None


def _qty_of(name: str) -> int | None:
    m = re.search(r"[×xX]\s*(\d+)\s*$", name or "")
    return int(m.group(1)) if m else None


def link_products(doc: dict[str, Any], sc: dict[str, Any], parsed: list[str], *, keep_existing: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def add(p: dict[str, Any], qty: int | None) -> None:
        key = service.product_key(p)
        for x in out:
            if service.product_key(x) == key:
                return
        out.append({"ref": p.get("ref"), "family_id": p.get("family_id"), "model_code": p.get("model_code"), "short": p.get("short") or p.get("label"),
                    "label": p.get("label") or p.get("short"), "qty": qty if qty is not None else p.get("qty"), "is_new": False})

    if keep_existing:
        for x in sc.get("products") or []:
            add(x, x.get("qty"))
    for raw in parsed:
        p = _find_pick(doc, raw)
        if p:
            add(p, _qty_of(raw) or p.get("qty"))
    text = " ".join([sc.get("title") or "", sc.get("story") or "", *(b.get("text") or "" for b in sc.get("beats") or [])])
    for p in doc.get("product_picks") or []:
        if any((c or "") and (c in text) for c in (p.get("short"), p.get("label"))):
            add(p, p.get("qty"))
    if not out and not keep_existing:
        for p in sc.get("products") or []:  # 조감도 존 제품 등 미리 붙은 제품
            add(p, p.get("qty"))
    if not out and doc.get("product_picks"):
        p = doc["product_picks"][0]
        add(p, p.get("qty"))
    return out


def link_beats(doc: dict[str, Any], sc: dict[str, Any], parsed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not parsed:
        return sc.get("beats") or []
    out = []
    used_roles: set[str] = set()
    old_by_role = {b.get("role_id"): b for b in sc.get("beats") or []}
    for i, pb in enumerate(parsed):
        r = tl.role_by_name(doc, pb.get("role"))
        if r is None or r["id"] in used_roles:
            continue
        used_roles.add(r["id"])
        old = old_by_role.get(r["id"])
        beat = {**(old or tl.new_beat(r["id"], "")), "role_id": r["id"], "text": texts.clip(pb.get("text") or (old or {}).get("text") or "", tl.BEAT_MAX),
                "place": texts.clip(pb.get("place") or (old or {}).get("place") or "", tl.PLACE_MAX), "primary": False}
        out.append(beat)
    # 원래 주 시점 역할이 빠졌으면 원래 비트를 남긴다
    for b in sc.get("beats") or []:
        if b.get("role_id") not in used_roles:
            out.append({**b, "primary": False})
    primary_role = next((b.get("role_id") for b in sc.get("beats") or [] if b.get("primary")), None)
    out.sort(key=lambda b: 0 if b.get("role_id") == primary_role else 1)
    if out:
        out[0]["primary"] = True
    return out


def characters_of(sc: dict[str, Any], keep: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    out = [dict(c) for c in keep or []]
    have = {c["role_id"] for c in out}
    for b in sc.get("beats") or []:
        if b.get("role_id") and b["role_id"] not in have:
            out.append({"role_id": b["role_id"], "is_new": False})
            have.add(b["role_id"])
    return out


def deterministic_scene(doc: dict[str, Any], sc: dict[str, Any]) -> dict[str, Any]:
    """모델이 빈 글을 줄 때 — 비트 문장으로만 초안(새 사실 없음)."""
    label = tl.scene_label(doc, sc)
    beats = sc.get("beats") or []
    first = beats[0]["text"] if beats else label
    sentences = []
    for b in beats:
        r = tl.role_by_id(doc, b.get("role_id"))
        who = (r or {}).get("name") or ""
        sentences.append(f"{texts.with_josa(who, '이/가')} {b['text']}" if who and not b["text"].startswith(who) else b["text"])
    story = " ".join(s.rstrip(".") + "." for s in sentences)
    return {"title": f"{label} — {first}", "story": texts.clip(story, tl.STORY_MAX), "beats": [], "solutions": [], "products": []}


async def kb_evidence(doc: dict[str, Any], solutions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    ind = seed.industry(doc.get("vertical_code"))
    vertical = (ind or {}).get("kr_verticals", [None])[0] if ind and ind.get("kr_verticals") else None
    seen = set()
    for s in solutions:
        so = seed.solution(s.get("solution_id"))
        if not so or so["id"] in seen or not so.get("kb_id"):
            continue
        seen.add(so["id"])
        res = await kbq.query("E1", {"about": [["solution", so["kb_id"]]], **({"vertical": vertical} if vertical else {})})
        tree = res.get("tree") or {}
        msgs = [m for m in (tree.get("key_messages") or []) if not m.get("claim_flag")]
        if msgs:
            m = msgs[0]
            out.append({"kind": "kb_message", "ref": m.get("id"), "text": m.get("text") or "", "source_url": m.get("source_url")})
    return out


def input_evidence(doc: dict[str, Any], sc: dict[str, Any]) -> list[dict[str, Any]]:
    line = prompts.line_for_slot(doc, tl.slot_by_id(doc, sc.get("slot_id")))
    if not line:
        return []
    m = TIME_LINE.match(line)
    quote = (m.group(3) if m else line).strip()
    return [{"kind": "input_quote", "ref": None, "text": quote}] if quote else []


DeltaFn = Callable[[str], Awaitable[None]]


async def compose_scene(doc: dict[str, Any], sc: dict[str, Any], *, memos: list[str] | None = None, stream: bool = False,
                        on_partial: DeltaFn | None = None, preset: str | None = None, pov_role: str | None = None,
                        instruction: str | None = None, rewrite: bool = False) -> tuple[dict[str, Any], bool]:
    """장면 하나를 쓴다 → (갱신된 장면 사본, 익명화했나). LLM 실패는 llm.LlmError 로 올린다."""
    import copy
    work = copy.deepcopy(sc)
    allowed = allowed_solutions(doc, work)
    kb_lines = []
    for e in work.get("evidence") or []:
        if e.get("kind") == "kb_message" and e.get("text"):
            kb_lines.append(e["text"])
    max_story = 70 if preset == "shorter" else tl.STORY_MAX
    prompt = prompts.write_scene(doc, work, memos=memos or [], allowed_solutions=allowed, kb_lines=kb_lines,
                                 others=tl.scenes(doc), instruction=instruction, preset=preset, pov_role=pov_role, max_story=max_story)
    task = "sc.rewrite_scene" if rewrite else "sc.write_scene"
    last = [0.0]

    async def delta(acc: str) -> None:
        if on_partial is None:
            return
        now = time.monotonic()
        if now - last[0] < 0.25:
            return
        last[0] = now
        part = prompts.partial_story(acc)
        if part:
            await on_partial(part)

    res = await llm.text_call(task, prompt, customer=doc.get("customer_name"), stream=stream, on_delta=delta if stream else None)
    parsed = prompts.parse_scene_text(llm.strip_code_fence(res.data))
    if not parsed["title"] and not parsed["story"]:
        if rewrite and work.get("story"):
            parsed = {"title": work.get("title") or "", "story": work.get("story") or "", "beats": [], "solutions": [], "products": []}
        else:
            parsed = deterministic_scene(doc, work)
    label = tl.scene_label(doc, work)
    title = parsed["title"].strip() or f"{label} — {texts.clip(parsed['story'], 20)}"
    if label and not title.startswith(label):
        title = f"{label} — {title.split('—', 1)[-1].strip()}" if "—" in title else f"{label} — {title}"
    work["title"] = texts.clip(title, 60)
    story = parsed["story"].strip()
    if preset == "shorter":
        story = texts.clip(story, 70)
    work["story"] = texts.clip(story, tl.STORY_MAX)
    work["beats"] = link_beats(doc, work, parsed["beats"])
    work["solutions"] = link_solutions(doc, work, parsed["solutions"], keep_existing=rewrite)
    work["products"] = link_products(doc, work, parsed["products"], keep_existing=rewrite)
    work["characters"] = characters_of(work, work.get("characters") if rewrite else None)
    if not work.get("place"):
        work["place"] = next((b.get("place") for b in work["beats"] if b.get("place")), "") or ""
    ev = input_evidence(doc, work)
    if work["solutions"]:
        ev += await kb_evidence(doc, work["solutions"])
    work["evidence"] = ev
    service.finalize_text(doc, work)
    work["status"] = "done"
    work["partial_story"] = None
    return work, res.anonymized


async def sleep_pace() -> None:
    """mock 시연 속도(SC_PACE_S, 기본 0) — SC4G 미리보기가 보이게."""
    from winmate_common import env
    try:
        pace = float(env.get("SC_PACE_S", "0") or 0)
    except ValueError:
        pace = 0.0
    if pace > 0:
        await asyncio.sleep(pace)
