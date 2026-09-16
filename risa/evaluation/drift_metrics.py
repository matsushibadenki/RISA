"""Pure G3.2 measurement helpers; probes and snapshots never update a model."""

from __future__ import annotations

from dataclasses import dataclass
import json

from risa.core.models import ReplaySummary
from risa.core.state import RisaState


@dataclass(frozen=True)
class StructureSnapshot:
    fingerprints: dict[str, dict[str, str]]


@dataclass(frozen=True)
class MechanismSnapshot:
    executed_context_splits: frozenset[str]
    merged_proposals: frozenset[str]
    adopted_merges: frozenset[str]
    dormant_candidates: frozenset[str]


def snapshot_mechanisms(state: RisaState) -> MechanismSnapshot:
    """Audit whether an ablated mechanism reached an operational state."""
    return MechanismSnapshot(
        executed_context_splits=frozenset(
            primitive.id for primitive in state.structural_primitives.values()
            if primitive.superseded_by
            and all(
                successor.startswith(f"{primitive.id}::context:")
                for successor in primitive.superseded_by
            )
        ),
        merged_proposals=frozenset(
            key for key, candidate in state.unnamed_concept_candidates.items()
            if candidate.derivation_type == "merged"
        ),
        adopted_merges=frozenset(
            key for key, candidate in state.unnamed_concept_candidates.items()
            if candidate.derivation_type == "merged"
            and candidate.lifecycle_status == "adopted" and not candidate.dormant
        ),
        dormant_candidates=frozenset(
            key for key, candidate in state.unnamed_concept_candidates.items()
            if candidate.dormant
        ),
    )


def mechanism_delta(before: MechanismSnapshot, after: MechanismSnapshot) -> dict[str, int]:
    return {
        "new_executed_context_splits": len(
            after.executed_context_splits - before.executed_context_splits
        ),
        "new_merged_proposals": len(after.merged_proposals - before.merged_proposals),
        "new_adopted_merges": len(after.adopted_merges - before.adopted_merges),
        "new_dormant_candidates": len(
            after.dormant_candidates - before.dormant_candidates
        ),
        "active_adopted_merges": len(after.adopted_merges),
    }


def snapshot_structures(state: RisaState) -> StructureSnapshot:
    """Capture material knowledge, excluding access time and replay counters."""
    groups: dict[str, dict[str, str]] = {}
    groups["nodes"] = {
        key: _fingerprint(node.to_dict(), {"last_activated_at", "recent_activity", "usage_count"})
        for key, node in state.graph.nodes_by_id.items()
        if node.kind != "event"
    }
    groups["edges"] = {
        repr(key): _fingerprint(edge.to_dict(), {"last_updated"})
        for key, edge in state.graph.edges_by_key.items()
        if not edge.source.startswith("event:") and not edge.target.startswith("event:")
    }
    groups["primitives"] = {
        key: _fingerprint(
            primitive.to_dict(),
            {"replay_count", "replay_success_count"},
        )
        for key, primitive in state.structural_primitives.items()
    }
    groups["candidates"] = {
        key: _fingerprint(
            candidate.to_dict(),
            {
                "evaluation_event_ids",
                "development_evaluation_event_ids",
                "final_evaluation_event_ids",
            },
        )
        for key, candidate in state.unnamed_concept_candidates.items()
    }
    return StructureSnapshot(groups)


def adaptation_touch_counts(
    before: StructureSnapshot, after: StructureSnapshot
) -> dict[str, object]:
    """Count changed pre-boundary structures and separately count additions/removals."""
    by_group: dict[str, dict[str, float | int]] = {}
    old_total = touched_total = added_total = removed_total = 0
    for group in sorted(before.fingerprints):
        old = before.fingerprints[group]
        new = after.fingerprints[group]
        removed = len(old.keys() - new.keys())
        touched = removed + sum(old[key] != new[key] for key in old.keys() & new.keys())
        added = len(new.keys() - old.keys())
        denominator = len(old)
        by_group[group] = {
            "pre_boundary": denominator,
            "touched": touched,
            "touch_ratio": touched / denominator if denominator else 0.0,
            "added": added,
            "removed": removed,
        }
        old_total += denominator
        touched_total += touched
        added_total += added
        removed_total += removed
    return {
        "pre_boundary": old_total,
        "touched": touched_total,
        "adaptation_touch_ratio": touched_total / old_total if old_total else 0.0,
        "added": added_total,
        "removed": removed_total,
        "by_group": by_group,
    }


def recovery_events(
    observations_and_accuracy: list[tuple[int, float]],
    reference_accuracy: float,
    *,
    target_fraction: float = 0.95,
    window: int = 5,
) -> int | None:
    """Return observed Event count at first sustained recovery, or None if censored."""
    if not 0.0 < target_fraction <= 1.0 or window < 1:
        raise ValueError("invalid recovery threshold or window")
    if not 0.0 <= reference_accuracy <= 1.0:
        raise ValueError("reference accuracy must be in [0, 1]")
    if reference_accuracy == 0.0:
        return None
    if observations_and_accuracy and observations_and_accuracy[0][0] == 0:
        if observations_and_accuracy[0][1] >= target_fraction * reference_accuracy:
            return 0
    previous_count = -1
    for index, (event_count, accuracy) in enumerate(observations_and_accuracy):
        if event_count < previous_count or not 0.0 <= accuracy <= 1.0:
            raise ValueError("probe samples must be ordered and accuracies in [0, 1]")
        previous_count = event_count
        if index + 1 < window:
            continue
        mean_accuracy = sum(
            item[1] for item in observations_and_accuracy[index + 1 - window : index + 1]
        ) / window
        if mean_accuracy >= target_fraction * reference_accuracy:
            return event_count
    return None


def replay_cost(summaries: list[ReplaySummary]) -> dict[str, int]:
    """Account for selection, model replay and deployment replay separately."""
    return {
        "calls": len(summaries),
        "selection_events_examined": sum(item.selection_events_examined for item in summaries),
        "model_events_reapplied": sum(item.replayed_events for item in summaries),
        "deployment_events_reapplied": sum(
            item.deployment_replayed_events for item in summaries
        ),
    }


def _fingerprint(payload: dict, excluded: set[str]) -> str:
    material = {key: value for key, value in payload.items() if key not in excluded}
    return json.dumps(material, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
