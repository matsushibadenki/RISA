from __future__ import annotations

import argparse
import json

from risa.core.models import PredictionQuery
from risa.engine.composer import compose_to_effect, forecast_next_effects
from risa.engine.event_parser import parse_events
from risa.engine.explainer import format_prediction
from risa.engine.persistence import load_state, save_state
from risa.engine.predictor import predict_next_effect
from risa.engine.runtime import train_events


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
    compose_parser.add_argument("--max-steps", type=int, default=3)
    compose_parser.add_argument("--state-dir", default="state")

    forecast_parser = subparsers.add_parser("forecast")
    forecast_parser.add_argument("--action", required=True)
    forecast_parser.add_argument("--current-state", action="append", default=[])
    forecast_parser.add_argument("--context", action="append", default=[])
    forecast_parser.add_argument("--max-candidates", type=int, default=3)
    forecast_parser.add_argument("--state-dir", default="state")

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
            context_tags=args.context,
            max_candidates=args.max_candidates,
        )
        print(json.dumps([candidate.to_dict() for candidate in candidates], indent=2))


if __name__ == "__main__":
    main()
