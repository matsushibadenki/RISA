from __future__ import annotations

from dataclasses import replace

from risa.core.models import (
    BranchSimulationReport,
    ConjunctivePlanGraph,
    PlanGraphSimulationReport,
    SequenceSimulationReport,
    TrajectoryBranch,
    TrajectoryStep,
)
from risa.core.state import RisaState
from risa.engine.composer import forecast_next_effects, next_actions
from risa.engine.graph_builder import normalize_label


def simulate_branches(
    state: RisaState,
    start_action: str,
    start_states: list[str] | None = None,
    start_variables: dict[str, float] | None = None,
    context_tags: list[str] | None = None,
    max_steps: int = 3,
    max_branches: int = 8,
    max_candidates_per_step: int = 3,
    forbidden_states: list[str] | None = None,
) -> list[TrajectoryBranch]:
    """Expand independent state trajectories with bounded local beam search."""
    return simulate_branches_with_diagnostics(
        state=state,
        start_action=start_action,
        start_states=start_states,
        start_variables=start_variables,
        context_tags=context_tags,
        max_steps=max_steps,
        max_branches=max_branches,
        max_candidates_per_step=max_candidates_per_step,
        forbidden_states=forbidden_states,
    ).branches


def simulate_branches_with_diagnostics(
    state: RisaState,
    start_action: str,
    start_states: list[str] | None = None,
    start_variables: dict[str, float] | None = None,
    context_tags: list[str] | None = None,
    max_steps: int = 3,
    max_branches: int = 8,
    max_candidates_per_step: int = 3,
    forbidden_states: list[str] | None = None,
) -> BranchSimulationReport:
    """Expand branches and report early hard-constraint and beam pruning."""
    if max_steps < 1 or max_branches < 1 or max_candidates_per_step < 1:
        return BranchSimulationReport()

    context = {normalize_label(tag) for tag in context_tags or []}
    forbidden = {normalize_label(state_name) for state_name in forbidden_states or []}
    initial = TrajectoryBranch(
        current_states=sorted(normalize_label(item) for item in start_states or []),
        current_variables={
            normalize_label(name): float(value) for name, value in (start_variables or {}).items()
        },
    )
    if forbidden.intersection(initial.current_states):
        return BranchSimulationReport(constraint_pruned_count=1)
    active: list[tuple[str, TrajectoryBranch]] = [(normalize_label(start_action), initial)]
    completed: list[TrajectoryBranch] = []
    expanded_candidate_count = 0
    constraint_pruned_count = 0
    beam_pruned_count = 0

    for depth in range(max_steps):
        expanded: list[tuple[str, TrajectoryBranch]] = []
        for action, branch in active:
            candidates = forecast_next_effects(
                state,
                action=action,
                current_states=branch.current_states,
                current_variables=branch.current_variables,
                context_tags=sorted(context),
                max_candidates=max_candidates_per_step,
                include_supported_alternatives=True,
            )
            if not candidates:
                completed.append(replace(branch, terminated_reason="no_applicable_transition"))
                continue

            for candidate in candidates:
                expanded_candidate_count += 1
                next_states = (
                    set(branch.current_states) - set(candidate.removed_states)
                ) | {candidate.target_effect}
                if forbidden.intersection(next_states):
                    constraint_pruned_count += 1
                    continue
                primitive_id = candidate.primitive_ids[0] if candidate.primitive_ids else ""
                step = TrajectoryStep(
                    action=action,
                    effect=candidate.target_effect,
                    primitive_id=primitive_id,
                    states_before=list(branch.current_states),
                    states_after=sorted(next_states),
                    variables_before=dict(branch.current_variables),
                    variables_after=dict(candidate.resulting_variables),
                    removed_states=list(candidate.removed_states),
                    score=candidate.score,
                )
                next_branch = TrajectoryBranch(
                    steps=[*branch.steps, step],
                    current_states=sorted(next_states),
                    current_variables=dict(candidate.resulting_variables),
                    score=branch.score * candidate.score,
                )

                if depth == max_steps - 1:
                    next_branch.terminated_reason = "max_steps"
                    completed.append(next_branch)
                    continue

                successors = next_actions(state, action, context)
                if not successors:
                    next_branch.terminated_reason = "no_next_action"
                    completed.append(next_branch)
                    continue
                for successor, precedence_score in successors:
                    expanded.append(
                        (
                            successor,
                            replace(next_branch, score=next_branch.score * precedence_score),
                        )
                    )

        expanded.sort(key=lambda item: (-item[1].score, _branch_signature(item[1]), item[0]))
        beam_pruned_count += max(0, len(expanded) - max_branches)
        active = expanded[:max_branches]
        if not active:
            break

    completed.extend(
        replace(branch, terminated_reason=branch.terminated_reason or "beam_complete")
        for _, branch in active
    )
    completed.sort(key=lambda branch: (-branch.score, _branch_signature(branch)))
    beam_pruned_count += max(0, len(completed) - max_branches)
    selected = completed[:max_branches]
    for index, branch in enumerate(selected, start=1):
        branch.id = f"branch:{index:03d}"
        branch.score = round(branch.score, 6)
    return BranchSimulationReport(
        branches=selected,
        expanded_candidate_count=expanded_candidate_count,
        constraint_pruned_count=constraint_pruned_count,
        beam_pruned_count=beam_pruned_count,
    )


def simulate_action_sequence_with_diagnostics(
    state: RisaState,
    actions: list[str],
    start_states: list[str] | None = None,
    start_variables: dict[str, float] | None = None,
    context_tags: list[str] | None = None,
    forbidden_states: list[str] | None = None,
    max_branches: int = 8,
    max_candidates_per_step: int = 3,
) -> SequenceSimulationReport:
    """Execute exactly the requested action order against observed local transitions."""
    normalized_actions = [normalize_label(action) for action in actions]
    if not normalized_actions or max_branches < 1 or max_candidates_per_step < 1:
        return SequenceSimulationReport(
            requested_actions=normalized_actions,
            sequence_failed_count=1,
        )
    context = {normalize_label(tag) for tag in context_tags or []}
    forbidden = {normalize_label(item) for item in forbidden_states or []}
    precedence_scores: list[float] = []
    for source, target in zip(normalized_actions, normalized_actions[1:]):
        score = next(
            (
                edge_score
                for next_action, edge_score in next_actions(state, source, context)
                if next_action == target
            ),
            None,
        )
        if score is None:
            return SequenceSimulationReport(
                requested_actions=normalized_actions,
                sequence_failed_count=1,
                invalid_sequence_edge_count=1,
            )
        precedence_scores.append(score)

    initial = TrajectoryBranch(
        current_states=sorted(normalize_label(item) for item in start_states or []),
        current_variables={
            normalize_label(name): float(value)
            for name, value in (start_variables or {}).items()
        },
    )
    if forbidden.intersection(initial.current_states):
        return SequenceSimulationReport(
            requested_actions=normalized_actions,
            constraint_pruned_count=1,
            sequence_failed_count=1,
        )

    active = [initial]
    completed: list[TrajectoryBranch] = []
    expanded_candidate_count = 0
    constraint_pruned_count = 0
    beam_pruned_count = 0
    sequence_failed_count = 0
    for index, action in enumerate(normalized_actions):
        expanded: list[TrajectoryBranch] = []
        for branch in active:
            candidates = forecast_next_effects(
                state,
                action=action,
                current_states=branch.current_states,
                current_variables=branch.current_variables,
                context_tags=sorted(context),
                max_candidates=max_candidates_per_step,
                include_supported_alternatives=True,
            )
            if not candidates:
                sequence_failed_count += 1
                continue
            for candidate in candidates:
                expanded_candidate_count += 1
                next_states = (
                    set(branch.current_states) - set(candidate.removed_states)
                ) | {candidate.target_effect}
                if forbidden.intersection(next_states):
                    constraint_pruned_count += 1
                    continue
                primitive_id = candidate.primitive_ids[0] if candidate.primitive_ids else ""
                step = TrajectoryStep(
                    action=action,
                    effect=candidate.target_effect,
                    primitive_id=primitive_id,
                    states_before=list(branch.current_states),
                    states_after=sorted(next_states),
                    variables_before=dict(branch.current_variables),
                    variables_after=dict(candidate.resulting_variables),
                    removed_states=list(candidate.removed_states),
                    score=candidate.score,
                )
                score = branch.score * candidate.score
                if index < len(precedence_scores):
                    score *= precedence_scores[index]
                next_branch = TrajectoryBranch(
                    steps=[*branch.steps, step],
                    current_states=sorted(next_states),
                    current_variables=dict(candidate.resulting_variables),
                    score=score,
                )
                if index == len(normalized_actions) - 1:
                    next_branch.terminated_reason = "sequence_complete"
                    completed.append(next_branch)
                else:
                    expanded.append(next_branch)
        expanded.sort(key=lambda branch: (-branch.score, _branch_signature(branch)))
        beam_pruned_count += max(0, len(expanded) - max_branches)
        active = expanded[:max_branches]
        if index < len(normalized_actions) - 1 and not active:
            break

    completed.sort(key=lambda branch: (-branch.score, _branch_signature(branch)))
    beam_pruned_count += max(0, len(completed) - max_branches)
    selected = completed[:max_branches]
    for index, branch in enumerate(selected, start=1):
        branch.id = f"branch:{index:03d}"
        branch.score = round(branch.score, 6)
    if not selected and sequence_failed_count == 0:
        sequence_failed_count = 1
    return SequenceSimulationReport(
        branches=selected,
        requested_actions=normalized_actions,
        expanded_candidate_count=expanded_candidate_count,
        constraint_pruned_count=constraint_pruned_count,
        beam_pruned_count=beam_pruned_count,
        sequence_failed_count=sequence_failed_count,
    )


def simulate_plan_graph_with_diagnostics(
    state: RisaState,
    plan_graph: ConjunctivePlanGraph,
    start_states: list[str] | None = None,
    start_variables: dict[str, float] | None = None,
    context_tags: list[str] | None = None,
    forbidden_states: list[str] | None = None,
    max_branches: int = 8,
) -> PlanGraphSimulationReport:
    """Execute dependency-ready primitive nodes without pre-linearizing the graph."""
    primitive_ids = set(plan_graph.primitive_ids)
    primitives = {
        primitive_id: state.structural_primitives[primitive_id]
        for primitive_id in primitive_ids
        if primitive_id in state.structural_primitives
    }
    if not primitive_ids or len(primitives) != len(primitive_ids) or max_branches < 1:
        return PlanGraphSimulationReport(
            plan_graph_id=plan_graph.id,
            primitive_mismatch_count=len(primitive_ids - set(primitives)) or 1,
        )
    incoming: dict[str, set[str]] = {primitive_id: set() for primitive_id in primitive_ids}
    for dependency in plan_graph.dependencies:
        if (
            dependency.source_primitive_id not in primitive_ids
            or dependency.target_primitive_id not in primitive_ids
        ):
            return PlanGraphSimulationReport(
                plan_graph_id=plan_graph.id,
                primitive_mismatch_count=1,
            )
        incoming[dependency.target_primitive_id].add(dependency.source_primitive_id)

    context = {normalize_label(tag) for tag in context_tags or []}
    forbidden = {normalize_label(item) for item in forbidden_states or []}
    initial = TrajectoryBranch(
        current_states=sorted(normalize_label(item) for item in start_states or []),
        current_variables={
            normalize_label(name): float(value)
            for name, value in (start_variables or {}).items()
        },
    )
    if forbidden.intersection(initial.current_states):
        return PlanGraphSimulationReport(
            plan_graph_id=plan_graph.id,
            constraint_pruned_count=1,
        )

    active: list[tuple[TrajectoryBranch, frozenset[str]]] = [(initial, frozenset())]
    completed: list[TrajectoryBranch] = []
    expanded_candidate_count = 0
    constraint_pruned_count = 0
    beam_pruned_count = 0
    ready_node_expansion_count = 0
    deadlock_count = 0
    primitive_mismatch_count = 0

    while active:
        expanded: list[tuple[TrajectoryBranch, frozenset[str]]] = []
        for branch, executed in active:
            if len(executed) == len(primitive_ids):
                completed.append(replace(branch, terminated_reason="plan_graph_complete"))
                continue
            ready = sorted(
                primitive_id
                for primitive_id in primitive_ids - set(executed)
                if incoming[primitive_id].issubset(executed)
            )
            if not ready:
                deadlock_count += 1
                continue
            progressed = False
            for primitive_id in ready:
                ready_node_expansion_count += 1
                primitive = primitives[primitive_id]
                actions = sorted(
                    condition.removeprefix("process:")
                    for condition in primitive.input_conditions
                    if condition.startswith("process:")
                )
                if not actions:
                    primitive_mismatch_count += 1
                    continue
                candidates = forecast_next_effects(
                    state,
                    action=actions[0],
                    current_states=branch.current_states,
                    current_variables=branch.current_variables,
                    context_tags=sorted(context),
                    max_candidates=max(1, len(state.structural_primitives)),
                    include_supported_alternatives=True,
                )
                candidate = next(
                    (item for item in candidates if primitive_id in item.primitive_ids),
                    None,
                )
                if candidate is None:
                    continue
                progressed = True
                expanded_candidate_count += 1
                next_states = (
                    set(branch.current_states) - set(candidate.removed_states)
                ) | {candidate.target_effect}
                if forbidden.intersection(next_states):
                    constraint_pruned_count += 1
                    continue
                step = TrajectoryStep(
                    action=actions[0],
                    effect=candidate.target_effect,
                    primitive_id=primitive_id,
                    states_before=list(branch.current_states),
                    states_after=sorted(next_states),
                    variables_before=dict(branch.current_variables),
                    variables_after=dict(candidate.resulting_variables),
                    removed_states=list(candidate.removed_states),
                    score=candidate.score,
                )
                expanded.append(
                    (
                        TrajectoryBranch(
                            steps=[*branch.steps, step],
                            current_states=sorted(next_states),
                            current_variables=dict(candidate.resulting_variables),
                            score=branch.score * candidate.score,
                        ),
                        frozenset({*executed, primitive_id}),
                    )
                )
            if not progressed:
                deadlock_count += 1
        expanded.sort(
            key=lambda item: (-item[0].score, _branch_signature(item[0]), sorted(item[1]))
        )
        beam_pruned_count += max(0, len(expanded) - max_branches)
        active = expanded[:max_branches]

    completed.sort(key=lambda branch: (-branch.score, _branch_signature(branch)))
    beam_pruned_count += max(0, len(completed) - max_branches)
    selected = completed[:max_branches]
    for index, branch in enumerate(selected, start=1):
        branch.id = f"branch:{index:03d}"
        branch.score = round(branch.score, 6)
    return PlanGraphSimulationReport(
        branches=selected,
        plan_graph_id=plan_graph.id,
        expanded_candidate_count=expanded_candidate_count,
        constraint_pruned_count=constraint_pruned_count,
        beam_pruned_count=beam_pruned_count,
        ready_node_expansion_count=ready_node_expansion_count,
        deadlock_count=deadlock_count,
        primitive_mismatch_count=primitive_mismatch_count,
        declared_threat_count=len(plan_graph.threats),
    )


def _branch_signature(branch: TrajectoryBranch) -> str:
    return "|".join(f"{step.action}->{step.effect}" for step in branch.steps)
