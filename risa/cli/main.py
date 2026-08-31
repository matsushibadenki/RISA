from __future__ import annotations

import argparse
import json
import math

from risa.core.models import GoalSpecification, PredictionQuery
from risa.engine.composer import compose_to_effect, forecast_next_effects
from risa.engine.event_parser import parse_events
from risa.engine.evaluator import evaluate_branches
from risa.engine.explainer import format_prediction
from risa.engine.persistence import load_state, save_state
from risa.engine.planner import (
    generate_backward_intervention_candidates,
    generate_conjunctive_plan_candidates,
    generate_disjunctive_plan_candidates,
    generate_intervention_candidates,
    parse_interventions,
    plan_counterfactuals,
)
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import train_events
from risa.engine.simulator import simulate_branches, simulate_branches_with_diagnostics


def _parse_variable_assignment(value: str) -> tuple[str, float]:
    name, separator, raw_value = value.partition("=")
    if not separator or not name.strip():
        raise argparse.ArgumentTypeError("state variable must use NAME=VALUE")
    try:
        parsed_value = float(raw_value)
        if not math.isfinite(parsed_value):
            raise ValueError
        return name.strip(), parsed_value
    except ValueError as error:
        raise argparse.ArgumentTypeError("state variable VALUE must be a finite number") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="risa")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("input_path")
    train_parser.add_argument("--state-dir", default="state")

    predict_parser = subparsers.add_parser("predict")
    predict_parser.add_argument("--actor", required=True)
    predict_parser.add_argument("--action", required=True)
    predict_parser.add_argument("--target")
    predict_parser.add_argument("--context", action="append", default=[])
    predict_parser.add_argument("--state-dir", default="state")

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--state-dir", default="state")

    compose_parser = subparsers.add_parser("compose")
    compose_parser.add_argument("--start-action", required=True)
    compose_parser.add_argument("--goal-effect", required=True)
    compose_parser.add_argument("--context", action="append", default=[])
    compose_parser.add_argument("--start-state", action="append", default=[])
    compose_parser.add_argument(
        "--start-variable", action="append", type=_parse_variable_assignment, default=[]
    )
    compose_parser.add_argument("--max-steps", type=int, default=3)
    compose_parser.add_argument("--state-dir", default="state")

    forecast_parser = subparsers.add_parser("forecast")
    forecast_parser.add_argument("--action", required=True)
    forecast_parser.add_argument("--current-state", action="append", default=[])
    forecast_parser.add_argument(
        "--variable", action="append", type=_parse_variable_assignment, default=[]
    )
    forecast_parser.add_argument("--context", action="append", default=[])
    forecast_parser.add_argument("--max-candidates", type=int, default=3)
    forecast_parser.add_argument("--state-dir", default="state")

    simulate_parser = subparsers.add_parser("simulate")
    simulate_parser.add_argument("--start-action", required=True)
    simulate_parser.add_argument("--start-state", action="append", default=[])
    simulate_parser.add_argument(
        "--start-variable", action="append", type=_parse_variable_assignment, default=[]
    )
    simulate_parser.add_argument("--context", action="append", default=[])
    simulate_parser.add_argument("--max-steps", type=int, default=3)
    simulate_parser.add_argument("--max-branches", type=int, default=8)
    simulate_parser.add_argument("--max-candidates-per-step", type=int, default=3)
    simulate_parser.add_argument("--state-dir", default="state")

    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--start-action", required=True)
    evaluate_parser.add_argument("--goal-state", action="append", default=[])
    evaluate_parser.add_argument("--require-state", action="append", default=[])
    evaluate_parser.add_argument("--forbid-state", action="append", default=[])
    evaluate_parser.add_argument(
        "--min-variable", action="append", type=_parse_variable_assignment, default=[]
    )
    evaluate_parser.add_argument(
        "--max-variable", action="append", type=_parse_variable_assignment, default=[]
    )
    evaluate_parser.add_argument("--avoid-state", action="append", default=[])
    evaluate_parser.add_argument("--start-state", action="append", default=[])
    evaluate_parser.add_argument(
        "--start-variable", action="append", type=_parse_variable_assignment, default=[]
    )
    evaluate_parser.add_argument(
        "--cost-variable", action="append", type=_parse_variable_assignment, default=[]
    )
    evaluate_parser.add_argument("--context", action="append", default=[])
    evaluate_parser.add_argument("--max-steps", type=int, default=3)
    evaluate_parser.add_argument("--max-branches", type=int, default=8)
    evaluate_parser.add_argument("--max-candidates-per-step", type=int, default=3)
    evaluate_parser.add_argument("--state-dir", default="state")

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--start-action", required=True)
    plan_parser.add_argument("--interventions")
    plan_parser.add_argument("--generate-interventions", action="store_true")
    plan_parser.add_argument("--max-generated-interventions", type=int, default=8)
    plan_parser.add_argument("--backward-depth", type=int, default=3)
    plan_parser.add_argument("--goal-state", action="append", default=[])
    plan_parser.add_argument("--require-state", action="append", default=[])
    plan_parser.add_argument("--forbid-state", action="append", default=[])
    plan_parser.add_argument(
        "--min-variable", action="append", type=_parse_variable_assignment, default=[]
    )
    plan_parser.add_argument(
        "--max-variable", action="append", type=_parse_variable_assignment, default=[]
    )
    plan_parser.add_argument("--avoid-state", action="append", default=[])
    plan_parser.add_argument("--start-state", action="append", default=[])
    plan_parser.add_argument(
        "--start-variable", action="append", type=_parse_variable_assignment, default=[]
    )
    plan_parser.add_argument(
        "--cost-variable", action="append", type=_parse_variable_assignment, default=[]
    )
    plan_parser.add_argument("--context", action="append", default=[])
    plan_parser.add_argument("--max-steps", type=int, default=3)
    plan_parser.add_argument("--max-branches", type=int, default=8)
    plan_parser.add_argument("--max-candidates-per-step", type=int, default=3)
    plan_parser.add_argument("--state-dir", default="state")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "train":
        events = parse_events(args.input_path)
        state = load_state(args.state_dir)
        train_events(state, events)
        save_state(state, args.state_dir)
        print(
            json.dumps(
                {
                    "trained_events": len(events),
                    "node_count": len(state.graph.nodes_by_id),
                    "edge_count": len(state.graph.edges_by_key),
                    "pattern_count": len(state.patterns),
                    "structural_primitive_count": len(state.structural_primitives),
                    "concept_count": len(state.concept_members),
                    "validation_bucket_count": len(state.prediction_validation_stats),
                },
                indent=2,
            )
        )
        return

    if args.command == "predict":
        state = load_state(args.state_dir)
        result = predict_next_effect(
            state,
            PredictionQuery(
                actor=args.actor,
                action=args.action,
                target=args.target,
                context_tags=args.context,
            ),
        )
        print(format_prediction(result))
        return

    if args.command == "inspect":
        state = load_state(args.state_dir)
        print(
            json.dumps(
                {
                    "node_count": len(state.graph.nodes_by_id),
                    "edge_count": len(state.graph.edges_by_key),
                    "pattern_count": len(state.patterns),
                    "structural_primitive_count": len(state.structural_primitives),
                    "validation_bucket_count": len(state.prediction_validation_stats),
                    "concepts": state.concept_members,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    if args.command == "compose":
        state = load_state(args.state_dir)
        result = compose_to_effect(
            state,
            start_action=args.start_action,
            target_effect=args.goal_effect,
            context_tags=args.context,
            start_states=args.start_state,
            start_variables=dict(args.start_variable),
            max_steps=args.max_steps,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return

    if args.command == "forecast":
        state = load_state(args.state_dir)
        candidates = forecast_next_effects(
            state,
            action=args.action,
            current_states=args.current_state,
            current_variables=dict(args.variable),
            context_tags=args.context,
            max_candidates=args.max_candidates,
        )
        print(json.dumps([candidate.to_dict() for candidate in candidates], indent=2))
        return

    if args.command == "simulate":
        state = load_state(args.state_dir)
        branches = simulate_branches(
            state,
            start_action=args.start_action,
            start_states=args.start_state,
            start_variables=dict(args.start_variable),
            context_tags=args.context,
            max_steps=args.max_steps,
            max_branches=args.max_branches,
            max_candidates_per_step=args.max_candidates_per_step,
        )
        print(json.dumps([branch.to_dict() for branch in branches], indent=2))
        return

    if args.command == "evaluate":
        state = load_state(args.state_dir)
        goal_specification = GoalSpecification(
            required_states=args.require_state,
            any_state_groups=[args.goal_state] if args.goal_state else [],
            minimum_variables=dict(args.min_variable),
            maximum_variables=dict(args.max_variable),
            forbidden_states=args.forbid_state,
        )
        simulation = simulate_branches_with_diagnostics(
            state,
            start_action=args.start_action,
            start_states=args.start_state,
            start_variables=dict(args.start_variable),
            context_tags=args.context,
            max_steps=args.max_steps,
            max_branches=args.max_branches,
            max_candidates_per_step=args.max_candidates_per_step,
            forbidden_states=goal_specification.forbidden_states,
        )
        report = evaluate_branches(
            simulation.branches,
            avoid_states=args.avoid_state,
            variable_cost_weights=dict(args.cost_variable),
            goal_specification=goal_specification,
            search_diagnostics={
                "expanded_candidate_count": simulation.expanded_candidate_count,
                "constraint_pruned_count": simulation.constraint_pruned_count,
                "beam_pruned_count": simulation.beam_pruned_count,
            },
        )
        print(json.dumps(report.to_dict(), indent=2))
        return

    if args.command == "plan":
        state = load_state(args.state_dir)
        goal_specification = GoalSpecification(
            required_states=args.require_state,
            any_state_groups=[args.goal_state] if args.goal_state else [],
            minimum_variables=dict(args.min_variable),
            maximum_variables=dict(args.max_variable),
            forbidden_states=args.forbid_state,
        )
        interventions = (
            parse_interventions(args.interventions) if args.interventions else []
        )
        if args.generate_interventions:
            generated_interventions = generate_intervention_candidates(
                state,
                start_action=args.start_action,
                start_states=args.start_state,
                start_variables=dict(args.start_variable),
                context_tags=args.context,
                goal_specification=goal_specification,
                max_candidates=args.max_generated_interventions,
            )
            generated_interventions.extend(
                generate_backward_intervention_candidates(
                    state,
                    start_action=args.start_action,
                    start_states=args.start_state,
                    start_variables=dict(args.start_variable),
                    context_tags=args.context,
                    goal_specification=goal_specification,
                    max_depth=args.backward_depth,
                    max_candidates=args.max_generated_interventions,
                )
            )
            generated_interventions.extend(
                generate_conjunctive_plan_candidates(
                    state,
                    start_action=args.start_action,
                    start_states=args.start_state,
                    start_variables=dict(args.start_variable),
                    context_tags=args.context,
                    goal_specification=goal_specification,
                    max_depth=args.backward_depth,
                    max_candidates=args.max_generated_interventions,
                )
            )
            generated_interventions.extend(
                generate_disjunctive_plan_candidates(
                    state,
                    start_action=args.start_action,
                    start_states=args.start_state,
                    start_variables=dict(args.start_variable),
                    context_tags=args.context,
                    goal_specification=goal_specification,
                    max_depth=args.backward_depth,
                    max_candidates=args.max_generated_interventions,
                )
            )
            generated_interventions.sort(key=lambda item: (item.cost, item.id))
            interventions.extend(
                generated_interventions[: args.max_generated_interventions]
            )
        if not interventions:
            parser.error("plan requires --interventions or --generate-interventions")
        report = plan_counterfactuals(
            state,
            start_action=args.start_action,
            start_states=args.start_state,
            start_variables=dict(args.start_variable),
            interventions=interventions,
            goal_specification=goal_specification,
            avoid_states=args.avoid_state,
            variable_cost_weights=dict(args.cost_variable),
            context_tags=args.context,
            max_steps=args.max_steps,
            max_branches=args.max_branches,
            max_candidates_per_step=args.max_candidates_per_step,
        )
        print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
