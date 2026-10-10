"""New joint-binding fixture against a learned transition table/simple search."""
import argparse
from collections import deque
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from risa.core.models import Event, StructuralPrimitive
from risa.core.state import RisaState
from risa.engine.runtime import TrainingOptions, train_events
from risa.engine.composer import compose_to_effect
from risa.engine.transitions import apply_primitive_transition


def training_episode(seed, index):
    self_binding = index % 2 == 1
    actor = f'train-agent:{seed}:{index}'
    target = actor if self_binding else f'train-device:{seed}:{index}'
    common = dict(actor=actor, target=target, actor_roles=['autonomous' if self_binding else 'operator'],
                  target_roles=['self_unit' if self_binding else 'remote_unit'],
                  episode_id=f'train-episode:{seed}:{index}', source=f'train-source:{(index // 2) % 2}')
    return [Event(id=f'prime:{seed}:{index}', timestamp=2 * index + 1, action='prime',
                  preconditions=['connected'], numeric_preconditions={'energy': 2},
                  state_variable_deltas={'energy': -1}, observed_effects=['ready'], **common),
            Event(id=f'execute:{seed}:{index}', timestamp=2 * index + 2, action='execute',
                  preconditions=['ready'], consumed_states=['ready'], numeric_preconditions={'energy': 1},
                  state_variable_deltas={'energy': -1}, observed_effects=['done'],
                  observed_states_before=['ready'], before_state_observed=True, **common)]


def heldout_cases(seed, partition, count):
    # Truth labels are fixed here; neither learner nor table defines the oracle.
    variants = [(['operator'], ['remote_unit'], False, ['connected'], 2, True),
                (['autonomous'], ['self_unit'], True, ['connected'], 2, True),
                (['operator'], ['remote_unit'], True, ['connected'], 2, False),
                (['autonomous'], ['self_unit'], False, ['connected'], 2, False),
                (['operator'], ['self_unit'], False, ['connected'], 2, False),
                (['autonomous'], ['remote_unit'], True, ['connected'], 2, False),
                ([], ['remote_unit'], False, ['connected'], 2, False),
                (['observer'], ['remote_unit'], False, ['connected'], 2, False),
                (['operator'], ['remote_unit'], False, [], 2, False),
                (['operator'], ['remote_unit'], False, ['connected'], 1, False)]
    if count < 10 or count % 10:
        raise ValueError('balanced ten-case panel required')
    rows = []
    for i in range(count):
        ar, tr, equal, states, energy, expected = variants[i % 10]
        actor = f'{partition}:agent:{seed}:{i}'
        rows.append(dict(id=f'{partition}:case:{seed}:{i}', actor=actor,
            target=actor if equal else f'{partition}:device:{seed}:{i}', actor_roles=ar,
            target_roles=tr, states=states, energy=energy, expected=expected))
    return rows


class GroundedContractTable:
    """Learn role-pair/equality transition contracts and episode successor links."""
    def __init__(self, events):
        self.events = [asdict(e) for e in events]
        self.contracts, self.next_actions = {}, {}
        episodes = {}
        for e in events:
            signature = dict(action=e.action, actor_roles=sorted(e.actor_roles), target_roles=sorted(e.target_roles),
                equal=e.actor == e.target, states=sorted(e.preconditions), numeric=e.numeric_preconditions,
                deltas=e.state_variable_deltas, consumed=sorted(e.consumed_states), effects=sorted(e.observed_effects))
            key = json.dumps(signature, sort_keys=True)
            self.contracts.setdefault(key, signature)
            episodes.setdefault(e.episode_id, []).append(e)
        for episode in episodes.values():
            ordered = sorted(episode, key=lambda e: e.timestamp)
            for first, second in zip(ordered, ordered[1:]):
                self.next_actions.setdefault(first.action, set()).add(second.action)

    def solve(self, case, max_steps, diagnostics=None):
        if diagnostics is not None:
            diagnostics.clear()
            diagnostics.update(expanded_nodes=0, contract_scan_count=0, transition_checks=0)
        queue = deque([('prime', case['states'], {'energy': case['energy']}, 0)])
        expanded = 0
        kernel_state = RisaState()
        while queue:
            action, states, variables, depth = queue.popleft()
            expanded += 1
            if diagnostics is not None:
                diagnostics['expanded_nodes'] += 1
            for signature in self.contracts.values():
                if diagnostics is not None:
                    diagnostics['contract_scan_count'] += 1
                if (signature['action'] != action or signature['actor_roles'] != sorted(case['actor_roles'])
                        or signature['target_roles'] != sorted(case['target_roles'])
                        or signature['equal'] != (case['actor'] == case['target'])):
                    continue
                primitive = StructuralPrimitive(id='table-transition', relation_type='transition', role_signature='table',
                    input_state_conditions={f'state:{v}' for v in signature['states']},
                    numeric_preconditions=signature['numeric'], state_variable_deltas=signature['deltas'],
                    consumed_states={f'state:{v}' for v in signature['consumed']}, output_states=set(signature['effects']))
                if diagnostics is not None:
                    diagnostics['transition_checks'] += 1
                result = apply_primitive_transition(kernel_state, primitive, states, variables)
                if result is None:
                    continue
                if 'done' in signature['effects']:
                    return True, expanded
                if depth + 1 < max_steps:
                    for successor in sorted(self.next_actions.get(action, [])):
                        queue.append((successor, result.resulting_states, result.resulting_variables, depth + 1))
        return False, expanded

    def stored_bytes(self):
        return len(json.dumps(dict(primary_events=self.events, contracts=list(self.contracts.values()),
            next_actions={k: sorted(v) for k, v in self.next_actions.items()}), sort_keys=True).encode())


def run_quality(manifest):
    if manifest['training_families'] != ['distinct', 'self']:
        raise ValueError('fixed training families required')
    rows, overlap_audits = [], []
    for seed in manifest['seeds']:
        cases = heldout_cases(seed, manifest['heldout_partition'], manifest['cases_per_seed'])
        state, events = RisaState(), []
        previous = 0
        for checkpoint in manifest['training_episode_checkpoints']:
            if checkpoint <= previous:
                raise ValueError('strictly increasing episode checkpoints required')
            added = [e for i in range(previous, checkpoint) for e in training_episode(seed, i)]
            events.extend(added)
            train_events(state, added, TrainingOptions(enable_metabolism=False, enable_replay=False))
            table = GroundedContractTable(events)
            training_identities = {identity for e in events for identity in (e.actor, e.target) if identity is not None}
            heldout_identities = {identity for c in cases for identity in (c['actor'], c['target'])}
            overlap_audits.append(dict(seed=seed, events=len(events),
                identity_overlap=len(training_identities & heldout_identities),
                event_case_id_overlap=len({e.id for e in events} & {c['id'] for c in cases})))
            if overlap_audits[-1]['identity_overlap'] or overlap_audits[-1]['event_case_id_overlap']:
                raise AssertionError('held-out leakage')
            snapshot = state.to_dict()
            restored = RisaState.from_dict(json.loads(json.dumps(snapshot)))
            metrics = {m: dict(correct=0, false_accepts=0, positive_correct=0) for m in ('candidate_on', 'candidate_off', 'table_simple_search')}
            outputs, reload_mismatches, expanded = [], 0, 0
            search_work = {name: {} for name in ('candidate_on', 'candidate_off', 'table_simple_search')}
            for case in cases:
                outcomes = {}
                for name, enabled in [('candidate_on', True), ('candidate_off', False)]:
                    kwargs = dict(actor=case['actor'], target=case['target'], actor_roles=case['actor_roles'],
                        target_roles=case['target_roles'], start_states=case['states'], start_variables={'energy': case['energy']},
                        max_steps=manifest['max_steps'], enable_candidate_concepts=enabled)
                    diagnostic = {}
                    result = compose_to_effect(state, 'prime', 'done', **kwargs, search_diagnostics=diagnostic)
                    if result != compose_to_effect(state, 'prime', 'done', **kwargs):
                        raise AssertionError('instrumentation changed CompositionResult')
                    for key, value in diagnostic.items():
                        search_work[name][key] = search_work[name].get(key, 0) + value
                    reload_mismatches += result != compose_to_effect(restored, 'prime', 'done', **kwargs)
                    outcomes[name] = bool(result.primitive_ids)
                table_diagnostic = {}
                outcomes['table_simple_search'], work = table.solve(case, manifest['max_steps'], table_diagnostic)
                for key, value in table_diagnostic.items():
                    search_work['table_simple_search'][key] = search_work['table_simple_search'].get(key, 0) + value
                expanded += work
                for name, success in outcomes.items():
                    metrics[name]['correct'] += success == case['expected']
                    metrics[name]['false_accepts'] += success and not case['expected']
                    metrics[name]['positive_correct'] += success and case['expected']
                outputs.append(dict(case_id=case['id'], expected=case['expected'], **outcomes))
            if snapshot != state.to_dict():
                raise AssertionError('held-out scoring mutated learned state')
            rows.append(dict(seed=seed, events=len(events), cases=len(cases), metrics=metrics, outputs=outputs,
                positive_cases=sum(c['expected'] for c in cases), reload_mismatches=reload_mismatches,
                risa_stored_bytes=len(json.dumps(snapshot, sort_keys=True).encode()), table_stored_bytes=table.stored_bytes(),
                active_primitives=sum(p.adopted for p in state.structural_primitives.values()),
                candidates=len(state.unnamed_concept_candidates),
                adopted_candidates=sum(c.lifecycle_status == 'adopted' for c in state.unnamed_concept_candidates.values()),
                table_contracts=len(table.contracts), table_expanded_nodes=expanded, search_work=search_work,
                candidate_advantage_pass=(metrics['candidate_on']['correct'] - metrics['table_simple_search']['correct']) / len(cases) >= manifest['minimum_advantage'],
                false_accept_gate=all(v['false_accepts'] <= manifest['maximum_false_accepts'] for v in metrics.values())))
            previous = checkpoint
    return dict(benchmark_version=manifest['benchmark_version'],
        manifest_sha256=hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        status='independent_fixture_development_control', rows=rows, search_work_version='composition-work-v1',
        overlap_audits=overlap_audits)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='docs/g3-independent-quality-results-2026-10-10.json')
    args = parser.parse_args()
    manifest = json.loads(Path('experiments/g3_independent_quality_manifest.json').read_text())
    result = run_quality(manifest)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'rows': len(result['rows']), 'metrics': result['rows'][-1]['metrics']}))
