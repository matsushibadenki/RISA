from __future__ import annotations

import math

from risa.core.models import (
    BranchEvaluation,
    BranchEvaluationReport,
    GoalSpecification,
    TrajectoryBranch,
)
from risa.engine.graph_builder import normalize_label


def evaluate_branches(
    branches: list[TrajectoryBranch],
    goal_states: list[str] | None = None,
    avoid_states: list[str] | None = None,
    variable_cost_weights: dict[str, float] | None = None,
    goal_specification: GoalSpecification | None = None,
    search_diagnostics: dict[str, int] | None = None,
) -> BranchEvaluationReport:
    """Rank simulated futures while keeping every utility component inspectable."""
    goal_spec = _normalize_goal_specification(
        goal_specification
        or GoalSpecification(any_state_groups=[list(goal_states or [])])
    )
    avoided = {normalize_label(state) for state in avoid_states or []}
    cost_weights = {
        normalize_label(name): _finite_value(weight, f"cost weight '{name}'")
        for name, weight in (variable_cost_weights or {}).items()
    }
    if any(weight < 0.0 for weight in cost_weights.values()):
        raise ValueError("variable cost weights must be non-negative")
    evaluations = [
        _evaluate_branch(branch, goal_spec, avoided, cost_weights) for branch in branches
    ]
    evaluations.sort(
        key=lambda item: (
            not (item.goal_satisfied and item.hard_constraints_satisfied),
            not item.hard_constraints_satisfied,
            -item.goal_score,
            -item.utility,
            item.branch.id,
        )
    )
    selected = next(
        (
            item
            for item in evaluations
            if item.goal_satisfied and item.hard_constraints_satisfied
        ),
        None,
    )
    return BranchEvaluationReport(
        selected_branch_id=selected.branch.id if selected else None,
        evaluations=evaluations,
        search_diagnostics=search_diagnostics or {},
    )


def _evaluate_branch(
    branch: TrajectoryBranch,
    goal_spec: GoalSpecification,
    avoided: set[str],
    cost_weights: dict[str, float],
) -> BranchEvaluation:
    current_states = set(branch.current_states)
    required = set(goal_spec.required_states)
    missing_required = sorted(required - current_states)
    matched_goals = set(required.intersection(current_states))
    unsatisfied_groups: list[list[str]] = []
    satisfied_clauses = len(required) - len(missing_required)
    total_clauses = len(required)
    for group in goal_spec.any_state_groups:
        choices = set(group)
        matches = current_states.intersection(choices)
        total_clauses += 1
        if matches:
            satisfied_clauses += 1
            matched_goals.update(matches)
        else:
            unsatisfied_groups.append(list(group))

    unsatisfied_variables: list[str] = []
    for name, minimum in goal_spec.minimum_variables.items():
        total_clauses += 1
        actual = branch.current_variables.get(name)
        if actual is not None and actual >= minimum:
            satisfied_clauses += 1
        else:
            unsatisfied_variables.append(f"{name}>={minimum:g}")
    for name, maximum in goal_spec.maximum_variables.items():
        total_clauses += 1
        actual = branch.current_variables.get(name)
        if actual is not None and actual <= maximum:
            satisfied_clauses += 1
        else:
            unsatisfied_variables.append(f"{name}<={maximum:g}")
    goal_score = satisfied_clauses / total_clauses if total_clauses else 0.0

    encountered_states = set(branch.current_states)
    for step in branch.steps:
        encountered_states.update(step.states_before)
        encountered_states.update(step.states_after)
    encountered_avoid = sorted(encountered_states.intersection(avoided))
    risk_penalty = len(encountered_avoid) / max(1, len(avoided))
    violated_constraints = [
        f"forbidden_state:{state}"
        for state in sorted(encountered_states.intersection(goal_spec.forbidden_states))
    ]
    hard_constraints_satisfied = not violated_constraints
    goal_satisfied = (
        total_clauses > 0
        and not missing_required
        and not unsatisfied_groups
        and not unsatisfied_variables
    )

    initial_variables = branch.steps[0].variables_before if branch.steps else branch.current_variables
    variable_costs = {
        name: max(0.0, initial_variables.get(name, 0.0) - branch.current_variables.get(name, 0.0))
        * weight
        for name, weight in cost_weights.items()
    }
    weighted_cost = sum(variable_costs.values())
    cost_penalty = 1.0 - math.exp(-weighted_cost)

    step_count = len(branch.steps)
    confidence_score = (
        max(0.0, min(1.0, branch.score ** (1.0 / step_count)))
        if step_count
        else 0.0
    )
    utility = (
        (0.55 * goal_score)
        + (0.20 * confidence_score)
        - (0.15 * cost_penalty)
        - (0.10 * risk_penalty)
    )
    return BranchEvaluation(
        branch=branch,
        utility=round(utility, 6),
        goal_score=round(goal_score, 6),
        confidence_score=round(confidence_score, 6),
        cost_penalty=round(cost_penalty, 6),
        risk_penalty=round(risk_penalty, 6),
        goal_satisfied=goal_satisfied,
        hard_constraints_satisfied=hard_constraints_satisfied,
        matched_goal_states=sorted(matched_goals),
        missing_required_states=missing_required,
        unsatisfied_any_state_groups=unsatisfied_groups,
        unsatisfied_variable_conditions=unsatisfied_variables,
        violated_hard_constraints=violated_constraints,
        encountered_avoid_states=encountered_avoid,
        variable_costs={name: round(value, 6) for name, value in sorted(variable_costs.items())},
        explanation=(
            f"goal={goal_score:.3f} satisfied={goal_satisfied}, "
            f"hard_constraints={hard_constraints_satisfied}, confidence={confidence_score:.3f}, "
            f"cost={cost_penalty:.3f}, risk={risk_penalty:.3f}"
        ),
    )


def _normalize_goal_specification(specification: GoalSpecification) -> GoalSpecification:
    minimum_variables = {
        normalize_label(name): _finite_value(value, f"minimum variable '{name}'")
        for name, value in specification.minimum_variables.items()
    }
    maximum_variables = {
        normalize_label(name): _finite_value(value, f"maximum variable '{name}'")
        for name, value in specification.maximum_variables.items()
    }
    for name in minimum_variables.keys() & maximum_variables.keys():
        if minimum_variables[name] > maximum_variables[name]:
            raise ValueError(f"goal variable '{name}' has minimum greater than maximum")
    return GoalSpecification(
        required_states=sorted(
            {normalize_label(state) for state in specification.required_states}
        ),
        any_state_groups=[
            sorted({normalize_label(state) for state in group})
            for group in specification.any_state_groups
            if group
        ],
        minimum_variables=minimum_variables,
        maximum_variables=maximum_variables,
        forbidden_states=sorted(
            {normalize_label(state) for state in specification.forbidden_states}
        ),
    )


def _finite_value(value: float, label: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{label} must be finite")
    return parsed
