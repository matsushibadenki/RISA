from __future__ import annotations

from collections.abc import Iterable

from risa.core.models import StructuralPrimitive, TransitionApplication
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
from risa.engine.state_variables import apply_variable_deltas, requirements_satisfied


def apply_primitive_transition(
    state: RisaState,
    primitive: StructuralPrimitive,
    current_states: Iterable[str],
    current_variables: dict[str, float],
) -> TransitionApplication | None:
    """Apply one complete transition outcome without mutating persistent state."""
    available_states = {
        f"state:{normalize_label(state_name.removeprefix('state:'))}"
        for state_name in current_states
    }
    variables = {
        normalize_label(name): float(value) for name, value in current_variables.items()
    }
    if not primitive.input_state_conditions.issubset(available_states):
        return None
    if not requirements_satisfied(primitive, variables):
        return None

    resulting_variables = apply_variable_deltas(
        state.state_variable_specs,
        variables,
        primitive.state_variable_deltas,
    )
    if resulting_variables is None:
        return None

    removed_states = set(primitive.consumed_states)
    for group, next_state in primitive.state_group_updates.items():
        removed_states.update(
            state_id
            for state_id in state.exclusive_state_groups.get(group, set())
            if state_id != f"state:{next_state}"
        )

    added_states = {f"state:{state_name}" for state_name in primitive.produced_states}
    resulting_states = (available_states - removed_states) | added_states
    return TransitionApplication(
        added_states=sorted(
            state_id.removeprefix("state:") for state_id in added_states
        ),
        removed_states=sorted(
            state_id.removeprefix("state:") for state_id in removed_states
        ),
        resulting_states=sorted(
            state_id.removeprefix("state:") for state_id in resulting_states
        ),
        variable_deltas=dict(sorted(primitive.state_variable_deltas.items())),
        resulting_variables=dict(sorted(resulting_variables.items())),
    )
