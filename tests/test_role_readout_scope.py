import copy
from dataclasses import replace
import json

import pytest

from experiments.g3_relational_return_cue import relational_world, with_relational_cue
from experiments.g3_drift_preflight import _events
from risa.core.state import RisaState
from risa.engine.persistence import save_state, load_state
from risa.engine.prediction_access import predict_next_effect_with_access
from risa.engine.prediction_indexes import rebuild_prediction_indexes
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import TrainingOptions, train_events


OPTIONS = TrainingOptions(enable_metabolism=False, enable_replay=False)


def test_two_hop_role_free_return_and_complete_persistence_access_equivalence(tmp_path):
    a1, b, _, ap, bp = relational_world(11, 12, 6)
    state = train_events(RisaState(target_role_readout_hops=2), a1, OPTIONS)
    train_events(state, b, OPTIONS)
    before = copy.deepcopy(state.to_dict())
    save_state(state, tmp_path)
    restored = load_state(tmp_path)
    assert restored.target_role_readout_hops == 2
    assert restored.action_target_role_context_effect_counts == state.action_target_role_context_effect_counts
    assert {k: sorted(v) for k, v in restored.evidence_index.items()} == {k: sorted(v) for k, v in state.evidence_index.items()}
    for probe in ap + bp:
        expected = predict_next_effect(state, probe.query)
        assert tuple(expected.predicted_effects) == probe.expected_effects
        assert predict_next_effect(restored, probe.query) == expected
        assert predict_next_effect_with_access(state, probe.query, 'full_scan')[0] == expected
    assert state.to_dict() == before
    # Explicit rebuilding does not change any field in PredictionResult.
    saved = [predict_next_effect(state, p.query) for p in ap + bp]
    rebuild_prediction_indexes(state)
    assert [predict_next_effect(state, p.query) for p in ap + bp] == saved


def test_missing_or_disabled_relations_do_not_fall_back_to_shallow_role():
    a1, b, _, ap, _ = relational_world(11, 12, 3)
    state = train_events(RisaState(target_role_readout_hops=2), a1 + b, OPTIONS)
    query = ap[0].query
    for missing in (replace(query, entity_relations=query.entity_relations[:1]),
                    replace(query, entity_relations=[]),
                    replace(query, enable_role_induction=False)):
        result = predict_next_effect(state, missing)
        assert result.claim_status == 'abstained'
        assert result.predicted_effects == []


def test_same_role_drift_still_adapts_and_known_entity_cannot_cross_roles():
    a1, b, _, ap, _ = relational_world(11, 12, 6)
    # Hold structural scope fixed: actual drift must remain possible.
    same_role_b = [with_relational_cue(event, 'A') for event in b]
    state = train_events(RisaState(target_role_readout_hops=2), a1 + same_role_b, OPTIONS)
    for probe in ap:
        expected = ('cold' if probe.expected_effects == ('warm',) else 'warm',)
        assert tuple(predict_next_effect(state, probe.query).predicted_effects) == expected

    # Reuse an entity in both regimes and prefer the query's matching scope.
    fixed_a = [replace(e, actor='shared', target='known') for e in _events(11, 'A1', 6) if e.context_tags == ['indoor']]
    fixed_a = [with_relational_cue(e, 'A') for e in fixed_a]
    fixed_b = [replace(e, actor='shared', target='known', context_tags=['indoor'], observed_effects=['cold'])
               for e in _events(11, 'B', 12)]
    fixed_b = [with_relational_cue(e, 'B') for e in fixed_b]
    state = train_events(RisaState(target_role_readout_hops=2), fixed_a + fixed_b, OPTIONS)
    query = with_relational_cue(replace(ap[0].query, actor='shared', target='known', context_tags=['indoor']), 'A')
    assert predict_next_effect(state, query).predicted_effects == ['warm']
    assert predict_next_effect(state, with_relational_cue(query, 'B')).predicted_effects == ['cold']
    assert predict_next_effect(state, replace(query, entity_relations=[])).claim_status == 'abstained'


def test_legacy_default_supplied_roles_and_invalid_depth():
    events = _events(11, 'A1', 6)
    legacy = train_events(RisaState(), events, OPTIONS)
    payload = json.loads(json.dumps(legacy.to_dict()))
    payload['schema_version'] = 4
    payload.pop('target_role_readout_hops')
    restored = RisaState.from_dict(payload)
    assert restored.target_role_readout_hops == 1
    assert restored.action_target_role_context_effect_counts == legacy.action_target_role_context_effect_counts
    supplied = train_events(RisaState(target_role_readout_hops=2), events, OPTIONS)
    assert supplied.action_target_role_context_effect_counts == legacy.action_target_role_context_effect_counts
    for bad in (0, 3, True, '2'):
        with pytest.raises(ValueError):
            RisaState(target_role_readout_hops=bad)
        with pytest.raises(ValueError):
            RisaState.from_dict({'schema_version': 5, 'target_role_readout_hops': bad})
