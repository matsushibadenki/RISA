"""Three-arm append/query comparison, including update costs and saved bytes."""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from experiments.compositional_grounding_costs import _query
from experiments.compositional_holdout import training_episode, heldout_cases
from risa.core.state import RisaState
from risa.engine.primitive_grounding import build_primitive_grounding, grounding_payload_bytes
from risa.engine.runtime import train_events, TrainingOptions
from risa.engine.persistence import save_state, load_state


def run(manifest):
    rows = []
    options = TrainingOptions(enable_metabolism=False, enable_replay=False)
    for seed in manifest['seeds']:
        for world in manifest['worlds']:
            events = [e for i in range(32) for e in training_episode(seed, world, i)]
            cases = heldout_cases(seed, world)
            for batch in manifest['event_batches']:
                for queries in manifest['queries_per_update']:
                    for repeat in range(manifest['repetitions']):
                        states = {name: RisaState() for name in ('scan', 'rebuild', 'incremental')}
                        build_primitive_grounding(states['incremental'], incremental=True)
                        stats = {name: dict(train_seconds=0., query_seconds=0., build_reads=0,
                            query_event_reads=0, update_reads=0) for name in states}
                        count = 0
                        for step, start in enumerate(range(0, 96, batch)):
                            order = list(states)
                            offset = (step + repeat) % 3
                            order = order[offset:] + order[:offset]
                            answers = {}
                            for name in order:
                                state = states[name]
                                begin = perf_counter()
                                train_events(state, events[start:start + batch], options)
                                stats[name]['train_seconds'] += perf_counter() - begin
                                answers[name] = []
                                begin = perf_counter()
                                for q in range(queries):
                                    ordinal = q if queries > 1 else step % 40
                                    detail = {}
                                    answers[name].append(_query(state, cases[ordinal // 2], bool(ordinal % 2), name != 'scan', detail))
                                    stats[name]['build_reads'] += detail['index_build_event_reads']
                                    stats[name]['query_event_reads'] += detail['grounding_event_reads']
                                stats[name]['query_seconds'] += perf_counter() - begin
                            if not answers['scan'] == answers['rebuild'] == answers['incremental']:
                                raise AssertionError('complete results differ')
                            payloads = {name: json.dumps(state.to_dict(), sort_keys=True) for name, state in states.items()}
                            if len(set(payloads.values())) != 1:
                                raise AssertionError('learning/persistence semantics differ')
                            count += queries
                        stats['incremental']['update_reads'] = states['incremental']._primitive_grounding_index['update_event_reads']
                        with TemporaryDirectory(prefix='risa-incremental-') as directory:
                            saved = []
                            for name, state in states.items():
                                path = Path(directory) / name
                                save_state(state, path)
                                saved.append((path / 'state.json').read_bytes())
                                restored = load_state(path)
                                if name == 'incremental':
                                    build_primitive_grounding(restored, incremental=True)
                                for case in cases:
                                    for enabled in (False, True):
                                        if _query(states['scan'], case, enabled, False) != _query(restored, case, enabled, name != 'scan'):
                                            raise AssertionError('reload differs')
                            if len(set(saved)) != 1:
                                raise AssertionError('actual saved bytes differ')
                        rows.append(dict(seed=seed, world=world, batch=batch, queries=queries, repeat=repeat,
                            complete_comparisons=count, mismatches=0, stats=stats,
                            saved_bytes=len(saved[0]), saved_sha256=hashlib.sha256(saved[0]).hexdigest(),
                            index_logical_bytes=grounding_payload_bytes(states['incremental']._primitive_grounding_index)))
    return dict(manifest=manifest, rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default='experiments/g3_incremental_grounding_manifest.json')
    parser.add_argument('--output', default='docs/g3-incremental-grounding-results-2026-10-11.json')
    args = parser.parse_args()
    result = run(json.loads(Path(args.manifest).read_text()))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'rows': len(result['rows']), 'comparisons': sum(r['complete_comparisons'] for r in result['rows'])}))
