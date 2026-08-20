from __future__ import annotations

from dataclasses import dataclass, field

from risa.core.graph_store import GraphStore
from risa.core.models import Event, Pattern, StructuralPattern, StructureDelta


@dataclass
class RisaState:
    graph: GraphStore = field(default_factory=GraphStore)
    patterns: dict[str, Pattern] = field(default_factory=dict)
    structural_patterns: dict[str, StructuralPattern] = field(default_factory=dict)
    structure_deltas: dict[str, StructureDelta] = field(default_factory=dict)
    events_by_id: dict[str, Event] = field(default_factory=dict)
    actor_action_effect_counts: dict[str, dict[str, dict[str, int]]] = field(default_factory=dict)
    action_effect_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    actor_action_context_effect_counts: dict[str, dict[str, dict[str, dict[str, int]]]] = field(default_factory=dict)
    action_context_effect_counts: dict[str, dict[str, dict[str, int]]] = field(default_factory=dict)
    prediction_validation_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    prediction_competition_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    concept_members: dict[str, list[str]] = field(default_factory=dict)
    activation_index: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "graph": self.graph.to_dict(),
            "patterns": {key: pattern.to_dict() for key, pattern in self.patterns.items()},
            "structural_patterns": {
                key: pattern.to_dict() for key, pattern in self.structural_patterns.items()
            },
            "structure_deltas": {key: delta.to_dict() for key, delta in self.structure_deltas.items()},
            "events": {key: event.to_dict() for key, event in self.events_by_id.items()},
            "actor_action_effect_counts": self.actor_action_effect_counts,
            "action_effect_counts": self.action_effect_counts,
            "actor_action_context_effect_counts": self.actor_action_context_effect_counts,
            "action_context_effect_counts": self.action_context_effect_counts,
            "prediction_validation_stats": self.prediction_validation_stats,
            "prediction_competition_stats": self.prediction_competition_stats,
            "concept_members": self.concept_members,
            "activation_index": self.activation_index,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RisaState":
        state = cls()
        state.graph = GraphStore.from_dict(data.get("graph", {}))
        for key, pattern_data in data.get("patterns", {}).items():
            state.patterns[key] = Pattern(
                id=pattern_data["id"],
                signature=pattern_data["signature"],
                event_count=pattern_data.get("event_count", 0),
                actors=set(pattern_data.get("actors", [])),
                actions=set(pattern_data.get("actions", [])),
                effects=set(pattern_data.get("effects", [])),
                support=pattern_data.get("support", 0),
                context_tags=set(pattern_data.get("context_tags", [])),
                validation_score=pattern_data.get("validation_score", 0.5),
            )
        for key, pattern_data in data.get("structural_patterns", {}).items():
            state.structural_patterns[key] = StructuralPattern(
                id=pattern_data["id"],
                signature=pattern_data["signature"],
                role_signature=pattern_data["role_signature"],
                support=pattern_data.get("support", 0),
                actions=set(pattern_data.get("actions", [])),
                effects=set(pattern_data.get("effects", [])),
                actors=set(pattern_data.get("actors", [])),
                context_tags=set(pattern_data.get("context_tags", [])),
                member_pattern_ids=set(pattern_data.get("member_pattern_ids", [])),
                validation_score=pattern_data.get("validation_score", 0.5),
            )
        for key, delta_data in data.get("structure_deltas", {}).items():
            state.structure_deltas[key] = StructureDelta(
                id=delta_data["id"],
                source_pattern_id=delta_data["source_pattern_id"],
                target_pattern_id=delta_data["target_pattern_id"],
                role_signature=delta_data["role_signature"],
                operations=list(delta_data.get("operations", [])),
                support=delta_data.get("support", 0),
                context_tags=set(delta_data.get("context_tags", [])),
            )
        for key, event_data in data.get("events", {}).items():
            state.events_by_id[key] = Event(**event_data)
        state.actor_action_effect_counts = data.get("actor_action_effect_counts", {})
        state.action_effect_counts = data.get("action_effect_counts", {})
        state.actor_action_context_effect_counts = data.get("actor_action_context_effect_counts", {})
        state.action_context_effect_counts = data.get("action_context_effect_counts", {})
        state.prediction_validation_stats = data.get("prediction_validation_stats", {})
        state.prediction_competition_stats = data.get("prediction_competition_stats", {})
        state.concept_members = data.get("concept_members", {})
        state.activation_index = data.get("activation_index", {})
        return state
