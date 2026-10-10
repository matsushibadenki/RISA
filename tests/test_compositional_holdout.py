import json
from pathlib import Path

import pytest

from experiments.compositional_holdout import (
    ContractModel, audit_split, heldout_cases, run_experiment, training_episode,
)
from risa.core.state import RisaState
from risa.engine.composer import compose_to_effect
from risa.engine.runtime import TrainingOptions, train_events


def fixture_events(world, count=8):
    return [e for i in range(count) for e in training_episode(701, world, i)]


def test_holdout_is_a_new_complete_path_with_observed_local_transitions():
    events = fixture_events('independent')
    cases = heldout_cases(701, 'independent')
    assert not any(audit_split(events, cases).values())
    # Audit must detect an accidental training copy of a held-out trajectory.
    copied = training_episode(701, 'independent', 100)
    copied[-1].action = 'finish_b'
    with pytest.raises(AssertionError, match='invalid compositional split'):
        audit_split(events + copied, cases)
    for branch in ('a', 'b'):
        for role in ('operator', 'autonomous'):
            assert {e.source for e in events if e.action == f'prepare_{branch}' and role in e.actor_roles} == {'source:0', 'source:1'}


@pytest.mark.parametrize('world', ['independent', 'coupled'])
def test_dependencies_are_required_and_each_ablation_breaks_its_own_probe(world):
    model = ContractModel(fixture_events(world))
    cases = heldout_cases(701, world)
    for case in cases:
        assert model.solve(case, 3)[0] == case['expected']
        if case['category'] == 'shared_resource':
            assert model.solve(case, 3, 'reset_resource')[0]
        if case['category'] in ('crossed_roles', 'wrong_identity'):
            assert model.solve(case, 3, 'role_marginals')[0]
        if case['category'] == 'unseen_path':
            assert model.solve(case, 3, 'drop_ticket')[0]
            assert not model.solve(case, 3, 'whole_path')[0]
        if case['expected']:
            assert not model.solve(case, 2)[0]


def test_table_cannot_invent_an_unobserved_finish_action():
    events = [e for i in (0, 2, 4, 6) for e in training_episode(701, 'independent', i)]
    model = ContractModel(events)
    unseen = next(c for c in heldout_cases(701, 'independent') if c['start'] == 'a' and c['finish'] == 'b')
    assert not model.solve(unseen, 3)[0]


def test_native_composition_preserves_atomic_receipt_and_shared_resource():
    state = RisaState()
    train_events(state, fixture_events('independent'), TrainingOptions(enable_metabolism=False, enable_replay=False))
    case = next(c for c in heldout_cases(701, 'independent') if c['category'] == 'unseen_path')
    result = compose_to_effect(state, case['start_action'], case['goal'], actor=case['actor'],
        target=case['target'], actor_roles=case['actor_roles'], target_roles=case['target_roles'],
        start_states=case['states'], start_variables={'energy': 3}, max_steps=3)
    assert len(result.primitive_ids) == 3
    assert set(result.added_states) == {case['goal'], 'receipt'}
    assert result.resulting_variables == {'energy': 0}
    assert result.removed_states == ['ready']


def test_full_runner_reports_negative_controls_reload_and_no_candidate_gain():
    manifest = json.loads(Path('experiments/g3_compositional_holdout_manifest.json').read_text())
    manifest.update(seeds=[701], training_episode_checkpoints=[8, 16])
    result = run_experiment(manifest)
    assert len(result['rows']) == 4
    for row in result['rows']:
        assert not any(row['split_audit'].values())
        assert row['reload_mismatches'] == row['adoption_labels'] == 0
        assert not row['candidate_advantage_pass']
        assert row['risa_false_accept_gate']
        for name in ('risa_candidate_on', 'risa_candidate_off', 'risa_primitives_shared_bfs', 'factorized_table'):
            score = row['metrics'][name]['all']
            assert score['correct'] == 20 and score['false_accepts'] == 0
            assert score['positive_correct'] == (8 if row['world'] == 'independent' else 4)
    for world in manifest['worlds']:
        small, large = [r for r in result['rows'] if r['world'] == world]
        assert large['search_work']['risa_candidate_on']['grounding_event_reads'] == 2 * small['search_work']['risa_candidate_on']['grounding_event_reads']


def test_runner_rejects_incomplete_source_family_blocks():
    manifest = json.loads(Path('experiments/g3_compositional_holdout_manifest.json').read_text())
    manifest['training_episode_checkpoints'] = [4]
    with pytest.raises(ValueError, match='eight-episode'):
        run_experiment(manifest)
