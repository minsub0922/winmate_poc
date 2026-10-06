"""정의서 도메인 규칙 — 저장 문서(dict)를 다루는 순수 함수.

저장 문서(collection `requirements`) 모양
    owner_id, owner_name, project_id, short_title, short_title_basis,
    saved_version, saved_at, saved_hash,
    form{project_name, customer_name, final_audience, author_note: Field, keymen[], weights_mode, weights_rev},
    files[], context{}, hints{decision_bodies[], language}, questions[] (CustomerQuestion),
    item_seq, keyman_seq, active_job, queued_jobs[], fill_progress, deep{session_id,status,current_index,total},
    last_deep_session_id, file_snapshots{}, indexed{}
DocStore 가 붙이는 `version` 은 작업본 revision 이다(정의서 저장 버전은 `saved_version`).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso

from .models import FIELD_LABELS, FIELD_MAX

FIELDS = ("project_name", "customer_name", "final_audience", "author_note")
ID_RE = {
    "km": re.compile(r"^km_[0-9A-HJKMNP-TV-Z]{26}$"),
    "ri": re.compile(r"^ri_[0-9A-HJKMNP-TV-Z]{26}$"),
}
WEIGHT_MIN = 5
IN_PROGRESS_STATES = ("input", "filling", "deepening", "editing")
ACTIVE_SESSION_STATES = ("analyzing", "ready", "asking")
FILE_LABELS = {"pptx": "PPTX", "pdf": "PDF", "docx": "DOCX", "text": "TXT", "email": "메일"}
SUPPORTED_EXT = {".pptx": "PPTX", ".pdf": "PDF", ".docx": "DOCX", ".txt": "TXT", ".eml": "메일", ".msg": "메일"}


class DraftConflict(Exception):
    def __init__(self, index: int, op: str, target: str):
        super().__init__(f"conflict op#{index} {op} {target}")
        self.index = index
        self.op = op
        self.target = target


# ── 기본 모양 ────────────────────────────────────────────

def empty_field() -> dict[str, Any]:
    return {"value": None, "source": None, "alternatives": [], "updated_at": None, "rev": 0}


def new_doc(*, owner_id: str, owner_name: str, project_id: str | None) -> dict[str, Any]:
    return {
        "owner_id": owner_id, "owner_name": owner_name, "project_id": project_id,
        "short_title": None, "short_title_basis": None,
        "saved_version": 0, "saved_at": None, "saved_hash": None,
        "form": {**{f: empty_field() for f in FIELDS}, "keymen": [], "weights_mode": "equal_default", "weights_rev": 0},
        "files": [], "context": {}, "hints": {"decision_bodies": [], "language": None}, "questions": [],
        "item_seq": 0, "keyman_seq": 0,
        "active_job": None, "queued_jobs": [], "fill_progress": None,
        "deep": None, "last_deep_session_id": None,
        "file_snapshots": {}, "indexed": None,
    }


def user_source() -> dict[str, Any]:
    return {"kind": "user"}


def clean_text(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    v = re.sub(r"[ \t ]+", " ", value.replace("\r\n", "\n")).strip()
    if not v:
        return None
    return v[:limit]


def file_label_for(name: str, kind: str | None = None) -> str | None:
    """파일 이름 · files kind → 배지 글자. 지원하지 않으면 None."""
    lower = (name or "").lower().strip()
    dot = lower.rfind(".")
    if dot > 0 and 1 <= len(lower) - dot - 1 <= 5:
        return SUPPORTED_EXT.get(lower[dot:])
    return FILE_LABELS.get(kind or "")


def item_code(n: int) -> str:
    return f"RQ-{n:02d}"


# ── 조회 도우미 ──────────────────────────────────────────

def keymen(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return doc["form"]["keymen"]


def find_keyman(doc: dict[str, Any], keyman_id: str) -> dict[str, Any] | None:
    return next((k for k in keymen(doc) if k["id"] == keyman_id), None)


def find_item(doc: dict[str, Any], item_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    for k in keymen(doc):
        for it in k["items"]:
            if it["id"] == item_id:
                return k, it
    return None, None


def all_items(doc: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [(k, it) for k in keymen(doc) for it in k["items"]]


def field_value(doc: dict[str, Any], field: str) -> str | None:
    return (doc["form"].get(field) or {}).get("value")


def open_questions(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [q for q in doc.get("questions") or [] if q.get("status") == "open"]


def item_needs_confirmation(doc: dict[str, Any], item_id: str) -> bool:
    return any((q.get("target") or {}).get("kind") == "item" and q["target"].get("id") == item_id
               for q in open_questions(doc))


def keyman_count(doc: dict[str, Any]) -> int:
    return sum(1 for k in keymen(doc) if (k.get("name") or "").strip() or k["items"])


def item_count(doc: dict[str, Any]) -> int:
    return sum(1 for _, it in all_items(doc) if (it.get("text") or "").strip())


def is_form_empty(doc: dict[str, Any]) -> bool:
    if any(field_value(doc, f) for f in FIELDS):
        return False
    if any((k.get("name") or "").strip() or any((i.get("text") or "").strip() for i in k["items"]) for k in keymen(doc)):
        return False
    return not doc.get("files")


def title_of(doc: dict[str, Any]) -> str | None:
    cust = field_value(doc, "customer_name")
    proj = field_value(doc, "project_name")
    st = doc.get("short_title")
    if st and doc.get("short_title_basis") == [cust, proj]:
        return st
    parts = [p for p in (cust, proj) if p]
    return " ".join(parts)[:120] if parts else None


# ── 가중치 ───────────────────────────────────────────────

def equal_weights(n: int) -> list[int]:
    """floor(100/n), 앞 키맨부터 나머지 +1 — 2명 50·50, 3명 34·33·33."""
    if n <= 0:
        return []
    base = 100 // n
    rem = 100 - base * n
    return [base + (1 if i < rem else 0) for i in range(n)]


def distribute(shares: list[float], total: int, minimum: int = WEIGHT_MIN) -> list[int]:
    """비율대로 total 을 정수로 나눈다(최대 나머지 반올림, 각 ≥ minimum)."""
    n = len(shares)
    if n == 0:
        return []
    if total < minimum * n:
        return equal_split(total, n)
    weights = [max(float(s), 0.0) for s in shares]
    fixed: dict[int, int] = {}
    for _ in range(n):
        free = [i for i in range(n) if i not in fixed]
        remaining = total - sum(fixed.values())
        ssum = sum(weights[i] for i in free)
        raw = {i: (remaining * weights[i] / ssum if ssum > 0 else remaining / len(free)) for i in free}
        low = [i for i in free if raw[i] < minimum]
        if not low:
            floors = {i: math.floor(raw[i]) for i in free}
            left = remaining - sum(floors.values())
            order = sorted(free, key=lambda i: (-(raw[i] - floors[i]), i))
            for i in order[:left]:
                floors[i] += 1
            fixed.update(floors)
            break
        for i in low:
            fixed[i] = minimum
    return [fixed[i] for i in range(n)]


def equal_split(total: int, n: int) -> list[int]:
    base = total // n
    rem = total - base * n
    return [base + (1 if i < rem else 0) for i in range(n)]


def apply_equal(doc: dict[str, Any]) -> None:
    ks = keymen(doc)
    if len(ks) == 0:
        return
    if len(ks) == 1:
        ks[0]["weight"] = 100
        return
    for k, w in zip(ks, equal_weights(len(ks)), strict=True):
        k["weight"] = w


def rebalance(doc: dict[str, Any], *, added_ids: list[str] | None = None) -> None:
    """키맨 수가 바뀐 뒤 가중치를 다시 맞춘다(§7.2.1-6, §4.6 삭제 규칙)."""
    ks = keymen(doc)
    if not ks:
        return
    if len(ks) == 1:
        ks[0]["weight"] = 100
        return
    if doc["form"].get("weights_mode") != "custom":
        apply_equal(doc)
        return
    added = set(added_ids or [])
    old = [k for k in ks if k["id"] not in added and isinstance(k.get("weight"), int)]
    new = [k for k in ks if k not in old]
    if not old:
        apply_equal(doc)
        return
    n = len(ks)
    new_share = 100 // n if new else 0
    rest = 100 - new_share * len(new)
    vals = distribute([k["weight"] for k in old], rest)
    for k, w in zip(old, vals, strict=True):
        k["weight"] = w
    for k in new:
        k["weight"] = new_share
    # 새 키맨 몫이 최소보다 작으면 전체를 다시 나눈다
    if any(k["weight"] < WEIGHT_MIN for k in ks):
        vals = distribute([k["weight"] for k in ks], 100)
        for k, w in zip(ks, vals, strict=True):
            k["weight"] = w


def validate_weights(doc: dict[str, Any], weights: dict[str, int]) -> None:
    ks = keymen(doc)
    if len(ks) < 2:
        raise ApiError(422, "VALIDATION_FAILED", "가중치는 키맨이 2명 이상일 때만 정할 수 있어요")
    if set(weights) != {k["id"] for k in ks}:
        raise ApiError(422, "VALIDATION_FAILED", "모든 키맨의 가중치를 함께 보내 주세요",
                       {"expected": [k["id"] for k in ks]})
    if sum(weights.values()) != 100:
        raise ApiError(422, "WEIGHTS_SUM_INVALID", "가중치 합은 100이어야 해요", {"sum": sum(weights.values())})
    low = [kid for kid, w in weights.items() if w < WEIGHT_MIN]
    if low:
        raise ApiError(422, "WEIGHT_MIN", f"가중치는 키맨마다 {WEIGHT_MIN}% 이상이어야 해요", {"keyman_ids": low})


def set_weights(doc: dict[str, Any], weights: dict[str, int], *, rev: int) -> None:
    validate_weights(doc, weights)
    for k in keymen(doc):
        k["weight"] = int(weights[k["id"]])
    doc["form"]["weights_mode"] = "custom"
    doc["form"]["weights_rev"] = rev


def step_weights(values: list[int], index: int, direction: int, minimum: int = WEIGHT_MIN) -> list[int]:
    """웹 −/+ 규칙(§4.6): 5의 배수로 맞춰 이동, 나머지는 현재 비율대로(최대 나머지, 각 ≥ 5, 합 100)."""
    n = len(values)
    cur = values[index]
    target = (cur // 5 + 1) * 5 if direction > 0 else ((cur - 1) // 5) * 5
    target = max(minimum, min(100 - minimum * (n - 1), target))
    if target == cur:
        return list(values)
    others = [i for i in range(n) if i != index]
    rest = 100 - target
    shares = distribute([values[i] for i in others], rest, minimum)
    out = list(values)
    out[index] = target
    for i, w in zip(others, shares, strict=True):
        out[i] = w
    return out


def weights_display(doc: dict[str, Any]) -> str:
    return " · ".join(str(k.get("weight") or 0) for k in keymen(doc))


# ── 작업본 ops(§6.3) ────────────────────────────────────

def _check(base: int | None, target_rev: int, index: int, op: str, target: str) -> None:
    if base is not None and target_rev > base:
        raise DraftConflict(index, op, target)


def set_field(doc: dict[str, Any], field: str, value: str | None, source: dict[str, Any], *, rev: int,
              keep_derived: bool = True) -> None:
    if field not in FIELDS:
        raise ApiError(422, "VALIDATION_FAILED", f"알 수 없는 칸: {field}")
    value = clean_text(value, FIELD_MAX[field]) if field != "author_note" else _clean_multiline(value, FIELD_MAX[field])
    f = doc["form"][field]
    prev = f.get("source")
    if keep_derived and prev and prev.get("kind") == "file" and source.get("kind") != "file":
        f["derived_from"] = prev
    f["value"] = value
    f["source"] = source if value is not None else (source if source.get("kind") != "user" else None)
    f["updated_at"] = now_iso()
    f["rev"] = rev


def _clean_multiline(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    v = value.replace("\r\n", "\n").strip()
    return v[:limit] if v else None


def new_keyman(doc: dict[str, Any], *, name: str, source: dict[str, Any] | None, rev: int,
               keyman_id: str | None = None) -> dict[str, Any]:
    idx = doc.get("keyman_seq", 0)
    doc["keyman_seq"] = idx + 1
    return {"id": keyman_id or new_id("km"), "name": (name or "").strip()[:40], "weight": None, "color_index": idx,
            "order": 0, "source": source, "items": [], "rev": rev}


def insert_keyman(doc: dict[str, Any], km: dict[str, Any], after_id: str | None = None) -> None:
    ks = keymen(doc)
    pos = len(ks)
    if after_id:
        for i, k in enumerate(ks):
            if k["id"] == after_id:
                pos = i + 1
    ks.insert(pos, km)
    for i, k in enumerate(ks):
        k["order"] = i
    rebalance(doc, added_ids=[km["id"]])


def remove_keyman(doc: dict[str, Any], keyman_id: str) -> dict[str, Any] | None:
    ks = keymen(doc)
    km = find_keyman(doc, keyman_id)
    if km is None:
        return None
    ks.remove(km)
    for i, k in enumerate(ks):
        k["order"] = i
    rebalance(doc)
    if len(ks) < 2:
        doc["form"]["weights_mode"] = "equal_default"
    return km


def new_item(doc: dict[str, Any], *, text: str, source: dict[str, Any] | None, rev: int,
             item_id: str | None = None, short: str | None = None) -> dict[str, Any]:
    seq = doc.get("item_seq", 0) + 1
    doc["item_seq"] = seq
    return {"id": item_id or new_id("ri"), "code": item_code(seq), "text": (text or "").strip()[:200],
            "short": short, "short_for": _short_key(text) if short else None, "source": source,
            "evidence": [], "entities": [], "order": 0, "rev": rev, "updated_at": now_iso()}


def insert_item(km: dict[str, Any], item: dict[str, Any], after_id: str | None = None, index: int | None = None) -> None:
    items = km["items"]
    pos = len(items)
    if index is not None:
        pos = max(0, min(index, len(items)))
    elif after_id:
        for i, it in enumerate(items):
            if it["id"] == after_id:
                pos = i + 1
    items.insert(pos, item)
    for i, it in enumerate(items):
        it["order"] = i


def set_item_text(item: dict[str, Any], text: str, source: dict[str, Any], *, rev: int,
                  short: str | None = None) -> None:
    prev = item.get("source")
    if prev and prev.get("kind") == "file" and source.get("kind") != "file":
        item["derived_from"] = prev
    item["text"] = (text or "").strip()[:200]
    item["source"] = source
    item["rev"] = rev
    item["updated_at"] = now_iso()
    if short is not None:
        item["short"] = short[:24]
        item["short_for"] = _short_key(item["text"])
    elif item.get("short_for") != _short_key(item["text"]):
        item["short"] = None
        item["short_for"] = None


def _short_key(text: str | None) -> str:
    return hashlib.sha1((text or "").strip().encode()).hexdigest()[:12]


def short_is_current(item: dict[str, Any]) -> bool:
    return bool(item.get("short")) and item.get("short_for") == _short_key(item.get("text"))


def apply_ops(doc: dict[str, Any], ops: list[dict[str, Any]], *, base_revision: int | None, rev: int) -> list[dict[str, Any]]:
    """작업본에 ops 를 적용한다. 충돌이면 DraftConflict, 검증 실패면 ApiError. 대상이 없는 op 는 건너뛴 목록으로."""
    skipped: list[dict[str, Any]] = []
    weights_touched = False
    for i, op in enumerate(ops):
        kind = op["op"]
        if kind == "set_field":
            field = op["field"]
            value = op.get("value")
            if value is not None and len(value) > FIELD_MAX[field]:
                raise ApiError(422, "VALIDATION_FAILED", f"{FIELD_LABELS[field]}은(는) {FIELD_MAX[field]}자까지 쓸 수 있어요",
                               {"field": field, "max": FIELD_MAX[field]})
            _check(base_revision, doc["form"][field].get("rev", 0), i, kind, field)
            set_field(doc, field, value, user_source(), rev=rev)
        elif kind == "add_keyman":
            kid = op.get("keyman_id")
            if kid and not ID_RE["km"].match(kid):
                raise ApiError(422, "VALIDATION_FAILED", "키맨 id 형식이 올바르지 않아요", {"keyman_id": kid})
            if kid and find_keyman(doc, kid):
                continue  # 같은 요청을 다시 보낸 경우(멱등)
            km = new_keyman(doc, name=op.get("name") or "", source=user_source(), rev=rev, keyman_id=kid)
            insert_keyman(doc, km, op.get("after_keyman_id"))
            weights_touched = True
        elif kind == "update_keyman":
            km = find_keyman(doc, op["keyman_id"])
            if km is None:
                skipped.append({"index": i, "op": kind, "reason": "키맨이 없어요"})
                continue
            _check(base_revision, km.get("rev", 0), i, kind, km["id"])
            km["name"] = (op.get("name") or "").strip()[:40]
            km["rev"] = rev
            if km.get("source") and km["source"].get("kind") == "file":
                km["derived_from"] = km["source"]
            km["source"] = user_source()
        elif kind == "remove_keyman":
            km = find_keyman(doc, op["keyman_id"])
            if km is None:
                skipped.append({"index": i, "op": kind, "reason": "키맨이 없어요"})
                continue
            _check(base_revision, km.get("rev", 0), i, kind, km["id"])
            remove_keyman(doc, km["id"])
            weights_touched = True
        elif kind == "set_weights":
            _check(base_revision, doc["form"].get("weights_rev", 0), i, kind, "weights")
            set_weights(doc, {k: int(v) for k, v in (op.get("weights") or {}).items()}, rev=rev)
        elif kind == "reset_weights_equal":
            doc["form"]["weights_mode"] = "equal_default"
            doc["form"]["weights_rev"] = rev
            apply_equal(doc)
        elif kind == "add_item":
            km = find_keyman(doc, op["keyman_id"])
            if km is None:
                skipped.append({"index": i, "op": kind, "reason": "키맨이 없어요"})
                continue
            iid = op.get("item_id")
            if iid and not ID_RE["ri"].match(iid):
                raise ApiError(422, "VALIDATION_FAILED", "항목 id 형식이 올바르지 않아요", {"item_id": iid})
            if iid and find_item(doc, iid)[1] is not None:
                continue
            item = new_item(doc, text=op.get("text") or "", source=user_source(), rev=rev, item_id=iid)
            insert_item(km, item, op.get("after_item_id"))
        elif kind == "update_item":
            _, item = find_item(doc, op["item_id"])
            if item is None:
                skipped.append({"index": i, "op": kind, "reason": "항목이 없어요"})
                continue
            _check(base_revision, item.get("rev", 0), i, kind, item["id"])
            set_item_text(item, op.get("text") or "", user_source(), rev=rev)
        elif kind == "remove_item":
            km, item = find_item(doc, op["item_id"])
            if item is None:
                skipped.append({"index": i, "op": kind, "reason": "항목이 없어요"})
                continue
            _check(base_revision, item.get("rev", 0), i, kind, item["id"])
            km["items"].remove(item)
            for j, it in enumerate(km["items"]):
                it["order"] = j
        elif kind == "move_item":
            src_km, item = find_item(doc, op["item_id"])
            dst = find_keyman(doc, op["keyman_id"])
            if item is None or dst is None:
                skipped.append({"index": i, "op": kind, "reason": "항목 또는 키맨이 없어요"})
                continue
            _check(base_revision, item.get("rev", 0), i, kind, item["id"])
            src_km["items"].remove(item)
            for j, it in enumerate(src_km["items"]):
                it["order"] = j
            item["rev"] = rev
            insert_item(dst, item, index=int(op.get("index", 0)))
        else:  # pragma: no cover — 모델이 막는다
            raise ApiError(422, "VALIDATION_FAILED", f"알 수 없는 op: {kind}")
    if weights_touched:
        doc["form"]["weights_rev"] = rev
    return skipped


# ── 저장 · 해시 · 상태 ───────────────────────────────────

def content_hash(doc: dict[str, Any]) -> str:
    """작업본 내용(값만)의 해시 — 최신 버전과 같은지 비교에 쓴다."""
    body = {
        "fields": {f: field_value(doc, f) for f in FIELDS},
        "keymen": [
            {"id": k["id"], "name": (k.get("name") or "").strip(), "weight": k.get("weight") if len(keymen(doc)) > 1 else None,
             "items": [{"id": it["id"], "text": (it.get("text") or "").strip(),
                        "evidence": sorted(e["file_id"] for e in it.get("evidence") or [])}
                       for it in k["items"] if (it.get("text") or "").strip()]}
            for k in keymen(doc) if (k.get("name") or "").strip() or any((it.get("text") or "").strip() for it in k["items"])
        ],
    }
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]


def has_unsaved_changes(doc: dict[str, Any]) -> bool:
    if doc.get("saved_version", 0) == 0:
        return not is_form_empty(doc)
    return content_hash(doc) != doc.get("saved_hash")


def deep_in_progress(doc: dict[str, Any]) -> dict[str, Any] | None:
    d = doc.get("deep")
    if d and d.get("status") in ACTIVE_SESSION_STATES:
        return d
    return None


def list_state(doc: dict[str, Any]) -> str:
    aj = doc.get("active_job")
    if aj and aj.get("kind") == "rq.fill" or doc.get("queued_jobs"):
        return "filling"
    if deep_in_progress(doc):
        return "deepening"
    if doc.get("saved_version", 0) == 0:
        return "input"
    if has_unsaved_changes(doc):
        return "editing"
    return "saved"


def state_label(doc: dict[str, Any], state: str | None = None) -> str:
    state = state or list_state(doc)
    v = doc.get("saved_version", 0)
    if state in ("input", "filling"):
        return "입력 중"
    if state == "deepening":
        d = deep_in_progress(doc) or {}
        total = d.get("total") or 0
        i = d.get("current_index") or 1
        if total:
            return f"심층 작성 {min(max(i, 1), total)} / {total}"
        return "심층 작성"
    if state == "editing":
        return f"고치는 중 · v{v}"
    return f"저장됨 · v{v}"


def route_of(doc: dict[str, Any], state: str | None = None) -> str:
    rid = doc["id"]
    state = state or list_state(doc)
    if state == "deepening":
        d = deep_in_progress(doc) or {}
        sid = d.get("session_id")
        if d.get("status") == "asking":
            return f"/requirements/{rid}/deep/{sid}/q"
        return f"/requirements/{rid}/deep/{sid}"
    if state == "saved":
        return f"/requirements/{rid}"
    return f"/requirements/{rid}/form"


def summary_of(doc: dict[str, Any]) -> str:
    return f"키맨 {keyman_count(doc)} · 요구사항 {item_count(doc)}"


# ── 응답 만들기 ──────────────────────────────────────────

def present(doc: dict[str, Any]) -> dict[str, Any]:
    """저장 문서 → Requirement 응답(dict)."""
    state = list_state(doc)
    form = copy.deepcopy(doc["form"])
    nc = {(q.get("target") or {}).get("id") for q in open_questions(doc) if (q.get("target") or {}).get("kind") == "item"}
    for k in form["keymen"]:
        for it in k["items"]:
            it["needs_confirmation"] = it["id"] in nc
    d = deep_in_progress(doc)
    return {
        "id": doc["id"], "owner": {"id": doc.get("owner_id") or "system", "name": doc.get("owner_name") or ""},
        "project_id": doc.get("project_id"), "title": title_of(doc), "short_title": doc.get("short_title"),
        "version": doc.get("saved_version", 0), "revision": doc.get("version", 0),
        "has_unsaved_changes": has_unsaved_changes(doc), "list_state": state, "state_label": state_label(doc, state),
        "form": form, "files": doc.get("files") or [], "context": doc.get("context") or {},
        "open_question_count": len(open_questions(doc)), "item_count": item_count(doc), "keyman_count": keyman_count(doc),
        "active_job": doc.get("active_job"), "queued_jobs": doc.get("queued_jobs") or [],
        "fill_progress": doc.get("fill_progress"),
        "active_deep_session_id": d.get("session_id") if d else None,
        "active_deep": d, "last_deep_session_id": doc.get("last_deep_session_id"),
        "route": route_of(doc, state), "created_at": doc.get("created_at"), "updated_at": doc.get("updated_at"),
        "saved_at": doc.get("saved_at"),
    }


def present_list_item(doc: dict[str, Any]) -> dict[str, Any]:
    state = list_state(doc)
    return {
        "id": doc["id"], "title": title_of(doc), "customer_name": field_value(doc, "customer_name"),
        "project_name": field_value(doc, "project_name"), "project_id": doc.get("project_id"),
        "list_state": state, "state_label": state_label(doc, state), "version": doc.get("saved_version", 0),
        "has_unsaved_changes": has_unsaved_changes(doc), "keyman_count": keyman_count(doc), "item_count": item_count(doc),
        "open_question_count": len(open_questions(doc)), "updated_at": doc.get("updated_at"),
        "saved_at": doc.get("saved_at"), "route": route_of(doc, state), "active_deep": deep_in_progress(doc),
        "owner": {"id": doc.get("owner_id") or "system", "name": doc.get("owner_name") or ""},
    }


def search_blob(doc: dict[str, Any]) -> str:
    parts = [title_of(doc) or "", field_value(doc, "customer_name") or "", field_value(doc, "project_name") or ""]
    parts += [k.get("name") or "" for k in keymen(doc)]
    return " ".join(parts).lower()


# ── 저장 스냅숏(§5.9) ────────────────────────────────────

def cleanup_for_save(doc: dict[str, Any]) -> None:
    """저장 때 이름 · 항목이 모두 빈 키맨과 빈 항목을 뺀다(§5.2)."""
    ks = keymen(doc)
    removed = False
    for k in ks:
        before = len(k["items"])
        k["items"] = [it for it in k["items"] if (it.get("text") or "").strip()]
        if len(k["items"]) != before:
            for j, it in enumerate(k["items"]):
                it["order"] = j
    keep = [k for k in ks if (k.get("name") or "").strip() or k["items"]]
    if len(keep) != len(ks):
        removed = True
    doc["form"]["keymen"] = keep
    for i, k in enumerate(keep):
        k["order"] = i
    if removed:
        rebalance(doc)


def snapshot(doc: dict[str, Any]) -> dict[str, Any]:
    form = copy.deepcopy(doc["form"])
    nc = {(q.get("target") or {}).get("id") for q in open_questions(doc) if (q.get("target") or {}).get("kind") == "item"}
    flat = []
    for k in form["keymen"]:
        for it in k["items"]:
            it["needs_confirmation"] = it["id"] in nc
            flat.append({"id": it["id"], "code": it["code"], "text": it["text"], "short": it.get("short"),
                         "keyman_id": k["id"], "keyman_name": k.get("name"), "keyman_weight": k.get("weight"),
                         "needs_confirmation": it["id"] in nc, "evidence": it.get("evidence") or [],
                         "entities": it.get("entities") or [], "source": it.get("source")})
    form["author_note_internal"] = True
    return {
        "form": form,
        "context": copy.deepcopy(doc.get("context") or {}),
        "keymen": [{"id": k["id"], "name": k.get("name") or "", "weight": k.get("weight"), "color_index": k.get("color_index", 0),
                    "order": k.get("order", 0), "item_ids": [it["id"] for it in k["items"]]} for k in form["keymen"]],
        "items_flat": flat,
        "customer_questions": [{"id": q["id"], "text": q["text"], "short_label": q.get("short_label"), "status": q["status"],
                                "keyman_id": q.get("keyman_id"), "target": q.get("target")}
                               for q in doc.get("questions") or [] if q.get("status") != "dismissed"],
        "source_files": [{"file_id": f["file_id"], "name": f["name"], "type_label": f.get("type_label")}
                         for f in doc.get("files") or [] if f.get("status") != "failed"],
        "author_note": {"value": field_value(doc, "author_note"), "internal": True},
    }


def snapshot_change_count(prev: dict[str, Any] | None, cur: dict[str, Any]) -> int:
    if prev is None:
        return len(cur["items_flat"]) + sum(1 for f in FIELDS if (cur["form"][f] or {}).get("value"))
    return len(diff_snapshots(prev, cur))


def diff_snapshots(a: dict[str, Any], b: dict[str, Any]) -> list[dict[str, Any]]:
    """항목 id 기준 결정적 비교(§6.5)."""
    out: list[dict[str, Any]] = []
    for f in FIELDS:
        va = (a["form"].get(f) or {}).get("value")
        vb = (b["form"].get(f) or {}).get("value")
        if va != vb:
            kind = "added" if va is None else ("removed" if vb is None else "changed")
            out.append({"target": {"kind": "field", "id": f}, "kind": kind, "label": FIELD_LABELS[f], "before": va, "after": vb})
    ka = {k["id"]: k for k in a.get("keymen") or []}
    kb = {k["id"]: k for k in b.get("keymen") or []}
    for kid, k in kb.items():
        if kid not in ka:
            out.append({"target": {"kind": "keyman", "id": kid}, "kind": "added", "label": k["name"], "before": None, "after": k["name"]})
        elif ka[kid]["name"] != k["name"]:
            out.append({"target": {"kind": "keyman", "id": kid}, "kind": "changed", "label": k["name"],
                        "before": ka[kid]["name"], "after": k["name"]})
    for kid, k in ka.items():
        if kid not in kb:
            out.append({"target": {"kind": "keyman", "id": kid}, "kind": "removed", "label": k["name"], "before": k["name"], "after": None})
    wa = {k["id"]: k.get("weight") for k in a.get("keymen") or []}
    wb = {k["id"]: k.get("weight") for k in b.get("keymen") or []}
    if len(wb) > 1 and any(wa.get(kid) != w for kid, w in wb.items() if kid in wa):
        out.append({"target": {"kind": "weights", "id": "weights"}, "kind": "changed", "label": "가중치",
                    "before": {k: v for k, v in wa.items()}, "after": {k: v for k, v in wb.items()}})
    ia = {i["id"]: i for i in a.get("items_flat") or []}
    ib = {i["id"]: i for i in b.get("items_flat") or []}
    for iid, it in ib.items():
        if iid not in ia:
            out.append({"target": {"kind": "item", "id": iid}, "kind": "added", "label": it.get("keyman_name"),
                        "before": None, "after": it, "keyman_id": it.get("keyman_id")})
        else:
            prev = ia[iid]
            if (prev["text"] != it["text"] or prev.get("keyman_id") != it.get("keyman_id")
                    or [e["file_id"] for e in prev.get("evidence") or []] != [e["file_id"] for e in it.get("evidence") or []]
                    or prev.get("needs_confirmation") != it.get("needs_confirmation")):
                out.append({"target": {"kind": "item", "id": iid}, "kind": "changed", "label": it.get("keyman_name"),
                            "before": prev, "after": it, "keyman_id": it.get("keyman_id")})
    for iid, it in ia.items():
        if iid not in ib:
            out.append({"target": {"kind": "item", "id": iid}, "kind": "removed", "label": it.get("keyman_name"),
                        "before": it, "after": None, "keyman_id": it.get("keyman_id")})
    return out


# ── 완성도 · 규칙형 보강할 곳(§7.3) ─────────────────────

LLM_ITEM_KINDS = ("unquantified", "vague_scope", "ambiguous", "conflict", "capability_unclear")


def completeness(doc: dict[str, Any], gaps: list[dict[str, Any]] | None = None) -> int:
    """§7.3.1 — round(100 × (충족 + 0.5 × 고객 확인) / 적용 항목 수)."""
    gaps = gaps or []
    met = 0.0
    total = 0
    for f in ("project_name", "customer_name", "final_audience"):
        total += 1
        if field_value(doc, f):
            met += 1
        elif _deferred(gaps, lambda g, f=f: g["target"].get("kind") == "field" and g["target"].get("field") == f):
            met += 0.5
    named = [k for k in keymen(doc) if (k.get("name") or "").strip() or k["items"]]
    total += 1
    if named:
        met += 1
    if len(named) >= 2:
        total += 1
        if doc["form"].get("weights_mode") == "custom":
            met += 1
        elif _deferred(gaps, lambda g: g["kind"] == "default_weights"):
            met += 0.5
    for k in named:
        total += 1
        n_items = sum(1 for it in k["items"] if (it.get("text") or "").strip())
        if n_items >= 2:
            met += 1
        elif _deferred(gaps, lambda g, k=k: g["kind"] == "too_few_items" and g["target"].get("keyman_id") == k["id"]):
            met += 0.5
    item_ids = {it["id"] for k in named for it in k["items"] if (it.get("text") or "").strip()}
    item_gaps: dict[str, list[dict[str, Any]]] = {}
    keyman_gaps: list[dict[str, Any]] = []
    for g in gaps:
        if g["origin"] == "rule":
            continue
        t = g["target"]
        if t.get("kind") == "item" and t.get("item_id") in item_ids:
            item_gaps.setdefault(t["item_id"], []).append(g)
        elif t.get("kind") == "keyman":
            keyman_gaps.append(g)
    for iid in item_ids:
        total += 1
        gs = item_gaps.get(iid, [])
        open_ = [g for g in gs if g["status"] not in ("applied", "deferred", "resolved_by_form")]
        if not open_ and not any(g["status"] == "deferred" for g in gs):
            met += 1
        elif not open_:
            met += 0.5
    for g in keyman_gaps:
        total += 1
        if g["status"] in ("applied", "resolved_by_form"):
            met += 1
        elif g["status"] == "deferred":
            met += 0.5
    if total == 0:
        return 0
    return max(0, min(100, round(100 * met / total)))


def _deferred(gaps: list[dict[str, Any]], pred: Any) -> bool:
    return any(g["status"] == "deferred" and pred(g) for g in gaps)


def rule_gap_resolved(doc: dict[str, Any], gap: dict[str, Any]) -> bool:
    """규칙형 보강할 곳이 폼에서 이미 충족됐나(§3.2 질의 중 폼 수정)."""
    kind = gap["kind"]
    t = gap["target"]
    if kind == "empty_field":
        return bool(field_value(doc, t.get("field") or ""))
    if kind == "default_weights":
        return doc["form"].get("weights_mode") == "custom" or len(keymen(doc)) < 2
    if kind == "too_few_items":
        km = find_keyman(doc, t.get("keyman_id") or "")
        return km is None or sum(1 for it in km["items"] if (it.get("text") or "").strip()) >= 2
    if kind == "no_keyman":
        return any((k.get("name") or "").strip() for k in keymen(doc))
    return False


def stale_signature(doc: dict[str, Any]) -> str:
    """세션 분석 뒤 폼이 '크게' 바뀌었나 판단용 — 키맨 · 항목 구성과 문장."""
    body = [[k["id"], [(it["id"], (it.get("text") or "").strip()) for it in k["items"]]] for k in keymen(doc)]
    return hashlib.sha1(json.dumps(body, ensure_ascii=False).encode()).hexdigest()[:16]
