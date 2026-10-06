"""서비스 레지스트리(config/services.yaml) 읽기."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import yaml

from .env import repo_root


@dataclass(frozen=True)
class ServiceInfo:
    name: str
    port: int
    title: str = ""
    kind: str = "api"                      # api | edge
    worker: bool = False
    feature: str | None = None             # RQ, SB, … (기능 서비스만)
    consumes: tuple[str, ...] = field(default_factory=tuple)
    owns: tuple[str, ...] = field(default_factory=tuple)

    @property
    def module(self) -> str:
        return module_name(self.name)


def module_name(service: str) -> str:
    return "winmate_" + service.replace("-", "_")


@lru_cache(maxsize=1)
def _load() -> dict:
    path = repo_root() / "config" / "services.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def services() -> dict[str, ServiceInfo]:
    raw = _load().get("services", {})
    out: dict[str, ServiceInfo] = {}
    for name, spec in raw.items():
        out[name] = ServiceInfo(
            name=name,
            port=int(spec["port"]),
            title=spec.get("title", ""),
            kind=spec.get("kind", "api"),
            worker=bool(spec.get("worker", False)),
            feature=spec.get("feature"),
            consumes=tuple(spec.get("consumes") or ()),
            owns=tuple(spec.get("owns") or ()),
        )
    return out


def get_service(name: str) -> ServiceInfo:
    try:
        return services()[name]
    except KeyError as exc:
        raise KeyError(f"등록되지 않은 서비스: {name} (config/services.yaml)") from exc


def service_port(name: str) -> int:
    return get_service(name).port


def redis_port() -> int:
    return int(_load().get("infra", {}).get("redis", {}).get("port", 5379))


def web_dev_port() -> int:
    return int(_load().get("infra", {}).get("web_dev", {}).get("port", 5001))


def feature_services() -> dict[str, ServiceInfo]:
    return {k: v for k, v in services().items() if v.feature}


def can_call(caller: str | None, target: str) -> bool:
    """caller 가 target 을 호출해도 되는가(consumes 목록 기준)."""
    if caller is None or caller == target:
        return True
    info = services().get(caller)
    if info is None:
        return False
    return target in info.consumes
