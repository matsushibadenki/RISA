from __future__ import annotations

from collections import defaultdict
import hashlib

from risa.core.models import Event, UnnamedConceptCandidate
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label


def discover_unnamed_candidates(state: RisaState) -> dict[str, UnnamedConceptCandidate]:
    """Propose cross-target schemas from primary Event evidence only."""
    previous_candidates = state.unnamed_concept_candidates
    groups: dict[tuple[str, str, tuple[str, ...]], list[Event]] = defaultdict(list)
    all_by_action_role: dict[tuple[str, str], list[Event]] = defaultdict(list)
    for event in state.events_by_id.values():
        if (
            not event.transition_succeeded
            or not event.target
            or not event.observed_effects
            or event.source.startswith(("derived:", "replay:"))
        ):
            continue
        action = normalize_label(event.action)
        outcome = tuple(sorted({normalize_label(item) for item in event.observed_effects}))
        for role in sorted({normalize_label(item) for item in event.target_roles}):
            groups[(action, role, outcome)].append(event)
            all_by_action_role[(action, role)].append(event)

    candidates: dict[str, UnnamedConceptCandidate] = {}
    for (action, role, outcome), events in sorted(groups.items()):
        targets = {normalize_label(event.target or "") for event in events}
        sources = {event.source for event in events}
        episodes = {event.episode_id for event in events}
        if len(targets) < 2 or len(sources) < 2 or len(episodes) < 2:
            continue
        signature = f"{action}|target_role:{role}|{'+'.join(outcome)}"
        candidate_id = f"candidate:{hashlib.sha256(signature.encode()).hexdigest()[:16]}"
        counterexamples = [
            event
            for event in all_by_action_role[(action, role)]
            if tuple(sorted({normalize_label(item) for item in event.observed_effects})) != outcome
        ]
        concrete_length = sum(
            len(action)
            + len(normalize_label(event.target or ""))
            + len(role)
            + sum(len(effect) for effect in outcome)
            for event in events
        )
        schema_length = (
            len(action)
            + len(role)
            + sum(len(effect) for effect in outcome)
            + sum(len(target) for target in targets)
        )
        candidate = UnnamedConceptCandidate(
            id=candidate_id,
            structural_schema={
                "action": action,
                "target_role": role,
                "effects": list(outcome),
            },
            typed_role_variables={"target": role},
            supporting_event_ids=sorted(event.id for event in events),
            counterexample_event_ids=sorted(event.id for event in counterexamples),
            source_diversity=len(sources),
            episode_diversity=len(episodes),
            actor_diversity=len({normalize_label(event.actor) for event in events}),
            target_diversity=len(targets),
            context_diversity=len(
                {tuple(sorted(normalize_label(tag) for tag in event.context_tags)) for event in events}
            ),
            description_length_delta=concrete_length - schema_length,
            reconstruction_gain=round(len(events) / (len(events) + len(counterexamples)), 6),
            exception_cost=len(counterexamples),
        )
        previous = previous_candidates.get(candidate_id)
        if (
            previous is not None
            and previous.supporting_event_ids == candidate.supporting_event_ids
            and previous.counterexample_event_ids == candidate.counterexample_event_ids
        ):
            candidate.lifecycle_status = previous.lifecycle_status
            candidate.evaluation_event_ids = list(previous.evaluation_event_ids)
            candidate.development_evaluation_event_ids = list(
                previous.development_evaluation_event_ids
            )
            candidate.final_evaluation_event_ids = list(
                previous.final_evaluation_event_ids
            )
            candidate.heldout_prediction_delta = previous.heldout_prediction_delta
            candidate.heldout_composition_delta = previous.heldout_composition_delta
            candidate.prediction_delta_ci_lower = previous.prediction_delta_ci_lower
            candidate.composition_delta_ci_lower = previous.composition_delta_ci_lower
            candidate.false_generalization_delta = previous.false_generalization_delta
        candidates[candidate_id] = candidate
    state.unnamed_concept_candidates = candidates
    rebuild_candidate_inference_index(state)
    return candidates


def rebuild_candidate_inference_index(state: RisaState) -> None:
    """Rebuild the derived index; source Events and persisted graph stay unchanged."""
    state.candidate_inference_index.clear()
    for candidate in state.unnamed_concept_candidates.values():
        if candidate.lifecycle_status != "adopted":
            continue
        action = normalize_label(str(candidate.structural_schema.get("action", "")))
        role = normalize_label(str(candidate.structural_schema.get("target_role", "")))
        if not action or not role:
            continue
        key = f"action:{action}:target_role:{role}"
        values = state.candidate_inference_index.setdefault(key, [])
        if candidate.id not in values:
            values.append(candidate.id)


def matching_adopted_candidates(
    state: RisaState,
    action: str,
    target_roles: list[str] | set[str] | tuple[str, ...],
) -> list[UnnamedConceptCandidate]:
    candidate_ids: set[str] = set()
    normalized_action = normalize_label(action)
    for role in target_roles:
        key = f"action:{normalized_action}:target_role:{normalize_label(role)}"
        candidate_ids.update(state.candidate_inference_index.get(key, []))
    return [
        state.unnamed_concept_candidates[candidate_id]
        for candidate_id in sorted(candidate_ids)
        if candidate_id in state.unnamed_concept_candidates
        and state.unnamed_concept_candidates[candidate_id].lifecycle_status == "adopted"
    ]


def evaluate_unnamed_candidate(
    state: RisaState,
    candidate_id: str,
    *,
    partition: str,
    evaluation_event_ids: list[str],
    prediction_delta: float,
    composition_delta: float,
    prediction_delta_ci_lower: float,
    composition_delta_ci_lower: float,
    false_generalization_delta: float,
    minimum_gain: float = 0.05,
) -> UnnamedConceptCandidate:
    candidate = state.unnamed_concept_candidates[candidate_id]
    overlap = set(candidate.supporting_event_ids).intersection(evaluation_event_ids)
    if overlap:
        raise ValueError(
            f"candidate evaluation overlaps supporting evidence: {sorted(overlap)}"
        )
    if partition not in {"development", "final"}:
        raise ValueError("partition must be 'development' or 'final'")
    if partition == "final" and candidate.lifecycle_status != "provisional":
        raise ValueError("final evaluation requires a provisional candidate")
    partition_ids = set(evaluation_event_ids)
    if partition == "development":
        cross_partition_overlap = partition_ids.intersection(
            candidate.final_evaluation_event_ids
        )
    else:
        cross_partition_overlap = partition_ids.intersection(
            candidate.development_evaluation_event_ids
        )
    if cross_partition_overlap:
        raise ValueError(
            "candidate evaluation overlaps development/final evidence: "
            f"{sorted(cross_partition_overlap)}"
        )
    candidate.evaluation_event_ids = sorted(
        set(candidate.evaluation_event_ids).union(evaluation_event_ids)
    )
    if partition == "development":
        candidate.development_evaluation_event_ids = sorted(
            set(candidate.development_evaluation_event_ids).union(evaluation_event_ids)
        )
    else:
        candidate.final_evaluation_event_ids = sorted(
            set(candidate.final_evaluation_event_ids).union(evaluation_event_ids)
        )
    candidate.heldout_prediction_delta = prediction_delta
    candidate.heldout_composition_delta = composition_delta
    candidate.prediction_delta_ci_lower = prediction_delta_ci_lower
    candidate.composition_delta_ci_lower = composition_delta_ci_lower
    candidate.false_generalization_delta = false_generalization_delta

    has_supported_gain = (
        prediction_delta >= minimum_gain and prediction_delta_ci_lower > 0.0
    ) or (
        composition_delta >= minimum_gain and composition_delta_ci_lower > 0.0
    )
    passes = (
        candidate.description_length_delta > 0
        and has_supported_gain
        and false_generalization_delta <= 0.0
    )
    if partition == "development":
        candidate.lifecycle_status = "provisional" if passes else "rejected"
    else:
        candidate.lifecycle_status = "adopted" if passes else "rejected"
    rebuild_candidate_inference_index(state)
    return candidate
