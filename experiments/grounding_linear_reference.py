"""Frozen linear-witness baseline for the 2026-10-11 lookup experiment.

Reconstructible joint-witness summaries for ordinary Primitive grounding.

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
"""
import json
from time import perf_counter

from risa.engine.graph_builder import normalize_label
from risa.engine.role_induction import effective_event_actor_roles, effective_event_target_roles


def invalidate_primitive_grounding(state):
    state._primitive_grounding_index = None


def build_primitive_grounding(state, *, incremental=False):
    started = perf_counter()
    entries, references, reads = {}, {}, 0
    missing = set()
    for key, primitive in state.structural_primitives.items():
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
        entries[key] = dict(rows=rows, targets=targets,
                            actor_typed=any(ar for ar, _, _ in rows))
        references[key] = primitive
    payload = {key: dict(rows=sorted(entry['rows'], key=repr), targets=sorted(entry['targets'])) for key, entry in entries.items()}
    index = dict(entries=entries, references=references, build_event_reads=reads,
                 signature_count=sum(len(e['rows']) for e in entries.values()),
                 payload_bytes=len(json.dumps(payload, sort_keys=True).encode()),
                 build_seconds=perf_counter() - started)
    index.update(incremental=incremental, missing_event_ids=missing,
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
    expected = len(primitive.evidence_event_ids) - (not already_supported)
    if (current is None or index['references'].get(key) is not primitive
            or index['support_counts'].get(key) != expected):
        ids = primitive.evidence_event_ids
        rows, targets = set(), set()
    elif already_supported:
        return
    else:
        ids = (event_id,)
        rows, targets = current['rows'], current['targets']
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
        rows.add((ar, tr, equal))
        actor_typed = actor_typed or bool(ar)
        targets.update(tr)
    index['signature_count'] += len(rows) - old_count
    index['entries'][key] = dict(rows=rows, targets=targets,
                                  actor_typed=actor_typed)
    index['references'][key] = primitive
    index['support_counts'][key] = len(primitive.evidence_event_ids)
    # Export-size accounting is deferred to explicit measurement, not queries.
    index['payload_bytes'] = None


def grounding_payload_bytes(index):
    payload = {key: dict(rows=sorted(entry['rows'], key=repr), targets=sorted(entry['targets']))
               for key, entry in index['entries'].items()}
    return len(json.dumps(payload, sort_keys=True).encode())


def grounding_entry(state, primitive, diagnostics=None):
    index = getattr(state, '_primitive_grounding_index', None)
    if (index is None or len(index['references']) != len(state.structural_primitives)
            or index['references'].get(primitive.id) is not primitive):
        index = build_primitive_grounding(state, incremental=bool(index and index['incremental']))
        if diagnostics is not None:
            diagnostics['index_build_event_reads'] += index['build_event_reads']
    return index['entries'][primitive.id]


def actor_matches(entry, actor_roles, actor, target, target_roles, diagnostics=None):
    if actor is None and not actor_roles and target is None and not target_roles:
        return True
    if not entry['actor_typed']:
        return True
    ars, trs = {normalize_label(r) for r in actor_roles}, {normalize_label(r) for r in target_roles}
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


def target_matches(entry, target_roles, diagnostics=None):
    if diagnostics is not None:
        diagnostics['grounding_signature_checks'] += 1
    return not entry['targets'] or bool(entry['targets'].intersection(normalize_label(r) for r in target_roles))
