import random

import pytest

from experiments.references.prediction_indexes_before_20261007 import rebuild_prediction_indexes as rebuild_before
from risa.core.models import Event, PredictionQuery
from risa.core.state import RisaState
from risa.engine.prediction_indexes import rebuild_prediction_indexes
from risa.engine.predictor import predict_next_effect


INDEX_NAMES = ('actor_action_effect_counts', 'action_effect_counts',
               'actor_action_context_effect_counts', 'action_context_effect_counts',
               'actor_action_target_context_effect_counts', 'action_target_context_effect_counts',
               'action_target_role_context_effect_counts', 'activation_index')


@pytest.mark.parametrize('hops', [1, 2])
def test_rebuild_matches_reference_for_diverse_effects_and_role_scopes(hops):
    rng = random.Random(17)
    events = [Event(f'e{i}', rng.randrange(8), f'Actor {i%3}', f'Action {i%2}',
                    target='Station' if i%4 else None,
                    context_tags=['Indoor', ' Dry '] if i%3 else [],
                    target_roles=[' Machine ', 'machine'] if i%2 else [],
                    entity_bindings={'target': 'Station'},
                    entity_relations=[{'source': 'Station', 'relation': 'next_to', 'target': 'robot'}],
                    observed_effects=[f'effect {i}', f'effect {i+1}', f'effect {i}', 'shared'] if i%5 else [])
              for i in range(120)]
    rng.shuffle(events)
    state = RisaState(events_by_id={e.id:e for e in events}, target_role_readout_hops=hops)
    reference = RisaState(events_by_id=state.events_by_id, target_role_readout_hops=hops)
    snapshot = state.to_dict()
    rebuild_before(reference)
    rebuild_prediction_indexes(state)
    for name in INDEX_NAMES:
        assert getattr(state, name) == getattr(reference, name)
    assert state.to_dict() == snapshot
    for actor in ('Actor 0', 'Actor 1', 'unknown'):
        for action in ('Action 0', 'Action 1'):
            query = PredictionQuery(actor=actor, action=action, target='Station', target_roles=['machine'])
            assert predict_next_effect(state, query) == predict_next_effect(reference, query)
    # A second rebuild must discard membership from the previous event corpus.
    state.events_by_id = {e.id:e for e in events[:20]}
    reference.events_by_id = state.events_by_id
    rebuild_before(reference)
    rebuild_prediction_indexes(state)
    for name in INDEX_NAMES:
        assert getattr(state, name) == getattr(reference, name)


def test_rebuild_preserves_chronological_first_seen_order_and_counts():
    events = [Event(str(i), 50-i, 'actor', 'action', observed_effects=[f'e{i}', 'shared', 'shared'])
              for i in range(50)]
    state = RisaState(events_by_id={e.id:e for e in events})
    rebuild_prediction_indexes(state)
    expected = []
    for event in sorted(events, key=lambda e:(e.timestamp,e.id)):
        for effect in sorted(set(event.observed_effects)):
            if effect not in expected:
                expected.append(effect)
    assert state.activation_index['action:action'] == expected
    assert state.action_effect_counts['action']['shared'] == 50
    assert not hasattr(state, 'activation_membership')
