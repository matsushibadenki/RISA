import copy
from dataclasses import replace
import json

import pytest

from experiments.g3_relational_return_cue import relational_world, with_relational_cue
from risa.core.models import PredictionQuery
from risa.core.state import RisaState
from risa.engine.runtime import train_events, TrainingOptions
from risa.evaluation.candidate_adoption import (
    ApplicabilityProbe, candidate_matches_probe, evaluate_candidate_on_probes,
)

OPTIONS = TrainingOptions(enable_metabolism=False, enable_replay=False)


def contextual_state(events):
    return train_events(RisaState(target_role_readout_hops=2,
                                  context_conditioned_role_refinement=True), events, OPTIONS)


def test_contextual_variation_keeps_counterexamples_and_refines_actual_collisions():
    a, b, _, _, _ = relational_world(11, 12, 6)
    legacy = train_events(RisaState(target_role_readout_hops=2), a, OPTIONS)
    assert not legacy.unnamed_concept_candidates
    state = contextual_state(a)
    assert len(state.unnamed_concept_candidates) == 6
    bases = [c for c in state.unnamed_concept_candidates.values() if c.derivation_type == 'base']
    assert all(c.counterexample_event_ids for c in bases)
    assert all(c.structural_schema['target_role_depth'] == 1 for c in bases)
    train_events(state, b, OPTIONS)
    assert len(state.unnamed_concept_candidates) == 12
    assert all(c.structural_schema['target_role_depth'] == 2 for c in state.unnamed_concept_candidates.values())
    assert all(c.lifecycle_status == 'proposed' for c in state.unnamed_concept_candidates.values())
    restored = RisaState.from_dict(json.loads(json.dumps(state.to_dict())))
    assert restored.context_conditioned_role_refinement
    assert {k: c.to_dict() for k, c in restored.unnamed_concept_candidates.items()} == {k: c.to_dict() for k, c in state.unnamed_concept_candidates.items()}


def test_unresolved_same_role_same_context_variation_does_not_generate_candidates():
    a, b, _, _, _ = relational_world(11, 12, 6)
    state = contextual_state(a + [with_relational_cue(event, 'A') for event in b])
    assert not state.unnamed_concept_candidates
    for bad in (1, None, 'true'):
        with pytest.raises(ValueError):
            RisaState(context_conditioned_role_refinement=bad)


def test_query_backed_applicability_does_not_ignore_role_or_action():
    a, b, _, ap, bp = relational_world(11, 12, 6)
    state = contextual_state(a + b)
    candidate = next(c for c in state.unnamed_concept_candidates.values()
                     if c.derivation_type == 'merged'
                     and c.structural_schema['effects'] == ['warm'])
    def panel_query(regime):
        query = replace(ap[0].query, context_tags=['indoor'])
        return with_relational_cue(query, regime)
    matches = []
    for regime in ('A', 'B'):
        query = panel_query(regime)
        probe = ApplicabilityProbe('q', 'episode', 'source', ('indoor',), True, query)
        matches.append(candidate_matches_probe(candidate, probe))
        assert not candidate_matches_probe(candidate, replace(probe, query=replace(query, action='unobserved')))
    assert sorted(matches) == [False, True]
    # Legacy context-only labels remain available, explicitly without role validation.
    assert candidate_matches_probe(candidate, ApplicabilityProbe('old', 'e', 's', ('indoor',), True))
    wrong = ApplicabilityProbe('bad', 'e', 's', ('outdoor',), False, panel_query('A'))
    before = copy.deepcopy(state.to_dict())
    with pytest.raises(ValueError, match='contexts differ'):
        evaluate_candidate_on_probes(state, candidate.id, [wrong, replace(wrong, id='bad2', episode_id='e2', source='s2')],
                                     partition='development', bootstrap_samples=100)
    assert state.to_dict() == before


def test_query_backed_merge_adoption_requires_role_evidence_and_survives_reload():
    from experiments.g3_context_conditioned_discovery import role_panel, post_b_adoption_diagnostic
    a, b, _, ap, bp = relational_world(11, 12, 6)
    state = contextual_state(a + b)
    before = copy.deepcopy(state.to_dict())
    diagnostic = post_b_adoption_diagnostic(state, 11, ap, bp, 200)
    assert diagnostic['status'] == 'adopted'
    assert diagnostic['labels_available'] == diagnostic['labels_consumed'] == 400
    assert diagnostic['final']['candidate_accuracy'] == 1
    assert diagnostic['nuisance_correct_before'] == 0
    assert diagnostic['nuisance_correct_after'] == 4
    assert state.to_dict() == before
    candidate = next(c for c in state.unnamed_concept_candidates.values()
                     if c.derivation_type == 'merged' and c.structural_schema['effects'] == ['warm'])
    # Identical labels without their observed role/action queries cannot
    # distinguish A and B. The evaluator must reject that unsupported gain.
    legacy_panel = [replace(p, query=None) for p in role_panel(11, 'legacy', 200, ap[0].query)]
    result = evaluate_candidate_on_probes(state, candidate.id, legacy_panel,
                                        partition='development', bootstrap_samples=200)
    assert result['status'] == 'rejected'
