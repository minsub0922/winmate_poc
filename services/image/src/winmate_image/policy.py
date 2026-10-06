"""생성 정책 사전 검사(R3 · §4.8 · §7.3 policy_check · §10.6).

- 설명 · 지시문 분류: LLM JSON(`img.policy`) + 경쟁사 사전(config/content_policy.yaml, 없으면 서비스 기본 사전) + 정규식.
  LLM 이 실패하면 사전 · 정규식만(사람 이름 판정 없음 → 시나리오 · 공간은 인물 기본값 '가상 인물'로 강제, `policy:rules_only`).
- 이슈: competitor_brand(자동 해결) · real_person(선택 필요) · product_unrecognized(후보1 ≥ 0.4 면 자동, 아니면 선택 필요).
- 보류: 선택 필요 이슈가 있으면 끝 번호부터 floor(N/2)장.
"""
from __future__ import annotations

import asyncio
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from winmate_common.env import repo_root

from . import config, llm

ISSUE_ORDER = {"product_unrecognized": 0, "competitor_brand": 1, "real_person": 2, "unsafe": 3}


@lru_cache(maxsize=1)
def dictionary() -> dict[str, Any]:
    for p in (repo_root() / "config" / "content_policy.yaml", Path(__file__).parent / "data" / "content_policy.yaml"):
        if p.is_file():
            try:
                return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue
    return {}


def rules_scan(text: str) -> dict[str, list[dict[str, Any]]]:
    d = dictionary()
    comps: list[dict[str, Any]] = []
    seen: set[str] = set()
    low = text or ""
    for b in d.get("competitor_brands") or []:
        for a in b.get("aliases") or [b.get("name")]:
            if not a:
                continue
            pat = re.compile(rf"(?<![A-Za-z가-힣]){re.escape(str(a))}(?![A-Za-z])", re.IGNORECASE)
            m = pat.search(low)
            if m and b["name"] not in seen:
                seen.add(b["name"])
                comps.append({"name": b["name"], "span": m.group(0)})
                break
    for p in d.get("generic_competitor_patterns") or []:
        for m in re.finditer(p, low):
            name = m.group(0).strip()
            name = re.sub(r"\s*(제품|로고|브랜드|화면)$", "", name).strip()
            if name and name not in seen:
                seen.add(name)
                comps.append({"name": name, "span": m.group(0)})
    persons: list[dict[str, Any]] = []
    for p in d.get("person_patterns") or []:
        for m in re.finditer(p, low):
            name = m.group(0).strip()
            core = re.sub(r"^\S+\s*", "", name)
            if len(core) >= 4 and core[-1] in "이가은는을를와과의":
                name = name[:-1]
            if not any(x["name"] == name for x in persons):
                persons.append({"name": name, "span": name})
    return {"competitors": comps, "real_persons": persons, "unsafe": []}


async def classify(text: str, *, confidential: bool = False, timeout: float | None = None) -> tuple[dict[str, Any], str]:
    """→ (분류, 'llm' | 'rules'). 사전 결과는 항상 합친다."""
    rules = rules_scan(text)
    out: dict[str, Any] | None = None
    if (text or "").strip():
        try:
            out = await llm.json_task("img.policy", llm.policy_prompt(text), llm.PolicyOut, system=llm.SYSTEM_KO,
                                      confidential=confidential, timeout=timeout or config.llm_timeout_s())
        except llm.ModelBlocked:
            out = None
    if out is None:
        return rules, "rules"
    merged = {"competitors": list(out.get("competitors") or []), "real_persons": list(out.get("real_persons") or []),
              "unsafe": list(out.get("unsafe") or [])}
    names = {c["name"] for c in merged["competitors"]}
    for c in rules["competitors"]:
        if c["name"] not in names and not any(c["name"] in n or n in c["name"] for n in names):
            merged["competitors"].append(c)
    pnames = {p["name"] for p in merged["real_persons"]}
    for p in rules["real_persons"]:
        if p["name"] not in pnames and not any(p["name"] in n or n in p["name"] for n in pnames):
            merged["real_persons"].append(p)
    # LLM 결과가 원문에 없는 이름이면 버린다(지어낸 인물 · 회사 방지)
    merged["competitors"] = [c for c in merged["competitors"] if c.get("name") and (c.get("span") or c["name"]) and _in_text(c, text)]
    merged["real_persons"] = [p for p in merged["real_persons"] if p.get("name") and _in_text(p, text)]
    return merged, "llm"


def _in_text(item: dict[str, Any], text: str) -> bool:
    span = (item.get("span") or "").strip()
    name = (item.get("name") or "").strip()
    core = re.sub(r"^(배우|가수|모델|아나운서|선수|연예인|탤런트|아이돌|방송인)\s*", "", name)
    return bool((span and span in text) or (name and name in text) or (core and core in text))


# ── 이슈 ─────────────────────────────────────────────────

def competitor_issue(i: int, name: str) -> dict[str, Any]:
    return {
        "id": f"iss_{i}", "type": "competitor_brand", "title": f"{name} 로고 · 제품은 이미지에 넣지 않아요",
        "status": "auto", "state_label": "대안 선택됨",
        "description": "다른 회사의 로고 · 상표 · 고유 디자인은 그리지 않아요. 비교가 목적이면 비교표 시트가 더 정확해요.",
        "options": [{"id": "generic_screen", "label": "로고 없는 일반 화면으로", "recommended": True, "default": True, "action": "choose"},
                    {"id": "label_only", "label": f"'{name}' 글자 라벨만", "recommended": False, "default": False, "action": "choose"}],
        "selected": "generic_screen", "custom_text": None,
        "data": {"competitor": name, "link_label": "Why Samsung 비교표로 보내기",
                 "link_route": f"/proposal?focus=CM&competitor={name}"},
    }


def person_issue(i: int, name: str) -> dict[str, Any]:
    return {
        "id": f"iss_{i}", "type": "real_person", "title": f"실존 인물({name})은 그리지 않아요", "status": "needs_choice",
        "state_label": "선택 필요",
        "description": "초상권 때문에 실제 인물의 얼굴 · 이름을 쓴 이미지는 만들지 않아요. 고르지 않으면 '인물 없이'로 만듭니다.",
        "options": [{"id": "virtual", "label": "가상 인물로", "recommended": False, "default": False, "action": "choose"},
                    {"id": "back_hands", "label": "뒷모습 · 손만", "recommended": False, "default": False, "action": "choose"},
                    {"id": "no_people", "label": "인물 없이 · 기본값", "recommended": True, "default": True, "action": "choose"}],
        "selected": None, "custom_text": None, "data": {"person": name},
    }


def product_issue(i: int, *, reference_id: str | None, thumb_url: str | None, candidates: list[dict[str, Any]],
                  box: list[float] | None) -> dict[str, Any]:
    top = candidates[0] if candidates else None
    auto = bool(top and float(top.get("score") or 0) >= 0.4)
    opts = []
    for j, c in enumerate(candidates[:3]):
        opts.append({"id": f"cand_{j + 1}", "label": f"{c['short']} · 가장 비슷" if j == 0 else c["short"],
                     "recommended": j == 0, "default": j == 0, "action": "choose"})
    opts.append({"id": "pick_product", "label": "제품 탐색에서 고르기", "recommended": False, "default": False, "action": "pick_product"})
    opts.append({"id": "generic", "label": "외형만 참고", "recommended": not candidates, "default": not candidates, "action": "choose"})
    return {
        "id": f"iss_{i}", "type": "product_unrecognized", "title": "참조 사진 속 디스플레이를 알아보지 못했어요",
        "status": "auto" if auto else "needs_choice", "state_label": "대안 선택됨" if auto else "선택 필요",
        "description": "사진 속 화면이 작고 멀어 베젤 · 두께를 알 수 없어요. 모델을 고르면 실제 외형으로 그립니다.",
        "options": opts, "selected": "cand_1" if auto else None, "custom_text": None,
        "data": {"reference_id": reference_id, "thumb_url": thumb_url, "candidates": candidates[:3], "box": box,
                 "thumb_label": "올린 참조 사진"},
    }


def build_issues(cls: dict[str, Any], product_issues: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for p in product_issues or []:
        issues.append(p)
    for c in (cls.get("competitors") or [])[:2]:
        issues.append(competitor_issue(0, c["name"]))
    for p in (cls.get("real_persons") or [])[:2]:
        issues.append(person_issue(0, p["name"]))
    issues.sort(key=lambda x: ISSUE_ORDER.get(x["type"], 9))
    for i, it in enumerate(issues, 1):
        it["id"] = f"iss_{i}"
    return issues


def needs_choice(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [i for i in issues if i.get("status") == "needs_choice" and not i.get("selected")]


def held_count(n: int, issues: list[dict[str, Any]]) -> int:
    """선택 필요 이슈가 있으면 floor(N/2)장 보류."""
    return n // 2 if needs_choice(issues) else 0


def selected_count(issues: list[dict[str, Any]]) -> int:
    return sum(1 for i in issues if i.get("selected"))


def applied_note(issues: list[dict[str, Any]]) -> str | None:
    """요약 카드 「경쟁사 · 인물 요소 없이 만들었어요」 — 기본 대안으로 바꾼 요소만."""
    words = []
    for it in issues:
        sel = effective_option(it)
        if it["type"] == "competitor_brand" and sel in ("generic_screen", "custom"):
            words.append("경쟁사")
        elif it["type"] == "real_person" and sel in ("no_people", None):
            words.append("인물")
    words = list(dict.fromkeys(words))
    return f"{' · '.join(words)} 요소 없이 만들었어요" if words else None


def change_band(issues: list[dict[str, Any]]) -> str | None:
    """보류 0 인데 사전 검사 이슈가 있었을 때 IMG3 띠."""
    if not issues:
        return None
    return f"요청 중 {len(issues)}가지를 바꿔서 만들었어요"


def effective_option(issue: dict[str, Any]) -> str | None:
    if issue.get("selected"):
        return issue["selected"]
    for o in issue.get("options") or []:
        if o.get("default"):
            return o["id"]
    return None


def apply_answers(issues: list[dict[str, Any]], answers: list[dict[str, Any]], *, all_recommended: bool) -> list[dict[str, Any]]:
    by_id = {i["id"]: i for i in issues}
    if all_recommended:
        for it in issues:
            rec = next((o["id"] for o in it.get("options") or [] if o.get("recommended")), None) or effective_option(it)
            it["selected"] = rec
    for a in answers:
        it = by_id.get(a.get("issue_id") or "")
        if not it:
            continue
        if a.get("custom_text"):
            it["selected"] = "custom"
            it["custom_text"] = a["custom_text"]
        elif a.get("product") and it["type"] == "product_unrecognized":
            p = a["product"]
            cand = {"short": p.get("short") or p.get("name"), "name": p.get("name") or p.get("short"),
                    "model_code": p.get("model_code"), "family_id": p.get("family_id"), "score": 1.0}
            it["data"]["candidates"] = [cand, *[c for c in it["data"].get("candidates") or [] if c.get("model_code") != cand["model_code"]]][:3]
            it["options"][0]["label"] = f"{cand['short']} · 가장 비슷"
            it["selected"] = "cand_1"
        elif a.get("option"):
            if any(o["id"] == a["option"] for o in it.get("options") or []):
                it["selected"] = a["option"]
    for it in issues:
        if it.get("selected"):
            it["state_label"] = "대안 선택됨"
    return issues


# ── 프롬프트 효과 ────────────────────────────────────────

def effects(issues: list[dict[str, Any]], *, kind: str, rules_only: bool) -> dict[str, Any]:
    """이슈별 고른 대안 → 프롬프트 지시 · 금지 · 사람 정책 · 제품 정체(모델 · generic)."""
    lines: list[str] = []
    negatives: list[str] = ["competitor logos or brand names", "real celebrities or identifiable real people",
                            "readable trademarks", "gibberish text"]
    people = "fictional" if kind == "scenario" else None
    identity: dict[str, Any] | None = None
    applied: dict[str, str] = {}
    for it in issues:
        sel = effective_option(it)
        label = next((o["label"] for o in it.get("options") or [] if o["id"] == sel), it.get("custom_text") or "")
        if it["type"] == "competitor_brand":
            if sel == "label_only":
                name = it["data"].get("competitor") or ""
                lines.append(f"Next to the Samsung display, show only a plain, generic text label reading '{name}' with no logo, "
                             "no brand colors and no distinctive product design.")
            elif sel == "custom":
                lines.append(f"Instead of the other company's product: {it.get('custom_text')}. No logos or brand names.")
            else:
                lines.append("Any non-Samsung displays show generic, logo-free content; do not draw other companies' logos, "
                             "trademarks or distinctive product designs.")
        elif it["type"] == "real_person":
            if sel == "virtual":
                people = "fictional"
            elif sel == "back_hands":
                people = "back_hands"
            elif sel == "custom":
                lines.append(f"People: {it.get('custom_text')} (fictional, not resembling any real person).")
                people = "fictional"
            else:
                people = "none"
        elif it["type"] == "product_unrecognized":
            cands = it["data"].get("candidates") or []
            if sel and sel.startswith("cand_"):
                j = int(sel.split("_")[1]) - 1
                if 0 <= j < len(cands):
                    identity = {"mode": "model", **cands[j]}
            elif sel == "generic" or sel is None:
                identity = {"mode": "generic"}
            elif sel == "custom":
                identity = {"mode": "generic"}
                lines.append(f"About the display in the reference photo: {it.get('custom_text')}")
        if sel:
            applied[it["type"]] = label
    if rules_only and kind in ("scenario", "space") and people is None:
        people = "fictional"
    return {"lines": lines, "negatives": negatives, "people": people, "identity": identity, "applied": applied}


async def judge_custom(text: str, issues: list[dict[str, Any]]) -> dict[str, Any] | None:
    """「다른 대안 입력」 → 어느 이슈의 대안인지 + 정책 재검사. 실패면 None."""
    kinds = ", ".join(sorted({i["type"] for i in issues}))
    prompt = (f"보류 사유 종류: {kinds}\n사용자가 적은 다른 대안: {text}\n\n"
              "이 대안이 어느 사유에 대한 것인지(issue_type) 고르고, 대안 문장을 짧게 정리하고(option_text), "
              "대안이 정책(다른 회사 로고 · 상표 · 고유 디자인 금지, 실존 인물 금지)을 지키는지(safe) 판단하라.")
    out = await llm.json_task("img.alt_custom", prompt, llm.CustomAltOut, system=llm.SYSTEM_KO, timeout=config.llm_timeout_s())
    if out is None:
        return None
    # 재검사: 대안 문장에 사전의 경쟁사 · 인물이 다시 나오면 거부
    again = rules_scan(out.get("option_text") or "")
    brands = {b.get("name") for b in dictionary().get("competitor_brands") or []}
    if any(c["name"] in brands for c in again["competitors"]):
        out["safe"] = False
    if again["real_persons"]:
        out["safe"] = False
    return out


async def classify_with_timeout(text: str, *, confidential: bool) -> tuple[dict[str, Any], str]:
    try:
        return await asyncio.wait_for(classify(text, confidential=confidential), timeout=config.llm_timeout_s() + 1)
    except asyncio.TimeoutError:
        return rules_scan(text), "rules"


def sanitize_text(text: str, issues: list[dict[str, Any]]) -> str:
    """프롬프트용 설명 — 경쟁사명 · 실존 인물 이름을 빼고(대안에 맞게) 남긴다(AC21)."""
    out = text or ""
    for it in issues:
        sel = effective_option(it)
        if it["type"] == "competitor_brand":
            name = (it.get("data") or {}).get("competitor") or ""
            for token in sorted({name, *[c for c in [name.split(" ")[0]] if c]}, key=len, reverse=True):
                if token and sel != "label_only":
                    out = re.sub(rf"{re.escape(token)}(\s*(로고|제품|브랜드|화면))?", "로고 없는 일반", out)
        elif it["type"] == "real_person":
            name = (it.get("data") or {}).get("person") or ""
            if name:
                out = re.sub(rf"{re.escape(name)}\s*(이|가|은|는|을|를|와|과|의)?\s*", "", out)
    for p in dictionary().get("person_patterns") or []:
        out = re.sub(p + r"\s*(이|가|은|는|을|를|와|과|의)?\s*", "", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" ,·")
    return out
