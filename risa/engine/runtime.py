from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from risa.core.models import Event, ReplaySummary, UnnamedConceptCandidate
from risa.core.state import RisaState
from risa.engine.abstractor import rebuild_concepts
from risa.engine.adaptation import execute_safe_adaptations
from risa.engine.candidate_discovery import discover_unnamed_candidates
from risa.engine.graph_builder import ingest_event
from risa.engine.graph_builder import normalize_label
from risa.engine.learner import learn_from_event, link_temporal_precedence
from risa.engine.metabolism import decay_nodes
from risa.engine.replay import replay_structural_memory
from risa.engine.readout_compaction import restore_compacted_readouts_for_learning
from risa.engine.state_variables import merge_state_variable_specs
from risa.engine.validator import validate_event_prediction


@dataclass(frozen=True)
class TrainingOptions:
    """Feature switches used by controlled ablation experiments."""

    enable_metabolism: bool = True
    enable_replay: bool = True
    enable_adaptation: bool = True
    enable_coactivation: bool = True
    enable_context_split: bool = True
    enable_contextual_split_proposal: bool = False
    enable_candidate_specialization: bool = True
    enable_candidate_merge: bool = True
    frozen_context_conditions: dict[str, tuple[tuple[str, ...], ...]] | None = None
    retain_validated_on_consistent_extension: bool = False
    candidate_extension_validator: Callable[
        [RisaState, UnnamedConceptCandidate, UnnamedConceptCandidate], bool
    ] | None = None
    replay_max_events: int | None = None
    replay_summaries: list[ReplaySummary] | None = None


def train_events(
    state: RisaState,
    events: list[Event],
    options: TrainingOptions | None = None,
) -> RisaState:
    options = options or TrainingOptions()
    if options.retain_validated_on_consistent_extension and options.candidate_extension_validator is None:
        raise ValueError("candidate validation inheritance requires an extension validator")
    new_events = _validate_and_filter_events(state, events)
    if not new_events:
        return state
    restore_compacted_readouts_for_learning(state)
    state.state_variable_specs = merge_state_variable_specs(
        state.state_variable_specs,
        new_events,
    )
    existing_events = sorted(
        state.events_by_id.values(),
        key=lambda item: (item.timestamp, item.id),
    )
    previous_global_by_episode: dict[str, Event] = {}
    previous_by_actor_episode: dict[tuple[str, str], Event] = {}
    for event in existing_events:
        episode_id = event.episode_id or "__default__"
        previous_global_by_episode[episode_id] = event
        previous_by_actor_episode[(episode_id, normalize_label(event.actor))] = event

    for event in sorted(new_events, key=lambda item: (item.timestamp, item.id)):
        if options.enable_metabolism:
            decay_nodes(state, event.timestamp)
        validate_event_prediction(state, event)
        ingest_event(state, event, enable_coactivation=options.enable_coactivation)
        learn_from_event(state, event)
        actor = normalize_label(event.actor)
        episode_id = event.episode_id or "__default__"
        actor_episode = (episode_id, actor)
        link_temporal_precedence(
            state,
            previous_by_actor_episode.get(actor_episode),
            event,
            "precedes",
        )
        link_temporal_precedence(
            state,
            previous_global_by_episode.get(episode_id),
            event,
            "globally_precedes",
        )
        previous_by_actor_episode[actor_episode] = event
        previous_global_by_episode[episode_id] = event
    rebuild_concepts(state)
    discover_unnamed_candidates(
        state,
        enable_specialization=options.enable_candidate_specialization,
        enable_merge=options.enable_candidate_merge,
        frozen_context_conditions=options.frozen_context_conditions,
        retain_validated_on_consistent_extension=(
            options.retain_validated_on_consistent_extension
        ),
        extension_validator=options.candidate_extension_validator,
    )
    if options.enable_replay:
        summary = replay_structural_memory(
            state, max_events=options.replay_max_events,
            enable_contextual_split_proposal=options.enable_contextual_split_proposal,
        )
        if options.replay_summaries is not None:
            options.replay_summaries.append(summary)
    if options.enable_adaptation:
        execute_safe_adaptations(
            state, enable_context_split=options.enable_context_split
        )
    return state


def _validate_and_filter_events(state: RisaState, events: list[Event]) -> list[Event]:
    """Make ingestion idempotent and reject ambiguous history rewrites."""
    accepted: list[Event] = []
    seen: dict[str, Event] = dict(state.events_by_id)
    latest_by_episode: dict[str, tuple[int, str]] = {}
    for existing in state.events_by_id.values():
        episode_id = existing.episode_id or "__default__"
        latest_by_episode[episode_id] = max(
            latest_by_episode.get(episode_id, (existing.timestamp, existing.id)),
            (existing.timestamp, existing.id),
        )

    for event in sorted(events, key=lambda item: (item.timestamp, item.id)):
        existing = seen.get(event.id)
        if existing is not None:
            if existing.to_dict() == event.to_dict():
                continue
            raise ValueError(
                f"event ID '{event.id}' already exists with different content; "
                "explicit correction is required"
            )

        episode_id = event.episode_id or "__default__"
        latest = latest_by_episode.get(episode_id)
        if latest is not None and (event.timestamp, event.id) <= latest:
            raise ValueError(
                f"late-arriving event '{event.id}' would rewrite episode "
                f"'{episode_id}' ordering"
            )
        accepted.append(event)
        seen[event.id] = event
        latest_by_episode[episode_id] = (event.timestamp, event.id)
    return accepted
