"""Compare scan, linear summaries and joint role/identity lookup, with owned-cache costs."""
from contextlib import ExitStack, contextmanager
import json
import os
import platform
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
import tracemalloc
from unittest.mock import patch

from experiments import grounding_linear_reference as linear
from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine import primitive_grounding as grounding
from risa.engine.composer import compose_to_effect
from risa.engine.runtime import train_events, TrainingOptions
from risa.engine.persistence import save_state, load_state


@contextmanager
def arm(name):
    with ExitStack() as stack:
        if name == 'linear':
            for function in ('build_primitive_grounding', 'update_primitive_grounding', 'actor_matches'):
                stack.enter_context(patch.object(grounding, function, getattr(linear, function)))
        yield


def cache_heap(index):
    """Unique reachable Python object bytes, excluding references to source primitives.

    Not RSS or retained-exclusive heap: strings shared with source may be counted.
    """
    seen = set()
    def visit(value):
        if id(value) in seen:
            return 0
        seen.add(id(value))
        size = sys.getsizeof(value)
        if isinstance(value, dict):
            size += sum(visit(k) + visit(v) for k, v in value.items())
        elif isinstance(value, (tuple, list, set, frozenset)):
            size += sum(visit(v) for v in value)
        return size
    return visit({k: v for k, v in index.items() if k != 'references'})


def event(i, k, width):
    return Event(id=str(i), timestamp=i, actor=f'a{i}', target=f'a{i}' if k % 2 else f'b{i}',
        action='go', actor_roles=[f'operator{j}' for j in range(width)],
        target_roles=[f'unit{k}-{j}' for j in range(width)], observed_effects=['done'], source=str(i % 2))


def cases(diversity, width, latest):
    result = []
    for k in (0, diversity - 1, latest):
        ar = [f'operator{j}' for j in range(width)]
        tr = [f'unit{k}-{j}' for j in range(width)]
        same = 'new-a' if k % 2 else 'new-b'
        variants = [
            (ar, tr, 'new-a', same),
            (ar, tr, 'new-a', 'new-b' if k % 2 else 'new-a'),
            (['absent'] + ar[-1:], ['absent'] + tr[-1:], 'new-a', same),
            (ar, ['absent'], 'new-a', same),
            (['absent'], tr, 'new-a', same),
            (ar, tr, None, None),
            (ar, [], 'new-a', None),
            ([], [], None, None),
        ]
        for args in variants:
            for candidate in (False, True):
                result.append((args, candidate))
    return result


def query(state, case, indexed, work=None):
    (ar, tr, actor, target), candidate = case
    return compose_to_effect(state, 'go', 'done', actor_roles=ar, target_roles=tr,
        actor=actor, target=target, max_steps=1, enable_candidate_concepts=candidate,
        use_grounding_index=indexed, search_diagnostics=work)


def run(diversities=(8, 64, 256), widths=(1, 4), repetitions=3, updates=8):
    options = TrainingOptions(enable_metabolism=False, enable_replay=False, enable_adaptation=False)
    rows = []
    for diversity in diversities:
        for width in widths:
            base = RisaState()
            train_events(base, [event(i, i, width) for i in range(diversity)], options)
            for repeat in range(repetitions):
                states = {name: RisaState.from_dict(base.to_dict()) for name in ('scan', 'linear', 'lookup')}
                stats = {name: dict(build=0., train=0., update=0., query=0., reads=0, checks=0, probes=0,
                    heap_before=0, heap_after=0, build_peak=0, build_retained=0, update_reads=0) for name in states}
                order = list(states)
                order = order[repeat % 3:] + order[:repeat % 3]
                for name in order:
                    if name == 'scan':
                        continue
                    with arm(name):
                        start = perf_counter()
                        index = grounding.build_primitive_grounding(states[name], incremental=True)
                        stats[name]['build'] = perf_counter() - start
                        stats[name]['heap_before'] = cache_heap(index)
                        # Separate untimed allocation pass; do not trace the timing run.
                        memory_state = RisaState.from_dict(base.to_dict())
                        tracemalloc.start()
                        grounding.build_primitive_grounding(memory_state, incremental=True)
                        retained, peak = tracemalloc.get_traced_memory()
                        tracemalloc.stop()
                        stats[name].update(build_peak=peak, build_retained=retained)
                        del memory_state
                comparisons = 0
                for step in range(updates):
                    k = diversity + step if step % 2 else step % diversity
                    e = event(diversity + step, k, width)
                    panel = cases(diversity, width, k)
                    answers = {}
                    order = list(states)
                    offset = (repeat + step) % 3
                    for name in order[offset:] + order[:offset]:
                        with arm(name):
                            update = grounding.update_primitive_grounding
                            def measured(*args, **kwargs):
                                start = perf_counter()
                                update(*args, **kwargs)
                                stats[name]['update'] += perf_counter() - start
                            with patch.object(grounding, 'update_primitive_grounding', measured):
                                start = perf_counter()
                                train_events(states[name], [e], options)
                                stats[name]['train'] += perf_counter() - start
                            answers[name] = []
                            start = perf_counter()
                            for case in panel:
                                work = {}
                                answers[name].append(query(states[name], case, name != 'scan', work))
                                stats[name]['reads'] += work['grounding_event_reads']
                                stats[name]['checks'] += work['grounding_signature_checks']
                                stats[name]['probes'] += work.get('grounding_lookup_probes', 0)
                            stats[name]['query'] += perf_counter() - start
                    assert answers['scan'] == answers['linear'] == answers['lookup']
                    assert all(state.to_dict() == states['scan'].to_dict() for state in states.values())
                    comparisons += len(panel)
                with TemporaryDirectory() as directory:
                    saved = []
                    for name, state in states.items():
                        if name != 'scan':
                            index = state._primitive_grounding_index
                            stats[name]['heap_after'] = cache_heap(index)
                            stats[name]['update_reads'] = index['update_event_reads']
                        path = Path(directory) / name
                        save_state(state, path)
                        saved.append((path / 'state.json').read_bytes())
                        restored = load_state(path)
                        with arm(name):
                            for case in panel:
                                assert query(states['scan'], case, False) == query(restored, case, name != 'scan')
                                comparisons += 1
                    assert len(set(saved)) == 1
                # Compare canonical witness summaries independently of derived lookup layout.
                li, new = (states[name]._primitive_grounding_index for name in ('linear', 'lookup'))
                assert grounding.grounding_payload_bytes(li) == grounding.grounding_payload_bytes(new)
                assert all(li['entries'][key]['rows'] == entry['rows'] for key, entry in new['entries'].items())
                rows.append(dict(diversity=diversity, width=width, repeat=repeat, stats=stats,
                    comparisons=comparisons, saved_bytes=len(saved[0]), mismatches=0))
    return dict(rows=rows, updates=updates, queries_per_update=48, order_balanced=repetitions % 3 == 0,
        environment=dict(python=platform.python_version(), platform=platform.platform(),
                         hash_seed=os.environ.get('PYTHONHASHSEED', 'random')))


if __name__ == '__main__':
    result = run()
    Path('docs/g3-grounding-lookup-results-2026-10-11.json').write_text(json.dumps(result, indent=2) + '\n')
    print(len(result['rows']), sum(row['comparisons'] for row in result['rows']))
