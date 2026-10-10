"""Exact G3.4 compositional parity and paired grounding-index cost measurements."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter
import tracemalloc

from experiments.compositional_holdout import audit_split, heldout_cases, training_episode
from risa.core.state import RisaState
from risa.engine.composer import compose_to_effect
from risa.engine.persistence import load_state, save_state
from risa.engine.primitive_grounding import build_primitive_grounding
from risa.engine.runtime import TrainingOptions, train_events


def _timed(function):
    started = perf_counter()
    result = function()
    return result, perf_counter() - started


def _query(state, case, candidate, indexed, work=None):
    return compose_to_effect(state, case['start_action'], case['goal'], actor=case['actor'],
        target=case['target'], actor_roles=case['actor_roles'], target_roles=case['target_roles'],
        start_states=case['states'], start_variables={'energy': case['energy']}, max_steps=3,
        enable_candidate_concepts=candidate, use_grounding_index=indexed, search_diagnostics=work)


def _panel(state, cases, indexed):
    return [_query(state, case, enabled, indexed) for case in cases for enabled in (False, True)]


def _digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def run_cost_audit(manifest):
    fixture = json.loads(Path(manifest['fixture_manifest']).read_text())
    if manifest['repetitions'] < 2:
        raise ValueError('at least two paired timing repetitions required')
    rows = []
    options = TrainingOptions(enable_metabolism=False, enable_replay=False)
    for seed in fixture['seeds']:
        for world in fixture['worlds']:
            events, previous, previous_snapshot = [], 0, RisaState().to_dict()
            cases = heldout_cases(seed, world)
            for episodes in fixture['training_episode_checkpoints']:
                added = [e for i in range(previous, episodes) for e in training_episode(seed, world, i)]
                events.extend(added)
                split = audit_split(events, cases)
                timings = {key: [] for key in ('train_reference_seconds', 'train_indexed_seconds',
                    'rebuild_after_update_seconds', 'query_reference_seconds', 'query_indexed_seconds',
                    'save_reference_seconds', 'save_indexed_seconds', 'load_seconds', 'load_rebuild_seconds')}
                expected = None
                persisted_bytes = []
                for repeat in range(manifest['repetitions']):
                    reference = RisaState.from_dict(json.loads(json.dumps(previous_snapshot)))
                    indexed = RisaState.from_dict(json.loads(json.dumps(previous_snapshot)))
                    build_primitive_grounding(indexed)
                    # Alternate order to reduce fixed warmup/order bias. Preloading
                    # previous state/index is outside the append-training interval.
                    order = [('reference', reference), ('indexed', indexed)]
                    if repeat % 2:
                        order.reverse()
                    for name, state in order:
                        _, seconds = _timed(lambda: train_events(state, added, options))
                        timings[f'train_{name}_seconds'].append(seconds)
                    if getattr(indexed, '_primitive_grounding_index', None) is not None:
                        raise AssertionError('append must invalidate stale grounding summaries')
                    if reference.to_dict() != indexed.to_dict():
                        raise AssertionError('index maintenance changed learning')
                    index, seconds = _timed(lambda: build_primitive_grounding(indexed))
                    timings['rebuild_after_update_seconds'].append(seconds)
                    snapshot = indexed.to_dict()
                    if expected is not None and snapshot != expected:
                        raise AssertionError('repeated training is not deterministic')
                    expected = snapshot
                    panels = {}
                    for name, state in order:
                        panels[name], seconds = _timed(lambda: _panel(state, cases, name == 'indexed'))
                        timings[f'query_{name}_seconds'].append(seconds)
                    if panels['reference'] != panels['indexed']:
                        raise AssertionError('complete G3.4 results differ')
                    with TemporaryDirectory(prefix='risa-grounding-cost-') as directory:
                        root = Path(directory)
                        for name, state in order:
                            _, seconds = _timed(lambda: save_state(state, root / name))
                            timings[f'save_{name}_seconds'].append(seconds)
                        reference_bytes = (root / 'reference/state.json').read_bytes()
                        indexed_bytes = (root / 'indexed/state.json').read_bytes()
                        if reference_bytes != indexed_bytes:
                            raise AssertionError('derived index changed persistence bytes')
                        persisted_bytes.append(len(indexed_bytes))
                        restored, seconds = _timed(lambda: load_state(root / 'indexed'))
                        timings['load_seconds'].append(seconds)
                        if getattr(restored, '_primitive_grounding_index', None) is not None:
                            raise AssertionError('index unexpectedly persisted')
                        _, seconds = _timed(lambda: build_primitive_grounding(restored))
                        timings['load_rebuild_seconds'].append(seconds)
                        if _panel(restored, cases, True) != panels['reference']:
                            raise AssertionError('reloaded complete G3.4 results differ')
                    if snapshot != indexed.to_dict() or snapshot != restored.to_dict():
                        raise AssertionError('scoring changed learned state')

                # Cold query accounts for build work, distinct from warm queries.
                cold = RisaState.from_dict(json.loads(json.dumps(snapshot)))
                cold_work, work = {}, {'reference': {}, 'indexed': {}}
                matches = correct = false_accepts = 0
                for case in cases:
                    for enabled in (False, True):
                        cold_diagnostic = {}
                        full = _query(reference, case, enabled, False)
                        if _query(cold, case, enabled, True, cold_diagnostic) != full:
                            raise AssertionError('lazy rebuild changed complete result')
                        for key, value in cold_diagnostic.items():
                            cold_work[key] = cold_work.get(key, 0) + value
                        for name, state, use_index in (('reference', reference, False), ('indexed', indexed, True)):
                            diagnostic = {}
                            output = _query(state, case, enabled, use_index, diagnostic)
                            if output != full:
                                raise AssertionError('instrumentation changed complete result')
                            for key, value in diagnostic.items():
                                work[name][key] = work[name].get(key, 0) + value
                        matches += 1
                        correct += bool(full.primitive_ids) == case['expected']
                        false_accepts += bool(full.primitive_ids) and not case['expected']
                # Separately trace allocations of rebuilding the index; timings
                # above run without tracemalloc. Borrowed source objects preexist.
                memory_state = RisaState.from_dict(json.loads(json.dumps(snapshot)))
                gc.collect()
                tracemalloc.start()
                build_primitive_grounding(memory_state)
                retained, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                medians = {key: median(values) for key, values in timings.items()}
                rows.append(dict(seed=seed, world=world, events=len(events), appended_events=len(added),
                    cases=len(cases), queries=matches, correct=correct, false_accepts=false_accepts,
                    split_audit=split, complete_result_mismatches=0, reload_mismatches=0,
                    lazy_rebuild_mismatches=0, state_digest=_digest(snapshot),
                    work=work, cold_work=cold_work, index_build_event_reads=index['build_event_reads'],
                    index_signatures=index['signature_count'], index_logical_bytes=index['payload_bytes'],
                    index_traced_retained_bytes=retained, index_traced_peak_bytes=peak,
                    persisted_file_bytes=persisted_bytes, persisted_extra_bytes=0,
                    timing_samples=timings, timing_medians=medians,
                    indexed_update_total_seconds=[a + b for a, b in zip(timings['train_indexed_seconds'],
                                                                       timings['rebuild_after_update_seconds'])]))
                previous, previous_snapshot = episodes, snapshot
    source_paths = [Path(__file__), Path('risa/engine/primitive_grounding.py'),
                    Path('risa/engine/composer.py'), Path('risa/engine/learner.py'),
                    Path('risa/engine/graph_builder.py'), Path('experiments/compositional_holdout.py')]
    return dict(status='development_compositional_grounding_cost_audit', manifest=manifest,
        paired_order_balanced=manifest['repetitions'] % 2 == 0,
        fixture_manifest=fixture, fixture_sha256=_digest(fixture),
        source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}, rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default='experiments/g3_compositional_grounding_cost_manifest.json')
    parser.add_argument('--output', default='docs/g3-compositional-grounding-cost-results-2026-10-10.json')
    args = parser.parse_args()
    result = run_cost_audit(json.loads(Path(args.manifest).read_text()))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'rows': len(result['rows']), 'correct': sum(r['correct'] for r in result['rows']),
                      'warm_event_reads': sum(r['work']['indexed']['grounding_event_reads'] for r in result['rows'])}))
