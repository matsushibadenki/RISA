from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from dataclasses import dataclass
from typing import Callable, Iterable

from risa.core.models import Event, ReplaySummary, UnnamedConceptCandidate
from risa.core.state import RisaState
from risa.engine.abstractor import rebuild_concepts
from risa.engine.adaptation import execute_safe_adaptations
from risa.engine.candidate_discovery import discover_unnamed_candidates
from risa.engine.graph_builder import ingest_event
from risa.engine.graph_builder import normalize_label
from risa.engine.learner import learn_from_event, link_temporal_precedence
from risa.engine.metabolism import decay_nodes, rebuild_metabolism_index
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
    reactivate_validated_orphaned_ancestors: bool = False
    retain_validated_on_consistent_extension: bool = False
    candidate_extension_validator: Callable[
        [RisaState, UnnamedConceptCandidate, UnnamedConceptCandidate], bool
    ] | None = None
    replay_max_events: int | None = None
    replay_summaries: list[ReplaySummary] | None = None
    stage_seconds: dict[str, float] | None = None
    enable_indexed_metabolism: bool = True


def _previous_events(
    history: Iterable[Event], incoming: list[Event],
) -> tuple[dict[str, Event], dict[tuple[str, str], Event]]:
    """Select the same latest predecessors without sorting unrelated episodes."""
    episodes = {event.episode_id or "__default__" for event in incoming}
    actors = {(event.episode_id or "__default__", normalize_label(event.actor))
              for event in incoming}
    global_previous: dict[str, Event] = {}
    actor_previous: dict[tuple[str, str], Event] = {}
    for event in history:
        episode = event.episode_id or "__default__"
        if episode not in episodes:
            continue
        key = (event.timestamp, event.id)
        previous = global_previous.get(episode)
        # >= preserves the last insertion when stable sorting finds equal keys.
        if previous is None or key >= (previous.timestamp, previous.id):
            global_previous[episode] = event
        actor_episode = (episode, normalize_label(event.actor))
        if actor_episode in actors:
            previous = actor_previous.get(actor_episode)
            if previous is None or key >= (previous.timestamp, previous.id):
                actor_previous[actor_episode] = event
    return global_previous, actor_previous


def train_events(
    state: RisaState,
    events: list[Event],
    options: TrainingOptions | None = None,
) -> RisaState:
    options = options or TrainingOptions()
    if options.retain_validated_on_consistent_extension and options.candidate_extension_validator is None:
        raise ValueError("candidate validation inheritance requires an extension validator")
    with _measure_stage(options.stage_seconds, "input_validation"):
        new_events = _validate_and_filter_events(state, events)
    if not new_events:
        return state
    with _measure_stage(options.stage_seconds, "history_setup"):
        if options.enable_metabolism and options.enable_indexed_metabolism:
            rebuild_metabolism_index(state)
        restore_compacted_readouts_for_learning(state)
        state.state_variable_specs = merge_state_variable_specs(
            state.state_variable_specs,
            new_events,
        )
        previous_global_by_episode, previous_by_actor_episode = _previous_events(
            state.events_by_id.values(), new_events,
        )

    for event in sorted(new_events, key=lambda item: (item.timestamp, item.id)):
        with _measure_stage(options.stage_seconds, "metabolism"):
            if options.enable_metabolism:
                decay_nodes(state, event.timestamp, indexed=options.enable_indexed_metabolism)
        with _measure_stage(options.stage_seconds, "pre_update_prediction"):
            validate_event_prediction(state, event)
        with _measure_stage(options.stage_seconds, "graph_update"):
            ingest_event(state, event, enable_coactivation=options.enable_coactivation)
        with _measure_stage(options.stage_seconds, "learning"):
            learn_from_event(state, event)
        actor = normalize_label(event.actor)
        episode_id = event.episode_id or "__default__"
        actor_episode = (episode_id, actor)
        with _measure_stage(options.stage_seconds, "temporal_linking"):
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
    with _measure_stage(options.stage_seconds, "concept_rebuild"):
        rebuild_concepts(state)
    with _measure_stage(options.stage_seconds, "candidate_discovery"):
        discover_unnamed_candidates(
            state,
            enable_specialization=options.enable_candidate_specialization,
            enable_merge=options.enable_candidate_merge,
            frozen_context_conditions=options.frozen_context_conditions,
            reactivate_validated_orphaned_ancestors=options.reactivate_validated_orphaned_ancestors,
            retain_validated_on_consistent_extension=(
                options.retain_validated_on_consistent_extension
            ),
            extension_validator=options.candidate_extension_validator,
        )
    if options.enable_replay:
        with _measure_stage(options.stage_seconds, "replay"):
            summary = replay_structural_memory(
                state, max_events=options.replay_max_events,
                enable_contextual_split_proposal=options.enable_contextual_split_proposal,
            )
        if options.replay_summaries is not None:
            options.replay_summaries.append(summary)
    if options.enable_adaptation:
        with _measure_stage(options.stage_seconds, "adaptation"):
            execute_safe_adaptations(
                state, enable_context_split=options.enable_context_split
            )
    return state


def _validate_and_filter_events(state: RisaState, events: list[Event]) -> list[Event]:
    """Make ingestion idempotent and reject ambiguous history rewrites."""
    accepted: list[Event] = []
    seen: dict[str, Event] = {}
    incoming_episodes = {event.episode_id or "__default__" for event in events}
    latest_by_episode: dict[str, tuple[int, str]] = {}
    for existing in state.events_by_id.values():
        episode_id = existing.episode_id or "__default__"
        if episode_id not in incoming_episodes:
            continue
        latest_by_episode[episode_id] = max(
            latest_by_episode.get(episode_id, (existing.timestamp, existing.id)),
            (existing.timestamp, existing.id),
        )

    for event in sorted(events, key=lambda item: (item.timestamp, item.id)):
        existing = seen.get(event.id)
        if existing is None:
            existing = state.events_by_id.get(event.id)
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


@contextmanager
def _measure_stage(timings: dict[str, float] | None, name: str):
    """Optional cumulative wall-time diagnostics; never persisted in learned state."""
    if timings is None:
        yield
        return
    started = perf_counter()
    try:
        yield
    finally:
        timings[name] = timings.get(name, 0.0) + perf_counter() - started
