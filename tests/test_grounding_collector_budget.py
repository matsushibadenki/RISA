import hashlib
import random
import sys

import pytest

from risa.engine.grounding_sampling import GroundingSampleWindow, collector_bytes


class EagerWindow(GroundingSampleWindow):
    """Previous RNG allocation timing, with the same random stream."""
    def _observe(self, key, *args):
        super()._observe(key, *args)
        stream = self._streams[key]
        if stream['seen'] == 1 and self.policy != 'prefix':
            seed = int.from_bytes(hashlib.sha256(f'{self.seed}\0{key}'.encode()).digest(), 'big')
            stream['rng'] = random.Random(seed)


@pytest.mark.parametrize('policy', ['reservoir', 'skip', 'prefix'])
def test_lazy_rng_preserves_samples_and_reduces_short_stream_memory(policy):
    lazy, eager = GroundingSampleWindow(policy=policy), EagerWindow(policy=policy)
    for i in range(64):
        for key in ('a', 'b'):
            args = (('r', str(i)), i, i if i % 2 else -i, ('t',))
            lazy.observe(key, *args)
            eager.observe(key, *args)
        assert lazy.samples() == eager.samples()
        assert lazy.counts() == eager.counts()
        if i == 7 and policy != 'prefix':
            assert all(s['rng'] is None for s in lazy._streams.values())
            assert collector_bytes(lazy._streams) < collector_bytes(eager._streams)


@pytest.mark.parametrize('policy', ['reservoir', 'skip', 'prefix'])
def test_budget_atomic_freeze_and_joint_bindings(policy):
    window = GroundingSampleWindow(capacity=1, policy=policy, budget_bytes=1800)
    window.observe('p', ['a'], 'actor', 'actor', ['b'])
    previous = window.samples(), window.counts()
    for i in range(30):
        before = window.samples(), window.counts()
        window.observe('p' + str(i), ['a'], 'x' * 3000, 'target', ['b'])
        assert collector_bytes(window._streams) <= 1800
        assert (window.samples(), window.counts()) == before == previous
    assert window.exhausted
    assert window.samples()['p'] == [(('a',), 'actor', 'actor', ('b',))]


def test_rng_growth_rollback_and_empty_budget():
    window = GroundingSampleWindow(capacity=1, budget_bytes=1800)
    window.observe('p', (), 1, 1, ())
    window.observe('p', (), 2, 2, ())
    assert window.exhausted and window.counts() == {'p': 1}
    assert window._streams['p']['rng'] is None
    empty = GroundingSampleWindow(budget_bytes=sys.getsizeof({}))
    empty.observe('p', (), 1, 1, ())
    assert empty.exhausted and empty.samples() == {}
    for bad in (True, -1, 0, 1.5):
        with pytest.raises(ValueError):
            GroundingSampleWindow(budget_bytes=bad)
    capped = GroundingSampleWindow(max_streams=1)
    for key in ('a', 'b', 'a'):
        capped.observe(key, (), key, key, ())
    assert capped.counts() == {'a': 2}


def test_large_budget_preserves_full_stream_and_schedule_resets_exhaustion():
    from risa.engine.grounding_sampling import GroundingSampleSchedule
    for policy in ('reservoir', 'skip'):
        plain = GroundingSampleWindow(policy=policy)
        capped = GroundingSampleWindow(policy=policy, budget_bytes=100000)
        for i in range(100):
            for window in (plain, capped):
                window.observe('p', ('a',), str(i), str(i), ('t',))
            assert capped.samples() == plain.samples()
            assert capped.counts() == plain.counts()
            assert not capped.exhausted
    schedule = GroundingSampleSchedule(budget_bytes=sys.getsizeof({}), interval=2)
    first = schedule.next_window()
    first.observe('p', (), 1, 1, ())
    assert first.exhausted
    assert schedule.next_window() is None
    assert not schedule.next_window().exhausted


@pytest.mark.parametrize('policy', ['reservoir', 'skip', 'prefix'])
def test_conservative_headroom_matches_full_accounting(policy):
    # Disable headroom on the reference; it executes the original audited path.
    for budget in (1800, 4096, 32768, 100000):
        fast = GroundingSampleWindow(policy=policy, budget_bytes=budget)
        reference = GroundingSampleWindow(policy=policy, budget_bytes=budget)
        for i in range(300):
            key = str(i % 4)
            roles = ('shared', str(i % 9))
            args = (roles, 'x' * (i % 97), 'x' * (i % 97), roles)
            reference._use_headroom = False
            reference.observe(key, *args)
            fast.observe(key, *args)
            assert fast.samples() == reference.samples()
            assert fast.counts() == reference.counts()
            assert fast.exhausted == reference.exhausted
            assert collector_bytes(fast._streams) <= fast._retained_upper <= budget


def test_headroom_avoids_trial_copies_and_bounds_counter_only_updates():
    from unittest.mock import patch
    import risa.engine.grounding_sampling as sampling
    window = GroundingSampleWindow(capacity=1, policy='prefix', budget_bytes=32768)
    window.observe('p', ('role',), 'actor', 'target', ())
    with patch.object(sampling.copy, 'deepcopy', wraps=sampling.copy.deepcopy) as copied:
        for _ in range(500):
            window.observe('p', (), 'unused', 'unused', ())
            assert collector_bytes(window._streams) <= window._retained_upper <= 32768
        assert copied.call_count == 0
    assert window.counts() == {'p': 501}
