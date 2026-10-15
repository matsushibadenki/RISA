"""Observe composer accesses on held-out worlds; no production trace is implied."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter, process_time
from experiments.compositional_holdout import training_episode, heldout_cases
from experiments.compositional_grounding_costs import _query
from experiments.grounding_frequency_evaluation import OPTIONS
from experiments.grounding_lookup_evaluation import cache_heap
from risa.core.state import RisaState
from risa.engine.runtime import train_events
from risa.engine.persistence import save_state, load_state
from risa.engine import primitive_grounding as g

ARMS = dict(id={}, eager=dict(confirmation_windows=2, probe_cold_candidates=True),
            lazy=dict(confirmation_windows=2, probe_cold_candidates=False))
BUDGET = 2320  # Two 1160-byte lookups on the measurement interpreter.


def content_digest(saved):
    """Ignore only graph edge ordering; retain every edge and its multiplicity."""
    content = json.loads(saved)
    content['graph']['edges'].sort(key=lambda e: json.dumps(e, sort_keys=True))
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def timed(fn):
    wall, cpu = perf_counter(), process_time()
    result = fn()
    return result, dict(wall=perf_counter()-wall, cpu=process_time()-cpu)


def run_worker(repeat=0, densities=(1,8)):
    rows = []
    for world in ('independent','coupled'):
        base = RisaState()
        train_events(base,[e for i in range(32) for e in training_episode(17,world,i)], OPTIONS)
        # Evaluation identities/seed differ from training and the prior single-action fixture.
        panel = [(c,b) for c in heldout_cases(29,world) for b in (False,True)]
        rejects = [(c,b) for c,b in panel if c['category'] in ('wrong_identity','crossed_roles')]
        valid = [(c,b) for c,b in panel if c['category'] in ('seen_path','unseen_path')]
        for density in densities:
            states = {n:RisaState.from_dict(base.to_dict()) for n in ARMS}
            order = list(states)
            stats = {n:dict(build={}, train=[], query=[], rebalance=[], probes=0, promotions=0) for n in states}
            traces, checks = [], 0
            for n in order[repeat%3:]+order[:repeat%3]:
                _, stats[n]['build'] = timed(lambda: g.build_primitive_grounding(states[n], incremental=True,
                    total_lookup_budget_bytes=BUDGET, allocation_policy='id' if n=='id' else 'frequency'))
            for block, cases in enumerate((rejects,rejects,valid,valid,panel,panel)):
                queries = cases * density
                trace = dict(queries=len(queries), arms={})
                answers = {}
                for n in order[(repeat+block)%3:]+order[:(repeat+block)%3]:
                    state = states[n]
                    if block == 2:
                        _, cost = timed(lambda: train_events(state,training_episode(17,world,32),OPTIONS))
                        stats[n]['train'].append(cost)
                    if block == 4:
                        state.events_by_id[f'train:{world}:17:0:0'].target = 'train:'+world+':17:0'
                        g.invalidate_primitive_grounding(state)
                    answers[n], cost = timed(lambda: [_query(state,c,b,True) for c,b in queries])
                    stats[n]['query'].append(cost)
                    index = state._primitive_grounding_index
                    hits = {k:e.get('query_hits',0) for k,e in index['entries'].items()}
                    moved, cost = timed(lambda: g.rebalance_primitive_grounding(state, **ARMS[n]))
                    stats[n]['rebalance'].append(cost)
                    stats[n]['probes'] += moved['cost_probes']
                    stats[n]['promotions'] += moved['promotions']
                    assert index['lookup_bytes_used'] <= BUDGET
                    assert index['lookup_bytes_used'] == sum(e['lookup_bytes'] for e in index['entries'].values())
                    trace['arms'][n] = dict(hits=hits, probes=moved['cost_probes'],
                        selected=sorted(k for k,e in index['entries'].items() if e['lookup'] is not None))
                expected = [_query(states['id'],c,b,False) for c,b in queries]
                assert all(a == expected for a in answers.values())
                checks += len(queries)
                # Full independent/coupled counterexample panel, without contaminating hit counts.
                for c,b in panel:
                    expected_case = _query(states['id'],c,b,False)
                    for state in states.values():
                        snapshot = {k:e.get('query_hits',0) for k,e in state._primitive_grounding_index['entries'].items()}
                        assert _query(state,c,b,True) == expected_case
                        for k,e in state._primitive_grounding_index['entries'].items():
                            if 'query_hits' in e: e['query_hits'] = snapshot[k]
                    checks += 1
                assert all(s.to_dict()==states['id'].to_dict() for s in states.values())
                trace['result_sha256'] = hashlib.sha256(repr(expected).encode()).hexdigest()
                traces.append(trace)
            with TemporaryDirectory() as directory:
                saved = []
                for n,state in states.items():
                    stats[n]['heap'] = cache_heap(state._primitive_grounding_index)
                    path = Path(directory)/n
                    save_state(state,path)
                    saved.append((path/'state.json').read_bytes())
                    restored = load_state(path)
                    g.build_primitive_grounding(restored,total_lookup_budget_bytes=BUDGET,
                        allocation_policy='id' if n=='id' else 'frequency')
                    for c,b in panel:
                        assert _query(restored,c,b,True)==_query(state,c,b,False)
                        checks += 1
                assert len(set(saved))==1
            query_count = sum(t['queries'] for t in traces)
            def cost(n,stage):
                return sum(c['cpu'] for c in stats[n][stage]) if stage!='build' else stats[n]['build']['cpu']
            payback = {}
            for n in ('eager','lazy'):
                savings = cost('id','query')-cost(n,'query')
                overhead = sum(cost(n,k)-cost('id',k) for k in ('build','train','rebalance'))
                payback[n] = dict(query_savings_cpu=savings, extra_maintenance_cpu=overhead,
                    net_cpu_savings=savings-overhead, recovered=savings>overhead,
                    retrospective_break_even_queries=max(0.,overhead)/(savings/query_count) if savings>0 else None)
            rows.append(dict(world=world,density=density,stats=stats,trace=traces,comparisons=checks,
                saved_sha256=hashlib.sha256(saved[0]).hexdigest(),
                saved_content_sha256=content_digest(saved[0]),payback=payback))
    return dict(pid=os.getpid(),hash_seed=os.environ.get('PYTHONHASHSEED'),repeat=repeat,rows=rows)


def run_processes():
    results = []
    with TemporaryDirectory() as directory:
        for seed in (0,1,42):
            for repeat in range(3):
                path = Path(directory)/f'{seed}-{repeat}.json'
                subprocess.run([sys.executable,'-m','experiments.grounding_payback_evaluation','--worker',
                    '--repeat',str(repeat),'--output',str(path)],env={**os.environ,'PYTHONHASHSEED':str(seed)},check=True)
                results.append(json.loads(path.read_text()))
                print(f'finished seed={seed} repeat={repeat}',flush=True)
    # Preserve measurements even if cross-process auditing fails.
    Path('docs/g3-grounding-payback-results-2026-10-15.json').write_text(
        json.dumps(dict(processes=results, cross_process_equal=False), indent=2)+'\n')
    return audit_results(results)


def audit_results(results):
    allocation_equal = True
    for world in ('independent','coupled'):
        for density in (1,8):
            rows = [r for p in results for r in p['rows'] if r['world']==world and r['density']==density]
            assert len({r['saved_content_sha256'] for r in rows})==1
            assert len({json.dumps([t['result_sha256'] for t in r['trace']]) for r in rows})==1
            allocation_equal &= len({json.dumps(r['trace'],sort_keys=True) for r in rows})==1
            for row in rows:
                for t in row['trace']:
                    assert t['arms']['eager']['hits'] == t['arms']['lazy']['hits']
    return dict(processes=results, budget=BUDGET, cross_process_results_and_saved_content_equal=True,
                cross_process_accesses_and_allocations_equal=allocation_equal,
                provenance='Development held-out world queries; no production logs supplied')



if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',action='store_true')
    parser.add_argument('--repeat',type=int,default=0)
    parser.add_argument('--output',default='docs/g3-grounding-payback-results-2026-10-15.json')
    args=parser.parse_args()
    Path(args.output).write_text(json.dumps(run_worker(args.repeat) if args.worker else run_processes(),indent=2)+'\n')
