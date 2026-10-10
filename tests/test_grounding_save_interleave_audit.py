import gc
import json
from pathlib import Path

import pytest

from experiments.grounding_save_interleave_audit import measured_save, run
from risa.core.state import RisaState
from risa.engine import persistence


def test_diagnostics_preserve_actual_save_and_restore_gc_on_failure(tmp_path, monkeypatch):
    state = RisaState()
    callbacks = list(gc.callbacks)
    enabled = gc.isenabled()
    before_to = RisaState.to_dict
    for mode in ('natural', 'collect_before', 'disabled'):
        row = measured_save(state, tmp_path / mode, mode)
        assert row['seconds'] > 0
        assert row['phases']['validate'] > 0
        assert persistence.load_state(tmp_path / mode).to_dict() == state.to_dict()
        assert gc.isenabled() == enabled and gc.callbacks == callbacks
        assert RisaState.to_dict is before_to
    def fail(*args):
        raise OSError('write failure')
    monkeypatch.setattr(persistence, '_atomic_write', fail)
    with pytest.raises(OSError, match='write failure'):
        measured_save(state, tmp_path / 'failure', 'disabled')
    assert gc.isenabled() == enabled and gc.callbacks == callbacks
    assert RisaState.to_dict is before_to


def test_balanced_order_interleaving_rebuild_and_backup_equivalence():
    manifest = json.loads(Path('experiments/g3_grounding_save_interleave_manifest.json').read_text())
    manifest.update(seeds=[701], save_repetitions=2, event_batches=[24], legacy_reproduction=False)
    result = run(manifest)
    assert len(result['save_rows']) == 48
    assert len(result['interleave_rows']) == 16
    for world in manifest['worlds']:
        for mode in manifest['gc_modes']:
            for storage in ('fresh', 'overwrite'):
                rows = [r for r in result['save_rows'] if r['world'] == world and r['gc_mode'] == mode and r['storage'] == storage]
                assert [r['arm'] for r in rows if r['position'] == 0].count('indexed') == 1
                if mode == 'disabled':
                    assert all(not r['gc'] for r in rows)
    for row in result['interleave_rows']:
        assert row['complete_result_mismatches'] == row['serialized_mismatches'] == 0
        assert row['saved_reload_checked']
        assert row['work']['indexed']['index_build_event_reads'] == row['events']
        assert row['work']['indexed']['grounding_event_reads'] == 0
        assert row['rebuild_seconds'] > 0


def test_reject_unbalanced_timing_manifest():
    with pytest.raises(ValueError, match='even'):
        run(dict(save_repetitions=3))
