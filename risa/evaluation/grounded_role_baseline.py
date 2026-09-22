"""Last-observed role-conditioned transition table for paired drift evaluation."""

from __future__ import annotations

import json
from collections import Counter
from typing import Callable, Protocol

from risa.core.models import Event, PredictionQuery
from risa.engine.graph_builder import normalize_label
from risa.evaluation.drift_metrics import recovery_events, retention_adaptation_audit
from risa.evaluation.drift_runner import DriftProbe, probe_return_identifiability


class GroundedRoleTransitionBaseline:
    """Memorize the latest observed outcome per action, supplied role and context."""

    def __init__(self) -> None:
        self._latest: dict[tuple[str, tuple[str, ...], tuple[str, ...]], tuple[str, ...]] = {}

    def observe(self, event: Event) -> None:
        self._latest[_key(event.action, event.target_roles, event.context_tags)] = tuple(
            sorted(normalize_label(effect) for effect in event.observed_effects)
        )

    def predict(self, query: PredictionQuery) -> tuple[str, ...]:
        return self._latest.get(
            _key(query.action, query.target_roles, query.context_tags), ()
        )

    def stored_bytes(self) -> int:
        payload = [
            {"action": action, "roles": roles, "context": context, "outcome": outcome}
            for (action, roles, context), outcome in sorted(self._latest.items())
        ]
        return len(json.dumps(payload, sort_keys=True).encode("utf-8"))


class GroundedRoleCountBaseline:
    """Vote over all observed outcomes per role/context; break ties by recency."""

    def __init__(self) -> None:
        self._counts: dict[
            tuple[str, tuple[str, ...], tuple[str, ...]], Counter[tuple[str, ...]]
        ] = {}
        self._latest: dict[
            tuple[str, tuple[str, ...], tuple[str, ...]], tuple[str, ...]
        ] = {}
        self._last_seen: dict[
            tuple[str, tuple[str, ...], tuple[str, ...]], dict[tuple[str, ...], int]
        ] = {}
        self._observations = 0

    def observe(self, event: Event) -> None:
        key = _key(event.action, event.target_roles, event.context_tags)
        outcome = tuple(sorted(normalize_label(effect) for effect in event.observed_effects))
        self._observations += 1
        self._counts.setdefault(key, Counter())[outcome] += 1
        self._latest[key] = outcome
        self._last_seen.setdefault(key, {})[outcome] = self._observations

    def predict(self, query: PredictionQuery) -> tuple[str, ...]:
        key = _key(query.action, query.target_roles, query.context_tags)
        counts = self._counts.get(key)
        if not counts:
            return ()
        return max(counts, key=lambda outcome: (counts[outcome], self._last_seen[key][outcome]))

    def stored_bytes(self) -> int:
        payload = [
            {"action": action, "roles": roles, "context": context,
             "counts": sorted((outcome, count) for outcome, count in counts.items()),
             "last_seen": sorted((outcome, index)
                                 for outcome, index in self._last_seen[key].items())}
            for key, counts in sorted(self._counts.items())
            for action, roles, context in [key]
        ]
        return len(json.dumps(payload, sort_keys=True).encode("utf-8"))


class _GroundedRoleModel(Protocol):
    def observe(self, event: Event) -> None: ...
    def predict(self, query: PredictionQuery) -> tuple[str, ...]: ...
    def stored_bytes(self) -> int: ...


def run_grounded_role_aba(
    a1: list[Event], b: list[Event], a2: list[Event],
    a_probes: list[DriftProbe], b_probes: list[DriftProbe],
    a_transfer_probes: list[DriftProbe], b_transfer_probes: list[DriftProbe],
    *, recovery_window: int,
    model_factory: Callable[[], _GroundedRoleModel] = GroundedRoleTransitionBaseline,
) -> dict[str, object]:
    """Score before learning each Event, matching the RISA drift order."""
    probe_ids = [probe.id for probe in a_probes + b_probes + a_transfer_probes + b_transfer_probes]
    if len(probe_ids) != len(set(probe_ids)):
        raise ValueError("baseline probe IDs must be unique")
    if set(probe_ids) & {event.id for event in a1 + b + a2}:
        raise ValueError("baseline scoring probes overlap learned Events")
    model = model_factory()
    for event in a1:
        model.observe(event)
    a1_accuracy = _accuracy(model, a_probes)
    a1_transfer_accuracy = _accuracy(model, a_transfer_probes)
    b_result = _phase(model, b, b_probes, reference_accuracy=1.0,
                      recovery_window=recovery_window)
    b_transfer_a = _accuracy(model, a_transfer_probes)
    b_transfer_b = _accuracy(model, b_transfer_probes)
    a2_entry_accuracy = _accuracy(model, a_probes)
    retention_audit = retention_adaptation_audit(
        a1_accuracy=a1_accuracy, b_exit_accuracy=b_result["exit_accuracy"],
        a2_entry_accuracy=a2_entry_accuracy,
    )
    a2_result = _phase(model, a2, a_probes, reference_accuracy=a1_accuracy,
                       recovery_window=recovery_window)
    return {
        "a1_accuracy": a1_accuracy,
        "a1_transfer_accuracy": a1_transfer_accuracy,
        "B_transfer_A_accuracy": b_transfer_a,
        "B_transfer_B_accuracy": b_transfer_b,
        "A2_transfer_A_accuracy": _accuracy(model, a_transfer_probes),
        **retention_audit,
        "return_identifiability": probe_return_identifiability(a_probes, b_probes),
        "B": b_result,
        "A2": a2_result,
        "stored_bytes": model.stored_bytes(),
        "stored_entries": len(model._latest),
    }


def _phase(
    model: _GroundedRoleModel, events: list[Event],
    probes: list[DriftProbe], *, reference_accuracy: float,
    recovery_window: int,
) -> dict[str, object]:
    trajectory = [(0, _accuracy(model, probes))]
    correct = 0
    for index, event in enumerate(events, 1):
        query = PredictionQuery(
            actor=event.actor, action=event.action, target=event.target,
            target_roles=list(event.target_roles), context_tags=list(event.context_tags),
        )
        correct += int(model.predict(query) == tuple(sorted(
            normalize_label(effect) for effect in event.observed_effects
        )))
        model.observe(event)
        trajectory.append((index, _accuracy(model, probes)))
    return {
        "online_pre_update_accuracy": correct / len(events) if events else None,
        "entry_accuracy": trajectory[0][1],
        "exit_accuracy": trajectory[-1][1],
        "recovery_events": recovery_events(
            trajectory, reference_accuracy, window=recovery_window
        ),
        "probe_accuracy_by_observed_events": trajectory,
    }


def _accuracy(model: _GroundedRoleModel, probes: list[DriftProbe]) -> float:
    if not probes:
        raise ValueError("baseline requires at least one probe")
    return sum(
        model.predict(probe.query) == tuple(sorted(
            normalize_label(effect) for effect in probe.expected_effects
        ))
        for probe in probes
    ) / len(probes)


def _key(
    action: str, roles: list[str], context_tags: list[str],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    return (
        normalize_label(action),
        tuple(sorted(normalize_label(role) for role in roles)),
        tuple(sorted(normalize_label(tag) for tag in context_tags)),
    )
