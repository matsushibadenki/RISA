from __future__ import annotations

from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label


def rebuild_prediction_indexes(state: RisaState) -> None:
    """Rebuild deterministic prediction read models from immutable Events."""
    state.actor_action_effect_counts.clear()
    state.action_effect_counts.clear()
    state.actor_action_context_effect_counts.clear()
    state.action_context_effect_counts.clear()
    state.actor_action_target_context_effect_counts.clear()
    state.action_target_context_effect_counts.clear()
    state.action_target_role_context_effect_counts.clear()
    state.activation_index.clear()

    for event in sorted(
        state.events_by_id.values(), key=lambda item: (item.timestamp, item.id)
    ):
        actor = normalize_label(event.actor)
        action = normalize_label(event.action)
        target = normalize_label(event.target or "")
        context = (
            "|".join(sorted(normalize_label(tag) for tag in event.context_tags))
            or "__no_context__"
        )
        effects = sorted({normalize_label(effect) for effect in event.observed_effects})
        for effect in effects:
            _increment_nested(state.actor_action_effect_counts, (actor, action), effect)
            _increment_nested(state.action_effect_counts, (action,), effect)
            _increment_nested(
                state.actor_action_context_effect_counts,
                (actor, action, context),
                effect,
            )
            _increment_nested(
                state.action_context_effect_counts,
                (action, context),
                effect,
            )
            if target:
                _increment_nested(
                    state.actor_action_target_context_effect_counts,
                    (_target_key(actor, action, target, context),),
                    effect,
                )
                _increment_nested(
                    state.action_target_context_effect_counts,
                    (_target_key("*", action, target, context),),
                    effect,
                )
            for role in sorted({normalize_label(item) for item in event.target_roles}):
                _increment_nested(
                    state.action_target_role_context_effect_counts,
                    (_target_key("role", action, role, context),),
                    effect,
                )
            for key in (
                f"actor_action:{actor}:{action}",
                f"actor:{actor}",
                f"action:{action}",
                f"context:{context}",
            ):
                values = state.activation_index.setdefault(key, [])
                if effect not in values:
                    values.append(effect)


def _increment_nested(
    index: dict,
    path: tuple[str, ...],
    effect: str,
) -> None:
    bucket = index
    for key in path:
        bucket = bucket.setdefault(key, {})
    bucket[effect] = bucket.get(effect, 0) + 1


def _target_key(actor: str, action: str, target: str, context: str) -> str:
    return "\x1f".join((actor, action, target, context))

