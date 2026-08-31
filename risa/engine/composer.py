from __future__ import annotations

from collections import deque

from risa.core.models import CompositionResult, StructuralPrimitive
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
from risa.engine.state_variables import apply_variable_deltas, requirements_satisfied


def forecast_next_effects(
    state: RisaState,
    action: str,
    current_states: list[str] | None = None,
    current_variables: dict[str, float] | None = None,
    context_tags: list[str] | None = None,
    max_candidates: int = 3,
    include_supported_alternatives: bool = False,
) -> list[CompositionResult]:
    """Return locally applicable next-state candidates without collapsing uncertainty."""
    normalized_action = normalize_label(action)
    context = {normalize_label(tag) for tag in context_tags or []}
    available_states = {f"state:{normalize_label(state_name)}" for state_name in current_states or []}
    available_variables = {
        normalize_label(name): float(value) for name, value in (current_variables or {}).items()
    }
    candidates: list[CompositionResult] = []

    for primitive in _adopted_primitives_for_action(
        state,
        normalized_action,
        context,
        available_states,
        available_variables,
        include_supported_alternatives=include_supported_alternatives,
    ):
        score = _primitive_score(primitive, context)
        resulting_variables = apply_variable_deltas(
            state.state_variable_specs,
            available_variables,
            primitive.state_variable_deltas,
        )
        if resulting_variables is None:
            continue
        candidates.append(
            CompositionResult(
                target_effect=primitive.output_state,
                removed_states=sorted(
                    state_id.removeprefix("state:")
                    for state_id in _removed_states_for_primitive(state, primitive)
                ),
                variable_deltas=dict(sorted(primitive.state_variable_deltas.items())),
                resulting_variables=dict(sorted(resulting_variables.items())),
                primitive_ids=[primitive.id],
                supporting_paths=[
                    [
                        *sorted(primitive.input_state_conditions),
                        f"process:{normalized_action}",
                        primitive.id,
                        f"state:{primitive.output_state}",
                    ]
                ],
                score=round(score, 4),
                explanation=(
                    f"Forecast candidate '{primitive.output_state}' from an adopted primitive "
                    f"applicable to action '{normalized_action}'."
                ),
            )
        )

    candidates.sort(key=lambda candidate: (-candidate.score, candidate.target_effect, candidate.primitive_ids))
    return candidates[:max_candidates]


def compose_to_effect(
    state: RisaState,
    start_action: str,
    target_effect: str,
    context_tags: list[str] | None = None,
    start_states: list[str] | None = None,
    start_variables: dict[str, float] | None = None,
    max_steps: int = 3,
) -> CompositionResult:
    """Find a local sequence of adopted transition primitives toward an effect."""
    action = normalize_label(start_action)
    effect = normalize_label(target_effect)
    context = {normalize_label(tag) for tag in context_tags or []}
    initial_states = {f"state:{normalize_label(state_name)}" for state_name in start_states or []}
    initial_variables = {
        normalize_label(name): float(value) for name, value in (start_variables or {}).items()
    }
    queue = deque([(action, initial_states, initial_variables, [], [], 1.0, 0)])
    best_depth_by_action: dict[str, int] = {action: 0}

    while queue:
        current_action, available_states, available_variables, primitive_ids, paths, score, depth = queue.popleft()
        for primitive in _adopted_primitives_for_action(
            state, current_action, context, available_states, available_variables
        ):
            primitive_score = _primitive_score(primitive, context)
            next_ids = [*primitive_ids, primitive.id]
            next_paths = [*paths, [f"process:{current_action}", primitive.id, f"state:{primitive.output_state}"]]
            next_score = score * primitive_score
            removed_states = _removed_states_for_primitive(state, primitive)
            next_states = (available_states - removed_states) | {
                f"state:{primitive.output_state}"
            }
            next_variables = apply_variable_deltas(
                state.state_variable_specs,
                available_variables,
                primitive.state_variable_deltas,
            )
            if next_variables is None:
                continue

            if primitive.output_state == effect:
                return CompositionResult(
                    target_effect=effect,
                    removed_states=sorted(
                        state_id.removeprefix("state:") for state_id in removed_states
                    ),
                    variable_deltas=dict(sorted(primitive.state_variable_deltas.items())),
                    resulting_variables=dict(sorted(next_variables.items())),
                    primitive_ids=next_ids,
                    supporting_paths=next_paths,
                    score=round(next_score, 4),
                    explanation=(
                        f"Composed {len(next_ids)} adopted structural primitives from action "
                        f"'{action}' toward effect '{effect}'."
                    ),
                )
            if depth >= max_steps - 1:
                continue

            for next_action, precedence_score in next_actions(state, current_action, context):
                next_depth = depth + 1
                if next_depth >= best_depth_by_action.get(next_action, max_steps):
                    continue
                best_depth_by_action[next_action] = next_depth
                queue.append(
                    (
                        next_action,
                        next_states,
                        next_variables,
                        next_ids,
                        [*next_paths, [f"process:{current_action}", "precedes", f"process:{next_action}"]],
                        next_score * precedence_score,
                        next_depth,
                    )
                )

    return CompositionResult(
        target_effect=effect,
        explanation=f"No adopted local primitive composition found from action '{action}' to effect '{effect}'.",
    )


def _adopted_primitives_for_action(
    state: RisaState,
    action: str,
    context: set[str],
    available_states: set[str],
    available_variables: dict[str, float],
    include_supported_alternatives: bool = False,
) -> list[StructuralPrimitive]:
    input_condition = f"process:{action}"
    return [
        primitive
        for primitive in state.structural_primitives.values()
        if (primitive.adopted or (include_supported_alternatives and _is_supported_alternative(primitive)))
        and input_condition in primitive.input_conditions
        and primitive.input_state_conditions.issubset(available_states)
        and requirements_satisfied(primitive, available_variables)
        and apply_variable_deltas(
            state.state_variable_specs,
            available_variables,
            primitive.state_variable_deltas,
        )
        is not None
        and _context_compatible(primitive.context_tags, context)
    ]


def _is_supported_alternative(primitive: StructuralPrimitive) -> bool:
    """Keep repeated, replayable minority outcomes available to branch search."""
    return primitive.support >= 2 and primitive.replay_count >= 2 and primitive.replay_score >= 0.8


def next_actions(state: RisaState, action: str, context: set[str]) -> list[tuple[str, float]]:
    edges = []
    for edge in state.graph.outgoing(f"process:{action}"):
        if edge.relation_type != "precedes" or not edge.target.startswith("process:"):
            continue
        if context and edge.context_tags and not context.intersection(edge.context_tags):
            continue
        evidence_score = min(1.0, edge.evidence_count / 3.0)
        edges.append((edge.target.removeprefix("process:"), max(0.2, evidence_score)))
    return edges


def _primitive_score(primitive: StructuralPrimitive, context: set[str]) -> float:
    context_score = 1.0 if not context else _context_overlap(primitive.context_tags, context)
    return max(0.1, primitive.adoption_score * context_score)


def _removed_states_for_primitive(
    state: RisaState,
    primitive: StructuralPrimitive,
) -> set[str]:
    removed = set(primitive.consumed_states)
    for group, next_state in primitive.state_group_updates.items():
        removed.update(
            state_id
            for state_id in state.exclusive_state_groups.get(group, set())
            if state_id != f"state:{next_state}"
        )
    return removed


def _context_compatible(primitive_context: set[str], query_context: set[str]) -> bool:
    return not query_context or not primitive_context or bool(primitive_context.intersection(query_context))


def _context_overlap(primitive_context: set[str], query_context: set[str]) -> float:
    if not primitive_context:
        return 0.5
    return len(primitive_context.intersection(query_context)) / len(query_context)
