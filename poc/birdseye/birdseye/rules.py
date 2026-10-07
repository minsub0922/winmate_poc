"""PlacementRule 로더 — 시드 룰 + 프로젝트별 파라미터 덮어쓰기."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

SEED = Path(__file__).resolve().parent / "seed" / "placement_rules.json"
_BASE = json.loads(SEED.read_text(encoding="utf-8"))["rules"]
_BY_ID = {r["id"]: r for r in _BASE}


class Rules:
    def __init__(self, overrides: dict | None = None):
        self.overrides = overrides or {}

    def rule(self, rid: str) -> dict:
        r = copy.deepcopy(_BY_ID[rid])
        ov = self.overrides.get(rid) or {}
        for k, v in ov.items():
            if k in r["params"]:
                r["params"][k] = v
        r["overridden"] = sorted(k for k in ov if k in _BY_ID[rid]["params"])
        return r

    def p(self, rid: str, key: str):
        ov = self.overrides.get(rid) or {}
        if key in ov:
            return ov[key]
        return _BY_ID[rid]["params"][key]

    def all(self) -> list[dict]:
        return [self.rule(r["id"]) for r in _BASE]

    def render(self, rid: str) -> str:
        """식의 {{param}} 을 현재 값으로 채운 문자열."""
        r = self.rule(rid)

        def sub(m):
            v = r["params"].get(m.group(1))
            if isinstance(v, (int, float)):
                return f"{v:,g}"
            return str(v)

        return re.sub(r"\{\{(\w+)\}\}", sub, r["expression"])


def rule_ids() -> list[str]:
    return [r["id"] for r in _BASE]
