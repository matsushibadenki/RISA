"""Paired diversity study: real learning, complete composition and persistence."""
import json
from contextlib import nullcontext
import os
import platform
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

from experiments import grounding_copy_sort_reference as legacy
from risa.core.models import Event
from risa.core.state import RisaState
from risa.engine import primitive_grounding as grounding
from risa.engine.composer import compose_to_effect
from risa.engine.runtime import train_events, TrainingOptions
from risa.engine.persistence import save_state, load_state


def event(i, diversity, shape):
    k = i % diversity
    return Event(id=str(i), timestamp=i, actor=f'a{i}',
        target=f'a{i}' if k % 2 else f'b{i}', action='go',
        actor_roles=[f'operator{k}' if shape == 'roles' else 'operator'],
        target_roles=[f'unit{k}'], observed_effects=['done'], source=str(i % 2))


def query(state, k, diversity, shape, indexed, variant, work=None):
    return compose_to_effect(state, 'go', 'done', actor='new-a',
        target='new-a' if (k % 2) ^ (variant == 2) else 'new-b',
        actor_roles=[f'operator{k}' if shape == 'roles' else 'operator'],
        target_roles=[f'unit{(k + (variant == 1)) % diversity}'],
        max_steps=1, use_grounding_index=indexed, enable_candidate_concepts=bool(variant % 2),
        search_diagnostics=work)


def run(diversities=(8, 64, 256), densities=(1, 4, 16), repetitions=4, updates=16):
    rows = []
    options = TrainingOptions(enable_metabolism=False, enable_replay=False, enable_adaptation=False)
    for shape in ('roles', 'shared_actor'):
        for diversity in diversities:
            base = RisaState()
            train_events(base, [event(i, diversity, shape) for i in range(diversity)], options)
            for density in densities:
                for repeat in range(repetitions):
                    states = {name: RisaState.from_dict(base.to_dict()) for name in ('scan', 'rebuild', 'legacy', 'incremental')}
                    cold = {}
                    for name in ('legacy', 'incremental'):
                        start = perf_counter()
                        (legacy if name == 'legacy' else grounding).build_primitive_grounding(states[name], incremental=True)
                        cold[name] = perf_counter() - start
                    stats = {name: dict(train=0., query=0., maintenance=0., reads=0, checks=0) for name in states}
                    for step in range(updates):
                        # Half the appends introduce new signatures; half repeat existing signatures.
                        e = event(diversity + step, diversity + updates if step % 2 else diversity, shape)
                        answers = {}
                        order = list(states)
                        offset = (repeat + step) % 4
                        for name in order[offset:] + order[:offset]:
                            state = states[name]
                            update = legacy.update_primitive_grounding if name == 'legacy' else grounding.update_primitive_grounding
                            def measured(*args, **kwargs):
                                start = perf_counter()
                                update(*args, **kwargs)
                                stats[name]['maintenance'] += perf_counter() - start
                            with patch.object(grounding, 'update_primitive_grounding', measured):
                                start = perf_counter()
                                train_events(state, [e], options)
                                stats[name]['train'] += perf_counter() - start
                            answers[name] = []
                            start = perf_counter()
                            for q in range(density):
                                work = {}
                                with patch.object(grounding, 'actor_matches', legacy.actor_matches) if name == 'legacy' else nullcontext():
                                    answers[name].append(query(state, (step + q) % diversity, diversity, shape, name != 'scan', (step + q) % 3, work))
                                stats[name]['reads'] += work['grounding_event_reads'] + work['index_build_event_reads']
                                stats[name]['checks'] += work['grounding_signature_checks']
                            stats[name]['query'] += perf_counter() - start
                        assert all(a == answers['scan'] for a in answers.values())
                        assert all(s.to_dict() == states['scan'].to_dict() for s in states.values())
                    with TemporaryDirectory() as directory:
                        saved = []
                        for name, state in states.items():
                            path = Path(directory) / name
                            save_state(state, path)
                            saved.append((path / 'state.json').read_bytes())
                            restored = load_state(path)
                            # All role labels with matched/crossed targets and identity reversal, including newly appended witnesses.
                            for k in range(diversity + updates):
                                for variant in range(3):
                                    assert query(states['scan'], k, diversity + updates, shape, False, variant) == query(restored, k, diversity + updates, shape, name != 'scan', variant)
                        assert len(set(saved)) == 1
                    rows.append(dict(shape=shape, diversity=diversity, density=density, repeat=repeat,
                        stats=stats, cold=cold, comparisons=updates*density + 4*(diversity+updates)*3,
                        saved_bytes=len(saved[0]), mismatches=0,
                        signatures=states['incremental']._primitive_grounding_index['signature_count'],
                        logical_bytes=grounding.grounding_payload_bytes(states['incremental']._primitive_grounding_index)))
    return dict(updates=updates, rows=rows, environment=dict(python=platform.python_version(), platform=platform.platform(), hash_seed=os.environ.get('PYTHONHASHSEED', 'random')), order_balanced=repetitions % 4 == 0)


if __name__ == '__main__':
    result = run()
    Path('docs/g3-grounding-diversity-results-2026-10-11.json').write_text(json.dumps(result, indent=2) + '\n')
    print(len(result['rows']), sum(r['comparisons'] for r in result['rows']))
