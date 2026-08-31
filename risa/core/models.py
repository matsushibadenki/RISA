from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class StateVariableSpec:
    unit: str = ""
    minimum: float | None = None
    maximum: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Node:
    id: str
    kind: str
    label: str
    attributes: dict[str, str] = field(default_factory=dict)
    abstraction_level: int = 0
    created_at: int = 0
    usage_count: int = 0
    stability: float = 0.0
    recent_activity: float = 0.0
    energy: float = 0.5
    last_activated_at: int = 0
    dormant: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Edge:
    source: str
    target: str
    relation_type: str
    context_tags: tuple[str, ...] = ()
    evidence_count: int = 0
    reliability: float = 0.0
    plasticity: float = 1.0
    last_updated: int = 0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["context_tags"] = list(self.context_tags)
        return data


@dataclass
class Event:
    id: str
    timestamp: int
    actor: str
    action: str
    target: str | None = None
    preconditions: list[str] = field(default_factory=list)
    consumed_states: list[str] = field(default_factory=list)
    state_group_updates: dict[str, str] = field(default_factory=dict)
    numeric_preconditions: dict[str, float] = field(default_factory=dict)
    state_variable_deltas: dict[str, float] = field(default_factory=dict)
    state_variable_specs: dict[str, StateVariableSpec] = field(default_factory=dict)
    observed_effects: list[str] = field(default_factory=list)
    context_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Episode:
    id: str
    events: list[Event]
    source: str = "unknown"


@dataclass
class Pattern:
    id: str
    signature: str
    event_count: int = 0
    actors: set[str] = field(default_factory=set)
    actions: set[str] = field(default_factory=set)
    effects: set[str] = field(default_factory=set)
    support: int = 0
    context_tags: set[str] = field(default_factory=set)
    validation_score: float = 0.5

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "signature": self.signature,
            "event_count": self.event_count,
            "actors": sorted(self.actors),
            "actions": sorted(self.actions),
            "effects": sorted(self.effects),
            "support": self.support,
            "context_tags": sorted(self.context_tags),
            "validation_score": self.validation_score,
        }


@dataclass
class StructuralPattern:
    id: str
    signature: str
    role_signature: str
    support: int = 0
    actions: set[str] = field(default_factory=set)
    effects: set[str] = field(default_factory=set)
    actors: set[str] = field(default_factory=set)
    context_tags: set[str] = field(default_factory=set)
    member_pattern_ids: set[str] = field(default_factory=set)
    validation_score: float = 0.5

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "signature": self.signature,
            "role_signature": self.role_signature,
            "support": self.support,
            "actions": sorted(self.actions),
            "effects": sorted(self.effects),
            "actors": sorted(self.actors),
            "context_tags": sorted(self.context_tags),
            "member_pattern_ids": sorted(self.member_pattern_ids),
            "validation_score": self.validation_score,
        }


@dataclass
class StructuralPrimitive:
    """A reusable transition factor extracted from repeated event structure."""

    id: str
    relation_type: str
    role_signature: str
    input_conditions: set[str] = field(default_factory=set)
    input_state_conditions: set[str] = field(default_factory=set)
    consumed_states: set[str] = field(default_factory=set)
    state_group_updates: dict[str, str] = field(default_factory=dict)
    numeric_preconditions: dict[str, float] = field(default_factory=dict)
    state_variable_deltas: dict[str, float] = field(default_factory=dict)
    output_state: str = ""
    temporal_constraint: str = "event_to_effect"
    context_tags: set[str] = field(default_factory=set)
    member_pattern_ids: set[str] = field(default_factory=set)
    evidence_event_ids: set[str] = field(default_factory=set)
    support: int = 0
    validation_score: float = 0.5
    reuse_score: float = 0.0
    compression_proxy: float = 0.0
    replay_count: int = 0
    replay_success_count: int = 0
    replay_score: float = 0.5
    deployment_replay_count: int = 0
    deployment_replay_success_count: int = 0
    deployment_replay_score: float = 0.5
    perturbation_replay_count: int = 0
    perturbation_replay_success_count: int = 0
    perturbation_replay_score: float = 0.5
    superseded_by: set[str] = field(default_factory=set)
    adoption_score: float = 0.0
    adopted: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "relation_type": self.relation_type,
            "role_signature": self.role_signature,
            "input_conditions": sorted(self.input_conditions),
            "input_state_conditions": sorted(self.input_state_conditions),
            "consumed_states": sorted(self.consumed_states),
            "state_group_updates": dict(sorted(self.state_group_updates.items())),
            "numeric_preconditions": dict(sorted(self.numeric_preconditions.items())),
            "state_variable_deltas": dict(sorted(self.state_variable_deltas.items())),
            "output_state": self.output_state,
            "temporal_constraint": self.temporal_constraint,
            "context_tags": sorted(self.context_tags),
            "member_pattern_ids": sorted(self.member_pattern_ids),
            "evidence_event_ids": sorted(self.evidence_event_ids),
            "support": self.support,
            "validation_score": self.validation_score,
            "reuse_score": self.reuse_score,
            "compression_proxy": self.compression_proxy,
            "replay_count": self.replay_count,
            "replay_success_count": self.replay_success_count,
            "replay_score": self.replay_score,
            "deployment_replay_count": self.deployment_replay_count,
            "deployment_replay_success_count": self.deployment_replay_success_count,
            "deployment_replay_score": self.deployment_replay_score,
            "perturbation_replay_count": self.perturbation_replay_count,
            "perturbation_replay_success_count": self.perturbation_replay_success_count,
            "perturbation_replay_score": self.perturbation_replay_score,
            "superseded_by": sorted(self.superseded_by),
            "adoption_score": self.adoption_score,
            "adopted": self.adopted,
        }


@dataclass
class StructureDelta:
    id: str
    source_pattern_id: str
    target_pattern_id: str
    role_signature: str
    operations: list[str] = field(default_factory=list)
    support: int = 0
    context_tags: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_pattern_id": self.source_pattern_id,
            "target_pattern_id": self.target_pattern_id,
            "role_signature": self.role_signature,
            "operations": list(self.operations),
            "support": self.support,
            "context_tags": sorted(self.context_tags),
        }


@dataclass
class StructuralAdaptationCandidate:
    primitive_id: str
    reason: str
    proposed_operation: str
    pressure: float
    evidence: dict[str, float | int] = field(default_factory=dict)
    status: str = "proposed"
    result_primitive_ids: list[str] = field(default_factory=list)
    result_structure_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PredictionQuery:
    actor: str
    action: str
    target: str | None = None
    context_tags: list[str] = field(default_factory=list)


@dataclass
class PredictionResult:
    predicted_effects: list[str]
    score: float
    supporting_paths: list[list[str]] = field(default_factory=list)
    evidence_event_ids: list[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CompositionResult:
    target_effect: str
    removed_states: list[str] = field(default_factory=list)
    variable_deltas: dict[str, float] = field(default_factory=dict)
    resulting_variables: dict[str, float] = field(default_factory=dict)
    primitive_ids: list[str] = field(default_factory=list)
    supporting_paths: list[list[str]] = field(default_factory=list)
    score: float = 0.0
    explanation: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReplaySummary:
    replayed_events: int = 0
    successful_events: int = 0
    failed_events: int = 0
    deployment_replayed_events: int = 0
    deployment_successful_events: int = 0
    deployment_failed_events: int = 0
    perturbed_events: int = 0
    perturbation_survived_events: int = 0
    perturbation_failed_events: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrajectoryStep:
    action: str
    effect: str
    primitive_id: str
    states_before: list[str] = field(default_factory=list)
    states_after: list[str] = field(default_factory=list)
    variables_before: dict[str, float] = field(default_factory=dict)
    variables_after: dict[str, float] = field(default_factory=dict)
    removed_states: list[str] = field(default_factory=list)
    score: float = 0.0


@dataclass
class TrajectoryBranch:
    id: str = ""
    steps: list[TrajectoryStep] = field(default_factory=list)
    current_states: list[str] = field(default_factory=list)
    current_variables: dict[str, float] = field(default_factory=dict)
    score: float = 1.0
    terminated_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BranchSimulationReport:
    branches: list[TrajectoryBranch] = field(default_factory=list)
    expanded_candidate_count: int = 0
    constraint_pruned_count: int = 0
    beam_pruned_count: int = 0

    def to_dict(self) -> dict:
        return {
            "branches": [branch.to_dict() for branch in self.branches],
            "expanded_candidate_count": self.expanded_candidate_count,
            "constraint_pruned_count": self.constraint_pruned_count,
            "beam_pruned_count": self.beam_pruned_count,
        }


@dataclass
class SequenceSimulationReport:
    branches: list[TrajectoryBranch] = field(default_factory=list)
    requested_actions: list[str] = field(default_factory=list)
    expanded_candidate_count: int = 0
    constraint_pruned_count: int = 0
    beam_pruned_count: int = 0
    sequence_failed_count: int = 0
    invalid_sequence_edge_count: int = 0

    def to_dict(self) -> dict:
        return {
            "branches": [branch.to_dict() for branch in self.branches],
            "requested_actions": list(self.requested_actions),
            "expanded_candidate_count": self.expanded_candidate_count,
            "constraint_pruned_count": self.constraint_pruned_count,
            "beam_pruned_count": self.beam_pruned_count,
            "sequence_failed_count": self.sequence_failed_count,
            "invalid_sequence_edge_count": self.invalid_sequence_edge_count,
        }


@dataclass
class GoalSpecification:
    required_states: list[str] = field(default_factory=list)
    any_state_groups: list[list[str]] = field(default_factory=list)
    minimum_variables: dict[str, float] = field(default_factory=dict)
    maximum_variables: dict[str, float] = field(default_factory=dict)
    forbidden_states: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlanGraphDependency:
    source_primitive_id: str
    target_primitive_id: str
    required_state: str


@dataclass
class ConjunctivePlanGraph:
    id: str
    primitive_ids: list[str] = field(default_factory=list)
    dependencies: list[PlanGraphDependency] = field(default_factory=list)
    unresolved_states: list[str] = field(default_factory=list)
    action_sequence: list[str] = field(default_factory=list)
    alternative_group_id: str = ""
    selected_producers: dict[str, str] = field(default_factory=dict)
    alternative_choice_count: int = 0
    dependency_depth: int = 0
    alternative_search_truncated: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InterventionSpecification:
    id: str
    start_action: str | None = None
    add_states: list[str] = field(default_factory=list)
    remove_states: list[str] = field(default_factory=list)
    variable_overrides: dict[str, float] = field(default_factory=dict)
    cost: float = 0.0
    generated: bool = False
    generation_reason: str = ""
    evidence_primitive_ids: list[str] = field(default_factory=list)
    suggested_action_sequence: list[str] = field(default_factory=list)
    plan_graph: ConjunctivePlanGraph | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BranchEvaluation:
    branch: TrajectoryBranch
    utility: float
    goal_score: float
    confidence_score: float
    cost_penalty: float
    risk_penalty: float
    goal_satisfied: bool = False
    hard_constraints_satisfied: bool = False
    matched_goal_states: list[str] = field(default_factory=list)
    missing_required_states: list[str] = field(default_factory=list)
    unsatisfied_any_state_groups: list[list[str]] = field(default_factory=list)
    unsatisfied_variable_conditions: list[str] = field(default_factory=list)
    violated_hard_constraints: list[str] = field(default_factory=list)
    encountered_avoid_states: list[str] = field(default_factory=list)
    variable_costs: dict[str, float] = field(default_factory=dict)
    explanation: str = ""

    def to_dict(self) -> dict:
        result = asdict(self)
        result["branch"] = self.branch.to_dict()
        return result


@dataclass
class BranchEvaluationReport:
    selected_branch_id: str | None
    evaluations: list[BranchEvaluation] = field(default_factory=list)
    search_diagnostics: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "selected_branch_id": self.selected_branch_id,
            "evaluations": [evaluation.to_dict() for evaluation in self.evaluations],
            "search_diagnostics": dict(sorted(self.search_diagnostics.items())),
        }


@dataclass
class CounterfactualOutcome:
    intervention: InterventionSpecification
    evaluation: BranchEvaluationReport
    feasible: bool
    intervention_cost_penalty: float
    plan_score: float

    def to_dict(self) -> dict:
        return {
            "intervention": self.intervention.to_dict(),
            "evaluation": self.evaluation.to_dict(),
            "feasible": self.feasible,
            "intervention_cost_penalty": self.intervention_cost_penalty,
            "plan_score": self.plan_score,
        }


@dataclass
class CounterfactualPlanningReport:
    selected_intervention_id: str | None
    selected_branch_id: str | None
    outcomes: list[CounterfactualOutcome] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "selected_intervention_id": self.selected_intervention_id,
            "selected_branch_id": self.selected_branch_id,
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }
