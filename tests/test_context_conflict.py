import copy
from dataclasses import replace

from experiments.g3_drift_preflight import _events, _probes
from risa.core.state import RisaState
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import TrainingOptions, train_events
from risa.evaluation.context_conflict import audit_context_conflict, predict_with_context_conflict_guard


def state_with(events):
    return train_events(RisaState(), events, TrainingOptions(enable_replay=False, enable_metabolism=False))


def test_conflicting_scopes_include_provenance_and_do_not_mutate_state():
    state = state_with(_events(11, 'A1', 6))
    query = replace(_probes(11, 'A', 3)[0].query, context_tags=['indoor', 'outdoor'])
    before = copy.deepcopy(state.to_dict())
    result, audit = predict_with_context_conflict_guard(state, query)
    assert audit['conflict']
    assert result.claim_status == 'abstained'
    assert len(result.evidence_event_ids) == 4
    assert state.to_dict() == before


def test_exact_context_and_more_specific_rule_override_subset_disagreement():
    events = _events(11, 'A1', 6)
    joint = replace(events[0], id='joint', context_tags=['indoor', 'outdoor'], observed_effects=['warm'])
    state = state_with(events + [joint])
    query = replace(_probes(11, 'A', 3)[0].query, context_tags=['indoor', 'outdoor'])
    assert predict_with_context_conflict_guard(state, query)[0] == predict_next_effect(state, query)
    query = replace(query, context_tags=query.context_tags + ['unseen'])
    assert not audit_context_conflict(state, query)['conflict']


def test_multi_effect_outcomes_and_unrelated_roles_are_not_false_conflicts():
    events = [replace(event, observed_effects=['warm', 'lit']) for event in _events(11, 'A1', 6)]
    other = replace(events[0], id='other-role', target_roles=['other'], observed_effects=['cold'])
    state = state_with(events + [other])
    query = replace(_probes(11, 'A', 3)[0].query, context_tags=['indoor', 'outdoor', 'unseen'])
    assert not audit_context_conflict(state, query)['conflict']


def test_exact_context_drift_is_left_to_existing_predictor():
    events = _events(11, 'A1', 6) + _events(11, 'B', 6)
    state = state_with(events)
    query = replace(_probes(11, 'A', 3)[0].query, context_tags=['indoor'])
    result, audit = predict_with_context_conflict_guard(state, query)
    assert audit['exact_context_present'] and not audit['conflict']
    assert result == predict_next_effect(state, query)


def test_index_matches_reference_after_replacement_ties_and_normalization():
    from risa.evaluation.context_conflict import ContextConflictIndex, conflict_audit_semantics
    # Use Event storage directly: this test verifies the audit, not training.
    state = RisaState()
    index = ContextConflictIndex()
    events = _events(11, 'A1', 6)
    events += [replace(events[0], id='tie', observed_effects=['cold']),
               replace(events[1], id='multi', context_tags=[], observed_effects=['warm', 'lit']),
               replace(events[0], id='replace', action='INSPECT', target_roles=['DEVICE', 'DEVICE'])]
    queries = [replace(_probes(11, 'A', 3)[0].query, context_tags=tags)
               for tags in ([], ['indoor'], ['indoor', 'outdoor'], ['sheltered', 'unseen'])]
    for event in events + [replace(events[-1], action='other', context_tags=['new']), events[0]]:
        state.events_by_id[event.id] = event
        index.observe(event)
        for query in queries:
            assert conflict_audit_semantics(index.audit(query)) == conflict_audit_semantics(audit_context_conflict(state, query))
    assert index.audit(queries[0])['event_reads'] == 0
    # Audit rows are copies, so callers cannot corrupt indexed provenance.
    result = index.audit(queries[1])
    result['most_specific_scopes'][0]['evidence_event_ids'].clear()
    assert index.audit(queries[1])['most_specific_scopes'][0]['evidence_event_ids']
