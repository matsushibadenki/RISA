from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

from risa.core.graph_store import GraphStore
from risa.core.models import (
    ApplicabilityHypothesis,
    ChangeHypothesis,
    Event,
    Pattern,
    StructuralAdaptationCandidate,
    StructuralPattern,
    StructuralPrimitive,
    StateVariableSpec,
    StructureDelta,
    UnnamedConceptCandidate,
)

CURRENT_SCHEMA_VERSION = 4


@dataclass
class RisaState:
    schema_version: int = CURRENT_SCHEMA_VERSION
    graph: GraphStore = field(default_factory=GraphStore)
    patterns: dict[str, Pattern] = field(default_factory=dict)
    structural_patterns: dict[str, StructuralPattern] = field(default_factory=dict)
    structural_primitives: dict[str, StructuralPrimitive] = field(default_factory=dict)
    structure_deltas: dict[str, StructureDelta] = field(default_factory=dict)
    structural_adaptation_candidates: dict[str, StructuralAdaptationCandidate] = field(
        default_factory=dict
    )
    event_primitive_ids: dict[str, list[str]] = field(default_factory=dict)
    exclusive_state_groups: dict[str, set[str]] = field(default_factory=dict)
    state_variable_specs: dict[str, StateVariableSpec] = field(default_factory=dict)
    events_by_id: dict[str, Event] = field(default_factory=dict)
    actor_action_effect_counts: dict[str, dict[str, dict[str, int]]] = field(default_factory=dict)
    action_effect_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    actor_action_context_effect_counts: dict[str, dict[str, dict[str, dict[str, int]]]] = field(default_factory=dict)
    action_context_effect_counts: dict[str, dict[str, dict[str, int]]] = field(default_factory=dict)
    actor_action_target_context_effect_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    action_target_context_effect_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    action_target_role_context_effect_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    prediction_validation_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    prediction_competition_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    concept_members: dict[str, list[str]] = field(default_factory=dict)
    activation_index: dict[str, list[str]] = field(default_factory=dict)
    change_hypotheses: dict[str, ChangeHypothesis] = field(default_factory=dict)
    applicability_hypotheses: dict[str, ApplicabilityHypothesis] = field(default_factory=dict)
    evidence_index: dict[str, list[str]] = field(default_factory=dict)
    candidate_inference_index: dict[str, list[str]] = field(default_factory=dict)
    compacted_role_readouts: dict[str, str] = field(default_factory=dict)
    unnamed_concept_candidates: dict[str, UnnamedConceptCandidate] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "graph": self.graph.to_compact_dict(),
            "patterns": {
                key: _pattern_persistence_record(key, pattern)
                for key, pattern in self.patterns.items()
            },
            "structural_patterns": {
                key: _structural_pattern_persistence_record(key, pattern)
                for key, pattern in self.structural_patterns.items()
            },
            "structural_primitives": {
                key: _primitive_persistence_record(primitive)
                for key, primitive in self.structural_primitives.items()
            },
            "structure_deltas": {key: delta.to_dict() for key, delta in self.structure_deltas.items()},
            "structural_adaptation_candidates": {
                key: candidate.to_dict()
                for key, candidate in self.structural_adaptation_candidates.items()
            },
            "event_primitive_ids": self.event_primitive_ids,
            "exclusive_state_groups": {
                key: sorted(values) for key, values in self.exclusive_state_groups.items()
            },
            "state_variable_specs": {
                key: spec.to_dict() for key, spec in self.state_variable_specs.items()
            },
            "events": {
                key: _event_persistence_record(event)
                for key, event in self.events_by_id.items()
            },
            "prediction_validation_stats": self.prediction_validation_stats,
            "prediction_competition_stats": self.prediction_competition_stats,
            "concept_members": self.concept_members,
            "change_hypotheses": {
                key: hypothesis.to_dict()
                for key, hypothesis in self.change_hypotheses.items()
            },
            "applicability_hypotheses": {
                key: hypothesis.to_dict()
                for key, hypothesis in self.applicability_hypotheses.items()
            },
            "candidate_evaluations": {
                key: _candidate_evaluation_record(candidate)
                for key, candidate in self.unnamed_concept_candidates.items()
                if _candidate_has_persisted_evaluation(candidate)
            },
            "derived_candidates": {
                key: candidate.to_dict()
                for key, candidate in self.unnamed_concept_candidates.items()
                if candidate.derivation_generation > 0
            },
            "compacted_role_readouts": dict(sorted(self.compacted_role_readouts.items())),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RisaState":
        schema_version = int(data.get("schema_version", 1))
        if schema_version > CURRENT_SCHEMA_VERSION:
            raise ValueError(
                f"state schema version {schema_version} is newer than supported "
                f"version {CURRENT_SCHEMA_VERSION}"
            )
        state = cls(schema_version=CURRENT_SCHEMA_VERSION)
        state.graph = GraphStore.from_dict(data.get("graph", {}))
        for key, pattern_data in data.get("patterns", {}).items():
            state.patterns[key] = Pattern(
                id=pattern_data.get("id", key),
                signature=pattern_data.get(
                    "signature", key.removeprefix("pattern:")
                ),
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
                id=pattern_data.get("id", key),
                signature=pattern_data.get("signature", key),
                role_signature=pattern_data["role_signature"],
                support=pattern_data.get("support", 0),
                actions=set(pattern_data.get("actions", [])),
                effects=set(pattern_data.get("effects", [])),
                actors=set(pattern_data.get("actors", [])),
                context_tags=set(pattern_data.get("context_tags", [])),
                member_pattern_ids=set(pattern_data.get("member_pattern_ids", [])),
                validation_score=pattern_data.get("validation_score", 0.5),
            )
        for key, primitive_data in data.get("structural_primitives", {}).items():
            state.structural_primitives[key] = StructuralPrimitive(
                id=primitive_data.get("id", key),
                relation_type=primitive_data["relation_type"],
                role_signature=primitive_data["role_signature"],
                input_conditions=set(primitive_data.get("input_conditions", [])),
                input_state_conditions=set(primitive_data.get("input_state_conditions", [])),
                learned_state_conditions=set(primitive_data.get("learned_state_conditions", [])),
                consumed_states=set(primitive_data.get("consumed_states", [])),
                state_group_updates=dict(primitive_data.get("state_group_updates", {})),
                numeric_preconditions={
                    key: float(value)
                    for key, value in primitive_data.get("numeric_preconditions", {}).items()
                },
                state_variable_deltas={
                    key: float(value)
                    for key, value in primitive_data.get("state_variable_deltas", {}).items()
                },
                output_state=primitive_data.get("output_state", ""),
                output_states=set(
                    primitive_data.get("output_states", [])
                    or ([primitive_data["output_state"]] if primitive_data.get("output_state") else [])
                ),
                temporal_constraint=primitive_data.get("temporal_constraint", "event_to_effect"),
                context_tags=set(primitive_data.get("context_tags", [])),
                member_pattern_ids=set(primitive_data.get("member_pattern_ids", [])),
                evidence_event_ids=set(primitive_data.get("evidence_event_ids", [])),
                support=primitive_data.get("support", 0),
                validation_score=primitive_data.get("validation_score", 0.5),
                reuse_score=primitive_data.get("reuse_score", 0.0),
                compression_proxy=primitive_data.get("compression_proxy", 0.0),
                replay_count=primitive_data.get("replay_count", 0),
                replay_success_count=primitive_data.get("replay_success_count", 0),
                replay_score=primitive_data.get("replay_score", 0.5),
                deployment_replay_count=primitive_data.get("deployment_replay_count", 0),
                deployment_replay_success_count=primitive_data.get(
                    "deployment_replay_success_count", 0
                ),
                deployment_replay_score=primitive_data.get("deployment_replay_score", 0.5),
                perturbation_replay_count=primitive_data.get("perturbation_replay_count", 0),
                perturbation_replay_success_count=primitive_data.get(
                    "perturbation_replay_success_count", 0
                ),
                perturbation_replay_score=primitive_data.get("perturbation_replay_score", 0.5),
                superseded_by=set(primitive_data.get("superseded_by", [])),
                adoption_score=primitive_data.get("adoption_score", 0.0),
                adopted=primitive_data.get("adopted", False),
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
        for key, candidate_data in data.get("structural_adaptation_candidates", {}).items():
            state.structural_adaptation_candidates[key] = StructuralAdaptationCandidate(
                primitive_id=candidate_data["primitive_id"],
                reason=candidate_data["reason"],
                proposed_operation=candidate_data["proposed_operation"],
                pressure=candidate_data.get("pressure", 0.0),
                evidence=dict(candidate_data.get("evidence", {})),
                status=candidate_data.get("status", "proposed"),
                result_primitive_ids=list(candidate_data.get("result_primitive_ids", [])),
                result_structure_ids=list(candidate_data.get("result_structure_ids", [])),
            )
        for key, event_data in data.get("events", {}).items():
            event_data = dict(event_data)
            event_data.setdefault("id", key)
            event_data["state_variable_specs"] = {
                name: StateVariableSpec(**spec)
                for name, spec in event_data.get("state_variable_specs", {}).items()
            }
            state.events_by_id[key] = Event(**event_data)
        state.prediction_validation_stats = data.get("prediction_validation_stats", {})
        state.prediction_competition_stats = data.get("prediction_competition_stats", {})
        state.event_primitive_ids = data.get("event_primitive_ids", {})
        state.exclusive_state_groups = {
            key: set(values) for key, values in data.get("exclusive_state_groups", {}).items()
        }
        state.state_variable_specs = {
            key: StateVariableSpec(**spec)
            for key, spec in data.get("state_variable_specs", {}).items()
        }
        state.concept_members = data.get("concept_members", {})
        state.change_hypotheses = {
            key: ChangeHypothesis(**hypothesis)
            for key, hypothesis in data.get("change_hypotheses", {}).items()
        }
        state.applicability_hypotheses = {
            key: ApplicabilityHypothesis(**hypothesis)
            for key, hypothesis in data.get("applicability_hypotheses", {}).items()
        }
        legacy_candidates = {
            key: UnnamedConceptCandidate(**candidate)
            for key, candidate in data.get("unnamed_concept_candidates", {}).items()
        }
        candidate_evaluations = data.get("candidate_evaluations")
        derived_candidates = {
            key: UnnamedConceptCandidate(**candidate)
            for key, candidate in data.get("derived_candidates", {}).items()
        }
        state.unnamed_concept_candidates = legacy_candidates
        state.compacted_role_readouts = dict(data.get("compacted_role_readouts", {}))
        from risa.engine.evidence import index_event_evidence

        for event in state.events_by_id.values():
            index_event_evidence(state, event)
        if state.events_by_id:
            from risa.engine.prediction_indexes import rebuild_prediction_indexes

            rebuild_prediction_indexes(state)
            if isinstance(candidate_evaluations, dict):
                from risa.engine.candidate_discovery import (
                    _candidate_lineage_fingerprint,
                    discover_unnamed_candidates,
                )

                state.unnamed_concept_candidates = {}
                discover_unnamed_candidates(state)
                for candidate_id, candidate in sorted(
                    derived_candidates.items(),
                    key=lambda item: (item[1].derivation_generation, item[0]),
                ):
                    if all(
                        parent_id in state.unnamed_concept_candidates
                        and candidate.parent_evidence_digests.get(parent_id)
                        == _candidate_lineage_fingerprint(
                            state.unnamed_concept_candidates[parent_id]
                        )
                        for parent_id in candidate.parent_candidate_ids
                    ):
                        state.unnamed_concept_candidates[candidate_id] = candidate
                for candidate_id, evaluation in candidate_evaluations.items():
                    candidate = state.unnamed_concept_candidates.get(candidate_id)
                    if candidate is not None and isinstance(evaluation, dict):
                        _restore_candidate_evaluation(candidate, evaluation)
            from risa.engine.readout_compaction import apply_persisted_readout_compaction

            apply_persisted_readout_compaction(state)
        else:
            state.actor_action_effect_counts = data.get("actor_action_effect_counts", {})
            state.action_effect_counts = data.get("action_effect_counts", {})
            state.actor_action_context_effect_counts = data.get(
                "actor_action_context_effect_counts", {}
            )
            state.action_context_effect_counts = data.get(
                "action_context_effect_counts", {}
            )
            state.actor_action_target_context_effect_counts = data.get(
                "actor_action_target_context_effect_counts", {}
            )
            state.action_target_context_effect_counts = data.get(
                "action_target_context_effect_counts", {}
            )
            state.action_target_role_context_effect_counts = data.get(
                "action_target_role_context_effect_counts", {}
            )
            state.activation_index = data.get("activation_index", {})
        from risa.engine.candidate_discovery import rebuild_candidate_inference_index

        rebuild_candidate_inference_index(state)
        return state


_CANDIDATE_EVALUATION_FIELDS = (
    "lifecycle_status",
    "dormant",
    "evaluation_event_ids",
    "development_evaluation_event_ids",
    "final_evaluation_event_ids",
    "heldout_prediction_delta",
    "heldout_composition_delta",
    "prediction_delta_ci_lower",
    "composition_delta_ci_lower",
    "false_generalization_delta",
    "parent_heldout_prediction_delta",
    "parent_heldout_composition_delta",
    "parent_prediction_delta_ci_lower",
    "parent_composition_delta_ci_lower",
)


def _candidate_evidence_digest(candidate: UnnamedConceptCandidate) -> str:
    evidence = [
        candidate.structural_schema,
        candidate.typed_role_variables,
        candidate.supporting_event_ids,
        candidate.counterexample_event_ids,
    ]
    encoded = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:20]


_EVENT_PERSISTENCE_DEFAULTS: dict[str, object] = {
    "target": None,
    "preconditions": [],
    "consumed_states": [],
    "state_group_updates": {},
    "numeric_preconditions": {},
    "state_variable_deltas": {},
    "state_variable_specs": {},
    "observed_effects": [],
    "context_tags": [],
    "episode_id": "__default__",
    "source": "unknown",
    "actor_roles": [],
    "target_roles": [],
    "entity_bindings": {},
    "entity_role_bindings": {},
    "entity_relations": [],
    "entity_relations_observed": False,
    "observed_states_before": [],
    "before_state_observed": False,
    "transition_succeeded": True,
}

_PATTERN_PERSISTENCE_DEFAULTS: dict[str, object] = {
    "event_count": 0,
    "actors": [],
    "actions": [],
    "effects": [],
    "support": 0,
    "context_tags": [],
    "validation_score": 0.5,
}

_STRUCTURAL_PATTERN_PERSISTENCE_DEFAULTS: dict[str, object] = {
    "support": 0,
    "actions": [],
    "effects": [],
    "actors": [],
    "context_tags": [],
    "member_pattern_ids": [],
    "validation_score": 0.5,
}

_PRIMITIVE_PERSISTENCE_DEFAULTS: dict[str, object] = {
    "input_conditions": [],
    "input_state_conditions": [],
    "learned_state_conditions": [],
    "consumed_states": [],
    "state_group_updates": {},
    "numeric_preconditions": {},
    "state_variable_deltas": {},
    "output_state": "",
    "output_states": [],
    "temporal_constraint": "event_to_effect",
    "context_tags": [],
    "member_pattern_ids": [],
    "evidence_event_ids": [],
    "support": 0,
    "validation_score": 0.5,
    "reuse_score": 0.0,
    "compression_proxy": 0.0,
    "replay_count": 0,
    "replay_success_count": 0,
    "replay_score": 0.5,
    "deployment_replay_count": 0,
    "deployment_replay_success_count": 0,
    "deployment_replay_score": 0.5,
    "perturbation_replay_count": 0,
    "perturbation_replay_success_count": 0,
    "perturbation_replay_score": 0.5,
    "superseded_by": [],
    "adoption_score": 0.0,
    "adopted": False,
}


def _event_persistence_record(event: Event) -> dict[str, object]:
    record = event.to_dict()
    record.pop("id", None)
    return {
        key: value
        for key, value in record.items()
        if key not in _EVENT_PERSISTENCE_DEFAULTS
        or value != _EVENT_PERSISTENCE_DEFAULTS[key]
    }


def _pattern_persistence_record(key: str, pattern: Pattern) -> dict[str, object]:
    record = pattern.to_dict()
    record.pop("id", None)
    if record.get("signature") == key.removeprefix("pattern:"):
        record.pop("signature")
    return _without_default_values(record, _PATTERN_PERSISTENCE_DEFAULTS)


def _structural_pattern_persistence_record(
    key: str,
    pattern: StructuralPattern,
) -> dict[str, object]:
    record = pattern.to_dict()
    record.pop("id", None)
    if record.get("signature") == key:
        record.pop("signature")
    return _without_default_values(record, _STRUCTURAL_PATTERN_PERSISTENCE_DEFAULTS)


def _primitive_persistence_record(
    primitive: StructuralPrimitive,
) -> dict[str, object]:
    record = primitive.to_dict()
    record.pop("id", None)
    return _without_default_values(record, _PRIMITIVE_PERSISTENCE_DEFAULTS)


def _without_default_values(
    record: dict[str, object],
    defaults: dict[str, object],
) -> dict[str, object]:
    return {
        key: value
        for key, value in record.items()
        if key not in defaults or value != defaults[key]
    }


def _candidate_has_persisted_evaluation(
    candidate: UnnamedConceptCandidate,
) -> bool:
    return candidate.lifecycle_status != "proposed" or bool(
        candidate.evaluation_event_ids
        or candidate.development_evaluation_event_ids
        or candidate.final_evaluation_event_ids
    )


def _candidate_evaluation_record(
    candidate: UnnamedConceptCandidate,
) -> dict[str, object]:
    record = {
        field_name: getattr(candidate, field_name)
        for field_name in _CANDIDATE_EVALUATION_FIELDS
    }
    if not candidate.dormant:
        record.pop("dormant", None)
    record["evidence_digest"] = _candidate_evidence_digest(candidate)
    return record


def _restore_candidate_evaluation(
    candidate: UnnamedConceptCandidate,
    evaluation: dict[str, object],
) -> None:
    if evaluation.get("evidence_digest") != _candidate_evidence_digest(candidate):
        return
    for field_name in _CANDIDATE_EVALUATION_FIELDS:
        if field_name not in evaluation:
            continue
        value = evaluation[field_name]
        if field_name.endswith("event_ids"):
            value = list(value) if isinstance(value, list) else []
        setattr(candidate, field_name, value)
