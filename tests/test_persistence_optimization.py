import json
from pathlib import Path
from unittest.mock import patch

import pytest

from risa.core.models import Event, Node, PredictionQuery
from risa.core.state import RisaState
from risa.engine import persistence
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import train_events
from experiments.references.persistence_before_20261007 import save_state as save_before


def example_state():
    state = RisaState()
    train_events(state, [Event('一', 1, 'robot', 'start', observed_effects=['ready']),
                         Event('二', 2, 'robot', 'finish', observed_effects=['done'])])
    state.graph.add_or_update_node(Node(id='state:unicode', kind='state', label='日本語 / 简体中文 / English',
                                       attributes={'key': [True, None, 3.5, 'line\nquote"']}))
    return state


def test_exact_bytes_and_predictions_match_baseline(tmp_path):
    state = example_state()
    source = state.to_dict()
    save_before(state, tmp_path / 'before')
    persistence.save_state(state, tmp_path / 'after', pretty=True)
    assert (tmp_path / 'after/state.json').read_bytes() == (tmp_path / 'before/state.json').read_bytes()
    assert state.to_dict() == source
    restored = persistence.load_state(tmp_path / 'after')
    for action in ('start', 'finish', 'unknown'):
        query = PredictionQuery(actor='robot', action=action)
        assert predict_next_effect(restored, query) == predict_next_effect(state, query)


@pytest.mark.skipif(json.encoder.c_make_encoder is None, reason='optional CPython encoder is unavailable')
def test_compact_save_uses_optimized_encoder_without_python_fragment_walk(tmp_path):
    state = RisaState()
    for i in range(500):
        state.graph.add_or_update_node(Node(id=f'n{i}', kind='entity', label='x' * 100))
    with patch.object(json.encoder, '_make_iterencode', side_effect=AssertionError('Python fragment walk')):
        persistence.save_state(state, tmp_path)
    assert len(persistence.load_state(tmp_path).graph.nodes_by_id) == 500


def test_invalid_snapshot_preserves_primary_and_backup(tmp_path):
    state = example_state()
    persistence.save_state(state, tmp_path)
    persistence.save_state(state, tmp_path)
    primary = (tmp_path / 'state.json').read_bytes()
    backup = (tmp_path / 'state.json.bak').read_bytes()
    state.target_role_readout_hops = 3
    with pytest.raises(ValueError):
        persistence.save_state(state, tmp_path)
    assert (tmp_path / 'state.json').read_bytes() == primary
    assert (tmp_path / 'state.json.bak').read_bytes() == backup
    assert not list(tmp_path.glob('*.tmp'))


def test_encoding_failure_cleans_stage_and_preserves_primary(tmp_path):
    state = example_state()
    persistence.save_state(state, tmp_path)
    primary = (tmp_path / 'state.json').read_bytes()
    state.graph.get_node('state:unicode').attributes['unsupported'] = object()
    with pytest.raises(TypeError):
        persistence.save_state(state, tmp_path)
    assert (tmp_path / 'state.json').read_bytes() == primary
    assert not list(tmp_path.glob('*.tmp'))


def test_replace_failure_preserves_primary_and_cleans_stage(tmp_path):
    state = example_state()
    persistence.save_state(state, tmp_path)
    primary = (tmp_path / 'state.json').read_bytes()
    original_replace = persistence.os.replace
    def fail_primary(source, target):
        if Path(target).name == 'state.json':
            raise OSError('injected replace failure')
        return original_replace(source, target)
    with patch.object(persistence.os, 'replace', side_effect=fail_primary):
        with pytest.raises(OSError):
            persistence.save_state(state, tmp_path)
    assert (tmp_path / 'state.json').read_bytes() == primary
    assert not list(tmp_path.glob('*.tmp'))


def test_fsync_failure_leaves_existing_files_unchanged(tmp_path):
    state = example_state()
    persistence.save_state(state, tmp_path)
    primary = (tmp_path / 'state.json').read_bytes()
    with patch.object(persistence.os, 'fsync', side_effect=OSError('injected fsync failure')):
        with pytest.raises(OSError):
            persistence.save_state(state, tmp_path)
    assert (tmp_path / 'state.json').read_bytes() == primary
    assert not list(tmp_path.glob('*.tmp'))


def test_corrupt_primary_does_not_overwrite_verified_backup(tmp_path):
    state = example_state()
    persistence.save_state(state, tmp_path)
    persistence.save_state(state, tmp_path)
    backup = (tmp_path / 'state.json.bak').read_bytes()
    (tmp_path / 'state.json').write_text('{broken')
    persistence.save_state(state, tmp_path)
    assert (tmp_path / 'state.json.bak').read_bytes() == backup
    (tmp_path / 'state.json').write_text('{broken again')
    assert persistence.load_state(tmp_path).events_by_id.keys() == state.events_by_id.keys()




def test_compact_default_preserves_all_json_values_and_is_smaller(tmp_path):
    state = example_state()
    persistence.save_state(state, tmp_path / 'compact')
    persistence.save_state(state, tmp_path / 'pretty', pretty=True)
    compact = (tmp_path / 'compact/state.json').read_text()
    pretty = (tmp_path / 'pretty/state.json').read_text()
    assert json.loads(compact) == json.loads(pretty)
    assert len(compact) < len(pretty)
    assert '\n' not in compact
    assert persistence.load_state(tmp_path / 'compact').to_dict() == persistence.load_state(tmp_path / 'pretty').to_dict()


def test_backup_keeps_legacy_pretty_bytes_when_new_primary_is_compact(tmp_path):
    state = example_state()
    save_before(state, tmp_path)
    previous = (tmp_path / 'state.json').read_bytes()
    persistence.save_state(state, tmp_path)
    assert (tmp_path / 'state.json.bak').read_bytes() == previous
    assert json.loads(previous) == json.loads((tmp_path / 'state.json').read_bytes())
