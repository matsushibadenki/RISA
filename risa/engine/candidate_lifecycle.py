from __future__ import annotations

import hashlib
import json

from risa.core.models import Event, UnnamedConceptCandidate
from risa.core.state import RisaState
from risa.engine.candidate_discovery import rebuild_candidate_inference_index


def specialize_candidate(
    state: RisaState,
    parent_candidate_id: str,
    *,
    supporting_event_ids: list[str],
    schema_updates: dict[str, object],
    typed_role_updates: dict[str, str] | None = None,
) -> UnnamedConceptCandidate:
    """Create a narrower, unevaluated child backed by a subset of parent evidence."""
    parent = _required_candidate(state, parent_candidate_id)
    support = sorted(set(supporting_event_ids))
    if not support or not set(support).issubset(parent.supporting_event_ids):
        raise ValueError("specialization support must be a non-empty subset of parent support")
    schema = _deep_merge(parent.structural_schema, schema_updates)
    roles = {**parent.typed_role_variables, **(typed_role_updates or {})}
    candidate = _register_derived_candidate(
        state,
        derivation_type="specialized",
        parents=[parent],
        structural_schema=schema,
        typed_role_variables=roles,
        supporting_event_ids=support,
    )
    candidate.counterexample_event_ids = _matching_context_counterexamples(
        state, parent, schema
    )
    _refresh_evidence_statistics(state, candidate)
    return candidate


def merge_candidates(
    state: RisaState,
    candidate_ids: list[str],
) -> UnnamedConceptCandidate:
    """Merge compatible sibling schemas without treating parent evaluations as new evidence."""
    parents = [_required_candidate(state, candidate_id) for candidate_id in candidate_ids]
    if len({parent.id for parent in parents}) < 2:
        raise ValueError("merge requires at least two distinct candidates")
    kinds = {parent.structural_schema.get("kind", "single_transition") for parent in parents}
    roles = {tuple(sorted(parent.typed_role_variables.items())) for parent in parents}
    if len(kinds) != 1 or len(roles) != 1:
        raise ValueError("merge candidates must have compatible schema kinds and typed roles")
    for key in ("action", "target_role", "effects", "goal_effects"):
        values = {
            repr(parent.structural_schema[key])
            for parent in parents
            if key in parent.structural_schema
        }
        if len(values) > 1:
            raise ValueError(f"merge candidates have incompatible '{key}' schemas")
    schema = _merged_schema([parent.structural_schema for parent in parents])
    support = sorted({event_id for parent in parents for event_id in parent.supporting_event_ids})
    candidate = _register_derived_candidate(
        state,
        derivation_type="merged",
        parents=parents,
        structural_schema=schema,
        typed_role_variables=dict(parents[0].typed_role_variables),
        supporting_event_ids=support,
    )
    candidate.counterexample_event_ids = sorted(
        {event_id for parent in parents for event_id in parent.counterexample_event_ids}
    )
    _refresh_evidence_statistics(state, candidate)
    return candidate


def propose_context_derivations(
    state: RisaState,
    *,
    minimum_precision_gain: float = 0.2,
    max_specializations_per_parent: int = 8,
) -> list[UnnamedConceptCandidate]:
    """Propose reproducible context specializations and a lossless sibling merge."""
    if max_specializations_per_parent < 1:
        raise ValueError("max_specializations_per_parent must be positive")
    proposed: list[UnnamedConceptCandidate] = []
    base_candidates = [
        candidate
        for candidate in state.unnamed_concept_candidates.values()
        if candidate.derivation_generation == 0
        and candidate.structural_schema.get("kind", "single_transition")
        == "single_transition"
        and candidate.counterexample_event_ids
    ]
    for parent in sorted(base_candidates, key=lambda item: item.id):
        support_events = [
            state.events_by_id[event_id]
            for event_id in parent.supporting_event_ids
            if event_id in state.events_by_id
        ]
        counter_events = [
            state.events_by_id[event_id]
            for event_id in parent.counterexample_event_ids
            if event_id in state.events_by_id
        ]
        parent_precision = len(support_events) / (len(support_events) + len(counter_events))
        tags = sorted(
            {
                normalize_tag(tag)
                for event in support_events
                for tag in event.context_tags
                if normalize_tag(tag)
            }
        )
        qualified: list[tuple[float, int, str, list[Event]]] = []
        for tag in tags:
            matching_support = [
                event
                for event in support_events
                if tag in {normalize_tag(item) for item in event.context_tags}
            ]
            matching_counters = [
                event
                for event in counter_events
                if tag in {normalize_tag(item) for item in event.context_tags}
            ]
            if not _has_independent_diversity(matching_support):
                continue
            precision = len(matching_support) / (
                len(matching_support) + len(matching_counters)
            )
            if precision - parent_precision < minimum_precision_gain:
                continue
            qualified.append(
                (precision - parent_precision, len(matching_support), tag, matching_support)
            )
        siblings: list[UnnamedConceptCandidate] = []
        for _, _, tag, matching_support in sorted(
            qualified, key=lambda item: (-item[0], -item[1], item[2])
        )[:max_specializations_per_parent]:
            child = specialize_candidate(
                state,
                parent.id,
                supporting_event_ids=[event.id for event in matching_support],
                schema_updates={"required_context_tags": [tag]},
            )
            siblings.append(child)
            proposed.append(child)
        if len(siblings) > 1:
            proposed.append(merge_candidates(state, [item.id for item in siblings]))
    return proposed


def set_candidate_dormant(
    state: RisaState,
    candidate_id: str,
    dormant: bool = True,
) -> UnnamedConceptCandidate:
    candidate = _required_candidate(state, candidate_id)
    if dormant and candidate.lifecycle_status != "adopted":
        raise ValueError("only adopted candidates can become dormant")
    candidate.dormant = dormant
    rebuild_candidate_inference_index(state)
    return candidate


def validate_candidate_ancestry(state: RisaState, candidate_id: str) -> None:
    _visit_ancestry(state, candidate_id, set(), set())


def _register_derived_candidate(
    state: RisaState,
    *,
    derivation_type: str,
    parents: list[UnnamedConceptCandidate],
    structural_schema: dict[str, object],
    typed_role_variables: dict[str, str],
    supporting_event_ids: list[str],
) -> UnnamedConceptCandidate:
    generation = max(parent.derivation_generation for parent in parents) + 1
    signature = json.dumps(
        {
            "type": derivation_type,
            "parents": sorted(parent.id for parent in parents),
            "schema": structural_schema,
            "roles": typed_role_variables,
            "support": supporting_event_ids,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    candidate_id = "candidate:derived:" + hashlib.sha256(signature.encode()).hexdigest()[:16]
    if candidate_id in {parent.id for parent in parents}:
        raise ValueError("candidate cannot derive from itself")
    candidate = UnnamedConceptCandidate(
        id=candidate_id,
        structural_schema=structural_schema,
        typed_role_variables=typed_role_variables,
        supporting_event_ids=supporting_event_ids,
        source_diversity=max(parent.source_diversity for parent in parents),
        episode_diversity=max(parent.episode_diversity for parent in parents),
        actor_diversity=max(parent.actor_diversity for parent in parents),
        target_diversity=max(parent.target_diversity for parent in parents),
        context_diversity=max(parent.context_diversity for parent in parents),
        description_length_delta=sum(parent.description_length_delta for parent in parents),
        reconstruction_gain=min(parent.reconstruction_gain for parent in parents),
        parent_candidate_ids=sorted(parent.id for parent in parents),
        parent_evidence_digests={
            parent.id: _lineage_fingerprint(parent) for parent in parents
        },
        derivation_generation=generation,
        derivation_type=derivation_type,
    )
    state.unnamed_concept_candidates[candidate_id] = candidate
    try:
        validate_candidate_ancestry(state, candidate_id)
    except ValueError:
        state.unnamed_concept_candidates.pop(candidate_id, None)
        raise
    return candidate


def _required_candidate(state: RisaState, candidate_id: str) -> UnnamedConceptCandidate:
    candidate = state.unnamed_concept_candidates.get(candidate_id)
    if candidate is None:
        raise KeyError(candidate_id)
    validate_candidate_ancestry(state, candidate_id)
    return candidate


def _visit_ancestry(
    state: RisaState,
    candidate_id: str,
    visiting: set[str],
    visited: set[str],
) -> None:
    if candidate_id in visiting:
        raise ValueError(f"candidate ancestry contains a cycle at '{candidate_id}'")
    if candidate_id in visited:
        return
    candidate = state.unnamed_concept_candidates.get(candidate_id)
    if candidate is None:
        raise ValueError(f"candidate ancestry references missing parent '{candidate_id}'")
    visiting.add(candidate_id)
    for parent_id in candidate.parent_candidate_ids:
        _visit_ancestry(state, parent_id, visiting, visited)
    visiting.remove(candidate_id)
    visited.add(candidate_id)


def _deep_merge(base: dict[str, object], updates: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged


def _common_schema(schemas: list[dict[str, object]]) -> dict[str, object]:
    first = schemas[0]
    return {
        key: value
        for key, value in first.items()
        if all(schema.get(key) == value for schema in schemas[1:])
    }


def _merged_schema(schemas: list[dict[str, object]]) -> dict[str, object]:
    stripped = [
        {
            key: value
            for key, value in schema.items()
            if key not in {"required_context_tags", "required_context_alternatives"}
        }
        for schema in schemas
    ]
    schema = _common_schema(stripped)
    alternatives: set[tuple[str, ...]] = set()
    compatible = all(item == stripped[0] for item in stripped[1:])
    for source in schemas:
        required = source.get("required_context_tags")
        if isinstance(required, list) and required:
            alternatives.add(tuple(sorted(normalize_tag(str(tag)) for tag in required)))
        raw_alternatives = source.get("required_context_alternatives")
        if isinstance(raw_alternatives, list):
            for item in raw_alternatives:
                if isinstance(item, list) and item:
                    alternatives.add(
                        tuple(sorted(normalize_tag(str(tag)) for tag in item))
                    )
    if compatible and len(alternatives) >= 2:
        schema["required_context_alternatives"] = [list(item) for item in sorted(alternatives)]
    return schema


def _matching_context_counterexamples(
    state: RisaState,
    parent: UnnamedConceptCandidate,
    schema: dict[str, object],
) -> list[str]:
    return sorted(
        event_id
        for event_id in parent.counterexample_event_ids
        if event_id in state.events_by_id
        and _schema_context_matches(schema, state.events_by_id[event_id].context_tags)
    )


def _schema_context_matches(schema: dict[str, object], context_tags: list[str]) -> bool:
    available = {normalize_tag(tag) for tag in context_tags}
    required = schema.get("required_context_tags", [])
    if isinstance(required, list) and not {
        normalize_tag(str(tag)) for tag in required
    }.issubset(available):
        return False
    alternatives = schema.get("required_context_alternatives", [])
    if isinstance(alternatives, list) and alternatives:
        return any(
            isinstance(item, list)
            and {normalize_tag(str(tag)) for tag in item}.issubset(available)
            for item in alternatives
        )
    return True


def _has_independent_diversity(events: list[Event]) -> bool:
    return (
        len({normalize_tag(getattr(event, "target", "") or "") for event in events}) >= 2
        and len({getattr(event, "source", "") for event in events}) >= 2
        and len({getattr(event, "episode_id", "") for event in events}) >= 2
    )


def _refresh_evidence_statistics(
    state: RisaState, candidate: UnnamedConceptCandidate
) -> None:
    events = [
        state.events_by_id[event_id]
        for event_id in candidate.supporting_event_ids
        if event_id in state.events_by_id
    ]
    candidate.source_diversity = len({event.source for event in events})
    candidate.episode_diversity = len({event.episode_id for event in events})
    candidate.actor_diversity = len({normalize_tag(event.actor) for event in events})
    candidate.target_diversity = len(
        {normalize_tag(event.target or "") for event in events}
    )
    candidate.context_diversity = len(
        {tuple(sorted(normalize_tag(tag) for tag in event.context_tags)) for event in events}
    )
    candidate.exception_cost = len(candidate.counterexample_event_ids)
    denominator = len(events) + candidate.exception_cost
    candidate.reconstruction_gain = round(len(events) / denominator, 6) if denominator else 0.0


def normalize_tag(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _lineage_fingerprint(candidate: UnnamedConceptCandidate) -> str:
    payload = repr(
        (
            candidate.structural_schema,
            candidate.typed_role_variables,
            candidate.supporting_event_ids,
            candidate.counterexample_event_ids,
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:20]
