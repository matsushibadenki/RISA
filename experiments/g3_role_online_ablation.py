"""Budget-capped online role-backed lifecycle development control."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from experiments.g3_context_conditioned_discovery import role_panel
from experiments.g3_drift_preflight import ARMS
from experiments.g3_relational_return_cue import relational_world, project_role
from risa.core.state import RisaState
from risa.engine.runtime import TrainingOptions, train_events
from risa.engine.predictor import predict_next_effect
from risa.engine.candidate_discovery import select_derived_candidates_for_final
from risa.evaluation.candidate_adoption import evaluate_candidate_on_probes
from risa.evaluation.drift_runner import ValidationStepResult, run_aba
from risa.evaluation.drift_metrics import snapshot_mechanisms
from risa.evaluation.grounded_role_baseline import (
    GroundedRoleSubsetTransitionBaseline, GroundedRoleSubsetCountBaseline,
)


def online_warm_adoption(state, seed, query, *, count, remaining, dormancy, cycle="online", skip_adopted=False):
    """Fixed A-warm contracts; absent proposals consume no labels.

    Validate indoor, sheltered, then their union. Contracts are defined by the
    fixture, not copied from the selected candidate's predictions. Each has
    independent development/final episodes and sources.
    """
    contracts = [('indoor', ('indoor',)), ('sheltered', ('sheltered',)),
                 ('warm-union', ('indoor', 'sheltered'))]
    selected = []
    for name, contexts in contracts:
        kind = 'merged' if name == 'warm-union' else 'specialized'
        candidates = [c for c in state.unnamed_concept_candidates.values()
                      if c.derivation_type == kind and c.structural_schema['effects'] == ['warm']]
        if kind == 'specialized':
            candidates = [c for c in candidates
                          if c.structural_schema.get('required_context_tags') == list(contexts)]
        if len(candidates) > 1:
            raise ValueError('ambiguous fixture candidate contract')
        if candidates and not (skip_adopted and candidates[0].lifecycle_status == 'adopted'):
            selected.append((name, contexts, candidates[0].id))
    # Reserve the complete dev/final allocation before mutating any candidate.
    if remaining is None or remaining < 2 * count * len(selected):
        raise ValueError('insufficient online label cap')
    labels, decisions = [], []
    for name, contexts, candidate_id in selected:
        panels = {}
        for partition in ('development', 'final'):
            panel = role_panel(seed, f'{cycle}:{name}:{partition}', count, query)
            panels[partition] = [replace(p, expected_applicable=(
                p.expected_applicable and p.context_tags[0] in contexts)) for p in panel]
        development = evaluate_candidate_on_probes(state, candidate_id, panels['development'],
            partition='development', bootstrap_samples=200, seed=seed)
        labels.extend(p.id for p in panels['development'])
        decisions.append({'contract': name, 'partition': 'development', 'result': development})
        if development['status'] == 'provisional':
            select_derived_candidates_for_final(state, [candidate_id])
            final = evaluate_candidate_on_probes(state, candidate_id, panels['final'],
                partition='final', development_probes=panels['development'],
                bootstrap_samples=200, seed=seed + 1, enable_ancestor_dormancy=dormancy)
            labels.extend(p.id for p in panels['final'])
            decisions.append({'contract': name, 'partition': 'final', 'result': final})
    return ValidationStepResult(tuple(labels), len(decisions)), decisions


def baseline_lifetime_rows(seed, manifest, a1, b, a2, ap, bp, nuisance):
    baseline_rows = []
    for name, factory in [('latest_subset_2hop', GroundedRoleSubsetTransitionBaseline),
                          ('count_subset_2hop', GroundedRoleSubsetCountBaseline)]:
        model, checkpoints, baseline_lifetime = factory(), [], []
        for boundary, events in [('A1', a1), ('B', b), ('A2', a2)]:
            for index, event in enumerate(events):
                if boundary == 'A2':
                    baseline_lifetime.append({'observed_events_before_update': index,
                        'A_correct': sum(model.predict(project_role(p.query, 2)) == p.expected_effects
                                         for p in nuisance[:len(ap)]), 'probe_count': len(ap)})
                model.observe(project_role(event, 2))
            results = [model.predict(project_role(p.query, 2)) for p in nuisance]
            checkpoints.append({'boundary': boundary, 'nuisance_A_correct': sum(
                r == p.expected_effects for r, p in zip(results[:len(ap)], ap)),
                'nuisance_B_correct': sum(r == p.expected_effects for r, p in zip(results[len(ap):], bp)),
                'probes_per_regime': len(ap)})
        baseline_rows.append({'seed': seed, 'model': name, 'labels_available': manifest['label_cap'],
                              'labels_consumed': 0, 'checkpoints': checkpoints,
                              'A2_nuisance_pre_update_trace': baseline_lifetime,
                              'A2_nuisance_correct_probe_exposures': sum(t['A_correct'] for t in baseline_lifetime),
                              'A2_nuisance_probe_exposures': sum(t['probe_count'] for t in baseline_lifetime)})
    return baseline_rows


def run_online_ablation(manifest):
    if set(manifest['arms']) != set(ARMS):
        raise ValueError('all seven arms required')
    count = manifest['probes_per_partition']
    if count < 8 or count % 8 or manifest['label_cap'] < 6 * count:
        raise ValueError('cap must reserve three independent dev/final panels')
    schedule = manifest.get('revalidation_after_A2_events', [])
    if len(set(schedule)) != len(schedule) or any(type(i) is not int or i < 1 or i > manifest['phase_observations'] for i in schedule):
        raise ValueError('invalid revalidation schedule')
    rows, baseline_rows = [], []
    for seed in manifest['seeds']:
        a1, b, a2, ap, bp = relational_world(seed, manifest['phase_observations'], manifest['probes_per_phase'])
        nuisance = [replace(p, query=replace(p.query, context_tags=p.query.context_tags + [f'nuisance:{p.id}']))
                    for p in ap + bp]
        for arm in manifest['arms']:
            split, merge, dormancy = ARMS[arm]
            options = TrainingOptions(enable_metabolism=False, enable_context_split=split,
                enable_candidate_specialization=split, enable_candidate_merge=merge,
                replay_max_events=manifest['replay_max_events'],
                reactivate_validated_orphaned_ancestors=manifest.get('reactivate_validated_orphaned_ancestors', False))
            state = train_events(RisaState(target_role_readout_hops=2,
                context_conditioned_role_refinement=True), a1, replace(options, enable_replay=False))
            checkpoints, decisions, lifetime, budget_trace = [], [], [], []

            def checkpoint(boundary):
                results = [predict_next_effect(state, p.query) for p in nuisance]
                restored = RisaState.from_dict(json.loads(json.dumps(state.to_dict())))
                if any(predict_next_effect(restored, p.query) != r for p, r in zip(nuisance, results)):
                    raise AssertionError('online lifecycle reload prediction mismatch')
                mechanisms = snapshot_mechanisms(state)
                checkpoints.append({'boundary': boundary, 'nuisance_A_correct': sum(
                    tuple(r.predicted_effects) == p.expected_effects for r, p in zip(results[:len(ap)], ap)),
                    'nuisance_B_correct': sum(tuple(r.predicted_effects) == p.expected_effects
                                             for r, p in zip(results[len(ap):], bp)),
                    'probes_per_regime': len(ap), 'adopted_merges': len(mechanisms.adopted_merges),
                    'dormant_candidates': len(mechanisms.dormant_candidates),
                    'prediction_reload_equal': True})
                if boundary == 'B-after-validation':
                    from risa.engine.candidate_discovery import rebuild_candidate_inference_index
                    removed = copy.deepcopy(state)
                    for candidate in removed.unnamed_concept_candidates.values():
                        if candidate.derivation_type == 'merged':
                            candidate.lifecycle_status = 'rejected'
                    rebuild_candidate_inference_index(removed)
                    alternative = [predict_next_effect(removed, p.query) for p in nuisance]
                    checkpoints[-1]['remove_merge_prediction_changes'] = sum(
                        a.predicted_effects != b.predicted_effects for a, b in zip(results, alternative))

            checkpoint('A1')

            def nuisance_correct():
                return sum(tuple(predict_next_effect(state, p.query).predicted_effects) == p.expected_effects
                           for p in nuisance[:len(ap)])

            def before_update(model, index, event):
                if event.id.startswith('A2:'):
                    lifetime.append({'observed_events_before_update': index - 1,
                                     'A_correct': nuisance_correct(), 'probe_count': len(ap)})
                return {}

            def validation(model, index, event, remaining):
                if event.id.startswith('A2:') and index in schedule:
                    before = nuisance_correct()
                    if remaining < 6 * count:
                        result, history = ValidationStepResult(), []
                        status = 'budget_reservation_exhausted'
                    else:
                        result, history = online_warm_adoption(model, seed, ap[0].query,
                            count=count, remaining=remaining, dormancy=dormancy,
                            cycle=f'A2:{index}', skip_adopted=True)
                        status = 'evaluated'
                    decisions.extend(history)
                    budget_trace.append({'A2_observed_events': index, 'remaining_before': remaining,
                        'labels_consumed': len(result.label_ids), 'status': status,
                        'A_correct_before': before, 'A_correct_after': nuisance_correct()})
                    checkpoint(f'A2-revalidation:{index}')
                    if index == manifest['phase_observations']:
                        checkpoint('A2')
                    return result
                if event.id.startswith('A2:') and index == 1:
                    checkpoint('A2-first-update')
                if index != manifest['phase_observations']:
                    return ValidationStepResult()
                if event.id.startswith('B:'):
                    checkpoint('B-before-validation')
                    result, history = online_warm_adoption(model, seed, ap[0].query,
                        count=count, remaining=remaining, dormancy=dormancy)
                    decisions.extend(history)
                    checkpoint('B-after-validation')
                    return result
                checkpoint('A2')
                return ValidationStepResult()

            outcome = run_aba(state, b, a2, ap, bp, options,
                replay_interval=manifest['replay_interval'], recovery_window=manifest['recovery_window'],
                validation_step=validation, validation_label_budget=manifest['label_cap'],
                pre_update_diagnostic=before_update)
            rows.append({'seed': seed, 'arm': arm,
                         'reactivate_validated_orphaned_ancestors': options.reactivate_validated_orphaned_ancestors,
                         'labels_available': manifest['label_cap'],
                         'labels_consumed': outcome['validation_labels_total'],
                         'outcome': outcome, 'checkpoints': checkpoints, 'adoption_decisions': decisions,
                         'A2_nuisance_pre_update_trace': lifetime, 'revalidation_budget_trace': budget_trace,
                         'A2_nuisance_correct_probe_exposures': sum(t['A_correct'] for t in lifetime),
                         'A2_nuisance_probe_exposures': sum(t['probe_count'] for t in lifetime)})
        baseline_rows.extend(baseline_lifetime_rows(seed, manifest, a1, b, a2, ap, bp, nuisance))
    return {'benchmark_version': manifest['benchmark_version'],
            'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            'status': 'development_online_control_only', 'rows': rows, 'baselines': baseline_rows}


if __name__ == '__main__':
    manifest = json.loads(Path('experiments/g3_role_online_ablation_manifest.json').read_text())
    result = run_online_ablation(manifest)
    Path('docs/g3-role-online-ablation-results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'rows': len(result['rows']), 'baselines': len(result['baselines'])}))
