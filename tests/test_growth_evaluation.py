import json
from pathlib import Path
import pytest
from experiments.growth_evaluation import cases, joint_signal, validate_manifest, worker


def manifest():
    return json.loads(Path('experiments/g3_growth_manifest.json').read_text())


def test_partitions_have_disjoint_entities_ids_and_balanced_controls():
    development=cases(13,'development',60);final=cases(13,'final',60)
    assert development==cases(13,'development',60)
    for select in (lambda c:c[0],lambda c:c[1].actor,lambda c:c[1].target):
        assert {select(c) for c in development}.isdisjoint(select(c) for c in final)
    assert sum(not expected for _,_,expected in final)==20
    assert sum(expected==['effect-0'] for _,_,expected in final)==20


def test_growth_and_quality_are_both_required_for_signal():
    rows=[dict(active_structures=2,marginal_bytes_per_event=1500),
          dict(active_structures=2,marginal_bytes_per_event=1400),
          dict(active_structures=2,marginal_bytes_per_event=1450,metrics={'final':dict(accuracy=1,no_role_accuracy=1/3,false_generalization_rate=0,no_role_false_generalization_rate=0)})]
    signal=joint_signal(rows,manifest())
    assert signal['prediction_gain_pass'] and signal['false_generalization_pass']
    assert not signal['active_growth_pass'] and not signal['marginal_bytes_pass']


def test_pilot_runs_real_training_and_exact_reload_without_using_case_ids(tmp_path):
    config=manifest();config.update(event_checkpoints=[12,24,36],cases_per_partition=6)
    result=worker(config,13,tmp_path/'progress.json')
    assert [row['events'] for row in result['rows']]==[12,24,36]
    assert all(row['reload_mismatches']==0 for row in result['rows'])
    assert set(result['case_ids']['development']).isdisjoint(result['case_ids']['final'])
    assert json.loads((tmp_path/'progress.json').read_text())==result


def test_nonincreasing_growth_checkpoints_rejected():
    config=manifest();config['event_checkpoints']=[12,12,24]
    with pytest.raises(ValueError):validate_manifest(config)
