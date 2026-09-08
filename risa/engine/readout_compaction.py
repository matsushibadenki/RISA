from __future__ import annotations

from dataclasses import dataclass, field
import json

from risa.core.models import PredictionQuery
from risa.core.state import RisaState
from risa.engine.candidate_discovery import matching_adopted_candidates
from risa.engine.graph_builder import normalize_label


@dataclass
class ReadoutCompactionResult:
    applied: bool
    removed_keys: list[str] = field(default_factory=list)
    readout_bytes_before: int = 0
    readout_bytes_after: int = 0
    checked_queries: int = 0
    mismatch_query_indexes: list[int] = field(default_factory=list)


def compact_adopted_candidate_readouts(
    state: RisaState,
    regression_queries: list[PredictionQuery],
) -> ReadoutCompactionResult:
    """Remove redundant role readouts only after output-equivalence validation."""
    if not regression_queries:
        raise ValueError("readout compaction requires regression queries")
    from risa.engine.predictor import predict_next_effect

    before = [
        tuple(predict_next_effect(state, query).predicted_effects)
        for query in regression_queries
    ]
    bytes_before = _role_readout_bytes(state)
    removed: dict[str, dict[str, int]] = {}
    directives: dict[str, str] = {}
    covered_candidates: set[str] = set()
    for query in regression_queries:
        action = normalize_label(query.action)
        roles = sorted({normalize_label(role) for role in query.target_roles})
        for candidate in matching_adopted_candidates(state, action, roles):
            role = normalize_label(
                str(candidate.structural_schema.get("target_role", ""))
            )
            key = _target_key("role", action, role, "__no_context__")
            if key in state.action_target_role_context_effect_counts:
                covered_candidates.add(candidate.id)
                removed[key] = state.action_target_role_context_effect_counts.pop(key)
                directives[key] = candidate.id
    if not removed:
        return ReadoutCompactionResult(
            applied=False,
            readout_bytes_before=bytes_before,
            readout_bytes_after=bytes_before,
            checked_queries=len(regression_queries),
        )
    if set(directives.values()) != covered_candidates:
        raise AssertionError("candidate compaction coverage is inconsistent")

    after = [
        tuple(predict_next_effect(state, query).predicted_effects)
        for query in regression_queries
    ]
    mismatches = [
        index for index, (left, right) in enumerate(zip(before, after)) if left != right
    ]
    if mismatches:
        state.action_target_role_context_effect_counts.update(removed)
        return ReadoutCompactionResult(
            applied=False,
            readout_bytes_before=bytes_before,
            readout_bytes_after=bytes_before,
            checked_queries=len(regression_queries),
            mismatch_query_indexes=mismatches,
        )
    state.compacted_role_readouts.update(directives)
    return ReadoutCompactionResult(
        applied=True,
        removed_keys=sorted(removed),
        readout_bytes_before=bytes_before,
        readout_bytes_after=_role_readout_bytes(state),
        checked_queries=len(regression_queries),
    )


def apply_persisted_readout_compaction(state: RisaState) -> None:
    """Apply valid persisted directives after read models are rebuilt from Events."""
    valid: dict[str, str] = {}
    for key, candidate_id in state.compacted_role_readouts.items():
        candidate = state.unnamed_concept_candidates.get(candidate_id)
        if candidate is None or candidate.lifecycle_status != "adopted":
            continue
        state.action_target_role_context_effect_counts.pop(key, None)
        valid[key] = candidate_id
    state.compacted_role_readouts = valid


def restore_compacted_readouts_for_learning(state: RisaState) -> None:
    """New evidence invalidates the static equivalence proof and restores all readouts."""
    if not state.compacted_role_readouts:
        return
    state.compacted_role_readouts.clear()
    from risa.engine.prediction_indexes import rebuild_prediction_indexes

    rebuild_prediction_indexes(state)


def _role_readout_bytes(state: RisaState) -> int:
    return len(
        json.dumps(
            state.action_target_role_context_effect_counts,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _target_key(actor: str, action: str, target: str, context: str) -> str:
    return "\x1f".join((actor, action, target, context))

