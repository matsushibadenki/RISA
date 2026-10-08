from copy import deepcopy
from dataclasses import replace
import pytest
from risa.core.models import Event, PredictionQuery
from risa.core.state import RisaState
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import TrainingOptions, _previous_events, train_events
from experiments.history_setup_optimization import before
from experiments.references.runtime_before_history_20261008 import train_events as train_before


@pytest.mark.parametrize('reverse', [False, True])
def test_predecessors_match_stable_sort_with_ties_and_mutation(reverse):
    history=[Event(id=f'e{i}', timestamp=i//3, actor=' Robot ' if i%2 else 'OTHER',
                   action='go', episode_id='a' if i%3 else None) for i in range(30)]
    history.append(replace(history[7], actor='robot'))
    if reverse:
        history.reverse()
    history[0].timestamp=100
    incoming=[Event(id='new', timestamp=101, actor='robot', action='go', episode_id='a'),
              Event(id='new2', timestamp=102, actor='other', action='go')]
    actual=_previous_events(iter(history), incoming)
    expected=before(history,incoming)
    assert actual==expected
    for got, want in zip(actual, expected):
        assert all(got[key] is value for key,value in want.items())


@pytest.mark.parametrize('hops', [1, 2])
@pytest.mark.parametrize('episodes', [False, True])
def test_training_and_public_predictions_match_after_each_chunk(hops, episodes):
    current, reference = RisaState(target_role_readout_hops=hops), RisaState(target_role_readout_hops=hops)
    for start in range(0, 48, 6):
        events=[Event(id=f'e{i:03d}', timestamp=i//2+1, actor='Robot' if i%3 else 'OTHER',
                      action='go', target='device', target_roles=['switch'],
                      episode_id=f'episode-{i//8}' if episodes else None,
                      observed_states_before=['ready'], before_state_observed=True,
                      observed_effects=['on'] if i<24 else ['off'], context_tags=[f'c{i%2}'])
                for i in range(start,start+6)]
        train_events(current, deepcopy(events[::-1]), TrainingOptions(replay_max_events=8))
        train_before(reference,deepcopy(events[::-1]),TrainingOptions(replay_max_events=8))
        assert current.to_dict()==reference.to_dict()
        for actor in ('robot','other'):
            query=PredictionQuery(actor=actor, action='go', target='new',target_roles=['switch'])
            assert predict_next_effect(current,query)==predict_next_effect(reference,query)


def test_history_selection_ignores_stale_event_order():
    state=RisaState()
    history=[Event(id='z',timestamp=2,actor='a',action='go'), Event(id='a',timestamp=1,actor='a',action='go')]
    state.events_by_id={event.id:event for event in history}
    state.event_order=['z','a']
    state.events_by_id['a'].timestamp=3
    incoming=[Event(id='new',timestamp=4,actor='a',action='go')]
    assert _previous_events(state.events_by_id.values(),incoming)==before(history,incoming)
