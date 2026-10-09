from copy import deepcopy
import json

import pytest

from experiments.end_to_end_scale_evaluation import profile_scale, run_evaluation, validate_manifest
from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine.runtime import TrainingOptions, train_events


def manifest():
    return dict(event_scales=[24], seeds=[17], chunk_size=12, replay_budget=4,
                queries_per_scale=4, scale_time_budget_seconds=30)


def test_runtime_profiling_preserves_state():
    events = [Event(id=f'e{i}', timestamp=i, actor='actor', action='go',
                    observed_effects=['done']) for i in range(1, 5)]
    plain, measured = RisaState(), RisaState()
    train_events(plain, deepcopy(events))
    timings = {}
    train_events(measured, deepcopy(events), TrainingOptions(stage_seconds=timings))
    assert plain.to_dict() == measured.to_dict()
    assert {'graph_update', 'learning', 'candidate_discovery', 'replay'} <= timings.keys()
    assert all(value >= 0 for value in timings.values())


def test_real_profile_roundtrip_and_bounded_replay(tmp_path):
    row = profile_scale(manifest(), 17, 24, tmp_path / 'progress.json')
    assert row['status'] == 'complete'
    assert row['ingested_events'] == 24
    assert row['prediction_mismatches_after_reload'] == 0
    assert row['prediction_mismatches_after_compaction'] == 0
    assert row['prediction_correct'] == 4
    assert row['replayed_events'] <= 8
    assert row['planner_expanded_candidates'] > 0
    assert row['stored_bytes'] > 0
    assert {'save', 'load', 'compaction', 'planning'} <= row['stage_seconds'].keys()
    for key in ('process_cpu_seconds', 'voluntary_context_switches', 'involuntary_context_switches'):
        assert row[key] >= 0
        assert json.loads((tmp_path / 'progress.json').read_text())[key] == row[key]


def test_timeout_is_not_completion():
    config = manifest()
    config['scale_time_budget_seconds'] = 0.001
    result = run_evaluation(config)
    assert result['rows'][0]['status'] == 'time_budget_exceeded'
    assert result['decision'] == 'scale_gate_incomplete'
    assert result['million_event_decision'] == 'do_not_attempt'


def test_empty_scales_rejected():
    config = manifest()
    config['event_scales'] = []
    with pytest.raises(ValueError):
        validate_manifest(config)


def test_change_window_matches_sorted_reference_across_contexts(monkeypatch):
    import risa.engine.learner as learner
    events = [Event(id=f'change-{i:03d}', timestamp=i + 1, actor=f'actor-{i % 2}',
                    action='switch', target=f'target-{i % 2}',
                    context_tags=[f'context-{i % 3}'],
                    observed_effects=['a' if i < 18 or i >= 36 else 'b'])
              for i in range(54)]
    indexed = RisaState()
    for event in events:
        train_events(indexed, [deepcopy(event)])
    original = learner._update_change_hypothesis
    def sorted_reference(state, *args, **kwargs):
        saved = state.event_order
        state.event_order = []
        try:
            return original(state, *args, **kwargs)
        finally:
            state.event_order = saved
    monkeypatch.setattr(learner, '_update_change_hypothesis', sorted_reference)
    scanned = RisaState()
    for event in events:
        train_events(scanned, [deepcopy(event)])
    assert indexed.to_dict() == scanned.to_dict()
