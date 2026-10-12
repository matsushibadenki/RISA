"""Serial fresh-process/hash-seed comparison of mixed lookup and linear grounding."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

from experiments.grounding_lookup_evaluation import cache_heap
from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine import primitive_grounding as grounding
from risa.engine.composer import compose_to_effect
from risa.engine.runtime import train_events, TrainingOptions
from risa.engine.persistence import save_state, load_state

WIDTHS = (1, 2, 4, 8)
OPTIONS = TrainingOptions(enable_metabolism=False, enable_replay=False, enable_adaptation=False)


def event(p, k):
    return Event(id=f'{p}-{k}', timestamp=k*10+p, actor='shared',
        target='shared' if k % 2 else f'other{k}', action=f'go{p}',
        actor_roles=[f'actor{p}-{j}' for j in range(WIDTHS[p])],
        target_roles=[f'unit{k}-{j}' for j in range(WIDTHS[p])], observed_effects=[f'done{p}'], source=str(k % 2))


def cases():
    return [(p, k, variant, candidate) for p in range(4) for k in (0, 23, 24)
            for variant in range(4) for candidate in (False, True)]


def query(state, case, indexed, work=None):
    p, k, variant, candidate = case
    return compose_to_effect(state, f'go{p}', f'done{p}', actor='new',
        target='new' if (k % 2) ^ (variant == 1) else 'other',
        actor_roles=['absent'] + [f'actor{p}-{j}' for j in range(WIDTHS[p])],
        target_roles=['absent'] if variant == 2 else [f'unit{k}-{j}' for j in range(WIDTHS[p])],
        max_steps=1, enable_candidate_concepts=candidate, use_grounding_index=indexed,
        search_diagnostics=work)


def run_worker(repeat=0):
    base = RisaState()
    train_events(base, [event(p, k) for p in range(4) for k in range(24)], OPTIONS)
    rows = []
    for workload, hot in (('lookup_hot', 0), ('linear_hot', 3)):
        budgets = dict(scan=None, linear=0, unlimited=None, mixed=8192)
        states = {name: RisaState.from_dict(base.to_dict()) for name in budgets}
        stats = {name: dict(build=0., train=0., update=0., query=0., cold_query=0., heap=0,
            probes=0, checks=0, used=0, allocation=[]) for name in budgets}
        order = list(budgets)
        offset = repeat % 4
        for name in order[offset:] + order[:offset]:
            if name != 'scan':
                start = perf_counter()
                grounding.build_primitive_grounding(states[name], incremental=True,
                                                     total_lookup_budget_bytes=budgets[name])
                stats[name]['build'] = perf_counter() - start
        comparisons = 0
        allocations = []
        for phase in range(3):
            order = list(budgets)
            offset = (repeat + phase) % 4
            for name in order[offset:] + order[:offset]:
                state = states[name]
                if phase == 1:
                    update = grounding.update_primitive_grounding
                    def measured(*args, **kwargs):
                        start = perf_counter()
                        update(*args, **kwargs)
                        stats[name]['update'] += perf_counter() - start
                    with patch.object(grounding, 'update_primitive_grounding', measured):
                        start = perf_counter()
                        train_events(state, [event(p, 24) for p in range(4)], OPTIONS)
                        stats[name]['train'] = perf_counter() - start
                elif phase == 2:
                    for p in range(4):
                        state.events_by_id[f'{p}-0'].target = 'shared'
                    grounding.invalidate_primitive_grounding(state)
                start = perf_counter()
                for q in range(64):
                    detail = {}
                    query(state, (hot, (0, 23, 24)[q % 3], q % 4, bool(q % 2)), name != 'scan', detail)
                    stats[name]['probes'] += detail['grounding_lookup_probes']
                    stats[name]['checks'] += detail['grounding_signature_checks']
                elapsed = perf_counter() - start
                stats[name]['query'] += elapsed
                if phase == 2:
                    stats[name]['cold_query'] = elapsed
            panel = cases()
            expected = [query(states['scan'], c, False) for c in panel]
            for name, state in states.items():
                assert [query(state, c, name != 'scan') for c in panel] == expected
                assert state.to_dict() == states['scan'].to_dict()
            comparisons += len(panel)
            index = states['mixed']._primitive_grounding_index
            assert index['lookup_bytes_used'] == sum(e['lookup_bytes'] for e in index['entries'].values())
            assert index['lookup_bytes_used'] <= 8192
            selected = sorted(k for k, e in index['entries'].items() if e['lookup'] is not None)
            assert 0 < len(selected) < len(index['entries'])
            allocations.append(selected)
        with TemporaryDirectory() as directory:
            saved = []
            for name, state in states.items():
                if name != 'scan':
                    index = state._primitive_grounding_index
                    stats[name]['heap'] = cache_heap(index)
                    stats[name]['used'] = index['lookup_bytes_used']
                    stats[name]['allocation'] = sorted(k for k, e in index['entries'].items() if e['lookup'] is not None)
                path = Path(directory) / name
                save_state(state, path)
                saved.append((path / 'state.json').read_bytes())
                restored = load_state(path)
                if name != 'scan':
                    grounding.build_primitive_grounding(restored, total_lookup_budget_bytes=budgets[name])
                assert [query(restored, c, name != 'scan') for c in panel] == expected
                comparisons += len(panel)
            assert len(set(saved)) == 1
        rows.append(dict(workload=workload, stats=stats, comparisons=comparisons, allocations=allocations,
            result_sha256=hashlib.sha256(repr(expected).encode()).hexdigest(),
            saved_sha256=hashlib.sha256(saved[0]).hexdigest(), saved_bytes=len(saved[0]), mismatches=0))
    return dict(hash_seed=os.environ.get('PYTHONHASHSEED'), repeat=repeat, pid=os.getpid(), rows=rows)


def run_processes():
    results = []
    with TemporaryDirectory() as directory:
        for seed in (0, 1, 42):
            for repeat in range(4):
                path = Path(directory) / f'{seed}-{repeat}.json'
                subprocess.run([sys.executable, '-m', 'experiments.grounding_total_budget_evaluation',
                                '--worker', '--repeat', str(repeat), '--output', str(path)],
                               env={**os.environ, 'PYTHONHASHSEED': str(seed)}, check=True)
                results.append(json.loads(path.read_text()))
                print(f'finished seed={seed} repeat={repeat}', flush=True)
    for workload in ('lookup_hot', 'linear_hot'):
        rows = [r for process in results for r in process['rows'] if r['workload'] == workload]
        assert len({r['saved_sha256'] for r in rows}) == 1
        assert len({r['result_sha256'] for r in rows}) == 1
        assert len({json.dumps(r['allocations']) for r in rows}) == 1
    return dict(processes=results, cross_process_exact=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--repeat', type=int, default=0)
    parser.add_argument('--output', default='docs/g3-grounding-total-budget-results-2026-10-12.json')
    args = parser.parse_args()
    result = run_worker(args.repeat) if args.worker else run_processes()
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
