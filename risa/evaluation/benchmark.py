from __future__ import annotations

from collections import Counter, deque
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from pathlib import Path
import random
import time
from typing import Any

from risa.core.models import Event, PredictionQuery
from risa.core.state import RisaState
from risa.engine.composer import forecast_next_effects
from risa.engine.graph_builder import normalize_label
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import TrainingOptions, train_events


Outcome = tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkManifest:
    benchmark_version: str
    seeds: tuple[int, ...]
    held_out_episodes_per_split: int
    development_fraction: float
    max_plan_steps: int
    online_replay_budget: int
    online_replay_interval: int
    splits: tuple[str, ...]
    methods: tuple[str, ...]


@dataclass(frozen=True)
class TransitionRule:
    action: str
    effects: Outcome
    target: str = ""
    target_roles: Outcome = ()
    context: Outcome = ()
    preconditions: Outcome = ()
    consumed_states: Outcome = ()


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    split: str
    partition: str
    actor: str
    action: str = ""
    target: str = ""
    target_roles: Outcome = ()
    context: Outcome = ()
    expected_effects: Outcome | None = None
    observation_mask: Outcome = ()
    candidate_actions: Outcome = ()
    goal_states: Outcome = ()
    forbidden_states: Outcome = ()
    max_steps: int = 1
    phase: str = ""
    observation_delay: int = 0


@dataclass
class GeneratedBenchmark:
    training_events: list[Event]
    static_cases: list[EvaluationCase]
    drift_cases: list[EvaluationCase]
    oracle_rules: list[TransitionRule]
    audit: dict[str, int]


@dataclass
class MetricAccumulator:
    successes: list[int] = field(default_factory=list)
    abstentions: int = 0
    covered_successes: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def record(
        self,
        case: EvaluationCase,
        predicted: Outcome,
        success: bool,
        elapsed_seconds: float,
    ) -> None:
        self.successes.append(int(success))
        self.abstentions += int(not predicted)
        self.covered_successes += int(bool(predicted) and success)
        self.elapsed_seconds += elapsed_seconds
        if not success and len(self.failures) < 5:
            self.failures.append(
                {
                    "case_id": case.id,
                    "expected": list(case.expected_effects or case.goal_states),
                    "predicted": list(predicted),
                    "mask": list(case.observation_mask),
                    "phase": case.phase,
                }
            )

    def summarize(self, stored_bytes: int) -> dict[str, Any]:
        total = len(self.successes)
        success_count = sum(self.successes)
        covered = total - self.abstentions
        lower, upper = _wilson_interval(success_count, total)
        return {
            "episodes": total,
            "success_rate": _ratio(success_count, total),
            "success_95ci": [lower, upper],
            "coverage": _ratio(covered, total),
            "covered_accuracy": _ratio(self.covered_successes, covered),
            "abstentions": self.abstentions,
            "elapsed_ms": round(self.elapsed_seconds * 1000.0, 3),
            "mean_episode_ms": round(self.elapsed_seconds * 1000.0 / max(total, 1), 6),
            "stored_bytes": stored_bytes,
            "failure_examples": self.failures,
        }


class LearnedModel:
    def __init__(self, name: str) -> None:
        self.name = name
        self.outcome_counts: dict[tuple[str, ...], Counter[Outcome]] = {}
        self.rules: dict[tuple[str, ...], Counter[TransitionRule]] = {}

    def observe(self, event: Event) -> None:
        action = normalize_label(event.action)
        actor = normalize_label(event.actor)
        target = normalize_label(event.target or "")
        context = tuple(sorted(normalize_label(tag) for tag in event.context_tags))
        outcome = tuple(sorted({normalize_label(effect) for effect in event.observed_effects}))
        rule = TransitionRule(
            action=action,
            effects=outcome,
            target=target,
            target_roles=tuple(sorted(normalize_label(role) for role in event.target_roles)),
            context=context,
            preconditions=tuple(sorted(normalize_label(item) for item in event.preconditions)),
            consumed_states=tuple(sorted(normalize_label(item) for item in event.consumed_states)),
        )
        if self.name == "frequency":
            prediction_key = (action,)
            rule_key = (action,)
        elif self.name == "exact_retrieval":
            prediction_key = (actor, action, target, *context)
            rule_key = (actor, action, target, *context)
        else:
            prediction_key = (action, target, *context)
            rule_key = (action, target, *context)
        self.outcome_counts.setdefault(prediction_key, Counter())[outcome] += 1
        self.rules.setdefault(rule_key, Counter())[rule] += 1

    def predict(self, case: EvaluationCase) -> Outcome:
        context = tuple(sorted(case.context))
        if self.name == "frequency":
            key = (case.action,)
        elif self.name == "exact_retrieval":
            key = (case.actor, case.action, case.target, *context)
        else:
            key = (case.action, case.target, *context)
        return _counter_mode(self.outcome_counts.get(key, Counter()))

    def transition_candidates(
        self,
        case: EvaluationCase,
        action: str,
        current_states: set[str],
    ) -> list[TransitionRule]:
        context = tuple(sorted(case.context))
        if self.name == "frequency":
            key = (action,)
        elif self.name == "exact_retrieval":
            key = (case.actor, action, case.target, *context)
        else:
            key = (action, case.target, *context)
        candidates = []
        for rule in self.rules.get(key, Counter()):
            if self.name == "frequency" or set(rule.preconditions).issubset(current_states):
                candidates.append(rule)
        return candidates

    def stored_bytes(self) -> int:
        payload = {
            "outcomes": {
                repr(key): {repr(outcome): count for outcome, count in counts.items()}
                for key, counts in self.outcome_counts.items()
            },
            "rules": {
                repr(key): {repr(rule): count for rule, count in counts.items()}
                for key, counts in self.rules.items()
            },
        }
        return len(json.dumps(payload, sort_keys=True).encode("utf-8"))


class RisaEvaluationModel:
    def __init__(
        self,
        name: str,
        replay_max_events: int,
        replay_interval: int,
        enable_g2_features: bool,
    ) -> None:
        self.name = name
        self.state = RisaState()
        self.observed_online_events = 0
        self.replay_interval = replay_interval
        self.enable_role_binding = enable_g2_features and name != "risa_no_role_binding"
        self.enable_change_adaptation = (
            enable_g2_features and name != "risa_no_change_adaptation"
        )
        self.enable_candidate_concepts = (
            enable_g2_features and name != "risa_no_candidate_concepts"
        )
        self.options = TrainingOptions(
            enable_metabolism=name != "risa_no_metabolism",
            enable_replay=name != "risa_no_replay",
            enable_adaptation=name != "risa_no_splitting",
            enable_coactivation=name != "risa_no_coactivation",
            replay_max_events=replay_max_events,
        )

    def observe_many(self, events: list[Event]) -> None:
        train_events(self.state, events, options=self.options)
        self._apply_readout_ablation()

    def observe(self, event: Event) -> None:
        self.observed_online_events += 1
        enable_scheduled_replay = (
            self.options.enable_replay
            and self.observed_online_events % self.replay_interval == 0
        )
        online_options = TrainingOptions(
            enable_metabolism=self.options.enable_metabolism,
            enable_replay=enable_scheduled_replay,
            enable_adaptation=self.options.enable_adaptation,
            enable_coactivation=self.options.enable_coactivation,
            replay_max_events=self.options.replay_max_events,
        )
        train_events(self.state, [event], options=online_options)
        self._apply_readout_ablation()

    def _apply_readout_ablation(self) -> None:
        if self.name == "risa_no_structural_sharing":
            self.state.structural_patterns.clear()
            self.state.structural_primitives.clear()
            self.state.structure_deltas.clear()
            self.state.concept_members.clear()

    def predict(self, case: EvaluationCase) -> Outcome:
        result = predict_next_effect(
            self.state,
            PredictionQuery(
                actor=case.actor,
                action=case.action,
                target=case.target or None,
                context_tags=list(case.context),
                target_roles=list(case.target_roles) if self.enable_role_binding else [],
                enable_change_adaptation=self.enable_change_adaptation,
                enable_candidate_concepts=self.enable_candidate_concepts,
            ),
        )
        return tuple(sorted(result.predicted_effects))

    def transition_candidates(
        self,
        case: EvaluationCase,
        action: str,
        current_states: set[str],
    ) -> list[TransitionRule]:
        candidates = forecast_next_effects(
            self.state,
            action=action,
            current_states=sorted(current_states),
            context_tags=list(case.context),
            max_candidates=16,
            target_roles=list(case.target_roles) if self.enable_role_binding else [],
            enable_candidate_concepts=self.enable_candidate_concepts,
        )
        return [
            TransitionRule(
                action=action,
                effects=tuple(candidate.added_states),
                consumed_states=tuple(candidate.removed_states),
            )
            for candidate in candidates
        ]

    def stored_bytes(self) -> int:
        return len(json.dumps(self.state.to_dict(), sort_keys=True).encode("utf-8"))


class OracleModel:
    name = "oracle"

    def __init__(self, rules: list[TransitionRule]) -> None:
        self.rules = rules

    def predict(self, case: EvaluationCase) -> Outcome:
        return tuple(case.expected_effects or ())

    def transition_candidates(
        self,
        case: EvaluationCase,
        action: str,
        current_states: set[str],
    ) -> list[TransitionRule]:
        return [
            rule
            for rule in self.rules
            if rule.action == action
            and (not rule.target or rule.target == case.target)
            and set(rule.preconditions).issubset(current_states)
        ]

    def stored_bytes(self) -> int:
        return len(json.dumps([asdict(rule) for rule in self.rules], sort_keys=True).encode("utf-8"))


def load_manifest(path: str | Path) -> BenchmarkManifest:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    manifest = BenchmarkManifest(
        benchmark_version=str(data["benchmark_version"]),
        seeds=tuple(int(seed) for seed in data["seeds"]),
        held_out_episodes_per_split=int(data["held_out_episodes_per_split"]),
        development_fraction=float(data["development_fraction"]),
        max_plan_steps=int(data["max_plan_steps"]),
        online_replay_budget=int(data["online_replay_budget"]),
        online_replay_interval=int(data["online_replay_interval"]),
        splits=tuple(str(split) for split in data["splits"]),
        methods=tuple(str(method) for method in data["methods"]),
    )
    if manifest.held_out_episodes_per_split < 1:
        raise ValueError("held_out_episodes_per_split must be positive")
    if manifest.online_replay_budget < 0 or manifest.online_replay_interval < 1:
        raise ValueError("online replay budget must be non-negative and interval positive")
    if not 0.0 <= manifest.development_fraction <= 1.0:
        raise ValueError("development_fraction must be between zero and one")
    return manifest


def run_benchmark(manifest: BenchmarkManifest) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    manifest_digest = hashlib.sha256(
        json.dumps(asdict(manifest), sort_keys=True).encode("utf-8")
    ).hexdigest()

    for seed in manifest.seeds:
        generated = generate_benchmark(seed, manifest)
        audits.append({"seed": seed, **generated.audit})
        models = _build_models(
            manifest.methods,
            generated.oracle_rules,
            manifest.online_replay_budget,
            manifest.online_replay_interval,
            manifest.benchmark_version.startswith("g2"),
        )
        for model in models:
            training_started = time.perf_counter()
            if isinstance(model, RisaEvaluationModel):
                model.observe_many(generated.training_events)
            elif isinstance(model, LearnedModel):
                for event in generated.training_events:
                    model.observe(event)
            training_seconds = time.perf_counter() - training_started
            static_metrics = _evaluate_static(model, generated.static_cases, generated.oracle_rules)
            for (split, partition), accumulator in sorted(static_metrics.items()):
                summary = accumulator.summarize(model.stored_bytes())
                summary.update(
                    {
                        "seed": seed,
                        "method": model.name,
                        "split": split,
                        "partition": partition,
                        "training_ms": round(training_seconds * 1000.0, 3),
                    }
                )
                rows.append(summary)

        drift_models = _build_models(
            manifest.methods,
            generated.oracle_rules,
            manifest.online_replay_budget,
            manifest.online_replay_interval,
            manifest.benchmark_version.startswith("g2"),
        )
        for model in drift_models:
            if isinstance(model, RisaEvaluationModel):
                model.observe_many(generated.training_events)
            elif isinstance(model, LearnedModel):
                for event in generated.training_events:
                    model.observe(event)
            drift_rows = _evaluate_drift(model, generated.drift_cases, seed)
            rows.extend(drift_rows)

    return {
        "benchmark_version": manifest.benchmark_version,
        "manifest_sha256": manifest_digest,
        "manifest": _jsonable(asdict(manifest)),
        "leakage_audit": audits,
        "rows": rows,
        "aggregate": _aggregate_rows(rows),
    }


def generate_benchmark(seed: int, manifest: BenchmarkManifest) -> GeneratedBenchmark:
    rng = random.Random(seed)
    enable_g2_features = manifest.benchmark_version.startswith("g2")
    training: list[Event] = []
    rules = [
        TransitionRule("signal", ("noticed",)),
        TransitionRule(
            "inspect",
            ("warm",),
            target="heater",
            target_roles=("heating_device",) if enable_g2_features else (),
        ),
        TransitionRule(
            "inspect",
            ("cold",),
            target="ice",
            target_roles=("cooling_device",) if enable_g2_features else (),
        ),
        TransitionRule("collect_key", ("key",)),
        TransitionRule("unlock_gate", ("gate_open",), preconditions=("key",), consumed_states=("key",)),
        TransitionRule("enter_room", ("inside",), preconditions=("gate_open",)),
        TransitionRule("activate", ("lit", "warm"), target="lamp"),
        TransitionRule("route_shortcut", ("goal", "danger")),
        TransitionRule("route_safe", ("goal",)),
        TransitionRule("toss", ("heads",)),
        TransitionRule("toss", ("tails",)),
        TransitionRule("tune", ("stable",), target="device"),
        TransitionRule("tune", ("unstable",), target="device"),
    ]
    timestamp = 1
    for repeat in range(3):
        for rule in [rule for rule in rules if rule.action not in {"toss", "tune"}]:
            training.append(_event_for_rule(rule, seed, repeat, timestamp))
            timestamp += 1
    for repeat, effect in enumerate(["heads"] * 7 + ["tails"] * 3):
        rule = TransitionRule("toss", (effect,))
        training.append(_event_for_rule(rule, seed, repeat + 10, timestamp))
        timestamp += 1
    for repeat in range(5):
        training.append(
            _event_for_rule(
                next(rule for rule in rules if rule.action == "tune" and rule.effects == ("stable",)),
                seed,
                repeat + 30,
                timestamp,
                actor="drift_actor",
            )
        )
        timestamp += 1

    learned_rules = [
        TransitionRule("collect_token", ("token",)),
        TransitionRule(
            "open_portal", ("portal_open",), preconditions=("token",),
            consumed_states=("token",),
        ),
        TransitionRule(
            "cross_portal", ("crossed",), preconditions=("portal_open",)
        ),
    ]
    if enable_g2_features:
        for repeat in range(3):
            for rule in learned_rules:
                training.append(
                    Event(
                        id=f"learned-success:{seed}:{rule.action}:{repeat}",
                        timestamp=timestamp,
                        actor=f"train_actor_{repeat}",
                        action=rule.action,
                        observed_states_before=list(rule.preconditions),
                        before_state_observed=True,
                        observed_effects=list(rule.effects),
                        episode_id=f"learned-success:{seed}:{rule.action}:{repeat}",
                        source="g2-before-after-generator",
                    )
                )
                timestamp += 1
        for repeat in range(2):
            for rule in learned_rules[1:]:
                training.append(
                    Event(
                        id=f"learned-failure:{seed}:{rule.action}:{repeat}",
                        timestamp=timestamp,
                        actor=f"train_actor_{repeat}",
                        action=rule.action,
                        observed_states_before=[],
                        before_state_observed=True,
                        observed_effects=[],
                        transition_succeeded=False,
                        episode_id=f"learned-failure:{seed}:{rule.action}:{repeat}",
                        source="g2-before-after-generator",
                    )
                )
                timestamp += 1
        rules.extend(learned_rules)

    static_cases: list[EvaluationCase] = []
    drift_cases: list[EvaluationCase] = []
    count = manifest.held_out_episodes_per_split
    development_slots = round(10 * manifest.development_fraction)
    for index in range(count):
        partition = "development" if index % 10 < development_slots else "final"
        actor = f"heldout_actor_{seed}_{index}"
        static_cases.append(
            EvaluationCase(
                id=f"control:{seed}:{index}", split="control", partition=partition,
                actor=actor, action="signal", expected_effects=("noticed",),
            )
        )

        if enable_g2_features:
            static_cases.append(
                EvaluationCase(
                    id=f"composition_learned:{seed}:{index}",
                    split="composition_learned",
                    partition=partition,
                    actor=actor,
                    candidate_actions=("cross_portal", "collect_token", "open_portal"),
                    goal_states=("crossed",),
                    max_steps=manifest.max_plan_steps,
                )
            )

        if index % 4 == 0:
            target, target_roles, outcome = "radiator", ("heating_device",), ("warm",)
        elif index % 2 == 0:
            target, target_roles, outcome = "heater", ("heating_device",), ("warm",)
        else:
            target, target_roles, outcome = "ice", ("cooling_device",), ("cold",)
        static_cases.append(
            EvaluationCase(
                id=f"binding:{seed}:{index}", split="binding", partition=partition,
                actor=actor, action="inspect", target=target,
                target_roles=target_roles if enable_g2_features else (),
                expected_effects=outcome,
            )
        )

        static_cases.append(
            EvaluationCase(
                id=f"composition:{seed}:{index}", split="composition", partition=partition,
                actor=actor, candidate_actions=("enter_room", "collect_key", "unlock_gate"),
                goal_states=("inside",), max_steps=manifest.max_plan_steps,
            )
        )

        uncertainty_kind = index % 4
        if uncertainty_kind == 0:
            uncertainty = EvaluationCase(
                id=f"uncertainty:{seed}:{index}", split="uncertainty", partition=partition,
                actor=actor, action=f"unknown_{index}", expected_effects=None,
            )
        elif uncertainty_kind == 1:
            uncertainty = EvaluationCase(
                id=f"uncertainty:{seed}:{index}", split="uncertainty", partition=partition,
                actor=actor, action="activate", target="lamp", expected_effects=("lit", "warm"),
                observation_mask=("lit",),
            )
        elif uncertainty_kind == 2:
            actual = "heads" if rng.random() < 0.7 else "tails"
            uncertainty = EvaluationCase(
                id=f"uncertainty:{seed}:{index}", split="uncertainty", partition=partition,
                actor=actor, action="toss", expected_effects=(actual,),
            )
        else:
            uncertainty = EvaluationCase(
                id=f"uncertainty:{seed}:{index}", split="uncertainty", partition=partition,
                actor=actor, candidate_actions=("route_shortcut", "route_safe"),
                goal_states=("goal",), forbidden_states=("danger",),
                max_steps=1,
            )
        static_cases.append(uncertainty)

        if index < int(count * 0.35):
            phase, outcome = "A1", ("stable",)
        elif index < int(count * 0.65):
            phase, outcome = "B", ("unstable",)
        else:
            phase, outcome = "A2", ("stable",)
        drift_cases.append(
            EvaluationCase(
                id=f"drift:{seed}:{index}", split="drift", partition=partition,
                actor="drift_actor", action="tune", target="device",
                context=("exception",) if phase == "B" and index % 3 == 0 else (),
                expected_effects=outcome, phase=phase,
                observation_delay=3 if phase == "B" and index % 10 == 0 else 0,
            )
        )

    train_ids = {event.id for event in training}
    eval_ids = {case.id for case in [*static_cases, *drift_cases]}
    audit = {
        "training_event_count": len(training),
        "held_out_case_count": len(static_cases) + len(drift_cases),
        "event_id_overlap": len(train_ids & eval_ids),
        "duplicate_training_ids": len(training) - len(train_ids),
        "composition_temporal_edges_supplied": 0,
        "allowed_control_isomorphisms": count,
    }
    if audit["event_id_overlap"] or audit["duplicate_training_ids"]:
        raise ValueError(f"benchmark leakage audit failed: {audit}")
    return GeneratedBenchmark(training, static_cases, drift_cases, rules, audit)


def _event_for_rule(
    rule: TransitionRule,
    seed: int,
    repeat: int,
    timestamp: int,
    actor: str | None = None,
) -> Event:
    return Event(
        id=f"train:{seed}:{rule.action}:{rule.target}:{repeat}",
        timestamp=timestamp,
        actor=actor or f"train_actor_{repeat % 3}",
        action=rule.action,
        target=rule.target or None,
        target_roles=list(rule.target_roles),
        preconditions=list(rule.preconditions),
        consumed_states=list(rule.consumed_states),
        observed_effects=list(rule.effects),
        episode_id=f"train:{seed}:{rule.action}:{rule.target}:{repeat}",
        source="g1-generator",
    )


def _build_models(
    methods: tuple[str, ...],
    rules: list[TransitionRule],
    replay_max_events: int,
    replay_interval: int,
    enable_g2_features: bool,
) -> list[Any]:
    models = []
    for method in methods:
        if method in {"frequency", "exact_retrieval", "grounded_transition"}:
            models.append(LearnedModel(method))
        elif method == "oracle":
            models.append(OracleModel(rules))
        elif method.startswith("risa"):
            models.append(
                RisaEvaluationModel(
                    method,
                    replay_max_events,
                    replay_interval,
                    enable_g2_features,
                )
            )
        else:
            raise ValueError(f"unknown evaluation method: {method}")
    return models


def _evaluate_static(
    model: Any,
    cases: list[EvaluationCase],
    oracle_rules: list[TransitionRule],
) -> dict[tuple[str, str], MetricAccumulator]:
    metrics: dict[tuple[str, str], MetricAccumulator] = {}
    for case in cases:
        accumulator = metrics.setdefault((case.split, case.partition), MetricAccumulator())
        started = time.perf_counter()
        if case.candidate_actions:
            sequence = _plan(model, case)
            success = _execute_oracle(sequence, oracle_rules, case)
            predicted = tuple(sequence)
        else:
            predicted = model.predict(case)
            success = _prediction_success(case, predicted)
        accumulator.record(case, predicted, success, time.perf_counter() - started)
    return metrics


def _evaluate_drift(model: Any, cases: list[EvaluationCase], seed: int) -> list[dict[str, Any]]:
    metrics: dict[tuple[str, str], MetricAccumulator] = {}
    phase_successes: dict[str, list[int]] = {}
    pending_observations: list[tuple[int, Event]] = []
    for index, case in enumerate(cases):
        if not isinstance(model, OracleModel):
            ready = [item for item in pending_observations if item[0] <= index]
            pending_observations = [item for item in pending_observations if item[0] > index]
            for _, ready_event in ready:
                model.observe(ready_event)
        accumulator = metrics.setdefault((case.phase, case.partition), MetricAccumulator())
        started = time.perf_counter()
        predicted = model.predict(case)
        success = _prediction_success(case, predicted)
        accumulator.record(
            case,
            predicted,
            success,
            time.perf_counter() - started,
        )
        phase_successes.setdefault(case.phase, []).append(int(success))
        if not isinstance(model, OracleModel):
            event = Event(
                id=f"online:{model.name}:{case.id}", timestamp=10_000 + index,
                actor=case.actor, action=case.action, target=case.target,
                observed_effects=list(case.expected_effects or ()),
                context_tags=list(case.context), episode_id=case.id,
                source="g1-online-drift",
            )
            if case.observation_delay:
                pending_observations.append((index + case.observation_delay, event))
            elif isinstance(model, RisaEvaluationModel):
                model.observe(event)
            else:
                model.observe(event)

    a1_rate = _ratio(sum(phase_successes.get("A1", [])), len(phase_successes.get("A1", [])))
    a2_rate = _ratio(sum(phase_successes.get("A2", [])), len(phase_successes.get("A2", [])))
    recovery = {
        "B": _recovery_steps(phase_successes.get("B", [])),
        "A2": _recovery_steps(phase_successes.get("A2", [])),
    }
    rows = []
    for (phase, partition), accumulator in sorted(metrics.items()):
        summary = accumulator.summarize(model.stored_bytes())
        summary.update(
            {
                "seed": seed,
                "method": model.name,
                "split": "drift",
                "partition": partition,
                "phase": phase,
                "training_ms": 0.0,
                "recovery_steps_to_80pct": recovery.get(phase),
                "forgetting_delta_a1_minus_a2": round(a1_rate - a2_rate, 6),
            }
        )
        rows.append(summary)
    return rows


def _plan(model: Any, case: EvaluationCase) -> list[str]:
    queue = deque([(set(), [])])
    visited = {frozenset()}
    while queue:
        states, sequence = queue.popleft()
        if set(case.goal_states).issubset(states):
            return sequence
        if len(sequence) >= case.max_steps:
            continue
        for action in case.candidate_actions:
            for rule in model.transition_candidates(case, action, states):
                next_states = (states - set(rule.consumed_states)) | set(rule.effects)
                if set(case.forbidden_states).intersection(next_states):
                    continue
                key = frozenset(next_states)
                if key in visited:
                    continue
                visited.add(key)
                queue.append((next_states, [*sequence, action]))
    return []


def _execute_oracle(
    sequence: list[str],
    rules: list[TransitionRule],
    case: EvaluationCase,
) -> bool:
    states: set[str] = set()
    for action in sequence:
        applicable = next(
            (
                rule
                for rule in rules
                if rule.action == action
                and (not rule.target or rule.target == case.target)
                and set(rule.preconditions).issubset(states)
            ),
            None,
        )
        if applicable is None:
            return False
        states.difference_update(applicable.consumed_states)
        states.update(applicable.effects)
        if set(case.forbidden_states).intersection(states):
            return False
    return set(case.goal_states).issubset(states)


def _prediction_success(case: EvaluationCase, predicted: Outcome) -> bool:
    if case.expected_effects is None:
        return not predicted
    if case.observation_mask:
        return set(case.observation_mask).issubset(predicted)
    return set(predicted) == set(case.expected_effects)


def _counter_mode(counter: Counter[Any]) -> Any:
    if not counter:
        return ()
    return sorted(counter, key=lambda item: (-counter[item], repr(item)))[0]


def _wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    z = 1.959963984540054
    rate = successes / total
    denominator = 1.0 + (z * z / total)
    center = (rate + (z * z / (2.0 * total))) / denominator
    margin = (
        z
        * math.sqrt((rate * (1.0 - rate) / total) + (z * z / (4.0 * total * total)))
        / denominator
    )
    return round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _recovery_steps(values: list[int], window: int = 10, threshold: float = 0.8) -> int | None:
    if not values:
        return None
    effective_window = min(window, len(values))
    for end in range(effective_window, len(values) + 1):
        if sum(values[end - effective_window : end]) / effective_window >= threshold:
            return end
    return None


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            row["method"], row["split"], row["partition"], row.get("phase", ""),
        )
        grouped.setdefault(key, []).append(row)
    aggregate = []
    for (method, split, partition, phase), members in sorted(grouped.items()):
        episode_count = sum(item["episodes"] for item in members)
        successes = sum(round(item["success_rate"] * item["episodes"]) for item in members)
        lower, upper = _wilson_interval(successes, episode_count)
        aggregate.append(
            {
                "method": method,
                "split": split,
                "partition": partition,
                "phase": phase,
                "seeds": len(members),
                "episodes": episode_count,
                "success_rate": _ratio(successes, episode_count),
                "success_95ci": [lower, upper],
                "mean_coverage": round(sum(item["coverage"] for item in members) / len(members), 6),
                "mean_episode_ms": round(sum(item["mean_episode_ms"] for item in members) / len(members), 6),
                "mean_stored_bytes": round(sum(item["stored_bytes"] for item in members) / len(members)),
            }
        )
    return aggregate


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value
