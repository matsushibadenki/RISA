import sys
import pytest
from risa.engine.grounding_sampling import GroundingSampleWindow, GroundingSampleSchedule, collector_bytes


def test_recent_collects_tail_and_new_keys_with_same_budget():
    frozen = GroundingSampleWindow(budget_bytes=4096)
    recent = GroundingSampleWindow(budget_bytes=4096, policy='recent')
    for i in range(120):
        key = 'early' if i < 60 else 'late'
        roles = ['actor', str(i % 3)]
        for window in (frozen, recent):
            window.observe(key, roles, str(i), str(i) if i % 2 else 'other', ['target'])
            assert collector_bytes(window._streams) <= 4096
        roles.clear()
    assert frozen.exhausted
    assert not recent.exhausted
    assert recent.samples()['late'][-1][1] == '119'
    assert all(args[0] and args[3] == ('target',) for args in recent.samples()['late'])
    assert not any(args[1] == '119' for stream in frozen.samples().values() for args in stream)


def test_recent_eviction_reentry_and_oversized_input_are_atomic():
    w = GroundingSampleWindow(capacity=2, policy='recent', budget_bytes=4096, max_streams=2)
    for key in ('a','b','a','c'):
        w.observe(key, (), key, key, ())
    assert list(w.samples()) == ['a','c']
    snapshot = w.samples(), w.counts()
    w.observe('a', (), 'x'*10000, 'x', ())
    assert (w.samples(), w.counts()) == snapshot
    w.observe('b', (), 'b', 'b', ())
    assert list(w.samples()) == ['c','b'] and w.counts()['b'] == 1
    assert collector_bytes(w._streams) <= w._retained_upper <= 4096


@pytest.mark.parametrize('capacity', [1, 8, 64])
def test_recent_shrinks_history_and_exports_copies(capacity):
    w = GroundingSampleWindow(capacity=capacity, policy='recent', budget_bytes=1800)
    for i in range(100):
        w.observe('key', ('r',), str(i)+'x'*100, str(i), ('r',))
        assert collector_bytes(w._streams) <= 1800
        assert w.samples()['key'][-1][2] == str(i)
    exported = w.samples()
    exported['key'].clear()
    assert w.samples()['key']
    assert all(s['rng'] is None for s in w._streams.values())


def test_recent_empty_budget_and_schedule():
    schedule = GroundingSampleSchedule(policy='recent', budget_bytes=sys.getsizeof({}))
    w = schedule.next_window()
    for i in range(20):
        w.observe(str(i), (), 'a', 'a', ())
    assert w.samples() == {} and not w.exhausted
    w = GroundingSampleWindow(policy='recent', max_streams=0)
    w.observe('a', (), 'a', 'a', ())
    assert not w.samples()


@pytest.mark.parametrize('budget', [1800, 4096, 32768])
def test_fast_recent_matches_original_at_every_update(budget):
    from random import Random
    rng = Random(71)
    fast = GroundingSampleWindow(policy='recent', budget_bytes=budget)
    old = GroundingSampleWindow(policy='recent', budget_bytes=budget)
    old._recent_fast = False
    for i in range(400):
        key = str(rng.randrange(16)) if i % 3 else 'hot'
        args = (('a', str(i % 3)), str(i % 5), 'x' * rng.choice([2, 90, 3000]), ('t',))
        fast.observe(key, *args)
        old.observe(key, *args)
        assert fast.samples() == old.samples()
        assert list(fast.samples()) == list(old.samples())
        assert fast.counts() == old.counts()
        assert collector_bytes(fast._streams) == collector_bytes(old._streams) <= budget


def test_fast_recent_reduces_accounting_calls():
    from unittest.mock import patch
    import risa.engine.grounding_sampling as sampling
    w = GroundingSampleWindow(policy='recent', budget_bytes=32768)
    w.observe('a', (), 'actor', 'target', ())
    with patch.object(sampling, 'collector_bytes', wraps=collector_bytes) as count:
        w.observe('a', (), 'actor', 'target', ())
        assert count.call_count == 1
