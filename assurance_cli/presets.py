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
    "dataverse": EvidencePreset(
        name="dataverse",
        summary="Evidence about Dataverse and Power Platform usage.",
        topic="Dataverse Power Platform solution connector connection reference",
        include_dataverse=True,
        limit=10,
    ),
    "scaling": EvidencePreset(
        name="scaling",
        summary="Evidence about scaling, performance, APIM, and Functions.",
        topic="APIM Functions scaling performance capacity timeout",
        include_azure=True,
        include_comments=True,
        limit=20,
    ),
    "architecture": EvidencePreset(
        name="architecture",
        summary="Architecture, design decision, integration, and dependency evidence.",
        topic="architecture design decision integration dependency",
        include_azure=True,
        limit=15,
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
