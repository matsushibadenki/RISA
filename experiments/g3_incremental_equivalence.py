"""Compare optimized training against a frozen local Git implementation."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from unittest.mock import patch

from risa.core.models import Event, PredictionQuery
from risa.core.state import RisaState
from risa.engine import predictor
from risa.engine.runtime import TrainingOptions, train_events

REFERENCE_REVISION = 'ce189ff6a6f6b031308ac7d0dafb500b583a74e7'


def load_reference(revision, name):
    source = subprocess.run(['git', 'show', f'{revision}:risa/engine/{name}.py'],
                            check=True, capture_output=True, text=True).stdout
    module_name = f'_risa_reference_{name}'
    module = ModuleType(module_name)
    sys.modules[module_name] = module
    exec(compile(source, f'{revision}:{name}.py', 'exec'), module.__dict__)
    return module


def run_equivalence(revision=REFERENCE_REVISION):
    full_revision = subprocess.run(['git', 'rev-parse', f'{revision}^{{commit}}'],
                                   check=True, capture_output=True, text=True).stdout.strip()
    references = {name: load_reference(full_revision, name)
                  for name in ('predictor', 'validator', 'learner', 'evidence', 'metabolism', 'runtime')}
    references['runtime'].learn_from_event = references['learner'].learn_from_event
    references['runtime'].validate_event_prediction = references['validator'].validate_event_prediction
    references['runtime'].decay_nodes = references['metabolism'].decay_nodes
    references['learner'].index_event_evidence = references['evidence'].index_event_evidence
    rows = []
    for readout_hops in (1, 2):
        optimized, reference = RisaState(target_role_readout_hops=readout_hops), RisaState(target_role_readout_hops=readout_hops)
        events = [Event(id=f'e-{i:03d}', timestamp=i + 1, actor=f'actor-{i % 3}', action='switch',
                        target=f'target-{i % 2}', target_roles=['device'], source=f'source-{i % 2}',
                        context_tags=[f'context-{i % 2}'], episode_id=f'episode-{i // 12}',
                        before_state_observed=True, observed_states_before=['ready'] if i % 7 else ['blocked'],
                        transition_succeeded=bool(i % 7),
                        observed_effects=(['a', 'joint'] if i < 36 or i >= 72 else ['b']) if i % 7 else [])
                  for i in range(108)]
        queries = [PredictionQuery(actor=actor, action=action, target=target, target_roles=[role], context_tags=context)
                   for actor, action, target, role, context in (
                       ('actor-0', 'switch', 'target-0', 'device', ['context-0']),
                       ('new', 'switch', 'unseen', 'device', ['context-0']),
                       ('new', 'switch', 'unseen', 'wrong', ['context-1']),
                       ('actor-1', 'switch', 'target-1', 'device', ['context-1']),
                       ('actor-0', 'unknown', None, 'device', []),
                       ('actor-0', 'switch', None, 'device', []))]
        for offset in range(0, len(events), 12):
            chunk = events[offset:offset + 12]
            train_events(optimized, deepcopy(chunk), TrainingOptions(replay_max_events=8))
            with ExitStack() as stack:
                stack.enter_context(patch.object(predictor, 'predict_next_effect', references['predictor'].predict_next_effect))
                stack.enter_context(patch.object(predictor, 'predict_effects_for_validation',
                    lambda state, query: references['predictor'].predict_next_effect(state, query).predicted_effects))
                references['runtime'].train_events(reference, deepcopy(chunk), references['runtime'].TrainingOptions(replay_max_events=8))
            optimized_predictions = [predictor.predict_next_effect(optimized, q).to_dict() for q in queries]
            reference_predictions = [references['predictor'].predict_next_effect(reference, q).to_dict() for q in queries]
            reload = RisaState.from_dict(optimized.to_dict())
            optimized_encoded = json.dumps(optimized.to_dict(), sort_keys=True)
            reference_encoded = json.dumps(reference.to_dict(), sort_keys=True)
            rows.append({'readout_hops': readout_hops, 'events': offset + len(chunk),
                         'query_count': len(queries), 'state_equal': optimized_encoded == reference_encoded,
                         'state_sha256': hashlib.sha256(optimized_encoded.encode()).hexdigest(),
                         'prediction_mismatches': sum(a != b for a, b in zip(optimized_predictions, reference_predictions)),
                         'reload_prediction_mismatches': sum(a != predictor.predict_next_effect(reload, q).to_dict()
                                                             for a, q in zip(optimized_predictions, queries))})
    return {'reference_revision': full_revision, 'rows': rows,
            'decision': 'exact' if all(r['state_equal'] and r['prediction_mismatches'] == 0 and
                                      r['reload_prediction_mismatches'] == 0 for r in rows) else 'mismatch',
            'note': 'Frozen prediction/validation/learning/evidence/metabolism/runtime functions; shared graph storage and discovery.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', default=REFERENCE_REVISION)
    parser.add_argument('--output', default='docs/g3-incremental-equivalence-results.json')
    args = parser.parse_args()
    result = run_equivalence(args.reference)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'output': args.output, 'decision': result['decision']}))
    if result['decision'] != 'exact':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
