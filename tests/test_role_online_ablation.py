"""Online lifecycle budget, genuine mutation and invalidation contracts."""
import copy
import json
from pathlib import Path

import pytest

from experiments.g3_relational_return_cue import relational_world
from experiments.g3_role_online_ablation import online_warm_adoption, run_online_ablation
from risa.core.state import RisaState
from risa.engine.runtime import train_events, TrainingOptions


def test_label_reservation_precedes_mutation():
    a, b, _, ap, _ = relational_world(11, 12, 6)
    state = train_events(RisaState(target_role_readout_hops=2,
        context_conditioned_role_refinement=True), a + b,
        TrainingOptions(enable_metabolism=False, enable_replay=False))
    before = copy.deepcopy(state.to_dict())
    with pytest.raises(ValueError, match='insufficient online label cap'):
        online_warm_adoption(state, 11, ap[0].query, count=200, remaining=1199, dormancy=True)
    assert state.to_dict() == before


def test_online_ablation_exposes_transient_adoption_and_strong_baselines():
    manifest = json.loads(Path('experiments/g3_role_online_ablation_manifest.json').read_text())
    manifest['seeds'] = [11]
    result = run_online_ablation(manifest)
    rows = {row['arm']: row for row in result['rows']}
    assert {row['labels_available'] for row in rows.values()} == {1200}
    assert rows['full']['labels_consumed'] == rows['no_dormancy']['labels_consumed'] == 1200
    assert rows['no_merge']['labels_consumed'] == 800
    assert rows['none']['labels_consumed'] == 0
    for arm in ('full', 'no_merge', 'no_dormancy'):
        checkpoints = {c['boundary']: c for c in rows[arm]['checkpoints']}
        assert checkpoints['B-before-validation']['nuisance_A_correct'] == 0
        assert checkpoints['B-after-validation']['nuisance_A_correct'] == 16
        assert checkpoints['A2-first-update']['nuisance_A_correct'] == (0 if arm == 'full' else 8)
        assert rows[arm]['outcome']['validation_labels_total'] == rows[arm]['labels_consumed']
        assert len(rows[arm]['outcome']['B']['validation_label_ids']) == rows[arm]['labels_consumed']
    full = rows['full']['checkpoints'][2]
    no_dormancy = rows['no_dormancy']['checkpoints'][2]
    assert full['adopted_merges'] == 1 and full['dormant_candidates'] == 2
    assert full['remove_merge_prediction_changes'] == 16
    assert no_dormancy['dormant_candidates'] == 0
    assert no_dormancy['remove_merge_prediction_changes'] == 0
    for baseline in result['baselines']:
        assert baseline['labels_consumed'] == 0
        assert baseline['checkpoints'][-1]['nuisance_A_correct'] == 24
        assert baseline['checkpoints'][-1]['nuisance_B_correct'] == 24
