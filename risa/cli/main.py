from __future__ import annotations

import argparse
import json

from risa.core.models import PredictionQuery
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
                    "concept_count": len(state.concept_members),
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
                    "concepts": state.concept_members,
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()

