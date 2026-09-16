"""Independent development-probe gate for G3.2 candidate validation inheritance."""

from __future__ import annotations

from dataclasses import dataclass
import random

from risa.core.models import UnnamedConceptCandidate
from risa.core.state import RisaState
from risa.engine.candidate_discovery import _candidate_context_matches


@dataclass(frozen=True)
class ExtensionProbe:
    id: str
    episode_id: str
    source: str
    context_tags: tuple[str, ...]
    expected_applicable: bool


class CandidateExtensionValidator:
    """Recheck scoped candidate gain without exposing final probes to learning."""

    def __init__(
        self,
        probes: list[ExtensionProbe],
        *,
        minimum_cases: int = 200,
        minimum_gain: float = 0.05,
        bootstrap_samples: int = 1000,
        seed: int = 0,
    ) -> None:
        if minimum_cases < 1 or bootstrap_samples < 100:
            raise ValueError("invalid validation budget")
        if len(probes) < minimum_cases:
            raise ValueError("insufficient development probes")
        if len({probe.id for probe in probes}) != len(probes):
            raise ValueError("duplicate development probe IDs")
        if len({probe.episode_id for probe in probes}) < 2 or len({probe.source for probe in probes}) < 2:
            raise ValueError("development probes need independent episodes and sources")
        self.probes = tuple(probes)
        self.minimum_gain = minimum_gain
        self.bootstrap_samples = bootstrap_samples
        self.seed = seed
        self.decisions: list[dict[str, object]] = []

    def __call__(
        self,
        state: RisaState,
        previous: UnnamedConceptCandidate,
        candidate: UnnamedConceptCandidate,
    ) -> bool:
        protected = set(previous.evaluation_event_ids)
        pending = [candidate.id]
        seen: set[str] = set()
        while pending:
            item_id = pending.pop()
            if item_id in seen:
                continue
            seen.add(item_id)
            item = state.unnamed_concept_candidates[item_id]
            protected.update(item.supporting_event_ids)
            protected.update(item.evaluation_event_ids)
            pending.extend(item.parent_candidate_ids)
        if any(probe.id in protected or probe.id in state.events_by_id for probe in self.probes):
            return self._record(candidate.id, False, "evidence_overlap")

        proposed = [
            int(_candidate_context_matches(candidate, list(probe.context_tags))
                == probe.expected_applicable)
            for probe in self.probes
        ]
        baseline = [int(not probe.expected_applicable) for probe in self.probes]
        parent_rows = [
            [
                int(_candidate_context_matches(parent, list(probe.context_tags))
                    == probe.expected_applicable)
                for probe in self.probes
            ]
            for parent_id in candidate.parent_candidate_ids
            if (parent := state.unnamed_concept_candidates.get(parent_id)) is not None
        ]
        if not parent_rows:
            return self._record(candidate.id, False, "missing_parent")
        strongest_parent = max(parent_rows, key=sum)
        negative_indexes = [
            index for index, probe in enumerate(self.probes)
            if not probe.expected_applicable
        ]
        candidate_false = sum(1 - proposed[index] for index in negative_indexes)
        parent_false = sum(1 - strongest_parent[index] for index in negative_indexes)
        baseline_gain = (sum(proposed) - sum(baseline)) / len(proposed)
        parent_gain = (sum(proposed) - sum(strongest_parent)) / len(proposed)
        baseline_lower = self._bootstrap_lower(proposed, baseline, self.seed)
        parent_lower = self._bootstrap_lower(proposed, strongest_parent, self.seed + 1)
        passed = (
            baseline_gain >= self.minimum_gain
            and parent_gain >= self.minimum_gain
            and baseline_lower > 0.0
            and parent_lower > 0.0
            and candidate_false <= parent_false
        )
        self.decisions.append({
            "candidate_id": candidate.id,
            "accepted": passed,
            "reason": "gain_confirmed" if passed else "insufficient_gain",
            "development_cases": len(self.probes),
            "candidate_accuracy": sum(proposed) / len(proposed),
            "baseline_gain": baseline_gain,
            "parent_gain": parent_gain,
            "baseline_ci_lower": baseline_lower,
            "parent_ci_lower": parent_lower,
            "candidate_false_generalizations": candidate_false,
            "parent_false_generalizations": parent_false,
        })
        return passed

    def _record(self, candidate_id: str, accepted: bool, reason: str) -> bool:
        self.decisions.append({
            "candidate_id": candidate_id,
            "accepted": accepted,
            "reason": reason,
        })
        return accepted

    def _bootstrap_lower(self, left: list[int], right: list[int], seed: int) -> float:
        rng = random.Random(seed)
        differences = [left[index] - right[index] for index in range(len(left))]
        estimates = sorted(
            sum(differences[rng.randrange(len(differences))] for _ in differences)
            / len(differences)
            for _ in range(self.bootstrap_samples)
        )
        return estimates[int(self.bootstrap_samples * 0.025)]
