"""Development control: nuisance-context transfer versus subset table lookup."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from experiments.g3_drift_candidate_primed import _adopt_warm_candidates
from experiments.g3_drift_preflight import _events, _probes
from risa.core.state import RisaState
from risa.engine.runtime import TrainingOptions, train_events
from risa.engine.predictor import predict_next_effect
from risa.evaluation.grounded_role_baseline import (
    GroundedRoleCountBaseline, GroundedRoleTransitionBaseline,
)
from risa.evaluation.readout_attribution import attribute_candidate_lifecycle_readout
from risa.evaluation.context_conflict import (
    ContextConflictIndex, conflict_audit_semantics, predict_with_context_conflict_guard,
)


def subset_table_predict(events, query):
    """Match observed context subsets; abstain when most specific rows disagree.

    All tags are treated identically. No domain labels or handpicked relevant
    tags are supplied to the table.
    """
    matches = [event for event in events
               if event.action == query.action
               and set(event.target_roles) == set(query.target_roles)
               and set(event.context_tags).issubset(query.context_tags)]
    if not matches:
        return ()
    specificity = max(len(set(event.context_tags)) for event in matches)
    outcomes = {tuple(sorted(event.observed_effects)) for event in matches
                if len(set(event.context_tags)) == specificity}
    return next(iter(outcomes)) if len(outcomes) == 1 else ()


def run_context_transfer(manifest):
    count = int(manifest['probes_per_panel'])
    if count <= 0 or count % 3:
        raise ValueError('probes_per_panel must be a positive multiple of three')
    rows = []
    for seed in manifest['seeds']:
        events = _events(seed, 'A1', 6)
        state = train_events(RisaState(), events,
                             TrainingOptions(enable_replay=False, enable_metabolism=False))
        labels = _adopt_warm_candidates(
            state, seed, dormancy=True,
            count=int(manifest['adoption_probes_per_partition']),
            bootstrap_samples=int(manifest['bootstrap_samples']))
        latest, counts = GroundedRoleTransitionBaseline(), GroundedRoleCountBaseline()
        for event in events:
            latest.observe(event)
            counts.observe(event)
        before = state.to_dict()
        conflict_index = ContextConflictIndex.from_state(state)
        for panel in ('exact_context', 'unseen_nuisance', 'conflicting_context'):
            probes = _probes(seed, 'A', count)
            if panel != 'exact_context':
                probes = [replace(probe, id=f'{panel}:{probe.id}', query=replace(
                    probe.query, context_tags=probe.query.context_tags + (
                        [f'nuisance:{seed}:{index}'] if panel == 'unseen_nuisance'
                        else ['outdoor' if probe.expected_effects == ('warm',) else 'indoor']
                    )), expected_effects=(() if panel == 'conflicting_context'
                                           else probe.expected_effects))
                          for index, probe in enumerate(probes)]
            guarded = [predict_with_context_conflict_guard(state, p.query) for p in probes]
            indexed_audits = [conflict_index.audit(p.query) for p in probes]
            if any(conflict_audit_semantics(reference) != conflict_audit_semantics(indexed)
                   for (_, reference), indexed in zip(guarded, indexed_audits)):
                raise AssertionError('indexed context audit differs from reference')
            predictions = {
                'risa_conflict_guard': [tuple(sorted(result.predicted_effects)) for result, _ in guarded],
                'risa': [tuple(sorted(predict_next_effect(state, p.query).predicted_effects)) for p in probes],
                'risa_no_candidate': [tuple(sorted(predict_next_effect(
                    state, replace(p.query, enable_candidate_concepts=False)).predicted_effects)) for p in probes],
                'latest_table': [latest.predict(p.query) for p in probes],
                'count_table': [counts.predict(p.query) for p in probes],
                'subset_table': [subset_table_predict(events, p.query) for p in probes],
            }
            rows.append({
                'seed': seed, 'panel': panel, 'probe_count': count,
                'supervised_adoption_labels': labels,
                'expected_behavior': 'abstain_on_conflict' if panel == 'conflicting_context' else 'predict_effect',
                'models': {name: {
                    'expected_behavior_rate': sum(result == p.expected_effects for result, p in zip(results, probes)) / count,
                    'abstention_count': sum(not result for result in results),
                } for name, results in predictions.items()},
                'conflict_guard_audit': {
                    'conflict_queries': sum(audit['conflict'] for _, audit in guarded),
                    'event_reads': sum(audit['event_reads'] for _, audit in guarded),
                    'extra_supervised_labels': 0,
                    'indexed_event_reads': sum(audit['event_reads'] for audit in indexed_audits),
                    'indexed_scope_reads': sum(audit['scope_reads'] for audit in indexed_audits),
                    'indexed_semantics_equal': True,
                },
                'candidate_changed_predictions': sum(a != b for a, b in zip(predictions['risa'], predictions['risa_no_candidate'])),
                'lifecycle_readout': attribute_candidate_lifecycle_readout(state, probes),
            })
        if state.to_dict() != before:
            raise AssertionError('evaluation mutated learning state')
    return {'benchmark_version': manifest['benchmark_version'],
            'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            'status': 'development_control_only', 'rows': rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', default='experiments/g3_candidate_context_transfer_manifest.json')
    parser.add_argument('--output', default='docs/g3-candidate-context-transfer-results.json')
    args = parser.parse_args()
    result = run_context_transfer(json.loads(Path(args.manifest).read_text()))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'rows': len(result['rows']), 'status': result['status']}))


if __name__ == '__main__':
    main()
