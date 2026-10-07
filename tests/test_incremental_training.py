from copy import deepcopy
from dataclasses import replace

from risa.core.models import Edge, Event, Node, PredictionQuery
from risa.core.state import RisaState
from risa.engine.evidence import index_event_evidence
from risa.engine.metabolism import activate_nodes, decay_nodes, rebuild_metabolism_index, reward_concept_cell
from risa.engine.predictor import _coactivation_candidate_effects, predict_effects_for_validation, predict_next_effect
from risa.engine.runtime import TrainingOptions, train_events


def test_indexed_metabolism_matches_scan_with_reactivation_and_reload():
    indexed, scanned = RisaState(), RisaState()
    for state in (indexed, scanned):
        for i in range(150):
            state.graph.add_or_update_node(Node(id=f'entity:{i}', kind='entity', label=str(i),
                                               created_at=i // 3, energy=0.7, recent_activity=2.0))
            if i:
                state.graph.add_or_update_edge(Edge(source=f'entity:{i-1}', target=f'entity:{i}', relation_type='next'))
        rebuild_metabolism_index(state)
    for timestamp in range(1, 185):
        if timestamp in (80, 130):
            for state in (indexed, scanned):
                activate_nodes(state, ['entity:3', 'entity:140'], timestamp)
                reward_concept_cell(state, 'entity:4', 3, 2)
        decay_nodes(indexed, timestamp, indexed=True)
        decay_nodes(scanned, timestamp)
        assert indexed.to_dict() == scanned.to_dict()
        if timestamp == 100:
            indexed = RisaState.from_dict(indexed.to_dict())
            rebuild_metabolism_index(indexed)
    assert not indexed.graph.metabolism_pending


def test_negative_decay_uses_scan_and_updates_worklist():
    state = RisaState()
    state.graph.add_or_update_node(Node(id='state:x', kind='state', label='x', created_at=1,
                                       energy=0, recent_activity=0, dormant=True))
    rebuild_metabolism_index(state)
    decay_nodes(state, 2, decay_rate=-1, connection_cost_rate=0, indexed=True)
    assert state.graph.get_node('state:x').energy > 0
    assert 'state:x' in state.graph.metabolism_pending


def test_coactivation_ignores_unrelated_edges_and_matches_scan():
    state = RisaState()
    for edge in [Edge(source='entity:a', target='process:p', relation_type='co_activates_with'),
                 Edge(source='state:done', target='process:p', relation_type='co_activates_with'),
                 Edge(source='state:done', target='state:next', relation_type='co_activates_with'),
                 Edge(source='entity:a', target='state:wrong', relation_type='affects')]:
        state.graph.add_or_update_edge(edge)
    for i in range(1000):
        state.graph.add_or_update_edge(Edge(source='entity:a', target=f'event:{i}', relation_type='participates_in_event'))
    def scan(depth):
        frontier, visited, effects = {'entity:a'}, {'entity:a'}, set()
        for _ in range(depth):
            following = set()
            for edge in state.graph.edges_by_key.values():
                if edge.relation_type == 'co_activates_with':
                    if edge.source in frontier and edge.target not in visited:
                        following.add(edge.target)
                    if edge.target in frontier and edge.source not in visited:
                        following.add(edge.source)
            effects.update(n.removeprefix('state:') for n in following if n.startswith('state:'))
            visited.update(following)
            frontier = following
        return effects
    for depth in range(1, 5):
        assert _coactivation_candidate_effects(state, 'entity:a', depth) == scan(depth)
    state.graph.edges_by_key.pop(('state:done', 'process:p', 'co_activates_with'))
    assert _coactivation_candidate_effects(state, 'entity:a', 3) == scan(3)


def test_validation_effects_equal_public_predictions_across_drift_and_binding():
    state = RisaState()
    queries = [PredictionQuery(actor='robot', action='switch', target='new', target_roles=['device']),
               PredictionQuery(actor='other', action='switch', target='known', target_roles=['device']),
               PredictionQuery(actor='robot', action='unknown'),
               PredictionQuery(actor='robot', action='switch', target='new', target_roles=['wrong']),
               PredictionQuery(actor='robot', action='switch')]
    for i in range(24):
        for query in queries:
            for q in (query, replace(query, enable_change_adaptation=False)):
                assert predict_effects_for_validation(state, q) == predict_next_effect(state, q).predicted_effects
        event = Event(id=f'e{i}', timestamp=i + 1, actor='robot', action='switch', target='known',
                      target_roles=['device'], observed_effects=['a', 'joint'] if i < 8 or i >= 16 else ['b'])
        train_events(state, [event])


def test_evidence_membership_preserves_idempotence_and_replaced_lists():
    state = RisaState()
    event = Event(id='a', timestamp=1, actor='actor', action='go', before_state_observed=True)
    for _ in range(3):
        index_event_evidence(state, event)
    assert state.evidence_index['applicability:go'] == ['a']
    key = 'action:go:context:__no_context__'
    state.evidence_index[key] = ['b']
    index_event_evidence(state, event)
    assert state.evidence_index[key] == ['b', 'a']
    assert 'evidence_membership' not in state.to_dict()


def test_full_training_indexed_metabolism_equal_at_every_event():
    indexed, scanned = RisaState(), RisaState()
    for i in range(120):
        event = Event(id=f'e{i}', timestamp=i + 1, actor=f'actor-{i % 3}', action='go',
                      target=f'target-{i % 2}', target_roles=['device'],
                      observed_states_before=['ready'] if i % 5 else ['blocked'],
                      before_state_observed=True, transition_succeeded=bool(i % 5),
                      observed_effects=['done'] if i % 5 else [])
        train_events(indexed, [deepcopy(event)], TrainingOptions(replay_max_events=8))
        train_events(scanned, [deepcopy(event)], TrainingOptions(replay_max_events=8, enable_indexed_metabolism=False))
        assert indexed.to_dict() == scanned.to_dict()


def test_ingestion_without_learning_still_indexes_observed_applicability():
    from risa.engine.graph_builder import ingest_event
    state = RisaState()
    event = Event(id='observed', timestamp=1, actor='actor', action='Go',
                  before_state_observed=True, observed_states_before=['ready'])
    ingest_event(state, event)
    assert state.evidence_index['applicability:go'] == ['observed']
    index_event_evidence(state, event)
    assert state.evidence_index['applicability:go'] == ['observed']
