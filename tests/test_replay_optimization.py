from unittest.mock import patch

import pytest

from risa.core.models import Event, PredictionQuery
from risa.core.state import RisaState
from risa.engine.runtime import TrainingOptions, train_events
from risa.engine.replay import replay_structural_memory
from risa.engine.predictor import predict_next_effect
from experiments.references.replay_before_20261008 import replay_structural_memory as replay_before


def drift_state(hops):
    state = RisaState(target_role_readout_hops=hops)
    events = [Event(f'e{i}', i+1, 'robot', 'toggle', target='switch',
                    observed_effects=['on' if i<4 else 'off'],
                    target_roles=['control'], context_tags=['inside'],
                    before_state_observed=True, observed_states_before=['ready'],
                    preconditions=['ready']) for i in range(8)]
    train_events(state, events, TrainingOptions(enable_replay=False))
    return state


@pytest.mark.parametrize('hops', [1, 2])
@pytest.mark.parametrize('bound', [0, 2, None])
@pytest.mark.parametrize('split', [False, True])
def test_replay_summary_counters_adoption_and_predictions_match_reference(hops, bound, split):
    source = drift_state(hops).to_dict()
    state, reference = RisaState.from_dict(source), RisaState.from_dict(source)
    result = replay_structural_memory(state, max_events=bound, enable_contextual_split_proposal=split)
    expected = replay_before(reference, max_events=bound, enable_contextual_split_proposal=split)
    assert result == expected
    assert state.to_dict() == reference.to_dict()
    if bound is None:
        assert result.failed_events > 0
    for action in ('toggle','unknown'):
        query = PredictionQuery('robot', action, target='switch', context_tags=['inside'], target_roles=['control'])
        assert predict_next_effect(state, query) == predict_next_effect(reference, query)


def test_replay_avoids_unused_event_provenance_but_public_prediction_keeps_it():
    state = drift_state(1)
    with patch('risa.engine.predictor._event_supporting_paths', side_effect=AssertionError('unused provenance')):
        replay_structural_memory(state, max_events=2)
    query = PredictionQuery('robot', 'toggle', target='switch', context_tags=['inside'], target_roles=['control'])
    assert predict_next_effect(state, query).evidence_event_ids
