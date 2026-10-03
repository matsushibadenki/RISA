"""Paired development opportunity audit of context-conditioned role discovery."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from experiments.g3_relational_return_cue import relational_world, with_relational_cue
from risa.core.state import RisaState
from risa.engine.runtime import TrainingOptions, train_events
from risa.engine.predictor import predict_next_effect
from risa.evaluation.drift_runner import ValidationStepResult, run_aba
from risa.evaluation.candidate_adoption import ApplicabilityProbe, evaluate_candidate_on_probes
from risa.engine.candidate_discovery import select_derived_candidates_for_final


def role_panel(seed, name, count, query):
    if count < 8 or count % 8:
        raise ValueError("role panel size must be a positive multiple of eight")
    rows = []
    for i in range(count):
        regime = ("A", "B")[i % 2]
        context = ("indoor", "sheltered", "outdoor", "exposed")[(i // 2) % 4]
        query_case = with_relational_cue(replace(query, actor=f"{name}:actor:{seed}:{i}",
            target=f"{name}:target:{seed}:{i}", context_tags=[context]), regime)
        # Fixed oracle contract for the A-scope warm merge, independent of the
        # proposed candidate's chosen context alternatives.
        rows.append(ApplicabilityProbe(f"{name}:{seed}:{i}", f"{name}:episode:{seed}:{i}",
            f"{name}:source:{seed}:{i % 2}", (context,),
            regime == "A" and context in {"indoor", "sheltered"}, query_case))
    return rows


def post_b_adoption_diagnostic(model, seed, ap, bp, count):
    budget = 2 * count
    merges = [c for c in model.unnamed_concept_candidates.values()
              if c.derivation_type == "merged" and c.structural_schema["effects"] == ["warm"]]
    if not merges:
        return {'labels_available': budget, 'labels_consumed': 0, 'status': 'no_candidate'}
    if len(merges) != 1:
        raise ValueError("fixture requires exactly one A-scope warm merge")
    copy_state = copy.deepcopy(model)
    candidate = merges[0]
    development = role_panel(seed, "role-development", count, ap[0].query)
    final = role_panel(seed, "role-final", count, ap[0].query)
    dev = evaluate_candidate_on_probes(copy_state, candidate.id, development,
        partition="development", bootstrap_samples=200, seed=seed)
    consumed = count
    approved = None
    if dev['status'] == 'provisional':
        select_derived_candidates_for_final(copy_state, [candidate.id])
        approved = evaluate_candidate_on_probes(copy_state, candidate.id, final,
            partition="final", development_probes=development, bootstrap_samples=200, seed=seed + 1)
        consumed += count
    nuisance = [replace(p, query=replace(p.query, context_tags=p.query.context_tags + [f"nuisance:{p.id}"]))
                for p in ap + bp]
    before = [predict_next_effect(model, p.query) for p in nuisance]
    after = [predict_next_effect(copy_state, p.query) for p in nuisance]
    restored = RisaState.from_dict(json.loads(json.dumps(copy_state.to_dict())))
    if any(predict_next_effect(restored, p.query) != result for p, result in zip(nuisance, after)):
        raise AssertionError("query-backed adopted predictions differ after reload")
    return {'labels_available': budget, 'labels_consumed': consumed,
            'status': approved['status'] if approved else dev['status'],
            'development': dev, 'final': approved, 'nuisance_probe_count': len(nuisance),
            'nuisance_predictions_changed': sum(a.predicted_effects != b.predicted_effects for a, b in zip(before, after)),
            'nuisance_correct_before': sum(tuple(r.predicted_effects) == p.expected_effects for r, p in zip(before, nuisance)),
            'nuisance_correct_after': sum(tuple(r.predicted_effects) == p.expected_effects for r, p in zip(after, nuisance)),
            'adopted_prediction_reload_equal': True}


def run_discovery_control(manifest):
    rows = []
    for seed in manifest['seeds']:
        a1, b, a2, ap, bp = relational_world(seed, manifest['phase_observations'], manifest['probes_per_phase'])
        for conditioned in (False, True):
            state = train_events(RisaState(target_role_readout_hops=2,
                context_conditioned_role_refinement=conditioned), a1,
                TrainingOptions(enable_metabolism=False, enable_replay=False))
            checkpoints = []
            adoption_diagnostics = []

            def checkpoint(model, boundary):
                candidates = list(model.unnamed_concept_candidates.values())
                restored = RisaState.from_dict(json.loads(json.dumps(model.to_dict())))
                equal_candidates = ({k: c.to_dict() for k, c in model.unnamed_concept_candidates.items()} ==
                                    {k: c.to_dict() for k, c in restored.unnamed_concept_candidates.items()})
                equal_predictions = all(predict_next_effect(model, p.query) == predict_next_effect(restored, p.query)
                                        for p in ap + bp)
                if not equal_candidates or not equal_predictions:
                    raise AssertionError('discovery checkpoint differs after reload')
                if boundary == 'B':
                    adoption_diagnostics.append(post_b_adoption_diagnostic(
                        model, seed, ap, bp, manifest['post_B_probes_per_partition']))
                checkpoints.append({'boundary': boundary, 'candidate_count': len(candidates),
                    'base_candidates': sum(c.derivation_type == 'base' for c in candidates),
                    'specialized_candidates': sum(c.derivation_type == 'specialized' for c in candidates),
                    'merged_candidates': sum(c.derivation_type == 'merged' for c in candidates),
                    'adopted_candidates': sum(c.lifecycle_status == 'adopted' for c in candidates),
                    'role_depths': sorted({c.structural_schema.get('target_role_depth') for c in candidates}),
                    'base_counterexample_events': sum(len(c.counterexample_event_ids) for c in candidates if c.derivation_type == 'base'),
                    'stored_bytes': len(json.dumps(model.to_dict(), sort_keys=True).encode()),
                    'candidate_reload_equal': equal_candidates, 'prediction_reload_equal': equal_predictions,
                })

            checkpoint(state, 'A1')

            def observe_boundary(model, index, event, remaining):
                if index == manifest['phase_observations']:
                    checkpoint(model, 'B' if event.id.startswith('B:') else 'A2')
                return ValidationStepResult()

            outcome = run_aba(state, b, a2, ap, bp,
                TrainingOptions(enable_metabolism=False, replay_max_events=manifest['replay_max_events']),
                replay_interval=manifest['replay_interval'], recovery_window=manifest['recovery_window'],
                validation_step=observe_boundary, validation_label_budget=0)
            rows.append({'seed': seed, 'context_conditioned_role_refinement': conditioned,
                         'supervised_labels_available': 0, 'supervised_labels_consumed': 0,
                         'checkpoints': checkpoints, 'outcome': outcome,
                         'post_B_copy_adoption_diagnostic': adoption_diagnostics[0]})
    return {'benchmark_version': manifest['benchmark_version'],
            'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            'status': 'development_candidate_opportunity_only', 'rows': rows}


if __name__ == '__main__':
    manifest = json.loads(Path('experiments/g3_context_conditioned_discovery_manifest.json').read_text())
    result = run_discovery_control(manifest)
    Path('docs/g3-context-conditioned-discovery-results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'rows': len(result['rows']), 'status': result['status']}))
