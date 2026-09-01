import unittest

from risa.core.models import (
    ConjunctivePlanGraph,
    Event,
    GoalSpecification,
    InterventionSpecification,
    PredictionQuery,
    PlanGraphDependency,
    StateVariableSpec,
    StructuralAdaptationCandidate,
    StructuralPrimitive,
)
from risa.cli.main import build_parser
from risa.core.state import RisaState
from risa.engine.abstractor import rebuild_concepts
from risa.engine.adaptation import execute_safe_adaptations
from risa.engine.composer import compose_to_effect, forecast_next_effects
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
from risa.engine.replay import replay_structural_memory
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
            ["forecast", "--action", "spend", "--variable", "energy=5"]
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
        self.assertEqual(dict(compose_args.start_variable), {"energy": 10.0})
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

    def test_prediction_can_fallback_to_structural_pattern_memory(self) -> None:
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

        self.assertEqual(result.predicted_effects, ["fatigue_up"])
        self.assertGreater(result.score, 0)
        self.assertTrue(any(path[0].startswith("structural:") for path in result.supporting_paths))

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


if __name__ == "__main__":
    unittest.main()
