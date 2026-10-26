"""Explicit offline calibration from caller-supplied past actor-binding samples.

No per-query sampling is installed. Calibration is transient, invalidated by
changed joint rows/rebuild, and never saved. Timing affects allocation, never match results.
"""
from itertools import islice
from statistics import median
import sys
from time import perf_counter, process_time
from risa.engine import primitive_grounding as g


def calibrate_grounding_benefits(state, samples, *, rounds=3, repetitions=4,
                                 reuse=False, max_reuses=2):
    """samples maps primitive IDs to past (roles, actor, target, target_roles).

    Compare both paths on up to 64 samples per primitive, alternating timing
    order. Use the minimum paired saving across rounds as a conservative point
    estimate (not a confidence bound). Include profiling and prospective build
    cost in promotion setup. Samples must represent the intended next window.
    Caller selects calibration cadence and bears its measured overhead.
    reuse=True skips measurement only for identical ordered samples, timing
    settings and budget, with unchanged witness rows. max_reuses forces periodic
    remeasurement; it counts explicit calibration calls, not elapsed time.
    
    """
    if type(reuse) is not bool or type(max_reuses) is not int or max_reuses < 0:
        raise ValueError('reuse must be bool and max_reuses a nonnegative integer')
    if type(rounds) is not int or rounds < 2 or type(repetitions) is not int or repetitions < 1:
        raise ValueError('rounds >= 2 and repetitions >= 1 must be integers')
    index = getattr(state, '_primitive_grounding_index', None)
    if index is None or index['allocation_policy'] != 'frequency':
        raise ValueError('build a frequency index before calibration')
    if (len(index['references']) != len(state.structural_primitives)
            or any(state.structural_primitives.get(k) is not v for k,v in index['references'].items())):
        raise ValueError('rebuild stale primitive references before calibration')
    start, cpu = perf_counter(), process_time()
    reports = {}
    measured = False
    limit = g._lookup_limit(index['lookup_budget_bytes'], index['total_lookup_budget_bytes'], 0)
    for key, supplied in samples.items():
        entry = index['entries'][key]
        past = [(tuple(ars), actor, target, tuple(trs))
                for ars, actor, target, trs in islice(supplied, 64)]
        if not past:
            continue
        signature = (rounds, repetitions, limit,
                     tuple((tuple(ars), actor, target, tuple(trs)) for ars,actor,target,trs in past))
        if (reuse and entry.get('calibration_key') == signature
                and entry.get('calibration_reuses', 0) < max_reuses):
            entry['calibration_reuses'] += 1
            reports[key] = dict(entry['calibration_report'], reused=True)
            continue
        measured = True
        begun = process_time()
        for field in ('calibration_key', 'calibration_report', 'calibration_reuses'):
            entry.pop(field, None)
        entry.pop('benefit_seconds', None)
        entry.pop('benefit_setup_cpu', None)
        lookup, size = {}, sys.getsizeof({})
        build_cpu = process_time()
        for row in sorted(entry['rows'], key=repr):
            lookup, size = g._extend_lookup(lookup, row, size, limit)
            if lookup is None:
                break
        build_cpu = process_time() - build_cpu
        if lookup is None or size > limit:
            entry['lookup_cost'] = float('inf')
            reports[key] = dict(fits=False)
            continue
        # Copies omit access counters and never alter the retained allocation.
        linear = dict(rows=entry['rows'], actor_typed=entry['actor_typed'], lookup=None)
        indexed = dict(linear, lookup=lookup)
        for args in past:
            if g.actor_matches(linear,*args) != g.actor_matches(indexed,*args):
                raise AssertionError('calibration paths disagree')
        costs = {'linear': [], 'lookup': []}
        entries = dict(linear=linear, lookup=indexed)
        for round_id in range(rounds):
            for name in ('linear','lookup')[::(-1 if round_id%2 else 1)]:
                tick = process_time()
                for _ in range(repetitions):
                    for args in past:
                        g.actor_matches(entries[name],*args)
                costs[name].append((process_time()-tick)/(len(past)*repetitions))
        gain = max(0., min(a-b for a,b in zip(costs['linear'], costs['lookup'])))
        profile_cpu = process_time()-begun
        entry.update(lookup_cost=size, benefit_seconds=gain,
                     benefit_setup_cpu=profile_cpu+build_cpu)
        reports[key] = dict(fits=True, samples=len(past), linear_cpu=median(costs['linear']),
            lookup_cpu=median(costs['lookup']), benefit_seconds=gain, build_cpu=build_cpu,
            calibration_cpu=profile_cpu, setup_cpu=profile_cpu+build_cpu, reused=False)
        entry.update(calibration_key=signature, calibration_report=reports[key].copy(), calibration_reuses=0)
    # A new estimate must not inherit confirmation of a previous proposal.
    if measured:
        index.update(proposal=None, proposal_windows=0)
    return dict(seconds=perf_counter()-start, cpu=process_time()-cpu, entries=reports)
