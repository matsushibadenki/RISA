"""G3.4: unseen whole paths, with independently specified dependency probes.

This is a structural, supplied-contract development control inspired by Memory
Mosaics, not an implementation or reproduction of its neural architecture.
"""
import argparse
from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path

from risa.core.models import Event, StructuralPrimitive
from risa.core.state import RisaState
from risa.engine.composer import compose_to_effect, next_actions
from risa.engine.runtime import TrainingOptions, train_events
from risa.engine.transitions import apply_primitive_transition


def training_episode(seed, world, index):
    branch = ('a', 'b')[index % 2]
    self_bound = (index // 2) % 2 == 1
    actor = f'train:{world}:{seed}:{index}'
    common = dict(actor=actor, target=actor if self_bound else f'device:{actor}',
        actor_roles=['autonomous' if self_bound else 'operator'],
        target_roles=['self_unit' if self_bound else 'remote_unit'],
        source=f'source:{(index // 4) % 2}', episode_id=f'episode:{actor}',
        numeric_preconditions={'energy': 1}, state_variable_deltas={'energy': -1})
    rows = [
        (f'prepare_{branch}', ['connected', 'token'], ['token'], ['staged', f'ticket_{branch}'], ['connected', 'token']),
        ('bridge', ['staged'], ['staged'], ['ready'], ['connected', 'staged', f'ticket_{branch}']),
        (f'finish_{branch}', ['ready'] + ([f'ticket_{branch}'] if world == 'coupled' else []),
         ['ready'], [f'done_{branch}', 'receipt'], ['connected', 'ready', f'ticket_{branch}']),
    ]
    return [Event(id=f'{actor}:{step}', timestamp=index * 3 + step + 1,
        action=action, preconditions=required, consumed_states=consumed,
        observed_effects=effects, observed_states_before=before,
        before_state_observed=True, **common)
        for step, (action, required, consumed, effects, before) in enumerate(rows)]


def heldout_cases(seed, world):
    """Oracle labels are a fixed panel, never computed by either learner/kernel."""
    cases = []
    for family in ('distinct', 'self'):
        for start, finish in (('a', 'a'), ('b', 'b'), ('a', 'b'), ('b', 'a')):
            novel = start != finish
            cases.append(dict(category='unseen_path' if novel else 'seen_path',
                family=family, start=start, finish=finish,
                expected=(not novel or world == 'independent')))
        for category in ('crossed_roles', 'wrong_identity', 'missing_token',
                         'missing_connected', 'shared_resource', 'missing_actor_role'):
            cases.append(dict(category=category, family=family, start='a', finish='a', expected=False))
    for index, case in enumerate(cases):
        self_bound = case['family'] == 'self'
        actor = f'heldout:{world}:{seed}:{index}'
        equal = self_bound ^ (case['category'] == 'wrong_identity')
        target_self = self_bound ^ (case['category'] == 'crossed_roles')
        case.update(id=f'query:{actor}', actor=actor, target=actor if equal else f'device:{actor}',
            actor_roles=[] if case['category'] == 'missing_actor_role' else ['autonomous' if self_bound else 'operator'],
            target_roles=['self_unit' if target_self else 'remote_unit'],
            states=[v for v in ('connected', 'token') if case['category'] != f'missing_{v}'],
            energy=2 if case['category'] == 'shared_resource' else 3,
            start_action=f"prepare_{case['start']}", goal=f"done_{case['finish']}")
    return cases


@dataclass
class Contract:
    action: str
    actor_roles: tuple
    target_roles: tuple
    equal: bool
    primitive: StructuralPrimitive


class ContractModel:
    """Common bounded BFS for Event contracts and RISA's learned primitives.

    The RISA adapter is an ordinary-primitive-only evaluation view, not native
    candidate search. It uses same-Event joint witnesses, never role marginals.
    """
    def __init__(self, events, state=None):
        self.contracts = []
        self.successors = defaultdict(set)
        self.paths = set()
        episodes = defaultdict(list)
        for event in events:
            episodes[event.episode_id].append(event)
        for episode in episodes.values():
            actions = tuple(e.action for e in sorted(episode, key=lambda e: e.timestamp))
            self.paths.add(actions)
            for left, right in zip(actions, actions[1:]):
                self.successors[left].add(right)
        if state is None:
            for event in events:
                primitive = StructuralPrimitive(id='event-contract', relation_type='transition', role_signature='table',
                    input_state_conditions={f'state:{s}' for s in event.preconditions},
                    consumed_states={f'state:{s}' for s in event.consumed_states},
                    numeric_preconditions=dict(event.numeric_preconditions),
                    state_variable_deltas=dict(event.state_variable_deltas),
                    output_states=set(event.observed_effects))
                self.contracts.append(Contract(event.action, tuple(sorted(event.actor_roles)),
                    tuple(sorted(event.target_roles)), event.actor == event.target, primitive))
        else:
            self.successors = {action: {n for n, _ in next_actions(state, action, set())}
                               for action in {e.action for e in events}}
            for primitive in state.structural_primitives.values():
                if not primitive.adopted or primitive.superseded_by:
                    continue
                actions = {v.removeprefix('process:') for v in primitive.input_conditions if v.startswith('process:')}
                for eid in sorted(primitive.evidence_event_ids):
                    event = state.events_by_id[eid]
                    if event.action in actions:
                        self.contracts.append(Contract(event.action, tuple(sorted(event.actor_roles)),
                            tuple(sorted(event.target_roles)), event.actor == event.target, primitive))
        unique = {}
        for contract in self.contracts:
            # Evidence IDs are excluded only for Event-table deduplication;
            # learned-primitive payloads retain their real support metadata.
            key = json.dumps(asdict(contract), sort_keys=True, default=lambda v: sorted(v))
            unique[key] = contract
        self.contracts = list(unique.values())

    def payload_bytes(self, events):
        return len(json.dumps(dict(events=[asdict(e) for e in events],
            contracts=[asdict(c) for c in self.contracts], successors=self.successors, paths=sorted(self.paths)),
            sort_keys=True, default=lambda v: sorted(v)).encode())

    def solve(self, case, max_steps, ablation=None):
        work = dict(expanded_nodes=0, contract_scans=0, transition_checks=0)
        queue = deque([(case['start_action'], case['states'], {'energy': case['energy']}, ())])
        kernel_state = RisaState()
        while queue:
            action, states, variables, path = queue.popleft()
            work['expanded_nodes'] += 1
            action_contracts = [c for c in self.contracts if c.action == action]
            for contract in self.contracts:
                work['contract_scans'] += 1
                if contract.action != action:
                    continue
                witness = (tuple(sorted(case['actor_roles'])), tuple(sorted(case['target_roles'])), case['actor'] == case['target'])
                if ablation == 'role_marginals':
                    if not all(value in {getattr(c, field) for c in action_contracts}
                               for value, field in zip(witness, ('actor_roles', 'target_roles', 'equal'))):
                        continue
                elif witness != (contract.actor_roles, contract.target_roles, contract.equal):
                    continue
                primitive = contract.primitive
                if ablation == 'drop_ticket':
                    primitive = replace(primitive, input_state_conditions={s for s in primitive.input_state_conditions
                                                                          if not s.startswith('state:ticket_')})
                work['transition_checks'] += 1
                result = apply_primitive_transition(kernel_state, primitive, states,
                    {'energy': case['energy']} if ablation == 'reset_resource' else variables)
                if result is None:
                    continue
                next_path = (*path, action)
                if case['goal'] in primitive.produced_states:
                    if ablation != 'whole_path' or next_path in self.paths:
                        return True, work
                if len(next_path) < max_steps:
                    for successor in sorted(self.successors.get(action, ())):
                        queue.append((successor, result.resulting_states, result.resulting_variables, next_path))
        return False, work


def audit_split(events, cases):
    episodes = defaultdict(list)
    for e in events:
        episodes[e.episode_id].append(e)
    paths = {tuple(e.action for e in sorted(v, key=lambda e: e.timestamp)) for v in episodes.values()}
    pairs = {pair for path in paths for pair in zip(path, path[1:])}
    novel = [c for c in cases if c['category'] == 'unseen_path']
    query_paths = [(c['start_action'], 'bridge', f"finish_{c['finish']}") for c in novel]
    identities = {x for e in events for x in (e.actor, e.target)}
    test_ids = {x for c in cases for x in (c['actor'], c['target'])}
    result = dict(identity_overlap=len(identities & test_ids),
        id_overlap=len({e.id for e in events} & {c['id'] for c in cases}),
        heldout_path_overlap=sum(p in paths for p in query_paths),
        missing_local_pairs=sum(pair not in pairs for p in query_paths for pair in zip(p, p[1:])))
    if any(result.values()):
        raise AssertionError(f'invalid compositional split: {result}')
    return result


def run_experiment(manifest):
    if manifest['worlds'] != ['independent', 'coupled'] or manifest['max_steps'] != 3:
        raise ValueError('fixed two-world, three-step protocol required')
    checkpoints = manifest['training_episode_checkpoints']
    if not checkpoints or any(n <= 0 or n % 8 for n in checkpoints) or checkpoints != sorted(set(checkpoints)):
        raise ValueError('increasing checkpoints in complete eight-episode blocks required')
    rows = []
    for seed in manifest['seeds']:
        for world in manifest['worlds']:
            state, events, previous = RisaState(), [], 0
            cases = heldout_cases(seed, world)
            for checkpoint in checkpoints:
                added = [e for i in range(previous, checkpoint) for e in training_episode(seed, world, i)]
                events.extend(added)
                train_events(state, added, TrainingOptions(enable_metabolism=False, enable_replay=False))
                audit = audit_split(events, cases)
                snapshot = deepcopy(state.to_dict())
                restored = RisaState.from_dict(json.loads(json.dumps(snapshot)))
                table, learned = ContractModel(events), ContractModel(events, state)
                metrics, work, outputs = {}, {}, []
                reload_mismatches = 0
                for case in cases:
                    answers = {}
                    for name, enabled in (('risa_candidate_on', True), ('risa_candidate_off', False)):
                        kwargs = dict(actor=case['actor'], target=case['target'], actor_roles=case['actor_roles'],
                            target_roles=case['target_roles'], start_states=case['states'],
                            start_variables={'energy': case['energy']}, max_steps=3, enable_candidate_concepts=enabled)
                        diagnostic = {}
                        prediction = compose_to_effect(state, case['start_action'], case['goal'],
                                                       **kwargs, search_diagnostics=diagnostic)
                        reload_mismatches += prediction != compose_to_effect(restored, case['start_action'], case['goal'], **kwargs)
                        if prediction != compose_to_effect(state, case['start_action'], case['goal'], **kwargs):
                            raise AssertionError('instrumentation changed complete result')
                        answers[name] = bool(prediction.primitive_ids)
                        for key, value in diagnostic.items():
                            work.setdefault(name, {}).setdefault(key, 0)
                            work[name][key] += value
                    for name, model, ablation in (
                        ('factorized_table', table, None), ('risa_primitives_shared_bfs', learned, None),
                        ('whole_path_table', table, 'whole_path'), ('unsafe_role_marginals', table, 'role_marginals'),
                        ('unsafe_reset_resource', table, 'reset_resource'), ('unsafe_drop_ticket', table, 'drop_ticket')):
                        answers[name], diagnostic = model.solve(case, 3, ablation)
                        for key, value in diagnostic.items():
                            work.setdefault(name, {}).setdefault(key, 0)
                            work[name][key] += value
                    for name, accepted in answers.items():
                        for category in ('all', case['category']):
                            score = metrics.setdefault(name, {}).setdefault(category,
                                dict(cases=0, correct=0, positive_cases=0, positive_correct=0, false_accepts=0))
                            score['cases'] += 1
                            score['correct'] += accepted == case['expected']
                            score['positive_cases'] += case['expected']
                            score['positive_correct'] += accepted and case['expected']
                            score['false_accepts'] += accepted and not case['expected']
                    outputs.append(dict(case_id=case['id'], category=case['category'], expected=case['expected'], **answers))
                if snapshot != state.to_dict() or snapshot != restored.to_dict():
                    raise AssertionError('evaluation mutated learned state')
                rows.append(dict(seed=seed, world=world, events=len(events), split_audit=audit,
                    metrics=metrics, search_work=work, outputs=outputs, reload_mismatches=reload_mismatches,
                    risa_stored_bytes=len(json.dumps(snapshot, sort_keys=True).encode()),
                    table_stored_bytes=table.payload_bytes(events), table_contracts=len(table.contracts),
                    active_primitives=sum(p.adopted for p in state.structural_primitives.values()),
                    proposed_candidates=len(state.unnamed_concept_candidates),
                    adopted_candidates=sum(c.lifecycle_status == 'adopted' for c in state.unnamed_concept_candidates.values()),
                    adoption_labels=0,
                    candidate_advantage_pass=(metrics['risa_candidate_on']['all']['correct'] - metrics['factorized_table']['all']['correct']) / len(cases) >= manifest['minimum_advantage'],
                    risa_false_accept_gate=metrics['risa_candidate_on']['all']['false_accepts'] <= manifest['maximum_false_accepts']))
                previous = checkpoint
    return dict(benchmark_version=manifest['benchmark_version'], status='development_control_not_final',
        manifest=manifest, manifest_sha256=hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(), rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default='experiments/g3_compositional_holdout_manifest.json')
    parser.add_argument('--output', default='docs/g3-compositional-holdout-results-2026-10-10.json')
    args = parser.parse_args()
    result = run_experiment(json.loads(Path(args.manifest).read_text()))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps([dict(world=r['world'], events=r['events'], scores={k: v['all'] for k, v in r['metrics'].items()})
                      for r in result['rows'] if r['seed'] == result['manifest']['seeds'][0]], indent=2))
