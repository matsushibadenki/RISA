import json
from pathlib import Path

from experiments.independent_joint_quality import run_quality, GroundedContractTable, training_episode, heldout_cases


def test_new_quality_fixture_preserves_binding_counterexamples_and_reload():
    manifest = json.loads(Path('experiments/g3_independent_quality_manifest.json').read_text())
    manifest.update(seeds=[101], training_episode_checkpoints=[4, 8], cases_per_seed=20)
    result = run_quality(manifest)
    assert len(result['rows']) == 2
    assert all(not a['identity_overlap'] and not a['event_case_id_overlap'] for a in result['overlap_audits'])
    for row in result['rows']:
        assert row['positive_cases'] == 4
        assert all(m['correct'] == 20 and m['false_accepts'] == 0 and m['positive_correct'] == 4
                   for m in row['metrics'].values())
        assert row['reload_mismatches'] == 0
        assert not row['candidate_advantage_pass']
        assert row['table_contracts'] == 4
        assert row['candidates'] == 6
        assert row['adopted_candidates'] == 0
        assert row['table_expanded_nodes'] > 0


def test_table_learns_only_observed_binding_contracts():
    # Learn only distinct/operator episodes. The valid self-world case must
    # fail until training supplies that family; the table has no oracle labels.
    table = GroundedContractTable([e for i in (0, 2) for e in training_episode(101, i)])
    cases = heldout_cases(101, 'independent-test', 10)
    assert table.solve(cases[0], 2)[0]
    assert not table.solve(cases[1], 2)[0]
    assert not table.solve(cases[0], 1)[0]
