"""Development-only context conflict intervention; no core inference changes."""
from __future__ import annotations

from collections import Counter

from risa.core.models import PredictionQuery, PredictionResult
from risa.core.state import RisaState
from risa.engine.graph_builder import normalize_label
from risa.engine.predictor import predict_next_effect


def audit_context_conflict(state: RisaState, query: PredictionQuery) -> dict:
    """Compare majority outcomes in equally specific observed context subsets.

    This explicit event scan is an evaluation reference, not an online index.
    Supplied target roles are used, matching the context-transfer fixture.
    Exact context evidence is left to the existing predictor, including drift.
    Multi-effect outcomes remain atomic rather than being treated as conflicts.
    """
    tags = frozenset(normalize_label(tag) for tag in query.context_tags)
    roles = {normalize_label(role) for role in query.target_roles}
    action = normalize_label(query.action)
    scopes = {}
    for event in state.events_by_id.values():
        context = frozenset(normalize_label(tag) for tag in event.context_tags)
        if (normalize_label(event.action) != action
                or {normalize_label(role) for role in event.target_roles} != roles
                or not context.issubset(tags)):
            continue
        scopes.setdefault(context, []).append(event)
    exact = tags in scopes
    specificity = max((len(scope) for scope in scopes), default=None)
    rows = []
    winners = set()
    for scope, events in sorted(scopes.items(), key=lambda item: sorted(item[0])):
        if len(scope) != specificity:
            continue
        counts = Counter(tuple(sorted(normalize_label(effect)
                                      for effect in event.observed_effects))
                         for event in events)
        maximum = max(counts.values())
        outcomes = sorted(outcome for outcome, count in counts.items() if count == maximum)
        winners.update(outcomes)
        rows.append({'context_tags': sorted(scope),
                     'majority_outcomes': [list(outcome) for outcome in outcomes],
                     'evidence_event_ids': sorted(event.id for event in events)})
    return {'conflict': not exact and len(winners) > 1,
            'exact_context_present': exact, 'matched_scope_count': len(scopes),
            'event_reads': len(state.events_by_id), 'most_specific_scopes': rows}


def predict_with_context_conflict_guard(
    state: RisaState, query: PredictionQuery,
) -> tuple[PredictionResult, dict]:
    """Opt-in development policy: abstain when subset scope evidence conflicts."""
    audit = audit_context_conflict(state, query)
    if not audit['conflict']:
        return predict_next_effect(state, query), audit
    evidence = sorted({event_id for row in audit['most_specific_scopes']
                       for event_id in row['evidence_event_ids']})
    return PredictionResult(
        predicted_effects=[], score=0.0, claim_status='abstained',
        evidence_event_ids=evidence,
        explanation='Abstained because equally specific observed context subsets disagree.',
        applicability_basis=['development_context_subset_conflict'],
    ), audit


class ContextConflictIndex:
    """Incrementally maintained evaluation index with full evidence provenance.

    The owner must observe each ingestion and replacement. This index does not
    attach to RisaState, and is not used by the default prediction path.
    """

    def __init__(self):
        self._events = {}
        self._scopes = {}

    def observe(self, event):
        action = normalize_label(event.action)
        roles = tuple(sorted({normalize_label(role) for role in event.target_roles}))
        context = frozenset(normalize_label(tag) for tag in event.context_tags)
        outcome = tuple(sorted(normalize_label(effect) for effect in event.observed_effects))
        record = ((action, roles), context, outcome)
        previous = self._events.get(event.id)
        if previous == record:
            return
        if previous is not None:
            old_key, old_context, old_outcome = previous
            scopes = self._scopes[old_key]
            outcomes = scopes[old_context]
            outcomes[old_outcome].remove(event.id)
            if not outcomes[old_outcome]:
                del outcomes[old_outcome]
            if not outcomes:
                del scopes[old_context]
            if not scopes:
                del self._scopes[old_key]
        self._events[event.id] = record
        self._scopes.setdefault((action, roles), {}).setdefault(context, {}).setdefault(outcome, set()).add(event.id)

    @classmethod
    def from_state(cls, state):
        index = cls()
        for event in state.events_by_id.values():
            index.observe(event)
        return index

    @property
    def scope_count(self):
        return sum(len(scopes) for scopes in self._scopes.values())

    def audit(self, query):
        tags = frozenset(normalize_label(tag) for tag in query.context_tags)
        key = (normalize_label(query.action),
               tuple(sorted({normalize_label(role) for role in query.target_roles})))
        scopes = self._scopes.get(key, {})
        matched = {context: outcomes for context, outcomes in scopes.items()
                   if context.issubset(tags)}
        specificity = max((len(context) for context in matched), default=None)
        rows, winners = [], set()
        for context, outcomes in sorted(matched.items(), key=lambda item: sorted(item[0])):
            if len(context) != specificity:
                continue
            maximum = max(len(ids) for ids in outcomes.values())
            majority = sorted(outcome for outcome, ids in outcomes.items() if len(ids) == maximum)
            winners.update(majority)
            rows.append({'context_tags': sorted(context),
                         'majority_outcomes': [list(outcome) for outcome in majority],
                         'evidence_event_ids': sorted(event_id for ids in outcomes.values() for event_id in ids)})
        return {'conflict': tags not in matched and len(winners) > 1,
                'exact_context_present': tags in matched,
                'matched_scope_count': len(matched), 'event_reads': 0,
                'scope_reads': len(scopes), 'most_specific_scopes': rows}


def conflict_audit_semantics(audit):
    """Exclude work counters when comparing complete decision and provenance."""
    return {key: value for key, value in audit.items()
            if key not in {'event_reads', 'scope_reads'}}
