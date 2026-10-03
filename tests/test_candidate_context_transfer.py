from dataclasses import replace

from experiments.g3_candidate_context_transfer import run_context_transfer, subset_table_predict
from experiments.g3_drift_preflight import _events, _probes


def test_subset_control_uses_no_selected_context_labels_and_abstains_on_conflict():
    events = _events(11, 'A1', 6)
    probe = _probes(11, 'A', 3)[0]
    query = replace(probe.query, context_tags=probe.query.context_tags + ['unknown-tag'])
    assert subset_table_predict(events, query) == probe.expected_effects
    query = replace(query, context_tags=['indoor', 'outdoor', 'unknown-tag'])
    assert subset_table_predict(events, query) == ()
    assert subset_table_predict(list(reversed(events)), query) == ()


def test_transfer_control_detects_candidate_benefit_and_stronger_table():
    result = run_context_transfer({
        'benchmark_version': 'test', 'seeds': [11], 'probes_per_panel': 6,
        'adoption_probes_per_partition': 200, 'bootstrap_samples': 200,
    })
    rows = {row['panel']: row for row in result['rows']}
    exact = rows['exact_context']
    assert all(model['expected_behavior_rate'] == 1 for model in exact['models'].values())
    transfer = rows['unseen_nuisance']
    assert transfer['candidate_changed_predictions'] == 4
    assert transfer['models']['risa']['expected_behavior_rate'] == 2 / 3
    assert transfer['models']['subset_table']['expected_behavior_rate'] == 1
    assert transfer['models']['risa_conflict_guard']['expected_behavior_rate'] == 2 / 3
    assert transfer['conflict_guard_audit']['conflict_queries'] == 0
    assert transfer['lifecycle_readout']['variants']['without_adopted_merges']['accuracy'] == 0
    conflict = rows['conflicting_context']
    assert conflict['models']['risa']['abstention_count'] == 0
    assert conflict['models']['subset_table']['abstention_count'] == 6
    assert conflict['models']['risa_no_candidate']['abstention_count'] == 6
    assert conflict['models']['risa_conflict_guard']['abstention_count'] == 6
    assert conflict['conflict_guard_audit'] == {
        'conflict_queries': 6, 'event_reads': 36, 'extra_supervised_labels': 0,
        'indexed_event_reads': 0, 'indexed_scope_reads': 18,
        'indexed_semantics_equal': True,
    }
