"""Cold reconstruction and high-diversity index ablation in fresh processes."""
from __future__ import annotations
import argparse
import cProfile
import json
from pathlib import Path
import platform
import pstats
import resource
import subprocess
import sys
from time import perf_counter, process_time
import tracemalloc

from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine import prediction_indexes
from risa.engine.persistence import load_state
from experiments.references import prediction_indexes_before_20261007 as before
from experiments.persistence_optimization import summarize


def worker(args):
    if args.implementation == 'before':
        prediction_indexes.rebuild_prediction_indexes = before.rebuild_prediction_indexes
    if args.case == 'cold-load':
        if not (args.fixture / 'state.json').is_file():
            raise ValueError('missing prepared fixture')
        operation = lambda: load_state(args.fixture)
    else:
        state = RisaState()
        state.events_by_id = {f'e{i}': Event(f'e{i}', args.scale-i, 'actor', 'action',
                              target='target', target_roles=['role'],
                              observed_effects=[f'effect{i}', f'effect{i+1}', f'effect{i+2}'])
                              for i in range(args.scale)}
        operation = lambda: prediction_indexes.rebuild_prediction_indexes(state)
    profile = cProfile.Profile() if args.profile else None
    if profile:
        tracemalloc.start()
        profile.enable()
    wall, cpu = perf_counter(), process_time()
    restored = operation()
    wall, cpu = perf_counter()-wall, process_time()-cpu
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
    traced = None
    if profile:
        profile.disable()
        _, traced = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    if args.case == 'cold-load':
        state = restored
    result = {'case': args.case, 'implementation': args.implementation, 'events': len(state.events_by_id),
              'operation': args.case, 'wall_seconds': wall, 'cpu_seconds': cpu,
              'peak_rss_bytes': peak_rss, 'instrumented': bool(profile), 'traced_peak_bytes': traced}
    reference = RisaState(events_by_id=state.events_by_id,
                          target_role_readout_hops=state.target_role_readout_hops)
    before.rebuild_prediction_indexes(reference)
    names = ('actor_action_effect_counts', 'action_effect_counts', 'actor_action_context_effect_counts',
             'action_context_effect_counts', 'actor_action_target_context_effect_counts',
             'action_target_context_effect_counts', 'action_target_role_context_effect_counts', 'activation_index')
    result['indexes_equal'] = all(getattr(reference, name) == getattr(state, name) for name in names)
    if not result['indexes_equal']:
        raise AssertionError('reconstructed indexes differ')
    if profile:
        stats = pstats.Stats(profile)
        result['total_calls'] = stats.total_calls
        result['profile'] = [{'function': f'{k[0]}:{k[1]}:{k[2]}', 'calls': v[1], 'self_seconds': v[2],
                              'cumulative_seconds': v[3]} for k,v in
                              sorted(stats.stats.items(), key=lambda item:item[1][3], reverse=True)[:25]]
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--worker', action='store_true')
    p.add_argument('--profile', action='store_true')
    p.add_argument('--implementation', choices=['before', 'after'], default='before')
    p.add_argument('--case', choices=['cold-load', 'diverse-index'], default='cold-load')
    p.add_argument('--scale', type=int, default=10000)
    p.add_argument('--fixture', type=Path, default=Path('/tmp/risa-optimization-fixtures/10000'))
    p.add_argument('--samples', type=int, default=7)
    p.add_argument('--output', type=Path, default=Path('/tmp/reconstruction.json'))
    args = p.parse_args()
    if args.samples < 1 or args.scale < 1:
        p.error('samples and scale must be positive')
    if args.worker:
        print(json.dumps(worker(args)))
        return
    rows=[]
    for case in ('cold-load', 'diverse-index'):
        for i in range(args.samples+1):
            command=[sys.executable, '-m', 'experiments.reconstruction_optimization', '--worker',
                     '--implementation',args.implementation,'--case',case,'--scale',str(args.scale),
                     '--fixture',str(args.fixture)]
            if i == args.samples:
                command.append('--profile')
            row=json.loads(subprocess.run(command,check=True,capture_output=True,text=True,timeout=180).stdout)
            rows.append(row)
            print(json.dumps({'case':case,'sample':i,'seconds':row['wall_seconds'],'profile':row['instrumented']}),flush=True)
    args.output.write_text(json.dumps({'environment':{'python':platform.python_version(),'platform':platform.platform()},
                           'rows':rows,'summary':summarize(rows, ('cold-load', 'diverse-index')),
                           'note':'Normal timings and instrumentation are separate; seven-sample tails are not production guarantees. Diverse-index is an isolated synthetic stress case, not trained quality evidence.'},indent=2)+'\n')

if __name__ == '__main__':
    main()
