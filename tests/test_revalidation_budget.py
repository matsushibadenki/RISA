import json
from pathlib import Path

import pytest

from experiments.g3_role_online_ablation import run_online_ablation


def configuration(cap):
    manifest = json.loads(Path('experiments/g3_role_online_ablation_manifest.json').read_text())
    return {**manifest, 'seeds': [11], 'label_cap': cap,
            'reactivate_validated_orphaned_ancestors': True,
            'revalidation_after_A2_events': [4, 8, 12]}


def test_revalidation_has_fresh_labels_and_measures_pre_update_lifetime():
    result = run_online_ablation(configuration(4800))
    row = next(row for row in result['rows'] if row['arm'] == 'full')
    outcome = row['outcome']
    assert row['labels_consumed'] <= row['labels_available'] == 4800
    labels = outcome['B']['validation_label_ids'] + outcome['A2']['validation_label_ids']
    assert len(labels) == len(set(labels)) == row['labels_consumed']
    assert all('online:' in label for label in outcome['B']['validation_label_ids'])
    assert all('A2:' in label for label in outcome['A2']['validation_label_ids'])
    assert [t['observed_events_before_update'] for t in row['A2_nuisance_pre_update_trace']] == list(range(12))
    assert len(outcome['A2']['pre_update_diagnostic_trace']) == 12
    assert row['A2_nuisance_probe_exposures'] == 288
    assert row['A2_nuisance_correct_probe_exposures'] == sum(t['A_correct'] for t in row['A2_nuisance_pre_update_trace'])
    # Final-boundary labels can improve exit accuracy but cannot contribute
    # to pre-update predictions earlier in the phase.
    last = row['revalidation_budget_trace'][-1]
    assert last['A2_observed_events'] == 12 and last['A_correct_after'] == 16
    assert row['A2_nuisance_pre_update_trace'][-1]['A_correct'] <= 16
    for baseline in result['baselines']:
        assert baseline['A2_nuisance_correct_probe_exposures'] == 288
        assert baseline['labels_consumed'] == 0


def test_exhausted_budget_blocks_revalidation_and_schedule_is_validated():
    result = run_online_ablation(configuration(1200))
    row = next(row for row in result['rows'] if row['arm'] == 'full')
    assert row['labels_consumed'] == 1200
    assert row['outcome']['A2']['validation_label_ids'] == []
    assert all(t['status'] == 'budget_reservation_exhausted' and t['labels_consumed'] == 0
               for t in row['revalidation_budget_trace'])
    for schedule in ([4, 4], [0], [13], [True]):
        with pytest.raises(ValueError, match='schedule'):
            run_online_ablation({**configuration(1200), 'revalidation_after_A2_events': schedule})
