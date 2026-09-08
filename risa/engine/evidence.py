from __future__ import annotations

from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label


def index_event_evidence(state: RisaState, event: Event) -> None:
    action = normalize_label(event.action)
    actor = normalize_label(event.actor)
    target = normalize_label(event.target or "")
    context = _context_key(event.context_tags)
    _append(state, f"action:{action}:context:{context}", event.id)
    _append(state, f"actor:{actor}:action:{action}:context:{context}", event.id)
    if target:
        _append(state, f"target:{target}:action:{action}:context:{context}", event.id)
    for role in sorted({normalize_label(item) for item in event.target_roles}):
        _append(state, f"target_role:{role}:action:{action}:context:{context}", event.id)
    for effect in sorted({normalize_label(item) for item in event.observed_effects}):
        _append(state, f"action:{action}:effect:{effect}:context:{context}", event.id)


def matching_evidence_event_ids(
    state: RisaState,
    action: str,
    context_key: str,
    effect: str | None = None,
    actor: str = "",
    target: str = "",
    target_roles: list[str] | None = None,
    exact_context: bool = False,
) -> list[str]:
    action = normalize_label(action)
    actor = normalize_label(actor) if actor else ""
    target = normalize_label(target) if target else ""
    base_prefix = (
        f"action:{action}:effect:{normalize_label(effect)}:context:"
        if effect
        else f"action:{action}:context:"
    )
    candidates = _lookup(state, base_prefix, context_key, exact_context)
    if actor:
        actor_ids = _lookup(
            state,
            f"actor:{actor}:action:{action}:context:",
            context_key,
            exact_context,
        )
        candidates &= actor_ids
    if target:
        grounded_ids = _lookup(
            state,
            f"target:{target}:action:{action}:context:",
            context_key,
            exact_context,
        )
        for role in target_roles or []:
            grounded_ids.update(
                _lookup(
                    state,
                    f"target_role:{normalize_label(role)}:action:{action}:context:",
                    context_key,
                    exact_context,
                )
            )
        candidates &= grounded_ids
    return sorted(candidates)


def _lookup(
    state: RisaState,
    prefix: str,
    context_key: str,
    exact_context: bool,
) -> set[str]:
    if exact_context or context_key != "__no_context__":
        return set(state.evidence_index.get(f"{prefix}{context_key}", []))
    return {
        event_id
        for key, event_ids in state.evidence_index.items()
        if key.startswith(prefix)
        for event_id in event_ids
    }


def _append(state: RisaState, key: str, event_id: str) -> None:
    values = state.evidence_index.setdefault(key, [])
    if event_id not in values:
        values.append(event_id)


def _context_key(context_tags: list[str]) -> str:
    return "|".join(sorted(normalize_label(tag) for tag in context_tags)) or "__no_context__"
