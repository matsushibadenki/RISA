from dataclasses import replace

from experiments.structural_growth_evaluation import training_episode, heldout_cases
from risa.core.state import RisaState
from risa.engine.runtime import TrainingOptions, train_events
from risa.engine.composer import compose_to_effect, forecast_next_effects


def test_grounded_composition_rejects_unknown_and_reversed_relations_in_both_modes():
    state = train_events(RisaState(), [e for i in range(8) for e in training_episode(13, i)],
                         TrainingOptions(replay_max_events=12))
    for case in heldout_cases(13, 'independent-test', 24):
        q = case['query']
        for enabled in (False, True):
            result = compose_to_effect(state, 'charge', 'online', start_states=case['states'],
                start_variables={'energy': case['energy']}, max_steps=2, actor=q.actor, target=q.target,
                entity_bindings=q.entity_bindings, entity_relations=q.entity_relations,
                enable_candidate_concepts=enabled)
            assert bool(result.primitive_ids) == case['online'], case['kind']
        # The one-step readout shares the same grounding contract.
        forecasts = forecast_next_effects(state, 'charge', current_states=['connected'],
            current_variables={'energy': 2}, target=q.target,
            entity_bindings=q.entity_bindings, entity_relations=q.entity_relations)
        assert bool(forecasts) == (case['kind'] not in ('unsupported_relation', 'reverse_relation'))
    # Abstract planning without a target remains available.
    assert compose_to_effect(state, 'charge', 'online', start_states=['connected'],
                             start_variables={'energy': 2}, max_steps=2).primitive_ids
