"""Save-stage/GC attribution and interleaved grounding-index costs."""
import argparse
from collections import defaultdict
import gc
import hashlib
import json
from pathlib import Path
import platform
import random
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

from experiments.compositional_holdout import heldout_cases, training_episode
from experiments.compositional_grounding_costs import _query
from risa.core.state import RisaState
from risa.engine import persistence
from risa.engine.primitive_grounding import build_primitive_grounding
from risa.engine.runtime import TrainingOptions, train_events


def encoded(state):
    return json.dumps(state.to_dict(), sort_keys=True, separators=(',', ':')).encode()


def measured_save(state, destination, gc_mode):
    """Instrument real save_state, including validation and atomic fsync writes.

    GC interventions are experiment-only and restored even on failure.
    Callback time is included in measured wall time; phase intervals are inclusive.
    """
    phases, collections = defaultdict(float), []
    active, started_gc = ['residual'], []
    original_to = RisaState.to_dict
    original_from = RisaState.from_dict.__func__
    original_write = persistence._atomic_write

    def wrap(name, function):
        def measured(*args, **kwargs):
            active.append(name)
            start = perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                phases[name] += perf_counter() - start
                active.pop()
        return measured

    def callback(phase, info):
        if phase == 'start':
            started_gc.append((perf_counter(), active[-1], info['generation']))
        elif started_gc:
            start, stage, generation = started_gc.pop()
            collections.append(dict(stage=stage, generation=generation,
                seconds=perf_counter() - start, collected=info['collected'], uncollectable=info['uncollectable']))

    was_enabled = gc.isenabled()
    if gc_mode == 'collect_before':
        gc.collect()
    if gc_mode == 'disabled':
        gc.disable()
    counts_before = gc.get_count()
    with patch.object(RisaState, 'to_dict', wrap('export', original_to)), \
         patch.object(RisaState, 'from_dict', classmethod(wrap('validate', original_from))), \
         patch.object(persistence, '_atomic_write', wrap('atomic_write', original_write)):
        gc.callbacks.append(callback)
        try:
            start = perf_counter()
            persistence.save_state(state, destination)
            elapsed = perf_counter() - start
        finally:
            gc.callbacks.remove(callback)
            if was_enabled:
                gc.enable()
            else:
                gc.disable()
    phases['residual'] = elapsed - sum(phases.values())
    return dict(seconds=elapsed, phases=dict(phases), gc=collections,
                gc_seconds=sum(c['seconds'] for c in collections), gc_count_before=counts_before)


def save_audit(manifest, root):
    rows = []
    options = TrainingOptions(enable_metabolism=False, enable_replay=False)
    for seed in manifest['seeds']:
        for world in manifest['worlds']:
            base = train_events(RisaState(), [e for i in range(32) for e in training_episode(seed, world, i)], options)
            data = encoded(base)
            reference = RisaState.from_dict(json.loads(data))
            indexed = RisaState.from_dict(json.loads(data))
            build_primitive_grounding(indexed)
            for mode in manifest['gc_modes']:
                for storage in ('fresh', 'overwrite'):
                    # Exactly balanced first positions, shuffled reproducibly.
                    firsts = ['reference', 'indexed'] * (manifest['save_repetitions'] // 2)
                    random.Random(f'{seed}:{world}:{mode}:{storage}').shuffle(firsts)
                    for repeat, first in enumerate(firsts):
                        order = [first, 'indexed' if first == 'reference' else 'reference']
                        for position, name in enumerate(order):
                            path = root / f'{seed}-{world}-{mode}-{storage}-{repeat}-{name}'
                            state = indexed if name == 'indexed' else reference
                            if storage == 'overwrite':
                                path.mkdir()
                                (path / 'state.json').write_bytes(data)
                            measurement = measured_save(state, path, mode)
                            if (path / 'state.json').read_bytes() != data:
                                raise AssertionError('save contents changed')
                            if storage == 'overwrite' and (path / 'state.json.bak').read_bytes() != data:
                                raise AssertionError('backup contents changed')
                            rows.append(dict(seed=seed, world=world, gc_mode=mode, storage=storage,
                                repeat=repeat, position=position, arm=name, file_bytes=len(data), **measurement))
            # Check instrumentation against normal save and full reloaded outputs.
            ordinary = root / f'{seed}-{world}-ordinary'
            persistence.save_state(indexed, ordinary)
            if (ordinary / 'state.json').read_bytes() != data:
                raise AssertionError('instrumentation changed bytes')
            restored = persistence.load_state(ordinary)
            for case in heldout_cases(seed, world):
                for enabled in (False, True):
                    expected = _query(reference, case, enabled, False)
                    if expected != _query(indexed, case, enabled, True) or expected != _query(restored, case, enabled, True):
                        raise AssertionError('save/reload changed complete result')
    return rows


def interleave_audit(manifest, root):
    rows = []
    options = TrainingOptions(enable_metabolism=False, enable_replay=False)
    for seed in manifest['seeds']:
        for world in manifest['worlds']:
            events = [e for i in range(32) for e in training_episode(seed, world, i)]
            cases = heldout_cases(seed, world)
            for batch in manifest['event_batches']:
                for queries in manifest['queries_per_update']:
                    reference, indexed = RisaState(), RisaState()
                    for step, start in enumerate(range(0, len(events), batch)):
                        chunk = events[start:start + batch]
                        times, results, work = {}, {}, {}
                        order = [('reference', reference, False), ('indexed', indexed, True)]
                        if step % 2:
                            order.reverse()
                        for name, state, use_index in order:
                            begin = perf_counter()
                            train_events(state, chunk, options)
                            times[name + '_train_seconds'] = perf_counter() - begin
                            diagnostics, results[name] = defaultdict(int), []
                            begin = perf_counter()
                            for q in range(queries):
                                ordinal = q if queries > 1 else step % 40
                                case, enabled = cases[ordinal // 2], bool(ordinal % 2)
                                detail = {}
                                results[name].append(_query(state, case, enabled, use_index, detail))
                                for key, value in detail.items():
                                    diagnostics[key] += value
                            times[name + '_query_seconds'] = perf_counter() - begin
                            work[name] = dict(diagnostics)
                        if results['reference'] != results['indexed']:
                            raise AssertionError('interleaved complete results differ')
                        data = encoded(reference)
                        if encoded(indexed) != data:
                            raise AssertionError('interleaved learned/serialized state differs')
                        index = getattr(indexed, '_primitive_grounding_index', None)
                        build_seconds = index['build_seconds'] if index and work['indexed']['index_build_event_reads'] else 0
                        file_checked = False
                        # Actual save/backup/reload every24 Events; serialization
                        # equality is checked at EVERY update, outside timed work.
                        if (start + len(chunk)) % 24 == 0:
                            paths = [root / f'live-{seed}-{world}-{batch}-{queries}-{name}' for name in ('reference', 'indexed')]
                            for state, path in zip((reference, indexed), paths):
                                persistence.save_state(state, path)
                            if paths[0].joinpath('state.json').read_bytes() != paths[1].joinpath('state.json').read_bytes():
                                raise AssertionError('interleaved saved bytes differ')
                            if paths[0].joinpath('state.json.bak').exists():
                                if paths[0].joinpath('state.json.bak').read_bytes() != paths[1].joinpath('state.json.bak').read_bytes():
                                    raise AssertionError('interleaved backup bytes differ')
                            restored = persistence.load_state(paths[1])
                            for case in cases:
                                for enabled in (False, True):
                                    if _query(reference, case, enabled, False) != _query(restored, case, enabled, True):
                                        raise AssertionError('interleaved reload differs')
                            file_checked = True
                        rows.append(dict(seed=seed, world=world, batch=batch, queries=queries,
                            events=start + len(chunk), work=work, times=times,
                            rebuild_seconds=build_seconds, saved_reload_checked=file_checked,
                            complete_result_mismatches=0, serialized_mismatches=0))
    return rows


def run(manifest):
    if manifest['save_repetitions'] < 2 or manifest['save_repetitions'] % 2:
        raise ValueError('even save repetitions required for balanced order')
    legacy_saves = []
    if manifest.get('legacy_reproduction', False):
        from experiments import compositional_grounding_costs as legacy
        original_manifest = json.loads(Path('experiments/g3_compositional_grounding_cost_manifest.json').read_text())
        original_manifest['repetitions'] = 3  # Preserve the original 2:1 order imbalance.
        def legacy_save(state, destination):
            measurement = measured_save(state, destination, 'natural')
            legacy_saves.append(dict(events=len(state.events_by_id), arm=Path(destination).name, **measurement))
        with patch.object(legacy, 'save_state', legacy_save):
            legacy.run_cost_audit(original_manifest)
    with TemporaryDirectory(prefix='risa-save-interleave-') as temporary:
        root = Path(temporary)
        saves = save_audit(manifest, root)
        interleaved = interleave_audit(manifest, root)
    return dict(manifest=manifest, python=platform.python_version(), platform=platform.platform(),
        gc_thresholds=gc.get_threshold(), legacy_save_rows=legacy_saves, save_rows=saves, interleave_rows=interleaved,
        source_sha256={p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in
            ('risa/engine/persistence.py', 'risa/engine/primitive_grounding.py',
             'experiments/grounding_save_interleave_audit.py')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default='experiments/g3_grounding_save_interleave_manifest.json')
    parser.add_argument('--output', default='docs/g3-grounding-save-interleave-results-2026-10-10.json')
    args = parser.parse_args()
    result = run(json.loads(Path(args.manifest).read_text()))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'saves': len(result['save_rows']), 'interleave_steps': len(result['interleave_rows'])}))
