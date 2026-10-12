"""Reconstructible joint-witness summaries for ordinary Primitive grounding.

The default mode invalidates on ingestion/learning. Explicitly build with
incremental=True to maintain appended support without full reconstruction.
Replacement ingestion invalidates; missing/new primitive references rebuild.
Call invalidate_primitive_grounding after direct Event/evidence corrections.
After invalidation/load, explicitly select incremental mode again if desired.
The JSON payload size measures a serializable summary, not Python heap usage.
After incremental updates use grounding_payload_bytes for current size;
payload_bytes is set to None rather than returning stale size metadata.
Rows and target unions are private mutable sets: append does not copy or sort
existing witnesses. Canonical sorting occurs only during explicit export-size
measurement. Joint actor/target/identity rows remain indivisible.
An actor/target role lookup stores equality masks from individual witnesses;
queries inspect supplied role combinations instead of scanning stored rows.
Optional lookup_budget_bytes caps extra dictionary containers PER primitive;
overflow falls back to exact linear rows. This is not a total-memory/RSS cap.
total_lookup_budget_bytes additionally caps their sum across all primitives.
Global-budget builds allocate in sorted primitive/row order, while append keeps
existing allocations; freed space is available to new/rebuilt entries.
Budgets and allocation policy survive invalidation on the same state; reselect
after load. Opt-in allocation_policy='frequency' counts actor-binding accesses.
Call rebalance_primitive_grounding at a query-window boundary to promote by
recent accesses per dictionary byte; the default remains ID-order allocation.
"""
import json
import sys
from time import perf_counter

from risa.engine.graph_builder import normalize_label
from risa.engine.role_induction import effective_event_actor_roles, effective_event_target_roles


def invalidate_primitive_grounding(state):
    state._primitive_grounding_index = None


def _add_lookup(lookup, row):
    """Expand roles within ONE witness; equality masks never join evidence rows."""
    actor_roles, target_roles, equal = row
    mask = 3 if equal is None else (2 if equal else 1)
    for role in actor_roles:
        bucket = lookup.get(role)
        if bucket is None:
            bucket = lookup[role] = dict(any=0, wildcard=0, targets={})
        bucket['any'] |= mask
        if not target_roles:
            bucket['wildcard'] |= mask
        for target_role in target_roles:
            bucket['targets'][target_role] = bucket['targets'].get(target_role, 0) | mask


def _extend_lookup(lookup, row, size, budget):
    """Bound extra dictionary containers per primitive, not source rows or RSS.

    Discard on overflow; transient overshoot is limited to one actor bucket or target-dict growth.
    Once discarded, remain linear until an explicit rebuild or frequency rebalance.
    """
    if lookup is None:
        return None, 0
    if budget is None:
        _add_lookup(lookup, row)
        return lookup, 0
    if size > budget:
        return None, 0
    ars, trs, equal = row
    mask = 3 if equal is None else (2 if equal else 1)
    for ar in ars:
        bucket = lookup.get(ar)
        if bucket is None:
            before = sys.getsizeof(lookup)
            bucket = lookup[ar] = dict(any=0, wildcard=0, targets={})
            size += sys.getsizeof(lookup) - before + sys.getsizeof(bucket) + sys.getsizeof(bucket['targets'])
            if size > budget:
                return None, 0
        bucket['any'] |= mask
        if not trs:
            bucket['wildcard'] |= mask
        for tr in trs:
            targets = bucket['targets']
            before = sys.getsizeof(targets)
            targets[tr] = targets.get(tr, 0) | mask
            size += sys.getsizeof(targets) - before
            if size > budget:
                return None, 0
    return lookup, size


def _lookup_limit(per_primitive, total, used):
    remaining = None if total is None else max(0, total - used)
    if per_primitive is None:
        return remaining
    return per_primitive if remaining is None else min(per_primitive, remaining)


def build_primitive_grounding(state, *, incremental=False, lookup_budget_bytes=None,
                              total_lookup_budget_bytes=None, allocation_policy='id'):
    if allocation_policy not in ('id', 'frequency'):
        raise ValueError('allocation_policy must be id or frequency')
    if allocation_policy == 'frequency' and total_lookup_budget_bytes is None:
        raise ValueError('frequency policy requires an explicit total lookup budget')
    if lookup_budget_bytes is not None and (type(lookup_budget_bytes) is not int or lookup_budget_bytes < 0):
        raise ValueError('lookup_budget_bytes must be a nonnegative integer or None')
    if total_lookup_budget_bytes is not None and (type(total_lookup_budget_bytes) is not int or total_lookup_budget_bytes < 0):
        raise ValueError('total_lookup_budget_bytes must be a nonnegative integer or None')
    state._primitive_grounding_allocation_policy = allocation_policy
    state._primitive_grounding_total_lookup_budget = total_lookup_budget_bytes
    state._primitive_grounding_lookup_budget = lookup_budget_bytes
    started = perf_counter()
    entries, references, reads = {}, {}, 0
    missing = set()
    used = 0
    primitives = state.structural_primitives.items()
    if total_lookup_budget_bytes is not None:
        primitives = sorted(primitives)
    for key, primitive in primitives:
        rows = set()
        targets = set()
        for event_id in primitive.evidence_event_ids:
            event = state.events_by_id.get(event_id)
            if event is None:
                missing.add(event_id)
                continue
            reads += 1
            ar = tuple(sorted({normalize_label(r) for r in effective_event_actor_roles(event)}))
            tr = tuple(sorted({normalize_label(r) for r in effective_event_target_roles(event)}))
            targets.update(tr)
            equal = None if event.target is None else normalize_label(event.actor) == normalize_label(event.target)
            rows.add((ar, tr, equal))
        limit = _lookup_limit(lookup_budget_bytes, total_lookup_budget_bytes, used)
        lookup = {}
        lookup_bytes = sys.getsizeof(lookup) if limit is not None else 0
        ordered_rows = sorted(rows, key=repr) if total_lookup_budget_bytes is not None else rows
        for row in ordered_rows:
            lookup, lookup_bytes = _extend_lookup(lookup, row, lookup_bytes, limit)
        if limit is not None and lookup_bytes > limit:
            lookup, lookup_bytes = None, 0
        used += lookup_bytes
        entries[key] = dict(rows=rows, targets=targets, lookup=lookup, lookup_bytes=lookup_bytes,
                            actor_typed=any(ar for ar, _, _ in rows))
        if allocation_policy == 'frequency':
            entries[key].update(query_hits=0, lookup_cost=None)
        references[key] = primitive
    payload = {key: dict(rows=sorted(entry['rows'], key=repr), targets=sorted(entry['targets'])) for key, entry in entries.items()}
    index = dict(entries=entries, references=references, build_event_reads=reads,
                 signature_count=sum(len(e['rows']) for e in entries.values()),
                 payload_bytes=len(json.dumps(payload, sort_keys=True).encode()),
                 build_seconds=perf_counter() - started)
    index.update(allocation_policy=allocation_policy, rebalances=0, promotions=0, demotions=0,
                 total_lookup_budget_bytes=total_lookup_budget_bytes, lookup_bytes_used=used,
                 lookup_budget_bytes=lookup_budget_bytes, incremental=incremental, missing_event_ids=missing,
                 support_counts={key: len(p.evidence_event_ids) for key, p in references.items()},
                 update_event_reads=0, update_support_visits=0)
    state._primitive_grounding_index = index
    return index


def prepare_grounding_ingest(state, event):
    index = getattr(state, '_primitive_grounding_index', None)
    if index is None:
        return
    if (not index['incremental'] or event.id in state.events_by_id
            or event.id in index['missing_event_ids']):
        invalidate_primitive_grounding(state)


def update_primitive_grounding(state, primitive, event_id, already_supported):
    """Maintain only appended support; corrections still require invalidation."""
    index = getattr(state, '_primitive_grounding_index', None)
    if index is None or not index['incremental']:
        return
    key = primitive.id
    current = index['entries'].get(key)
    old_count = len(current['rows']) if current else 0
    old_bytes = current['lookup_bytes'] if current else 0
    limit = _lookup_limit(index['lookup_budget_bytes'], index['total_lookup_budget_bytes'],
                          index['lookup_bytes_used'] - old_bytes)
    expected = len(primitive.evidence_event_ids) - (not already_supported)
    if (current is None or index['references'].get(key) is not primitive
            or index['support_counts'].get(key) != expected):
        ids = primitive.evidence_event_ids
        rows, targets, lookup = set(), set(), {}
        lookup_bytes = sys.getsizeof(lookup) if limit is not None else 0
    elif already_supported:
        return
    else:
        ids = (event_id,)
        rows, targets, lookup = current['rows'], current['targets'], current['lookup']
        lookup_bytes = current['lookup_bytes']
    actor_typed = bool(current and rows is current['rows'] and current['actor_typed'])
    for eid in ids:
        index['update_support_visits'] += 1
        event = state.events_by_id.get(eid)
        if event is None:
            index['missing_event_ids'].add(eid)
            continue
        index['update_event_reads'] += 1
        ar = tuple(sorted({normalize_label(r) for r in effective_event_actor_roles(event)}))
        tr = tuple(sorted({normalize_label(r) for r in effective_event_target_roles(event)}))
        equal = None if event.target is None else normalize_label(event.actor) == normalize_label(event.target)
        row = (ar, tr, equal)
        if row not in rows:
            rows.add(row)
            lookup, lookup_bytes = _extend_lookup(lookup, row, lookup_bytes, limit)
        actor_typed = actor_typed or bool(ar)
        targets.update(tr)
    if limit is not None and lookup_bytes > limit:
        lookup, lookup_bytes = None, 0
    index['lookup_bytes_used'] += lookup_bytes - old_bytes
    index['signature_count'] += len(rows) - old_count
    index['entries'][key] = dict(rows=rows, targets=targets, lookup=lookup, lookup_bytes=lookup_bytes,
                                  actor_typed=actor_typed)
    if index['allocation_policy'] == 'frequency':
        index['entries'][key].update(query_hits=current.get('query_hits', 0) if current and index['references'].get(key) is primitive else 0, lookup_cost=None)
    index['references'][key] = primitive
    index['support_counts'][key] = len(primitive.evidence_event_ids)
    # Export-size accounting is deferred to explicit measurement, not queries.
    index['payload_bytes'] = None


def rebalance_primitive_grounding(state):
    """Explicit query-window boundary. Rank recent actor-binding hits per byte.

    Counts reset after each window; no future queries or persisted state are used.
    Cost probes and promoted dictionaries are included in returned elapsed time.
    """
    started = perf_counter()
    index = getattr(state, '_primitive_grounding_index', None)
    if index is None or index['allocation_policy'] != 'frequency':
        return dict(seconds=0., promotions=0, demotions=0, cost_probes=0)
    if (len(index['references']) != len(state.structural_primitives)
            or any(state.structural_primitives.get(k) is not v for k,v in index['references'].items())):
        # Structural changes invalidate both cost estimates and frequency history.
        build_primitive_grounding(state, incremental=index['incremental'],
            lookup_budget_bytes=index['lookup_budget_bytes'],
            total_lookup_budget_bytes=index['total_lookup_budget_bytes'], allocation_policy='frequency')
        return dict(seconds=perf_counter()-started, promotions=0, demotions=0, cost_probes=0)
    entries = index['entries']
    if not any(e['query_hits'] for e in entries.values()):
        return dict(seconds=perf_counter()-started, promotions=0, demotions=0, cost_probes=0)
    limit = _lookup_limit(index['lookup_budget_bytes'], index['total_lookup_budget_bytes'], 0)
    probes = 0
    def construct(entry):
        lookup, size = {}, sys.getsizeof({})
        for row in sorted(entry['rows'], key=repr):
            lookup, size = _extend_lookup(lookup, row, size, limit)
            if lookup is None:
                break
        return (None, 0) if size > limit else (lookup, size)
    for entry in entries.values():
        if entry['lookup_cost'] is None:
            if entry['lookup'] is not None:
                entry['lookup_cost'] = entry['lookup_bytes']
            else:
                lookup, size = construct(entry)
                entry['lookup_cost'] = size if lookup is not None else float('inf')
                del lookup
                probes += 1
    ranked = sorted(entries, key=lambda k: (-entries[k]['query_hits'] / entries[k]['lookup_cost'], k))
    selected, used = set(), 0
    for key in ranked:
        size = entries[key]['lookup_cost']
        if size + used <= index['total_lookup_budget_bytes']:
            selected.add(key)
            used += size
    promotions = demotions = 0
    for key, entry in entries.items():
        if key not in selected and entry['lookup'] is not None:
            entry['lookup'], entry['lookup_bytes'] = None, 0
            demotions += 1
    for key in sorted(selected):
        entry = entries[key]
        if entry['lookup'] is None:
            entry['lookup'], entry['lookup_bytes'] = construct(entry)
            promotions += 1
    for entry in entries.values():
        entry['query_hits'] = 0
    index['lookup_bytes_used'] = sum(e['lookup_bytes'] for e in entries.values())
    index['rebalances'] += 1
    index['promotions'] += promotions
    index['demotions'] += demotions
    return dict(seconds=perf_counter()-started, promotions=promotions, demotions=demotions, cost_probes=probes)


def grounding_payload_bytes(index):
    payload = {key: dict(rows=sorted(entry['rows'], key=repr), targets=sorted(entry['targets']))
               for key, entry in index['entries'].items()}
    return len(json.dumps(payload, sort_keys=True).encode())


def grounding_entry(state, primitive, diagnostics=None):
    index = getattr(state, '_primitive_grounding_index', None)
    if (index is None or len(index['references']) != len(state.structural_primitives)
            or index['references'].get(primitive.id) is not primitive):
        index = build_primitive_grounding(state, incremental=bool(index and index['incremental']),
            lookup_budget_bytes=getattr(state, '_primitive_grounding_lookup_budget', None),
            total_lookup_budget_bytes=getattr(state, '_primitive_grounding_total_lookup_budget', None),
            allocation_policy=getattr(state, '_primitive_grounding_allocation_policy', 'id'))
        if diagnostics is not None:
            diagnostics['index_build_event_reads'] += index['build_event_reads']
    return index['entries'][primitive.id]


def actor_matches(entry, actor_roles, actor, target, target_roles, diagnostics=None):
    if actor is None and not actor_roles and target is None and not target_roles:
        return True
    if not entry['actor_typed']:
        return True
    if 'query_hits' in entry:
        entry['query_hits'] += 1
    ars, trs = {normalize_label(r) for r in actor_roles}, {normalize_label(r) for r in target_roles}
    if entry['lookup'] is None:
        for ar, tr, equal in entry['rows']:
            if diagnostics is not None:
                diagnostics['grounding_signature_checks'] += 1
            if not ars.intersection(ar):
                continue
            if (target is not None or target_roles) and tr and not trs.intersection(tr):
                continue
            if actor is not None and target is not None and equal is not None:
                if (normalize_label(actor) == normalize_label(target)) != equal:
                    continue
            return True
        return False
    required = 3
    if actor is not None and target is not None:
        required = 2 if normalize_label(actor) == normalize_label(target) else 1
    constrained_target = target is not None or bool(target_roles)
    for role in ars:
        bucket = entry['lookup'].get(role)
        if diagnostics is not None:
            diagnostics['grounding_lookup_probes'] = diagnostics.get('grounding_lookup_probes', 0) + 1
        if bucket is None:
            continue
        if not constrained_target:
            if bucket['any'] & required:
                return True
            continue
        if bucket['wildcard'] & required:
            return True
        for target_role in trs:
            if diagnostics is not None:
                diagnostics['grounding_lookup_probes'] = diagnostics.get('grounding_lookup_probes', 0) + 1
            if bucket['targets'].get(target_role, 0) & required:
                return True
    return False


def target_matches(entry, target_roles, diagnostics=None):
    if diagnostics is not None:
        diagnostics['grounding_signature_checks'] += 1
    return not entry['targets'] or bool(entry['targets'].intersection(normalize_label(r) for r in target_roles))
