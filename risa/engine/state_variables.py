from __future__ import annotations

import math

from risa.core.models import Event, StateVariableSpec, StructuralPrimitive
from risa.engine.graph_builder import normalize_label


def merge_state_variable_specs(
    existing: dict[str, StateVariableSpec],
    events: list[Event],
) -> dict[str, StateVariableSpec]:
    merged = {
        name: StateVariableSpec(spec.unit, spec.minimum, spec.maximum)
        for name, spec in existing.items()
    }

    for event in events:
        _validate_numeric_values(event)
        referenced = set(event.numeric_preconditions) | set(event.state_variable_deltas)
        for raw_name in referenced:
            merged.setdefault(normalize_label(raw_name), StateVariableSpec())
        for raw_name, incoming in event.state_variable_specs.items():
            name = normalize_label(raw_name)
            _validate_spec(incoming)
            current = merged.setdefault(name, StateVariableSpec())
            merged[name] = _merge_spec(name, current, incoming)
    return merged


def requirements_satisfied(
    primitive: StructuralPrimitive,
    current: dict[str, float],
) -> bool:
    return all(
        current.get(name, 0.0) >= minimum
        for name, minimum in primitive.numeric_preconditions.items()
    )


def apply_variable_deltas(
    specs: dict[str, StateVariableSpec],
    current: dict[str, float],
    deltas: dict[str, float],
) -> dict[str, float] | None:
    candidate = dict(current)
    for name, delta in deltas.items():
        candidate[name] = candidate.get(name, 0.0) + delta

    for name in deltas:
        value = candidate[name]
        spec = specs.get(name, StateVariableSpec())
        if spec.minimum is not None and value < spec.minimum:
            return None
        if spec.maximum is not None and value > spec.maximum:
            return None
    return candidate


def _validate_numeric_values(event: Event) -> None:
    values = [*event.numeric_preconditions.values(), *event.state_variable_deltas.values()]
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("numeric state values must be finite")


def _validate_spec(spec: StateVariableSpec) -> None:
    if spec.minimum is not None and not math.isfinite(spec.minimum):
        raise ValueError("state variable minimum must be finite")
    if spec.maximum is not None and not math.isfinite(spec.maximum):
        raise ValueError("state variable maximum must be finite")
    if spec.minimum is not None and spec.maximum is not None and spec.minimum > spec.maximum:
        raise ValueError("state variable minimum must not exceed maximum")


def _merge_spec(
    name: str,
    current: StateVariableSpec,
    incoming: StateVariableSpec,
) -> StateVariableSpec:
    if current.unit and incoming.unit and current.unit != incoming.unit:
        raise ValueError(f"conflicting unit for state variable '{name}'")
    if (
        current.minimum is not None
        and incoming.minimum is not None
        and current.minimum != incoming.minimum
    ):
        raise ValueError(f"conflicting minimum for state variable '{name}'")
    if (
        current.maximum is not None
        and incoming.maximum is not None
        and current.maximum != incoming.maximum
    ):
        raise ValueError(f"conflicting maximum for state variable '{name}'")
    return StateVariableSpec(
        unit=current.unit or incoming.unit,
        minimum=current.minimum if current.minimum is not None else incoming.minimum,
        maximum=current.maximum if current.maximum is not None else incoming.maximum,
    )
