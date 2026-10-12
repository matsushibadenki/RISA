"""Explicit per-primitive lookup-container budgets, append and correction costs."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from experiments.grounding_lookup_evaluation import event, cases, query, cache_heap
from risa.core.state import RisaState
from risa.engine.runtime import train_events, TrainingOptions
from risa.engine.primitive_grounding import build_primitive_grounding, invalidate_primitive_grounding
from risa.engine.persistence import save_state, load_state


def run(widths=(4, 16, 64), densities=(1, 16), repetitions=4):
    rows = []
    opts = TrainingOptions(enable_metabolism=False, enable_replay=False, enable_adaptation=False)
    arms = dict(scan=None, linear=0, lookup=None, budget=8192)
    for world in ('shared', 'distinct'):
        for width in widths:
            def make(i):
                e = event(i, i, width)
                if world == 'distinct':
                    e.actor_roles = [f'actor{i}-{j}' for j in range(width)]
                return e
            base = RisaState()
            train_events(base, [make(i) for i in range(32)], opts)
            def panel():
                result = cases(32, width, 35)
                if world == 'distinct':
                    result = [((['actor0-0', 'actor31-0', 'actor35-0'], tr, actor, target), c)
                              for (_, tr, actor, target), c in result]
                return result
            checks = panel()
            for density in densities:
                for repeat in range(repetitions):
                    states = {name: RisaState.from_dict(base.to_dict()) for name in arms}
                    stats = {name: dict(build=0., train=0., query=0., correction_query=0., heap=0,
                        fallback_entries=0, lookup_container_bytes=0) for name in arms}
                    order = list(arms)
                    order = order[repeat % 4:] + order[:repeat % 4]
                    for name in order:
                        if name != 'scan':
                            start = perf_counter()
                            build_primitive_grounding(states[name], incremental=True, lookup_budget_bytes=arms[name])
                            stats[name]['build'] = perf_counter() - start
                    comparisons = 0
                    for phase in range(5):
                        order = list(arms)
                        offset = (repeat + phase) % 4
                        for name in order[offset:] + order[:offset]:
                            state = states[name]
                            if phase < 4:
                                start = perf_counter()
                                train_events(state, [make(32 + phase)], opts)
                                stats[name]['train'] += perf_counter() - start
                            else:
                                state.events_by_id['0'].target = state.events_by_id['0'].actor
                                invalidate_primitive_grounding(state)
                            start = perf_counter()
                            for q in range(density):
                                query(state, checks[(q + phase) % len(checks)], name != 'scan')
                            elapsed = perf_counter() - start
                            stats[name]['query'] += elapsed
                            if phase == 4:
                                stats[name]['correction_query'] = elapsed
                        reference = [query(states['scan'], c, False) for c in checks]
                        for name in arms:
                            assert [query(states[name], c, name != 'scan') for c in checks] == reference
                            assert states[name].to_dict() == states['scan'].to_dict()
                        comparisons += len(checks)
                    with TemporaryDirectory() as directory:
                        saved = []
                        for name, state in states.items():
                            if name != 'scan':
                                index = state._primitive_grounding_index
                                stats[name]['heap'] = cache_heap(index)
                                stats[name]['fallback_entries'] = sum(e['lookup'] is None for e in index['entries'].values())
                                stats[name]['lookup_container_bytes'] = (None if arms[name] is None else
                                    sum(e['lookup_bytes'] for e in index['entries'].values()))
                                if name == 'budget':
                                    assert all(e['lookup_bytes'] <= arms[name] for e in index['entries'].values())
                            path = Path(directory) / name
                            save_state(state, path)
                            saved.append((path / 'state.json').read_bytes())
                            restored = load_state(path)
                            if name != 'scan':
                                build_primitive_grounding(restored, lookup_budget_bytes=arms[name])
                            assert [query(restored, c, name != 'scan') for c in checks] == reference
                            comparisons += len(checks)
                        assert len(set(saved)) == 1
                    rows.append(dict(world=world, width=width, density=density, repeat=repeat, stats=stats,
                        comparisons=comparisons, saved_bytes=len(saved[0]), mismatches=0))
    return dict(rows=rows, budget_bytes_per_primitive=8192, hash_seed=os.environ.get('PYTHONHASHSEED', 'random'),
                order_balanced=repetitions % 4 == 0)


if __name__ == '__main__':
    result = run()
    Path('docs/g3-grounding-budget-results-2026-10-12.json').write_text(json.dumps(result, indent=2) + '\n')
    print(len(result['rows']), sum(r['comparisons'] for r in result['rows']))
