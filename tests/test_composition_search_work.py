from experiments.independent_joint_quality import training_episode
from experiments.temporal_candidate_evaluation import _training_state, _compare, _cases
from risa.core.state import RisaState
from risa.engine.runtime import train_events, TrainingOptions
from risa.engine.composer import compose_to_effect
from risa.engine.candidate_discovery import rebuild_candidate_inference_index


def test_work_is_reset_and_does_not_change_result_or_learned_state():
    state = train_events(RisaState(), [e for i in range(4) for e in training_episode(419, i)],
                         TrainingOptions(enable_metabolism=False, enable_replay=False))
    kwargs = dict(actor='new-operator', target='new-unit', actor_roles=['operator'], target_roles=['remote_unit'],
                  start_states=['connected'], start_variables={'energy': 2}, max_steps=2, enable_candidate_concepts=False)
    before = state.to_dict()
    expected = compose_to_effect(state, 'prime', 'done', **kwargs)
    work = {'stale': 999}
    assert compose_to_effect(state, 'prime', 'done', **kwargs, search_diagnostics=work) == expected
    assert 'stale' not in work
    assert work['expanded_nodes'] == 2
    assert work['primitive_scan_count'] == 4
    assert work['transition_checks'] == 4
    assert work['grounding_event_reads'] > 0
    old = dict(work)
    compose_to_effect(state, 'prime', 'done', **kwargs, search_diagnostics=work)
    assert work == old and state.to_dict() == before
    kwargs['actor_roles'] = ['observer']
    assert not compose_to_effect(state, 'prime', 'done', **kwargs, search_diagnostics=work).primitive_ids
    assert work['expanded_nodes'] == 1 and work['transition_checks'] == 0


def test_candidate_macro_execution_is_not_mistaken_for_zero_work():
    state = _training_state(29, True)
    candidate = next(c for c in state.unnamed_concept_candidates.values()
                     if c.structural_schema.get('kind') == 'temporal_sequence')
    # Counterfactual scoring setup only: production still requires adoption.
    candidate.lifecycle_status = 'adopted'
    rebuild_candidate_inference_index(state)
    work = {}
    kwargs = dict(actor='new-controller', target='new-device', actor_roles=['controller'],
                  target_roles=['powered_device'], start_states=['connected'], start_variables={'energy': 2}, max_steps=2)
    expected = compose_to_effect(state, 'charge', 'online', **kwargs)
    assert compose_to_effect(state, 'charge', 'online', **kwargs, search_diagnostics=work) == expected
    assert work['expanded_nodes'] == 0
    assert work['plan_candidates'] > 0
    assert work['candidate_step_attempts'] == work['transition_checks'] == 2
