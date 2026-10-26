"""Explicit, per-primitive bounded sampling of complete binding witnesses."""
import hashlib
import random


class GroundingSampleWindow:
    """One window, uniform reservoir or prefix baseline, 1..64 slots per key.

    All binding fields stay together. Use a fresh window at each boundary.
    A stable seed makes identical streams reusable; changing tails can trigger
    recalibration, but finite samples cannot guarantee drift detection.
    No sampler is installed in normal queries. Limits are per primitive, not RSS.
    """
    def __init__(self, *, capacity=8, seed=0, policy='reservoir'):
        if type(capacity) is not int or not 1 <= capacity <= 64:
            raise ValueError('capacity must be an integer in 1..64')
        if type(seed) is not int or policy not in ('reservoir','prefix'):
            raise ValueError('seed must be an integer and policy reservoir or prefix')
        self.capacity, self.seed, self.policy = capacity, seed, policy
        self._streams = {}

    def observe(self, key, actor_roles, actor, target, target_roles):
        stream = self._streams.get(key)
        if stream is None:
            # Avoid process-dependent Python hash and cross-primitive interference.
            rng = None
            if self.policy == 'reservoir':
                seed = int.from_bytes(hashlib.sha256(f'{self.seed}\0{key}'.encode()).digest(), 'big')
                rng = random.Random(seed)
            stream = self._streams[key] = dict(seen=0, rng=rng, slots=[])
        stream['seen'] += 1
        position = stream['seen']
        slots = stream['slots']
        if len(slots) < self.capacity:
            slot = len(slots)
        elif self.policy == 'prefix':
            return
        else:
            slot = stream['rng'].randrange(position)
            if slot >= self.capacity:
                return
        sample = (position, (tuple(actor_roles), actor, target, tuple(target_roles)))
        if slot == len(slots):
            slots.append(sample)
        else:
            slots[slot] = sample

    def samples(self):
        """Copy retained bindings in source order, preserving repeated accesses."""
        return {key:[args for _,args in sorted(s['slots'])] for key,s in self._streams.items()}

    def counts(self):
        return {key:s['seen'] for key,s in self._streams.items()}


class GroundingSampleSchedule:
    """Explicit periodic collection; skipped windows install no observer.

    Call once at each window boundary. The caller can force collection after
    known changes. This does not detect drift in skipped windows or retain old
    samples; calibration invalidation remains the index's responsibility.
    """
    def __init__(self, *, interval=1, capacity=8, seed=0):
        if type(interval) is not int or interval < 1:
            raise ValueError('interval must be a positive integer')
        GroundingSampleWindow(capacity=capacity, seed=seed)
        self.interval, self.capacity, self.seed = interval, capacity, seed
        self._remaining = 0

    def next_window(self, *, force=False):
        if type(force) is not bool:
            raise ValueError('force must be a boolean')
        if force or self._remaining == 0:
            self._remaining = self.interval - 1
            return GroundingSampleWindow(capacity=self.capacity, seed=self.seed)
        self._remaining -= 1
        return None
