"""경고 카드(06-spec §4.17.1) — 종류별 제목 · 본문 · 선택지 · 기본 결정 · 지문."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from winmate_common.ids import new_id

from .. import config

ROLE_LABEL = {"proposed": "제안 모델", "existing": "고객 기존 장비", "alternative": "대안 모델"}
SOURCE_BODY = {"datasheet": "제품 데이터시트(PDF)", "policy_doc": "국내 보증 정책 문서", "user": "직접 입력", "catalog": "사내 제품 카탈로그"}
SOURCE_CHIP = {"datasheet": "데이터시트", "policy_doc": "보증 정책 문서", "user": "직접 입력", "catalog": "카탈로그"}


def fingerprint(*parts: Any) -> str:
    return hashlib.sha1(json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _base(kind: str, title: str, body: str, *, fp: str, row_id: str | None = None, product_id: str | None = None,
          link_id: str | None = None, options: list[dict[str, Any]] | None = None, default: str | None = None,
          replacement: dict[str, Any] | None = None, data: dict[str, Any] | None = None, catalog_version: str = "") -> dict[str, Any]:
    w = {"id": new_id("swn"), "n": 0, "kind": kind, "title": title, "body": body, "row_id": row_id, "product_id": product_id,
         "link_id": link_id, "options": options or [], "default_option": default, "replacement": replacement, "data": data or {},
         "decision": None, "status": "open", "fingerprint": fp, "detected_at": config.now_iso(), "catalog_version": catalog_version}
    if default:
        w["decision"] = {"option_key": default, "at": w["detected_at"], "default": True}
        w["status"] = "decided"
    return w


def discontinued(p: dict[str, Any], *, empty_labels: list[str], replacement: dict[str, Any] | None, version: str) -> dict[str, Any]:
    role = p.get("role") or "proposed"
    body = "사내 카탈로그에 단종 모델로 표시돼요."
    if empty_labels:
        body += f" {' · '.join(empty_labels)} 값이 없어 [확정 필요]로 두었어요."
    opts = [{"key": "keep_existing", "label": "'기존 장비'로 표기하고 유지 — 교체 전 ↔ 후 비교", "kind": "radio"},
            {"key": "remove", "label": "시트에서 빼기", "kind": "radio"}]
    if role != "existing" and replacement:
        opts.append({"key": "replace", "label": f"대체 모델 {replacement['label']}로 바꾸기", "kind": "radio"})
    opts.append({"key": "find_other", "label": "다른 후보 찾기", "kind": "button", "navigates_to": "SP1C"})
    default = "replace" if role != "existing" and replacement else "keep_existing"
    return _base("discontinued", f"{p['display_name']} · {ROLE_LABEL.get(role, '제안 모델')}", body, product_id=p["id"],
                 fp=fingerprint("discontinued", p.get("model_code") or p.get("display_name")), options=opts, default=default,
                 replacement=replacement, catalog_version=version)


def not_in_catalog(p: dict[str, Any], *, version: str) -> dict[str, Any]:
    role = p.get("role") or "proposed"
    opts = [{"key": "keep_existing", "label": "'기존 장비'로 표기하고 유지 — 교체 전 ↔ 후 비교", "kind": "radio"},
            {"key": "remove", "label": "시트에서 빼기", "kind": "radio"},
            {"key": "upload_datasheet", "label": "데이터시트 올리기", "kind": "button"}]
    return _base("not_in_catalog", f"{p['display_name']} · {ROLE_LABEL.get(role, '제안 모델')}",
                 "사내 카탈로그에서 찾을 수 없는 모델이에요. 단종됐거나 아직 등록되지 않았을 수 있어요.", product_id=p["id"],
                 fp=fingerprint("not_in_catalog", p.get("display_name")), options=opts, default="keep_existing", catalog_version=version)


def value_mismatch_source(row: dict[str, Any], p: dict[str, Any], *, choices: list[dict[str, Any]], current_key: str,
                          other_kind: str, version: str) -> dict[str, Any]:
    """choices: [{key, kind, label, value, value_text, sources}] — 지금 셀 값의 칩이 눌림. 한 칸의 일부만 다르면 그 부분만(`밝기 · QB55C`)."""
    from .values import diff_part
    body = f"카탈로그와 {SOURCE_BODY.get(other_kind, other_kind)}의 값이 달라요."
    part, texts = diff_part(row["row_key"], [c.get("value") for c in choices])
    if part:
        choices = [{**c, "value_text": t} for c, t in zip(choices, texts)]
    opts = [{"key": c["key"], "label": f"{SOURCE_CHIP.get(c['kind'], c['kind'])} · {c['value_text']}", "kind": "chip"} for c in choices]
    return _base("value_mismatch_source", f"{part or row['label_ko']} · {p['display_name']}", body, row_id=row["id"], product_id=p["id"],
                 fp=fingerprint("value_mismatch_source", p.get("model_code"), row["row_key"], [c["value_text"] for c in choices]),
                 options=opts, default=current_key, data={"choices": choices}, catalog_version=version)


def catalog_changed(row: dict[str, Any], p: dict[str, Any], *, old: dict[str, Any], new: dict[str, Any], new_version: str) -> dict[str, Any]:
    from .values import diff_part
    part, texts = diff_part(row["row_key"], [old.get("value"), new.get("value")])
    ot, nt = (texts if part else (old["value_text"], new["value_text"]))
    opts = [{"key": "prev", "label": f"이전 · {ot}", "kind": "chip"},
            {"key": "latest", "label": f"최신 · {nt}", "kind": "chip"}]
    return _base("catalog_changed", f"{part or row['label_ko']} · {p['display_name']}", f"사내 카탈로그 {new_version}에서 값이 바뀌었어요.",
                 row_id=row["id"], product_id=p["id"], fp=fingerprint("catalog_changed", p.get("model_code"), row["row_key"], new["value_text"]),
                 options=opts, default="prev", data={"choices": [{"key": "prev", **old}, {"key": "latest", **new}]}, catalog_version=new_version)


def value_mismatch_proposal(row: dict[str, Any], p: dict[str, Any], *, link: dict[str, Any], sent_text: str, current_text: str,
                            version: str) -> dict[str, Any]:
    opts = [{"key": "reflect", "label": "제안서에도 반영", "kind": "button", "navigates_to": "SP4"},
            {"key": "keep", "label": "그대로 두기", "kind": "button"}]
    return _base("value_mismatch_proposal", f"{row['label_ko']} · {p['display_name']} · 제안서와 다름",
                 f"제안서 {link.get('section_no') or ''} {link.get('section_name') or '제품 스펙'}에는 이전 값이 들어가 있어요.".replace("  ", " "),
                 row_id=row["id"], product_id=p["id"], link_id=link["id"],
                 fp=fingerprint("value_mismatch_proposal", link["id"], p.get("model_code") or p["id"], row["row_key"], current_text),
                 options=opts, data={"sent_text": sent_text, "current_text": current_text}, catalog_version=version)


def requirement_unmet(row: dict[str, Any] | None, p: dict[str, Any], *, item_label: str, source_label: str, summary: str,
                      fp_key: str, version: str) -> dict[str, Any]:
    opts = [{"key": "view", "label": "요구사항 대응표 보기", "kind": "button", "navigates_to": "SP1R"},
            {"key": "ack", "label": "확인함", "kind": "button"}]
    return _base("requirement_unmet", f"{item_label} · {p['display_name']}", f"고객 {source_label}의 '{summary}' 요구와 맞지 않아요.",
                 row_id=(row or {}).get("id"), product_id=p["id"], fp=fingerprint("requirement_unmet", p.get("model_code") or p["id"], fp_key),
                 options=opts, catalog_version=version)


def agent_text(ws: list[dict[str, Any]], products: dict[str, dict[str, Any]], *, catalog_date: str | None = None) -> str:
    """SP3W 에이전트(§4.11.1)."""
    disc = [products[w["product_id"]]["display_name"] for w in ws if w["kind"] in ("discontinued",) and w.get("product_id") in products]
    nic = [products[w["product_id"]]["display_name"] for w in ws if w["kind"] == "not_in_catalog" and w.get("product_id") in products]
    mism = len([w for w in ws if w["kind"] in ("value_mismatch_source", "value_mismatch_proposal")])
    unmet = len([w for w in ws if w["kind"] == "requirement_unmet"])
    changed = len([w for w in ws if w["kind"] == "catalog_changed"])
    parts = []
    if disc:
        names = " · ".join(disc)
        from .fmt import josa
        parts.append(f"{names}{josa(names, '은', '는')} 단종 모델이고")
    if nic:
        names = " · ".join(nic)
        from .fmt import josa
        parts.append(f"{names}{josa(names, '은', '는')} 카탈로그에 없는 모델이고")
    if mism:
        parts.append(f"출처나 제안서와 값이 다른 곳이 {mism}곳")
    if changed:
        parts.append(f"카탈로그에서 바뀐 값이 {changed}곳")
    if unmet:
        parts.append(f"고객 요구와 맞지 않는 곳이 {unmet}곳")
    lead = "최신 카탈로그와 다시 대조했어요."
    if catalog_date and changed and len(parts) == 1:
        lead = f"사내 카탈로그가 {catalog_date} 갱신되어 다시 대조했어요."
    if not parts:
        return f"{lead} 확인이 필요한 곳이 없어요."
    # 조각을 `, ` 로 잇고 끝을 `있어요`
    text = ", ".join(parts)
    if text.endswith("이고"):
        text = text[:-2] + "이에요"
    else:
        text += " 있어요"
    return f"{lead} {text}. 오른쪽에서 하나씩 정하면 시트에 반영할게요."
