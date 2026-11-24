from collections import Counter

from risa.engine.grounding_sampling import GroundingSampleSchedule


def test_skip_joint_inclusion_and_independent_replay():
    counts = Counter()
    for seed in range(1024):
        schedule = GroundingSampleSchedule(capacity=8, seed=seed, policy='skip')
        a, b = schedule.next_window(), schedule.next_window()
        for i in range(64):
            roles = [str(i % 3)]
            args = (roles, i, i if i % 2 else -i, roles)
            a.observe('p', *args)
            b.observe('other', *args)
            b.observe('p', *args)
            roles.clear()
        sample = a.samples()['p']
        assert sample == b.samples()['p']
        ids = [actor for _, actor, _, _ in sample]
        assert ids == sorted(set(ids)) and len(ids) == 8
        assert a.counts() == {'p': 64}
        for ar, i, target, tr in sample:
            assert ar == tr == (str(i % 3),)
            assert target == (i if i % 2 else -i)
        counts.update(ids)
    # Each position should occur ~128 times (binomial SD ~10.6).
    assert all(80 <= counts[i] <= 176 for i in range(64))


def test_skip_full_boundary_and_floating_endpoints():
    import math
    from unittest.mock import Mock
    from risa.engine.grounding_sampling import GroundingSampleWindow

    for capacity in (1, 64):
        window = GroundingSampleWindow(policy='skip', capacity=capacity)
        for i in range(capacity):
            window.observe('p', (), i, i, ())
        stream = window._streams['p']
        assert 'next' not in stream
        # An open draw can be extremely close to 1 (W would round to 1);
        # random() can also produce 0 and must be redrawn before taking log.
        rng = Mock()
        rng.random.side_effect = [0., math.nextafter(1., 0.), .5, .5, .5]
        rng.randrange.return_value = 0
        stream['rng'] = rng
        window.observe('p', (), 'new', 'new', ())
        assert stream['slots'][0][0] == capacity + 1
        assert stream['next'] > capacity + 1
