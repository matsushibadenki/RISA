from __future__ import annotations

import json
import math
from itertools import permutations
from pathlib import Path

from risa.core.models import (
    CounterfactualOutcome,
    CounterfactualPlanningReport,
    ConjunctivePlanGraph,
    GoalSpecification,
    InterventionSpecification,
    PlanGraphDependency,
    StructuralPrimitive,
)
from risa.core.state import RisaState
from risa.engine.evaluator import evaluate_branches
from risa.engine.graph_builder import normalize_label
from risa.engine.simulator import (
    simulate_action_sequence_with_diagnostics,
    simulate_branches_with_diagnostics,
)


def parse_interventions(path: str | Path) -> list[InterventionSpecification]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("intervention file must contain a JSON array")
    return [
        InterventionSpecification(
            id=str(item["id"]),
            start_action=item.get("start_action"),
            add_states=list(item.get("add_states", [])),
            remove_states=list(item.get("remove_states", [])),
            variable_overrides={
                str(name): float(value)
                for name, value in item.get("variable_overrides", {}).items()
            },
            cost=float(item.get("cost", 0.0)),
            generated=bool(item.get("generated", False)),
            generation_reason=str(item.get("generation_reason", "")),
            evidence_primitive_ids=list(item.get("evidence_primitive_ids", [])),
            suggested_action_sequence=list(item.get("suggested_action_sequence", [])),
        )
        for item in raw
    ]


def generate_intervention_candidates(
    state: RisaState,
    start_action: str,
    goal_specification: GoalSpecification,
    start_states: list[str] | None = None,
    start_variables: dict[str, float] | None = None,
    context_tags: list[str] | None = None,
    max_candidates: int = 8,
) -> list[InterventionSpecification]:
    """Generate grounded interventions by reversing goal-producing primitives."""
    if max_candidates < 1:
        return []
    baseline_states = {normalize_label(item) for item in start_states or []}
    baseline_variables = {
        normalize_label(name): float(value) for name, value in (start_variables or {}).items()
    }
    context = {normalize_label(tag) for tag in context_tags or []}
    target_states = {
        normalize_label(item) for item in goal_specification.required_states
    }
    for group in goal_specification.any_state_groups:
        target_states.update(normalize_label(item) for item in group)
    forbidden = {normalize_label(item) for item in goal_specification.forbidden_states}
    minimum_variables = {
        normalize_label(name): float(value)
        for name, value in goal_specification.minimum_variables.items()
    }
    candidates: list[InterventionSpecification] = []

    for primitive in state.structural_primitives.values():
        if primitive.output_state not in target_states or primitive.output_state in forbidden:
            continue
        if not _eligible_generation_primitive(primitive):
            continue
        if context and primitive.context_tags and not context.intersection(primitive.context_tags):
            continue
        actions = sorted(
            condition.removeprefix("process:")
            for condition in primitive.input_conditions
            if condition.startswith("process:")
        )
        if not actions:
            continue
        action = actions[0]
        required_states = {
            item.removeprefix("state:") for item in primitive.input_state_conditions
        }
        add_states = sorted(required_states - baseline_states)
        if forbidden.intersection(add_states):
            continue

        variable_overrides: dict[str, float] = {}
        variable_names = set(primitive.numeric_preconditions) | set(minimum_variables)
        for name in variable_names:
            required_before = primitive.numeric_preconditions.get(name, float("-inf"))
            if name in minimum_variables:
                required_before = max(
                    required_before,
                    minimum_variables[name] - primitive.state_variable_deltas.get(name, 0.0),
                )
            current = baseline_variables.get(name)
            if current is None or current < required_before:
                variable_overrides[name] = required_before

        action_cost = 0.0 if action == normalize_label(start_action) else 0.25
        state_cost = float(len(add_states))
        variable_cost = sum(
            abs(value - baseline_variables.get(name, 0.0)) * 0.1
            for name, value in variable_overrides.items()
        )
        candidates.append(
            InterventionSpecification(
                id=f"generated:{primitive.id}",
                start_action=action,
                add_states=add_states,
                variable_overrides=dict(sorted(variable_overrides.items())),
                cost=round(action_cost + state_cost + variable_cost, 6),
                generated=True,
                generation_reason=(
                    f"Primitive '{primitive.id}' produces goal state "
                    f"'{primitive.output_state}' from its observed input conditions."
                ),
                evidence_primitive_ids=[primitive.id],
            )
        )

    candidates.sort(key=lambda item: (item.cost, item.id))
    return candidates[:max_candidates]


def generate_backward_intervention_candidates(
    state: RisaState,
    start_action: str,
    goal_specification: GoalSpecification,
    start_states: list[str] | None = None,
    start_variables: dict[str, float] | None = None,
    context_tags: list[str] | None = None,
    max_depth: int = 3,
    max_candidates: int = 8,
) -> list[InterventionSpecification]:
    """Build observed linear primitive chains backward from terminal goal states."""
    if max_depth < 2 or max_candidates < 1:
        return []
    baseline_states = {normalize_label(item) for item in start_states or []}
    baseline_variables = {
        normalize_label(name): float(value) for name, value in (start_variables or {}).items()
    }
    context = {normalize_label(tag) for tag in context_tags or []}
    forbidden = {normalize_label(item) for item in goal_specification.forbidden_states}
    target_states = {
        normalize_label(item) for item in goal_specification.required_states
    }
    for group in goal_specification.any_state_groups:
        target_states.update(normalize_label(item) for item in group)

    eligible = [
        primitive
        for primitive in state.structural_primitives.values()
        if _eligible_generation_primitive(primitive)
        and primitive.output_state not in forbidden
        and (
            not context
            or not primitive.context_tags
            or bool(context.intersection(primitive.context_tags))
        )
    ]
    by_output: dict[str, list[StructuralPrimitive]] = {}
    for primitive in eligible:
        by_output.setdefault(primitive.output_state, []).append(primitive)
    for primitives in by_output.values():
        primitives.sort(key=lambda item: item.id)

    chains: list[list[StructuralPrimitive]] = []
    for target in sorted(target_states):
        for terminal in by_output.get(target, []):
            chains.extend(
                _expand_backward_chains(
                    state,
                    terminal,
                    by_output,
                    baseline_states,
                    context,
                    max_depth,
                    {terminal.id},
                )
            )

    candidates: list[InterventionSpecification] = []
    seen_chains: set[tuple[str, ...]] = set()
    for chain in chains:
        chain_ids = tuple(primitive.id for primitive in chain)
        if len(chain) < 2 or chain_ids in seen_chains:
            continue
        seen_chains.add(chain_ids)
        actions = [_primitive_action(primitive) for primitive in chain]
        if any(action is None for action in actions):
            continue
        produced_states = {primitive.output_state for primitive in chain}
        required_states = {
            state_id.removeprefix("state:")
            for primitive in chain
            for state_id in primitive.input_state_conditions
        }
        add_states = sorted(required_states - produced_states - baseline_states)
        if forbidden.intersection(add_states):
            continue
        variable_overrides = _reverse_chain_variables(
            chain,
            goal_specification.minimum_variables,
            baseline_variables,
        )
        first_action = actions[0]
        action_cost = 0.0 if first_action == normalize_label(start_action) else 0.25
        state_cost = float(len(add_states))
        variable_cost = sum(
            abs(value - baseline_variables.get(name, 0.0)) * 0.1
            for name, value in variable_overrides.items()
        )
        candidates.append(
            InterventionSpecification(
                id="generated_chain:" + "|".join(chain_ids),
                start_action=first_action,
                add_states=add_states,
                variable_overrides=variable_overrides,
                cost=round(action_cost + state_cost + variable_cost, 6),
                generated=True,
                generation_reason=(
                    f"Observed primitive chain produces goal state "
                    f"'{chain[-1].output_state}' through {len(chain)} transitions."
                ),
                evidence_primitive_ids=list(chain_ids),
                suggested_action_sequence=[action for action in actions if action],
            )
        )
    candidates.sort(key=lambda item: (item.cost, len(item.evidence_primitive_ids), item.id))
    return candidates[:max_candidates]


def generate_conjunctive_plan_candidates(
    state: RisaState,
    start_action: str,
    goal_specification: GoalSpecification,
    start_states: list[str] | None = None,
    start_variables: dict[str, float] | None = None,
    context_tags: list[str] | None = None,
    max_depth: int = 4,
    max_candidates: int = 8,
) -> list[InterventionSpecification]:
    """Resolve all primitive state preconditions into a bounded dependency graph."""
    if max_depth < 2 or max_candidates < 1:
        return []
    baseline_states = {normalize_label(item) for item in start_states or []}
    baseline_variables = {
        normalize_label(name): float(value) for name, value in (start_variables or {}).items()
    }
    context = {normalize_label(tag) for tag in context_tags or []}
    forbidden = {normalize_label(item) for item in goal_specification.forbidden_states}
    target_states = {
        normalize_label(item) for item in goal_specification.required_states
    }
    for group in goal_specification.any_state_groups:
        target_states.update(normalize_label(item) for item in group)
    eligible = [
        primitive
        for primitive in state.structural_primitives.values()
        if _eligible_generation_primitive(primitive)
        and primitive.output_state not in forbidden
        and (
            not context
            or not primitive.context_tags
            or bool(context.intersection(primitive.context_tags))
        )
    ]
    by_output: dict[str, list[StructuralPrimitive]] = {}
    for primitive in eligible:
        by_output.setdefault(primitive.output_state, []).append(primitive)
    for primitives in by_output.values():
        primitives.sort(key=lambda item: item.id)

    candidates: list[InterventionSpecification] = []
    for target in sorted(target_states):
        for terminal in by_output.get(target, []):
            nodes: dict[str, StructuralPrimitive] = {terminal.id: terminal}
            dependencies: list[PlanGraphDependency] = []
            unresolved: set[str] = set()
            _resolve_all_preconditions(
                state,
                terminal,
                by_output,
                baseline_states,
                context,
                max_depth,
                {terminal.id},
                nodes,
                dependencies,
                unresolved,
            )
            if len(nodes) < 2:
                continue
            sequence = _linearize_plan_graph(state, nodes, dependencies, context)
            if not sequence:
                continue
            ordered_primitives = [
                next(item for item in nodes.values() if _primitive_action(item) == action)
                for action in sequence
            ]
            produced_states = {primitive.output_state for primitive in ordered_primitives}
            add_states = sorted(unresolved - produced_states - baseline_states)
            if forbidden.intersection(add_states):
                continue
            variable_overrides = _reverse_chain_variables(
                ordered_primitives,
                goal_specification.minimum_variables,
                baseline_variables,
            )
            action_cost = 0.0 if sequence[0] == normalize_label(start_action) else 0.25
            state_cost = float(len(add_states))
            variable_cost = sum(
                abs(value - baseline_variables.get(name, 0.0)) * 0.1
                for name, value in variable_overrides.items()
            )
            graph_id = "plan_graph:" + "|".join(item.id for item in ordered_primitives)
            plan_graph = ConjunctivePlanGraph(
                id=graph_id,
                primitive_ids=[item.id for item in ordered_primitives],
                dependencies=sorted(
                    dependencies,
                    key=lambda item: (
                        item.source_primitive_id,
                        item.target_primitive_id,
                        item.required_state,
                    ),
                ),
                unresolved_states=add_states,
                action_sequence=sequence,
            )
            candidates.append(
                InterventionSpecification(
                    id=f"generated_conjunctive:{graph_id}",
                    start_action=sequence[0],
                    add_states=add_states,
                    variable_overrides=variable_overrides,
                    cost=round(action_cost + state_cost + variable_cost, 6),
                    generated=True,
                    generation_reason=(
                        f"Conjunctive plan graph resolves {len(dependencies)} state "
                        f"dependencies for goal state '{target}'."
                    ),
                    evidence_primitive_ids=plan_graph.primitive_ids,
                    suggested_action_sequence=sequence,
                    plan_graph=plan_graph,
                )
            )
    candidates.sort(key=lambda item: (item.cost, len(item.evidence_primitive_ids), item.id))
    return candidates[:max_candidates]


def generate_disjunctive_plan_candidates(
    state: RisaState,
    start_action: str,
    goal_specification: GoalSpecification,
    start_states: list[str] | None = None,
    start_variables: dict[str, float] | None = None,
    context_tags: list[str] | None = None,
    max_depth: int = 4,
    max_candidates: int = 8,
) -> list[InterventionSpecification]:
    """Enumerate bounded producer alternatives throughout a nested AND/OR plan."""
    if max_depth < 2 or max_candidates < 1:
        return []
    baseline_states = {normalize_label(item) for item in start_states or []}
    baseline_variables = {
        normalize_label(name): float(value) for name, value in (start_variables or {}).items()
    }
    context = {normalize_label(tag) for tag in context_tags or []}
    forbidden = {normalize_label(item) for item in goal_specification.forbidden_states}
    target_states = {
        normalize_label(item) for item in goal_specification.required_states
    }
    for group in goal_specification.any_state_groups:
        target_states.update(normalize_label(item) for item in group)
    eligible = [
        primitive
        for primitive in state.structural_primitives.values()
        if _eligible_generation_primitive(primitive)
        and primitive.output_state not in forbidden
        and (
            not context
            or not primitive.context_tags
            or bool(context.intersection(primitive.context_tags))
        )
    ]
    by_output: dict[str, list[StructuralPrimitive]] = {}
    for primitive in eligible:
        by_output.setdefault(primitive.output_state, []).append(primitive)
    for primitives in by_output.values():
        primitives.sort(key=lambda item: item.id)

    candidates: list[InterventionSpecification] = []
    for target in sorted(target_states):
        for terminal in by_output.get(target, []):
            alternative_group_id = f"alternative_group:{terminal.id}"
            variants = _expand_nested_plan_variants(
                state,
                terminal,
                by_output,
                baseline_states,
                context,
                max_depth,
                {terminal.id},
                max_candidates + 1,
            )
            search_truncated = len(variants) > max_candidates
            for (
                nodes,
                dependencies,
                unresolved,
                selected_producers,
                alternative_choice_count,
            ) in variants[:max_candidates]:
                if alternative_choice_count == 0:
                    continue
                sequence = _linearize_plan_graph(state, nodes, dependencies, context)
                if not sequence:
                    continue
                ordered_primitives = [
                    next(
                        item
                        for item in nodes.values()
                        if _primitive_action(item) == action
                    )
                    for action in sequence
                ]
                produced_states = {
                    primitive.output_state for primitive in ordered_primitives
                }
                add_states = sorted(unresolved - produced_states - baseline_states)
                if forbidden.intersection(add_states):
                    continue
                variable_overrides = _reverse_chain_variables(
                    ordered_primitives,
                    goal_specification.minimum_variables,
                    baseline_variables,
                )
                action_cost = (
                    0.0 if sequence[0] == normalize_label(start_action) else 0.25
                )
                state_cost = float(len(add_states))
                variable_cost = sum(
                    abs(value - baseline_variables.get(name, 0.0)) * 0.1
                    for name, value in variable_overrides.items()
                )
                graph_id = "plan_graph:" + "|".join(
                    item.id for item in ordered_primitives
                )
                plan_graph = ConjunctivePlanGraph(
                    id=graph_id,
                    primitive_ids=[item.id for item in ordered_primitives],
                    dependencies=sorted(
                        dependencies,
                        key=lambda item: (
                            item.source_primitive_id,
                            item.target_primitive_id,
                            item.required_state,
                        ),
                    ),
                    unresolved_states=add_states,
                    action_sequence=sequence,
                    alternative_group_id=alternative_group_id,
                    selected_producers=dict(sorted(selected_producers.items())),
                    alternative_choice_count=alternative_choice_count,
                    dependency_depth=_plan_dependency_depth(terminal.id, dependencies),
                    alternative_search_truncated=search_truncated,
                )
                candidates.append(
                    InterventionSpecification(
                        id=f"generated_disjunctive:{graph_id}",
                        start_action=sequence[0],
                        add_states=add_states,
                        variable_overrides=variable_overrides,
                        cost=round(action_cost + state_cost + variable_cost, 6),
                        generated=True,
                        generation_reason=(
                            f"Nested AND/OR plan selects producers at "
                            f"{alternative_choice_count} alternative points for goal "
                            f"'{target}'."
                        ),
                        evidence_primitive_ids=plan_graph.primitive_ids,
                        suggested_action_sequence=sequence,
                        plan_graph=plan_graph,
                    )
                )
                if len(candidates) >= max_candidates:
                    break
            if len(candidates) >= max_candidates:
                break
        if len(candidates) >= max_candidates:
            break
    candidates.sort(key=lambda item: (item.cost, len(item.evidence_primitive_ids), item.id))
    return candidates[:max_candidates]


def _expand_nested_plan_variants(
    state: RisaState,
    current: StructuralPrimitive,
    by_output: dict[str, list[StructuralPrimitive]],
    baseline_states: set[str],
    context: set[str],
    remaining_depth: int,
    visited: set[str],
    max_variants: int,
) -> list[
    tuple[
        dict[str, StructuralPrimitive],
        list[PlanGraphDependency],
        set[str],
        dict[str, str],
        int,
    ]
]:
    """Expand every AND prerequisite while preserving each reachable OR producer."""
    variants = [({current.id: current}, [], set(), {}, 0)]
    for state_id in sorted(current.input_state_conditions):
        required_state = state_id.removeprefix("state:")
        if required_state in baseline_states:
            continue
        producers = [
            producer
            for producer in by_output.get(required_state, [])
            if producer.id not in visited
            and _action_reaches(
                state,
                _primitive_action(producer),
                _primitive_action(current),
                context,
                remaining_depth,
            )
        ]
        if remaining_depth <= 1 or not producers:
            variants = [
                (nodes, dependencies, {*unresolved, required_state}, selected, choices)
                for nodes, dependencies, unresolved, selected, choices in variants
            ]
            continue

        producer_variants = []
        for producer in producers:
            for subvariant in _expand_nested_plan_variants(
                state,
                producer,
                by_output,
                baseline_states,
                context,
                remaining_depth - 1,
                {*visited, producer.id},
                max_variants,
            ):
                nodes, dependencies, unresolved, selected, choices = subvariant
                dependency = PlanGraphDependency(
                    source_primitive_id=producer.id,
                    target_primitive_id=current.id,
                    required_state=required_state,
                )
                selected = _with_selected_producer(
                    selected,
                    current.id,
                    required_state,
                    producer.id,
                )
                producer_variants.append(
                    (
                        nodes,
                        [*dependencies, dependency],
                        unresolved,
                        selected,
                        choices + (1 if len(producers) > 1 else 0),
                    )
                )
                if len(producer_variants) >= max_variants:
                    break
            if len(producer_variants) >= max_variants:
                break

        combined = []
        for left in variants:
            for right in producer_variants:
                left_nodes, left_dependencies, left_unresolved, left_selected, left_choices = left
                right_nodes, right_dependencies, right_unresolved, right_selected, right_choices = right
                merged_dependencies = list(left_dependencies)
                for dependency in right_dependencies:
                    if dependency not in merged_dependencies:
                        merged_dependencies.append(dependency)
                combined.append(
                    (
                        {**left_nodes, **right_nodes},
                        merged_dependencies,
                        left_unresolved | right_unresolved,
                        {**left_selected, **right_selected},
                        left_choices + right_choices,
                    )
                )
                if len(combined) >= max_variants:
                    break
            if len(combined) >= max_variants:
                break
        variants = combined
    return variants


def _with_selected_producer(
    selected: dict[str, str],
    consumer_id: str,
    required_state: str,
    producer_id: str,
) -> dict[str, str]:
    result = dict(selected)
    key = required_state
    if key in result and result[key] != producer_id:
        key = f"{consumer_id}::{required_state}"
    result[key] = producer_id
    return result


def _plan_dependency_depth(
    terminal_id: str,
    dependencies: list[PlanGraphDependency],
) -> int:
    incoming: dict[str, list[str]] = {}
    for dependency in dependencies:
        incoming.setdefault(dependency.target_primitive_id, []).append(
            dependency.source_primitive_id
        )

    def depth(primitive_id: str, visited: set[str]) -> int:
        producers = incoming.get(primitive_id, [])
        if not producers:
            return 0
        return 1 + max(
            depth(producer_id, {*visited, producer_id})
            for producer_id in producers
            if producer_id not in visited
        )

    return depth(terminal_id, {terminal_id})


def plan_counterfactuals(
    state: RisaState,
    start_action: str,
    goal_specification: GoalSpecification,
    interventions: list[InterventionSpecification],
    start_states: list[str] | None = None,
    start_variables: dict[str, float] | None = None,
    avoid_states: list[str] | None = None,
    variable_cost_weights: dict[str, float] | None = None,
    context_tags: list[str] | None = None,
    max_steps: int = 3,
    max_branches: int = 8,
    max_candidates_per_step: int = 3,
    include_baseline: bool = True,
) -> CounterfactualPlanningReport:
    """Compare explicit interventions without changing persistent learned state."""
    normalized = [_normalize_intervention(item) for item in interventions]
    if include_baseline:
        normalized = [InterventionSpecification(id="baseline"), *normalized]
    ids = [item.id for item in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("intervention IDs must be unique, including reserved ID 'baseline'")

    baseline_states = {normalize_label(item) for item in start_states or []}
    baseline_variables = {
        normalize_label(name): float(value) for name, value in (start_variables or {}).items()
    }
    outcomes: list[CounterfactualOutcome] = []
    for intervention in normalized:
        intervention_states = (
            baseline_states - set(intervention.remove_states)
        ) | set(intervention.add_states)
        intervention_variables = {
            **baseline_variables,
            **intervention.variable_overrides,
        }
        if intervention.suggested_action_sequence:
            simulation = simulate_action_sequence_with_diagnostics(
                state,
                actions=intervention.suggested_action_sequence,
                start_states=sorted(intervention_states),
                start_variables=intervention_variables,
                context_tags=context_tags,
                forbidden_states=goal_specification.forbidden_states,
                max_branches=max_branches,
                max_candidates_per_step=max_candidates_per_step,
            )
        else:
            simulation = simulate_branches_with_diagnostics(
                state,
                start_action=intervention.start_action or start_action,
                start_states=sorted(intervention_states),
                start_variables=intervention_variables,
                context_tags=context_tags,
                max_steps=max_steps,
                max_branches=max_branches,
                max_candidates_per_step=max_candidates_per_step,
                forbidden_states=goal_specification.forbidden_states,
            )
        search_diagnostics = {
            "expanded_candidate_count": simulation.expanded_candidate_count,
            "constraint_pruned_count": simulation.constraint_pruned_count,
            "beam_pruned_count": simulation.beam_pruned_count,
        }
        if intervention.suggested_action_sequence:
            search_diagnostics.update(
                {
                    "sequence_failed_count": simulation.sequence_failed_count,
                    "invalid_sequence_edge_count": simulation.invalid_sequence_edge_count,
                }
            )
        evaluation = evaluate_branches(
            simulation.branches,
            avoid_states=avoid_states,
            variable_cost_weights=variable_cost_weights,
            goal_specification=goal_specification,
            search_diagnostics=search_diagnostics,
        )
        selected = next(
            (
                item
                for item in evaluation.evaluations
                if item.branch.id == evaluation.selected_branch_id
            ),
            None,
        )
        cost_penalty = 1.0 - math.exp(-intervention.cost)
        feasible = selected is not None
        plan_score = (selected.utility if selected else 0.0) - (0.15 * cost_penalty)
        outcomes.append(
            CounterfactualOutcome(
                intervention=intervention,
                evaluation=evaluation,
                feasible=feasible,
                intervention_cost_penalty=round(cost_penalty, 6),
                plan_score=round(plan_score, 6),
            )
        )

    outcomes.sort(
        key=lambda item: (
            not item.feasible,
            -item.plan_score,
            item.intervention.plan_graph is None,
            item.intervention.id,
        )
    )
    selected_outcome = next((item for item in outcomes if item.feasible), None)
    return CounterfactualPlanningReport(
        selected_intervention_id=(
            selected_outcome.intervention.id if selected_outcome else None
        ),
        selected_branch_id=(
            selected_outcome.evaluation.selected_branch_id if selected_outcome else None
        ),
        outcomes=outcomes,
    )


def _normalize_intervention(
    intervention: InterventionSpecification,
) -> InterventionSpecification:
    add_states = {normalize_label(item) for item in intervention.add_states}
    remove_states = {normalize_label(item) for item in intervention.remove_states}
    if add_states.intersection(remove_states):
        raise ValueError("an intervention cannot add and remove the same state")
    cost = float(intervention.cost)
    if not math.isfinite(cost) or cost < 0.0:
        raise ValueError("intervention cost must be a finite non-negative number")
    variables = {
        normalize_label(name): float(value)
        for name, value in intervention.variable_overrides.items()
    }
    if any(not math.isfinite(value) for value in variables.values()):
        raise ValueError("intervention variable overrides must be finite")
    suggested_actions = [
        normalize_label(action) for action in intervention.suggested_action_sequence
    ]
    normalized_start_action = (
        normalize_label(intervention.start_action)
        if intervention.start_action
        else None
    )
    if suggested_actions and normalized_start_action and suggested_actions[0] != normalized_start_action:
        raise ValueError("intervention start action must match the suggested sequence")
    return InterventionSpecification(
        id=normalize_label(intervention.id),
        start_action=normalized_start_action,
        add_states=sorted(add_states),
        remove_states=sorted(remove_states),
        variable_overrides=variables,
        cost=cost,
        generated=intervention.generated,
        generation_reason=intervention.generation_reason,
        evidence_primitive_ids=list(dict.fromkeys(intervention.evidence_primitive_ids)),
        suggested_action_sequence=suggested_actions,
        plan_graph=intervention.plan_graph,
    )


def _eligible_generation_primitive(primitive: StructuralPrimitive) -> bool:
    return primitive.adopted or (
        primitive.support >= 2
        and primitive.replay_count >= 2
        and primitive.replay_score >= 0.8
    )


def _expand_backward_chains(
    state: RisaState,
    current: StructuralPrimitive,
    by_output: dict[str, list[StructuralPrimitive]],
    baseline_states: set[str],
    context: set[str],
    max_depth: int,
    visited: set[str],
) -> list[list[StructuralPrimitive]]:
    if max_depth <= 1:
        return [[current]]
    unmet = sorted(
        state_id.removeprefix("state:")
        for state_id in current.input_state_conditions
        if state_id.removeprefix("state:") not in baseline_states
    )
    if not unmet:
        return [[current]]
    current_action = _primitive_action(current)
    chains: list[list[StructuralPrimitive]] = []
    for required_state in unmet:
        for producer in by_output.get(required_state, []):
            if producer.id in visited:
                continue
            producer_action = _primitive_action(producer)
            if not producer_action or not current_action:
                continue
            if not _actions_observed_in_order(
                state, producer_action, current_action, context
            ):
                continue
            prefixes = _expand_backward_chains(
                state,
                producer,
                by_output,
                baseline_states,
                context,
                max_depth - 1,
                {*visited, producer.id},
            )
            chains.extend([*prefix, current] for prefix in prefixes)
    return chains or [[current]]


def _primitive_action(primitive: StructuralPrimitive) -> str | None:
    actions = sorted(
        condition.removeprefix("process:")
        for condition in primitive.input_conditions
        if condition.startswith("process:")
    )
    return actions[0] if actions else None


def _actions_observed_in_order(
    state: RisaState,
    source_action: str,
    target_action: str,
    context: set[str],
) -> bool:
    for edge in state.graph.outgoing(f"process:{source_action}"):
        if edge.relation_type != "precedes" or edge.target != f"process:{target_action}":
            continue
        if context and edge.context_tags and not context.intersection(edge.context_tags):
            continue
        return True
    return False


def _reverse_chain_variables(
    chain: list[StructuralPrimitive],
    minimum_variables: dict[str, float],
    baseline_variables: dict[str, float],
) -> dict[str, float]:
    variable_names = set(minimum_variables)
    for primitive in chain:
        variable_names.update(primitive.numeric_preconditions)
    overrides: dict[str, float] = {}
    for raw_name in variable_names:
        name = normalize_label(raw_name)
        required_after = float(minimum_variables.get(raw_name, minimum_variables.get(name, float("-inf"))))
        for primitive in reversed(chain):
            delta = primitive.state_variable_deltas.get(name, 0.0)
            precondition = primitive.numeric_preconditions.get(name, float("-inf"))
            required_after = max(precondition, required_after - delta)
        current = baseline_variables.get(name)
        if current is None or current < required_after:
            overrides[name] = required_after
    return dict(sorted(overrides.items()))


def _resolve_all_preconditions(
    state: RisaState,
    current: StructuralPrimitive,
    by_output: dict[str, list[StructuralPrimitive]],
    baseline_states: set[str],
    context: set[str],
    remaining_depth: int,
    visited: set[str],
    nodes: dict[str, StructuralPrimitive],
    dependencies: list[PlanGraphDependency],
    unresolved: set[str],
) -> None:
    for state_id in sorted(current.input_state_conditions):
        required_state = state_id.removeprefix("state:")
        if required_state in baseline_states:
            continue
        producers = [
            producer
            for producer in by_output.get(required_state, [])
            if producer.id not in visited
            and _action_reaches(
                state,
                _primitive_action(producer),
                _primitive_action(current),
                context,
                remaining_depth,
            )
        ]
        if not producers or remaining_depth <= 1:
            unresolved.add(required_state)
            continue
        producer = producers[0]
        nodes[producer.id] = producer
        dependency = PlanGraphDependency(
            source_primitive_id=producer.id,
            target_primitive_id=current.id,
            required_state=required_state,
        )
        if dependency not in dependencies:
            dependencies.append(dependency)
        _resolve_all_preconditions(
            state,
            producer,
            by_output,
            baseline_states,
            context,
            remaining_depth - 1,
            {*visited, producer.id},
            nodes,
            dependencies,
            unresolved,
        )


def _action_reaches(
    state: RisaState,
    source_action: str | None,
    target_action: str | None,
    context: set[str],
    max_hops: int,
) -> bool:
    if not source_action or not target_action:
        return False
    frontier = [(source_action, 0)]
    visited = {source_action}
    while frontier:
        action, depth = frontier.pop(0)
        if depth >= max_hops:
            continue
        for next_action, _ in _observed_next_actions(state, action, context):
            if next_action == target_action:
                return True
            if next_action not in visited:
                visited.add(next_action)
                frontier.append((next_action, depth + 1))
    return False


def _linearize_plan_graph(
    state: RisaState,
    nodes: dict[str, StructuralPrimitive],
    dependencies: list[PlanGraphDependency],
    context: set[str],
) -> list[str]:
    if len(nodes) > 7:
        return []
    primitive_ids = sorted(nodes)
    dependency_pairs = {
        (dependency.source_primitive_id, dependency.target_primitive_id)
        for dependency in dependencies
    }
    for order in permutations(primitive_ids):
        positions = {primitive_id: index for index, primitive_id in enumerate(order)}
        if any(positions[source] >= positions[target] for source, target in dependency_pairs):
            continue
        actions = [_primitive_action(nodes[primitive_id]) for primitive_id in order]
        if any(action is None for action in actions):
            continue
        if all(
            _actions_observed_in_order(state, source, target, context)
            for source, target in zip(actions, actions[1:])
        ):
            return [action for action in actions if action]
    return []


def _observed_next_actions(
    state: RisaState,
    action: str,
    context: set[str],
) -> list[tuple[str, float]]:
    from risa.engine.composer import next_actions

    return next_actions(state, action, context)
