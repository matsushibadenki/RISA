"""Explicit correction of a derived grounding cache, not learned-world repair.

Call after direct Event edits and before the next indexed query. All edited IDs
must be supplied; unreported in-place changes cannot be detected here. Unknown
rule/dependency changes require dependencies_known=False (full rebuild).
Nothing in this tracker is persisted or installed in normal ingestion.
"""
from math import isfinite
from types import SimpleNamespace

from risa.engine.primitive_grounding import build_primitive_grounding


class GroundingCorrectionTracker:
    def __init__(self, state, *, max_fraction=0.5):
        if isinstance(max_fraction, bool) or not isinstance(max_fraction, (int, float)) or not isfinite(max_fraction) or not 0 <= max_fraction <= 1:
            raise ValueError('max_fraction must be finite and in [0, 1]')
        self.state = state
        self.max_fraction = max_fraction
        # Establish a trusted baseline even if an older cache predates edits.
        # This initial full build is part of the tracker's measured setup cost.
        self._rebuild()
        self._capture()

    def _rebuild(self):
        state = self.state
        old = getattr(state, '_primitive_grounding_index', None)
        return build_primitive_grounding(state,
            incremental=bool(old and old['incremental']),
            lookup_budget_bytes=getattr(state, '_primitive_grounding_lookup_budget', None),
            total_lookup_budget_bytes=getattr(state, '_primitive_grounding_total_lookup_budget', None),
            allocation_policy=getattr(state, '_primitive_grounding_allocation_policy', 'id'))

    def _capture(self):
        self.index = self.state._primitive_grounding_index
        self.references = dict(self.state.structural_primitives)
        self.supports = {k: frozenset(p.evidence_event_ids) for k, p in self.references.items()}
        self.reverse = {}
        for key, ids in self.supports.items():
            for eid in ids:
                self.reverse.setdefault(eid, set()).add(key)

    def refresh(self, event_ids, *, dependencies_known=True):
        """Refresh after reported edits; return a diagnostic dependency manifest.

        Validation scans support IDs, not all Event payloads. A caller requiring
        arbitrary mutation detection must use full rebuilding instead.
        """
        if type(dependencies_known) is not bool:
            raise ValueError('dependencies_known must be boolean')
        if isinstance(event_ids, (str, bytes)):
            raise ValueError('event_ids must be an iterable of IDs, not a string')
        ids = frozenset(event_ids)
        if any(not isinstance(eid, str) for eid in ids):
            raise ValueError('Event IDs must be strings')
        state, old = self.state, self.index
        affected = set().union(*(self.reverse.get(eid, set()) for eid in ids)) if ids else set()
        reason = None
        support_checks = 0
        if not dependencies_known:
            reason = 'unknown_dependencies'
        elif getattr(state, '_primitive_grounding_index', None) is not old:
            reason = 'index_replaced'
        elif state.structural_primitives.keys() != self.references.keys():
            reason = 'primitive_set_changed'
        else:
            for key, primitive in state.structural_primitives.items():
                support_checks += len(primitive.evidence_event_ids)
                if primitive is not self.references[key] or primitive.evidence_event_ids != self.supports[key]:
                    reason = 'primitive_or_support_changed'
                    break
        if reason is None:
            if any(eid not in self.reverse for eid in ids):
                reason = 'untracked_event'
            elif ids & old['missing_event_ids']:
                reason = 'missing_reference_changed'
            elif any(eid not in state.events_by_id for eid in ids):
                reason = 'event_deleted'
            else:
                total = sum(map(len, self.supports.values()))
                touched = sum(len(self.supports[k]) for k in affected)
                if touched > total * self.max_fraction:
                    reason = 'wide_fanout'
        report = dict(mode='partial', reason=reason, event_ids=sorted(ids),
                      affected_primitives=sorted(affected), support_checks=support_checks,
                      dependencies={eid: sorted(self.reverse.get(eid, ())) for eid in sorted(ids)})
        if reason is not None:
            rebuilt = self._rebuild()
            self._capture()
            report.update(mode='full', event_reads=rebuilt['build_event_reads'],
                          rebuilt_primitives=len(rebuilt['entries']))
            return report
        if not affected:
            report.update(mode='noop', event_reads=0, rebuilt_primitives=0)
            return report
        untouched_bytes = sum(entry['lookup_bytes'] for k, entry in old['entries'].items() if k not in affected)
        total_budget = old['total_lookup_budget_bytes']
        remaining = None if total_budget is None else max(0, total_budget - untouched_bytes)
        view = SimpleNamespace(events_by_id=state.events_by_id,
                               structural_primitives={k: state.structural_primitives[k] for k in sorted(affected)})
        rebuilt = build_primitive_grounding(view, incremental=old['incremental'],
            lookup_budget_bytes=old['lookup_budget_bytes'], total_lookup_budget_bytes=remaining,
            allocation_policy=old['allocation_policy'])
        # Replacing affected entries clears all their calibration and hit history,
        # even when joint rows happen to remain equal. Untouched entries survive.
        old['entries'].update(rebuilt['entries'])
        old['lookup_bytes_used'] = untouched_bytes + rebuilt['lookup_bytes_used']
        old['signature_count'] = sum(len(e['rows']) for e in old['entries'].values())
        old['update_event_reads'] += rebuilt['build_event_reads']
        old['update_support_visits'] += sum(len(self.supports[k]) for k in affected)
        old.update(payload_bytes=None, proposal=None, proposal_windows=0)
        report.update(event_reads=rebuilt['build_event_reads'], rebuilt_primitives=len(affected))
        return report
