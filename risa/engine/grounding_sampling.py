"""Explicit, per-primitive bounded sampling of complete binding witnesses."""
import math
import hashlib
import random
import sys
import copy


def collector_bytes(value):
    """Unique retained Python bytes, including Random C state; not process RSS."""
    seen, pending, total = set(), [value], 0
    while pending:
        obj = pending.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        total += sys.getsizeof(obj)
        if isinstance(obj, dict):
            pending.extend(obj.keys())
            pending.extend(obj.values())
        elif isinstance(obj, random.Random):
            pending.append(obj.__dict__)
        elif isinstance(obj, (tuple, list)):
            pending.extend(obj)
    return total


def _log_uniform(rng):
    # random() excludes 1 but may return 0. Draw from the open interval.
    u = rng.random()
    while u == 0:
        u = rng.random()
    return math.log(u)


def _schedule_replacement(stream, after, capacity):
    # Algorithm L: W is the current priority threshold. Conditional on W,
    # the number of rejected positions before the next admission is geometric.
    rng = stream['rng']
    log_w = stream.get('log_w', 0.) + _log_uniform(rng) / capacity
    stream['log_w'] = log_w
    log_reject = (math.log(-math.expm1(log_w)) if log_w > -0.693
                  else math.log1p(-math.exp(log_w)))
    stream['next'] = after + 1 + int(_log_uniform(rng) / log_reject)


class GroundingSampleWindow:
    """One window, uniform reservoir or prefix baseline, 1..64 slots per key.

    All binding fields stay together. Use a fresh window at each boundary.
    A stable seed makes identical streams reusable; changing tails can trigger
    recalibration, but finite samples cannot guarantee drift detection.
    No sampler is installed in normal queries. Optional budget_bytes caps the
    unique retained _streams graph (keys, containers, bindings, RNG and counters),
    not RSS, the constant window header, trial allocations or exported copies.
    At exhaustion collection freezes: samples/counts describe only that prefix,
    NOT an unbiased sample/count of the full window. max_streams is a separate
    first-admitted-key baseline. policy='recent' instead evicts least-recently
    observed keys and retains recent joint bindings, continuing after overflow.
    Its counts cover accepted observations in current key residency, not all
    queries, and it is not a uniform reservoir.
    Neither mode changes query semantics.
    """
    _use_headroom = True
    _recent_fast = True

    def __init__(self, *, capacity=8, seed=0, policy='reservoir', budget_bytes=None, max_streams=None):
        if type(capacity) is not int or not 1 <= capacity <= 64:
            raise ValueError('capacity must be an integer in 1..64')
        if type(seed) is not int or policy not in ('reservoir','prefix','skip','recent'):
            raise ValueError('seed must be an integer and policy reservoir, prefix, skip or recent')
        if budget_bytes is not None and (type(budget_bytes) is not int or budget_bytes < sys.getsizeof({})):
            raise ValueError('budget_bytes must cover at least an empty stream dictionary')
        if max_streams is not None and (type(max_streams) is not int or max_streams < 0):
            raise ValueError('max_streams must be a nonnegative integer')
        self.budget_bytes, self.max_streams = budget_bytes, max_streams
        self.exhausted = False
        self.capacity, self.seed, self.policy = capacity, seed, policy
        self._streams = {}
        self._retained_upper = sys.getsizeof(self._streams)

    def observe(self, key, actor_roles, actor, target, target_roles):
        if self.policy == 'recent':
            self._observe_recent(key, actor_roles, actor, target, target_roles)
            return
        if self.exhausted:
            return
        if key not in self._streams and self.max_streams is not None and len(self._streams) >= self.max_streams:
            return
        if self.budget_bytes is None:
            self._observe(key, actor_roles, actor, target, target_roles)
            return
        # A conservative positive-growth bound permits in-place updates when
        # there is ample headroom. Shared objects are deliberately overcounted;
        # never subtract removed payloads without a global reachability audit.
        previous = self._streams.get(key)
        if previous is not None and self._use_headroom:
            position = previous['seen'] + 1
            slots = previous['slots']
            stable_rng = (self.policy == 'prefix' or len(slots) < self.capacity
                          or (self.policy == 'reservoir' and previous['rng'] is not None)
                          or (self.policy == 'skip' and previous.get('next', 0) > position))
            if stable_rng:
                if len(slots) >= self.capacity and self.policy in ('prefix', 'skip'):
                    # These positions only increment the count; no binding or
                    # random state changes, and input iterables remain unread.
                    growth = sys.getsizeof(position)
                else:
                    actor_roles, target_roles = tuple(actor_roles), tuple(target_roles)
                    candidate = (position, (actor_roles, actor, target, target_roles))
                    # New sample graph + an entire slot list + allocation slack
                    # bounds append/replacement growth (capacity <= 64).
                    growth = collector_bytes(candidate) + sys.getsizeof(slots) + 256
                if self._retained_upper + growth <= self.budget_bytes:
                    self._observe(key, actor_roles, actor, target, target_roles)
                    self._retained_upper += growth
                    return
        # Conservative opt-in baseline: stop at a complete stream-prefix boundary.
        # Trial allocation and export are NOT covered by the retained-byte budget.
        previous = self._streams.get(key)
        trial = dict(self._streams)
        if previous is not None:
            trial[key] = copy.deepcopy(previous)
        original = self._streams
        self._streams = trial
        try:
            self._observe(key, actor_roles, actor, target, target_roles)
            retained = collector_bytes(trial)
            fits = retained <= self.budget_bytes
        except BaseException:
            self._streams = original
            raise
        if not fits:
            self._streams = original
            self.exhausted = True
        else:
            self._retained_upper = retained

    def _observe_recent(self, key, actor_roles, actor, target, target_roles):
        """Bounded recency, not uniform sampling; counts cover current residency.

        Evict least-recently-observed keys, keeping each joint binding atomic.
        An individually oversized observation leaves the previous state intact.
        No evicted-key ledger or random generator is retained.
        """
        if self.max_streams == 0:
            return
        previous = self._streams.get(key)
        position = previous['seen'] + 1 if previous is not None else 1
        sample = (position, (tuple(actor_roles), actor, target, tuple(target_roles)))
        slots = (previous['slots'] if previous is not None else []) + [sample]
        candidate = dict(seen=position, rng=None, slots=slots[-self.capacity:])
        trial = None
        trial_bytes = None
        # If the complete update fits, it also proves the single binding and
        # key history fit. Avoid two redundant traversals and their allocations.
        # New-key churn keeps the original path: it frequently needs eviction.
        # Near the cap, history trimming often invalidates the full precheck.
        # Keep the original order unless at least half the budget is spare.
        if (self._recent_fast and previous is not None
                and (self.budget_bytes is None or self._retained_upper * 2 <= self.budget_bytes)):
            trial = dict(self._streams)
            trial.pop(key)
            trial[key] = candidate
            retained = collector_bytes(trial)
            trial_bytes = retained
            if ((self.budget_bytes is None or retained <= self.budget_bytes)
                    and (self.max_streams is None or len(trial) <= self.max_streams)):
                self._streams = trial
                self._retained_upper = retained
                return
        single = {key: dict(seen=position, rng=None, slots=[sample])}
        if self.budget_bytes is not None and collector_bytes(single) > self.budget_bytes:
            return
        # Shrink this key first if even its own retained history cannot fit.
        if self.budget_bytes is not None:
            while collector_bytes({key: candidate}) > self.budget_bytes:
                candidate['slots'] = candidate['slots'][1:]
                trial = None
                trial_bytes = None
        if trial is None:
            trial = dict(self._streams)
            trial.pop(key, None)
            trial[key] = candidate
        while self.max_streams is not None and len(trial) > self.max_streams:
            del trial[next(iter(trial))]
            trial_bytes = None
        retained = collector_bytes(trial) if trial_bytes is None else trial_bytes
        if self.budget_bytes is not None:
            while retained > self.budget_bytes:
                if len(trial) > 1:
                    del trial[next(iter(trial))]
                    # Release dictionary capacity after eviction as well.
                    trial = dict(trial)
                else:
                    # The single-key preflight fit; compact the dictionary.
                    trial = {key: candidate}
                retained = collector_bytes(trial)
        self._streams = trial
        self._retained_upper = retained

    def _observe(self, key, actor_roles, actor, target, target_roles):
        stream = self._streams.get(key)
        if stream is None:
            stream = self._streams[key] = dict(seen=0, rng=None, slots=[])
        stream['seen'] += 1
        position = stream['seen']
        slots = stream['slots']
        if len(slots) < self.capacity:
            pass
        elif self.policy == 'prefix':
            return
        else:
            if stream['rng'] is None:
                seed = int.from_bytes(hashlib.sha256(f'{self.seed}\0{key}'.encode()).digest(), 'big')
                stream['rng'] = random.Random(seed)
            self._replace(stream, position, actor_roles, actor, target, target_roles)
            return
        sample = (position, (tuple(actor_roles), actor, target, tuple(target_roles)))
        slots.append(sample)

    def _replace(self, stream, position, actor_roles, actor, target, target_roles):
        slots = stream['slots']
        if self.policy == 'skip':
            if position == self.capacity + 1:
                _schedule_replacement(stream, self.capacity, self.capacity)
            if position != stream['next']:
                return
            slot = stream['rng'].randrange(self.capacity)
            _schedule_replacement(stream, position, self.capacity)
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
    def __init__(self, *, interval=1, capacity=8, seed=0, policy='reservoir', budget_bytes=None, max_streams=None):
        if type(interval) is not int or interval < 1:
            raise ValueError('interval must be a positive integer')
        GroundingSampleWindow(capacity=capacity, seed=seed, policy=policy,
                              budget_bytes=budget_bytes, max_streams=max_streams)
        self.budget_bytes, self.max_streams = budget_bytes, max_streams
        self.interval, self.capacity, self.seed = interval, capacity, seed
        self.policy = policy
        self._remaining = 0

    def next_window(self, *, force=False):
        if type(force) is not bool:
            raise ValueError('force must be a boolean')
        if force or self._remaining == 0:
            self._remaining = self.interval - 1
            return GroundingSampleWindow(capacity=self.capacity, seed=self.seed, policy=self.policy,
                                         budget_bytes=self.budget_bytes, max_streams=self.max_streams)
        self._remaining -= 1
        return None


class GroundingCountTrigger:
    """Constant-state hint from completed-window counts, never future traffic.

    Feed the returned boolean to the NEXT window's schedule.force. Counts must
    describe comparable windows (e.g. fixed duration). This cannot detect
    equal-count role/identity changes or recover a transient already missed.
    A sampled window needs no extra refresh for its own count change.
    """
    def __init__(self, *, factor=2, min_delta=16):
        if type(factor) is not int or factor < 2:
            raise ValueError('factor must be an integer >= 2')
        if type(min_delta) is not int or min_delta < 1:
            raise ValueError('min_delta must be a positive integer')
        self.factor, self.min_delta = factor, min_delta
        self._previous = None

    def observe(self, completed_count, *, sampled=False):
        if type(completed_count) is not int or completed_count < 0:
            raise ValueError('completed_count must be a nonnegative integer')
        if type(sampled) is not bool:
            raise ValueError('sampled must be a boolean')
        previous = self._previous
        self._previous = completed_count
        if previous is None or sampled:
            return False
        return (abs(completed_count - previous) >= self.min_delta
                and max(completed_count, previous) >=
                self.factor * min(completed_count, previous))
