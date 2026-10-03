"""Development A→B→A control with a role-free relational return cue."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

from experiments.g3_drift_preflight import ARMS, _events, _probes, mechanism_opportunity_audit
from risa.core.state import RisaState
from risa.engine.role_induction import induced_entity_role_hierarchy
from risa.engine.runtime import TrainingOptions, train_events
from risa.evaluation.drift_metrics import snapshot_mechanisms
from risa.evaluation.drift_runner import ValidationStepResult, probe_return_identifiability, run_aba
from risa.engine.predictor import predict_next_effect
from risa.engine.prediction_access import predict_next_effect_with_access
from risa.evaluation.grounded_role_baseline import (
    GroundedRoleTransitionBaseline, GroundedRoleCountBaseline, run_grounded_role_aba,
)


def with_relational_cue(item, regime):
    """Only the direction of a second-hop edge identifies the regime.

    IDs and binding-variable names are irrelevant to role signatures. No A/B
    tag, supplied role, effect label or precomputed signature enters the input.
    """
    suffix = hashlib.sha256(str(item.target).encode()).hexdigest()[:12]
    root, middle, end = (f'v:{suffix}:{i}' for i in range(3))
    bindings = {root: item.target, middle: f'platform:{suffix}', end: f'anchor:{suffix}'}
    second = {'source': middle, 'relation': 'coupled_to', 'target': end}
    if regime == 'B':
        second = {'source': end, 'relation': 'coupled_to', 'target': middle}
    return replace(item, target_roles=[], entity_bindings=bindings,
                   entity_relations=[{'source': root, 'relation': 'mounted_on', 'target': middle}, second])


def relational_world(seed, phase_count, probe_count):
    a1 = [with_relational_cue(event, 'A') for event in _events(seed, 'A1', 6)]
    b = [with_relational_cue(event, 'B') for event in _events(seed, 'B', phase_count)]
    a2 = [with_relational_cue(event, 'A') for event in _events(seed, 'A2', phase_count)]
    a_probes = [replace(probe, query=with_relational_cue(probe.query, 'A'))
                for probe in _probes(seed, 'A', probe_count)]
    b_probes = [replace(probe, id=f'B:{probe.id}', query=with_relational_cue(probe.query, 'B'),
                        expected_effects=('cold' if probe.expected_effects == ('warm',) else 'warm',))
                for probe in a_probes]
    return a1, b, a2, a_probes, b_probes


def project_role(item, hops):
    hierarchy = induced_entity_role_hierarchy(
        identity=item.target, entity_bindings=item.entity_bindings,
        entity_relations=item.entity_relations, max_hops=hops)
    return replace(item, target_roles=[hierarchy[-1][0]] if hierarchy else [])


def run_relational_return(manifest):
    if set(manifest['arms']) != set(ARMS):
        raise ValueError('all seven arms are required')
    if manifest['phase_observations'] <= 0 or manifest['probes_per_phase'] <= 0:
        raise ValueError('phase and probe counts must be positive')
    rows, baselines, cue_audits, projection_controls, native_controls = [], [], [], [], []
    for seed in manifest['seeds']:
        a1, b, a2, a_probes, b_probes = relational_world(
            seed, manifest['phase_observations'], manifest['probes_per_phase'])
        # Remove precisely the environment edge. All remaining query fields
        # must agree, so identity/variable naming cannot masquerade as a cue.
        no_cue_a = [replace(p, query=replace(p.query, entity_relations=p.query.entity_relations[:1]))
                    for p in a_probes]
        no_cue_b = [replace(p, query=replace(p.query, entity_relations=p.query.entity_relations[:1]))
                    for p in b_probes]
        cue_audits.append({'seed': seed,
            'with_cue': probe_return_identifiability(a_probes, b_probes),
            'without_cue': probe_return_identifiability(no_cue_a, no_cue_b),
            'one_hop_roles_equal': all(project_role(a.query, 1).target_roles ==
                                       project_role(b.query, 1).target_roles
                                       for a, b in zip(a_probes, b_probes)),
            'two_hop_roles_distinct': all(project_role(a.query, 2).target_roles !=
                                          project_role(b.query, 2).target_roles
                                          for a, b in zip(a_probes, b_probes)),
        })
        for arm in manifest['arms']:
            split, merge, dormancy = ARMS[arm]
            options = TrainingOptions(enable_metabolism=False,
                enable_context_split=split, enable_candidate_specialization=split,
                enable_candidate_merge=merge, replay_max_events=manifest['replay_max_events'])
            state = train_events(RisaState(), a1, replace(options, enable_replay=False))
            outcome = run_aba(state, b, a2, a_probes, b_probes, options,
                              replay_interval=manifest['replay_interval'],
                              recovery_window=manifest['recovery_window'])
            mechanisms = snapshot_mechanisms(state)
            rows.append({'seed': seed, 'arm': arm,
                'split_enabled': split, 'merge_enabled': merge, 'dormancy_enabled': dormancy,
                'supervised_adoption_labels': 0, 'outcome': outcome,
                'final_executed_context_splits': len(mechanisms.executed_context_splits),
                'final_adopted_merges': len(mechanisms.adopted_merges),
                'final_dormant_candidates': len(mechanisms.dormant_candidates),
            })
        # Isolate evidence routing using RISA's existing deterministic role
        # extractor. This preprocessing control supplies computed roles at the
        # model boundary; it is not a change to default role-free inference.
        projected_options = TrainingOptions(enable_metabolism=False,
                                             replay_max_events=manifest['replay_max_events'])
        projected_state = train_events(RisaState(), [project_role(e, 2) for e in a1],
                                       replace(projected_options, enable_replay=False))
        projected_outcome = run_aba(
            projected_state, [project_role(e, 2) for e in b], [project_role(e, 2) for e in a2],
            [replace(p, query=project_role(p.query, 2)) for p in a_probes],
            [replace(p, query=project_role(p.query, 2)) for p in b_probes], projected_options,
            replay_interval=manifest['replay_interval'], recovery_window=manifest['recovery_window'])
        projection_controls.append({'seed': seed, 'model': 'risa_shared_2hop_projection',
                                    'supervised_adoption_labels': 0, 'outcome': projected_outcome})
        native_state = train_events(RisaState(target_role_readout_hops=2), a1,
                                    replace(projected_options, enable_replay=False))
        checkpoints = []

        def check_readout(model, boundary):
            restored = RisaState.from_dict(json.loads(json.dumps(model.to_dict())))
            panel = a_probes + b_probes
            for probe in panel:
                expected = predict_next_effect(model, probe.query)
                if predict_next_effect(restored, probe.query) != expected:
                    raise AssertionError('reloaded role readout differs')
                if predict_next_effect_with_access(model, probe.query, 'full_scan')[0] != expected:
                    raise AssertionError('full-scan role readout differs')
            checkpoints.append({'boundary': boundary, 'query_count': len(panel),
                                'prediction_results_equal': True,
                                'persisted_role_readout_hops': restored.target_role_readout_hops})

        check_readout(native_state, 'A1')

        def checkpoint_validation(model, index, event, remaining):
            if index == manifest['phase_observations']:
                check_readout(model, 'B' if event.id.startswith('B:') else 'A2')
            return ValidationStepResult()

        native_outcome = run_aba(native_state, b, a2, a_probes, b_probes, projected_options,
            replay_interval=manifest['replay_interval'], recovery_window=manifest['recovery_window'],
            validation_step=checkpoint_validation, validation_label_budget=0)
        native_controls.append({'seed': seed, 'model': 'risa_native_2hop_readout',
                                'supervised_adoption_labels': 0, 'outcome': native_outcome,
                                'readout_equivalence_checkpoints': checkpoints})
        for hops in (1, 2):
            for name, model in (('latest', GroundedRoleTransitionBaseline), ('count', GroundedRoleCountBaseline)):
                ap = [replace(p, query=project_role(p.query, hops)) for p in a_probes]
                bp = [replace(p, query=project_role(p.query, hops)) for p in b_probes]
                outcome = run_grounded_role_aba(
                    [project_role(event, hops) for event in a1],
                    [project_role(event, hops) for event in b],
                    [project_role(event, hops) for event in a2], ap, bp,
                    [replace(p, id=f'transfer:{p.id}') for p in ap],
                    [replace(p, id=f'transfer:{p.id}') for p in bp],
                    recovery_window=manifest['recovery_window'], model_factory=model)
                baselines.append({'seed': seed, 'model': f'{hops}hop_{name}',
                                  'supervised_adoption_labels': 0, 'outcome': outcome})
    opportunity = mechanism_opportunity_audit(rows)
    return {'benchmark_version': manifest['benchmark_version'],
            'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            'status': 'development_cue_control_only', 'cue_audits': cue_audits,
            'projection_controls': projection_controls, 'native_readout_controls': native_controls,
            'mechanism_opportunity_gate': opportunity['status'],
            'mechanism_opportunity_audit': opportunity, 'rows': rows, 'baselines': baselines}


if __name__ == '__main__':
    manifest = json.loads(Path('experiments/g3_relational_return_cue_manifest.json').read_text())
    result = run_relational_return(manifest)
    Path('docs/g3-relational-return-cue-results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'risa_rows': len(result['rows']), 'baseline_rows': len(result['baselines']),
                      'opportunity_gate': result['mechanism_opportunity_gate']}))
