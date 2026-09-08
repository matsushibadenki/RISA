import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from risa.core.models import (
    ConjunctivePlanGraph,
    Event,
    GoalSpecification,
    InterventionSpecification,
    PredictionQuery,
    PlanGraphDependency,
    ReplaySummary,
    StateVariableSpec,
    StructuralAdaptationCandidate,
    StructuralPrimitive,
)
from risa.cli.main import build_parser
from risa.core.state import RisaState
from risa.engine.abstractor import rebuild_concepts
from risa.engine.adaptation import execute_safe_adaptations
from risa.engine.composer import compose_to_effect, forecast_next_effects
from risa.engine.candidate_discovery import evaluate_unnamed_candidate
from risa.engine.event_parser import parse_events
from risa.engine.evaluator import evaluate_branches
from risa.engine.predictor import predict_next_effect
from risa.engine.planner import (
    detect_plan_graph_threats,
    generate_backward_intervention_candidates,
    generate_conjunctive_plan_candidates,
    generate_disjunctive_plan_candidates,
    generate_intervention_candidates,
    parse_interventions,
    plan_counterfactuals,
)
from risa.engine.persistence import load_state, save_state
from risa.engine.replay import _replay_deployment_trajectory, replay_structural_memory
from risa.engine.readout_compaction import compact_adopted_candidate_readouts
from risa.engine.runtime import train_events
from risa.engine.simulator import (
    simulate_action_sequence_with_diagnostics,
    simulate_branches,
    simulate_branches_with_diagnostics,
    simulate_plan_graph_with_diagnostics,
)
from risa.engine.state_variables import apply_variable_deltas


class TrainingAndPredictionTests(unittest.TestCase):
    def test_cli_parses_numeric_state_variables(self) -> None:
        parser = build_parser()
        forecast_args = parser.parse_args(
            [
                "forecast", "--action", "spend", "--variable", "energy=5",
                "--target-role", "battery",
            ]
        )
        compose_args = parser.parse_args(
            [
                "compose",
                "--start-action",
                "refill",
                "--goal-effect",
                "spent",
                "--start-variable",
                "energy=10",
                "--actor-role",
                "operator",
                "--actor",
                "robot-a",
                "--target",
                "battery-a",
                "--target-role",
                "battery",
            ]
        )
        simulate_args = parser.parse_args(
            [
                "simulate",
                "--start-action",
                "route",
                "--start-variable",
                "energy=5",
                "--max-branches",
                "4",
            ]
        )
        evaluate_args = parser.parse_args(
            [
                "evaluate",
                "--start-action",
                "route",
                "--goal-state",
                "arrived_safe",
                "--require-state",
                "safe_path",
                "--min-variable",
                "energy=2",
                "--forbid-state",
                "fast_path",
                "--cost-variable",
                "energy=0.1",
            ]
        )
        plan_args = parser.parse_args(
            [
                "plan",
                "--start-action",
                "route",
                "--interventions",
                "data/branching_interventions.json",
                "--generate-interventions",
                "--backward-depth",
                "3",
                "--goal-state",
                "arrived_safe",
            ]
        )

        self.assertEqual(dict(forecast_args.variable), {"energy": 5.0})
        self.assertEqual(forecast_args.target_role, ["battery"])
        self.assertEqual(dict(compose_args.start_variable), {"energy": 10.0})
        self.assertEqual(compose_args.actor_role, ["operator"])
        self.assertEqual(compose_args.actor, "robot-a")
        self.assertEqual(compose_args.target, "battery-a")
        self.assertEqual(compose_args.target_role, ["battery"])
        self.assertEqual(dict(simulate_args.start_variable), {"energy": 5.0})
        self.assertEqual(simulate_args.max_branches, 4)
        self.assertEqual(evaluate_args.goal_state, ["arrived_safe"])
        self.assertEqual(evaluate_args.require_state, ["safe_path"])
        self.assertEqual(dict(evaluate_args.min_variable), {"energy": 2.0})
        self.assertEqual(evaluate_args.forbid_state, ["fast_path"])
        self.assertEqual(dict(evaluate_args.cost_variable), {"energy": 0.1})
        self.assertEqual(plan_args.interventions, "data/branching_interventions.json")
        self.assertTrue(plan_args.generate_interventions)
        self.assertEqual(plan_args.backward_depth, 3)

    def test_stateful_world_benchmark_combines_discrete_and_numeric_state(self) -> None:
        state = RisaState()
        train_events(state, parse_events("data/stateful_world.json"))

        allowed = forecast_next_effects(
            state,
            action="use",
            current_states=["charged"],
            current_variables={"energy": 5.0},
            context_tags=["robot", "power"],
        )
        insufficient = forecast_next_effects(
            state,
            action="use",
            current_states=["charged"],
            current_variables={"energy": 4.0},
            context_tags=["robot", "power"],
        )

        self.assertEqual(allowed[0].target_effect, "depleted")
        self.assertEqual(allowed[0].removed_states, ["charged"])
        self.assertEqual(allowed[0].variable_deltas, {"energy": -5.0})
        self.assertEqual(allowed[0].resulting_variables, {"energy": 0.0})
        self.assertEqual(insufficient, [])
        self.assertEqual(state.state_variable_specs["energy"].unit, "joule")

    def test_branch_simulation_keeps_candidate_trajectories_independent(self) -> None:
        state = RisaState()
        events = [
            Event(
                "b001",
                1,
                "robot_a",
                "route",
                numeric_preconditions={"energy": 2.0},
                state_variable_deltas={"energy": -2.0},
                state_variable_specs={
                    "energy": StateVariableSpec(unit="joule", minimum=0.0, maximum=10.0)
                },
                observed_effects=["safe_path"],
            ),
            Event(
                "b002",
                2,
                "robot_a",
                "finish",
                preconditions=["safe_path"],
                observed_effects=["arrived_safe"],
            ),
            Event(
                "b003",
                3,
                "robot_b",
                "route",
                numeric_preconditions={"energy": 2.0},
                state_variable_deltas={"energy": -2.0},
                observed_effects=["safe_path"],
            ),
            Event(
                "b004",
                4,
                "robot_b",
                "finish",
                preconditions=["safe_path"],
                observed_effects=["arrived_safe"],
            ),
            Event(
                "b005",
                5,
                "robot_c",
                "route",
                numeric_preconditions={"energy": 5.0},
                state_variable_deltas={"energy": -5.0},
                observed_effects=["fast_path"],
            ),
            Event(
                "b006",
                6,
                "robot_c",
                "finish",
                preconditions=["fast_path"],
                observed_effects=["arrived_fast"],
            ),
            Event(
                "b007",
                7,
                "robot_d",
                "route",
                numeric_preconditions={"energy": 5.0},
                state_variable_deltas={"energy": -5.0},
                observed_effects=["fast_path"],
            ),
            Event(
                "b008",
                8,
                "robot_d",
                "finish",
                preconditions=["fast_path"],
                observed_effects=["arrived_fast"],
            ),
        ]
        train_events(state, events)

        branches = simulate_branches(
            state,
            start_action="route",
            start_variables={"energy": 5.0},
            max_steps=2,
            max_branches=4,
        )

        self.assertEqual(len(branches), 2)
        by_effect = {branch.steps[-1].effect: branch for branch in branches}
        safe = by_effect["arrived_safe"]
        fast = by_effect["arrived_fast"]
        self.assertEqual([step.effect for step in safe.steps], ["safe_path", "arrived_safe"])
        self.assertEqual([step.effect for step in fast.steps], ["fast_path", "arrived_fast"])
        self.assertEqual(safe.current_variables, {"energy": 3.0})
        self.assertEqual(fast.current_variables, {"energy": 0.0})
        self.assertIn("safe_path", safe.current_states)
        self.assertNotIn("fast_path", safe.current_states)
        self.assertIn("fast_path", fast.current_states)
        self.assertEqual(safe.terminated_reason, "max_steps")
        self.assertEqual(fast.terminated_reason, "max_steps")

        beam_limited = simulate_branches(
            state,
            start_action="route",
            start_variables={"energy": 5.0},
            max_steps=2,
            max_branches=1,
        )
        self.assertEqual(len(beam_limited), 1)

    def test_branch_evaluator_separates_goal_cost_and_trajectory_risk(self) -> None:
        state = RisaState()
        train_events(state, parse_events("data/branching_world.json"))
        branches = simulate_branches(
            state,
            start_action="route",
            start_variables={"energy": 5.0},
            max_steps=2,
            max_branches=4,
        )

        fast_goal = evaluate_branches(
            branches,
            goal_states=["arrived_fast"],
            variable_cost_weights={"energy": 0.1},
        )
        self.assertEqual(fast_goal.evaluations[0].branch.steps[-1].effect, "arrived_fast")
        self.assertEqual(fast_goal.evaluations[0].matched_goal_states, ["arrived_fast"])

        either_goal = evaluate_branches(
            branches,
            goal_states=["arrived_safe", "arrived_fast"],
            variable_cost_weights={"energy": 0.1},
        )
        selected = either_goal.evaluations[0]
        self.assertEqual(selected.branch.steps[-1].effect, "arrived_safe")
        self.assertLess(selected.variable_costs["energy"], either_goal.evaluations[1].variable_costs["energy"])

        risk_aware = evaluate_branches(
            branches,
            goal_states=["arrived_safe", "arrived_fast"],
            avoid_states=["fast_path"],
        )
        by_effect = {
            evaluation.branch.steps[-1].effect: evaluation
            for evaluation in risk_aware.evaluations
        }
        self.assertEqual(by_effect["arrived_fast"].encountered_avoid_states, ["fast_path"])
        self.assertEqual(by_effect["arrived_fast"].risk_penalty, 1.0)
        self.assertEqual(by_effect["arrived_safe"].risk_penalty, 0.0)

        unreachable = evaluate_branches(branches, goal_states=["arrived_impossible"])
        self.assertIsNone(unreachable.selected_branch_id)
        self.assertTrue(all(evaluation.goal_score == 0.0 for evaluation in unreachable.evaluations))

    def test_goal_specification_combines_and_or_numeric_and_hard_constraints(self) -> None:
        state = RisaState()
        train_events(state, parse_events("data/branching_world.json"))
        branches = simulate_branches(
            state,
            start_action="route",
            start_variables={"energy": 5.0},
            max_steps=2,
            max_branches=4,
        )

        safe_required = evaluate_branches(
            branches,
            goal_specification=GoalSpecification(
                required_states=["safe_path"],
                any_state_groups=[["arrived_safe", "arrived_fast"]],
                minimum_variables={"energy": 1.0},
                forbidden_states=["fast_path"],
            ),
        )
        selected = safe_required.evaluations[0]
        self.assertEqual(selected.branch.steps[-1].effect, "arrived_safe")
        self.assertTrue(selected.goal_satisfied)
        self.assertTrue(selected.hard_constraints_satisfied)
        self.assertEqual(selected.goal_score, 1.0)

        fast = next(
            evaluation
            for evaluation in safe_required.evaluations
            if evaluation.branch.steps[-1].effect == "arrived_fast"
        )
        self.assertFalse(fast.goal_satisfied)
        self.assertFalse(fast.hard_constraints_satisfied)
        self.assertEqual(fast.missing_required_states, ["safe_path"])
        self.assertEqual(fast.unsatisfied_variable_conditions, ["energy>=1"])
        self.assertEqual(fast.violated_hard_constraints, ["forbidden_state:fast_path"])

        zero_energy = evaluate_branches(
            branches,
            goal_specification=GoalSpecification(
                any_state_groups=[["arrived_safe", "arrived_fast"]],
                maximum_variables={"energy": 0.0},
            ),
        )
        self.assertEqual(zero_energy.evaluations[0].branch.steps[-1].effect, "arrived_fast")

        impossible_hard_constraint = evaluate_branches(
            branches,
            goal_specification=GoalSpecification(
                any_state_groups=[["arrived_safe"]],
                forbidden_states=["safe_path"],
            ),
        )
        self.assertIsNone(impossible_hard_constraint.selected_branch_id)

        with self.assertRaisesRegex(ValueError, "minimum greater than maximum"):
            evaluate_branches(
                branches,
                goal_specification=GoalSpecification(
                    minimum_variables={"energy": 2.0},
                    maximum_variables={"energy": 1.0},
                ),
            )

    def test_constraint_aware_search_prunes_forbidden_trajectories_early(self) -> None:
        state = RisaState()
        train_events(state, parse_events("data/branching_world.json"))

        report = simulate_branches_with_diagnostics(
            state,
            start_action="route",
            start_variables={"energy": 5.0},
            forbidden_states=["fast_path"],
            max_steps=2,
            max_branches=4,
        )
        self.assertEqual(len(report.branches), 1)
        self.assertEqual(report.branches[0].steps[-1].effect, "arrived_safe")
        self.assertEqual(report.constraint_pruned_count, 1)
        self.assertEqual(report.expanded_candidate_count, 3)

        blocked_at_start = simulate_branches_with_diagnostics(
            state,
            start_action="route",
            start_states=["forbidden_initial"],
            start_variables={"energy": 5.0},
            forbidden_states=["forbidden_initial"],
            max_steps=2,
        )
        self.assertEqual(blocked_at_start.branches, [])
        self.assertEqual(blocked_at_start.expanded_candidate_count, 0)
        self.assertEqual(blocked_at_start.constraint_pruned_count, 1)

        unfiltered = simulate_branches(
            state,
            start_action="route",
            start_variables={"energy": 5.0},
            max_steps=2,
            max_branches=4,
        )
        self.assertEqual(len(unfiltered), 2)

    def test_counterfactual_planner_selects_feasible_intervention_without_mutating_state(self) -> None:
        state = RisaState()
        train_events(state, parse_events("data/branching_world.json"))
        node_count = len(state.graph.nodes_by_id)
        start_variables = {"energy": 3.0}

        report = plan_counterfactuals(
            state,
            start_action="route",
            start_variables=start_variables,
            interventions=parse_interventions("data/branching_interventions.json"),
            goal_specification=GoalSpecification(
                required_states=["safe_path"],
                any_state_groups=[["arrived_safe", "arrived_fast"]],
                minimum_variables={"energy": 2.0},
                forbidden_states=["fast_path"],
            ),
            max_steps=2,
            max_branches=4,
        )

        self.assertEqual(report.selected_intervention_id, "boost_energy")
        self.assertIsNotNone(report.selected_branch_id)
        by_id = {outcome.intervention.id: outcome for outcome in report.outcomes}
        self.assertFalse(by_id["baseline"].feasible)
        self.assertTrue(by_id["boost_energy"].feasible)
        self.assertFalse(by_id["inject_forbidden_path"].feasible)
        self.assertEqual(
            by_id["inject_forbidden_path"].evaluation.search_diagnostics[
                "constraint_pruned_count"
            ],
            1,
        )
        self.assertFalse(by_id["unknown_action"].feasible)
        self.assertEqual(
            by_id["unknown_action"].evaluation.evaluations[0].confidence_score,
            0.0,
        )
        self.assertEqual(start_variables, {"energy": 3.0})
        self.assertEqual(len(state.graph.nodes_by_id), node_count)

        with self.assertRaisesRegex(ValueError, "add and remove"):
            plan_counterfactuals(
                state,
                start_action="route",
                interventions=[
                    InterventionSpecification(
                        id="invalid",
                        add_states=["charged"],
                        remove_states=["charged"],
                    )
                ],
                goal_specification=GoalSpecification(required_states=["charged"]),
            )

    def test_intervention_generator_reverses_grounded_primitive_requirements(self) -> None:
        state = RisaState()
        train_events(state, parse_events("data/branching_world.json"))
        goal = GoalSpecification(
            required_states=["safe_path"],
            any_state_groups=[["arrived_safe", "arrived_fast"]],
            minimum_variables={"energy": 2.0},
            forbidden_states=["fast_path"],
        )

        candidates = generate_intervention_candidates(
            state,
            start_action="route",
            start_variables={"energy": 3.0},
            goal_specification=goal,
        )
        route_candidate = next(
            candidate
            for candidate in candidates
            if candidate.start_action == "route"
            and candidate.variable_overrides.get("energy") == 4.0
        )
        self.assertTrue(route_candidate.generated)
        self.assertEqual(len(route_candidate.evidence_primitive_ids), 1)
        self.assertIn("route->safe_path", route_candidate.evidence_primitive_ids[0])
        self.assertFalse(
            any("fast_path" in candidate.add_states for candidate in candidates)
        )

        report = plan_counterfactuals(
            state,
            start_action="route",
            start_variables={"energy": 3.0},
            interventions=candidates,
            goal_specification=goal,
            max_steps=2,
            max_branches=4,
        )
        self.assertEqual(report.selected_intervention_id, route_candidate.id)
        selected = next(
            outcome
            for outcome in report.outcomes
            if outcome.intervention.id == report.selected_intervention_id
        )
        self.assertTrue(selected.feasible)
        self.assertEqual(selected.intervention.evidence_primitive_ids, route_candidate.evidence_primitive_ids)

    def test_backward_goal_decomposition_builds_observed_action_chain(self) -> None:
        state = RisaState()
        train_events(state, parse_events("data/branching_world.json"))
        goal = GoalSpecification(
            any_state_groups=[["arrived_safe"]],
            minimum_variables={"energy": 2.0},
            forbidden_states=["fast_path"],
        )

        candidates = generate_backward_intervention_candidates(
            state,
            start_action="route",
            start_variables={"energy": 3.0},
            goal_specification=goal,
            max_depth=3,
        )
        self.assertEqual(len(candidates), 1)
        chain = candidates[0]
        self.assertEqual(chain.suggested_action_sequence, ["route", "finish"])
        self.assertEqual(chain.variable_overrides, {"energy": 4.0})
        self.assertEqual(chain.add_states, [])
        self.assertEqual(len(chain.evidence_primitive_ids), 2)
        self.assertIn("route->safe_path", chain.evidence_primitive_ids[0])
        self.assertIn("finish->arrived_safe", chain.evidence_primitive_ids[1])

        report = plan_counterfactuals(
            state,
            start_action="route",
            start_variables={"energy": 3.0},
            interventions=candidates,
            goal_specification=goal,
            max_steps=2,
            max_branches=4,
        )
        self.assertEqual(report.selected_intervention_id, chain.id)
        selected_outcome = next(
            outcome
            for outcome in report.outcomes
            if outcome.intervention.id == report.selected_intervention_id
        )
        selected_branch = selected_outcome.evaluation.evaluations[0].branch
        self.assertEqual(
            [step.action for step in selected_branch.steps],
            chain.suggested_action_sequence,
        )
        self.assertEqual(
            selected_outcome.evaluation.search_diagnostics["sequence_failed_count"],
            0,
        )
        self.assertEqual(
            generate_backward_intervention_candidates(
                state,
                start_action="route",
                goal_specification=goal,
                max_depth=1,
            ),
            [],
        )

    def test_sequence_constrained_simulation_validates_exact_order(self) -> None:
        state = RisaState()
        train_events(state, parse_events("data/branching_world.json"))

        valid = simulate_action_sequence_with_diagnostics(
            state,
            actions=["route", "finish"],
            start_variables={"energy": 5.0},
            forbidden_states=["fast_path"],
            max_branches=4,
        )
        self.assertEqual(len(valid.branches), 1)
        self.assertEqual(
            [step.action for step in valid.branches[0].steps],
            ["route", "finish"],
        )
        self.assertEqual(
            [step.effect for step in valid.branches[0].steps],
            ["safe_path", "arrived_safe"],
        )
        self.assertEqual(valid.branches[0].terminated_reason, "sequence_complete")
        self.assertEqual(valid.constraint_pruned_count, 1)
        self.assertEqual(valid.sequence_failed_count, 0)

        invalid_order = simulate_action_sequence_with_diagnostics(
            state,
            actions=["finish", "route"],
            start_states=["safe_path"],
            start_variables={"energy": 4.0},
        )
        self.assertEqual(invalid_order.branches, [])
        self.assertEqual(invalid_order.invalid_sequence_edge_count, 1)
        self.assertEqual(invalid_order.expanded_candidate_count, 0)

        insufficient = simulate_action_sequence_with_diagnostics(
            state,
            actions=["route", "finish"],
            start_variables={"energy": 1.0},
        )
        self.assertEqual(insufficient.branches, [])
        self.assertEqual(insufficient.sequence_failed_count, 1)

    def test_conjunctive_plan_graph_resolves_all_required_subplans(self) -> None:
        state = RisaState()
        train_events(state, parse_events("data/conjunctive_world.json"))
        goal = GoalSpecification(any_state_groups=[["launched"]])

        candidates = generate_conjunctive_plan_candidates(
            state,
            start_action="inspect",
            goal_specification=goal,
            context_tags=["assembly"],
            max_depth=4,
        )
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertIsNotNone(candidate.plan_graph)
        self.assertEqual(
            candidate.suggested_action_sequence,
            ["prepare_frame", "prepare_power", "launch"],
        )
        self.assertEqual(candidate.add_states, [])
        self.assertEqual(len(candidate.plan_graph.primitive_ids), 3)
        self.assertEqual(len(candidate.plan_graph.dependencies), 3)
        self.assertEqual(candidate.plan_graph.unresolved_states, [])
        dependency_states = {
            dependency.required_state for dependency in candidate.plan_graph.dependencies
        }
        self.assertEqual(dependency_states, {"frame_ready", "power_ready"})

        linear_candidates = generate_backward_intervention_candidates(
            state,
            start_action="inspect",
            goal_specification=goal,
            context_tags=["assembly"],
            max_depth=4,
        )
        report = plan_counterfactuals(
            state,
            start_action="inspect",
            interventions=[*linear_candidates, candidate],
            goal_specification=goal,
            context_tags=["assembly"],
            max_steps=3,
            max_branches=4,
        )
        self.assertEqual(report.selected_intervention_id, candidate.id)
        outcome = next(
            item for item in report.outcomes if item.intervention.id == candidate.id
        )
        branch = outcome.evaluation.evaluations[0].branch
        self.assertEqual(
            [step.action for step in branch.steps],
            candidate.suggested_action_sequence,
        )
        self.assertEqual(branch.steps[-1].effect, "launched")
        self.assertEqual(branch.terminated_reason, "plan_graph_complete")
        self.assertGreater(
            outcome.evaluation.search_diagnostics["ready_node_expansion_count"],
            0,
        )
        self.assertEqual(outcome.evaluation.search_diagnostics["deadlock_count"], 0)

    def test_disjunctive_subplan_search_preserves_and_compares_producers(self) -> None:
        state = RisaState()
        train_events(state, parse_events("data/disjunctive_world.json"))
        goal = GoalSpecification(
            any_state_groups=[["launched"]],
            minimum_variables={"energy": 2.0},
        )

        candidates = generate_disjunctive_plan_candidates(
            state,
            start_action="inspect",
            start_variables={"energy": 3.0},
            goal_specification=goal,
            context_tags=["assembly"],
            max_depth=4,
        )
        self.assertEqual(len(candidates), 2)
        group_ids = {candidate.plan_graph.alternative_group_id for candidate in candidates}
        self.assertEqual(len(group_ids), 1)
        power_producers = {
            candidate.plan_graph.selected_producers["power_ready"]
            for candidate in candidates
        }
        self.assertTrue(any("prepare_power_safe" in item for item in power_producers))
        self.assertTrue(any("prepare_power_fast" in item for item in power_producers))

        by_action = {
            candidate.suggested_action_sequence[1]: candidate for candidate in candidates
        }
        self.assertEqual(by_action["prepare_power_safe"].variable_overrides, {})
        self.assertEqual(
            by_action["prepare_power_fast"].variable_overrides,
            {"energy": 5.0},
        )

        report = plan_counterfactuals(
            state,
            start_action="inspect",
            start_variables={"energy": 3.0},
            interventions=candidates,
            goal_specification=goal,
            context_tags=["assembly"],
            max_steps=3,
            max_branches=4,
        )
        selected = next(
            outcome
            for outcome in report.outcomes
            if outcome.intervention.id == report.selected_intervention_id
        )
        self.assertEqual(
            selected.intervention.suggested_action_sequence,
            ["prepare_frame", "prepare_power_safe", "launch"],
        )
        self.assertTrue(all(outcome.feasible for outcome in report.outcomes[:2]))

    def test_nested_and_or_search_expands_alternatives_below_direct_producer(self) -> None:
        state = RisaState()
        train_events(state, parse_events("data/nested_and_or_world.json"))
        goal = GoalSpecification(
            required_states=["launched"],
            minimum_variables={"energy": 2.0},
        )

        candidates = generate_disjunctive_plan_candidates(
            state,
            start_action="inspect",
            start_variables={"energy": 2.0},
            goal_specification=goal,
            context_tags=["nested_assembly"],
            max_depth=4,
        )

        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            {candidate.plan_graph.alternative_choice_count for candidate in candidates},
            {1},
        )
        self.assertEqual(
            {candidate.plan_graph.dependency_depth for candidate in candidates},
            {2},
        )
        self.assertTrue(
            all(not candidate.plan_graph.alternative_search_truncated for candidate in candidates)
        )
        self.assertEqual(
            {
                candidate.plan_graph.selected_producers["supply_ready"]
                for candidate in candidates
            },
            {
                next(item for item in state.structural_primitives if "collect_solar" in item),
                next(item for item in state.structural_primitives if "draw_grid" in item),
            },
        )

        by_action = {
            candidate.suggested_action_sequence[0]: candidate for candidate in candidates
        }
        self.assertEqual(
            by_action["collect_solar"].suggested_action_sequence,
            ["collect_solar", "charge_core", "launch"],
        )
        self.assertEqual(by_action["collect_solar"].variable_overrides, {})
        self.assertEqual(by_action["draw_grid"].variable_overrides, {"energy": 4.0})

        report = plan_counterfactuals(
            state,
            start_action="inspect",
            start_variables={"energy": 2.0},
            interventions=candidates,
            goal_specification=goal,
            context_tags=["nested_assembly"],
            max_steps=3,
            max_branches=4,
        )
        selected = next(
            outcome
            for outcome in report.outcomes
            if outcome.intervention.id == report.selected_intervention_id
        )
        self.assertEqual(
            selected.intervention.suggested_action_sequence,
            ["collect_solar", "charge_core", "launch"],
        )

        limited = generate_disjunctive_plan_candidates(
            state,
            start_action="inspect",
            goal_specification=goal,
            context_tags=["nested_assembly"],
            max_depth=4,
            max_candidates=1,
        )
        self.assertEqual(len(limited), 1)
        self.assertTrue(limited[0].plan_graph.alternative_search_truncated)

    def test_partial_order_executor_runs_large_graph_and_pins_primitives(self) -> None:
        state = RisaState()
        producer_ids = []
        dependencies = []
        for index in range(8):
            primitive = StructuralPrimitive(
                id=f"primitive:source:{index}",
                relation_type="transition",
                role_signature="entity->process->state",
                input_conditions={f"process:prepare_{index}"},
                output_state=f"ready_{index}",
                adopted=True,
                adoption_score=0.9,
            )
            state.structural_primitives[primitive.id] = primitive
            producer_ids.append(primitive.id)
            dependencies.append(
                PlanGraphDependency(
                    source_primitive_id=primitive.id,
                    target_primitive_id="primitive:finish",
                    required_state=f"ready_{index}",
                )
            )
        terminal = StructuralPrimitive(
            id="primitive:finish",
            relation_type="transition",
            role_signature="entity->process->state",
            input_conditions={"process:finish"},
            input_state_conditions={f"state:ready_{index}" for index in range(8)},
            output_state="complete",
            adopted=True,
            adoption_score=0.9,
        )
        state.structural_primitives[terminal.id] = terminal
        graph = ConjunctivePlanGraph(
            id="plan_graph:wide",
            primitive_ids=[*producer_ids, terminal.id],
            dependencies=dependencies,
        )

        report = simulate_plan_graph_with_diagnostics(
            state,
            graph,
            max_branches=16,
        )

        self.assertTrue(report.branches)
        self.assertTrue(all(len(branch.steps) == 9 for branch in report.branches))
        self.assertTrue(
            all(branch.steps[-1].primitive_id == terminal.id for branch in report.branches)
        )
        self.assertTrue(
            all(branch.terminated_reason == "plan_graph_complete" for branch in report.branches)
        )
        self.assertGreater(report.ready_node_expansion_count, 9)
        self.assertEqual(report.deadlock_count, 0)
        self.assertEqual(report.primitive_mismatch_count, 0)

    def test_plan_graph_threats_explain_and_preserve_safe_order(self) -> None:
        state = RisaState()
        prepare = StructuralPrimitive(
            id="primitive:prepare_shared",
            relation_type="transition",
            role_signature="entity->process->state",
            input_conditions={"process:prepare_shared"},
            output_state="shared",
            adopted=True,
            adoption_score=0.9,
        )
        use = StructuralPrimitive(
            id="primitive:use_shared",
            relation_type="transition",
            role_signature="entity->process->state",
            input_conditions={"process:use_shared"},
            input_state_conditions={"state:shared"},
            output_state="used",
            adopted=True,
            adoption_score=0.9,
        )
        consume = StructuralPrimitive(
            id="primitive:consume_shared",
            relation_type="transition",
            role_signature="entity->process->state",
            input_conditions={"process:consume_shared"},
            input_state_conditions={"state:shared"},
            consumed_states={"state:shared"},
            output_state="consumed",
            adopted=True,
            adoption_score=0.9,
        )
        finish = StructuralPrimitive(
            id="primitive:finish_shared",
            relation_type="transition",
            role_signature="entity->process->state",
            input_conditions={"process:finish_shared"},
            input_state_conditions={"state:used", "state:consumed"},
            output_state="complete",
            adopted=True,
            adoption_score=0.9,
        )
        nodes = {
            primitive.id: primitive
            for primitive in (prepare, use, consume, finish)
        }
        state.structural_primitives.update(nodes)
        dependencies = [
            PlanGraphDependency(prepare.id, use.id, "shared"),
            PlanGraphDependency(prepare.id, consume.id, "shared"),
            PlanGraphDependency(use.id, finish.id, "used"),
            PlanGraphDependency(consume.id, finish.id, "consumed"),
        ]
        threats = detect_plan_graph_threats(state, nodes, dependencies)
        graph = ConjunctivePlanGraph(
            id="plan_graph:shared_state_threat",
            primitive_ids=list(nodes),
            dependencies=dependencies,
            threats=threats,
        )

        self.assertEqual(len(threats), 1)
        self.assertEqual(threats[0].threat_type, "state_clobber")
        self.assertEqual(threats[0].ordering, "unordered")
        self.assertEqual(threats[0].affected_primitive_id, use.id)

        report = simulate_plan_graph_with_diagnostics(
            state,
            graph,
            max_branches=8,
        )
        self.assertTrue(report.branches)
        self.assertEqual(report.declared_threat_count, 1)
        self.assertGreater(report.deadlock_count, 0)
        self.assertEqual(
            [step.action for step in report.branches[0].steps],
            ["prepare_shared", "use_shared", "consume_shared", "finish_shared"],
        )

        planning = plan_counterfactuals(
            state,
            start_action="prepare_shared",
            goal_specification=GoalSpecification(required_states=["complete"]),
            interventions=[
                InterventionSpecification(
                    id="threat_aware_plan",
                    start_action="prepare_shared",
                    plan_graph=graph,
                )
            ],
            max_branches=8,
            include_baseline=False,
        )
        self.assertEqual(planning.selected_intervention_id, "threat_aware_plan")
        self.assertTrue(planning.outcomes[0].feasible)
        self.assertEqual(
            planning.outcomes[0].evaluation.search_diagnostics[
                "declared_threat_count"
            ],
            1,
        )

    def test_plan_graph_threat_detector_covers_exclusive_and_numeric_resources(self) -> None:
        state = RisaState()
        state.exclusive_state_groups["mode"] = {"state:on", "state:off"}
        switch = StructuralPrimitive(
            id="primitive:switch_off",
            relation_type="transition",
            role_signature="entity->process->state",
            state_group_updates={"mode": "off"},
            state_variable_deltas={"energy": -1.0},
        )
        require_on = StructuralPrimitive(
            id="primitive:require_on",
            relation_type="transition",
            role_signature="entity->process->state",
            input_state_conditions={"state:on"},
            state_variable_deltas={"energy": -2.0},
        )
        nodes = {switch.id: switch, require_on.id: require_on}

        threats = detect_plan_graph_threats(state, nodes, [])

        self.assertEqual(
            {threat.threat_type for threat in threats},
            {"exclusive_state_clobber", "numeric_resource_contention"},
        )
        self.assertTrue(all(threat.ordering == "unordered" for threat in threats))

    def test_train_and_predict_generalizes_run_to_fatigue(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        result = predict_next_effect(state, PredictionQuery(actor="wolf", action="run"))

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertGreater(result.score, 0)
        self.assertGreaterEqual(len(state.concept_members), 1)
        self.assertTrue(any("event:" in " -> ".join(path) for path in result.supporting_paths))

    def test_context_bias_changes_local_prediction_candidates(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        result = predict_next_effect(
            state,
            PredictionQuery(actor="dog", action="drink", context_tags=["animal", "hydration"]),
        )

        self.assertEqual(result.predicted_effects, ["thirst_down"])
        self.assertGreater(result.score, 0)

    def test_concept_cell_receives_energy_when_pattern_is_supported(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)
        rebuild_concepts(state)

        concept = state.graph.get_node("concept:shared_run_fatigue_up")
        self.assertIsNotNone(concept)
        self.assertFalse(concept.dormant)
        self.assertGreater(concept.energy, 0.4)

    def test_training_creates_coactivation_trace_for_repeated_memory(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        edge = state.graph.edges_by_key.get(("entity:dog", "process:run", "co_activates_with"))
        self.assertIsNotNone(edge)
        assert edge is not None
        self.assertGreater(edge.reliability, 0.0)
        self.assertGreaterEqual(edge.evidence_count, 1)

    def test_prediction_exposes_coactivation_support_path(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertTrue(any("co_activates_with" in path for path in result.supporting_paths))
        self.assertIn("co-activation", result.explanation)

    def test_prediction_can_use_coactivation_candidates_without_activation_index(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        state.activation_index = {}
        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertGreater(result.score, 0)

    def test_prediction_can_use_coactivation_radius_without_direct_counts(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        state.activation_index = {}
        state.actor_action_effect_counts = {}
        state.actor_action_context_effect_counts = {}
        state.action_context_effect_counts = {}

        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertGreater(result.score, 0)

    def test_structural_pattern_is_learned_from_contextual_transition(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        pattern = state.structural_patterns.get("structural:entity->process->state:animal|movement")
        self.assertIsNotNone(pattern)
        assert pattern is not None
        self.assertIn("run", pattern.actions)
        self.assertIn("fatigue_up", pattern.effects)
        self.assertGreaterEqual(pattern.support, 3)

    def test_prediction_abstains_when_structural_context_lacks_action_applicability(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        state.activation_index = {}
        state.actor_action_effect_counts = {}
        state.action_effect_counts = {}
        state.actor_action_context_effect_counts = {}
        state.action_context_effect_counts = {}

        result = predict_next_effect(
            state,
            PredictionQuery(actor="unknown_animal", action="unknown_move", context_tags=["animal", "movement"]),
        )

        self.assertEqual(result.predicted_effects, [])
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.claim_status, "abstained")
        self.assertIn("no observed applicability evidence", result.explanation)

    def test_structure_delta_is_stored_between_structural_patterns(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        delta_id = (
            "delta:structural:entity->process->state:animal|movement"
            "=>structural:entity->process->state:animal|recovery"
        )
        delta = state.structure_deltas.get(delta_id)
        self.assertIsNotNone(delta)
        assert delta is not None
        self.assertIn("REMOVE_ACTION:run", delta.operations)
        self.assertIn("ADD_ACTION:rest", delta.operations)
        self.assertIn("REMOVE_EFFECT:fatigue_up", delta.operations)
        self.assertIn("ADD_EFFECT:fatigue_down", delta.operations)

    def test_training_records_local_prediction_validation_history(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        bucket = state.prediction_validation_stats.get("action_context:run:animal|movement")
        self.assertIsNotNone(bucket)
        assert bucket is not None
        self.assertGreater(bucket["total"], 0)
        self.assertGreater(bucket["correct"], 0)
        effect_bucket = state.prediction_validation_stats.get(
            "action_context_effect:run:animal|movement:fatigue_up"
        )
        self.assertIsNotNone(effect_bucket)

    def test_prediction_uses_validation_history_in_explanation(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertIn("prediction-validation history", result.explanation)

    def test_pattern_and_structural_pattern_receive_validation_score(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        pattern = state.patterns.get("pattern:run->fatigue_up")
        structural_pattern = state.structural_patterns.get("structural:entity->process->state:animal|movement")
        self.assertIsNotNone(pattern)
        self.assertIsNotNone(structural_pattern)
        assert pattern is not None
        assert structural_pattern is not None
        self.assertGreaterEqual(pattern.validation_score, 0.5)
        self.assertGreaterEqual(structural_pattern.validation_score, 0.5)

    def test_mispredicted_effect_builds_competition_history(self) -> None:
        state = RisaState()
        events = [
            Event(
                id="e001",
                timestamp=1,
                actor="dog",
                action="run",
                observed_effects=["fatigue_up"],
                context_tags=["animal", "movement"],
            ),
            Event(
                id="e002",
                timestamp=2,
                actor="human",
                action="run",
                observed_effects=["fatigue_up"],
                context_tags=["animal", "movement"],
            ),
            Event(
                id="e003",
                timestamp=3,
                actor="horse",
                action="run",
                observed_effects=["thirst_down"],
                context_tags=["animal", "movement"],
            ),
        ]
        train_events(state, events)

        competition_bucket = state.prediction_competition_stats.get(
            "action_context_competition:run:animal|movement:fatigue_up"
        )
        self.assertIsNotNone(competition_bucket)
        assert competition_bucket is not None
        self.assertGreaterEqual(competition_bucket.get("thirst_down", 0), 1)

    def test_prediction_exposes_competition_inhibition_path_when_present(self) -> None:
        state = RisaState()
        events = [
            Event(
                id="e001",
                timestamp=1,
                actor="dog",
                action="run",
                observed_effects=["fatigue_up"],
                context_tags=["animal", "movement"],
            ),
            Event(
                id="e002",
                timestamp=2,
                actor="human",
                action="run",
                observed_effects=["fatigue_up"],
                context_tags=["animal", "movement"],
            ),
            Event(
                id="e003",
                timestamp=3,
                actor="horse",
                action="run",
                observed_effects=["thirst_down"],
                context_tags=["animal", "movement"],
            ),
        ]
        train_events(state, events)

        result = predict_next_effect(
            state,
            PredictionQuery(actor="horse", action="run", context_tags=["animal", "movement"]),
        )

        self.assertEqual(result.predicted_effects, ["thirst_down"])
        self.assertIn("competition inhibition", result.explanation)
        self.assertTrue(any("competition_inhibits" in path for path in result.supporting_paths))

    def test_repeated_observations_stabilize_action_effect_relation(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        edge = state.graph.edges_by_key.get(("process:run", "state:fatigue_up", "affects"))
        self.assertIsNotNone(edge)
        assert edge is not None
        self.assertGreater(edge.reliability, 0.0)
        self.assertLess(edge.plasticity, 1.0)

        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))
        self.assertIn("reproducibility plasticity", result.explanation)
        self.assertTrue(any("reproducibly_affects" in path for path in result.supporting_paths))

    def test_repeated_transition_is_extracted_as_structural_primitive(self) -> None:
        state = RisaState()
        events = parse_events("data/toy_world.json")
        train_events(state, events)

        primitive_id = "primitive:transition:entity->process->state:run->fatigue_up"
        primitive = state.structural_primitives.get(primitive_id)
        self.assertIsNotNone(primitive)
        assert primitive is not None
        self.assertEqual(primitive.relation_type, "transition")
        self.assertIn("process:run", primitive.input_conditions)
        self.assertEqual(primitive.output_state, "fatigue_up")
        self.assertGreaterEqual(primitive.support, 3)
        self.assertIn(primitive_id, state.event_primitive_ids["e001"])
        self.assertTrue(primitive.adopted)
        self.assertGreater(primitive.reuse_score, 0.9)
        self.assertGreater(primitive.compression_proxy, 0.0)
        self.assertGreaterEqual(primitive.replay_count, len(primitive.evidence_event_ids))
        self.assertGreater(primitive.replay_score, 0.0)

        one_shot = state.structural_primitives[
            "primitive:transition:entity->process->state:drink->thirst_down"
        ]
        self.assertFalse(one_shot.adopted)

        restored = RisaState.from_dict(state.to_dict())
        self.assertIn(primitive_id, restored.structural_primitives)
        self.assertIn(primitive_id, restored.event_primitive_ids["e001"])
        self.assertTrue(restored.structural_primitives[primitive_id].adopted)

        result = predict_next_effect(state, PredictionQuery(actor="dog", action="run"))
        self.assertIn("structural primitives", result.explanation)
        self.assertTrue(any(path[0] == primitive_id and "composes_to" in path for path in result.supporting_paths))

    def test_replay_uses_current_predictions_to_detect_structural_drift(self) -> None:
        state = RisaState()
        events = [
            Event("e001", 1, "dog", "run", observed_effects=["fatigue_up"]),
            Event("e002", 2, "dog", "run", observed_effects=["fatigue_up"]),
            Event("e003", 3, "dog", "run", observed_effects=["injury"]),
        ]
        train_events(state, events)

        injury = state.structural_primitives[
            "primitive:transition:entity->process->state:run->injury"
        ]
        self.assertGreater(injury.replay_count, 0)
        self.assertEqual(injury.replay_success_count, 0)
        self.assertEqual(injury.replay_score, 0.0)

        summary = replay_structural_memory(state)
        self.assertEqual(summary.replayed_events, 3)
        self.assertEqual(summary.successful_events, 2)
        self.assertEqual(summary.failed_events, 1)
        adaptation = state.structural_adaptation_candidates[injury.id]
        self.assertEqual(adaptation.reason, "clean_replay_instability")
        self.assertEqual(adaptation.proposed_operation, "SPLIT_CONTEXT")

    def test_deployment_replay_rolls_model_generated_state_forward(self) -> None:
        state = RisaState()
        events = [
            Event("e001", 1, "robot_a", "charge", observed_effects=["charged"]),
            Event(
                "e002",
                2,
                "robot_a",
                "use",
                preconditions=["charged"],
                observed_effects=["depleted"],
            ),
            Event("e003", 3, "robot_b", "charge", observed_effects=["charged"]),
            Event(
                "e004",
                4,
                "robot_b",
                "use",
                preconditions=["charged"],
                observed_effects=["depleted"],
            ),
        ]

        train_events(state, events)

        use_primitive = state.structural_primitives[
            "primitive:transition:entity->process->state:charged::use->depleted"
        ]
        self.assertEqual(use_primitive.deployment_replay_count, 2)
        self.assertEqual(use_primitive.deployment_replay_success_count, 2)
        self.assertEqual(use_primitive.deployment_replay_score, 1.0)
        self.assertEqual(use_primitive.perturbation_replay_count, 2)
        self.assertEqual(use_primitive.perturbation_replay_success_count, 0)
        self.assertEqual(use_primitive.perturbation_replay_score, 0.0)
        adaptation = state.structural_adaptation_candidates[use_primitive.id]
        self.assertEqual(adaptation.reason, "single_state_dependency")
        self.assertEqual(adaptation.proposed_operation, "ADD_REDUNDANT_PATH")
        self.assertEqual(adaptation.pressure, 1.0)

        restored = RisaState.from_dict(state.to_dict())
        restored_primitive = restored.structural_primitives[use_primitive.id]
        self.assertEqual(restored_primitive.deployment_replay_count, 2)
        self.assertEqual(restored_primitive.deployment_replay_score, 1.0)
        self.assertEqual(restored_primitive.perturbation_replay_count, 2)
        self.assertEqual(restored_primitive.perturbation_replay_score, 0.0)
        restored_adaptation = restored.structural_adaptation_candidates[use_primitive.id]
        self.assertEqual(restored_adaptation.proposed_operation, "ADD_REDUNDANT_PATH")

        summary = replay_structural_memory(restored)
        self.assertEqual(summary.perturbed_events, 2)
        self.assertEqual(summary.perturbation_survived_events, 0)
        self.assertEqual(summary.perturbation_failed_events, 2)

    def test_safe_context_split_uses_only_observed_context_groups(self) -> None:
        state = RisaState()
        events = [
            Event("e001", 1, "robot_a", "move", observed_effects=["arrived"], context_tags=["indoor"]),
            Event("e002", 2, "robot_b", "move", observed_effects=["arrived"], context_tags=["indoor"]),
            Event("e003", 3, "robot_c", "move", observed_effects=["arrived"], context_tags=["outdoor"]),
            Event("e004", 4, "robot_d", "move", observed_effects=["arrived"], context_tags=["outdoor"]),
        ]
        train_events(state, events)
        primitive_id = "primitive:transition:entity->process->state:move->arrived"
        state.structural_adaptation_candidates[primitive_id] = StructuralAdaptationCandidate(
            primitive_id=primitive_id,
            reason="clean_replay_instability",
            proposed_operation="SPLIT_CONTEXT",
            pressure=0.8,
        )

        processed = execute_safe_adaptations(state)

        candidate = state.structural_adaptation_candidates[primitive_id]
        self.assertEqual(len(processed), 1)
        self.assertEqual(candidate.status, "executed")
        self.assertEqual(len(candidate.result_primitive_ids), 2)
        original = state.structural_primitives[primitive_id]
        self.assertFalse(original.adopted)
        self.assertEqual(original.superseded_by, set(candidate.result_primitive_ids))
        self.assertTrue(any("context:indoor" in item for item in candidate.result_primitive_ids))
        self.assertTrue(any("context:outdoor" in item for item in candidate.result_primitive_ids))
        self.assertNotIn(primitive_id, state.event_primitive_ids["e001"])

        restored = RisaState.from_dict(state.to_dict())
        self.assertEqual(
            restored.structural_adaptation_candidates[primitive_id].status,
            "executed",
        )
        self.assertEqual(restored.structural_primitives[primitive_id].superseded_by, original.superseded_by)

        indoor_variant = next(
            item for item in candidate.result_primitive_ids if "context:indoor" in item
        )
        previous_support = state.structural_primitives[indoor_variant].support
        train_events(
            state,
            [
                Event(
                    "e005",
                    5,
                    "robot_e",
                    "move",
                    observed_effects=["arrived"],
                    context_tags=["indoor"],
                )
            ],
        )
        self.assertIn(indoor_variant, state.event_primitive_ids["e005"])
        self.assertEqual(state.structural_primitives[indoor_variant].support, previous_support + 1)

    def test_transition_repair_restores_observed_actor_local_precedence(self) -> None:
        state = RisaState()
        events = [
            Event("e001", 1, "robot_a", "charge", observed_effects=["charged"]),
            Event("e002", 2, "robot_b", "idle", observed_effects=["waiting"]),
            Event(
                "e003",
                3,
                "robot_a",
                "use",
                preconditions=["charged"],
                observed_effects=["depleted"],
            ),
        ]
        train_events(state, events)
        primitive_id = "primitive:transition:entity->process->state:charged::use->depleted"
        state.graph.edges_by_key.pop(("process:charge", "process:use", "precedes"))
        state.structural_adaptation_candidates[primitive_id] = StructuralAdaptationCandidate(
            primitive_id=primitive_id,
            reason="deployment_trajectory_drift",
            proposed_operation="REPAIR_TRANSITION",
            pressure=0.7,
        )

        processed = execute_safe_adaptations(state)

        candidate = state.structural_adaptation_candidates[primitive_id]
        edge = state.graph.edges_by_key.get(("process:charge", "process:use", "precedes"))
        self.assertEqual(len(processed), 1)
        self.assertEqual(candidate.status, "executed")
        self.assertIsNotNone(edge)
        self.assertEqual(
            candidate.result_structure_ids,
            ["edge:process:charge->precedes->process:use"],
        )

        restored = RisaState.from_dict(state.to_dict())
        self.assertEqual(
            restored.structural_adaptation_candidates[primitive_id].result_structure_ids,
            candidate.result_structure_ids,
        )

    def test_transition_repair_blocks_unobserved_precondition_link(self) -> None:
        state = RisaState()
        events = [
            Event("e001", 1, "robot_a", "idle", observed_effects=["waiting"]),
            Event(
                "e002",
                2,
                "robot_a",
                "use",
                preconditions=["charged"],
                observed_effects=["depleted"],
            ),
        ]
        train_events(state, events)
        primitive_id = "primitive:transition:entity->process->state:charged::use->depleted"
        state.structural_adaptation_candidates[primitive_id] = StructuralAdaptationCandidate(
            primitive_id=primitive_id,
            reason="deployment_trajectory_drift",
            proposed_operation="REPAIR_TRANSITION",
            pressure=0.7,
        )
        edge_key = ("process:idle", "process:use", "precedes")
        evidence_before = state.graph.edges_by_key[edge_key].evidence_count

        execute_safe_adaptations(state)

        self.assertEqual(state.structural_adaptation_candidates[primitive_id].status, "blocked")
        self.assertEqual(state.graph.edges_by_key[edge_key].evidence_count, evidence_before)

    def test_global_and_actor_local_temporal_relations_are_separate(self) -> None:
        state = RisaState()
        train_events(
            state,
            [
                Event("e001", 1, "robot_a", "charge", observed_effects=["charged"]),
                Event("e002", 2, "robot_b", "idle", observed_effects=["waiting"]),
                Event(
                    "e003",
                    3,
                    "robot_a",
                    "use",
                    preconditions=["charged"],
                    observed_effects=["depleted"],
                ),
            ],
        )

        self.assertIn(
            ("process:charge", "process:use", "precedes"),
            state.graph.edges_by_key,
        )
        self.assertNotIn(
            ("process:idle", "process:use", "precedes"),
            state.graph.edges_by_key,
        )
        self.assertIn(
            ("process:charge", "process:idle", "globally_precedes"),
            state.graph.edges_by_key,
        )
        self.assertIn(
            ("process:idle", "process:use", "globally_precedes"),
            state.graph.edges_by_key,
        )
        self.assertIn(
            ("event:e001", "event:e003", "event_precedes"),
            state.graph.edges_by_key,
        )
        self.assertNotIn(
            ("event:e002", "event:e003", "event_precedes"),
            state.graph.edges_by_key,
        )
        self.assertIn(
            ("event:e001", "event:e002", "event_globally_precedes"),
            state.graph.edges_by_key,
        )
        self.assertIn(
            ("event:e002", "event:e003", "event_globally_precedes"),
            state.graph.edges_by_key,
        )

        train_events(
            state,
            [Event("e004", 4, "robot_a", "rest", observed_effects=["recovered"])],
        )
        self.assertIn(
            ("process:use", "process:rest", "precedes"),
            state.graph.edges_by_key,
        )
        self.assertIn(
            ("process:use", "process:rest", "globally_precedes"),
            state.graph.edges_by_key,
        )
        self.assertIn(
            ("event:e003", "event:e004", "event_precedes"),
            state.graph.edges_by_key,
        )
        self.assertIn(
            ("event:e003", "event:e004", "event_globally_precedes"),
            state.graph.edges_by_key,
        )

        prediction = predict_next_effect(
            state,
            PredictionQuery(actor="robot_a", action="use"),
        )
        self.assertTrue(
            any("event_precedes" in path for path in prediction.supporting_paths)
        )

        restored = RisaState.from_dict(state.to_dict())
        self.assertIn(
            ("event:e001", "event:e003", "event_precedes"),
            restored.graph.edges_by_key,
        )

    def test_consumed_state_is_removed_from_deployment_trajectory(self) -> None:
        state = RisaState()
        events = [
            Event("e001", 1, "robot_a", "charge", observed_effects=["charged"]),
            Event(
                "e002",
                2,
                "robot_a",
                "use",
                preconditions=["charged"],
                consumed_states=["charged"],
                observed_effects=["depleted"],
            ),
            Event(
                "e003",
                3,
                "robot_a",
                "use",
                preconditions=["charged"],
                consumed_states=["charged"],
                observed_effects=["depleted"],
            ),
            Event("e004", 4, "robot_b", "charge", observed_effects=["charged"]),
            Event(
                "e005",
                5,
                "robot_b",
                "use",
                preconditions=["charged"],
                consumed_states=["charged"],
                observed_effects=["depleted"],
            ),
            Event(
                "e006",
                6,
                "robot_b",
                "use",
                preconditions=["charged"],
                consumed_states=["charged"],
                observed_effects=["depleted"],
            ),
        ]
        train_events(state, events)

        primitive_id = (
            "primitive:transition:entity->process->state:"
            "charged::use->depleted::consume:charged"
        )
        primitive = state.structural_primitives[primitive_id]
        self.assertEqual(primitive.consumed_states, {"state:charged"})
        self.assertEqual(primitive.deployment_replay_count, 4)
        self.assertEqual(primitive.deployment_replay_success_count, 2)
        self.assertEqual(primitive.deployment_replay_score, 0.5)
        self.assertIn(
            ("event:e002", "state:charged", "consumes_state"),
            state.graph.edges_by_key,
        )

        forecast = forecast_next_effects(
            state,
            action="use",
            current_states=["charged"],
        )
        self.assertEqual(forecast[0].target_effect, "depleted")
        self.assertEqual(forecast[0].removed_states, ["charged"])

        restored = RisaState.from_dict(state.to_dict())
        self.assertEqual(restored.structural_primitives[primitive_id].consumed_states, {"state:charged"})
        self.assertEqual(restored.events_by_id["e002"].consumed_states, ["charged"])

    def test_exclusive_state_group_replaces_previous_state(self) -> None:
        state = RisaState()
        events = [
            Event(
                "e001",
                1,
                "robot_a",
                "charge",
                state_group_updates={"battery": "charged"},
                observed_effects=["charged"],
            ),
            Event(
                "e002",
                2,
                "robot_a",
                "use",
                preconditions=["charged"],
                state_group_updates={"battery": "depleted"},
                observed_effects=["depleted"],
            ),
            Event(
                "e003",
                3,
                "robot_a",
                "use",
                preconditions=["charged"],
                state_group_updates={"battery": "depleted"},
                observed_effects=["depleted"],
            ),
            Event(
                "e004",
                4,
                "robot_b",
                "charge",
                state_group_updates={"battery": "charged"},
                observed_effects=["charged"],
            ),
            Event(
                "e005",
                5,
                "robot_b",
                "use",
                preconditions=["charged"],
                state_group_updates={"battery": "depleted"},
                observed_effects=["depleted"],
            ),
            Event(
                "e006",
                6,
                "robot_b",
                "use",
                preconditions=["charged"],
                state_group_updates={"battery": "depleted"},
                observed_effects=["depleted"],
            ),
        ]
        train_events(state, events)

        primitive_id = (
            "primitive:transition:entity->process->state:"
            "charged::use->depleted::groups:battery=depleted"
        )
        primitive = state.structural_primitives[primitive_id]
        self.assertEqual(primitive.state_group_updates, {"battery": "depleted"})
        self.assertEqual(
            state.exclusive_state_groups["battery"],
            {"state:charged", "state:depleted"},
        )
        self.assertEqual(primitive.deployment_replay_count, 4)
        self.assertEqual(primitive.deployment_replay_success_count, 2)
        self.assertEqual(primitive.deployment_replay_score, 0.5)

        forecast = forecast_next_effects(
            state,
            action="use",
            current_states=["charged"],
        )
        self.assertEqual(forecast[0].target_effect, "depleted")
        self.assertEqual(forecast[0].removed_states, ["charged"])
        self.assertIn(
            ("event:e002", "state_group:battery", "updates_state_group"),
            state.graph.edges_by_key,
        )
        self.assertIn(
            ("state_group:battery", "state:depleted", "allows_state"),
            state.graph.edges_by_key,
        )

        restored = RisaState.from_dict(state.to_dict())
        self.assertEqual(
            restored.exclusive_state_groups["battery"],
            state.exclusive_state_groups["battery"],
        )
        self.assertEqual(
            restored.structural_primitives[primitive_id].state_group_updates,
            {"battery": "depleted"},
        )

    def test_numeric_state_variable_supports_partial_consumption(self) -> None:
        state = RisaState()
        events: list[Event] = []
        timestamp = 1
        for actor in ["robot_a", "robot_b"]:
            events.append(
                Event(
                    f"e{timestamp:03d}",
                    timestamp,
                    actor,
                    "refill",
                    state_variable_deltas={"energy": 10.0},
                    observed_effects=["fueled"],
                )
            )
            timestamp += 1
            for _ in range(3):
                events.append(
                    Event(
                        f"e{timestamp:03d}",
                        timestamp,
                        actor,
                        "spend",
                        numeric_preconditions={"energy": 5.0},
                        state_variable_deltas={"energy": -5.0},
                        observed_effects=["spent"],
                    )
                )
                timestamp += 1

        train_events(state, events)

        primitive_id = (
            "primitive:transition:entity->process->state:"
            "spend->spent::require:energy>=5::delta:energy=-5"
        )
        primitive = state.structural_primitives[primitive_id]
        self.assertEqual(primitive.numeric_preconditions, {"energy": 5.0})
        self.assertEqual(primitive.state_variable_deltas, {"energy": -5.0})
        self.assertEqual(primitive.deployment_replay_count, 6)
        self.assertEqual(primitive.deployment_replay_success_count, 4)
        self.assertAlmostEqual(primitive.deployment_replay_score, 4 / 6)

        allowed = forecast_next_effects(
            state,
            action="spend",
            current_variables={"energy": 5.0},
        )
        blocked = forecast_next_effects(
            state,
            action="spend",
            current_variables={"energy": 4.0},
        )
        self.assertEqual(allowed[0].target_effect, "spent")
        self.assertEqual(allowed[0].variable_deltas, {"energy": -5.0})
        self.assertEqual(allowed[0].resulting_variables, {"energy": 0.0})
        self.assertEqual(blocked, [])
        self.assertIn(
            ("event:e002", "state_variable:energy", "requires_state_variable"),
            state.graph.edges_by_key,
        )
        self.assertIn(
            ("event:e002", "state_variable:energy", "changes_state_variable"),
            state.graph.edges_by_key,
        )

        restored = RisaState.from_dict(state.to_dict())
        restored_primitive = restored.structural_primitives[primitive_id]
        self.assertEqual(restored_primitive.numeric_preconditions, {"energy": 5.0})
        self.assertEqual(restored.events_by_id["e002"].state_variable_deltas, {"energy": -5.0})

    def test_numeric_state_bounds_and_atomic_updates(self) -> None:
        state = RisaState()
        events = [
            Event(
                "e001",
                1,
                "robot_a",
                "top_up",
                state_variable_deltas={"energy": 6.0},
                state_variable_specs={
                    "energy": StateVariableSpec(unit="joule", minimum=0.0, maximum=10.0)
                },
                observed_effects=["energy_added"],
            ),
            Event(
                "e002",
                2,
                "robot_b",
                "top_up",
                state_variable_deltas={"energy": 6.0},
                state_variable_specs={
                    "energy": StateVariableSpec(unit="joule", minimum=0.0, maximum=10.0)
                },
                observed_effects=["energy_added"],
            ),
        ]
        train_events(state, events)

        allowed = forecast_next_effects(
            state,
            action="top_up",
            current_variables={"energy": 4.0},
        )
        blocked = forecast_next_effects(
            state,
            action="top_up",
            current_variables={"energy": 5.0},
        )
        self.assertEqual(allowed[0].variable_deltas, {"energy": 6.0})
        self.assertEqual(allowed[0].resulting_variables, {"energy": 10.0})
        self.assertEqual(blocked, [])
        self.assertEqual(state.state_variable_specs["energy"].unit, "joule")
        self.assertEqual(
            state.graph.nodes_by_id["state_variable:energy"].attributes["maximum"],
            "10.0",
        )

        current = {"energy": 5.0, "waste": 0.0}
        specs = {
            "energy": StateVariableSpec(unit="joule", minimum=0.0, maximum=10.0),
            "waste": StateVariableSpec(unit="gram", minimum=0.0, maximum=3.0),
        }
        updated = apply_variable_deltas(
            specs,
            current,
            {"energy": -5.0, "waste": 5.0},
        )
        self.assertIsNone(updated)
        self.assertEqual(current, {"energy": 5.0, "waste": 0.0})

        restored = RisaState.from_dict(state.to_dict())
        self.assertEqual(restored.state_variable_specs["energy"].maximum, 10.0)

    def test_conflicting_state_variable_unit_is_rejected_before_ingest(self) -> None:
        state = RisaState()
        train_events(
            state,
            [
                Event(
                    "e001",
                    1,
                    "robot",
                    "measure",
                    state_variable_deltas={"energy": 1.0},
                    state_variable_specs={"energy": StateVariableSpec(unit="joule")},
                    observed_effects=["measured"],
                )
            ],
        )

        with self.assertRaisesRegex(ValueError, "conflicting unit"):
            train_events(
                state,
                [
                    Event(
                        "e002",
                        2,
                        "robot",
                        "measure",
                        state_variable_deltas={"energy": 1.0},
                        state_variable_specs={"energy": StateVariableSpec(unit="calorie")},
                        observed_effects=["measured"],
                    )
                ],
            )

        self.assertNotIn("e002", state.events_by_id)
        self.assertEqual(state.state_variable_specs["energy"].unit, "joule")

    def test_composer_finds_local_sequence_of_adopted_primitives(self) -> None:
        state = RisaState()
        events = [
            Event("e001", 1, "dog", "run", observed_effects=["fatigue_up"], context_tags=["animal", "sequence"]),
            Event("e002", 2, "dog", "rest", observed_effects=["fatigue_down"], context_tags=["animal", "sequence"]),
            Event("e003", 3, "horse", "run", observed_effects=["fatigue_up"], context_tags=["animal", "sequence"]),
            Event("e004", 4, "horse", "rest", observed_effects=["fatigue_down"], context_tags=["animal", "sequence"]),
        ]
        train_events(state, events)

        result = compose_to_effect(
            state,
            start_action="run",
            target_effect="fatigue_down",
            context_tags=["animal", "sequence"],
            max_steps=2,
        )

        self.assertEqual(result.target_effect, "fatigue_down")
        self.assertEqual(len(result.primitive_ids), 2)
        self.assertEqual(
            result.primitive_ids[0],
            "primitive:transition:entity->process->state:run->fatigue_up",
        )
        self.assertEqual(
            result.primitive_ids[1],
            "primitive:transition:entity->process->state:rest->fatigue_down",
        )
        self.assertGreater(result.score, 0.0)
        self.assertTrue(any("precedes" in path for path in result.supporting_paths))

    def test_composer_respects_state_preconditions(self) -> None:
        state = RisaState()
        events = [
            Event(
                "e001",
                1,
                "dog",
                "run",
                preconditions=["rested"],
                observed_effects=["fatigue_up"],
                context_tags=["animal", "sequence"],
            ),
            Event(
                "e002",
                2,
                "dog",
                "rest",
                preconditions=["fatigue_up"],
                observed_effects=["fatigue_down"],
                context_tags=["animal", "sequence"],
            ),
            Event(
                "e003",
                3,
                "horse",
                "run",
                preconditions=["rested"],
                observed_effects=["fatigue_up"],
                context_tags=["animal", "sequence"],
            ),
            Event(
                "e004",
                4,
                "horse",
                "rest",
                preconditions=["fatigue_up"],
                observed_effects=["fatigue_down"],
                context_tags=["animal", "sequence"],
            ),
        ]
        train_events(state, events)

        blocked = compose_to_effect(
            state,
            start_action="run",
            target_effect="fatigue_down",
            context_tags=["animal", "sequence"],
            start_states=["fatigue_up"],
            max_steps=2,
        )
        self.assertEqual(blocked.primitive_ids, [])

        result = compose_to_effect(
            state,
            start_action="run",
            target_effect="fatigue_down",
            context_tags=["animal", "sequence"],
            start_states=["rested"],
            max_steps=2,
        )
        self.assertEqual(len(result.primitive_ids), 2)
        self.assertIn("state:rested", state.structural_primitives[result.primitive_ids[0]].input_state_conditions)
        self.assertIn("state:fatigue_up", state.structural_primitives[result.primitive_ids[1]].input_state_conditions)

    def test_forecast_returns_multiple_state_compatible_effects(self) -> None:
        state = RisaState()
        events = [
            Event("e001", 1, "dog", "touch", preconditions=["charged"], observed_effects=["warm"], context_tags=["warm"]),
            Event("e002", 2, "dog", "touch", preconditions=["charged"], observed_effects=["warm"], context_tags=["warm"]),
            Event("e003", 3, "horse", "touch", preconditions=["charged"], observed_effects=["spark"], context_tags=["spark"]),
            Event("e004", 4, "horse", "touch", preconditions=["charged"], observed_effects=["spark"], context_tags=["spark"]),
        ]
        train_events(state, events)

        candidates = forecast_next_effects(
            state,
            action="touch",
            current_states=["charged"],
            max_candidates=3,
        )

        self.assertEqual({candidate.target_effect for candidate in candidates}, {"spark", "warm"})
        self.assertTrue(all(candidate.score > 0.0 for candidate in candidates))
        self.assertTrue(all("state:charged" in candidate.supporting_paths[0] for candidate in candidates))

        blocked = forecast_next_effects(state, action="touch", current_states=["uncharged"])
        self.assertEqual(blocked, [])

    def test_joint_effects_form_one_atomic_outcome(self) -> None:
        state = RisaState()
        events = [
            Event(
                f"e{index:03d}",
                index,
                "robot",
                "activate",
                observed_effects=["lit", "warm"],
                state_variable_deltas={"energy": -1.0},
            )
            for index in range(1, 4)
        ]
        train_events(state, events)

        self.assertEqual(len(state.structural_primitives), 1)
        primitive = next(iter(state.structural_primitives.values()))
        self.assertEqual(primitive.produced_states, {"lit", "warm"})
        self.assertTrue(primitive.adopted)
        self.assertTrue(
            all(state.event_primitive_ids[event.id] == [primitive.id] for event in events)
        )

        candidates = forecast_next_effects(
            state,
            action="activate",
            current_variables={"energy": 3.0},
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].added_states, ["lit", "warm"])
        self.assertEqual(candidates[0].resulting_variables, {"energy": 2.0})

        branches = simulate_branches(
            state,
            start_action="activate",
            start_variables={"energy": 3.0},
            max_steps=1,
        )
        self.assertEqual(len(branches), 1)
        self.assertEqual(branches[0].current_states, ["lit", "warm"])
        self.assertEqual(branches[0].current_variables, {"energy": 2.0})
        self.assertEqual(branches[0].steps[0].effects, ["lit", "warm"])

    def test_separate_observed_outcomes_remain_separate_primitives(self) -> None:
        state = RisaState()
        train_events(
            state,
            [
                Event("left-1", 1, "robot", "route", observed_effects=["left"]),
                Event("right-1", 2, "robot", "route", observed_effects=["right"]),
            ],
        )

        outcomes = {
            frozenset(primitive.produced_states)
            for primitive in state.structural_primitives.values()
        }
        self.assertEqual(outcomes, {frozenset({"left"}), frozenset({"right"})})
        self.assertNotEqual(
            state.event_primitive_ids["left-1"],
            state.event_primitive_ids["right-1"],
        )

    def test_joint_outcome_survives_state_round_trip(self) -> None:
        state = RisaState()
        train_events(
            state,
            [
                Event(str(index), index, "robot", "activate", observed_effects=["lit", "warm"])
                for index in range(3)
            ],
        )

        restored = RisaState.from_dict(state.to_dict())
        primitive = next(iter(restored.structural_primitives.values()))
        self.assertEqual(primitive.produced_states, {"lit", "warm"})
        self.assertEqual(primitive.to_dict()["output_states"], ["lit", "warm"])
        self.assertEqual(state.to_dict()["graph"]["format"], "compact-v1")

    def test_deployment_replay_does_not_union_alternative_worlds(self) -> None:
        state = RisaState()
        state.structural_primitives = {
            "left": StructuralPrimitive(
                id="left",
                relation_type="transition",
                role_signature="entity->process->state",
                input_conditions={"process:route"},
                output_state="left",
                state_group_updates={"location": "left"},
                adopted=True,
                adoption_score=1.0,
            ),
            "right": StructuralPrimitive(
                id="right",
                relation_type="transition",
                role_signature="entity->process->state",
                input_conditions={"process:route"},
                output_state="right",
                state_group_updates={"location": "right"},
                adopted=True,
                adoption_score=1.0,
            ),
            "join": StructuralPrimitive(
                id="join",
                relation_type="transition",
                role_signature="entity->process->state",
                input_conditions={"process:join"},
                input_state_conditions={"state:left", "state:right"},
                output_state="impossible",
                adopted=True,
                adoption_score=1.0,
            ),
        }
        state.exclusive_state_groups["location"] = {"state:left", "state:right"}
        state.events_by_id = {
            "route": Event("route", 1, "robot", "route", observed_effects=["left"]),
            "join": Event("join", 2, "robot", "join", observed_effects=["impossible"]),
        }
        state.event_primitive_ids = {"route": ["left"], "join": ["join"]}

        calls: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []

        def traced_forecast(*args, **kwargs):
            candidates = forecast_next_effects(*args, **kwargs)
            calls.append(
                (
                    kwargs["action"],
                    tuple(kwargs["current_states"]),
                    tuple(
                        effect
                        for candidate in candidates
                        for effect in candidate.added_states
                    ),
                )
            )
            return candidates

        with patch(
            "risa.engine.replay.forecast_next_effects",
            side_effect=traced_forecast,
        ):
            summary = ReplaySummary()
            _replay_deployment_trajectory(state, summary)

        join_calls = [call for call in calls if call[0] == "join"]
        self.assertTrue(join_calls)
        self.assertFalse(any(set(call[1]) == {"left", "right"} for call in join_calls))
        self.assertFalse(any("impossible" in call[2] for call in join_calls))
        self.assertEqual(summary.deployment_failed_events, 1)

    def test_deployment_replay_resets_world_at_episode_boundary(self) -> None:
        state = RisaState()
        state.structural_primitives = {
            "seed": StructuralPrimitive(
                id="seed",
                relation_type="transition",
                role_signature="entity->process->state",
                input_conditions={"process:seed"},
                output_state="ready",
                adopted=True,
                adoption_score=1.0,
            ),
            "use": StructuralPrimitive(
                id="use",
                relation_type="transition",
                role_signature="entity->process->state",
                input_conditions={"process:use"},
                input_state_conditions={"state:ready"},
                output_state="done",
                adopted=True,
                adoption_score=1.0,
            ),
        }
        state.events_by_id = {
            "seed": Event(
                "seed", 1, "robot", "seed", observed_effects=["ready"], episode_id="a"
            ),
            "use": Event(
                "use", 2, "robot", "use", observed_effects=["done"], episode_id="b"
            ),
        }
        state.event_primitive_ids = {"seed": ["seed"], "use": ["use"]}

        summary = ReplaySummary()
        _replay_deployment_trajectory(state, summary)

        self.assertEqual(summary.deployment_successful_events, 1)
        self.assertEqual(summary.deployment_failed_events, 1)

    def test_reingesting_the_same_event_is_a_no_op(self) -> None:
        state = RisaState()
        event = Event("stable-id", 1, "robot", "move", observed_effects=["moved"])
        train_events(state, [event])
        before = state.to_dict()

        train_events(state, [event])

        self.assertEqual(state.to_dict(), before)

    def test_reusing_an_event_id_with_different_content_is_rejected(self) -> None:
        state = RisaState()
        train_events(
            state,
            [Event("conflict", 1, "robot", "move", observed_effects=["left"])],
        )

        with self.assertRaisesRegex(ValueError, "explicit correction is required"):
            train_events(
                state,
                [Event("conflict", 1, "robot", "move", observed_effects=["right"])],
            )

    def test_episode_boundaries_prevent_cross_episode_temporal_edges(self) -> None:
        state = RisaState()
        train_events(
            state,
            [
                Event(
                    "a1",
                    1,
                    "robot",
                    "start_a",
                    observed_effects=["a_ready"],
                    episode_id="episode-a",
                    source="sensor-a",
                ),
                Event(
                    "b1",
                    2,
                    "robot",
                    "start_b",
                    observed_effects=["b_ready"],
                    episode_id="episode-b",
                    source="sensor-b",
                ),
                Event(
                    "a2",
                    3,
                    "robot",
                    "finish_a",
                    observed_effects=["a_done"],
                    episode_id="episode-a",
                    source="sensor-a",
                ),
            ],
        )

        self.assertIn(
            ("event:a1", "event:a2", "event_precedes"),
            state.graph.edges_by_key,
        )
        self.assertNotIn(
            ("event:a1", "event:b1", "event_precedes"),
            state.graph.edges_by_key,
        )
        self.assertNotIn(
            ("event:b1", "event:a2", "event_precedes"),
            state.graph.edges_by_key,
        )
        self.assertEqual(
            state.graph.get_node("event:a1").attributes["source"],
            "sensor-a",
        )

    def test_late_event_that_rewrites_episode_order_is_rejected(self) -> None:
        state = RisaState()
        train_events(
            state,
            [
                Event(
                    "later",
                    2,
                    "robot",
                    "finish",
                    observed_effects=["done"],
                    episode_id="episode-a",
                )
            ],
        )

        with self.assertRaisesRegex(ValueError, "late-arriving event"):
            train_events(
                state,
                [
                    Event(
                        "earlier",
                        1,
                        "robot",
                        "start",
                        observed_effects=["ready"],
                        episode_id="episode-a",
                    )
                ],
            )

    def test_prediction_uses_grounded_target_evidence_and_can_abstain(self) -> None:
        state = RisaState()
        train_events(
            state,
            [
                Event("heater-1", 1, "robot", "touch", target="heater", observed_effects=["hot"]),
                Event("ice-1", 2, "robot", "touch", target="ice", observed_effects=["cold"]),
                Event("heater-2", 3, "robot", "touch", target="heater", observed_effects=["hot"]),
                Event("ice-2", 4, "robot", "touch", target="ice", observed_effects=["cold"]),
            ],
        )

        heater = predict_next_effect(
            state,
            PredictionQuery(actor="robot", action="touch", target="heater"),
        )
        ice = predict_next_effect(
            state,
            PredictionQuery(actor="robot", action="touch", target="ice"),
        )
        unknown = predict_next_effect(
            state,
            PredictionQuery(actor="robot", action="touch", target="unknown"),
        )

        self.assertEqual(heater.predicted_effects, ["hot"])
        self.assertEqual(ice.predicted_effects, ["cold"])
        self.assertEqual(heater.claim_status, "derived")
        self.assertEqual(heater.evidence_event_ids, ["heater-1", "heater-2"])
        self.assertTrue(all("entity:heater" in path for path in heater.supporting_paths if "event:" in " ".join(path)))
        self.assertEqual(unknown.predicted_effects, [])
        self.assertEqual(unknown.claim_status, "abstained")

        restored = RisaState.from_dict(state.to_dict())
        restored_heater = predict_next_effect(
            restored,
            PredictionQuery(actor="robot", action="touch", target="heater"),
        )
        self.assertEqual(restored_heater.predicted_effects, ["hot"])

    def test_target_grounding_preserves_the_complete_atomic_outcome(self) -> None:
        state = RisaState()
        train_events(
            state,
            [
                Event(
                    "heater-1",
                    1,
                    "robot",
                    "touch",
                    target="heater",
                    observed_effects=["changed", "warm"],
                ),
                Event(
                    "ice-1",
                    2,
                    "robot",
                    "touch",
                    target="ice",
                    observed_effects=["changed", "cold"],
                ),
            ],
        )

        heater = predict_next_effect(
            state,
            PredictionQuery(actor="robot", action="touch", target="heater"),
        )
        ice = predict_next_effect(
            state,
            PredictionQuery(actor="robot", action="touch", target="ice"),
        )

        self.assertEqual(set(heater.predicted_effects), {"changed", "warm"})
        self.assertEqual(set(ice.predicted_effects), {"changed", "cold"})

    def test_unseen_target_can_bind_through_an_observed_role(self) -> None:
        state = RisaState()
        train_events(
            state,
            [
                Event(
                    f"heater-{index}",
                    index,
                    "robot",
                    "inspect",
                    target="heater",
                    target_roles=["heating_device"],
                    observed_effects=["warm"],
                )
                for index in range(1, 4)
            ],
        )

        result = predict_next_effect(
            state,
            PredictionQuery(
                actor="new_robot",
                action="inspect",
                target="radiator",
                target_roles=["heating_device"],
            ),
        )

        self.assertEqual(result.predicted_effects, ["warm"])
        self.assertEqual(result.claim_status, "derived")
        self.assertIn("target_role:heating_device", result.applicability_basis)
        self.assertTrue(any("role:heating_device" in path for path in result.supporting_paths))

        unknown_role = predict_next_effect(
            state,
            PredictionQuery(
                actor="new_robot",
                action="inspect",
                target="radiator",
                target_roles=["unknown_device"],
            ),
        )
        self.assertEqual(unknown_role.claim_status, "abstained")
        self.assertIn(
            ("entity:heater", "role:heating_device", "has_role"),
            state.graph.edges_by_key,
        )

    def test_three_consistent_recent_outcomes_create_a_reversible_change_hypothesis(self) -> None:
        state = RisaState()
        train_events(
            state,
            [
                Event(
                    f"stable-{index}", index, "robot", "tune", target="device",
                    observed_effects=["stable"], episode_id=f"initial-{index}",
                )
                for index in range(1, 4)
            ],
        )
        for index in range(4, 7):
            train_events(
                state,
                [
                    Event(
                        f"unstable-{index}", index, "robot", "tune", target="device",
                        observed_effects=["unstable"], episode_id=f"change-{index}",
                    )
                ],
            )

        changed = predict_next_effect(
            state,
            PredictionQuery(actor="robot", action="tune", target="device"),
        )
        hypothesis = state.change_hypotheses["change:tune:device:__no_context__"]
        self.assertEqual(changed.predicted_effects, ["unstable"])
        self.assertEqual(hypothesis.previous_outcome, ["stable"])
        self.assertEqual(hypothesis.current_outcome, ["unstable"])

        for index in range(7, 10):
            train_events(
                state,
                [
                    Event(
                        f"restored-{index}", index, "robot", "tune", target="device",
                        observed_effects=["stable"], episode_id=f"restore-{index}",
                    )
                ],
            )
        restored = predict_next_effect(
            state,
            PredictionQuery(actor="robot", action="tune", target="device"),
        )
        restored_hypothesis = state.change_hypotheses[
            "change:tune:device:__no_context__"
        ]
        self.assertEqual(restored.predicted_effects, ["stable"])
        self.assertEqual(restored_hypothesis.previous_outcome, ["unstable"])
        self.assertEqual(restored_hypothesis.current_outcome, ["stable"])

        round_tripped = RisaState.from_dict(state.to_dict())
        self.assertEqual(
            round_tripped.change_hypotheses[
                "change:tune:device:__no_context__"
            ].current_outcome,
            ["stable"],
        )

    def test_applicability_is_learned_from_successes_and_failures_then_retracted(self) -> None:
        state = RisaState()
        train_events(
            state,
            [
                Event(
                    "success-1", 1, "robot", "open", observed_states_before=["key"],
                    before_state_observed=True, observed_effects=["opened"], episode_id="s1",
                ),
                Event(
                    "success-2", 2, "robot", "open", observed_states_before=["key"],
                    before_state_observed=True, observed_effects=["opened"], episode_id="s2",
                ),
                Event(
                    "failure-1", 3, "robot", "open", observed_states_before=[],
                    before_state_observed=True, observed_effects=[], transition_succeeded=False,
                    episode_id="f1",
                ),
            ],
        )

        primitive = next(iter(state.structural_primitives.values()))
        self.assertEqual(primitive.learned_state_conditions, {"state:key"})
        self.assertIn(primitive.id, state.applicability_hypotheses)
        self.assertEqual(forecast_next_effects(state, "open", current_states=[]), [])
        self.assertEqual(
            forecast_next_effects(state, "open", current_states=["key"])[0].added_states,
            ["opened"],
        )

        train_events(
            state,
            [
                Event(
                    "counterexample", 4, "robot", "open", observed_states_before=[],
                    before_state_observed=True, observed_effects=["opened"], episode_id="s3",
                )
            ],
        )
        self.assertEqual(primitive.learned_state_conditions, set())
        self.assertNotIn(primitive.id, state.applicability_hypotheses)
        self.assertTrue(forecast_next_effects(state, "open", current_states=[]))

    def test_unnamed_candidate_requires_diverse_primary_evidence_and_keeps_counterexamples(self) -> None:
        state = RisaState()
        events = [
            Event(
                "heater", 1, "robot-a", "inspect", target="heater",
                target_roles=["heating_device"], observed_effects=["warm"],
                episode_id="episode-a", source="sensor-a",
            ),
            Event(
                "radiator", 2, "robot-b", "inspect", target="radiator",
                target_roles=["heating_device"], observed_effects=["warm"],
                episode_id="episode-b", source="sensor-b",
            ),
            Event(
                "boiler-exception", 3, "robot-c", "inspect", target="boiler",
                target_roles=["heating_device"], observed_effects=["cold"],
                episode_id="episode-c", source="sensor-c",
            ),
        ]

        train_events(state, events)

        self.assertEqual(len(state.unnamed_concept_candidates), 1)
        candidate = next(iter(state.unnamed_concept_candidates.values()))
        self.assertEqual(candidate.lifecycle_status, "proposed")
        self.assertEqual(candidate.target_diversity, 2)
        self.assertEqual(candidate.source_diversity, 2)
        self.assertGreater(candidate.description_length_delta, 0)
        self.assertEqual(candidate.counterexample_event_ids, ["boiler-exception"])
        self.assertEqual(candidate.derivation_generation, 0)
        self.assertEqual(set(state.events_by_id), {event.id for event in events})

        restored = RisaState.from_dict(state.to_dict())
        self.assertEqual(
            next(iter(restored.unnamed_concept_candidates.values())).supporting_event_ids,
            ["heater", "radiator"],
        )

        evaluate_unnamed_candidate(
            state,
            candidate.id,
            partition="development",
            evaluation_event_ids=["dev-heldout"],
            prediction_delta=0.08,
            composition_delta=0.0,
            prediction_delta_ci_lower=0.02,
            composition_delta_ci_lower=0.0,
            false_generalization_delta=0.0,
        )
        self.assertEqual(candidate.lifecycle_status, "provisional")
        with self.assertRaisesRegex(ValueError, "overlaps development/final evidence"):
            evaluate_unnamed_candidate(
                state,
                candidate.id,
                partition="final",
                evaluation_event_ids=["dev-heldout"],
                prediction_delta=0.07,
                composition_delta=0.0,
                prediction_delta_ci_lower=0.01,
                composition_delta_ci_lower=0.0,
                false_generalization_delta=0.0,
            )

        evaluate_unnamed_candidate(
            state,
            candidate.id,
            partition="final",
            evaluation_event_ids=["final-heldout"],
            prediction_delta=0.07,
            composition_delta=0.0,
            prediction_delta_ci_lower=0.01,
            composition_delta_ci_lower=0.0,
            false_generalization_delta=-0.01,
        )
        self.assertEqual(candidate.lifecycle_status, "adopted")
        self.assertEqual(
            state.candidate_inference_index[
                "action:inspect:target_role:heating_device"
            ],
            [candidate.id],
        )

        state.action_target_role_context_effect_counts.clear()
        without_candidate = predict_next_effect(
            state,
            PredictionQuery(
                actor="robot-d",
                action="inspect",
                target="new-radiator",
                target_roles=["heating_device"],
                enable_candidate_concepts=False,
            ),
        )
        self.assertEqual(without_candidate.claim_status, "abstained")
        with_candidate = predict_next_effect(
            state,
            PredictionQuery(
                actor="robot-d",
                action="inspect",
                target="new-radiator",
                target_roles=["heating_device"],
            ),
        )
        self.assertEqual(with_candidate.predicted_effects, ["warm"])
        self.assertIn(candidate.id, with_candidate.applicability_basis)
        self.assertTrue(
            any(path[0] == candidate.id for path in with_candidate.supporting_paths)
        )

        state.structural_primitives.clear()
        self.assertEqual(
            forecast_next_effects(
                state,
                "inspect",
                target_roles=["heating_device"],
                enable_candidate_concepts=False,
            ),
            [],
        )
        candidate_forecast = forecast_next_effects(
            state,
            "inspect",
            target_roles=["heating_device"],
        )
        self.assertEqual(candidate_forecast[0].added_states, ["warm"])
        self.assertEqual(candidate_forecast[0].primitive_ids, [f"derived:{candidate.id}"])
        self.assertEqual(set(state.events_by_id), {event.id for event in events})

        compact_payload = state.to_dict()
        self.assertNotIn("activation_index", compact_payload)
        self.assertNotIn("action_effect_counts", compact_payload)
        self.assertNotIn("candidate_inference_index", compact_payload)
        adopted_restored = RisaState.from_dict(compact_payload)
        self.assertEqual(
            adopted_restored.candidate_inference_index[
                "action:inspect:target_role:heating_device"
            ],
            [candidate.id],
        )

        with self.assertRaisesRegex(ValueError, "overlaps supporting evidence"):
            evaluate_unnamed_candidate(
                state,
                candidate.id,
                partition="development",
                evaluation_event_ids=["heater"],
                prediction_delta=0.1,
                composition_delta=0.0,
                prediction_delta_ci_lower=0.01,
                composition_delta_ci_lower=0.0,
                false_generalization_delta=0.0,
            )

    def test_temporal_candidate_reuses_a_same_target_plan_without_stored_primitives(self) -> None:
        state = RisaState()
        support = [
            Event(
                "charge-a", 1, "robot-a", "charge", target="device-a",
                target_roles=["powered_device"], preconditions=["connected"],
                numeric_preconditions={"energy": 2.0},
                state_variable_deltas={"energy": -1.0},
                observed_effects=["charged"],
                episode_id="sequence-a", source="sensor-a",
            ),
            Event(
                "activate-a", 2, "robot-a", "activate", target="device-a",
                target_roles=["powered_device"], preconditions=["charged"],
                consumed_states=["charged"], numeric_preconditions={"energy": 1.0},
                state_variable_deltas={"energy": -1.0},
                observed_states_before=["charged"], before_state_observed=True,
                observed_effects=["online"], episode_id="sequence-a", source="sensor-a",
            ),
            Event(
                "charge-b", 3, "robot-b", "charge", target="device-b",
                target_roles=["powered_device"], preconditions=["connected"],
                numeric_preconditions={"energy": 2.0},
                state_variable_deltas={"energy": -1.0},
                observed_effects=["charged"],
                episode_id="sequence-b", source="sensor-b",
            ),
            Event(
                "activate-b", 4, "robot-b", "activate", target="device-b",
                target_roles=["powered_device"], preconditions=["charged"],
                consumed_states=["charged"], numeric_preconditions={"energy": 1.0},
                state_variable_deltas={"energy": -1.0},
                observed_states_before=["charged"], before_state_observed=True,
                observed_effects=["online"], episode_id="sequence-b", source="sensor-b",
            ),
            Event(
                "charge-c", 5, "robot-c", "charge", target="device-c",
                target_roles=["powered_device"], preconditions=["connected"],
                numeric_preconditions={"energy": 2.0},
                state_variable_deltas={"energy": -1.0}, observed_effects=["charged"],
                episode_id="sequence-c", source="sensor-c",
            ),
            Event(
                "activate-c-failed", 6, "robot-c", "activate", target="device-c",
                target_roles=["powered_device"], preconditions=["charged"],
                observed_states_before=["charged"], before_state_observed=True,
                observed_effects=[], transition_succeeded=False,
                episode_id="sequence-c", source="sensor-c",
            ),
            Event(
                "activate-c-retry", 7, "robot-c", "activate", target="device-c",
                target_roles=["powered_device"], preconditions=["charged"],
                consumed_states=["charged"], numeric_preconditions={"energy": 1.0},
                state_variable_deltas={"energy": -1.0},
                observed_states_before=["charged"], before_state_observed=True,
                observed_effects=["online"], episode_id="sequence-c", source="sensor-c",
            ),
        ]
        train_events(state, support)
        candidate = next(
            item
            for item in state.unnamed_concept_candidates.values()
            if item.structural_schema.get("kind") == "temporal_sequence"
        )

        self.assertEqual(candidate.structural_schema["target_binding"], "same_target")
        self.assertEqual(candidate.typed_role_variables, {"target": "powered_device"})
        self.assertEqual(len(candidate.structural_schema["steps"]), 2)
        self.assertEqual(candidate.target_diversity, 2)
        self.assertIn("activate-c-failed", candidate.counterexample_event_ids)
        self.assertNotIn("activate-c-retry", candidate.supporting_event_ids)
        self.assertGreater(candidate.description_length_delta, 0)
        evaluate_unnamed_candidate(
            state,
            candidate.id,
            partition="development",
            evaluation_event_ids=["sequence-dev-1", "sequence-dev-2"],
            prediction_delta=0.0,
            composition_delta=0.25,
            prediction_delta_ci_lower=0.0,
            composition_delta_ci_lower=0.1,
            false_generalization_delta=0.0,
        )
        evaluate_unnamed_candidate(
            state,
            candidate.id,
            partition="final",
            evaluation_event_ids=["sequence-final-1", "sequence-final-2"],
            prediction_delta=0.0,
            composition_delta=0.2,
            prediction_delta_ci_lower=0.0,
            composition_delta_ci_lower=0.08,
            false_generalization_delta=0.0,
        )
        self.assertEqual(candidate.lifecycle_status, "adopted")
        plan_key = "plan_start:charge:goal:online:target_role:powered_device"
        self.assertEqual(state.candidate_inference_index[plan_key], [candidate.id])

        source_event_ids = set(state.events_by_id)
        state.structural_primitives.clear()
        without_candidate = compose_to_effect(
            state,
            "charge",
            "online",
            target_roles=["powered_device"],
            enable_candidate_concepts=False,
            start_states=["connected"],
            start_variables={"energy": 2.0},
            max_steps=2,
        )
        with_candidate = compose_to_effect(
            state,
            "charge",
            "online",
            target_roles=["powered_device"],
            start_states=["connected"],
            start_variables={"energy": 2.0},
            max_steps=2,
        )
        wrong_role = compose_to_effect(
            state,
            "charge",
            "online",
            target_roles=["heating_device"],
            start_states=["connected"],
            start_variables={"energy": 2.0},
            max_steps=2,
        )
        insufficient = compose_to_effect(
            state,
            "charge",
            "online",
            target_roles=["powered_device"],
            start_states=["connected"],
            start_variables={"energy": 1.0},
            max_steps=2,
        )

        self.assertEqual(without_candidate.primitive_ids, [])
        self.assertEqual(wrong_role.primitive_ids, [])
        self.assertIn("do not match query role bindings", wrong_role.explanation)
        self.assertEqual(insufficient.primitive_ids, [])
        self.assertEqual(with_candidate.added_states, ["online"])
        self.assertEqual(with_candidate.removed_states, ["charged"])
        self.assertEqual(with_candidate.variable_deltas, {"energy": -2.0})
        self.assertEqual(with_candidate.resulting_variables, {"energy": 0.0})
        self.assertEqual(
            with_candidate.primitive_ids,
            [
                f"derived:{candidate.id}:step:1",
                f"derived:{candidate.id}:step:2",
            ],
        )
        self.assertTrue(
            all("bind:target=same_target" in path for path in with_candidate.supporting_paths)
        )
        self.assertEqual(set(state.events_by_id), source_event_ids)

        restored = RisaState.from_dict(state.to_dict())
        self.assertEqual(restored.candidate_inference_index[plan_key], [candidate.id])
        restored_result = compose_to_effect(
            restored,
            "charge",
            "online",
            target_roles=["powered_device"],
            start_states=["connected"],
            start_variables={"energy": 2.0},
            max_steps=2,
        )
        self.assertEqual(restored_result.primitive_ids, with_candidate.primitive_ids)

    def test_candidate_backed_readout_compaction_is_equivalent_and_reversible(self) -> None:
        state = RisaState()
        support = [
            Event(
                "compact-heater", 1, "robot-a", "inspect", target="heater",
                target_roles=["heating_device"], observed_effects=["warm"],
                episode_id="compact-a", source="sensor-a",
            ),
            Event(
                "compact-radiator", 2, "robot-b", "inspect", target="radiator",
                target_roles=["heating_device"], observed_effects=["warm"],
                episode_id="compact-b", source="sensor-b",
            ),
        ]
        train_events(state, support)
        candidate = next(iter(state.unnamed_concept_candidates.values()))
        evaluate_unnamed_candidate(
            state,
            candidate.id,
            partition="development",
            evaluation_event_ids=["compact-dev"],
            prediction_delta=0.08,
            composition_delta=0.0,
            prediction_delta_ci_lower=0.01,
            composition_delta_ci_lower=0.0,
            false_generalization_delta=0.0,
        )
        evaluate_unnamed_candidate(
            state,
            candidate.id,
            partition="final",
            evaluation_event_ids=["compact-final"],
            prediction_delta=0.07,
            composition_delta=0.0,
            prediction_delta_ci_lower=0.01,
            composition_delta_ci_lower=0.0,
            false_generalization_delta=0.0,
        )
        queries = [
            PredictionQuery(
                actor="heldout", action="inspect", target="new-heater",
                target_roles=["heating_device"],
            ),
            PredictionQuery(
                actor="heldout", action="inspect", target="new-cooler",
                target_roles=["cooling_device"],
            ),
        ]
        rollback_state = RisaState.from_dict(state.to_dict())
        rollback_query = PredictionQuery(
            actor="heldout", action="inspect", target="new-heater",
            target_roles=["heating_device"], enable_candidate_concepts=False,
        )
        rollback_result = compact_adopted_candidate_readouts(
            rollback_state, [rollback_query]
        )
        self.assertFalse(rollback_result.applied)
        self.assertEqual(rollback_result.mismatch_query_indexes, [0])
        self.assertTrue(rollback_state.action_target_role_context_effect_counts)
        self.assertEqual(rollback_state.compacted_role_readouts, {})

        before = [predict_next_effect(state, query).predicted_effects for query in queries]
        result = compact_adopted_candidate_readouts(state, queries)
        after = [predict_next_effect(state, query).predicted_effects for query in queries]

        self.assertTrue(result.applied)
        self.assertEqual(before, after)
        self.assertLess(result.readout_bytes_after, result.readout_bytes_before)
        self.assertEqual(len(state.compacted_role_readouts), 1)

        restored = RisaState.from_dict(state.to_dict())
        self.assertEqual(
            [predict_next_effect(restored, query).predicted_effects for query in queries],
            before,
        )
        self.assertEqual(len(restored.compacted_role_readouts), 1)
        train_events(
            restored,
            [
                Event(
                    "new-evidence", 3, "robot-c", "inspect", target="boiler",
                    target_roles=["heating_device"], observed_effects=["warm"],
                    episode_id="compact-c", source="sensor-c",
                )
            ],
        )
        self.assertEqual(restored.compacted_role_readouts, {})
        self.assertTrue(restored.action_target_role_context_effect_counts)

    def test_temporal_candidate_binds_actor_and_target_role_variables(self) -> None:
        state = RisaState()
        events: list[Event] = []
        timestamp = 1
        for actor, target, source in (
            ("controller-a", "device-a", "sensor-a"),
            ("controller-b", "device-b", "sensor-b"),
        ):
            episode = f"relational-{target}"
            events.extend(
                [
                    Event(
                        f"{episode}-prepare", timestamp, actor, "prepare",
                        target=target, actor_roles=["controller"],
                        target_roles=["powered_device"], observed_effects=["ready"],
                        episode_id=episode, source=source,
                    ),
                    Event(
                        f"{episode}-start", timestamp + 1, actor, "start",
                        target=target, actor_roles=["controller"],
                        target_roles=["powered_device"], preconditions=["ready"],
                        observed_states_before=["ready"], before_state_observed=True,
                        observed_effects=["running"], episode_id=episode, source=source,
                    ),
                ]
            )
            timestamp += 2
        train_events(state, events)
        candidate = next(
            item
            for item in state.unnamed_concept_candidates.values()
            if item.structural_schema.get("kind") == "temporal_sequence"
        )

        self.assertEqual(
            candidate.typed_role_variables,
            {"target": "powered_device", "actor": "controller"},
        )
        self.assertEqual(candidate.structural_schema["actor_binding"], "same_actor")
        self.assertEqual(
            candidate.structural_schema["variable_constraints"],
            [{"left": "actor", "relation": "not_equal", "right": "target"}],
        )
        evaluate_unnamed_candidate(
            state,
            candidate.id,
            partition="development",
            evaluation_event_ids=["relational-dev"],
            prediction_delta=0.0,
            composition_delta=0.2,
            prediction_delta_ci_lower=0.0,
            composition_delta_ci_lower=0.05,
            false_generalization_delta=-0.1,
        )
        evaluate_unnamed_candidate(
            state,
            candidate.id,
            partition="final",
            evaluation_event_ids=["relational-final"],
            prediction_delta=0.0,
            composition_delta=0.2,
            prediction_delta_ci_lower=0.0,
            composition_delta_ci_lower=0.05,
            false_generalization_delta=-0.1,
        )

        valid = compose_to_effect(
            state, "prepare", "running",
            actor_roles=["controller"], target_roles=["powered_device"],
            actor="controller-new", target="device-new", max_steps=2,
        )
        wrong_actor = compose_to_effect(
            state, "prepare", "running",
            actor_roles=["observer"], target_roles=["powered_device"], max_steps=2,
        )
        missing_actor_role = compose_to_effect(
            state, "prepare", "running",
            target_roles=["powered_device"], max_steps=2,
        )
        untyped_baseline = compose_to_effect(
            state, "prepare", "running",
            actor_roles=["observer"], target_roles=["powered_device"],
            enable_candidate_concepts=False, max_steps=2,
        )
        same_identity = compose_to_effect(
            state, "prepare", "running",
            actor_roles=["controller"], target_roles=["powered_device"],
            actor="self-controller", target="self-controller", max_steps=2,
        )
        same_identity_baseline = compose_to_effect(
            state, "prepare", "running",
            actor_roles=["controller"], target_roles=["powered_device"],
            actor="self-controller", target="self-controller",
            enable_candidate_concepts=False, max_steps=2,
        )

        self.assertEqual(len(valid.primitive_ids), 2)
        self.assertTrue(
            all("bind:actor=same_actor" in path for path in valid.supporting_paths)
        )
        self.assertEqual(wrong_actor.primitive_ids, [])
        self.assertEqual(missing_actor_role.primitive_ids, [])
        self.assertTrue(untyped_baseline.primitive_ids)
        self.assertEqual(same_identity.primitive_ids, [])
        self.assertTrue(same_identity_baseline.primitive_ids)
        self.assertIn("identities violate", same_identity.explanation)
        self.assertIn("do not match query role bindings", wrong_actor.explanation)

    def test_legacy_state_migrates_single_output_to_atomic_output_set(self) -> None:
        legacy = RisaState().to_dict()
        legacy.pop("schema_version")
        legacy["structural_primitives"] = {
            "legacy": {
                "id": "legacy",
                "relation_type": "transition",
                "role_signature": "entity->process->state",
                "output_state": "ready",
            }
        }

        restored = RisaState.from_dict(legacy)

        self.assertEqual(restored.schema_version, 3)
        self.assertEqual(restored.structural_primitives["legacy"].produced_states, {"ready"})

    def test_future_state_schema_is_rejected(self) -> None:
        payload = RisaState().to_dict()
        payload["schema_version"] = 999

        with self.assertRaisesRegex(ValueError, "newer than supported"):
            RisaState.from_dict(payload)

    def test_atomic_persistence_keeps_verified_backup_for_recovery(self) -> None:
        with TemporaryDirectory() as directory:
            state = RisaState()
            train_events(
                state,
                [Event("first", 1, "robot", "start", observed_effects=["ready"])],
            )
            save_state(state, directory)

            train_events(
                state,
                [Event("second", 2, "robot", "finish", observed_effects=["done"])],
            )
            save_state(state, directory)
            self.assertTrue((Path(directory) / "state.json.bak").exists())
            self.assertFalse(list(Path(directory).glob("*.tmp")))

            (Path(directory) / "state.json").write_text("{broken", encoding="utf-8")
            recovered = load_state(directory)

            self.assertIn("first", recovered.events_by_id)
            self.assertNotIn("second", recovered.events_by_id)
            self.assertEqual(recovered.schema_version, 3)


if __name__ == "__main__":
    unittest.main()
