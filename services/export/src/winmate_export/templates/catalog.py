"""런타임 카탈로그 — catalog.json 을 한 번 읽어 코드 · 역할 · 업종으로 찾는다."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).resolve().parent / "catalog.json"

SUMMARY_KEYS = (
    "code", "display_code", "name", "sheet_role", "role_name", "section", "section_name", "kind", "family",
    "industry", "industry_name", "industry_scheme", "solution", "solution_name", "variant", "product_count",
    "proposal_types", "description", "when", "status", "base", "archetype", "thumb_kind", "thumb_n", "data_shape",
)


def normalize_code(code: str) -> str:
    return re.sub(r"[\s·•]", "", code or "").upper()


class Catalog:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.templates: list[dict[str, Any]] = data["templates"]
        self._by_code = {normalize_code(t["code"]): t for t in self.templates}
        self.aliases: dict[str, dict[str, Any]] = {normalize_code(k): v for k, v in (data.get("aliases") or {}).items()}

    # ── 찾기 ───────────────────────────────────────────
    def get(self, code: str, slots: dict[str, Any] | None = None) -> dict[str, Any] | None:
        key = normalize_code(code)
        t = self._by_code.get(key)
        if t is not None:
            return t
        alias = self.aliases.get(key)
        if alias:
            target = alias.get("default")
            by = alias.get("by")
            if by and slots and isinstance(slots.get(by), list):
                target = alias.get("options", {}).get(str(len(slots[by])), target)
            return self._by_code.get(normalize_code(target or ""))
        return None

    def search(
        self,
        *,
        role: str | None = None,
        section: str | None = None,
        industry: str | None = None,
        proposal_type: str | None = None,
        q: str | None = None,
        solution: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        codes: list[str] | None = None,
        include_internal: bool = False,
    ) -> list[dict[str, Any]]:
        roles = {r.strip().upper() for r in role.split(",")} if role else None
        sections = {s.strip() for s in section.split(",")} if section else None
        kinds = {k.strip() for k in kind.split(",")} if kind else None
        code_set = {normalize_code(c) for c in codes} if codes else None
        words = [w for w in re.split(r"\s+", (q or "").strip().lower()) if w]
        out = []
        for t in self.templates:
            if not include_internal and t["status"] == "internal" and not code_set:
                continue
            if code_set is not None and normalize_code(t["code"]) not in code_set:
                continue
            if roles and t["sheet_role"] not in roles:
                continue
            if sections and t["section"] not in sections:
                continue
            if kinds and t["kind"] not in kinds:
                continue
            if status and t["status"] != status:
                continue
            if proposal_type and proposal_type not in t["proposal_types"]:
                continue
            if solution and (t.get("solution") or "").upper() != solution.upper():
                continue
            if industry:
                ind = industry.upper()
                # 업종 템플릿은 그 업종만, 범용은 늘 포함(템플릿 고르기 목록 = 업종판 + 범용)
                if t.get("industry") and ind != t["industry"] and ind not in (t.get("industry_aliases") or []):
                    continue
            if words:
                hay = " ".join(str(t.get(k) or "") for k in ("code", "display_code", "name", "when", "role_name",
                                                            "industry_name", "solution_name", "sample_title")).lower()
                if not all(w in hay for w in words):
                    continue
            out.append(t)
        if industry:
            # 업종 레이아웃을 목록 맨 앞에(10-proposal §10.6)
            out.sort(key=lambda t: 0 if t.get("industry") else 1)
        return out

    def stats(self) -> dict[str, Any]:
        return self.data["stats"]

    @staticmethod
    def summary(t: dict[str, Any]) -> dict[str, Any]:
        d = {k: t.get(k) for k in SUMMARY_KEYS}
        d["thumb_url"] = f"/api/export/v1/templates/{t['code']}/thumbnail.png"
        d["slot_count"] = len(t["slots"])
        return d


@lru_cache(maxsize=1)
def catalog() -> Catalog:
    return Catalog(json.loads(CATALOG_PATH.read_text(encoding="utf-8")))
