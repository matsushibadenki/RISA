from __future__ import annotations

import json
import math
from pathlib import Path

from risa.core.models import Event, StateVariableSpec


def _validate_event(data: dict) -> Event:
    required = ["id", "timestamp", "actor", "action", "observed_effects"]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Missing required event fields: {', '.join(missing)}")
    if not data["observed_effects"]:
        raise ValueError("observed_effects must contain at least one effect")
    group_updates = {
        str(group): str(state) for group, state in data.get("state_group_updates", {}).items()
    }
    missing_group_effects = sorted(set(group_updates.values()) - set(data["observed_effects"]))
    if missing_group_effects:
        raise ValueError("state_group_updates values must also appear in observed_effects")
    numeric_preconditions = {
        str(name): float(value) for name, value in data.get("numeric_preconditions", {}).items()
    }
    state_variable_deltas = {
        str(name): float(value) for name, value in data.get("state_variable_deltas", {}).items()
    }
    if not all(math.isfinite(value) for value in [*numeric_preconditions.values(), *state_variable_deltas.values()]):
        raise ValueError("numeric state values must be finite")
    state_variable_specs: dict[str, StateVariableSpec] = {}
    for name, raw_spec in data.get("state_variable_specs", {}).items():
        minimum = raw_spec.get("minimum")
        maximum = raw_spec.get("maximum")
        spec = StateVariableSpec(
            unit=str(raw_spec.get("unit", "")),
            minimum=None if minimum is None else float(minimum),
            maximum=None if maximum is None else float(maximum),
        )
        if spec.minimum is not None and not math.isfinite(spec.minimum):
            raise ValueError("state variable minimum must be finite")
        if spec.maximum is not None and not math.isfinite(spec.maximum):
            raise ValueError("state variable maximum must be finite")
        if spec.minimum is not None and spec.maximum is not None and spec.minimum > spec.maximum:
            raise ValueError("state variable minimum must not exceed maximum")
        state_variable_specs[str(name)] = spec
    return Event(
        id=str(data["id"]),
        timestamp=int(data["timestamp"]),
        actor=str(data["actor"]),
        action=str(data["action"]),
        target=None if data.get("target") is None else str(data.get("target")),
        preconditions=[str(condition) for condition in data.get("preconditions", [])],
        consumed_states=[str(state) for state in data.get("consumed_states", [])],
        state_group_updates=group_updates,
        numeric_preconditions=numeric_preconditions,
        state_variable_deltas=state_variable_deltas,
        state_variable_specs=state_variable_specs,
        observed_effects=[str(effect) for effect in data.get("observed_effects", [])],
        context_tags=[str(tag) for tag in data.get("context_tags", [])],
    )


def parse_events(path: str | Path) -> list[Event]:
    input_path = Path(path)
    text = input_path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if text.startswith("["):
        payload = json.loads(text)
        return [_validate_event(item) for item in payload]

    events: list[Event] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(_validate_event(json.loads(line)))
    return events
