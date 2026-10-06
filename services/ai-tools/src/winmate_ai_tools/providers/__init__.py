"""제공자 레지스트리 — `<CAP>_PROVIDER` 값 → 제공자 객체.

    gemini(gemini_grounding) · openai_compat(openai) · internal · mock

테스트는 `REGISTRY["fake"] = FakeProvider` 로 가짜 제공자를 넣고 `LLM_PROVIDER=fake` 로 고른다.
"""
from __future__ import annotations

from collections.abc import Callable

from ..errors import not_configured
from .base import Provider

REGISTRY: dict[str, Callable[[], Provider]] = {}
_instances: dict[str, tuple[Callable[[], Provider], Provider]] = {}


def _register_defaults() -> None:
    from .gemini import GeminiProvider
    from .internal import InternalProvider
    from .mock import MockProvider
    from .openai_compat import OpenAICompatProvider

    REGISTRY.setdefault("gemini", GeminiProvider)
    REGISTRY.setdefault("openai_compat", OpenAICompatProvider)
    REGISTRY.setdefault("internal", InternalProvider)
    REGISTRY.setdefault("mock", MockProvider)


_ALIASES = {"gemini_grounding": "gemini", "openai": "openai_compat"}


def get(name: str) -> Provider:
    _register_defaults()
    key = _ALIASES.get(name, name)
    factory = REGISTRY.get(key)
    if factory is None:
        raise not_configured(f"알 수 없는 제공자 '{name}'", provider=name, known=sorted(REGISTRY))
    cached = _instances.get(key)
    if cached is None or cached[0] is not factory:
        cached = _instances[key] = (factory, factory())
    return cached[1]


def reset() -> None:
    """테스트용: 만들어 둔 제공자 객체(클라이언트 캐시 포함)를 버린다."""
    _instances.clear()
