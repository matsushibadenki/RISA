"""Paired complete-result and build/query-cost audit for Primitive grounding."""
import json
from pathlib import Path
from time import perf_counter

from experiments.independent_joint_quality import training_episode, heldout_cases
from risa.core.state import RisaState
from risa.engine.runtime import TrainingOptions, train_events
from risa.engine.composer import compose_to_effect
from risa.engine.primitive_grounding import build_primitive_grounding


def run_index_audit(manifest):
    rows = []
    for seed in manifest['seeds']:
        state, previous = RisaState(), 0
        cases = heldout_cases(seed, manifest['heldout_partition'], manifest['cases_per_seed'])
        for episodes in manifest['training_episode_checkpoints']:
            train_events(state, [e for i in range(previous, episodes) for e in training_episode(seed, i)],
                         TrainingOptions(enable_metabolism=False, enable_replay=False))
            index = build_primitive_grounding(state)
            before = state.to_dict()
            restored = RisaState.from_dict(json.loads(json.dumps(before)))
            build_primitive_grounding(restored)
            work = {name: {} for name in ('full_scan', 'indexed')}
            elapsed = {name: 0.0 for name in work}
            mismatches = correct = false_accepts = 0
            for case in cases:
                kwargs = dict(actor=case['actor'], target=case['target'], actor_roles=case['actor_roles'],
                    target_roles=case['target_roles'], start_states=case['states'], start_variables={'energy': case['energy']}, max_steps=2)
                for enabled in (False, True):
                    outputs = []
                    for name, indexed in [('full_scan', False), ('indexed', True)]:
                        diagnostics = {}
                        start = perf_counter()
                        result = compose_to_effect(state, 'prime', 'done', **kwargs,
                            enable_candidate_concepts=enabled, use_grounding_index=indexed, search_diagnostics=diagnostics)
                        elapsed[name] += perf_counter() - start
                        for key, value in diagnostics.items():
                            work[name][key] = work[name].get(key, 0) + value
                        outputs.append(result)
                    mismatches += outputs[0] != outputs[1]
                    mismatches += outputs[1] != compose_to_effect(restored, 'prime', 'done', **kwargs,
                                              enable_candidate_concepts=enabled, use_grounding_index=True)
                    correct += bool(outputs[1].primitive_ids) == case['expected']
                    false_accepts += bool(outputs[1].primitive_ids) and not case['expected']
            if mismatches or before != state.to_dict():
                raise AssertionError('grounding index changed learned state or complete result')
            rows.append(dict(seed=seed, events=2 * episodes, queries=2 * len(cases), correct=correct,
                false_accepts=false_accepts, complete_result_mismatches=mismatches, work=work, query_seconds=elapsed,
                index_build_event_reads=index['build_event_reads'], index_signatures=index['signature_count'],
                index_payload_bytes=index['payload_bytes'], index_build_seconds=index['build_seconds']))
            previous = episodes
    return dict(status='development_lossless_grounding_index', manifest=manifest, rows=rows)


if __name__ == '__main__':
    manifest = json.loads(Path('experiments/g3_grounding_index_manifest.json').read_text())
    result = run_index_audit(manifest)
    Path('docs/g3-grounding-index-results-2026-10-10.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'rows': len(result['rows']), 'last': result['rows'][-1]}))
