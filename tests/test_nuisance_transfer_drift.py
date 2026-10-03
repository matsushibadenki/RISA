from dataclasses import replace

from experiments.g3_drift_candidate_primed import nuisance_transfer_probe_panels
from experiments.g3_drift_preflight import ARMS, _events
from experiments.g3_nuisance_transfer_drift import run_transfer_drift
from risa.evaluation.grounded_role_baseline import (
    GroundedRoleSubsetTransitionBaseline, GroundedRoleSubsetCountBaseline,
)


def test_subset_models_adapt_without_selecting_relevant_tags():
    a, _ = nuisance_transfer_probe_panels(11, 3)
    query = replace(a[0].query, context_tags=['indoor', 'unseen'])
    events = _events(11, 'A1', 6)
    latest, counts = GroundedRoleSubsetTransitionBaseline(), GroundedRoleSubsetCountBaseline()
    for event in events:
        latest.observe(event)
        counts.observe(event)
    assert latest.predict(query) == counts.predict(query) == ('warm',)
    changed = replace(events[0], id='changed', observed_effects=['cold'])
    latest.observe(changed)
    counts.observe(changed)
    assert latest.predict(query) == ('cold',)
    assert counts.predict(query) == ('warm',)
    counts.observe(replace(changed, id='tie'))
    assert counts.predict(query) == ('cold',)
    for model in (latest, counts):
        assert model.predict(replace(query, context_tags=['indoor', 'outdoor', 'unknown'])) == ('cold',)
        # A more specific observed joint rule takes precedence.
        model.observe(replace(events[0], id='joint', context_tags=['indoor', 'outdoor'], observed_effects=['lit', 'warm']))
        assert model.predict(replace(query, context_tags=['indoor', 'outdoor', 'unknown'])) == ('lit', 'warm')


def test_drift_control_exposes_candidate_loss_and_return_unidentifiability():
    result = run_transfer_drift({
        'benchmark_version': 'test', 'seeds': [11], 'phase_observations': 12,
        'probes_per_phase': 6, 'adoption_probes_per_partition': 200,
        'bootstrap_samples': 200, 'extra_a2_observations': 0,
        'replay_interval': 4, 'replay_max_events': 8, 'recovery_window': 3,
        'nuisance_context_probes': True, 'arms': list(ARMS),
    })
    full = next(row for row in result['rows'] if row['arm'] == 'full')
    assert full['a1_accuracy'] == 2 / 3
    assert full['transfer_drift']['B']['exit_accuracy'] == 0
    assert full['transfer_drift']['A2']['exit_accuracy'] == 0
    assert full['B_recovery_events'] is None
    assert full['transfer_drift']['return_identifiability']['a_accuracy_ceiling_given_perfect_b'] == 0
    assert full['a1_supervised_adoption_labels'] == 1200
    assert full['online_validation_labels'] == 0
    assert full['B_mechanism_trace'][-1]['adopted_merges'] == 0
    baselines = {row['model']: row['outcome'] for row in result['baselines']}
    for name in ('latest_subset', 'count_subset'):
        assert baselines[name]['B']['exit_accuracy'] == 1
        assert baselines[name]['A2']['exit_accuracy'] == 1
    assert result['mechanism_opportunity_gate'] == 'fail'
