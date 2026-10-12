"""Past-window hit/byte allocation versus equal-budget ID order; serial processes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter, process_time
from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine.runtime import train_events, TrainingOptions
from risa.engine.composer import compose_to_effect
from risa.engine import primitive_grounding as g
from risa.engine.persistence import save_state, load_state
from experiments.grounding_lookup_evaluation import cache_heap

WIDTHS = (1, 1, 2, 2)
OPTIONS = TrainingOptions(enable_metabolism=False, enable_replay=False, enable_adaptation=False)


def event(p, k):
    return Event(id=f'{p}-{k}', timestamp=k*10+p, actor='shared', target='shared' if k%2 else f'other{k}',
        action=f'go{p}', actor_roles=[f'a{p}-{j}' for j in range(WIDTHS[p])],
        target_roles=[f't{k}-{j}' for j in range(WIDTHS[p])], observed_effects=[f'done{p}'], source=str(k%2))


def query(state, p, k, variant, indexed):
    return compose_to_effect(state, f'go{p}', f'done{p}', actor='new',
        target='new' if (k%2) ^ (variant == 1) else 'other', actor_roles=[f'a{p}-{j}' for j in range(WIDTHS[p])],
        target_roles=['absent'] if variant == 2 else [f't{k}-{j}' for j in range(WIDTHS[p])],
        enable_candidate_concepts=bool(variant%2), max_steps=1, use_grounding_index=indexed)


def verify(states):
    snapshots = {name: {k:e.get('query_hits',0) for k,e in state._primitive_grounding_index['entries'].items()}
                 for name,state in states.items()}
    count = 0
    complete_results = []
    for p in range(4):
        for k in (0,63,64):
            for variant in range(3):
                expected = query(states['id'], p,k,variant,False)
                complete_results.append(repr(expected))
                for state in states.values():
                    assert query(state,p,k,variant,True) == expected
                count += 1
    for name,state in states.items():
        for k,e in state._primitive_grounding_index['entries'].items():
            if 'query_hits' in e:
                e['query_hits'] = snapshots[name][k]
    assert states['id'].to_dict() == states['frequency'].to_dict()
    return count, hashlib.sha256(json.dumps(complete_results).encode()).hexdigest()


def run_worker(repeat=0, queries=256):
    base = RisaState()
    train_events(base,[event(p,k) for p in range(4) for k in range(64)],OPTIONS)
    rows = []
    for workload, schedule in dict(stationary=[3]*6, shifting=[3,3,0,0,2,2], rapid=[3,0,2,1,3,0]).items():
        states = {name:RisaState.from_dict(base.to_dict()) for name in ('id','frequency')}
        stats = {name:dict(build=0.,train=0.,query=0.,rebalance=0.,build_cpu=0.,train_cpu=0.,query_cpu=0.,rebalance_cpu=0.,promotions=0,demotions=0,cost_probes=0,heap=0) for name in states}
        for name in list(states)[::(-1 if repeat%2 else 1)]:
            start = perf_counter()
            start_cpu = process_time()
            g.build_primitive_grounding(states[name], incremental=True,total_lookup_budget_bytes=12000,allocation_policy=name)
            stats[name]['build'] = perf_counter()-start
            stats[name]['build_cpu'] = process_time()-start_cpu
        comparisons, trace = 0, []
        for block,hot in enumerate(schedule):
            block_trace = dict(hot=hot)
            for name in list(states)[::(-1 if (repeat+block)%2 else 1)]:
                state = states[name]
                if block == 2:
                    start = perf_counter()
                    start_cpu = process_time()
                    train_events(state,[event(p,64) for p in range(4)],OPTIONS)
                    stats[name]['train'] += perf_counter()-start
                    stats[name]['train_cpu'] += process_time()-start_cpu
                if block == 4:
                    for p in range(4): state.events_by_id[f'{p}-0'].target = 'shared'
                    g.invalidate_primitive_grounding(state)
                start = perf_counter()
                start_cpu = process_time()
                for q in range(queries): query(state,hot,q%65,q%3,True)
                elapsed = perf_counter()-start
                stats[name]['query'] += elapsed
                stats[name]['query_cpu'] += process_time()-start_cpu
                start_cpu = process_time()
                moved = g.rebalance_primitive_grounding(state)
                stats[name]['rebalance'] += moved['seconds']
                stats[name]['rebalance_cpu'] += process_time()-start_cpu
                for k in ('promotions','demotions','cost_probes'): stats[name][k] += moved[k]
                index = state._primitive_grounding_index
                assert index['lookup_bytes_used'] <= 12000
                assert index['lookup_bytes_used'] == sum(e['lookup_bytes'] for e in index['entries'].values())
                block_trace[name] = dict(query=elapsed,rebalance=moved['seconds'],selected=sorted(k for k,e in index['entries'].items() if e['lookup'] is not None))
            checked, digest = verify(states)
            comparisons += checked
            block_trace['result_sha256'] = digest
            trace.append(block_trace)
        with TemporaryDirectory() as directory:
            saved = []
            for name,state in states.items():
                stats[name]['heap'] = cache_heap(state._primitive_grounding_index)
                path = Path(directory)/name
                save_state(state,path)
                saved.append((path/'state.json').read_bytes())
                restored = load_state(path)
                g.build_primitive_grounding(restored,total_lookup_budget_bytes=12000,allocation_policy=name)
                for p in range(4):
                    for k in (0,63,64):
                        for v in range(3):
                            assert query(restored,p,k,v,True)==query(state,p,k,v,False)
                            comparisons+=1
            assert len(set(saved))==1
        rows.append(dict(workload=workload,stats=stats,trace=trace,comparisons=comparisons,mismatches=0,
                         saved_sha256=hashlib.sha256(saved[0]).hexdigest()))
    return dict(hash_seed=os.environ.get('PYTHONHASHSEED'),repeat=repeat,pid=os.getpid(),queries=queries,rows=rows)


def run_processes():
    results=[]
    with TemporaryDirectory() as directory:
        for seed in (0,1,42):
            for repeat in range(2):
                path=Path(directory)/f'{seed}-{repeat}.json'
                subprocess.run([sys.executable,'-m','experiments.grounding_frequency_evaluation','--worker','--repeat',str(repeat),'--output',str(path)],env={**os.environ,'PYTHONHASHSEED':str(seed)},check=True)
                results.append(json.loads(path.read_text()))
                print(f'finished seed={seed} repeat={repeat}',flush=True)
    assert len({row['saved_sha256'] for proc in results for row in proc['rows']})==1
    for workload in ('stationary','shifting','rapid'):
        allocations=[[[block[name]['selected'] for name in ('id','frequency')] for block in row['trace']]
                     for proc in results for row in proc['rows'] if row['workload']==workload]
        assert len({json.dumps(a) for a in allocations})==1
        digests = [[block['result_sha256'] for block in row['trace']] for proc in results for row in proc['rows'] if row['workload']==workload]
        assert len({json.dumps(d) for d in digests})==1
    return dict(processes=results,cross_process_saved_and_allocations_equal=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',action='store_true')
    parser.add_argument('--repeat',type=int,default=0)
    parser.add_argument('--output',default='docs/g3-grounding-frequency-results-2026-10-12.json')
    args=parser.parse_args()
    result=run_worker(args.repeat) if args.worker else run_processes()
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
