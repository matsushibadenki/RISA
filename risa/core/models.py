from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Node:
    id: str
    kind: str
    label: str
    attributes: dict[str, str] = field(default_factory=dict)
    abstraction_level: int = 0
    created_at: int = 0
    usage_count: int = 0
    stability: float = 0.0
    recent_activity: float = 0.0
    energy: float = 0.5
    last_activated_at: int = 0
    dormant: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Edge:
    source: str
    target: str
    relation_type: str
    context_tags: tuple[str, ...] = ()
    evidence_count: int = 0
    reliability: float = 0.0
    plasticity: float = 1.0
    last_updated: int = 0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["context_tags"] = list(self.context_tags)
        return data


@dataclass
class Event:
    id: str
    timestamp: int
    actor: str
    action: str
    target: str | None = None
    observed_effects: list[str] = field(default_factory=list)
    context_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Episode:
    id: str
    events: list[Event]
    source: str = "unknown"


@dataclass
class Pattern:
    id: str
    signature: str
    event_count: int = 0
    actors: set[str] = field(default_factory=set)
    actions: set[str] = field(default_factory=set)
    effects: set[str] = field(default_factory=set)
    support: int = 0
    context_tags: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "signature": self.signature,
            "event_count": self.event_count,
            "actors": sorted(self.actors),
            "actions": sorted(self.actions),
            "effects": sorted(self.effects),
            "support": self.support,
            "context_tags": sorted(self.context_tags),
        }


@dataclass
class PredictionQuery:
    actor: str
    action: str
    target: str | None = None
    context_tags: list[str] = field(default_factory=list)


@dataclass
class PredictionResult:
    predicted_effects: list[str]
    score: float
    supporting_paths: list[list[str]] = field(default_factory=list)
    evidence_event_ids: list[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
