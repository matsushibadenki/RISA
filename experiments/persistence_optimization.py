"""Isolated, repeatable save profiles; allocation tracing is a separate run."""
from __future__ import annotations

import argparse
import cProfile
import hashlib
import json
import platform
from pathlib import Path
import pstats
import resource
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from time import perf_counter, process_time
import tracemalloc

from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine.persistence import load_state, save_state
from risa.engine.runtime import TrainingOptions, train_events
from experiments.references import persistence_before_20261007 as before


def prepare(directory, scales):
    state = RisaState()
    previous = 0
    for scale in scales:
        if scale == 0:
            from risa.engine.event_parser import parse_events
            example = RisaState()
            train_events(example, parse_events('data/stateful_world.json'))
            before.save_state(example, directory / 'examples')
            continue
        for offset in range(previous, scale, 1000):
            events = [Event(id=f'e-17-{i:09d}', timestamp=i+1, actor=f'actor-{i % 8}',
                            action=f'action-{i % 4}', observed_effects=[f'effect-{i % 4}'],
                            context_tags=[f'context-{i % 3}'], episode_id=f'episode-17-{i // 12}',
                            source=f'source-{i % 2}') for i in range(offset, min(scale, offset+1000))]
            train_events(state, events, TrainingOptions(replay_max_events=32))
        before.save_state(state, directory / str(scale))
        previous = scale
    print(json.dumps({'prepared': scales, 'directory': str(directory)}), flush=True)


def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)


def worker(args):
    if args.fixture is None or not (args.fixture / "state.json").is_file():
        raise ValueError("prepare an existing state fixture before benchmarking")
    if args.implementation == 'index-before':
        from risa.engine import prediction_indexes
        from experiments.references.prediction_indexes_before_20261007 import rebuild_prediction_indexes

        prediction_indexes.rebuild_prediction_indexes = rebuild_prediction_indexes
    state = load_state(args.fixture)
    if args.implementation == 'event-before':
        import risa.core.state as state_module

        def legacy_event_export(event):
            record = event.to_dict()
            record.pop('id', None)
            return state_module._without_default_values(record, state_module._EVENT_PERSISTENCE_DEFAULTS)

        state_module._event_persistence_record = legacy_event_export
    module = before if args.implementation == 'before' else sys.modules['risa.engine.persistence']
    with tempfile.TemporaryDirectory(prefix='risa-persistence-save-') as directory:
        if args.operation == 'overwrite':
            shutil.copyfile(args.fixture / "state.json", Path(directory) / "state.json")
        profile = cProfile.Profile() if args.profile else None
        if profile:
            tracemalloc.start()
            profile.enable()
        rss_before_save = rss()
        wall_start, cpu_start = perf_counter(), process_time()
        module.save_state(state, directory)
        wall, cpu = perf_counter()-wall_start, process_time()-cpu_start
        save_peak_rss = rss()
        if profile:
            profile.disable()
            current, peak = tracemalloc.get_traced_memory()
            allocation_blocks = sum(stat.count for stat in tracemalloc.take_snapshot().statistics('filename'))
            tracemalloc.stop()
        else:
            current = peak = allocation_blocks = None
        saved = Path(directory) / 'state.json'
        digest_builder = hashlib.sha256()
        with saved.open('rb') as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b''):
                digest_builder.update(block)
        digest = digest_builder.hexdigest()
        file_bytes = saved.stat().st_size
        restored = load_state(directory)
        # Compare canonical persistence snapshots, outside latency measurement.
        state_equal = restored.to_dict() == state.to_dict()
        result = {'implementation': args.implementation, 'operation': args.operation,
                  'fixture': str(args.fixture), 'events': len(state.events_by_id),
                  'wall_seconds': wall, 'cpu_seconds': cpu, 'peak_rss_bytes': save_peak_rss, 'rss_before_save_bytes': rss_before_save,
                  'file_bytes': file_bytes, 'file_sha256': digest, 'state_equal': state_equal,
                  'traced_current_bytes': current, 'traced_peak_bytes': peak,
                  'live_allocation_blocks': allocation_blocks, 'instrumented': bool(profile)}
        if profile:
            stats = pstats.Stats(profile)
            entries = sorted(stats.stats.items(), key=lambda item: item[1][3], reverse=True)[:18]
            result['profile'] = [{'function': f'{key[0]}:{key[1]}:{key[2]}', 'primitive_calls': value[0],
                                  'calls': value[1], 'self_seconds': value[2], 'cumulative_seconds': value[3]}
                                 for key, value in entries]
            result['total_calls'] = stats.total_calls
        return result


def summarize(rows, operations=('fresh', 'overwrite')):
    groups = []
    for size in sorted({r['events'] for r in rows if not r['instrumented']}):
        for operation in operations:
            selected = [r for r in rows if r['events'] == size and r['operation'] == operation and not r['instrumented']]
            if not selected:
                continue
            def percentile(values, fraction):
                ordered = sorted(values)
                return ordered[max(0, int(len(ordered)*fraction + 0.999999)-1)]
            groups.append({'events': size, 'operation': operation, 'sample_count': len(selected),
                           'median_seconds': percentile([r['wall_seconds'] for r in selected], .5),
                           'p95_seconds': percentile([r['wall_seconds'] for r in selected], .95),
                           'p99_seconds': percentile([r['wall_seconds'] for r in selected], .99),
                           'maximum_seconds': max(r['wall_seconds'] for r in selected),
                           'median_cpu_seconds': percentile([r['cpu_seconds'] for r in selected], .5),
                           'maximum_rss_bytes': max(r['peak_rss_bytes'] for r in selected)})
    return groups


def audit_membership(fixture):
    if fixture is None or not (fixture / "state.json").is_file():
        raise ValueError("prepare an existing state fixture before auditing")
    from unittest.mock import patch
    from risa.engine import evidence
    counters = dict(cache_hits=0, cache_misses=0, invalidations=0, rebuilds=0,
                    duplicate_membership_hits=0, evictions=0)
    original = evidence._append
    def tracked(state, key, event_id):
        values = state.evidence_index.get(key)
        cached = state.evidence_membership.get(key)
        usable = cached is not None and cached[0] is values and len(cached[1]) == len(values)
        if usable:
            counters['cache_hits'] += 1
            counters['duplicate_membership_hits'] += event_id in cached[1]
        else:
            counters['cache_misses'] += 1
            counters['rebuilds'] += 1
            counters['invalidations'] += cached is not None
        original(state, key, event_id)
    with patch.object(evidence, '_append', tracked):
        state = load_state(fixture)
    calls = counters['cache_hits'] + counters['cache_misses']
    return {**counters, 'events': len(state.events_by_id), 'calls': calls,
            'cache_hit_ratio': counters['cache_hits'] / max(1, calls),
            'cache_shallow_bytes': sys.getsizeof(state.evidence_membership) + sum(
                sys.getsizeof(record) + sys.getsizeof(record[1]) for record in state.evidence_membership.values()),
            'note': 'Evidence-membership cache during one cold reload. Shallow bytes exclude shared Event-ID strings and evidence lists. Hits reuse per-bucket membership sets during reconstruction, not across CLI invocations. No eviction mechanism.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--directory', type=Path, default=Path('/tmp/risa-optimization-fixtures'))
    parser.add_argument('--scales', type=int, nargs='+', default=[1000, 10000, 100000])
    parser.add_argument('--implementation', choices=['before', 'after', 'event-before', 'index-before'], default='before')
    parser.add_argument('--paired-index', action='store_true', help='alternate old/new index reconstruction in fresh subprocesses')
    parser.add_argument('--operation', choices=['fresh', 'overwrite'], default='fresh')
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--audit-cache', action='store_true')
    parser.add_argument('--samples', type=int, default=3)
    parser.add_argument('--output', default='docs/persistence-before-results.json')
    args = parser.parse_args()
    if args.samples < 1 or args.scales != sorted(set(args.scales)) or any(scale < 0 for scale in args.scales):
        parser.error("samples must be positive and scales must be nonnegative, unique and ascending")
    if args.audit_cache:
        result = audit_membership(args.fixture)
        Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        return
    if args.prepare:
        prepare(args.directory, args.scales)
        return
    if args.worker:
        print(json.dumps(worker(args)))
        return
    rows = []
    if args.paired_index:
        for scale in args.scales:
            for operation in ('fresh', 'overwrite'):
                for sample in range(args.samples):
                    implementations = ('index-before', 'after') if sample % 2 == 0 else ('after', 'index-before')
                    for implementation in implementations:
                        command = [sys.executable, '-m', 'experiments.persistence_optimization', '--worker',
                                   '--fixture', str(args.directory / ('examples' if scale == 0 else str(scale))),
                                   '--implementation', implementation, '--operation', operation]
                        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=180)
                        row = json.loads(completed.stdout)
                        row['sample'] = sample
                        rows.append(row)
                print(json.dumps({'scale': scale, 'operation': operation, 'paired_samples': args.samples}), flush=True)
        result = {'environment': {'python': platform.python_version(), 'platform': platform.platform()},
                  'rows': rows, 'summary': {implementation: summarize([r for r in rows if r['implementation'] == implementation])
                                           for implementation in ('index-before', 'after')},
                  'note': 'Alternating old/new order per sample; fresh subprocesses, no simultaneous benchmark workers; empirical tails only.'}
        Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        return
    for scale in args.scales:
        for operation in ('fresh', 'overwrite'):
            for sample in range(args.samples):
                command = [sys.executable, '-m', 'experiments.persistence_optimization', '--worker',
                           '--fixture', str(args.directory / ('examples' if scale == 0 else str(scale))), '--implementation', args.implementation,
                           '--operation', operation]
                completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=180)
                row = json.loads(completed.stdout)
                row['sample'] = sample
                rows.append(row)
                print(json.dumps({'requested_scale': scale, 'events': row['events'], 'operation': operation, 'sample': sample,
                                  'wall_seconds': row['wall_seconds']}), flush=True)
    profile_scale = 10000 if 10000 in args.scales else max(args.scales)
    command = [sys.executable, '-m', 'experiments.persistence_optimization', '--worker', '--profile',
               '--fixture', str(args.directory / ('examples' if profile_scale == 0 else str(profile_scale))), '--implementation', args.implementation]
    profiled = subprocess.run(command, check=True, capture_output=True, text=True, timeout=180)
    rows.append(json.loads(profiled.stdout))
    result = {'implementation': args.implementation, 'environment': {'python': platform.python_version(),
              'platform': platform.platform(), 'python_debug_build': bool(sysconfig.get_config_var('Py_DEBUG'))}, 'rows': rows, 'summary': summarize(rows),
              'note': f'Fresh subprocess per sample; percentiles over {args.samples} samples are empirical order statistics, not robust production tail estimates. Three-sample p95/p99 equal maxima. CPU time is an energy proxy only; no direct energy measurement.'}
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
