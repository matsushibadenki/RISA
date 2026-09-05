"""Read-only, synthetic design probes; these are not a generalization benchmark.
Run from the repository root: python3 -m experiments.structural_assessment
"""
import json
from unittest.mock import patch

from risa.core.models import Event, PredictionQuery, StructuralPrimitive
from risa.core.state import RisaState
from risa.engine.composer import forecast_next_effects
from risa.engine.predictor import predict_next_effect
from risa.engine.replay import _replay_deployment_trajectory
from risa.core.models import ReplaySummary
from risa.engine.runtime import train_events
from risa.engine.simulator import simulate_branches


def run():
    result = {}
    state = RisaState()
    events = [Event(str(i), i, 'dog', 'run', observed_effects=['tired']) for i in range(3)]
    train_events(state, events)
    result['unseen_actor_control'] = {
        'risa': predict_next_effect(state, PredictionQuery(actor='wolf', action='run')).predicted_effects,
        'action_frequency_baseline': [max(state.action_effect_counts['run'], key=state.action_effect_counts['run'].get)],
    }
    result['unknown_action'] = predict_next_effect(
        state, PredictionQuery(actor='dog', action='never_seen')
    ).to_dict()
    before = state.action_effect_counts['run']['tired']
    train_events(state, events)
    result['duplicate_ingestion'] = {
        'unique_events': len(state.events_by_id), 'count_before': before,
        'count_after': state.action_effect_counts['run']['tired'],
    }

    state = RisaState()
    train_events(state, [Event(str(i), i, 'robot', 'activate',
        observed_effects=['lit', 'warm'], state_variable_deltas={'energy': -1}) for i in range(3)])
    result['simultaneous_effects'] = {
        'observed_together': ['lit', 'warm'],
        'branches': [{'states': b.current_states, 'variables': b.current_variables}
            for b in simulate_branches(state, 'activate', start_variables={'energy': 3}, max_steps=1)],
    }

    state = RisaState()
    train_events(state, [Event(str(i), i, 'robot', 'touch', target=target,
        observed_effects=[effect]) for i, (target, effect) in enumerate([
            ('heater', 'hot'), ('ice', 'cold'), ('heater', 'hot'), ('ice', 'cold')])])
    result['target_binding'] = {target: predict_next_effect(
        state, PredictionQuery(actor='robot', action='touch', target=target)).predicted_effects
        for target in ['heater', 'ice']}

    # A controlled fixture isolates deployment replay from adoption heuristics.
    state = RisaState()
    for name, action, output, conditions, groups in [
        ('left', 'route', 'left', set(), {'location': 'left'}),
        ('right', 'route', 'right', set(), {'location': 'right'}),
        ('join', 'join', 'impossible', {'state:left', 'state:right'}, {}),
    ]:
        state.structural_primitives[name] = StructuralPrimitive(
            id=name, relation_type='transition', role_signature='entity->process->state',
            input_conditions={f'process:{action}'}, input_state_conditions=conditions,
            output_state=output, state_group_updates=groups, adopted=True, adoption_score=1.0,
        )
    state.exclusive_state_groups['location'] = {'state:left', 'state:right'}
    state.events_by_id = {
        'r': Event('r', 0, 'robot', 'route', observed_effects=['left']),
        'j': Event('j', 1, 'robot', 'join', observed_effects=['impossible']),
    }
    # Evidence keys activate replay; no fixture primitive is re-scored during the probe.
    state.event_primitive_ids = {'r': ['probe-only'], 'j': ['probe-only']}
    calls = []
    def traced_forecast(*args, **kwargs):
        candidates = forecast_next_effects(*args, **kwargs)
        calls.append({'action': kwargs['action'], 'states': kwargs['current_states'],
                      'outputs': [c.target_effect for c in candidates]})
        return candidates
    with patch('risa.engine.replay.forecast_next_effects', side_effect=traced_forecast):
        _replay_deployment_trajectory(state, ReplaySummary())
    result['deployment_replay_branch_union'] = calls
    return result


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
