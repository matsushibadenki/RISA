import copy
import json
from pathlib import Path

from experiments.g3_relational_return_cue import relational_world
from experiments.g3_role_online_ablation import online_warm_adoption
from experiments.g3_orphaned_dormancy import run_orphaned_dormancy
from risa.core.state import RisaState
from risa.engine.runtime import TrainingOptions, train_events
from risa.engine.candidate_discovery import _reactivate_validated_orphaned_ancestors


def adopted_fixture():
    a, b, a2, ap, _ = relational_world(11, 12, 6)
    state = train_events(RisaState(target_role_readout_hops=2,
        context_conditioned_role_refinement=True), a + b,
        TrainingOptions(enable_metabolism=False, enable_replay=False))
    online_warm_adoption(state, 11, ap[0].query, count=200, remaining=1200, dormancy=True)
    merge = next(c for c in state.unnamed_concept_candidates.values()
                 if c.derivation_type == 'merged' and c.lifecycle_status == 'adopted')
    return state, merge, a2


def test_active_replacement_blocks_wakeup_but_expired_one_releases_valid_parent():
    state, merge, _ = adopted_fixture()
    previous = copy.deepcopy(state.unnamed_concept_candidates)
    assert _reactivate_validated_orphaned_ancestors(state, previous) == []
    assert all(state.unnamed_concept_candidates[p].dormant for p in merge.parent_candidate_ids)
    merge.lifecycle_status = 'rejected'
    changed = _reactivate_validated_orphaned_ancestors(state, previous)
    assert set(changed) == set(merge.parent_candidate_ids)
    assert all(state.unnamed_concept_candidates[p].lifecycle_status == 'adopted' for p in changed)
    assert _reactivate_validated_orphaned_ancestors(state, previous) == []


def test_changed_or_unvalidated_parent_and_unrelated_manual_dormancy_remain_asleep():
    state, merge, _ = adopted_fixture()
    previous = copy.deepcopy(state.unnamed_concept_candidates)
    merge.lifecycle_status = 'rejected'
    first, second = [state.unnamed_concept_candidates[p] for p in merge.parent_candidate_ids]
    first.counterexample_event_ids.append('new-counterexample')
    second.final_evaluation_event_ids = []
    assert _reactivate_validated_orphaned_ancestors(state, previous) == []
    state, merge, _ = adopted_fixture()
    # No validated replacement in the previous snapshot: dormancy is not ours
    # to undo, even though the parent itself has validation.
    previous = copy.deepcopy(state.unnamed_concept_candidates)
    previous[merge.id].lifecycle_status = 'proposed'
    merge.lifecycle_status = 'rejected'
    assert _reactivate_validated_orphaned_ancestors(state, previous) == []


def test_changed_parent_semantics_blocks_wakeup():
    state, merge, _ = adopted_fixture()
    previous = copy.deepcopy(state.unnamed_concept_candidates)
    merge.lifecycle_status = 'rejected'
    for item in merge.parent_candidate_ids:
        parent = state.unnamed_concept_candidates[item]
        for root in parent.parent_candidate_ids:
            state.unnamed_concept_candidates[root].structural_schema['target_role'] = 'changed-role'
    assert _reactivate_validated_orphaned_ancestors(state, previous) == []


def test_out_of_scope_root_evidence_changes_do_not_expire_unchanged_scoped_validation():
    state, merge, a2 = adopted_fixture()
    previous = copy.deepcopy(state.unnamed_concept_candidates)
    train_events(state, a2[:1], TrainingOptions(enable_metabolism=False, enable_replay=False))
    changed = _reactivate_validated_orphaned_ancestors(state, previous)
    assert len(changed) == 1
    parent, old = state.unnamed_concept_candidates[changed[0]], previous[changed[0]]
    assert parent.supporting_event_ids == old.supporting_event_ids
    assert parent.counterexample_event_ids == old.counterexample_event_ids
    assert parent.parent_evidence_digests != old.parent_evidence_digests
    assert parent.final_evaluation_event_ids == old.final_evaluation_event_ids


def test_independent_active_replacement_still_blocks_ancestor():
    state, merge, _ = adopted_fixture()
    replacement = copy.deepcopy(merge)
    replacement.id = 'independent-valid-replacement'
    state.unnamed_concept_candidates[replacement.id] = replacement
    previous = copy.deepcopy(state.unnamed_concept_candidates)
    merge.lifecycle_status = 'rejected'
    assert _reactivate_validated_orphaned_ancestors(state, previous) == []


def test_paired_online_reactivation_preserves_budget_and_validation():
    manifest = json.loads(Path('experiments/g3_orphaned_dormancy_manifest.json').read_text())
    manifest['seeds'] = [11]
    result = run_orphaned_dormancy(manifest)
    comparisons = {row['arm']: row for row in result['comparisons']}
    assert comparisons['full']['checkpoint_A_correct_delta']['A2-first-update'] == 8
    assert comparisons['full']['checkpoint_A_correct_delta']['A2'] == 0
    assert all(c['labels_consumed_equal'] and c['adoption_decisions_equal']
               and c['B_recovery_equal'] and c['A2_recovery_equal'] for c in comparisons.values())
    assert all(all(delta == 0 for delta in c['checkpoint_A_correct_delta'].values())
               for arm, c in comparisons.items() if arm != 'full')
