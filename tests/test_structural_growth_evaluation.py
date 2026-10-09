import json
from pathlib import Path
import pytest
from experiments.structural_growth_evaluation import heldout_cases, training_episode, validate_manifest, worker


def config():
    return json.loads(Path('experiments/g3_structural_growth_manifest.json').read_text())


def test_structural_heldout_ids_entities_and_variable_names_are_independent():
    training=training_episode(13,0)
    development=heldout_cases(13,'development',24);final=heldout_cases(13,'final',24)
    assert development==heldout_cases(13,'development',24)
    assert {c['id'] for c in development}.isdisjoint(c['id'] for c in final)
    targets={e.target for e in training}
    assert targets.isdisjoint(c['query'].target for c in development+final)
    assert all(not c['query'].target_roles for c in development+final)
    assert all(not e.target_roles for e in training)
    assert set(training[0].entity_bindings).isdisjoint(development[0]['query'].entity_bindings)


def test_structural_controls_cover_resources_states_and_relation_direction():
    cases=heldout_cases(13,'final',24)
    assert sum(c['online'] for c in cases)==8
    assert {c['kind'] for c in cases}=={'powered','cooled','missing_state','low_energy','unsupported_relation','reverse_relation'}
    assert all(not c['online'] for c in cases if c['kind'] in ('low_energy','missing_state'))
    assert all(not c['effects'] for c in cases if c['kind'] in ('unsupported_relation','reverse_relation'))


def test_structural_pilot_discovers_candidates_and_preserves_complete_reload(tmp_path):
    manifest=config();manifest.update(episode_checkpoints=[4,8,12],cases_per_partition=6)
    path=tmp_path/'progress.json';worker(manifest,13,path)
    result=json.loads(path.read_text())
    assert [r['events'] for r in result['rows']]==[12,24,36]
    assert all(r['reload_mismatches']==0 for r in result['rows'])
    assert result['rows'][-1]['candidate_kinds']['temporal_sequence']>0
    assert result['rows'][-1]['candidate_kinds']['relational_sequence']>0
    assert result['rows'][-1]['adopted_candidates']==0


def test_unbalanced_controls_and_invalid_checkpoints_rejected():
    manifest=config();manifest['cases_per_partition']=25
    with pytest.raises(ValueError):validate_manifest(manifest)
    manifest=config();manifest['episode_checkpoints']=[8,4,16]
    with pytest.raises(ValueError):validate_manifest(manifest)
