from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from time import perf_counter_ns

from risa.core.models import PredictionQuery, PredictionResult
from risa.core.state import RisaState
from risa.engine.evidence import index_event_evidence, matching_evidence_event_ids
from risa.engine.graph_builder import normalize_label
from risa.engine.prediction_indexes import rebuild_prediction_indexes
from risa.engine.predictor import predict_next_effect
from risa.engine.role_induction import effective_query_target_roles


@dataclass(frozen=True)
class PredictionAccessStats:
    mode: str
    events_examined: int
    candidate_events_loaded: int
    elapsed_ns: int


def predict_next_effect_with_access(
    state: RisaState,
    query: PredictionQuery,
    mode: str = "indexed",
) -> tuple[PredictionResult, PredictionAccessStats]:
    """Run indexed prediction or an Event-scan reference with identical semantics."""
    if mode not in {"indexed", "full_scan"}:
        raise ValueError("mode must be 'indexed' or 'full_scan'")

    prediction_state = state
    events_examined = 0
    started = perf_counter_ns()
    if mode == "full_scan":
        prediction_state = _materialize_event_scan_state(state)
        events_examined = len(state.events_by_id)
    result = predict_next_effect(prediction_state, query)
    elapsed_ns = perf_counter_ns() - started

    candidate_event_ids = _candidate_event_ids(prediction_state, query)
    if mode == "indexed":
        events_examined = len(candidate_event_ids)
    return result, PredictionAccessStats(
        mode=mode,
        events_examined=events_examined,
        candidate_events_loaded=len(candidate_event_ids),
        elapsed_ns=elapsed_ns,
    )


def _materialize_event_scan_state(state: RisaState) -> RisaState:
    scan_state = copy(state)
    scan_state.actor_action_effect_counts = {}
    scan_state.action_effect_counts = {}
    scan_state.actor_action_context_effect_counts = {}
    scan_state.action_context_effect_counts = {}
    scan_state.actor_action_target_context_effect_counts = {}
    scan_state.action_target_context_effect_counts = {}
    scan_state.action_target_role_context_effect_counts = {}
    scan_state.activation_index = {}
    scan_state.evidence_index = {}
    rebuild_prediction_indexes(scan_state)
    for event in scan_state.events_by_id.values():
        index_event_evidence(scan_state, event)
    return scan_state


def _candidate_event_ids(
    state: RisaState,
    query: PredictionQuery,
) -> list[str]:
    context_key = (
        "|".join(sorted(normalize_label(tag) for tag in query.context_tags))
        or "__no_context__"
    )
    target_roles = effective_query_target_roles(
        target=query.target,
        supplied_roles=query.target_roles,
        entity_bindings=query.entity_bindings,
        entity_relations=query.entity_relations,
        enable_role_induction=query.enable_role_induction,
    )
    return matching_evidence_event_ids(
        state,
        action=query.action,
        context_key=context_key,
        target=query.target or "",
        target_roles=target_roles,
        exact_context=bool(query.context_tags),
    )
