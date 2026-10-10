"""Reconstructible joint-witness summaries for ordinary Primitive grounding.

Ingestion and learning invalidate this transient cache. Call
invalidate_primitive_grounding after direct in-place Event/evidence corrections.
The JSON payload size measures a serializable summary, not Python heap usage.
"""
import json
from time import perf_counter

from risa.engine.graph_builder import normalize_label
from risa.engine.role_induction import effective_event_actor_roles, effective_event_target_roles


def invalidate_primitive_grounding(state):
    state._primitive_grounding_index = None


def build_primitive_grounding(state):
    started = perf_counter()
    entries, references, reads = {}, {}, 0
    for key, primitive in state.structural_primitives.items():
        rows = set()
        targets = set()
        for event_id in primitive.evidence_event_ids:
            event = state.events_by_id.get(event_id)
            if event is None:
                continue
            reads += 1
            ar = tuple(sorted({normalize_label(r) for r in effective_event_actor_roles(event)}))
            tr = tuple(sorted({normalize_label(r) for r in effective_event_target_roles(event)}))
            targets.update(tr)
            equal = None if event.target is None else normalize_label(event.actor) == normalize_label(event.target)
            rows.add((ar, tr, equal))
        entries[key] = dict(rows=tuple(sorted(rows, key=repr)), targets=frozenset(targets),
                            actor_typed=any(ar for ar, _, _ in rows))
        references[key] = primitive
    payload = {key: dict(rows=entry['rows'], targets=sorted(entry['targets'])) for key, entry in entries.items()}
    index = dict(entries=entries, references=references, build_event_reads=reads,
                 signature_count=sum(len(e['rows']) for e in entries.values()),
                 payload_bytes=len(json.dumps(payload, sort_keys=True).encode()),
                 build_seconds=perf_counter() - started)
    state._primitive_grounding_index = index
    return index


def grounding_entry(state, primitive, diagnostics=None):
    index = getattr(state, '_primitive_grounding_index', None)
    if (index is None or len(index['references']) != len(state.structural_primitives)
            or index['references'].get(primitive.id) is not primitive):
        index = build_primitive_grounding(state)
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
