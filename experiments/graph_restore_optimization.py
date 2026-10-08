"""Paired graph hydration, cold-load and save measurements; no parallel workers."""
from __future__ import annotations
import argparse
import cProfile
import hashlib
import json
from pathlib import Path
import platform
import pstats
import resource
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from time import perf_counter, process_time
import tracemalloc

from risa.core import state as state_module
from risa.core.graph_store import GraphStore
from risa.engine.persistence import load_state, save_state
from risa.engine import persistence
from experiments.references.graph_store_before_20261007 import GraphStore as BeforeGraphStore
from experiments.persistence_optimization import summarize


def audit_context_pool(fixture):
    from unittest.mock import patch
    from risa.core import graph_store

    original = graph_store._restore_context_tags
    counters = dict(hits=0, misses=0, empty_bypasses=0, unhashable_bypasses=0,
                    invalidations=0, rebuilds=1, evictions=0, peak_entries=0,
                    peak_shallow_pool_bytes=0)

    def tracked(values, pool):
        tags = tuple(values)
        if not tags:
            counters['empty_bypasses'] += 1
        else:
            try:
                if tags in pool:
                    counters['hits'] += 1
                else:
                    counters['misses'] += 1
            except TypeError:
                counters['unhashable_bypasses'] += 1
        result = original(values, pool)
        counters['peak_entries'] = max(counters['peak_entries'], len(pool))
        counters['peak_shallow_pool_bytes'] = max(counters['peak_shallow_pool_bytes'],
                                                 sys.getsizeof(pool) + sum(sys.getsizeof(key) for key in pool))
        return result

    raw = json.loads((fixture / 'state.json').read_text())
    with patch.object(graph_store, '_restore_context_tags', tracked):
        actual = GraphStore.from_dict(raw['graph'])
    expected = BeforeGraphStore.from_dict(raw['graph'])
    assert actual.to_compact_dict() == expected.to_compact_dict()
    counters['hit_ratio'] = counters['hits'] / max(1, counters['hits']+counters['misses'])
    return {'fixture': str(fixture), 'edges': len(raw['graph']['edges']), 'counters': counters,
            'note': 'Separate instrumented audit; shallow pool bytes include canonical tuples shared with Edges but exclude strings. Pool dictionary is released after graph restoration. No cumulative allocation count or energy measurement.'}


def worker(args):
    path = args.fixture / 'state.json'
    if not path.is_file():
        raise ValueError('prepare the fixture first')
    graph_class = BeforeGraphStore if args.implementation == 'before' else GraphStore
    if args.event_baseline:
        from experiments.references.state_before_event_restore_20261008 import RisaState as BeforeState

        graph_class = GraphStore
        persistence.RisaState = BeforeState if args.implementation == 'before' else state_module.RisaState
    state_module.GraphStore = graph_class
    raw = json.loads(path.read_text()) if args.operation == 'graph' else None
    state = load_state(args.fixture) if args.operation in ('fresh', 'overwrite') else None
    with tempfile.TemporaryDirectory(prefix='risa-graph-restore-') as directory:
        if args.operation == 'overwrite':
            shutil.copyfile(path, Path(directory)/'state.json')
        profile = cProfile.Profile() if args.profile else None
        if profile:
            tracemalloc.start()
            profile.enable()
        usage_before = resource.getrusage(resource.RUSAGE_SELF)
        wall, cpu = perf_counter(), process_time()
        if args.operation == 'graph':
            result_state = graph_class.from_dict(raw['graph'])
        elif args.operation == 'load':
            result_state = load_state(args.fixture)
        else:
            save_state(state, directory)
        wall, cpu = perf_counter()-wall, process_time()-cpu
        usage = resource.getrusage(resource.RUSAGE_SELF)
        peak = current = blocks = None
        if profile:
            profile.disable()
            current, peak = tracemalloc.get_traced_memory()
            blocks = sum(stat.count for stat in tracemalloc.take_snapshot().statistics('filename'))
            tracemalloc.stop()
        if args.operation == 'graph':
            reference = BeforeGraphStore.from_dict(raw['graph'])
            equal = (result_state.to_compact_dict() == reference.to_compact_dict()
                     and result_state.adjacency_out == reference.adjacency_out
                     and result_state.adjacency_in == reference.adjacency_in
                     and result_state.coactivation_neighbors == reference.coactivation_neighbors
                     and result_state.metabolism_pending == reference.metabolism_pending)
            events = len(raw.get('events', {}))
            snapshot = result_state.to_compact_dict()
        elif args.operation == 'load':
            snapshot = result_state.to_dict()
            state_module.GraphStore = BeforeGraphStore
            equal = snapshot == load_state(args.fixture).to_dict()
            events = len(result_state.events_by_id)
        else:
            snapshot = load_state(directory).to_dict()
            equal = snapshot == state.to_dict()
            events = len(state.events_by_id)
        if not equal:
            raise AssertionError('restore differs')
        row = {'implementation': args.implementation, 'operation': args.operation, 'events': events,
               'wall_seconds': wall, 'cpu_seconds': cpu, 'peak_rss_bytes': usage.ru_maxrss * (1 if sys.platform == 'darwin' else 1024),
               'voluntary_context_switches': usage.ru_nvcsw-usage_before.ru_nvcsw,
               'involuntary_context_switches': usage.ru_nivcsw-usage_before.ru_nivcsw,
               'instrumented': bool(profile), 'traced_peak_bytes': peak, 'state_equal': equal,
               'traced_retained_bytes': current, 'live_allocation_blocks': blocks,
               'snapshot_sha256': hashlib.sha256(json.dumps(snapshot,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        if args.operation in ('fresh', 'overwrite'):
            saved=Path(directory)/'state.json'
            row['file_bytes']=saved.stat().st_size
            row['file_sha256']=hashlib.sha256(saved.read_bytes()).hexdigest()
        if profile:
            stats=pstats.Stats(profile)
            row['total_calls']=stats.total_calls
            row['profile']=[{'function':f'{k[0]}:{k[1]}:{k[2]}','calls':v[1],'self_seconds':v[2],'cumulative_seconds':v[3]}
                            for k,v in sorted(stats.stats.items(),key=lambda item:item[1][3],reverse=True)[:20]]
        return row


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--worker',action='store_true')
    p.add_argument('--event-baseline',action='store_true', help='compare Event restoration, keeping graph restoration fixed')
    p.add_argument('--profile',action='store_true')
    p.add_argument('--audit-cache',action='store_true')
    p.add_argument('--implementation',choices=['before','after'],default='before')
    p.add_argument('--operation',choices=['graph','load','fresh','overwrite'],default='graph')
    p.add_argument('--operations', nargs='+', choices=['graph','load','fresh','overwrite'],
                   default=['graph','load','fresh','overwrite'])
    p.add_argument('--fixture',type=Path,default=Path('/tmp/risa-optimization-fixtures/10000'))
    p.add_argument('--samples',type=int,default=7)
    p.add_argument('--output',type=Path,default=Path('/tmp/graph-restore.json'))
    args=p.parse_args()
    if args.samples<1:
        p.error('samples must be positive')
    if args.audit_cache:
        args.output.write_text(json.dumps(audit_context_pool(args.fixture),indent=2)+'\n')
        return
    if args.worker:
        print(json.dumps(worker(args)))
        return
    rows=[]
    for operation in args.operations:
        for sample in range(args.samples):
            for implementation in (('before','after') if sample%2==0 else ('after','before')):
                command=[sys.executable,'-m','experiments.graph_restore_optimization','--worker',
                         '--implementation',implementation,'--operation',operation,'--fixture',str(args.fixture)]
                if args.event_baseline:
                    command.append('--event-baseline')
                row=json.loads(subprocess.run(command,check=True,capture_output=True,text=True,timeout=180).stdout)
                row['sample']=sample
                rows.append(row)
        for implementation in ('before','after'):
            command=[sys.executable,'-m','experiments.graph_restore_optimization','--worker','--profile',
                     '--implementation',implementation,'--operation',operation,'--fixture',str(args.fixture)]
            if args.event_baseline:
                command.append('--event-baseline')
            rows.append(json.loads(subprocess.run(command,check=True,capture_output=True,text=True,timeout=180).stdout))
        print(json.dumps({'operation':operation,'pairs':args.samples}),flush=True)
    for operation in args.operations:
        for sample in range(args.samples):
            pair=[r for r in rows if r['operation']==operation and r.get('sample')==sample and not r['instrumented']]
            assert pair[0]['snapshot_sha256']==pair[1]['snapshot_sha256']
            if operation in ('fresh','overwrite'):
                assert pair[0]['file_sha256']==pair[1]['file_sha256']
    args.output.write_text(json.dumps({'baseline': 'event-restore-20261008' if args.event_baseline else 'graph-restore-20261007',
                           'environment':{'python':platform.python_version(),'platform':platform.platform(),
                                       'python_debug_build':bool(sysconfig.get_config_var('Py_DEBUG'))},
                           'rows':rows,'summary':{impl:summarize([r for r in rows if r['implementation']==impl],
                                     args.operations) for impl in ('before','after')},
                           'note':'Alternating order per pair, fresh subprocesses, normal timings separate from instrumentation. Empirical tails are not production guarantees. Context switches exclude setup and correctness checks; traced allocation peaks are not cumulative allocation counts.'},indent=2)+'\n')

if __name__=='__main__':
    main()
