from dataclasses import replace

from experiments.g3_drift_preflight import ARMS
from experiments.g3_relational_return_cue import (
    project_role, relational_world, run_relational_return,
)


def test_return_cue_is_in_topology_and_survives_identity_and_variable_renaming():
    a1, b, a2, ap, bp = relational_world(11, 6, 6)
    assert all(not item.target_roles for item in a1 + b + a2)
    assert all(a.query.context_tags == b.query.context_tags for a, b in zip(ap, bp))
    assert project_role(ap[0].query, 1).target_roles == project_role(bp[0].query, 1).target_roles
    assert project_role(ap[0].query, 2).target_roles != project_role(bp[0].query, 2).target_roles
    query = ap[0].query
    names = {name: f'new-variable:{i}' for i, name in enumerate(query.entity_bindings)}
    identities = {value: f'new-identity:{i}' for i, value in enumerate(query.entity_bindings.values())}
    renamed = replace(query, target=identities[query.target],
        entity_bindings={names[name]: identities[value] for name, value in query.entity_bindings.items()},
        entity_relations=[{'source': names[row['source']], 'relation': row['relation'],
                           'target': names[row['target']]} for row in query.entity_relations])
    assert project_role(query, 2).target_roles == project_role(renamed, 2).target_roles
    assert {p.id for p in ap + bp}.isdisjoint({e.id for e in a1 + b + a2})


def test_relational_cue_resolves_identifiability_but_default_risa_loses_return():
    result = run_relational_return({
        'benchmark_version': 'test', 'seeds': [11], 'phase_observations': 12,
        'probes_per_phase': 6, 'replay_interval': 4, 'replay_max_events': 8,
        'recovery_window': 3, 'arms': list(ARMS),
    })
    audit = result['cue_audits'][0]
    assert audit['with_cue']['identical_query_conflicting_a_probes'] == 0
    assert audit['without_cue']['identical_query_conflicting_a_probes'] == 6
    full = next(row['outcome'] for row in result['rows'] if row['arm'] == 'full')
    assert full['a1_accuracy'] == full['B']['exit_accuracy'] == full['A2']['exit_accuracy'] == 1
    assert full['retention_after_return'] == 0
    projected = result['projection_controls'][0]['outcome']
    assert projected['B']['exit_accuracy'] == projected['retention_after_return'] == 1
    assert projected['A2']['recovery_events'] == 0
    native = result['native_readout_controls'][0]
    assert native['outcome']['B']['exit_accuracy'] == native['outcome']['retention_after_return'] == 1
    assert native['outcome']['A2']['recovery_events'] == 0
    assert len(native['readout_equivalence_checkpoints']) == 3
    assert all(row['prediction_results_equal'] for row in native['readout_equivalence_checkpoints'])
    baselines = {row['model']: row['outcome'] for row in result['baselines']}
    assert baselines['1hop_latest']['retention_after_return'] == 0
    assert baselines['2hop_latest']['retention_after_return'] == 1
    assert baselines['2hop_count']['retention_after_return'] == 1
    assert all(row['supervised_adoption_labels'] == 0 for row in result['rows'] + result['baselines'] + result['projection_controls'])
    assert result['mechanism_opportunity_gate'] == 'fail'
