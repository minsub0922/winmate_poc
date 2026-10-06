"""주장 · 인용 · 출처 조작(§5.4 · §7.6.5) — 버전 문서 안에서 상태를 다시 모은다."""
from __future__ import annotations

from typing import Any

from winmate_common.ids import now_iso

from . import verify
from .store import nid


def citations_of(version: dict[str, Any], claim_id: str, *, include_dropped: bool = False) -> list[dict[str, Any]]:
    return [c for c in version.get("citations") or [] if c.get("claim_id") == claim_id and (include_dropped or not c.get("dropped"))]


def fix_confirmed(version: dict[str, Any], claim_id: str) -> bool:
    return any(f.get("claim_id") == claim_id and f.get("status") == "ok" for f in (version.get("fix_items") or {}).values())


def recompute(version: dict[str, Any], claim_id: str) -> dict[str, Any]:
    claim = (version.get("claims") or {}).get(claim_id)
    if claim is None:
        return {}
    cits = citations_of(version, claim_id)
    srcs = version.get("sources") or {}
    checking = any(srcs.get(c["source_id"], {}).get("state") == "checking" for c in cits)
    agg = verify.aggregate(claim, cits, srcs, confirmed=claim.get("status") == "confirmed" or fix_confirmed(version, claim_id),
                           checking=checking)
    claim["status"] = agg["status"]
    claim["label"] = agg["label"]
    claim["n_needs"] = agg["n_needs"]
    claim["conflict"] = agg["conflict"]
    return claim


def recompute_all(version: dict[str, Any]) -> None:
    for cid in list((version.get("claims") or {}).keys()):
        recompute(version, cid)


def refresh_source_states(version: dict[str, Any]) -> None:
    """인용이 하나도 남지 않은 출처는 제외(직접 뺀 것 · 원문으로 대체된 요약)."""
    live: dict[str, int] = {}
    for c in version.get("citations") or []:
        if not c.get("dropped"):
            live[c["source_id"]] = live.get(c["source_id"], 0) + 1
    for sid, s in (version.get("sources") or {}).items():
        if s.get("state") == "checking":
            continue
        if live.get(sid):
            if s.get("state") == "excluded" and s.get("excluded_reason") in ("superseded", "irrelevant"):
                s["state"] = "used"
                s["excluded_reason"] = None
            continue
        if s.get("state") != "excluded" and s.get("kind") != "user" and s.get("pin_used") is not True:
            s["state"] = "excluded"
            reasons = {c.get("dropped_reason") for c in version.get("citations") or [] if c.get("source_id") == sid}
            s["excluded_reason"] = "superseded" if "superseded" in reasons else (s.get("excluded_reason") or "irrelevant")


def remove_citation(version: dict[str, Any], claim_id: str, source_id: str) -> bool:
    hit = False
    for c in version.get("citations") or []:
        if c.get("claim_id") == claim_id and c.get("source_id") == source_id and not c.get("dropped"):
            c["dropped"] = True
            c["dropped_reason"] = "removed_by_user"
            hit = True
    if hit:
        recompute(version, claim_id)
        refresh_source_states(version)
    return hit


def user_source(version: dict[str, Any], *, name: str, value: str, note: str | None = None) -> str:
    sid = nid("src")
    version.setdefault("sources", {})[sid] = {
        "id": sid, "kind": "user", "subtype": "", "title": "직접 입력", "publisher": name, "url": None, "published_at": now_iso()[:10],
        "published_basis": "meta", "retrieved_at": now_iso(), "authority": 2, "classification": "internal", "state": "used",
        "mode": "user", "areas": [], "value": value, "note": note,
    }
    return sid


def replace_citations(version: dict[str, Any], claim_id: str, source_id: str, quote: str, *, page: int | None = None,
                      status: str = "matched") -> None:
    for c in version.get("citations") or []:
        if c.get("claim_id") == claim_id and not c.get("dropped"):
            c["dropped"] = True
            c["dropped_reason"] = "replaced"
    version.setdefault("citations", []).append({
        "claim_id": claim_id, "source_id": source_id, "quote": quote, "highlight": None, "page": page,
        "check": {"quote": "ok", "numbers": "ok", "entities": "na", "date": "ok"}, "status": status, "reason_code": None,
        "reason_text": "", "verified_at": now_iso(), "value": None,
    })
    refresh_source_states(version)


def area_claims(version: dict[str, Any], area: str) -> list[dict[str, Any]]:
    return [c for c in (version.get("claims") or {}).values() if c.get("area") == area]
