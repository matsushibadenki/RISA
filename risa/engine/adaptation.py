from __future__ import annotations

from collections import defaultdict

from risa.core.models import Edge, Event, StructuralAdaptationCandidate, StructuralPrimitive
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
from risa.engine.learner import refresh_primitive_adoption


def execute_safe_adaptations(state: RisaState) -> list[StructuralAdaptationCandidate]:
    """Execute only adaptations that can be derived from existing evidence."""
    processed: list[StructuralAdaptationCandidate] = []
    for candidate in state.structural_adaptation_candidates.values():
        if candidate.status != "proposed":
            continue
        if candidate.proposed_operation == "SPLIT_CONTEXT":
            _execute_context_split(state, candidate)
        elif candidate.proposed_operation == "REPAIR_TRANSITION":
            _execute_transition_repair(state, candidate)
        else:
            continue
        processed.append(candidate)
    return processed


def _execute_context_split(
    state: RisaState,
    candidate: StructuralAdaptationCandidate,
) -> None:
    primitive = state.structural_primitives.get(candidate.primitive_id)
    if primitive is None or primitive.superseded_by:
        candidate.status = "blocked"
        return

    evidence_by_context: dict[str, set[str]] = defaultdict(set)
    for event_id in primitive.evidence_event_ids:
        event = state.events_by_id.get(event_id)
        if event is None:
            continue
        context_key = "|".join(sorted(normalize_label(tag) for tag in event.context_tags))
        evidence_by_context[context_key or "__no_context__"].add(event_id)

    if len(evidence_by_context) < 2:
        candidate.status = "blocked"
        return

    result_ids: list[str] = []
    for context_key, evidence_ids in sorted(evidence_by_context.items()):
        variant_id = f"{primitive.id}::context:{context_key}"
        variant = StructuralPrimitive(
            id=variant_id,
            relation_type=primitive.relation_type,
            role_signature=primitive.role_signature,
            input_conditions=set(primitive.input_conditions),
            input_state_conditions=set(primitive.input_state_conditions),
            consumed_states=set(primitive.consumed_states),
            state_group_updates=dict(primitive.state_group_updates),
            numeric_preconditions=dict(primitive.numeric_preconditions),
            state_variable_deltas=dict(primitive.state_variable_deltas),
            output_state=primitive.output_state,
            temporal_constraint=primitive.temporal_constraint,
            context_tags=set() if context_key == "__no_context__" else set(context_key.split("|")),
            member_pattern_ids=set(primitive.member_pattern_ids),
            evidence_event_ids=set(evidence_ids),
            support=len(evidence_ids),
            validation_score=primitive.validation_score,
        )
        refresh_primitive_adoption(variant)
        state.structural_primitives[variant_id] = variant
        result_ids.append(variant_id)

        for event_id in evidence_ids:
            mapped_ids = state.event_primitive_ids.get(event_id, [])
            state.event_primitive_ids[event_id] = [
                variant_id if item == primitive.id else item for item in mapped_ids
            ]

    primitive.superseded_by.update(result_ids)
    refresh_primitive_adoption(primitive)
    candidate.status = "executed"
    candidate.result_primitive_ids = result_ids


def _execute_transition_repair(
    state: RisaState,
    candidate: StructuralAdaptationCandidate,
) -> None:
    primitive = state.structural_primitives.get(candidate.primitive_id)
    if primitive is None or not primitive.input_state_conditions:
        candidate.status = "blocked"
        return

    result_ids: set[str] = set()
    ordered_events = sorted(state.events_by_id.values(), key=lambda item: (item.timestamp, item.id))
    for event_id in sorted(primitive.evidence_event_ids):
        event = state.events_by_id.get(event_id)
        if event is None:
            continue
        predecessor = _previous_event_for_actor(ordered_events, event)
        if predecessor is None:
            continue
        predecessor_effects = {
            f"state:{normalize_label(effect)}" for effect in predecessor.observed_effects
        }
        if not primitive.input_state_conditions.intersection(predecessor_effects):
            continue

        source = f"process:{normalize_label(predecessor.action)}"
        target = f"process:{normalize_label(event.action)}"
        state.graph.add_or_update_edge(
            Edge(
                source=source,
                target=target,
                relation_type="precedes",
                context_tags=tuple(sorted(normalize_label(tag) for tag in event.context_tags)),
                evidence_count=1,
                reliability=0.5,
                last_updated=event.timestamp,
            )
        )
        result_ids.add(f"edge:{source}->precedes->{target}")

    if not result_ids:
        candidate.status = "blocked"
        return
    candidate.status = "executed"
    candidate.result_structure_ids = sorted(result_ids)


def _previous_event_for_actor(events: list[Event], event: Event) -> Event | None:
    actor = normalize_label(event.actor)
    previous = [
        candidate
        for candidate in events
        if normalize_label(candidate.actor) == actor
        and (candidate.timestamp, candidate.id) < (event.timestamp, event.id)
    ]
    return previous[-1] if previous else None
