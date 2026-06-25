from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidencePreset:
    name: str
    summary: str
    topic: str
    include_azure: bool = False
    include_dataverse: bool = False
    include_comments: bool = False
    limit: int = 10
    max_page_chars: int = 8000


BUILTIN_PRESETS: dict[str, EvidencePreset] = {
    "architecture": EvidencePreset(
        name="architecture",
        summary="Architecture, design decision, integration, and dependency evidence.",
        topic="architecture design decision integration dependency",
        include_azure=True,
        limit=15,
    ),
    "dataverse": EvidencePreset(
        name="dataverse",
        summary="Dataverse, Power Platform, solutions, connectors, and connection reference evidence.",
        topic="Dataverse Power Platform solution connector connection reference",
        include_dataverse=True,
        limit=10,
    ),
    "delivery": EvidencePreset(
        name="delivery",
        summary="Delivery trail, implementation ticket, status, release, and blocker evidence.",
        topic="delivery implementation ticket story epic release status blocker defect",
        include_comments=True,
        limit=20,
    ),
    "operations": EvidencePreset(
        name="operations",
        summary="Operational readiness, deployment, monitoring, alerting, and runtime evidence.",
        topic="operations deployment monitoring alert incident configuration resource health",
        include_azure=True,
        include_comments=True,
        limit=20,
    ),
    "performance": EvidencePreset(
        name="performance",
        summary="Performance, scaling, APIM, Functions, capacity, and timeout evidence.",
        topic="APIM Functions scaling performance capacity timeout",
        include_azure=True,
        include_comments=True,
        limit=20,
    ),
    "risk": EvidencePreset(
        name="risk",
        summary="Known risk, blocker, incident, defect, security concern, and mitigation evidence.",
        topic="risk blocker incident defect vulnerability unsupported dependency mitigation warning failed unresolved",
        include_azure=True,
        include_comments=True,
        limit=20,
    ),
}


def list_presets() -> list[EvidencePreset]:
    return [BUILTIN_PRESETS[name] for name in sorted(BUILTIN_PRESETS)]


def get_preset(name: str) -> EvidencePreset:
    try:
        return BUILTIN_PRESETS[name]
    except KeyError as exc:
        available = ", ".join(sorted(BUILTIN_PRESETS))
        raise ValueError(f"Unknown preset '{name}'. Available presets: {available}") from exc
