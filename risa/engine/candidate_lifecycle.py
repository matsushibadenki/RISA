from __future__ import annotations

import hashlib
import json

from risa.core.models import UnnamedConceptCandidate
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
    return _register_derived_candidate(
        state,
        derivation_type="specialized",
        parents=[parent],
        structural_schema=schema,
        typed_role_variables=roles,
        supporting_event_ids=support,
    )


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
    schema = _common_schema([parent.structural_schema for parent in parents])
    support = sorted({event_id for parent in parents for event_id in parent.supporting_event_ids})
    return _register_derived_candidate(
        state,
        derivation_type="merged",
        parents=parents,
        structural_schema=schema,
        typed_role_variables=dict(parents[0].typed_role_variables),
        supporting_event_ids=support,
    )


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
