"""Audit-only scaling; excludes training, graph construction and planning."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from time import perf_counter

from experiments.g3_drift_preflight import _events, _probes
from risa.core.state import RisaState
from risa.evaluation.context_conflict import (
    ContextConflictIndex, audit_context_conflict, conflict_audit_semantics,
)


def run_scaling(manifest):
    rows = []
    seed = int(manifest['seed'])
    templates = _events(seed, 'A1', 6)
    base = _probes(seed, 'A', 3)[0].query
    queries = [replace(base, context_tags=tags) for tags in (
        ['indoor'], ['indoor', 'outdoor'], ['indoor', 'lighting:unseen'])]
    for count in manifest['event_counts']:
        for growth in ('reused_contexts', 'unique_contexts'):
            state = RisaState()
            for i in range(count):
                event = templates[i % len(templates)]
                event = replace(event, id=f'scale:{i}', context_tags=event.context_tags +
                                ([f'instance:{i}'] if growth == 'unique_contexts' else []))
                state.events_by_id[event.id] = event
            start = perf_counter()
            index = ContextConflictIndex.from_state(state)
            build_seconds = perf_counter() - start
            start = perf_counter()
            reference = [audit_context_conflict(state, query) for query in queries]
            scan_seconds = perf_counter() - start
            start = perf_counter()
            indexed = [index.audit(query) for query in queries]
            index_seconds = perf_counter() - start
            equal = all(conflict_audit_semantics(a) == conflict_audit_semantics(b)
                        for a, b in zip(reference, indexed))
            if not equal:
                raise AssertionError('audit semantics mismatch')
            scope_reads = sum(row['scope_reads'] for row in indexed)
            rows.append({
                'event_count': count, 'context_growth': growth, 'query_count': len(queries),
                'scope_count': index.scope_count, 'index_build_event_reads': count,
                'index_build_seconds': build_seconds,
                'scan_event_reads': count * len(queries),
                'indexed_event_reads': 0, 'indexed_scope_reads': scope_reads,
                'scope_to_event_work_ratio': scope_reads / (count * len(queries)),
                'scan_seconds': scan_seconds, 'indexed_seconds': index_seconds,
                'semantics_and_provenance_equal': equal,
                'returned_evidence_ids': sum(len(scope['evidence_event_ids'])
                    for row in indexed for scope in row['most_specific_scopes']),
                'indexed_provenance_ids': count,
            })
    return {'benchmark_version': manifest['benchmark_version'],
            'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
            'scope': 'context_conflict_audit_only', 'rows': rows}


if __name__ == '__main__':
    manifest = json.loads(Path('experiments/g3_context_conflict_scaling_manifest.json').read_text())
    result = run_scaling(manifest)
    Path('docs/g3-context-conflict-scaling-results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'rows': len(result['rows']), 'all_equal': all(row['semantics_and_provenance_equal'] for row in result['rows'])}))
